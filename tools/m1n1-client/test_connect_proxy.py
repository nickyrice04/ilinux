"""Tests for connect-proxy.py: tunnels, policy, errors, half-close, concurrency. Loopback only.

    python3 -I tools/m1n1-client/test_connect_proxy.py
"""
import hashlib
import http.client
import http.server
import importlib.util
import io
import os
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("connect_proxy", HERE / "connect-proxy.py")
connect_proxy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(connect_proxy)
Policy, Proxy, Refused = connect_proxy.Policy, connect_proxy.Proxy, connect_proxy.Refused


class EchoServer:
    """Echoes bytes back; after the client half-closes, finishes echoing and closes."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(64)
        self.port = self.sock.getsockname()[1]
        self.connections = 0
        self.lock = threading.Lock()
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with self.lock:
                self.connections += 1
            threading.Thread(target=self.echo, args=(conn,), daemon=True).start()

    @staticmethod
    def echo(conn):
        try:
            while True:
                data = conn.recv(65536)
                if not data:
                    break
                conn.sendall(data)
            conn.shutdown(socket.SHUT_WR)
            time.sleep(0.05)
        except OSError:
            pass
        finally:
            conn.close()

    def close(self):
        self.sock.close()


class Handler(http.server.BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):
        Handler.seen.append((self.path, dict(self.headers)))
        body = ("hello from %s\n" % self.path).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def start_proxy(policy=None, **kw):
    log = io.StringIO()
    proxy = Proxy("127.0.0.1", 0, policy or Policy(allow_loopback=True), log=log, **kw)
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    return proxy, log


def connect_through(proxy, host, port, timeout=10):
    sock = socket.create_connection(("127.0.0.1", proxy.port), timeout=timeout)
    sock.sendall(("CONNECT %s:%d HTTP/1.1\r\nHost: %s:%d\r\n\r\n" % (host, port, host, port)).encode())
    status = recv_until(sock, b"\r\n\r\n")
    return sock, status


def recv_until(sock, marker, limit=65536):
    data = b""
    while marker not in data and len(data) < limit:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data


def recv_all(sock):
    data = b""
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            return data
        data += chunk


class PolicyTests(unittest.TestCase):
    def test_ports(self):
        policy = Policy(ports=(443, 80))
        policy.check_port(443)
        with self.assertRaises(Refused) as ctx:
            policy.check_port(22)
        self.assertEqual(ctx.exception.status, 403)

    def test_addresses(self):
        policy = Policy()
        self.assertIsNone(policy.address_refusal("93.184.216.34"))
        self.assertIsNone(policy.address_refusal("2606:2800:220:1:248:1893:25c8:1946"))
        for address in ("127.0.0.1", "::1", "::ffff:127.0.0.1"):
            self.assertIn("loopback", policy.address_refusal(address))
        for address in ("10.1.2.3", "192.168.1.1", "172.16.0.1", "169.254.1.1", "fe80::1", "fd00::1",
                        "224.0.0.1", "0.0.0.0", "100.64.0.1"):
            self.assertIn("private", policy.address_refusal(address), address)
        self.assertIsNone(Policy(allow_loopback=True).address_refusal("127.0.0.1"))
        self.assertIn("private", Policy(allow_loopback=True).address_refusal("10.0.0.1"))
        self.assertIsNone(Policy(allow_private=True).address_refusal("10.0.0.1"))
        self.assertIn("loopback", Policy(allow_private=True).address_refusal("127.0.0.1"))

    def test_listen_loopback_only(self):
        with self.assertRaises(ValueError):
            Proxy("0.0.0.0", 0)
        with self.assertRaises(ValueError):
            Proxy("192.168.1.2", 0)

    def test_split_host_port(self):
        split = connect_proxy.split_host_port
        self.assertEqual(split("example.com:443"), ("example.com", 443))
        self.assertEqual(split("[::1]:8443"), ("::1", 8443))
        self.assertEqual(split("example.com", 80), ("example.com", 80))
        for bad in ("example.com", "example.com:0", "example.com:x", "a:b:c", "[::1", ":443"):
            with self.assertRaises(Refused):
                split(bad)


class TunnelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.echo = EchoServer()
        cls.http = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.http_port = cls.http.server_address[1]
        threading.Thread(target=cls.http.serve_forever, daemon=True).start()
        cls.proxy, cls.log = start_proxy(Policy(ports=(cls.echo.port, cls.http_port), allow_loopback=True))

    @classmethod
    def tearDownClass(cls):
        cls.proxy.shutdown()
        cls.http.shutdown()
        cls.echo.close()

    def test_connect_relays_both_ways(self):
        sock, status = connect_through(self.proxy, "127.0.0.1", self.echo.port)
        self.assertTrue(status.startswith(b"HTTP/1.1 200 "), status)
        payload = os.urandom(1 << 20)
        sent = hashlib.sha256(payload).hexdigest()
        received = []

        def reader():
            got = b""
            while len(got) < len(payload):
                chunk = sock.recv(65536)
                if not chunk:
                    break
                got += chunk
            received.append(got)

        thread = threading.Thread(target=reader)
        thread.start()
        sock.sendall(payload)
        thread.join(20)
        self.assertEqual(hashlib.sha256(received[0]).hexdigest(), sent)
        sock.shutdown(socket.SHUT_WR)
        self.assertEqual(recv_all(sock), b"")   # the echo server's end came back through
        sock.close()

    def test_half_close_reaches_the_server_and_back(self):
        sock, status = connect_through(self.proxy, "127.0.0.1", self.echo.port)
        self.assertIn(b" 200 ", status)
        sock.sendall(b"ping")
        sock.shutdown(socket.SHUT_WR)
        self.assertEqual(recv_all(sock), b"ping")
        sock.close()

    def test_refused_port(self):
        sock, status = connect_through(self.proxy, "127.0.0.1", 22)
        self.assertTrue(status.startswith(b"HTTP/1.1 403 "), status)
        self.assertIn(b"port 22 is not allowed", status)
        sock.close()

    def test_refused_loopback_without_the_flag(self):
        proxy, _ = start_proxy(Policy(ports=(self.echo.port,)))
        try:
            sock, status = connect_through(proxy, "127.0.0.1", self.echo.port)
            self.assertTrue(status.startswith(b"HTTP/1.1 403 "), status)
            self.assertIn(b"loopback", status)
            sock.close()
        finally:
            proxy.shutdown()

    def test_unreachable_and_unresolvable(self):
        free = socket.socket()
        free.bind(("127.0.0.1", 0))
        port = free.getsockname()[1]
        free.close()
        proxy, _ = start_proxy(Policy(ports=(port,), allow_loopback=True))
        try:
            sock, status = connect_through(proxy, "127.0.0.1", port)
            self.assertTrue(status.startswith(b"HTTP/1.1 502 "), status)
            sock.close()
            sock, status = connect_through(proxy, "no-such-host.invalid", port)
            self.assertTrue(status.startswith(b"HTTP/1.1 502 "), status)
            self.assertIn(b"resolve", status)
            sock.close()
        finally:
            proxy.shutdown()

    def test_bad_requests(self):
        for request, expect in ((b"GET / HTTP/1.1\r\nHost: x\r\n\r\n", b"400"),
                                (b"nonsense\r\n\r\n", b"400"),
                                (b"CONNECT nohost HTTP/1.1\r\n\r\n", b"400"),
                                (b"GET ftp://x/ HTTP/1.1\r\n\r\n", b"405"),
                                (b"X" * 70000 + b"\r\n\r\n", b"431")):
            sock = socket.create_connection(("127.0.0.1", self.proxy.port), timeout=10)
            sock.sendall(request)
            status = recv_until(sock, b"\r\n\r\n")
            self.assertTrue(status.startswith(b"HTTP/1.1 " + expect), (request[:30], status[:60]))
            sock.close()

    def test_plain_http_is_forwarded_with_connection_close(self):
        Handler.seen.clear()
        sock = socket.create_connection(("127.0.0.1", self.proxy.port), timeout=10)
        sock.sendall(("GET http://127.0.0.1:%d/mirror/core.db?x=1 HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n"
                      "Proxy-Connection: keep-alive\r\nUser-Agent: pacman\r\n\r\n" % (self.http_port, self.http_port)).encode())
        response = recv_all(sock)
        sock.close()
        self.assertTrue(response.startswith(b"HTTP/1.0 200 ") or response.startswith(b"HTTP/1.1 200 "), response[:40])
        self.assertTrue(response.endswith(b"hello from /mirror/core.db?x=1\n"), response[-60:])
        path, headers = Handler.seen[-1]
        self.assertEqual(path, "/mirror/core.db?x=1")
        self.assertEqual(headers.get("Connection"), "close")
        self.assertNotIn("Proxy-Connection", headers)
        self.assertEqual(headers.get("User-Agent"), "pacman")

    def test_concurrent_tunnels(self):
        results = []

        def one(i):
            sock, status = connect_through(self.proxy, "127.0.0.1", self.echo.port)
            payload = bytes([i]) * (4096 * (i + 1))
            sock.sendall(payload)
            sock.shutdown(socket.SHUT_WR)
            results.append(recv_all(sock) == payload)
            sock.close()

        threads = [threading.Thread(target=one, args=(i,)) for i in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(30)
        self.assertEqual(results, [True] * 16)

    def test_connection_limit(self):
        proxy, _ = start_proxy(Policy(ports=(self.echo.port,), allow_loopback=True), max_connections=2)
        try:
            held = [connect_through(proxy, "127.0.0.1", self.echo.port)[0] for _ in range(2)]
            sock, status = connect_through(proxy, "127.0.0.1", self.echo.port)
            self.assertTrue(status.startswith(b"HTTP/1.1 503 "), status)
            sock.close()
            for h in held:
                h.close()
            time.sleep(0.2)
            sock, status = connect_through(proxy, "127.0.0.1", self.echo.port)
            self.assertTrue(status.startswith(b"HTTP/1.1 200 "), status)
            sock.close()
        finally:
            proxy.shutdown()

    def test_log_lines_name_the_request(self):
        sock, _ = connect_through(self.proxy, "127.0.0.1", self.echo.port)
        sock.sendall(b"abc")
        sock.shutdown(socket.SHUT_WR)
        recv_all(sock)
        sock.close()
        time.sleep(0.2)
        text = self.log.getvalue()
        self.assertIn("CONNECT 127.0.0.1:%d -> 127.0.0.1:%d 3>/3<" % (self.echo.port, self.echo.port), text)
        self.assertIn(" ok\n", text)

    def test_idle_timeout_ends_a_tunnel(self):
        proxy, _ = start_proxy(Policy(ports=(self.echo.port,), allow_loopback=True), idle_timeout=0.5)
        try:
            sock, status = connect_through(proxy, "127.0.0.1", self.echo.port)
            self.assertIn(b" 200 ", status)
            sock.settimeout(5)
            self.assertEqual(sock.recv(10), b"")   # closed after 0.5 s without data
            sock.close()
        finally:
            proxy.shutdown()


BODY = hashlib.sha256(b"ilinux").digest() * (3 * 1024 * 1024 // 32)   # 3 MiB, deterministic


class BigHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", str(len(BODY)))
        self.end_headers()
        self.wfile.write(BODY)

    def log_message(self, *_):
        pass


def make_cert(where):
    """A self-signed certificate (key, cert) for 127.0.0.1 with openssl, or None."""
    openssl = shutil.which("openssl")
    if not openssl:
        return None
    config = Path(where) / "cert.cnf"
    config.write_text("[req]\ndistinguished_name = dn\nx509_extensions = v3\nprompt = no\n[dn]\nCN = ilinux-test\n"
                      "[v3]\nsubjectAltName = IP:127.0.0.1\nbasicConstraints = critical, CA:TRUE\n")
    cert, key = Path(where) / "cert.pem", Path(where) / "key.pem"
    result = subprocess.run([openssl, "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1",
                             "-nodes", "-keyout", str(key), "-out", str(cert), "-days", "2", "-config", str(config)],
                            capture_output=True, text=True)
    return (cert, key) if result.returncode == 0 else None


class TlsThroughProxyTests(unittest.TestCase):
    """What the M5 does: TLS to a server, end to end, through a CONNECT tunnel the proxy only relays."""

    def test_https_get_through_connect_verifies_the_servers_certificate(self):
        with tempfile.TemporaryDirectory(prefix="proxy-tls-") as tmp:
            pair = make_cert(tmp)
            if pair is None:
                self.skipTest("no openssl to make a certificate")
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), BigHandler)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(str(pair[0]), str(pair[1]))
            server.socket = context.wrap_socket(server.socket, server_side=True)
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            proxy, log = start_proxy(Policy(ports=(port,), allow_loopback=True))
            try:
                client = ssl.create_default_context(cafile=str(pair[0]))   # the proxy never sees this trust
                conn = http.client.HTTPSConnection("127.0.0.1", proxy.port, context=client, timeout=30)
                conn.set_tunnel("127.0.0.1", port)
                conn.request("GET", "/big")
                response = conn.getresponse()
                body = response.read()
                self.assertEqual(response.status, 200)
                self.assertEqual(hashlib.sha256(body).hexdigest(), hashlib.sha256(BODY).hexdigest())
                conn.close()
                time.sleep(0.3)
                line = [l for l in log.getvalue().splitlines() if "CONNECT" in l][-1]
                self.assertIn("CONNECT 127.0.0.1:%d -> 127.0.0.1:%d" % (port, port), line)
                self.assertIn(" ok", line)
                # The proxy relayed ciphertext: the request path never appears in its log.
                self.assertNotIn("/big", log.getvalue())
                # A client that does not trust the certificate fails in the TLS handshake, not in the proxy.
                conn = http.client.HTTPSConnection("127.0.0.1", proxy.port, context=ssl.create_default_context(), timeout=30)
                conn.set_tunnel("127.0.0.1", port)
                with self.assertRaises(ssl.SSLError):
                    conn.request("GET", "/big")
                conn.close()
            finally:
                proxy.shutdown()
                server.shutdown()


if __name__ == "__main__":
    unittest.main()

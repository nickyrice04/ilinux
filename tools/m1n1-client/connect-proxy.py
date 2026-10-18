#!/usr/bin/env python3
"""connect-proxy.py: a small HTTP CONNECT proxy for the M5, standard library only.

It listens on the M1's loopback only. The M1's ssh session over the USB byte pipe
reverse-forwards 127.0.0.1:3128 on the M5 to it (tools/m1n1-client/m5-ssh-config), so
pacman, mise, curl and Claude Code on the M5 reach the web with
HTTPS_PROXY=http://127.0.0.1:3128 while nothing on the M1 changes: no Internet Sharing,
no new interface, no network setting. The proxy resolves names and opens the TCP
connections on the M1's own network; TLS passes through it untouched.

  CONNECT host:port HTTP/1.1       a tunnel to host:port (ports 443 and 80 by default)
  GET http://host/path HTTP/1.1    plain HTTP, forwarded with Connection: close (mirrors)

Destinations on loopback, link-local, private or other special networks are refused
unless --allow-loopback or --allow-private says otherwise (the VM self-test uses
--allow-loopback). One line per connection goes to stderr or --log: time, client port,
request, destination, bytes each way, duration, result.

    python3 -I tools/m1n1-client/connect-proxy.py            # 127.0.0.1:3128
"""
import argparse
import datetime
import ipaddress
import selectors
import socket
import sys
import threading
import time
import urllib.parse

DEFAULT_PORTS = (443, 80)
HEAD_LIMIT = 65536
CHUNK = 65536
# Not public Internet: refused unless --allow-private (older Pythons' is_private misses some).
SPECIAL_NETWORKS = [ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12",
    "192.0.0.0/24", "192.0.2.0/24", "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24",
    "203.0.113.0/24", "224.0.0.0/4", "240.0.0.0/4", "::/128", "::1/128", "fc00::/7", "fe80::/10",
    "ff00::/8", "2001:db8::/32")]
HOP_BY_HOP = {"connection", "keep-alive", "proxy-connection", "proxy-authorization",
              "proxy-authenticate", "te", "trailer", "transfer-encoding", "upgrade"}


class Refused(Exception):
    """A request the proxy answers with an HTTP error: (status, reason)."""

    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status
        self.reason = reason


class Policy:
    def __init__(self, ports=DEFAULT_PORTS, allow_loopback=False, allow_private=False):
        self.ports = frozenset(int(p) for p in ports)
        self.allow_loopback = allow_loopback
        self.allow_private = allow_private

    def check_port(self, port):
        if port not in self.ports:
            raise Refused(403, "port %d is not allowed (allowed: %s)" % (
                port, ", ".join(str(p) for p in sorted(self.ports))))

    def address_refusal(self, text):
        """None if the proxy may connect to this IP address, else why not."""
        address = ipaddress.ip_address(text)
        if getattr(address, "ipv4_mapped", None):
            address = address.ipv4_mapped
        if address.is_loopback:
            return None if self.allow_loopback else "loopback destination"
        special = (address.is_link_local or address.is_private or address.is_multicast or
                   address.is_unspecified or address.is_reserved or
                   any(address in network for network in SPECIAL_NETWORKS))
        if special and not self.allow_private:
            return "private, link-local or special destination"
        return None


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def split_host_port(target, default_port=None):
    """host:port or [v6]:port (or a bare host with default_port) -> (host, port)."""
    if target.startswith("["):
        end = target.find("]")
        if end < 0:
            raise Refused(400, "bad IPv6 host")
        host, rest = target[1:end], target[end + 1:]
        if rest == "":
            port = default_port
        elif rest.startswith(":"):
            port = rest[1:]
        else:
            raise Refused(400, "bad host:port")
    elif target.count(":") == 1:
        host, port = target.split(":")
    elif ":" not in target:
        host, port = target, default_port
    else:
        raise Refused(400, "bad host:port")
    if not host or port is None:
        raise Refused(400, "host and port are required")
    try:
        port = int(port)
    except ValueError:
        raise Refused(400, "bad port") from None
    if not 1 <= port <= 65535:
        raise Refused(400, "bad port")
    return host, port


def parse_head(head):
    """The request head (bytes, without the final CRLF CRLF) -> (method, target, version, headers)."""
    try:
        text = head.decode("iso-8859-1")
    except UnicodeDecodeError:
        raise Refused(400, "bad request") from None
    lines = text.split("\r\n")
    parts = lines[0].split(" ")
    if len(parts) != 3 or not parts[2].startswith("HTTP/1."):
        raise Refused(400, "bad request line")
    headers = []
    for line in lines[1:]:
        if not line:
            continue
        if ":" not in line:
            raise Refused(400, "bad header")
        name, value = line.split(":", 1)
        headers.append((name.strip(), value.strip()))
    return parts[0], parts[1], parts[2], headers


def recv_head(sock):
    """Read the request head; returns (head, leftover bytes received after it)."""
    data = b""
    while True:
        end = data.find(b"\r\n\r\n")
        if end > HEAD_LIMIT or (end < 0 and len(data) > HEAD_LIMIT):
            raise Refused(431, "request head too large")
        if end >= 0:
            return data[:end], data[end + 4:]
        chunk = sock.recv(CHUNK)
        if not chunk:
            raise Refused(400, "connection closed before the request head ended")
        data += chunk


def error_response(status, reason):
    phrases = {400: "Bad Request", 403: "Forbidden", 405: "Method Not Allowed", 431: "Request Header Fields Too Large",
               502: "Bad Gateway", 503: "Service Unavailable", 504: "Gateway Timeout"}
    body = (reason + "\n").encode()
    return ("HTTP/1.1 %d %s\r\nContent-Type: text/plain\r\nContent-Length: %d\r\nConnection: close\r\n\r\n"
            % (status, phrases.get(status, "Error"), len(body))).encode() + body


class Proxy:
    def __init__(self, host="127.0.0.1", port=3128, policy=None, max_connections=64,
                 idle_timeout=300.0, connect_timeout=20.0, log=None):
        if not ipaddress.ip_address(host).is_loopback:
            raise ValueError("the proxy listens on a loopback address only, not " + host)
        self.policy = policy or Policy()
        self.idle_timeout = idle_timeout
        self.connect_timeout = connect_timeout
        self.log = log if log is not None else sys.stderr
        self.slots = threading.BoundedSemaphore(max_connections)
        self.counter = 0
        self.lock = threading.Lock()
        self.stopping = False
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        self.sock = socket.socket(family, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(128)
        self.host = host
        self.port = self.sock.getsockname()[1]

    def say(self, text):
        with self.lock:
            self.log.write("%s %s\n" % (utc_now(), text))
            self.log.flush()

    def serve_forever(self):
        self.say("listening on %s:%d; allowed ports %s; loopback %s, private %s" % (
            self.host, self.port, ",".join(str(p) for p in sorted(self.policy.ports)),
            "allowed" if self.policy.allow_loopback else "refused",
            "allowed" if self.policy.allow_private else "refused"))
        while not self.stopping:
            try:
                client, address = self.sock.accept()
            except OSError:
                if self.stopping:
                    break
                raise
            with self.lock:
                self.counter += 1
                number = self.counter
            threading.Thread(target=self.handle, args=(client, address, number), daemon=True).start()

    def shutdown(self):
        self.stopping = True
        try:
            self.sock.close()
        except OSError:
            pass

    def connect(self, host, port):
        """Resolve host and connect, under the policy; returns (socket, 'ip:port')."""
        try:
            infos = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise Refused(502, "cannot resolve %s: %s" % (host, exc.strerror or exc)) from None
        refusals, failures = [], []
        for family, kind, proto, _, address in infos:
            why = self.policy.address_refusal(address[0])
            if why:
                refusals.append("%s: %s" % (address[0], why))
                continue
            upstream = socket.socket(family, kind, proto)
            upstream.settimeout(self.connect_timeout)
            try:
                upstream.connect(address)
            except OSError as exc:
                failures.append("%s: %s" % (address[0], exc.strerror or exc))
                upstream.close()
                continue
            upstream.settimeout(None)
            return upstream, "%s:%d" % (address[0], address[1])
        if refusals and not failures:
            raise Refused(403, "; ".join(refusals))
        if any("timed out" in f for f in failures):
            raise Refused(504, "connecting to %s timed out" % host)
        raise Refused(502, "cannot connect to %s: %s" % (host, "; ".join(failures) or "no address"))

    def handle(self, client, address, number):
        start = time.monotonic()
        tag = "#%d %s:%d" % (number, address[0], address[1])
        request, destination, result, counts = "-", "-", "-", (0, 0)
        upstream = None
        slot = self.slots.acquire(blocking=False)
        try:
            client.settimeout(self.connect_timeout)
            if not slot:
                raise Refused(503, "too many connections")
            head, leftover = recv_head(client)
            method, target, version, headers = parse_head(head)
            request = "%s %s" % (method, target)
            if method == "CONNECT":
                host, port = split_host_port(target)
                self.policy.check_port(port)
                upstream, destination = self.connect(host, port)
                client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                first = leftover
            elif target.lower().startswith("http://"):
                url = urllib.parse.urlsplit(target)
                host, port = split_host_port(url.netloc, 80)
                self.policy.check_port(port)
                upstream, destination = self.connect(host, port)
                path = (url.path or "/") + ("?" + url.query if url.query else "")
                lines = ["%s %s HTTP/1.1" % (method, path)]
                has_host = False
                for name, value in headers:
                    if name.lower() in HOP_BY_HOP:
                        continue
                    if name.lower() == "host":
                        has_host = True
                    lines.append("%s: %s" % (name, value))
                if not has_host:
                    lines.append("Host: " + url.netloc)
                lines.append("Connection: close")
                first = ("\r\n".join(lines) + "\r\n\r\n").encode("iso-8859-1") + leftover
            elif target.startswith("/"):
                raise Refused(400, "this is a proxy: send CONNECT host:port or an absolute http:// URL")
            else:
                raise Refused(405, "only CONNECT and plain http:// requests are proxied")
            if first:
                upstream.sendall(first)
            client.settimeout(None)
            counts = self.relay(client, upstream, len(first))
            result = "ok"
        except Refused as exc:
            result = "%d %s" % (exc.status, exc.reason)
            try:
                client.sendall(error_response(exc.status, exc.reason))
            except OSError:
                pass
        except (OSError, socket.timeout) as exc:
            result = "error %s" % (getattr(exc, "strerror", None) or exc)
        finally:
            for sock in (client, upstream):
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass
            if slot:
                self.slots.release()
            self.say("%s %s -> %s %d>/%d< %.1fs %s" % (
                tag, request, destination, counts[0], counts[1], time.monotonic() - start, result))

    def relay(self, client, upstream, sent_already):
        """Copy bytes both ways until both directions have ended or idle_timeout passes.

        Each socket is read while its peer's unsent backlog is small, and written while it
        has a backlog. When one side stops sending, the other side gets a half-close once its
        backlog is out, so the end of a request reaches the server and the end of the response
        reaches the client. Returns (bytes client->upstream, bytes upstream->client)."""
        up, down = sent_already, 0
        sel = selectors.DefaultSelector()
        state = {client: {"peer": upstream, "reading": True, "pending": b"", "registered": False},
                 upstream: {"peer": client, "reading": True, "pending": b"", "registered": False}}
        backlog_limit = 1 << 20

        def update(sock):
            st = state[sock]
            events = 0
            if st["reading"] and len(state[st["peer"]]["pending"]) < backlog_limit:
                events |= selectors.EVENT_READ
            if st["pending"]:
                events |= selectors.EVENT_WRITE
            if events and st["registered"]:
                sel.modify(sock, events)
            elif events:
                sel.register(sock, events)
                st["registered"] = True
            elif st["registered"]:
                sel.unregister(sock)
                st["registered"] = False

        def half_close(sock):
            try:
                sock.shutdown(socket.SHUT_WR)
            except OSError:
                pass

        for sock in state:
            sock.setblocking(False)
            update(sock)
        last = time.monotonic()
        try:
            while any(st["reading"] or st["pending"] for st in state.values()):
                timeout = self.idle_timeout - (time.monotonic() - last)
                if timeout <= 0:
                    break
                events = sel.select(timeout=timeout)
                if not events:
                    break   # idle for too long
                last = time.monotonic()
                for key, mask in events:
                    sock = key.fileobj
                    st = state[sock]
                    peer = st["peer"]
                    pst = state[peer]
                    if mask & selectors.EVENT_WRITE and st["pending"]:
                        try:
                            n = sock.send(st["pending"])
                        except BlockingIOError:
                            n = 0
                        except OSError:
                            return up, down
                        st["pending"] = st["pending"][n:]
                        if not st["pending"] and not pst["reading"]:
                            half_close(sock)   # the peer had ended; its last bytes are out now
                        update(sock)
                        update(peer)
                    if mask & selectors.EVENT_READ and st["reading"]:
                        try:
                            data = sock.recv(CHUNK)
                        except BlockingIOError:
                            continue
                        except OSError:
                            data = b""
                        if not data:
                            st["reading"] = False
                            if not pst["pending"]:
                                half_close(peer)
                            update(sock)
                            continue
                        if sock is client:
                            up += len(data)
                        else:
                            down += len(data)
                        if pst["pending"]:
                            pst["pending"] += data
                        else:
                            try:
                                n = peer.send(data)
                            except BlockingIOError:
                                n = 0
                            except OSError:
                                return up, down
                            if n < len(data):
                                pst["pending"] = data[n:]
                        update(peer)
                        update(sock)
        finally:
            sel.close()
        return up, down


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--listen", default="127.0.0.1", help="loopback address to listen on (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=3128, help="port (default 3128; 0 = any free port, printed)")
    parser.add_argument("--allow-ports", default=",".join(str(p) for p in DEFAULT_PORTS),
                        help="destination ports, comma-separated (default 443,80)")
    parser.add_argument("--allow-loopback", action="store_true", help="allow destinations on loopback (tests)")
    parser.add_argument("--allow-private", action="store_true",
                        help="allow private, link-local and other special destinations")
    parser.add_argument("--max-connections", type=int, default=64)
    parser.add_argument("--idle-timeout", type=float, default=300.0, help="seconds without data that end a tunnel")
    parser.add_argument("--connect-timeout", type=float, default=20.0)
    parser.add_argument("--log", help="append the connection lines to this file instead of stderr")
    args = parser.parse_args(argv)
    try:
        ports = [int(p) for p in args.allow_ports.split(",") if p]
    except ValueError:
        parser.error("--allow-ports takes numbers")
    log = open(args.log, "a") if args.log else sys.stderr
    try:
        proxy = Proxy(args.listen, args.port, Policy(ports, args.allow_loopback, args.allow_private),
                      args.max_connections, args.idle_timeout, args.connect_timeout, log)
    except (ValueError, OSError) as exc:
        print("connect-proxy: %s" % exc, file=sys.stderr)
        return 2
    print("connect-proxy: listening on %s:%d" % (proxy.host, proxy.port), file=sys.stderr, flush=True)
    try:
        proxy.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        proxy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())

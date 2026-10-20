"""Offline tests for usb-pipe (tools/m1n1-client/usb-pipe): the relay and the banner logic
against a socket pair and a pseudo-terminal, the static check of the macOS backend, and ssh
end to end over a pseudo-terminal, with sshd -i on its raw slave side as on the M5, a reverse
forward to a CONNECT proxy and an HTTPS fetch through it. No USB device is touched: the
IOUSBHost backend is compiled (macOS) but only its source is checked here.

    python3 -I tools/m1n1-client/test_usb_pipe.py
"""
import hashlib
import http.server
import importlib.util
import io
import os
import pty
import pwd
import re
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import tty
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "usb-pipe"
SOURCES = ["relay.h", "relay.c", "usb-pipe.h", "usb-pipe.c", "iousbhost.m", "build.sh"]

# Calls the macOS backend must never make (see bulk-log-reader-brief.md's read-only contract;
# this tool writes the OUT pipe of interface 1 and nothing else), and the names it must use.
FORBIDDEN = ["selectAlternateSetting", "sendDeviceRequest", "enqueueDeviceRequest", "sendControlRequest",
             "enqueueControlRequest", "abortDeviceRequests", "clearStall", "setIdleTimeout", "DeviceCapture",
             "DeviceSeize", "IOUSBHostDevice", "descriptorWithType", "stringWithIndex", "deviceDescriptor",
             "configurationDescriptorWithIndex", "configurationDescriptorWithConfigurationValue",
             "capabilityDescriptors", "IOUSBHostStream", "copyStream", "adjustPipeWithDescriptors", "resetWithError",
             "resetDevice", "powerState", "setIdlePolicy",
             "IOServiceOpen", "IOCreatePlugInInterfaceForService"]
REQUIRED = ["IOUSBHostObjectInitOptionsNone", "interfaceNumber:@USB_PIPE_INTERFACE", "bcdDevice:@USB_PIPE_BCD_DEVICE",
            "copyPipeWithAddress", "kIOMessageServiceIsTerminated", "[intf destroy]"]


def build(where):
    """Compile the tool into where/usb-pipe: with the IOUSBHost backend on macOS, without it elsewhere."""
    out = Path(where) / "usb-pipe"
    if sys.platform == "darwin":
        objs = []
        for name, flags in (("relay.c", ["-std=gnu11"]), ("usb-pipe.c", ["-std=gnu11"]), ("iousbhost.m", ["-fobjc-arc"])):
            obj = Path(where) / (name + ".o")
            subprocess.run(["clang", "-O2", "-Wall", "-Wextra", "-Werror"] + flags + ["-c", "-o", str(obj), str(SRC / name)],
                           check=True)
            objs.append(str(obj))
        subprocess.run(["clang", "-o", str(out)] + objs + ["-framework", "Foundation", "-framework", "IOKit",
                       "-framework", "IOUSBHost"], check=True)
    else:
        subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-pthread", "-o", str(out),
                        str(SRC / "usb-pipe.c"), str(SRC / "relay.c")], check=True)
    return out


class Tool:
    """usb-pipe with a socket pair as the device: self.device is the M5's end."""

    def __init__(self, binary, *args):
        self.device, far = socket.socketpair()
        far.set_inheritable(True)
        self.proc = subprocess.Popen([str(binary), "--fd", str(far.fileno())] + list(args), stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, pass_fds=[far.fileno()])
        far.close()
        self.device.settimeout(10)

    def device_recv(self, n, timeout=10):
        self.device.settimeout(timeout)
        try:
            return self.device.recv(n)
        except socket.timeout:
            return None

    def finish(self, timeout=10):
        """Close the tool's stdin (ssh's end) and collect what it wrote; (status, stdout, stderr)."""
        out, err = self.proc.communicate(timeout=timeout)
        return self.proc.returncode, out, err.decode(errors="replace")

    def close(self):
        self.device.close()
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()


def read_exactly(stream, n, timeout=20):
    data = b""
    deadline = time.monotonic() + timeout
    while len(data) < n and time.monotonic() < deadline:
        chunk = stream.read1(n - len(data)) if hasattr(stream, "read1") else stream.read(n - len(data))
        if not chunk:
            break
        data += chunk
    return data


class StaticTests(unittest.TestCase):
    def test_macos_backend_never_names_forbidden_calls(self):
        text = (SRC / "iousbhost.m").read_text()
        code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)   # the comments name what is forbidden
        code = "\n".join(line.split("//")[0] for line in code.splitlines())
        for name in FORBIDDEN:
            self.assertNotIn(name, code, name + " must not appear in the macOS backend")
        for name in REQUIRED:
            self.assertIn(name, text, name + " expected in the macOS backend")
        self.assertIn("kIOUSBEndpointDirectionOut", text)   # the OUT pipe is used, deliberately

    def test_identity_is_the_ram_root_ssh_interface(self):
        text = (SRC / "usb-pipe.h").read_text()
        for line in ("#define USB_PIPE_VENDOR_ID 0x1d6b", "#define USB_PIPE_PRODUCT_ID 0x0104",
                     "#define USB_PIPE_BCD_DEVICE 0x0039", "#define USB_PIPE_INTERFACE 1",
                     "#define USB_PIPE_INTERFACE_CLASS 0xff", "#define USB_PIPE_INTERFACES_IN_CONFIGURATION 2",
                     '#define USB_PIPE_PRODUCT_PREFIX "iLinux J716c control channel, port "'):
            self.assertIn(line, text)
        gadget = (HERE.parents[1] / "omarchy-arm64/ram-root/overlay/usr/local/lib/ilinux/usb-gadget.sh").read_text()
        self.assertIn("echo 0x0039 > \"$G/bcdDevice\"", gadget)
        self.assertIn('functions="gser.log gser.ssh"', gadget)   # interface 0 log, interface 1 SSH

    def test_build_script_uses_the_sdk_only(self):
        text = (SRC / "build.sh").read_text()
        for word in ("brew", "pip", "libusb", "npm", "sudo"):
            self.assertNotRegex(text, r"\b%s\b" % word)
        self.assertIn("-framework IOUSBHost", text)


class RelayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="usb-pipe-test-")
        cls.binary = build(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_banner_sync_drops_stale_bytes_and_holds_the_client(self):
        t = Tool(self.binary, "--banner-wait", "10", "--quiet-ms", "200")
        try:
            t.proc.stdin.write(b"SSH-2.0-client\r\n")
            t.proc.stdin.flush()
            self.assertIsNone(t.device_recv(100, timeout=0.7), "the client's bytes left before the banner")
            t.device.sendall(b"\x00\x11garbage of an old session\r\nSSH-2.0-OpenSSH_old\r\n")
            time.sleep(0.05)
            t.device.sendall(b"SSH-2.0-OpenSSH_10.6\r\n")
            self.assertEqual(read_exactly(t.proc.stdout, len(b"SSH-2.0-OpenSSH_10.6\r\n")), b"SSH-2.0-OpenSSH_10.6\r\n")
            self.assertEqual(t.device_recv(100), b"SSH-2.0-client\r\n")
            t.device.sendall(b"server packet")
            self.assertEqual(read_exactly(t.proc.stdout, 13), b"server packet")
            t.proc.stdin.write(b"client packet")
            t.proc.stdin.flush()
            self.assertEqual(t.device_recv(100), b"client packet")
            rc, out, err = t.finish()
            self.assertEqual(rc, 0, err)
            self.assertEqual(out, b"")
            self.assertIn("banner after", err)
            self.assertIn("stale bytes dropped first", err)
            self.assertIn("ssh closed the session", err)
            self.assertEqual(t.device_recv(100), b"")   # the tool's end closed with it
        finally:
            t.close()

    def test_partial_banner_line_waits_for_its_end(self):
        t = Tool(self.binary, "--banner-wait", "10", "--quiet-ms", "200")
        try:
            t.device.sendall(b"SSH-2.0-Open")
            time.sleep(0.5)   # longer than quiet-ms: an incomplete line must not end the wait
            t.device.sendall(b"SSH_10.6\r\n")
            self.assertEqual(read_exactly(t.proc.stdout, 22), b"SSH-2.0-OpenSSH_10.6\r\n")
            self.assertEqual(t.finish()[0], 0)
        finally:
            t.close()

    def test_no_banner_exits_5(self):
        t = Tool(self.binary, "--banner-wait", "1")
        try:
            t.device.sendall(b"only noise, no banner\r\n")
            rc, out, err = t.finish()
            self.assertEqual(rc, 5, err)
            self.assertEqual(out, b"")
            self.assertIn("no SSH banner from the device in 1000 ms", err)
        finally:
            t.close()

    def test_banner_wait_zero_relays_at_once(self):
        t = Tool(self.binary, "--banner-wait", "0")
        try:
            t.proc.stdin.write(b"first")
            t.proc.stdin.flush()
            self.assertEqual(t.device_recv(100), b"first")
            t.device.sendall(b"second")
            self.assertEqual(read_exactly(t.proc.stdout, 6), b"second")
            self.assertEqual(t.finish()[0], 0)
        finally:
            t.close()

    def test_device_end_closes_the_session(self):
        t = Tool(self.binary, "--banner-wait", "0")
        try:
            t.device.sendall(b"bye")
            t.device.shutdown(socket.SHUT_WR)
            # finish() closes ssh's stdin too. Let device EOF win first so
            # the assertion tests device shutdown rather than two racing ends.
            self.assertEqual(t.proc.wait(timeout=5), 0)
            rc, out, err = t.finish()
            self.assertEqual(rc, 0, err)
            self.assertEqual(out, b"bye")
            self.assertIn("the device ended", err)
        finally:
            t.close()

    def test_large_transfers_both_ways(self):
        t = Tool(self.binary, "--banner-wait", "0")
        try:
            sizes = [1, 511, 512, 513, 1024, 16384, 16385, 65536, 1 << 20]
            down = b"".join(os.urandom(s) for s in sizes)   # device -> ssh
            up = b"".join(os.urandom(s) for s in reversed(sizes))   # ssh -> device
            got_down, got_up = [], []

            def read_stdout():
                got_down.append(read_exactly(t.proc.stdout, len(down), timeout=60))

            def read_device():
                data = b""
                t.device.settimeout(60)
                while len(data) < len(up):
                    chunk = t.device.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                got_up.append(data)

            threads = [threading.Thread(target=read_stdout), threading.Thread(target=read_device)]
            for th in threads:
                th.start()
            writer = threading.Thread(target=lambda: (t.proc.stdin.write(up), t.proc.stdin.flush()))
            writer.start()
            for i in range(0, len(down), 4096):
                t.device.sendall(down[i:i + 4096])
            writer.join(60)
            for th in threads:
                th.join(60)
            self.assertEqual(hashlib.sha256(got_down[0]).hexdigest(), hashlib.sha256(down).hexdigest())
            self.assertEqual(hashlib.sha256(got_up[0]).hexdigest(), hashlib.sha256(up).hexdigest())
            rc, _, err = t.finish()
            self.assertEqual(rc, 0, err)
            self.assertIn("%d bytes to the device, %d from it" % (len(up), len(down)), err)
        finally:
            t.close()

    def test_ssh_exit_does_not_lose_the_last_packets(self):
        """ssh writes its last packets to the ProxyCommand, closes the socket and sends SIGHUP. The tool must
        still deliver everything it was given, even while the device is slow to take it."""
        import signal
        t = Tool(self.binary, "--banner-wait", "0")
        try:
            payload = os.urandom(6 << 20)
            got = []

            def slow_device():
                data = b""
                t.device.settimeout(60)
                while True:
                    chunk = t.device.recv(8192)
                    if not chunk:
                        break
                    data += chunk
                    time.sleep(0.0005)   # the M5 takes its time, so the tool still holds data when SIGHUP comes
                got.append(data)

            reader = threading.Thread(target=slow_device)
            reader.start()
            t.proc.stdin.write(payload)
            t.proc.stdin.close()                       # ssh closes its end ...
            t.proc.send_signal(signal.SIGHUP)          # ... and hangs up the ProxyCommand
            rc = t.proc.wait(timeout=60)
            reader.join(60)
            self.assertEqual(rc, 0, t.proc.stderr.read().decode(errors="replace"))
            self.assertEqual(len(got[0]), len(payload))
            self.assertEqual(hashlib.sha256(got[0]).hexdigest(), hashlib.sha256(payload).hexdigest())
        finally:
            t.close()

    def test_ssh_gone_while_the_device_still_talks(self):
        """Once ssh has closed its side, writes to it fail (SIGPIPE is ignored); the tool still delivers what
        ssh wrote before it left, and ends normally."""
        t = Tool(self.binary, "--banner-wait", "0")
        try:
            got = []

            def device_side():   # the M5: takes everything the tool sends until it closes
                data = b""
                t.device.settimeout(30)
                while True:
                    chunk = t.device.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                got.append(data)

            reader = threading.Thread(target=device_side)
            reader.start()
            t.proc.stdout.close()                       # ssh's read side is gone
            t.device.sendall(b"server packet that nobody reads" * 100)   # the tool writes it to ssh and fails
            time.sleep(0.2)
            tail = os.urandom(300000)
            t.proc.stdin.write(tail)                    # what ssh wrote before it left
            t.proc.stdin.close()
            rc = t.proc.wait(timeout=30)
            reader.join(30)
            self.assertEqual(rc, 0, t.proc.stderr.read().decode(errors="replace"))
            self.assertEqual(hashlib.sha256(got[0]).hexdigest(), hashlib.sha256(tail).hexdigest())
        finally:
            t.close()

    def test_tty_backend_makes_the_port_raw(self):
        master, slave = pty.openpty()
        path = os.ttyname(slave)
        proc = subprocess.Popen([str(self.binary), "--tty", path, "--banner-wait", "0"], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            time.sleep(0.3)
            import termios
            attrs = termios.tcgetattr(slave)
            self.assertFalse(attrs[3] & termios.ECHO)
            self.assertFalse(attrs[3] & termios.ICANON)
            self.assertFalse(attrs[1] & termios.OPOST)
            self.assertFalse(attrs[0] & termios.ICRNL)
            proc.stdin.write(b"to the device\r\n")
            proc.stdin.flush()
            self.assertEqual(os.read(master, 100), b"to the device\r\n")   # no CR/LF translation, no echo
            os.write(master, b"from the device\r\n")
            self.assertEqual(read_exactly(proc.stdout, 17), b"from the device\r\n")
            out, err = proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 0, err)
        finally:
            if proc.poll() is None:
                proc.kill()
            os.close(master)
            os.close(slave)

    def test_usage_errors(self):
        for args in (["--port", "4"], ["--wait"], ["--fd", "3", "--tty", "/dev/null"], ["--nonsense"]):
            proc = subprocess.run([str(self.binary)] + args, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 6, args)
        proc = subprocess.run([str(self.binary), "--version"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(proc.stdout.startswith("usb-pipe 1"))


def make_cert(where):
    """A self-signed certificate for 127.0.0.1 with openssl (OpenSSL or LibreSSL), or None."""
    openssl = shutil.which("openssl")
    if not openssl:
        return None
    config = Path(where) / "cert.cnf"
    config.write_text("[req]\ndistinguished_name = dn\nx509_extensions = v3\nprompt = no\n"
                      "[dn]\nCN = localhost\n[v3]\nsubjectAltName = IP:127.0.0.1\n")
    cert, key = Path(where) / "cert.pem", Path(where) / "key.pem"
    proc = subprocess.run([openssl, "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1",
                           "-nodes", "-keyout", str(key), "-out", str(cert), "-days", "2", "-config", str(config)],
                          capture_output=True, text=True)
    if proc.returncode:
        return None
    return cert, key


class HelloHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"HELLO-THROUGH-THE-PROXY\n"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


@unittest.skipUnless(shutil.which("ssh") and shutil.which("ssh-keygen") and os.path.exists("/usr/sbin/sshd"),
                     "needs ssh, ssh-keygen and /usr/sbin/sshd")
class SshOverPtyTests(unittest.TestCase):
    """The M5 layout on one machine: sshd -i on the raw slave of a pseudo-terminal, usb-pipe on
    the same terminal as ssh's ProxyCommand, a reverse forward to the CONNECT proxy, and curl
    on the "M5" side fetching an HTTPS page through it."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="usb-pipe-ssh-")
        cls.binary = build(cls.tmp)
        d = Path(cls.tmp)
        for name in ("host_key", "client_key"):
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(d / name)], check=True)
        (d / "authorized_keys").write_bytes((d / "client_key.pub").read_bytes())
        (d / "sshd_config").write_text(
            "HostKey %s/host_key\nAuthorizedKeysFile %s/authorized_keys\nStrictModes no\nUsePAM no\n"
            "PasswordAuthentication no\nKbdInteractiveAuthentication no\nPidFile none\nLogLevel VERBOSE\n"
            "AllowTcpForwarding yes\nLoginGraceTime 45\nClientAliveInterval 15\nClientAliveCountMax 3\n"
            "SetEnv HTTPS_PROXY=http://127.0.0.1:%%RPORT%% NO_PROXY=\n" % (d, d))
        spec = importlib.util.spec_from_file_location("connect_proxy", HERE / "connect-proxy.py")
        cls.connect_proxy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.connect_proxy)
        cls.cert = make_cert(cls.tmp)
        cls.https = None
        if cls.cert:
            cls.https = http.server.ThreadingHTTPServer(("127.0.0.1", 0), HelloHandler)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(str(cls.cert[0]), str(cls.cert[1]))
            cls.https.socket = context.wrap_socket(cls.https.socket, server_side=True)
            threading.Thread(target=cls.https.serve_forever, daemon=True).start()
        ports = (cls.https.server_address[1],) if cls.https else (443,)
        cls.proxy = cls.connect_proxy.Proxy("127.0.0.1", 0, cls.connect_proxy.Policy(ports, allow_loopback=True),
                                            log=io.StringIO())
        threading.Thread(target=cls.proxy.serve_forever, daemon=True).start()
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        cls.rport = probe.getsockname()[1]
        probe.close()
        (d / "sshd_config").write_text((d / "sshd_config").read_text().replace("%RPORT%", str(cls.rport)))
        (d / "ssh_config").write_text(
            "Host m5test\n  HostName m5test\n  User %s\n  IdentityFile %s/client_key\n  IdentitiesOnly yes\n"
            "  UserKnownHostsFile %s/known_hosts\n  StrictHostKeyChecking accept-new\n  BatchMode yes\n"
            "  ConnectTimeout 30\n  RemoteForward 127.0.0.1:%d 127.0.0.1:%d\n  ExitOnForwardFailure yes\n"
            "  ProxyCommand %s --tty %%%%TTY%%%% --banner-wait 15 --log %s/usb-pipe.log\n"
            % (pwd.getpwuid(os.getuid()).pw_name, d, d, cls.rport, cls.proxy.port, cls.binary, d))

    @classmethod
    def tearDownClass(cls):
        cls.proxy.shutdown()
        if cls.https:
            cls.https.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def start_sshd(self, stale=b""):
        """sshd -i on the raw slave of a new pseudo-terminal; returns (process, slave path, master)."""
        master, slave = pty.openpty()
        tty.setraw(slave)
        if stale:
            os.write(master, stale)   # what an earlier session left in the pipe
        log = open(Path(self.tmp) / "sshd.log", "ab")
        proc = subprocess.Popen(["/usr/sbin/sshd", "-i", "-e", "-f", str(Path(self.tmp) / "sshd_config")],
                                stdin=master, stdout=master, stderr=log, close_fds=True)
        log.close()
        return proc, os.ttyname(slave), master, slave

    def ssh(self, path, command, timeout=60):
        """Run ssh through the tool; returns (exit status or None on timeout, stdout, stderr)."""
        config = (Path(self.tmp) / "ssh_config").read_text().replace("%%TTY%%", path)
        cfg = Path(self.tmp) / "ssh_config.run"
        cfg.write_text(config)
        try:
            r = subprocess.run(["ssh", "-v", "-F", str(cfg), "m5test", command], capture_output=True, text=True,
                               timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            return None, (exc.stdout or b"").decode(errors="replace"), (exc.stderr or b"").decode(errors="replace")
        return r.returncode, r.stdout, r.stderr

    def session(self, stale, command, expect_output):
        """One sshd -i on a fresh terminal, one ssh session through the tool. On macOS an
        unprivileged sshd completes the key authentication and then stalls in its audit setup
        (setaudit_addr needs privileges), so there the test ends at the authenticated handshake;
        the VM (job 046) runs the whole session as root, with the forward and the HTTPS fetch."""
        sshd, path, master, slave = self.start_sshd(stale=stale)
        try:
            status, out, err = self.ssh(path, command, timeout=40 if sys.platform == "darwin" else 90)
            self.assertIn("Authenticated to m5test (via proxy)", err, err[-2000:])
            if status is None and sys.platform == "darwin":
                self.assertIn("Entering interactive session", err)
                return "handshake only (macOS: unprivileged sshd stalls after authentication)"
            self.assertEqual(status, 0, err[-2000:])
            for text in expect_output:
                self.assertIn(text, out)
            sshd.wait(timeout=20)   # one session per sshd -i, as on the M5
            return "session"
        finally:
            if sshd.poll() is None:
                sshd.kill()
                sshd.wait()
            os.close(master)
            os.close(slave)

    def log_until(self, text, seconds=10):
        """The tool is ssh's child and writes its last line after ssh has returned: wait for it."""
        path = Path(self.tmp) / "usb-pipe.log"
        deadline = time.monotonic() + seconds
        while True:
            log = path.read_text() if path.exists() else ""
            if text in log or time.monotonic() > deadline:
                return log
            time.sleep(0.1)

    def test_login_forward_and_https_fetch(self):
        if self.https:
            command = ('echo SSH-OK "$HTTPS_PROXY"; curl -sS --cacert %s https://127.0.0.1:%d/hello.txt'
                       % (self.cert[0], self.https.server_address[1]))
            expect = ["SSH-OK http://127.0.0.1:%d" % self.rport, "HELLO-THROUGH-THE-PROXY"]
        else:
            command, expect = 'echo SSH-OK "$HTTPS_PROXY"', ["SSH-OK http://127.0.0.1:%d" % self.rport]
        stale = b"\x17\x03stale tail of an earlier session\r\nSSH-2.0-Stale\r\n"
        first = self.session(stale, command, expect)
        log = self.log_until("ssh closed the session")
        self.assertIn("banner after", log)
        self.assertRegex(log, r"\([1-9]\d* stale bytes dropped first\)")
        # The next session: a new sshd on a new terminal, as the M5's unit restarts it.
        second = self.session(b"", "echo SECOND-SESSION-OK", ["SECOND-SESSION-OK"])
        print("[%s; %s]" % (first, second), end=" ", file=sys.stderr)

    def test_wrong_key_is_refused(self):
        sshd, path, master, slave = self.start_sshd()
        try:
            d = Path(self.tmp)
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(d / "wrong_key")], check=True)
            config = (d / "ssh_config").read_text().replace("%%TTY%%", path).replace("client_key", "wrong_key")
            (d / "ssh_config.wrong").write_text(config)
            result = subprocess.run(["ssh", "-F", str(d / "ssh_config.wrong"), "m5test", "echo SHOULD-NOT-RUN"],
                                    capture_output=True, text=True, timeout=120)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("SHOULD-NOT-RUN", result.stdout)
            self.assertIn("Permission denied", result.stderr)
        finally:
            if sshd.poll() is None:
                sshd.kill()
            os.close(master)
            os.close(slave)


if __name__ == "__main__":
    unittest.main()

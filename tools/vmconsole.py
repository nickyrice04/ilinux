#!/usr/bin/env python3
"""Run a shell command on a VM's console socket (QEMU chardev, root autologin)
and print its output.  Usage: vmconsole.py SOCKET 'command' [timeout_s]"""
import re, socket, sys, time
path, cmd = sys.argv[1], sys.argv[2]
timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 30
marker = "__VMDONE_%d__" % int(time.time() * 1000)
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(path); s.settimeout(0.5)
s.sendall(("\n" + cmd + "; echo " + marker + "\n").encode())
buf, end = b"", time.time() + timeout
while time.time() < end and buf.count(marker.encode()) < 2:
    try:
        d = s.recv(65536)
        if not d: break
        buf += d
    except socket.timeout:
        pass
text = buf.decode("utf-8", "replace")
text = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x1b\\]*\x1b?\\?|\]3008;[^\\]*\\", "", text)
out = text.split(marker)
print(out[1] if len(out) > 2 else text)

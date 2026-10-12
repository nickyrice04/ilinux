#!/usr/bin/env python3
"""Run a shell command on a VM's console socket (QEMU chardev, root autologin)
and print its output.  Usage: vmconsole.py SOCKET 'command' [timeout_s]

Completion is detected by a marker the shell prints after the command.  The
command line itself carries the marker split by an empty quote pair
(__VM''DONE_n__), so the tty echo of a long, readline-redrawn command line
can never be mistaken for completion; only the real `echo` output matches."""
import re, socket, sys, time
path, cmd = sys.argv[1], sys.argv[2]
timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 30
tag = "DONE_%d__" % int(time.time() * 1000)
marker = "__VM" + tag
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(path); s.settimeout(0.5)
s.sendall(("\n" + cmd + "; echo __VM''" + tag + "\n").encode())
buf, end = b"", time.time() + timeout
while time.time() < end and marker.encode() not in buf:
    try:
        d = s.recv(65536)
        if not d: break
        buf += d
    except socket.timeout:
        pass
text = buf.decode("utf-8", "replace")
text = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x1b\x07]*(\x1b\\|\x07)?|\]3008;[^\\]*\\", "", text)
text = text.replace("\r", "")
if marker in text:
    head = text[:text.index(marker)]
    # Drop the echoed command line: everything up to the newline after the
    # quoted marker (falls back to the first line if the echo was mangled).
    echo = head.rfind("''" + tag)
    start = head.find("\n", echo) + 1 if echo >= 0 else head.find("\n") + 1
    print(head[start:], end="")
else:
    print(text)
    sys.exit(124)

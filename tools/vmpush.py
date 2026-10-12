#!/usr/bin/env python3
"""Copy a small host file into a VM over its console socket (root shell),
base64 in chunks below the tty's 4095-byte line limit, verified by sha256.
Usage: vmpush.py SOCKET LOCAL_FILE GUEST_PATH [MODE]"""
import base64, hashlib, os, subprocess, sys
sock, local, dest = sys.argv[1], sys.argv[2], sys.argv[3]
mode = sys.argv[4] if len(sys.argv) > 4 else "0644"
data = open(local, "rb").read()
b64 = base64.b64encode(data).decode()
tmp = dest + ".vmpush"
console = [sys.executable, "-I", os.path.join(os.path.dirname(__file__), "vmconsole.py"), sock]
def run(cmd):
    return subprocess.run(console + [cmd, "30"], capture_output=True, text=True).stdout
run(f": > '{tmp}'")
for i in range(0, len(b64), 3000):
    run(f"printf %s '{b64[i:i + 3000]}' >> '{tmp}'")
want = hashlib.sha256(data).hexdigest()
out = run(f"base64 -d '{tmp}' > '{dest}' && rm -f '{tmp}' && chmod {mode} '{dest}' && sha256sum '{dest}'")
ok = want in out
print(("ok " if ok else "MISMATCH ") + dest)
sys.exit(0 if ok else 1)

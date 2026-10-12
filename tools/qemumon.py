import socket, sys, time
"""Send HMP commands to a QEMU monitor socket: qemumon.py SOCKET CMD [CMD...]"""
s = socket.socket(socket.AF_UNIX); s.connect(sys.argv[1]); s.settimeout(3)
def rd():
    buf=b''
    try:
        while True:
            d=s.recv(65536)
            if not d: break
            buf+=d
            if buf.endswith(b'(qemu) '): break
    except Exception: pass
    return buf.decode(errors='replace')
rd()
for cmd in sys.argv[2:]:
    s.sendall(cmd.encode()+b'\n'); time.sleep(0.3); print(rd())

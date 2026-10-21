#!/usr/bin/env python3
"""VM-only logger overhead control: no shell/layers, fixed fullscreen client."""
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import time

s=importlib.util.spec_from_file_location('d','/run/t31/collect30.py')
d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
d.HYPR_SHA=Path('/run/t31/hypr.sha256').read_text().strip()
for _ in range(60):
    try:pid,ipc,env=d.find_desktop();break
    except ValueError:time.sleep(.5)
else:raise RuntimeError('no compositor')
def control(cmd):
    with socket.socket(socket.AF_UNIX) as c:
        c.settimeout(10);c.connect(str(ipc));c.sendall(cmd.encode());data=bytearray()
        while block:=c.recv(65536):data.extend(block)
        if data.strip()!=b'ok':raise RuntimeError('control failed')
control('output create headless OBSERVER31')
control('eval hl.monitor({output="OBSERVER31",mode="3456x2160@60",position="0x0",scale=1})')
control('eval hl.monitor({output="Virtual-1",disabled=true})')
control('eval hl.config({animations={enabled=false}})')
time.sleep(4)
layers=d.request(ipc,'j/layers')
if any(v for m in layers.values() for v in m['levels'].values()):raise RuntimeError('control has unexpected layers')
for rep in range(3):
    p=subprocess.run(['setpriv','--reuid=1000','--regid=1000','--init-groups','env',*[k+'='+v for k,v in env.items()],
                      'taskset','-c','0','/run/t31/frameprobe'],capture_output=True,text=True,timeout=30,check=True)
    rows=[json.loads(s) for s in p.stdout.splitlines()];d.validate_frames(rows)
    print(json.dumps({'rep':rep,'rows':rows}),flush=True)

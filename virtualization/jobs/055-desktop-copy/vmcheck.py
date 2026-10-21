#!/usr/bin/env python3
"""VM-only integration; never included in a native bundle."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import re
import subprocess
import time

spec = importlib.util.spec_from_file_location('d30', '/run/d31/collect30.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
d.HYPR_SHA = Path('/run/d31/new.sha256').read_text().strip()

def raw(ipc, command):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(20)
        s.connect(str(ipc))
        s.sendall(command.encode())
        out = bytearray()
        while chunk := s.recv(65536):
            out.extend(chunk)
        print('IPC', command, out.decode(), flush=True)
        return out.decode()

for _ in range(60):
    try:
        pid, ipc, env = d.find_desktop()
        break
    except ValueError:
        time.sleep(1)
else:
    raise RuntimeError('no desktop')
print('initial', d.request(ipc, 'j/monitors'), flush=True)
assert raw(ipc, 'output create headless COPY31').strip() == 'ok'
assert raw(ipc, 'eval hl.monitor({output="COPY31",mode="3456x2160@60",position="0x0",scale=1})').strip() == 'ok'
assert raw(ipc, 'eval hl.monitor({output="Virtual-1",disabled=true})').strip() == 'ok'
time.sleep(3)
monitors = d.request(ipc, 'j/monitors')
print('headless', monitors, flush=True)
assert len(monitors) == 1 and monitors[0]['name'] == 'COPY31'
assert (monitors[0]['width'], monitors[0]['height']) == (3456, 2160)
assert raw(ipc, 'eval hl.config({animations={enabled=false}})').strip() == 'ok'
assert raw(ipc, 'eval hl.config({debug={disable_logs=false}})').strip() == 'ok'
# Let startup notifications expire before the fixed-order crossover.
time.sleep(25)
for index, mode in enumerate((0, 1, 1, 0)):
    assert raw(ipc, 'eval hl.config({debug={ilinux_copy31='+str(mode)+'}})').strip() == 'ok'
    assert d.request(ipc, 'j/getoption debug:ilinux_copy31')['int'] == mode
    d.phase('copy31-mode%d-run%d' % (mode, index), pid, ipc, env, Path('/run/d31'))
    time.sleep(1)
assert raw(ipc, 'eval hl.config({debug={ilinux_copy31=0}})').strip() == 'ok'
print('CROSSOVER-COMPLETE', flush=True)
# Negative controls use the unchanged draw branch. Never part of native scope.
for label, change in [
    ('fp16', 'hl.config({render={use_fp16=1}})'),
    ('resized', 'hl.config({render={use_fp16=2}});hl.monitor({output="COPY31",mode="1728x1080@60",position="0x0",scale=1})'),
    ('rotated', 'hl.monitor({output="COPY31",mode="1728x1080@60",position="0x0",scale=1,transform=1})'),
]:
    assert raw(ipc, 'eval '+change).strip() == 'ok'
    time.sleep(2)
    assert raw(ipc, 'eval hl.config({debug={ilinux_copy31=1}})').strip() == 'ok'
    d.phase('fallback-'+label, pid, ipc, env, Path('/run/d31'))
    assert raw(ipc, 'eval hl.config({debug={ilinux_copy31=0}})').strip() == 'ok'
print('VM-INTEGRATION-PASS', flush=True)
trace = [{k:int(v) for k,v in re.findall(r'([a-z_]+)=(-?[0-9]+)', line)}
         for line in Path('/run/user/1000/ilinux-copy31.log').read_text().splitlines()]
assert sum(r.get('parity') == 1 for r in trace) == 3
assert not any(r.get('parity') == 0 or r.get('gl_error',0) or r.get('runtime_error',0) for r in trace)
fallback = [r for r in trace if r.get('enabled') == 1 and r.get('eligible') == 0]
assert len(fallback) == 3 and all(r['copies'] > 0 for r in fallback)
assert len({r['copies'] for r in fallback}) == 1
print('PATH-PARITY-AND-FALLBACK-PASS', flush=True)
# Leave the opt-in bit set so the real independent reset must clear it. The
# rotated VM output remains ineligible, so this does not add a timing sample.
assert raw(ipc, 'eval hl.config({debug={ilinux_copy31=1}})').strip() == 'ok'

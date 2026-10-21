#!/usr/bin/env python3
"""Real Omarchy menu/foot + frame control, VM only; timestamps are NOT photons."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

spec = importlib.util.spec_from_file_location('d30', '/run/t31/collect30.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
d.HYPR_SHA = Path('/run/t31/hypr.sha256').read_text().strip()


def emit(event, **kw):
    print(json.dumps(dict(event=event, ns=time.monotonic_ns(), **kw)), flush=True)


def ipc(command):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(15)
        s.connect(str(sock))
        s.sendall(command.encode())
        data = bytearray()
        while block := s.recv(65536):
            data.extend(block)
            if len(data) > 1024*1024:
                raise RuntimeError('oversized IPC')
    return data.decode()


def control(command):
    result = ipc(command).strip()
    if result != 'ok':
        raise RuntimeError(command + ': ' + result)


def launch(args, log=None):
    return subprocess.Popen(['setpriv', '--reuid=1000', '--regid=1000', '--init-groups',
                             'env', *[k+'='+v for k,v in env.items()], 'taskset', '-c', '0', *args],
                            stdout=log or subprocess.PIPE, stderr=log or subprocess.PIPE, text=True)


for _ in range(60):
    try:
        pid, sock, env = d.find_desktop()
        break
    except ValueError:
        time.sleep(1)
else:
    raise RuntimeError('desktop absent')
env.update(PATH='/usr/local/bin:/usr/bin:/usr/share/omarchy/bin', OMARCHY_PATH='/usr/share/omarchy',
           XDG_SESSION_TYPE='wayland', LIBGL_ALWAYS_SOFTWARE='1', LP_NUM_THREADS='0')
for s in Path('/proc',str(pid),'environ').read_bytes().split(b'\0'):
    if s.startswith(b'DBUS_SESSION_BUS_ADDRESS='):
        env['DBUS_SESSION_BUS_ADDRESS'] = s.split(b'=',1)[1].decode()
control('output create headless TIMELINE31')
control('eval hl.monitor({output="TIMELINE31",mode="3456x2160@60",position="0x0",scale=1})')
control('eval hl.monitor({output="Virtual-1",disabled=true})')
# Manual chroot sessions lack the image's systemd user autostart. Explicitly
# launch the SAME installed shell; refuse an empty compositor-only workload.
env.update(QS_DISABLE_FILE_WATCHER='1', QS_NO_RELOAD_POPUP='1')
shell_log=open('/run/t31/shell.log','w')
shell=launch(['quickshell','-n','-p','/usr/share/omarchy/shell'],shell_log)
time.sleep(25)
if shell.poll() is not None:
    raise RuntimeError('installed shell exited; inspect shell.log')
ping=launch(['omarchy-shell','shell','ping'])
_,err=ping.communicate(timeout=15)
if ping.returncode:
    raise RuntimeError('installed shell unavailable: '+err[:200])
emit('ready', compositor_pid=pid, monitors=json.loads(ipc('j/monitors')),
     layers=json.loads(ipc('j/layers')))
if os.environ.get('ILINUX_VM_PROFILE')=='blur':
    original=json.loads(ipc('j/getoption decoration:blur:enabled'))['bool']
    if original not in (0,1):raise RuntimeError('unknown blur state')
    try:
        for rep, enabled in enumerate((original,0,0,original)):
            control('eval hl.config({decoration={blur={enabled='+('true' if enabled else 'false')+'}}})')
            if json.loads(ipc('j/getoption decoration:blur:enabled'))['bool']!=enabled:raise RuntimeError('blur control failed')
            time.sleep(2)
            p=launch(['/run/t31/frameprobe']);out,err=p.communicate(timeout=30)
            if p.returncode:raise RuntimeError('blur frame control failed')
            rows=[json.loads(s) for s in out.splitlines()];d.validate_frames(rows)
            emit('blur_frames',rep=rep,enabled=enabled,original=original,rows=rows)
    finally:
        control('eval hl.config({decoration={blur={enabled='+('true' if original else 'false')+'}}})')
    emit('done');sys.exit(0)
for rep in range(3):
    emit('menu_request', rep=rep)
    p = launch(['omarchy-menu','summon','root'])
    _, err = p.communicate(timeout=15)
    emit('menu_command_return', rep=rep, rc=p.returncode)
    if p.returncode:
        raise RuntimeError('menu command failed: '+err[:200])
    time.sleep(3)
    emit('menu_layers', rep=rep, layers=json.loads(ipc('j/layers')))
    p = launch(['omarchy-menu','close'])
    p.communicate(timeout=15)
    if p.returncode:
        raise RuntimeError('close failed')
    time.sleep(1)
    emit('terminal_request', rep=rep)
    p = launch(['foot','--app-id=ilinux-timeline31','sh','-c','printf "iLinux fixed text\\n"; sleep 3'])
    emit('terminal_spawn', rep=rep, client_pid=p.pid)
    _, err = p.communicate(timeout=15)
    emit('terminal_exit', rep=rep, rc=p.returncode)
    if p.returncode:
        raise RuntimeError('foot failed: '+err[:200])
    time.sleep(1)
for label, size in [('native_pixels', '3456x2160'), ('quarter_pixels', '1728x1080')]:
    if label == 'quarter_pixels':
        control('eval hl.monitor({output="TIMELINE31",mode="'+size+'@60",position="0x0",scale=1})')
        time.sleep(2)
    emit('frames_start', label=label)
    p = launch(['/run/t31/frameprobe'])
    out, err = p.communicate(timeout=30)
    if p.returncode:
        raise RuntimeError('frameprobe failed: '+err[:200])
    rows = [json.loads(s) for s in out.splitlines()]
    d.validate_frames(rows)
    emit('frames_end', label=label, rows=rows)
emit('done')

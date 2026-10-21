#!/usr/bin/env python3
"""One native RAM-only compositor crossover; no CPU, boot or storage writes."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

basepath = HERE/'baseline.py'
if not basepath.is_file():
    basepath = HERE.parent/'desktop30/collect.py'
base = load('desktop31_baseline', basepath)
emit = base.emit

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def find_desktop(expected):
    # Inspect the actual running executable across the current session.
    pids = []
    for p in Path('/proc').glob('[0-9]*'):
        try:
            if (p/'comm').read_text().strip() == 'Hyprland' and (p/'status').stat().st_uid == 1000:
                if digest(p/'exe') != expected:
                    raise ValueError('running compositor digest differs')
                pids.append(int(p.name))
        except (OSError, RuntimeError):
            continue
    if len(pids) != 1:
        raise ValueError('need one verified compositor')
    runtime = Path('/run/user/1000')
    sockets = [p for p in (runtime/'hypr').glob('*/.socket.sock') if p.is_socket()]
    wayland = [p for p in runtime.glob('wayland-*') if p.is_socket()]
    if len(sockets) != 1 or len(wayland) != 1:
        raise ValueError('ambiguous live desktop sockets')
    env = dict(HOME='/home/omarchy', USER='omarchy', LOGNAME='omarchy', PATH='/usr/bin',
               XDG_RUNTIME_DIR=str(runtime), WAYLAND_DISPLAY=wayland[0].name,
               HYPRLAND_INSTANCE_SIGNATURE=sockets[0].parent.name)
    return pids[0], sockets[0], env

def wait_desktop(expected):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            return find_desktop(expected)
        except (OSError, ValueError):
            time.sleep(.5)
    raise ValueError('verified desktop did not return within 30 seconds')

def set_mode(ipc, mode):
    if mode not in (0, 1):
        raise ValueError('invalid copy mode')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(3)
        sock.connect(str(ipc))
        sock.sendall(('eval hl.config({debug={ilinux_copy31=%d}})' % mode).encode())
        data = bytearray()
        while chunk := sock.recv(4096):
            data.extend(chunk)
            if len(data) > 4096:
                raise ValueError('oversized mode response')
    if data.decode().strip() != 'ok' or base.request(ipc, 'j/getoption debug:ilinux_copy31').get('int') != mode:
        raise ValueError('mode switch refused')
    emit('mode', enabled=mode)

def read_options(ipc):
    return {n: base.request(ipc, 'j/getoption '+n) for n in
            ('render:cm_enabled', 'debug:damage_tracking', 'input:repeat_delay', 'animations:enabled')}

def path_evidence(pid):
    # The compositor creates this new, mode600 numeric-only file in the user's
    # RAM runtime directory. No journal attribution or persistent log setting.
    path = Path('/run/user/1000/ilinux-copy31.log')
    if not path.is_file() or path.is_symlink() or path.stat().st_uid != 1000 or path.stat().st_mode & 0o077 or path.stat().st_size > 65536:
        raise ValueError('unexpected experiment log')
    rows = []
    for line in path.read_text().splitlines():
        if line.startswith('ILINUX_COPY31 '):
            if not re.fullmatch(r'ILINUX_COPY31 (?:[a-z_]+=-?[0-9]+ ?)+', line):
                raise ValueError('unexpected experiment log')
            rows.append({k:int(v) for k,v in re.findall(r'([a-z_]+)=(-?[0-9]+)', line)})
        else:
            raise ValueError('unexpected experiment log line')
    if len(rows) > 100:
        raise ValueError('too many experiment records')
    emit('copy_path', rows=rows)
    return rows

def require_verified(rows):
    if any(r.get('parity') == 0 or r.get('gl_error', 0) or r.get('runtime_error', 0) for r in rows):
        raise ValueError('copy parity or GL error; original path restored')
    if not any(r.get('parity') == 1 for r in rows) or not any(r.get('copies', 0) > 0 for r in rows):
        raise ValueError('candidate path not proven active; no improvement claim')

def main():
    import observe28
    import measurement
    def interrupted(*_):
        raise TimeoutError('copy31 time limit or termination')
    signal.signal(signal.SIGALRM, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    signal.alarm(280)
    changed = False
    complete = False
    try:
        mounts = [s.split() for s in Path('/proc/mounts').read_text().splitlines()]
        if os.geteuid() != 0 or not any(s[1:3] == ['/run','tmpfs'] for s in mounts):
            raise ValueError('requires root and RAM /run')
        identity = observe28.identity()
        if identity['mpidr'] != '0x40000' or identity['kernel'] != '7.1.9-g863199d8b4a3-dirty':
            raise ValueError('unexpected native core or kernel')
        observe28.verify_assets()
        if measurement.snapshot()['policies'] or any(Path('/sys/module', n).exists() for n in ('apple_soc_cpufreq', 'ilinux_mem29')):
            raise ValueError('unexpected CPU policy or prior diagnostic module')
        assets = json.loads((HERE/'assets.json').read_text())
        for n, sha in assets['sha256'].items():
            if digest(HERE/n) != sha:
                raise ValueError('asset changed after delivery')
        expected = assets['sha256']['Hyprland-copy31']
        if digest('/usr/bin/Hyprland') != expected:
            raise ValueError('experimental compositor differs')
        pid, ipc, env = find_desktop(expected)
        monitors = base.request(ipc, 'j/monitors')
        if len(monitors) != 1 or tuple(monitors[0].get(n) for n in ('width','height','scale','transform','currentFormat')) != (3456,2160,1,0,'XRGB8888'):
            raise ValueError('unexpected native display')
        options = read_options(ipc)
        if options['input:repeat_delay'].get('int') != 1000 or options['debug:damage_tracking'].get('int') != 2:
            raise ValueError('unexpected input/damage options')
        fd = os.open('/run/ilinux-desktop31.started', os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
        os.close(fd)
        emit('identity', identity=identity, options=options, snapshot=measurement.snapshot())
        os.sched_setaffinity(0, {0})
        base.clock_estimate('before')
        if base.request(ipc, 'j/getoption debug:ilinux_copy31').get('int') != 0:
            raise ValueError('copy mode must start disabled')
        changed = True
        emit('candidate_started', pixel_equivalence='pending', default_enabled=False)
        time.sleep(25)
        for index, mode in enumerate((0,1,1,0)):
            set_mode(ipc, mode)
            base.phase('copy31-mode%d-run%d' % (mode,index), pid, ipc, env, HERE)
            time.sleep(1)
        require_verified(path_evidence(pid))
        set_mode(ipc, 1)
        base.phase('human-candidate', pid, ipc, env, HERE, human_seconds=45)
        set_mode(ipc, 0)
        require_verified(path_evidence(pid))
        if read_options(ipc) != options:
            raise ValueError('desktop options changed during experiment')
        base.clock_estimate('after')
        complete = True
    except (OSError, ValueError, TimeoutError, subprocess.SubprocessError) as exc:
        emit('stop', reason=str(exc))
    finally:
        signal.alarm(0)
        # ExecStopPost on the supervising unit independently repeats this rollback
        # even if this process is forcibly killed. Both paths refuse foreign files.
        if changed:
            try:
                set_mode(ipc, 0)
                emit('reference_path_restored', executable_sha256=expected)
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                complete = False
                emit('rollback_failed', reason=type(exc).__name__, action='return_to_Macintosh_HD')
        if complete:
            emit('done', status='COPY31_OBSERVED', frequency_writes=False,
                 renderer_changes='RAM-only A/B, reference path restored', modules_loaded=False)
    return 0 if complete else 3

if __name__ == '__main__':
    sys.exit(main())

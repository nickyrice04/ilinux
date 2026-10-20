#!/usr/bin/env python3
"""Attempt30: attribute native GUI latency without changing CPU/render policy.

Two original fullscreen SHM workloads, then a 45-second human desktop window.
No injected keys, profile changes, module loading, MMIO or CPU hardware events.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
CPU28 = Path('/usr/local/lib/ilinux-cpu28')
HYPR_SHA = 'a9e57097798b2e815c8e91a0a4472d287573c4f7ce177b72a5b0907562a68da9'
sys.path.insert(0, str(CPU28))


def emit(event, **fields):
    print(json.dumps(dict(event=event, monotonic_s=time.monotonic(), **fields)), flush=True)


def request(path, command):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(2)
        sock.connect(str(path))
        sock.sendall(command.encode())
        data = bytearray()
        while True:
            block = sock.recv(16384)
            if not block:
                break
            data.extend(block)
            if len(data) > 256*1024:
                raise ValueError('IPC response exceeds bound')
    return json.loads(data)


def cpu_times(pid):
    text = Path('/proc', str(pid), 'stat').read_text()
    fields = text[text.rindex(')')+2:].split()
    return (int(fields[11])+int(fields[12])) / os.sysconf('SC_CLK_TCK'), int(fields[19])


def stop_child(child):
    if child and child.poll() is None:
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=2)


def validate_frames(rows):
    frames = [r for r in rows if r.get('event') == 'frame']
    if (len(frames) != 20 or [r.get('index') for r in frames] != list(range(20)) or
            not rows or rows[-1].get('event') != 'done' or rows[-1].get('frames') != 20):
        raise ValueError('incomplete frame workload')
    for r in frames:
        if not (0 < r['callback_ms'] < 45000 and 64 <= r['width'] <= 3840 and
                64 <= r['height'] <= 2400 and r['damage'] == ('cell' if r['index'] < 12 else 'full') and
                r['warmup'] == (r['index'] < 4)):
            raise ValueError('invalid frame sample')
    if len({(r['width'],r['height']) for r in frames})!=1:
        raise ValueError('surface geometry changed')
    return rows


def phase(name, pid, ipc, env, binary_dir, human_seconds=0, uid=1000):
    before, start_id = cpu_times(pid)
    started = time.monotonic()
    sampler = worker = None
    done = threading.Event()
    ipc_samples, errors = [], []
    def heartbeat():
        while not done.is_set():
            t = time.monotonic()
            try:
                value = request(ipc, 'j/getoption input:repeat_delay')
                if value.get('int') != 1000:
                    raise ValueError('repeat-delay changed during experiment')
                ipc_samples.append((time.monotonic()-t)*1000)
            except (OSError, ValueError) as exc:
                errors.append(type(exc).__name__)
                done.set()
                return
            done.wait(.1)
    thread = threading.Thread(target=heartbeat, daemon=True)
    rows = []
    try:
        sampler = subprocess.Popen([str(binary_dir/'samplecpu'), str(pid), '90'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   start_new_session=True)
        thread.start()
        if human_seconds:
            emit('human_window', seconds=human_seconds,
                 instruction='Open menu, type omarchy in a terminal, open file manager; no commands or setup.')
            done.wait(human_seconds)
        else:
            worker = subprocess.Popen([str(binary_dir/'frameprobe')], env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                      user=uid, group=uid, extra_groups=[], start_new_session=True)
            out, err = worker.communicate(timeout=40)
            if worker.returncode or err:
                raise ValueError('frame workload failed; no retry')
            rows = validate_frames([json.loads(s) for s in out.splitlines()])
    finally:
        done.set()
        if thread.ident:
            thread.join(timeout=3)
        stop_child(worker)
        stop_child(sampler)
        # A stalled compositor is useful evidence too. Preserve observations
        # gathered before a timeout instead of losing the whole current phase.
        problem = sys.exc_info()[0] or (ValueError if errors else None)
        if problem:
            partial_cpu = partial_profile = None
            try:
                current, current_id = cpu_times(pid)
                if current_id == start_id:
                    partial_cpu = current-before
                if sampler:
                    partial_out, _ = sampler.communicate(timeout=2)
                    partial_profile = json.loads(partial_out)
            except (OSError, ValueError, TypeError, subprocess.SubprocessError):
                pass
            emit('phase_incomplete', name=name, reason=problem.__name__,
                 wall_s=time.monotonic()-started, compositor_process_cpu_s=partial_cpu,
                 ipc_roundtrip_ms=ipc_samples, ipc_errors=errors, cpu_samples=partial_profile)
    after, final_id = cpu_times(pid)
    if start_id != final_id or errors or thread.is_alive():
        raise ValueError('compositor changed or IPC observation failed')
    out, err = sampler.communicate(timeout=2)
    if sampler.returncode or err:
        raise ValueError('CPU sampler failed')
    sampled = json.loads(out)
    if sampled.get('status') not in ('sampled', 'unavailable'):
        raise ValueError('invalid CPU sample ring')
    result = dict(name=name, wall_s=time.monotonic()-started,
                  compositor_process_cpu_s=after-before, ipc_roundtrip_ms=ipc_samples,
                  cpu_samples=sampled, frames=rows)
    emit('phase', **result)
    return result


def clock_estimate(label):
    child=subprocess.Popen([str(CPU28/'cpubench'),'freq','-t','1','-r','3','-s','0.2','-c','0'],
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    try:
        out,err=child.communicate(timeout=10)
        if child.returncode or err:
            raise ValueError('clock-estimate workload failed')
        rows=[json.loads(s) for s in out.splitlines() if s.strip()]
        if not rows:
            raise ValueError('missing clock estimate')
        emit('clock_estimate',label=label,results=rows,
             limitation='Assumes one cycle per dependent ADD; not clock or power telemetry.')
    finally:
        stop_child(child)


def find_desktop():
    pids=[]
    for p in Path('/proc').glob('[0-9]*'):
        try:
            if (p/'exe').resolve() == Path('/usr/bin/Hyprland') and (p/'status').stat().st_uid == 1000:
                pids.append(int(p.name))
        except (OSError, RuntimeError):
            continue
    if len(pids) != 1:
        raise ValueError('expected exactly one Omarchy compositor owned by uid1000')
    if hashlib.sha256(Path('/usr/bin/Hyprland').read_bytes()).hexdigest() != HYPR_SHA:
        raise ValueError('unreviewed compositor binary')
    runtime=Path('/run/user/1000')
    sockets=[p for p in (runtime/'hypr').glob('*/.socket.sock') if p.is_socket()]
    wayland=[p for p in runtime.glob('wayland-*') if p.is_socket()]
    if len(sockets)!=1 or len(wayland)!=1:
        raise ValueError('ambiguous compositor/Wayland session')
    env=dict(HOME='/home/omarchy',USER='omarchy',LOGNAME='omarchy',PATH='/usr/bin',
             XDG_RUNTIME_DIR=str(runtime),WAYLAND_DISPLAY=wayland[0].name,
             HYPRLAND_INSTANCE_SIGNATURE=sockets[0].parent.name)
    return pids[0],sockets[0],env


def main():
    import observe28
    import measurement
    def interrupted(*_):
        raise TimeoutError('desktop30 interrupted or time limit reached')
    signal.signal(signal.SIGALRM,interrupted)
    signal.signal(signal.SIGTERM,interrupted)
    signal.alarm(170)
    try:
        if os.geteuid()!=0:
            raise ValueError('collector needs the reviewed root supervisor')
        identity=observe28.identity()
        if identity['mpidr']!='0x40000' or identity['kernel']!='7.1.9-g863199d8b4a3-dirty':
            raise ValueError('unexpected core/kernel')
        observe28.verify_assets()
        if measurement.snapshot()['policies'] or any(Path('/sys/module',n).exists() for n in ('apple_soc_cpufreq','ilinux_mem29')):
            raise ValueError('previous diagnostic module or CPU policy unexpectedly active')
        pid,ipc,env=find_desktop()
        monitors=request(ipc,'j/monitors')
        if len(monitors)!=1 or (monitors[0].get('width'),monitors[0].get('height'),monitors[0].get('scale'))!=(3456,2160,1.0):
            raise ValueError('unexpected native display geometry')
        options={n:request(ipc,'j/getoption '+n) for n in
                 ('render:cm_enabled','debug:damage_tracking','input:repeat_delay','animations:enabled')}
        if options['input:repeat_delay'].get('int')!=1000 or options['debug:damage_tracking'].get('int')!=2:
            raise ValueError('unexpected native input/damage policy')
        fd=os.open('/run/ilinux-desktop30.started',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
        os.sched_setaffinity(0,{0})
        emit('identity',identity=identity,options=options,snapshot=measurement.snapshot(),
             geometry={k:monitors[0].get(k) for k in ('width','height','scale','currentFormat')})
        clock_estimate('before')
        for name in ('frame-control-1','frame-control-2'):
            phase(name,pid,ipc,env,HERE)
            time.sleep(1)
        phase('human-desktop',pid,ipc,env,HERE,human_seconds=45)
        clock_estimate('after')
        final={n:request(ipc,'j/getoption '+n) for n in options}
        if final!=options:
            raise ValueError('desktop options changed; record and return')
        emit('done',status='LATENCY_OBSERVED',frequency_writes=False,renderer_changes=False,
             modules_loaded=False,snapshot=measurement.snapshot())
        return 0
    except (OSError,ValueError,TimeoutError,subprocess.SubprocessError) as exc:
        emit('stop',reason=str(exc));return 3
    finally:
        signal.alarm(0)


if __name__=='__main__':
    sys.exit(main())

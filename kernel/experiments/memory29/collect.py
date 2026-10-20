#!/usr/bin/env python3
"""One-shot attempt29 memory evidence. Only private RAM test allocations change.

Load one architectural read-only module; never load the cpufreq module, touch
MMIO, set global VM knobs, access storage or start cores. Asset hashes are
checked by the pinned receiver before this script is executed.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
CPU28 = Path('/usr/local/lib/ilinux-cpu28')
sys.path.insert(0, str(CPU28))


def emit(event, **fields):
    print(json.dumps(dict(event=event, monotonic_s=time.monotonic(), **fields)), flush=True)


def run(argv, seconds):
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, start_new_session=True)
    try:
        out, err = p.communicate(timeout=seconds)
        if p.returncode:
            raise ValueError('child failed: %s exit=%s' % (Path(argv[0]).name, p.returncode))
        return out
    finally:
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGKILL)
            p.communicate()


def decode(line):
    match = re.search(r'ilinux_mem29 sctlr=([0-9a-f]{16}) tcr=([0-9a-f]{16}) '
                      r'mair=([0-9a-f]{16}) ctr=([0-9a-f]{16}) clidr=([0-9a-f]{16}) '
                      r'page_shift=(\d+) level=(\d+) attrs=([0-9a-f]+) normal_index=(\d+)', line)
    if not match:
        raise ValueError('missing memory-attribute observation')
    sctlr, tcr, mair, ctr, clidr = [int(x, 16) for x in match.groups()[:5]]
    shift, level, attrs, normal = match.groups()[5:]
    attrs, normal = int(attrs, 16), int(normal)
    index = (attrs >> 2) & 7
    return dict(mmu=bool(sctlr & 1), dcache=bool(sctlr & 4), icache=bool(sctlr & (1 << 12)),
                tg0=(tcr >> 14) & 3, tg1=(tcr >> 30) & 3,
                irgn0=(tcr >> 8) & 3, orgn0=(tcr >> 10) & 3, sh0=(tcr >> 12) & 3,
                irgn1=(tcr >> 24) & 3, orgn1=(tcr >> 26) & 3, sh1=(tcr >> 28) & 3,
                sample_page_index=index, sample_page_attribute=(mair >> (8 * index)) & 255,
                normal_index=normal, normal_attribute=(mair >> (8 * normal)) & 255,
                sample_page_shareability=(attrs >> 8) & 3, sample_page_valid=bool(attrs & 1),
                sample_mapping_level=int(level), page_shift=int(shift),
                ctr_hex=hex(ctr), clidr_hex=hex(clidr),
                scope='one insmod userspace stack page; not every userspace PTE')


def inventory(root=Path('/')):
    result = {}
    for name in ('enabled', 'defrag', 'hpage_pmd_size'):
        p = root / 'sys/kernel/mm/transparent_hugepage' / name
        result['thp_' + name] = p.read_text().strip() if p.exists() else None
    result['cache'] = []
    for p in sorted((root / 'sys/devices/system/cpu/cpu0/cache').glob('index*')):
        result['cache'].append({n: (p/n).read_text().strip() if (p/n).exists() else None
                                for n in ('level','type','size','coherency_line_size','shared_cpu_list')})
    return result


def main():
    import observe28
    import measurement
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('memory29 deadline')))
    signal.alarm(160)
    try:
        if os.geteuid() != 0:
            raise ValueError('explicit module load requires root')
        identity = observe28.identity()
        if identity['mpidr'] != '0x40000' or identity['kernel'] != '7.1.9-g863199d8b4a3-dirty':
            raise ValueError('not the reviewed attempt28 core/kernel')
        observe28.verify_assets()
        for module in ('ilinux_mem29', 'apple_soc_cpufreq'):
            if Path('/sys/module', module).exists():
                raise ValueError('unexpected preloaded module: ' + module)
        if measurement.snapshot()['policies']:
            raise ValueError('unexpected CPU policy; do not change it')
        fd = os.open('/run/ilinux-memory29.started', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        os.sched_setaffinity(0, {0})
        emit('identity', identity=identity, memory=inventory(), snapshot=measurement.snapshot())
        run(['/usr/bin/insmod', str(HERE/'ilinux_mem29.ko')], 10)
        lines = [s for s in run(['/usr/bin/dmesg','--color=never'],5).splitlines() if 'ilinux_mem29 ' in s]
        if len(lines) != 1:
            raise ValueError('expected exactly one architectural snapshot')
        emit('attributes', decoded=decode(lines[0]))
        for name, command, bound in (
            ('freq', [str(CPU28/'cpubench'),'freq','-t','1','-r','3','-s','0.2','-c','0'], 15),
            ('chase28', [str(CPU28/'chase_short')], 45),
            ('memory29', [str(HERE/'memory29')], 85),
            ('freq_after', [str(CPU28/'cpubench'),'freq','-t','1','-r','3','-s','0.2','-c','0'], 15)):
            output = run(command, bound)
            rows = [json.loads(s) for s in output.splitlines() if s.strip()]
            if not rows:
                raise ValueError('empty benchmark')
            if name == 'memory29' and (len(rows) != 49 or any(r.get('sink') != 0 for r in rows[1:])):
                raise ValueError('memory matrix incomplete or invalid')
            emit('benchmark', name=name, results=rows)
            time.sleep(1)
        emit('done', frequency_writes=False, global_vm_writes=False,
             status='MEMORY_OBSERVED', snapshot=measurement.snapshot())
        return 0
    except (OSError, ValueError, TimeoutError, subprocess.SubprocessError) as exc:
        emit('stop', reason=str(exc)); return 3
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    sys.exit(main())

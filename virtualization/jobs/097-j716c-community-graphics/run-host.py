#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run graphics only in an approved exclusive retained no-network Linux VM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SIBLING = ROOT.parent / 'apple-silicon-linux-research'
OWNER = 'codex-j716c-graphics097'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-build-window', action='store_true')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.absolute()
    if (not args.approved_build_window or ROOT / 'build' not in out.parents or
            '..' in out.parts or out.exists() or any(p.is_symlink() for p in out.parents)):
        raise ValueError('fresh workspace and approved exclusive window required')
    if subprocess.run(['/usr/bin/pgrep', '-x', 'vzrun'], capture_output=True).returncode == 0:
        raise ValueError('VM already running')
    held = []
    try:
        for repo in (ROOT, SIBLING):
            for name in ('quiet', 'vm'):
                subprocess.run(['/bin/sh', str(repo / 'tools/lock.sh'), 'acquire', name,
                                OWNER, 'Exact J716c offline graphics source build', '20'], check=True)
                held.append((repo, name))
        job = out / 'job'; job.mkdir(parents=True, mode=0o700); (job / 'out').mkdir(mode=0o700)
        reuse = json.loads((HERE / 'toolchain-reuse.json').read_text())
        old = ROOT / reuse['source_job']
        for name, expected in reuse['files'].items():
            if hashlib.sha256((old / name).read_bytes()).hexdigest() != expected:
                raise ValueError('reused compiler helper pin differs')
        for name, expected in reuse['aura_helpers'].items():
            if hashlib.sha256((ROOT / 'kernel/experiments/direct31ah/aura' / name).read_bytes()).hexdigest() != expected:
                raise ValueError('reused Aura helper pin differs')
        for p in HERE.iterdir():
            if p.suffix in ('.json', '.py', '.sh'):
                shutil.copyfile(p, job / p.name)
        kernel = ROOT / 'virtualization/jobs/096-j716c-community-kernel/prepare.py'
        shutil.copyfile(kernel, job / 'kernel-prepare.py')
        shutil.copyfile(kernel.with_name('inputs.json'), job / 'inputs.json')
        helpers = job / 'aura-helpers'; helpers.mkdir()
        for name in ('pad_boot.py', 'test_pad_boot.py', 'collect_cargo_licenses.py'):
            shutil.copyfile(ROOT / 'kernel/experiments/direct31ah/aura' / name, helpers / name)
        guards = job / 'stack-guards'; guards.mkdir()
        for name in ('validate.py', 'test_validate.py', 'manifest.json', 'package_guard.py', 'test_package_guard.py',
                     'lease.py', 'test_lease.py'):
            shutil.copyfile(ROOT / 'native/stack/j716c-community' / name, guards / name)
        probe = job / 'blit-contract'; probe.mkdir()
        for name in ('prepare_test.py', 'cpu_roundtrip.inc', 'test-only.patch', 'test_prepare.py'):
            shutil.copyfile(ROOT / 'kernel/experiments/j716c-mesa-blit-tests' / name, probe / name)
        support = job / 'support'; support.mkdir()
        for name in ('isolate-toolchain.py', 'package-space.py'):
            shutil.copyfile(old / name, support / name)
        manifest = json.loads((old / 'packages.json').read_text())
        manifest['packages'] = [x for x in manifest['packages'] if x['name'] in ('spirv-headers', 'spirv-tools')]
        (support / 'packages.json').write_text(json.dumps(manifest, indent=2) + '\n')
        (job / 'run.sh').chmod(0o700)
        command = ['/usr/bin/caffeinate', '-i', str(SIBLING / 'virtualization/bin/vzrun'),
            '--cpus', '8', '--mem', '52', '--no-net',
            '--kernel', str(SIBLING / 'virtualization/images/alarm/Image-7.1.6-vzrun2-pkg'),
            '--cmdline', 'console=hvc0 root=/dev/vda rootflags=subvol=@ rw rootwait quiet loglevel=3',
            '--disk', str(SIBLING / 'virtualization/images/alarm/root-btrfs.img')]
        shares = {'job': (job, False),
            'inputs': (ROOT / 'build/community31ay-inputs', True),
            'kernel-inputs': (ROOT / 'build/j716c-community-kernel/inputs', True),
            'cargo-crates': (ROOT / 'build/direct31ah-deps/job/cargo/registry/cache/index.crates.io-1949cf8c6b5b557f', True),
            'fatfs-packs': (ROOT / 'build/direct31ah-deps/job/cargo/git/db/fatfs-0832648bee8099b7/objects/pack', True),
            'gpu-support': (ROOT / 'build/gpu31p-sources', True)}
        for name, (path, readonly) in shares.items():
            if not path.is_dir() or path.is_symlink():
                raise ValueError('required curated public input absent')
            command += ['--share', str(path) + ':' + name + (':ro' if readonly else '')]
        pins = {p.relative_to(job).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in job.rglob('*') if p.is_file()}
        (out / 'guest-input-pins.json').write_text(json.dumps(pins, indent=2) + '\n')
        with (out / 'console.log').open('wb') as console:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=console,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = child.wait(timeout=5400)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGINT)
                try:
                    child.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL); child.wait()
                raise
        guest_exit_file = job / 'out/guest-exit.txt'
        if not guest_exit_file.is_file() or guest_exit_file.stat().st_size > 4:
            raise ValueError('guest completion evidence missing')
        guest_exit = int(guest_exit_file.read_text().strip())
        if not 0 <= guest_exit <= 255:
            raise ValueError('invalid guest completion evidence')
        receipt = {'schema': 'ilinux097-vm-run-v1', 'vm_exit': code, 'guest_exit': guest_exit,
                   'network_enabled': False,
                   'virtual_cpus': 8, 'memory_gib': 52, 'tmpfs_gib': 32, 'parallel_build_jobs': 8,
                   'existing_project_disk_only': True, 'native_ready': False,
                   'host_code_executed_from_downloads': False}
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(receipt))
        if code or guest_exit:
            raise ValueError('graphics guest reported failure; preserved outputs distinguish build and tests')
    finally:
        for repo, name in reversed(held):
            subprocess.run(['/bin/sh', str(repo / 'tools/lock.sh'), 'release', name, OWNER], check=True)


if __name__ == '__main__':
    main()

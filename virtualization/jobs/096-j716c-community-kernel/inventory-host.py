#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run only an explicitly approved inventory in the retained Linux build VM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SIBLING=ROOT.parent/'apple-silicon-linux-research'
OWNER='codex-j716c-kernel096'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-inventory-window',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    out=args.output.absolute()
    if not args.approved_inventory_window or ROOT/'build' not in out.parents or '..' in out.parts or out.exists() or any(p.is_symlink() for p in out.parents):
        raise ValueError('fresh workspace inventory and approved window required')
    disk=SIBLING/'virtualization/images/alarm/root-btrfs.img'
    image=SIBLING/'virtualization/images/alarm/Image-7.1.6-vzrun2-pkg'
    runner=SIBLING/'virtualization/bin/vzrun'
    if not all(p.is_file() and not p.is_symlink() for p in (disk,image,runner)):
        raise ValueError('retained VM input absent')
    if subprocess.run(['/usr/bin/pgrep','-x','vzrun'],capture_output=True).returncode==0:
        raise ValueError('another VM is already running')
    held=[]
    try:
        for repository in (ROOT,SIBLING):
            for name in ('quiet','vm'):
                subprocess.run(['/bin/sh',str(repository/'tools/lock.sh'),'acquire',name,OWNER,'J716c exact-stack VM inventory only','20'],check=True)
                held.append((repository,name))
        out.mkdir(parents=True,mode=0o700)
        job=out/'job';job.mkdir(mode=0o700);(job/'out').mkdir(mode=0o700)
        source=(HERE/'inventory.sh').read_bytes();(job/'run.sh').write_bytes(source);(job/'run.sh').chmod(0o700)
        command=['/usr/bin/caffeinate','-i',str(runner),'--cpus','4','--mem','12','--no-net',
            '--kernel',str(image),'--cmdline','console=hvc0 root=/dev/vda rootflags=subvol=@ rw rootwait quiet loglevel=3',
            '--disk',str(disk),'--share',str(job)+':job']
        with (out/'console.log').open('wb') as console:
            child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=console,stderr=subprocess.STDOUT,start_new_session=True)
            try:code=child.wait(timeout=180)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGINT)
                try:child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid,signal.SIGKILL);child.wait()
                raise
        receipt={'schema':'ilinux096-inventory-run-v1','vm_exit':code,'network_enabled':False,
            'existing_project_disk_only':True,'guest_script_sha256':hashlib.sha256(source).hexdigest(),
            'native_ready':False,'source_builds':0,'package_installations':0}
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        if code:raise ValueError('VM inventory failed')
        print(json.dumps(receipt))
    finally:
        for repository,name in reversed(held):
            subprocess.run(['/bin/sh',str(repository/'tools/lock.sh'),'release',name,OWNER],check=True)


if __name__=='__main__':main()

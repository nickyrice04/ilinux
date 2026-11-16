#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the explicitly approved no-net, retained-disk, tmpfs-only build."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SIBLING=ROOT.parent/'apple-silicon-linux-research'
OWNER='codex-j716c-kernel096'
SPEC=importlib.util.spec_from_file_location('prepare096',HERE/'prepare.py')
PREPARE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(PREPARE)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-build-window',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--inputs',type=Path,required=True)
    args=parser.parse_args();out=args.output.absolute();inputs=args.inputs.resolve()
    if not args.approved_build_window or ROOT/'build' not in out.parents or '..' in out.parts or out.exists() or any(p.is_symlink() for p in out.parents):raise ValueError('fresh approved workspace build required')
    if ROOT/'build' not in inputs.parents or inputs.is_symlink():raise ValueError('workspace inputs required')
    manifest=PREPARE.load_pinned_manifest(inputs)
    for row in manifest['files']:
        p=inputs/row['name']
        if not p.is_file() or p.is_symlink() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise ValueError('input differs')
    if subprocess.run(['/usr/bin/pgrep','-x','vzrun'],capture_output=True).returncode==0:raise ValueError('another VM running')
    held=[]
    try:
        for repo in (ROOT,SIBLING):
            for name in ('quiet','vm'):
                subprocess.run(['/bin/sh',str(repo/'tools/lock.sh'),'acquire',name,OWNER,'Exact J716c community kernel build','120'],check=True);held.append((repo,name))
        out.mkdir(parents=True,mode=0o700);job=out/'job';job.mkdir(mode=0o700);(job/'out').mkdir(mode=0o700)
        recipe=out/'recipe';recipe.mkdir(mode=0o700)
        files={}
        for path in HERE.iterdir():
            if path.is_file() and path.suffix in ('.py','.sh','.json'):
                data=path.read_bytes();(recipe/path.name).write_bytes(data);files[path.name]=hashlib.sha256(data).hexdigest()
        (job/'run.sh').write_text('#!/bin/bash\nset -e\nmkdir -p /mnt/recipe\nmountpoint -q /mnt/recipe || mount -t virtiofs recipe /mnt/recipe -o ro\nexec bash /mnt/recipe/run.sh\n');(job/'run.sh').chmod(0o700)
        command=['/usr/bin/caffeinate','-i',str(SIBLING/'virtualization/bin/vzrun'),'--cpus','8','--mem','48','--no-net',
            '--kernel',str(SIBLING/'virtualization/images/alarm/Image-7.1.6-vzrun2-pkg'),
            '--cmdline','console=hvc0 root=/dev/vda rootflags=subvol=@ rw rootwait quiet loglevel=3',
            '--disk',str(SIBLING/'virtualization/images/alarm/root-btrfs.img'),
            '--share',str(job)+':job','--share',str(recipe)+':recipe:ro','--share',str(inputs)+':inputs:ro']
        with (out/'console.log').open('wb') as console:
            child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=console,stderr=subprocess.STDOUT,start_new_session=True)
            try:code=child.wait(timeout=1800)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGINT)
                try:child.wait(timeout=20)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                raise
        unchanged=all((HERE/name).is_file() and sha(HERE/name)==digest for name,digest in files.items())
        job_result=job/'out/exit.json';artifact_result=job/'out/artifact-validation.json'
        job_exit=json.loads(job_result.read_text()).get('exit') if job_result.is_file() else None
        artifacts_pass=artifact_result.is_file() and json.loads(artifact_result.read_text()).get('status')=='PASS'
        result={'schema':'ilinux096-host-build-run-v1','vm_exit':code,'job_exit':job_exit,'artifacts_pass':artifacts_pass,'source_bindings':files,'sources_unchanged':unchanged,
            'vcpus':8,'memory_gib':48,'tmpfs_gib':32,'make_jobs':6,'network_enabled':False,'new_disks':0,
            'native_ready':False,'host_settings_changed':False}
        (out/'host-result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'vm_exit':code,'job_exit':job_exit,'artifacts_pass':artifacts_pass,'sources_unchanged':unchanged,'native_ready':False}))
        if code or job_exit!=0 or not artifacts_pass or not unchanged:raise ValueError('build refused or inputs changed')
    finally:
        for repo,name in reversed(held):subprocess.run(['/bin/sh',str(repo/'tools/lock.sh'),'release',name,OWNER],check=True)


if __name__=='__main__':main()

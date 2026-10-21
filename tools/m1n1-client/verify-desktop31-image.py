#!/usr/bin/env python3
"""Read-only macOS intake of the pinned attempt31 root; no extraction/execution."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('pair',ROOT/'tools/m1n1-client/verify-two-stage.py')
pair=importlib.util.module_from_spec(spec);spec.loader.exec_module(pair)

def main():
    image=Path(sys.argv[1]).resolve()
    records=ROOT/'native/boot/attempt31'
    pair.hash_image(image,pair.record(records/'omarchy-root-manifest.json','omarchy'))
    def member(name, limit):
        p=subprocess.run(['/usr/bin/tar','-xOf',str(image),name],capture_output=True,check=True,timeout=120)
        if not 0 < len(p.stdout) <= limit:raise ValueError('member size outside bound')
        return p.stdout
    prefix='usr/local/lib/ilinux-desktop31/'
    manifest=json.loads(member(prefix+'assets.json',16384))
    if manifest!=json.loads((records/'assets.json').read_text()):raise ValueError('asset manifest differs')
    sources={'collect.py':'kernel/experiments/desktop31/collect.py',
             'restore.py':'kernel/experiments/desktop31/restore.py',
             'baseline.py':'kernel/experiments/desktop30/collect.py'}
    if set(manifest['sha256']) != set(sources)|{'Hyprland-copy31','frameprobe','samplecpu'}:
        raise ValueError('asset set differs')
    for name,sha in manifest['sha256'].items():
        data=member(prefix+name,20*1024*1024)
        if hashlib.sha256(data).hexdigest()!=sha:raise ValueError('asset differs: '+name)
        if name in sources and data!=(ROOT/sources[name]).read_bytes():raise ValueError('source differs: '+name)
    if hashlib.sha256(member('usr/bin/Hyprland',20*1024*1024)).hexdigest()!=manifest['sha256']['Hyprland-copy31']:
        raise ValueError('installed experimental binary differs')
    cpu=json.loads(member('usr/local/lib/ilinux-cpu28/assets.json',16384))
    if cpu!=json.loads((ROOT/'native/boot/attempt28/assets.json').read_text()):raise ValueError('CPU28 assets manifest changed')
    print(json.dumps({'read_only':True,'status':'PASS','native':'NOT RUN',
                      'experiment_assets':6,'source_equality':True,'default_enabled':False,
                      'compositor_sha256':manifest['sha256']['Hyprland-copy31']}))

if __name__=='__main__':main()

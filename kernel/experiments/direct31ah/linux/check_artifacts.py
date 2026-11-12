#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check completed diagnostic build outputs without executing them."""
import hashlib
import json
import struct
import sys
from pathlib import Path

out=Path(sys.argv[1]);image=(out/'Image').read_bytes()
if len(image)<64 or image[56:60]!=b'ARM\x64':raise ValueError('invalid arm64 Image magic')
offset,size,flags=struct.unpack_from('<3Q',image,8)
if not size or size>128*1024*1024 or len(image)>128*1024*1024:
    raise ValueError('kernel cannot fit the execution pool')
if ((flags>>1)&3)!=2:raise ValueError('Image must have 16 KiB pages')
checks={}
for name in ('config-check.json','dt-check.json','diag-dt-check.json'):
    r=json.loads((out/name).read_text());assert r['status']=='PASS';checks[name]='PASS'
selftest_pass=False
for line in (out/'collector-selftest.json').read_text().splitlines():
    r=json.loads(line)
    if r.get('result')=='FAIL' or r.get('selftest')=='FAIL':raise ValueError('collector selftest failed')
    if r.get('scope')=='GENERIC_LINUX_CONTROL' and r.get('selftest')=='PASS':selftest_pass=True
if not selftest_pass:raise ValueError('missing completed collector selftest')
timeout_control=[json.loads(line) for line in (out/'collector-timeout-selftest.json').read_text().splitlines()]
if not timeout_control or timeout_control[-1].get('scope')!='GENERIC_LINUX_TIMEOUT_CONTROL' or timeout_control[-1].get('selftest')!='PASS' or timeout_control[-1].get('expected_timeout_observed') is not True:
    raise ValueError('missing successful intentional worker-timeout control')
files={}
for name in ('Image','kernel.config','t6050-j716c-upstream.dtb','t6050-j716c-diagnostic.dtb',
             'diag-init','initramfs-direct31ah.cpio.gz','modules-OFFLINE-REVIEW.tar.gz','input-source-files.json','collector-selftest.json','collector-timeout-selftest.json'):
    p=out/name;h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    files[name]={'bytes':p.stat().st_size,'sha256':h.hexdigest()}
print(json.dumps({'scope':'OFFLINE_FULL_KERNEL_BUILD','status':'PASS',
    'source_commit':'dc8f6f77934b471a13c91e7780e2d91ebc904b3d',
    'reporter_config_reproduced':False,'profile':'reconstructed-ram-diagnostic',
    'arm64_image_size':size,'arm64_image_text_offset':offset,'page_bytes':16384,
    'pool_bytes':128*1024*1024,'static_image_fits_pool':True,
    'runtime_pool_capacity_qualified':False,'checks':checks,'files':files,
    'physical_m5_tested':False,'boot_ready':False},indent=2))

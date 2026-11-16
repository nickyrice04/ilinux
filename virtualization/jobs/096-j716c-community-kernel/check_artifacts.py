#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate compiled files as data; do not boot or load any produced module."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tarfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('static096',HERE/'static_dt.py')
dt=importlib.util.module_from_spec(spec);spec.loader.exec_module(dt)


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def main():
    out,modules=map(Path,sys.argv[1:]);image=(out/'Image').read_bytes()
    if len(image)<64 or image[56:60]!=b'ARM\x64':raise ValueError('ARM64 Image magic')
    offset,size,flags=struct.unpack_from('<3Q',image,8)
    if not size or ((flags>>1)&3)!=2:raise ValueError('ARM64 16K image required')
    compressed=gzip.decompress((out/'Image.gz').read_bytes())
    if compressed!=image:raise ValueError('Image.gz differs from Image')
    release=(out/'kernelrelease.txt').read_text().strip()
    if release!='7.3.0-j716c-bringup-unified':raise ValueError('kernel release differs')
    config=json.loads((out/'full-config-comparison.json').read_text())
    if not config['semantic_match']:raise ValueError('full config differs')
    topology=dt.inspect((out/'t6050-j716c.PRIVATE.dtb').read_bytes())
    module_files=sorted(modules.glob('lib/modules/'+release+'/**/*.ko'))
    if not module_files:raise ValueError('no built modules')
    folded={};case_collisions=0
    for path in module_files:
        data=path.read_bytes()
        if len(data)<20 or data[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',data,18)[0]!=183:raise ValueError('non-AArch64 module')
        marker=data.find(b'vermagic=')
        if marker<0:raise ValueError('module vermagic absent')
        end=data.find(b'\0',marker)
        if end<0 or data[marker+9:end].split(b' ',1)[0].decode()!=release:raise ValueError('module release differs')
        key=str(path.relative_to(modules)).casefold()
        if key in folded:case_collisions+=1
        folded[key]=True
    with tarfile.open(out/'modules.PRIVATE.tar.gz','r:gz') as tar:
        archived=[m for m in tar if m.isfile() and m.name.endswith('.ko')]
    if len(archived)!=len(module_files):raise ValueError('module archive lost files')
    files={}
    for name in ('Image','Image.gz','kernel.config','t6050-j716c.PRIVATE.dtb','modules.PRIVATE.tar.gz'):
        path=out/name;files[name]={'bytes':path.stat().st_size,'sha256':sha(path)}
    report={'schema':'ilinux096-matched-kernel-build-v1','status':'PASS','scope':'OFFLINE_ARM64_VM_BUILD',
        'kernel_commit':'a59e709c737777495c84541c6afb6c862bb79227','full_config_semantic_match':True,
        'kernelrelease':release,'module_count':len(module_files),'module_case_collisions_preserved':case_collisions,
        'modules_aarch64_and_release_match':True,'image_page_bytes':16384,'image_header_size':size,
        'image_text_offset':offset,'static_128MiB_fit':size<=128*1024*1024 and len(image)<=128*1024*1024,
        'static_cpu_count':topology['cpu_count'],'static_core_clusters':topology['cluster_core_types'],
        'raw_upstream_dtb_private_and_nondeployable':True,'runtime_ADT_firmware_and_safety_gates_pending':True,
        'native_ready':False,'native_hardware_tested':False,'native_performance_measured':False,
        'tested_publisher_Image_gz_identical':files['Image.gz']['sha256']=='40d474c2207835d7bb9e08f955b57e125061166722837585e34790df9e9f0670',
        'files':files}
    print(json.dumps(report,indent=2,sort_keys=True))


if __name__=='__main__':main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Remove another unit's DROM and keep unrelated native devices unbound."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

spec=importlib.util.spec_from_file_location('fdt_read',Path(__file__).with_name('fdt_read.py'))
fdt=importlib.util.module_from_spec(spec);sys.modules[spec.name]=fdt;spec.loader.exec_module(fdt)

def transform(blob):
    root,reservations,boot=fdt.parse(blob)
    if 'apple,j716c' not in fdt.text(root.props.get('compatible',b'unknown\0')):
        raise ValueError('wrong board')
    removed=[];disabled=[];publisher_count=0
    for path,node in fdt.walk(root):
        if 'apple,thunderbolt-drom' in node.props:
            if len(node.props['apple,thunderbolt-drom'])>1:publisher_count+=1
            del node.props['apple,thunderbolt-drom'];removed.append(path)
        compatibles=fdt.text(node.props['compatible']) if 'compatible' in node.props else []
        # Disabled drivers are also excluded by the resolved kernel config.
        if any(c.startswith(('apple,t6050-usb4-','apple,t6050-sep','apple,t6050-isp')) for c in compatibles):
            node.props['status']=b'disabled\0';disabled.append(path)
    if publisher_count!=1:
        raise ValueError('unexpected public upstream DROM inventory')
    out=fdt.encode(root,reservations,boot)
    fdt.parse(out)
    return out,{'scope':'OFFLINE_DIAGNOSTIC_DTB_DERIVATIVE',
        'base_dtb_sha256':hashlib.sha256(blob).hexdigest(),
        'output_dtb_sha256':hashlib.sha256(out).hexdigest(),
        'removed_property':'apple,thunderbolt-drom','removed_count':len(removed),
        'publisher_droms_removed':publisher_count,'placeholder_droms_removed':len(removed)-publisher_count,
        'disabled_unqualified_nodes':disabled,'cpu_nodes_changed':False,
        'source_tree_modified':False,'native_qualified':False}

if __name__=='__main__':
    source,target=map(Path,sys.argv[1:])
    if source.resolve()==target.resolve():raise ValueError('use separate output')
    blob,report=transform(source.read_bytes());target.write_bytes(blob)
    print(json.dumps(report,indent=2))

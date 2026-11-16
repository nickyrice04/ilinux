#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare every resolved option against the published complete config."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def values(data):
    result={}
    for line in data.decode().splitlines():
        match=re.fullmatch(r'(CONFIG_[A-Za-z0-9_]+)=(.*)',line)
        disabled=re.fullmatch(r'# (CONFIG_[A-Za-z0-9_]+) is not set',line)
        if match:key,value=match.groups()
        elif disabled:key,value=disabled[1],'n'
        else:continue
        if key in result:raise ValueError('duplicate option')
        result[key]=value
    return result


def compare(reference,resolved):
    old,new=values(reference),values(resolved)
    diffs=[{'option':k,'reference':old.get(k),'resolved':new.get(k)} for k in sorted(old.keys()|new.keys()) if old.get(k)!=new.get(k)]
    no_debug=new.get('CONFIG_DEBUG_INFO_NONE')=='y' and all(
        value=='n' for key,value in new.items() if key=='CONFIG_DEBUG_INFO' or
        key.startswith(('CONFIG_DEBUG_INFO_BTF','CONFIG_DEBUG_INFO_DWARF')))
    exceptions=[];substantive=[]
    for row in diffs:
        link_probe=row=={'option':'CONFIG_CC_CAN_LINK','reference':None,'resolved':'y'}
        unused_pahole=row=={'option':'CONFIG_PAHOLE_VERSION','reference':'131','resolved':'132'} and no_debug
        if link_probe or unused_pahole:
            exceptions.append(dict(row,reason='SUCCESSFUL_USER_LINK_PROBE' if link_probe else 'PAHOLE_UNUSED_WITH_DEBUG_INFO_NONE'))
        else:substantive.append(row)
    required={'CONFIG_ARM64_16K_PAGES':'y','CONFIG_SMP':'y','CONFIG_RUST':'y','CONFIG_DEBUG_INFO_NONE':'y',
              'CONFIG_LTO_NONE':'y','CONFIG_LOCALVERSION':'"-j716c-bringup-unified"'}
    if any(new.get(k)!=v for k,v in required.items()):raise ValueError('required complete config lost')
    result={'schema':'ilinux096-full-config-comparison-v1','full_reference_options':len(old),'resolved_options':len(new),
        'reference_sha256':hashlib.sha256(reference).hexdigest(),'resolved_sha256':hashlib.sha256(resolved).hexdigest(),
        'byte_identical':reference==resolved,'all_option_differences':diffs,'substantive_differences':substantive,
        'semantic_match':not substantive,'qualified_metadata_exceptions':exceptions,
        'exception_source':'https://github.com/cameroncooper/linux/blob/a59e709c737777495c84541c6afb6c862bb79227/init/Kconfig',
        'debug_info_disabled_for_pahole_exception':no_debug,'native_ready':False}
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('reference',type=Path);parser.add_argument('resolved',type=Path)
    args=parser.parse_args();result=compare(args.reference.read_bytes(),args.resolved.read_bytes())
    print(json.dumps(result,indent=2,sort_keys=True));raise SystemExit(0 if result['semantic_match'] else 2)

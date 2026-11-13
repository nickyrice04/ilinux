#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit private REA dossiers; emit hashes/bounds only, never Apple code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

RAW_SHA='b4822fc8902c3693ee590c544011603423a75291edd60afd31210d068a4ca120'
ELF_SHA='f89169923c17be829c6b31c3c04c5695d06d42a42cea7390f61214202400dcee'
BASE=0x100c1aa4000
QUERIES={'entry-profile-preparation':0x100c1ae51d8,
         'ordinary-kernel-entry-dispatch':0x100c1ae5334}
sha=lambda b:hashlib.sha256(b).hexdigest()


def audit(raw_path,elf_path,dossiers,private_out):
    raw=raw_path.read_bytes();elf=elf_path.read_bytes()
    if sha(raw)!=RAW_SHA or sha(elf)!=ELF_SHA or elf[4096:4096+len(raw)]!=raw:
        raise ValueError('pinned source identity/mapping mismatch')
    llvm=subprocess.check_output(['xcrun','--find','llvm-objdump'],text=True).strip()
    rows=[];private_out.mkdir(parents=True,exist_ok=True)
    for name,entry in QUERIES.items():
        path=dossiers/(name+'.json');e=json.loads(path.read_text())
        rpath=dossiers/(name+'.run.json');run=json.loads(rpath.read_text())
        if run['exit']!=0 or run['input_sha256']!=ELF_SHA or int(run['address'],16)!=entry:
            raise ValueError('unsuccessful or wrong-input REA query')
        if e['subject']['digest']['sha256']!=ELF_SHA:
            raise ValueError('provider subject mismatch')
        n=e['normalized_result'];body=n['procedure']['body']
        if not body['available'] or int(n['procedure']['address'],16)!=entry:
            raise ValueError('unexpected provider body')
        addresses=set();anchors=[];counts=[]
        for region in body['ranges']:
            lo,hi=int(region['start'],16),int(region['end'],16)+1
            if lo%4 or hi%4 or not BASE<=lo<hi<=BASE+len(raw) or hi-lo>4096:
                raise ValueError('unbounded or unmapped provider body')
            want=set(range(lo,hi,4))
            if addresses&want:raise ValueError('overlapping provider ranges')
            addresses|=want
            text=subprocess.check_output([llvm,'-d','--start-address='+hex(lo),
                 '--stop-address='+hex(hi),str(elf_path)],text=True)
            (private_out/(name+'.llvm.private.txt')).write_text(text)
            words={}
            for line in text.splitlines():
                m=re.match(r'\s*(?:0x)?([0-9a-f]+):\s*((?:[0-9a-f]{2} ){3}[0-9a-f]{2}|[0-9a-f]{8})\s',line)
                if m and lo<=int(m[1],16)<hi:
                    pc=int(m[1],16)
                    if pc in words:raise ValueError('duplicate LLVM instruction')
                    value=m[2];words[pc]=bytes.fromhex(value) if ' ' in value else int(value,16).to_bytes(4,'little')
            if set(words)!=want or any(words[pc]!=raw[pc-BASE:pc-BASE+4] for pc in words):
                raise ValueError('independent LLVM/source word mismatch')
            anchors.append({'start':hex(lo),'end_exclusive':hex(hi),'bytes':hi-lo,
                            'source_offset':lo-BASE,'range_sha256':sha(raw[lo-BASE:hi-BASE])})
        actual=[int(line.split(':',1)[0],16) for line in n['assembly']]
        if len(actual)!=len(addresses) or set(actual)!=addresses:
            raise ValueError('provider assembly extent mismatch')
        flow=n.get('native_value_flow',{});operations=flow.get('operations',[])
        outside=sum(int(o['address'],16) not in addresses for o in operations)
        pseudo=n.get('pseudocode','')
        removed=pseudo.count('Removing unreachable block');bad=pseudo.lower().count('bad instruction')
        architecture_ops=0
        for line in n['assembly']:
            tail=line.partition(':')[2].strip().split()
            if tail and tail[0].lower() in ('mrs','msr','eret','hvc','smc'):
                architecture_ops+=1
        rows.append({'query_label_is_hypothesis':True,'query':name,
                     'input_sha256':ELF_SHA,'evidence_sha256':sha(path.read_bytes()),
                     'run_receipt_sha256':sha(rpath.read_bytes()),'exit':run['exit'],
                     'seconds':run['seconds'],'body_anchors':anchors,
                     'instruction_words':len(addresses),'llvm_word_mismatches':0,
                     'pcode_operations':len(operations),'pcode_outside_body':outside,
                     'pcode_truncated':bool(flow.get('truncated')),
                     'removed_block_warnings':removed,'bad_instruction_warnings':bad,
                     'direct_architectural_state_instruction_count':architecture_ops,
                     'whole_function_semantic_qualification':False,
                     'pseudocode_used_as_linux_source':False})
    return {'schema':'ilinux-direct31ai-rea-audit-v1','status':'CONSISTENCY_PASS',
            'provider':'REA 6.4.0 / Ghidra 12.1.4',
            'independent_decoder':subprocess.check_output([llvm,'--version'],text=True).splitlines()[0],
            'raw_sha256':RAW_SHA,'analysis_elf_sha256':ELF_SHA,
            'retained_generic_loader_version':'mBoot-18000.161.10',
            'analysis_base_is_not_live_address':True,'queries':rows,
            'instruction_words':sum(r['instruction_words'] for r in rows),
            'pcode_outside_body':sum(r['pcode_outside_body'] for r in rows),
            'native_entry_el_qualified':False,'selected_lab_firmware_qualified':False,
            'firmware_update_required_proven':False,'native_ready':False,
            'apple_code_or_bytes_published':False}


def main():
    a=argparse.ArgumentParser(description=__doc__)
    for n in ('raw','elf','dossiers','private-out','report'):
        a.add_argument('--'+n,type=Path,required=True)
    v=a.parse_args();r=audit(v.raw,v.elf,v.dossiers,v.private_out)
    if v.report.exists():raise ValueError('refusing existing public report')
    v.report.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'status':r['status'],'queries':len(r['queries']),'words':r['instruction_words']}))


if __name__=='__main__':main()

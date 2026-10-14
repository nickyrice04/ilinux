#!/usr/bin/env python3
"""Verify bounded REA deferred-probe queries against object bytes and the linked Image."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

def sha(data): return hashlib.sha256(data).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inspection', type=Path, required=True)
    p.add_argument('--rea', type=Path, required=True)
    p.add_argument('--image', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    obj=(a.inspection/'dd.o').read_bytes(); image=a.image.read_bytes()
    assert sha(obj)=='2e3db1646e915ed2fb173c0b50e582c40b45d99747d0507b8ff62167e6038662'
    assert sha(image)=='8849de7c2b8e529ad5895707ed26f535993cc8ff85447c450b2c13240185a0ea'
    # The preceding clock audit established the exact ELF/Image roundtrip.
    eh=struct.unpack_from('<16sHHIQQQIHHHHHH',obj)
    assert eh[0][:6]==b'\x7fELF\x02\x01' and eh[2]==183
    hs=[struct.unpack_from('<IIQQQQIIQQ',obj,eh[6]+i*eh[11]) for i in range(eh[12])]
    sh=hs[eh[13]]; names=obj[sh[4]:sh[4]+sh[5]]
    syms={}
    for h in hs:
        if h[1]!=2: continue
        strings=hs[h[6]]; strings=obj[strings[4]:strings[4]+strings[5]]
        for pos in range(h[4],h[4]+h[5],24):
            n,info,other,idx,offset,size=struct.unpack_from('<IBBHQQ',obj,pos)
            name=strings[n:].split(b'\0')[0].decode()
            syms[name]=(idx,offset,size)
    linked={}
    for line in (a.inspection/'kernel-symbols.txt').read_text().splitlines():
        fields=line.split()
        if len(fields)==4: linked[fields[3]]=(int(fields[0],16),int(fields[1],16))
        elif len(fields)==3: linked[fields[2]]=(int(fields[0],16),0)
    facts=[]
    for symbol,query in [('deferred_probe_initcall','deferred_probe_initcall'),
                         ('deferred_probe_work_func','deferred_probe_work_func')]:
        idx,offset,size=syms[symbol];h=hs[idx]
        code=obj[h[4]+offset:h[4]+offset+size]
        d=json.loads((a.rea/(query+'.json')).read_text());r=d['normalized_result']
        assert d['subject']['digest']['sha256']==sha(obj)
        start=int(r['procedure']['address'],16)
        assert r['procedure']['body']['ranges']==[{'start':hex(start),'end':hex(start+size-1)}]
        assert {int(x.split(':')[0],16) for x in r['assembly']}==set(range(start,start+size,4))
        assert all(start<=int(op['address'],16)<start+size for op in r['native_value_flow']['operations']
                   if op.get('address','').startswith('0x'))
        mh=struct.pack('<8I',0xfeedfacf,0x100000c,0,1,1,152,0,0)
        seg=struct.pack('<II16sQQQQiiII',0x19,152,b'__TEXT',offset,size,184,size,7,5,1,0)
        sec=struct.pack('<16s16sQQIIIIIIII',b'__text',b'__TEXT',offset,size,184,2,0,0,0x80000400,0,0,0)
        carrier=a.inspection/(query+'-carrier.o');carrier.write_bytes(mh+seg+sec+code)
        asm=subprocess.check_output(['xcrun','llvm-objdump','-d',str(carrier)],text=True)
        (a.inspection/(query+'-llvm.txt')).write_text(asm)
        words={int(m[1],16):int(m[2],16) for line in asm.splitlines()
               if (m:=re.match(r'^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+',line))}
        assert '<unknown>' not in asm and set(words)==set(range(offset,offset+size,4))
        assert all(struct.pack('<I',w)==code[pc-offset:pc-offset+4] for pc,w in words.items())
        relocated=set()
        for rh in hs:
            if rh[1]!=4 or rh[7]!=idx: continue
            for pos in range(rh[4],rh[4]+rh[5],24):
                loc,info,addend=struct.unpack_from('<QQq',obj,pos)
                if offset<=loc<offset+size:
                    assert loc%4==0 and (info&0xffffffff) not in (257,260)
                    relocated.add(loc-offset)
        address,lsize=linked[symbol];assert lsize==size
        image_offset=address-linked['_text'][0]
        for pos in range(0,size,4):
            if pos not in relocated:
                assert code[pos:pos+4]==image[image_offset+pos:image_offset+pos+4],(symbol,pos)
        facts.append({'elf_symbol':symbol,'rea_function':r['procedure']['name'],
                      'section':names[h[0]:].split(b'\0')[0].decode(),
                      'symbol_bytes':size,'llvm_instruction_words':size//4,
                      'image_relative_offset':hex(image_offset),
                      'linked_matching_nonrelocated_words':size//4-len(relocated),
                      'relocation_words_reviewed_separately':len(relocated),
                      'high_pcode_outside_body':0,'rea_evidence_id':d['evidence_id'],
                      'provider':d['provider']})
    a.out.write_text(json.dumps({'image_sha256':sha(image),'object_sha256':sha(obj),
        'vmlinux_sha256':'3abfbe1e4d8a86c496488230bf2cc788d15cecf1cca34bd836e7bc46ae9391bc',
        'functions':facts,'limits':['Two debugfs/workqueue boundaries require native phase and timer evidence; last-visible line is not an exact blocking PC.',
        'Relocations require linked disassembly review; pseudocode call signatures can be incomplete.',
        'No native success, timer interrupt failure or faulty device is inferred from static analysis.']},indent=2)+'\n')
    print('PASS: two full REA bodies, LLVM words and linked nonrelocated instructions')

if __name__=='__main__': main()

#!/usr/bin/env python3
"""Audit exact boot031 regcache initialization REA against ELF, LLVM and linked bytes."""
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
    image=a.image.read_bytes()
    assert sha(image)=='09d3cc302da20ef53c41bec3324d702b249a729a55e3799b5676618034bff37d'
    linked={}
    for line in (a.inspection/'kernel-symbols.txt').read_text().splitlines():
        fields=line.split()
        if len(fields)==4: linked[fields[3]]=(int(fields[0],16),int(fields[1],16))
        elif len(fields)==3: linked[fields[2]]=(int(fields[0],16),0)
    facts=[]
    for symbol, filename, digest in [('regcache_init', 'source/drivers/base/regmap/regcache.o', '1fb833a80113d04a29aff3286ff0f17e6d9a35f2f6f9914fff0b9c2114d4e8c4')]:
        query = symbol
        obj = (a.inspection/filename).read_bytes()
        assert sha(obj) == digest
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
        idx,offset,size=syms[symbol];h=hs[idx]
        code=obj[h[4]+offset:h[4]+offset+size]
        d=json.loads((a.rea/(query+'.json')).read_text());r=d['normalized_result']
        assert d['subject']['digest']['sha256']==sha(obj)
        start=int(r['procedure']['address'],16)
        for region in r['procedure']['body']['ranges']:
            assert start<=int(region['start'],16)<=int(region['end'],16)<start+size
        assembly_pcs = {int(x.split(':')[0],16) for x in r['assembly']}
        assert assembly_pcs <= set(range(start,start+size,4))
        missing = size//4 - len(assembly_pcs)
        assert missing == 0
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
        assert set(words)==set(range(offset,offset+size,4))
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
        facts.append({'object_sha256':sha(obj),'elf_symbol':symbol,'rea_function':r['procedure']['name'],
                      'section':names[h[0]:].split(b'\0')[0].decode(),
                      'symbol_bytes':size,'llvm_instruction_words':size//4,
                      'llvm_unknown_instructions':asm.count('<unknown>'),'rea_omitted_instruction_words':missing,
                      'rea_body_bytes':r['procedure']['body']['total_bytes'],
                      'image_relative_offset':hex(image_offset),
                      'linked_matching_nonrelocated_words':size//4-len(relocated),
                      'relocation_words_reviewed_separately':len(relocated),
                      'high_pcode_outside_body':0,'rea_evidence_id':d['evidence_id'],
                      'provider':d['provider']})
    a.out.write_text(json.dumps({'image_sha256':sha(image),

        'functions':facts,'limits':['Static source/REA/linked-byte consistency; no native blocked PC or hardware fix proven.']},indent=2)+'\n')
    print('PASS: bounded REA coverage measured; full ELF/LLVM/linked bytes audited')

if __name__=='__main__': main()

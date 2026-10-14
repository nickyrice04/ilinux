#!/usr/bin/env python3
"""Reconcile REA object analysis, exact Image instruction and independent LLVM."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inspection', type=Path, required=True)
    p.add_argument('--rea', type=Path, required=True)
    p.add_argument('--image', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    obj = (a.inspection/'irq-apple-aic.o').read_bytes()
    image = a.image.read_bytes()
    assert sha(obj) == '99913e7dd3cf041271635cc902720617c5eb17ee7694db0b314d47334803c79a'
    assert sha(image) == '6b683a2f52e769d1a23474b6807d009da8ad2e19d2168e62caba6cbbae240f7d'
    assert image == (a.inspection/'elf-roundtrip.bin').read_bytes()
    eh = struct.unpack_from('<16sHHIQQQIHHHHHH', obj)
    assert eh[0][:6] == b'\x7fELF\x02\x01' and eh[2] == 183
    headers = [struct.unpack_from('<IIQQQQIIQQ',obj,eh[6]+i*eh[11]) for i in range(eh[12])]
    sh = headers[eh[13]]; names = obj[sh[4]:sh[4]+sh[5]]
    sections = {names[h[0]:].split(b'\0')[0].decode(): obj[h[4]:h[4]+h[5]] for h in headers}
    evidence = []
    for name, section, offset, size in [('aic_init_cpu','.text',0x7b0,0x138),
                                        ('aic_handle_fiq','.irqentry.text',0x160,0x17c)]:
        d = json.loads((a.rea/(name+'.json')).read_text()); r = d['normalized_result']
        assert d['subject']['digest']['sha256'] == sha(obj)
        assert r['procedure']['name'] == name
        start = int(r['procedure']['address'],16)
        body = [(int(x['start'],16),int(x['end'],16)) for x in r['procedure']['body']['ranges']]
        assert all(start <= b <= e < start+size for b,e in body)
        pcs = {int(line.split(':')[0],16) for line in r['assembly']}
        assert pcs == {x for b,e in body for x in range(b,e+1,4)}
        assert all(any(b<=int(op['address'],16)<=e for b,e in body)
                   for op in r['native_value_flow']['operations'] if op.get('address','').startswith('0x'))
        code = sections[section][offset:offset+size]
        assert len(code) == size
        # Static analysis carrier preserves every instruction, never executed.
        mh=struct.pack('<8I',0xfeedfacf,0x100000c,0,1,1,152,0,0)
        sg=struct.pack('<II16sQQQQiiII',0x19,152,b'__TEXT',offset,size,184,size,7,5,1,0)
        sc=struct.pack('<16s16sQQIIIIIIII',b'__text',b'__TEXT',offset,size,184,2,0,0,0x80000400,0,0,0)
        carrier=a.inspection/(name+'-carrier.o');carrier.write_bytes(mh+sg+sc+code)
        asm=subprocess.check_output(['xcrun','llvm-objdump','-d',str(carrier)],text=True)
        (a.inspection/(name+'-llvm.txt')).write_text(asm)
        words={int(m[1],16):int(m[2],16) for line in asm.splitlines()
               if (m:=re.match(r'^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+',line))}
        assert set(words)==set(range(offset,offset+size,4))
        assert all(struct.pack('<I',w)==code[pc-offset:pc-offset+4] for pc,w in words.items())
        assert '<unknown>' not in asm
        evidence.append({'function':name,'object_section':section,'object_offset':hex(offset),
                         'elf_symbol_bytes':size,'rea_body_bytes':sum(e-b+1 for b,e in body),
                         'llvm_instruction_words':len(words),'high_pcode_outside_body':0,
                         'rea_evidence_id':d['evidence_id'],'provider':d['provider'],
                         'rea_full_symbol_coverage':sum(e-b+1 for b,e in body)==size})
    pc_offset=0x663e30+0x9c
    assert struct.unpack_from('<I',image,pc_offset)[0]==0xd51df160
    assert struct.unpack_from('<I',sections['.text'],0x7b0+0x9c)[0]==0xd51df160
    # The fault and straight-line EL2 register-update sequence are exact in both.
    assert image[0x663e30+0x8c:0x663e30+0xa0] == sections['.text'][0x7b0+0x8c:0x7b0+0xa0]
    result={'boot024_image_sha256':sha(image),'object_sha256':sha(obj),
            'vmlinux_sha256':'70cfefa993df92eba8d81ec50708377253d3db20e8245095f15ee31ae436ef53',
            'fault':{'symbol':'aic_init_cpu','offset':'0x9c','instruction_word':'d51df160',
                     'instruction':'msr s3_5_c15_c1_3, x0','register':'SYS_IMP_APL_VM_TMR_FIQ_ENA_EL2'},
            'functions':evidence,
            'limits':['Object relocations and static-key runtime patching require source/linked-binary cross-checks.',
                      'Ghidra omits 48 bytes of aic_init_cpu: alternate static-key and post-WARN continuation paths. Its pseudocode is not a complete function model.',
                      'The write traps in the observed boot state; register absence or its restriction mechanism is not established.',
                      'No native boot025 or performance result is established by these static checks.']}
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('PASS: exact fault word and EL2 sequence, two bounded REA queries, 173 LLVM instruction words')

if __name__=='__main__': main()

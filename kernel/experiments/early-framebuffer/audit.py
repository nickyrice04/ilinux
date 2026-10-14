#!/usr/bin/env python3
"""Check REA boundaries/byte provenance and linked diagnostic descriptor."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess


def digest(b): return hashlib.sha256(b).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--rea-dir', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    repo = a.repo
    raw = (repo/'build/native-boot022/verified/m1n1.bin').read_bytes()
    elf = (repo/'virtualization/jobs/023-dapf-handoff/out/m1n1-raw.elf').read_bytes()
    assert digest(raw) == 'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'
    assert raw == (repo/'virtualization/jobs/023-dapf-handoff/out/elf-roundtrip.bin').read_bytes()
    work = repo/'virtualization/jobs/024-early-framebuffer/out'
    facts = []
    for name, start, end in [('fb_shutdown', 0x1bf80, 0x1c02c),
                              ('m1n1_main', 0x25620, 0x257b4)]:
        ev = json.loads((a.rea_dir/(name+'.json')).read_text())
        r = ev['normalized_result']; proc = r['procedure']
        assert ev['subject']['digest']['sha256'] == digest(elf)
        assert proc['name'] == name
        bias = int(proc['address'], 16) - start
        assert bias == 0x100000
        assert proc['body']['ranges'] == [{'start': hex(start+bias), 'end': hex(end-1+bias)}]
        expected = set(range(start, end, 4))
        assert {int(line.split(':')[0], 16)-bias for line in r['assembly']} == expected
        assert all(int(op['address'], 16)-bias in expected
                   for op in r['native_value_flow']['operations']
                   if op.get('address', '').startswith('0x'))
        code = raw[start:end]
        # Analysis carrier only: existing Apple LLVM cannot read this Rust ELF.
        mh = struct.pack('<8I', 0xfeedfacf, 0x100000c, 0, 1, 1, 152, 0, 0)
        seg = struct.pack('<II16sQQQQiiII', 0x19, 152, b'__TEXT', start, len(code), 184, len(code), 7, 5, 1, 0)
        sect = struct.pack('<16s16sQQIIIIIIII', b'__text', b'__TEXT', start, len(code), 184, 2, 0, 0, 0x80000400, 0, 0, 0)
        carrier = work/(name+'-carrier.o'); carrier.write_bytes(mh+seg+sect+code)
        asm = subprocess.check_output(['xcrun','llvm-objdump','--disassemble',str(carrier)], text=True)
        (work/(name+'-llvm.txt')).write_text(asm)
        seen = set()
        for line in asm.splitlines():
            match = re.match(r'^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(.+)$', line)
            if not match: continue
            address, word = int(match[1],16), int(match[2],16)
            assert address in expected and address not in seen
            assert struct.pack('<I',word) == raw[address:address+4]
            assert '<unknown>' not in match[3]
            seen.add(address)
        assert seen == expected
        facts.append({'function':name,'relative_start':hex(start),'relative_end_exclusive':hex(end),
                      'instructions':len(expected),'rea_evidence_id':ev['evidence_id'],
                      'provider':ev['provider'],'pcode_outside_body':0})
    image = (work/'export/Image').read_bytes()
    manifest = json.loads((repo/'native/boot/package-manifest.json').read_text())
    offset = manifest['early_framebuffer_descriptor_offset']
    assert image[offset-16:offset+16] == b'ILINUX-FB024-V1\0'+bytes(16)
    assert offset % 8 == 0
    symbols = {}
    for line in (work/'kernel-symbols.txt').read_text().splitlines():
        fields = line.split()
        if len(fields) == 3: symbols[fields[2]] = int(fields[0],16)
    assert symbols['ilinux_fb_descriptor']-symbols['_text'] == offset
    assert digest(image) == manifest['files']['Image']['sha256']
    a.out.write_text(json.dumps({'installed_m1n1_sha256':digest(raw), 'matching_elf_sha256':digest(elf),
        'functions':facts,'kernel_sha256':digest(image),'descriptor_relative_offset':hex(offset),
        'limits':['Static teardown analysis does not identify the attempt-4 stop location',
                  'Diagnostic framebuffer writes and early console are not native-tested']}, indent=2)+'\n')
    print('PASS: exact bootloader bytes, REA/LLVM boundaries and linked kernel descriptor')


if __name__ == '__main__': main()

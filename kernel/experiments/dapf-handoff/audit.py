#!/usr/bin/env python3
"""Verify exact boot021 symbolization, REA boundaries, decoders and ADT layout.

Reads only project artifacts. Saves summary metadata, never raw ADT or registers.
"""
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
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--rea', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); root = a.repo
    out = root / 'virtualization/jobs/023-dapf-handoff/out'
    raw = (root / 'build/native-boot022/verified/m1n1.bin').read_bytes()
    elf = (out / 'm1n1-raw.elf').read_bytes()
    assert sha(raw) == 'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'
    assert sha(raw) == sha((out / 'elf-roundtrip.bin').read_bytes())
    assert elf[:6] == b'\x7fELF\x02\x01'
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', elf)
    phoff, shoff = header[5:7]
    phsize, phnum, shsize, shnum = header[9:13]
    segments = [struct.unpack_from('<IIQQQQQQ', elf, phoff + i * phsize) for i in range(phnum)]
    sections = [struct.unpack_from('<IIQQQQIIQQ', elf, shoff + i * shsize) for i in range(shnum)]
    def mapped(address, count):
        matches = [s for s in segments if s[0] == 1 and s[3] <= address and address + count <= s[3] + s[5]]
        assert len(matches) == 1
        s = matches[0]; off = s[2] + address - s[3]
        return elf[off:off + count]
    assert mapped(0x160e0, 0x16618 - 0x160e0) == raw[0x160e0:0x16618]
    relocs = {}
    for s in sections:
        if s[1] == 4:
            assert s[9] == 24
            for off in range(s[4], s[4] + s[5], 24):
                address, info, addend = struct.unpack_from('<QQq', elf, off)
                assert not 0x160e0 <= address < 0x16618, 'live code has relocations'
                if 0x102728 <= address < 0x102788:
                    assert info == 1027  # R_AARCH64_RELATIVE, no symbol index.
                    assert address not in relocs
                    relocs[address] = addend
    paths = ['aop', 'mtp', 'pmp', 'isp', 'isp0']
    offsets = [0x71218, 0x71230, 0x71248, 0x71260, 0x71278]
    assert relocs == {0x102728 + i * 16: offset for i, offset in enumerate(offsets)}
    for path, off in zip(paths, offsets):
        text = ('/arm-io/dart-' + path).encode() + b'\0'
        assert raw[off:off + len(text)] == text
    ev = json.loads(a.rea.read_text()); r = ev['normalized_result']; proc = r['procedure']
    assert ev['subject']['digest']['sha256'] == sha(elf)
    assert proc['name'] == 'dapf_init' and proc['body']['ranges'] == [{'start': '0x1160e0', 'end': '0x11658f'}]
    bias = int(proc['address'], 16) - 0x160e0
    addresses = set(range(0x160e0, 0x16590, 4))
    assert {int(line.split(':')[0], 16) - bias for line in r['assembly']} == addresses
    operations = r['native_value_flow']['operations']
    outside = [op for op in operations if op.get('address', '').startswith('0x') and
               int(op['address'], 16) - bias not in addresses]
    assert not outside
    assert not any(s in r['pseudocode'] for s in ('halt_baddata', 'Truncating control flow', 'bad instruction'))
    # Apple LLVM rejects this Rust-linked ELF's metadata. Wrap exactly the
    # same 1,200 function bytes in a minimal analysis-only Mach-O object;
    # preserve code addresses. This object is never linked or executed.
    code = raw[0x160e0:0x16590]
    mh = struct.pack('<8I', 0xfeedfacf, 0x100000c, 0, 1, 1, 152, 0, 0)
    seg = struct.pack('<II16sQQQQiiII', 0x19, 152, b'__TEXT', 0x160e0, len(code), 184, len(code), 7, 5, 1, 0)
    sect = struct.pack('<16s16sQQIIIIIIII', b'__text', b'__TEXT', 0x160e0, len(code), 184, 2, 0, 0, 0x80000400, 0, 0, 0)
    wrapper = out / 'dapf-byte-wrapper.o'
    wrapper.write_bytes(mh + seg + sect + code)
    with (out / 'dapf-llvm.txt').open('w') as stream:
        subprocess.run(['xcrun', 'llvm-objdump', '--disassemble', str(wrapper)], stdout=stream, check=True)
    for name in ['dapf-disassembly.txt', 'dapf-llvm.txt']:
        lines = (out / name).read_text().splitlines(); seen = set()
        for line in lines:
            m = re.match(r'^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(.+)$', line)
            if not m: continue
            addr, word = int(m[1], 16), int(m[2], 16)
            if addr not in addresses: continue
            assert addr not in seen and struct.pack('<I', word) == raw[addr:addr + 4]
            assert '<unknown>' not in m[3]
            seen.add(addr)
        assert seen == addresses, name
    rootadt = json.loads((root / 'hardware/adt/adt-sanitized.json').read_text())
    facts = []
    def visit(n):
        name = n['path'].split('/')[-1]
        if name in ('dart-aop', 'dart-mtp', 'dart-isp0'):
            v = n['values']; words = [int(w, 16) for w in v['instance']]
            assert len(words) % 4 == 0 and len(words) // 4 == len(v['reg'])
            kinds = [words[i] for i in range(0, len(words), 4)]
            ix = [i for i, kind in enumerate(kinds) if kind == 0x44415046]
            facts.append({'node': name, 'register_count': len(kinds),
                          'instance_types': [hex(k) for k in kinds], 'dapf_indexes': ix})
        for child in n['children']: visit(child)
    visit(rootadt)
    assert {f['node']: f['dapf_indexes'] for f in facts} == {'dart-aop': [], 'dart-mtp': [1], 'dart-isp0': [5]}
    report = {'installed_raw_sha256': sha(raw), 'matching_elf_sha256': sha(elf),
              'elf_roundtrip_matches': True, 'table_relocations_verified': 5,
              'exception_relative_pc': '0x16458', 'function': 'dapf_init_t8110a (inlined in dapf_init)',
              'instruction_at_pc': 'ldrb w5, [x0, #4]', 'preceding_mmio_store': '0x16438: str w3, [x5]',
              'rea_provider': ev['provider'], 'rea_evidence_id': ev['evidence_id'],
              'ghidra_load_bias': hex(bias), 'instructions_checked_each_decoder': len(addresses),
              'pcode_operations': len(operations), 'pcode_outside_body': len(outside),
              'rea_boundary_gate': 'PASS; manual source/assembly review performed',
              'adt_facts': facts,
              'limits': ['SError is asynchronous; exact original faulting write not established',
                         'ADT snapshot is macOS inventory; next live attempt must recheck layout',
                         'No native correction test or Linux execution observed']}
    a.out.write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: exact ELF/raw, relocations, REA body, 300 instructions in two decoders, ADT layout')


if __name__ == '__main__': main()

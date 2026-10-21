#!/usr/bin/env python3
"""Offline evidence for a proposed CPU1-only RAM-state experiment.

No proxy imports, USB access, target writes or deployment commands. These
checks establish a linked-image layout, not execution on a secondary CPU.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

IMAGE_SHA = 'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'
SYMBOL_SHA = '751a9643a2196eda44efba4789aa789465b2b75e9546be460946d2fa4c70ac11'
SOURCE_SHA = {
    'start.S': '91de75024c12f034a046171e88c8be9377bb09e4bfe95bf1ac5ba3cdd1e423ea',
    'smp.c': '4b000be8d4e6437fc24351a57db5277785cc2e427045fb45d1750b158f2b8766',
    'startup.c': 'c563ad48a6da509f4914624a38ea4ad6adea8d1220d707dce698c698b032f865',
    'memory.c': 'a3a07cf06c0b16c0964c0e894a11914fd62900a1494b4e3cfaa184e2642b6609',
    'utils.c': '0361304388c7b42de38bc6be8717f25f48e59fb8c513712ee202c2d698a2ac5c',
    'proxy.c': '647a6e8468ef1ff0728a81eff46a831c88a14be610b3a4bad34a99fe8f26ea5c',
    'smp_asm.h': '2afe4c4ac4cd696a2d020fcef5621aa1ac66c2e7edcaaaef11f17df17cc696bd',
}
EXPECTED = {
    '_vectors_start': 0, 'cpu_reset': 0x8fc, '_cpu_reset_c': 0x328e0,
    'smp_secondary_entry': 0x30d40, 'smp_set_wfe_mode': 0x318c0,
    'timeout_calculate': 0x37f20,
    '_smp_shared_start': 0x90000, '_smp_shared_end': 0xa0000,
    'smp_reset_stacks': 0x90010, 'spin_table': 0x90210,
    'target_cpu': 0x90a10, 'wfe_mode': 0x90a14,
    '_reset_stack': 0x90a20, 'secondary_stacks': 0x158000,
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def branch_target(image, offset, link=False):
    require(0 <= offset <= len(image) - 4 and offset % 4 == 0,
            'instruction outside image or unaligned')
    word, = struct.unpack_from('<I', image, offset)
    require(word >> 26 == (0b100101 if link else 0b000101),
            'unexpected branch opcode')
    displacement = word & 0x3ffffff
    if displacement & (1 << 25):
        displacement -= 1 << 26
    return offset + displacement * 4


def layout(symbols):
    for name, value in EXPECTED.items():
        require(symbols.get(name) == value, 'linked symbol mismatch: ' + name)
    lo, hi = symbols['_smp_shared_start'], symbols['_smp_shared_end']
    spans = [(symbols['smp_reset_stacks'], 32 * 16),
             (symbols['spin_table'], 32 * 64),
             (symbols['target_cpu'], 4), (symbols['wfe_mode'], 1),
             (symbols['_reset_stack'], 8)]
    require(all(lo <= start < start + size <= hi for start, size in spans),
            'SMP state outside uncached shared section')
    for (start, size), (following, _) in zip(sorted(spans), sorted(spans)[1:]):
        require(start + size <= following, 'overlapping SMP state')
    return {
        'cpu_id': 1, 'expected_mpidr': '0x40001',
        'spin_record_offset': hex(symbols['spin_table'] + 64),
        'reset_stack_record_offset': hex(symbols['smp_reset_stacks'] + 16),
        'dedicated_stack_bottom_offset': hex(symbols['secondary_stacks'] + 0x10000),
        'dedicated_stack_top_offset': hex(symbols['secondary_stacks'] + 0x20000),
        'stack_bytes': 0x10000,
    }


def audit(image, symbol_bytes, sources):
    require(len(image) == 3932160 and hashlib.sha256(image).hexdigest() == IMAGE_SHA,
            'boot021 image mismatch')
    require(hashlib.sha256(symbol_bytes).hexdigest() == SYMBOL_SHA,
            'boot021 symbol table mismatch')
    for name, digest in SOURCE_SHA.items():
        require(hashlib.sha256(sources[name]).hexdigest() == digest,
                'pinned source mismatch: ' + name)
    symbols = {}
    for line in symbol_bytes.decode('ascii').splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[2] in EXPECTED:
            require(fields[2] not in symbols, 'duplicate expected symbol')
            symbols[fields[2]] = int(fields[0], 16)
    cpu = layout(symbols)
    require(branch_target(image, 4) == symbols['cpu_reset'],
            'vector does not branch to cpu_reset')
    require(branch_target(image, 0x970, link=True) == symbols['_cpu_reset_c'],
            'non-EL3 reset call differs')
    return {
        'result': 'OFFLINE_LAYOUT_VERIFIED',
        'image_sha256': IMAGE_SHA, 'symbol_table_sha256': SYMBOL_SHA,
        'source_sha256': SOURCE_SHA,
        'image_relative_symbols': {k: hex(v) for k, v in symbols.items()},
        'cpu1_layout': cpu,
        'branch_checks': ['vectors+4 -> cpu_reset', 'cpu_reset non-EL3 -> _cpu_reset_c'],
        'native_cpu_start': 'NOT RUN', 'deployment_ready': False,
        'limit': 'Static layout only; no reset execution, park, Linux SMP or efficiency evidence.',
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', required=True, type=Path)
    p.add_argument('--symbols', required=True, type=Path)
    p.add_argument('--source', required=True, type=Path)
    args = p.parse_args()
    print(json.dumps(audit(args.image.read_bytes(), args.symbols.read_bytes(),
          {name: (args.source / 'src' / name).read_bytes() for name in SOURCE_SHA}), indent=2))


if __name__ == '__main__':
    main()

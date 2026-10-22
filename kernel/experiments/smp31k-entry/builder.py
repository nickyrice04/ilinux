#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Original cold provenance tripwire encoder. No target operations or writes."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('_31k_cold_audit', HERE / 'audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
need = audit.need
COLD_ENTRY, RESUME = 0x800, None
CODE_START, CODE_END = 0xb00, 0xc00
RECORD, RECORD_END = 0x90a80, 0x90ac0
ORIGINAL_WORD = 0xaa0003f3
branch, adrp = audit.previous.branch, audit.previous.adrp


def program():
    """Independent A64 encoding; independent assembly must match before use."""
    words = [adrp(CODE_START, RECORD), 0x91000000 | (RECORD & 4095) << 10,
             0xd2800028, 0xf9000008, 0xd5033f9f,
             0xd53800a8, 0xd3405d08, 0xf9000808, 0xd5033f9f,
             0xd2800048, 0xf9000008, 0xd5033f9f,
             0xd5384249, 0xf9000409, 0xd5033f9f,
             0xd2800068, 0xf9000008, 0xd5033f9f, 0x14000000]
    labels = {'first_store': CODE_START+12, 'first_mrs': CODE_START+20,
              'identity_commit': CODE_START+40, 'el_commit': CODE_START+64,
              'terminal_spin': CODE_START+72}
    need(CODE_START + 4*len(words) <= CODE_END, 'tripwire_too_large')
    return struct.pack('<19I', *words), labels


def build(image, symbols=None):
    checked = audit.audit(image, symbols)
    body, labels = program()
    hook = struct.pack('<I', branch(COLD_ENTRY, CODE_START))
    return ({'schema': 1, 'kind': 'smp31k_original_cold_provenance_tripwire',
             'native_deployment_ready': False, 'entry_authorized': False,
             'input_image_sha256': checked['image_sha256'],
             'input_symbol_sha256': checked['symbol_sha256'],
             'source_sha256': hashlib.sha256((HERE/'tripwire.S').read_bytes()).hexdigest(),
             'entry_offset': hex(COLD_ENTRY), 'resume_offset': None,
             'recorder_offset': hex(CODE_START), 'recorder_bytes': len(body),
             'recorder_sha256': hashlib.sha256(body).hexdigest(),
             'entry_original_word': hex(ORIGINAL_WORD),
             'entry_branch_word': hex(struct.unpack('<I', hook)[0]),
             'record_range': [hex(RECORD), hex(RECORD_END)],
             'record_fields': {'phase': 0, 'current_el': 8, 'mpidr_low24': 16},
             'phase_meaning': {'0': 'no_publication_observed',
                               '1': 'first_store_before_system_reads',
                               '2': 'identity_published', '3': 'current_el_published'},
             'clobbers': ['x0', 'x8', 'x9'], 'sp_changed': False,
             'lr_changed': False, 'nzcv_changed': False,
             'incoming_x0_retained': False, 'mmio_operations': 0,
             'system_register_writes': 0, 'effective_cpu1_entry': 'UNKNOWN',
             'park_verified': False, 'terminal_behavior': 'externally_bounded_terminal_spin',
             'phase3_proves_loop_execution': False, 'resumes_shared_bss': False,
             'labels': {key: hex(value) for key, value in labels.items()},
             'layout_audit': checked['layout_audit'], 'entry_audit': checked,
             'native_execution': 'NOT RUN'}, body, hook)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--symbols', type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.image.read_bytes(),
                           args.symbols.read_bytes() if args.symbols else None)[0], sort_keys=True))

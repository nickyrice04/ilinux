#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Original Normal-first prefix encoder. No target operations or file writes."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('_31l_prefix_audit', HERE / 'audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
need = audit.need
branch = audit.previous.previous.branch
CODE = {'vector': 0xc00, 'cold': 0xd00}
ENTRY = {'vector': 0, 'cold': 0x800}
RESUME = {'vector': 0xa00, 'cold': 0xb00}
RECORD = {'vector': 0x1000, 'cold': 0x1080}
RECORD_BYTES = 64
HELPER_BYTES = 0x4000
BODY_BYTES = 60


def record_address(kind, helper):
    need(type(kind) is str and kind in CODE, 'normal_prefix_kind')
    need(type(helper) is int and 0 < helper < (1 << 41)-HELPER_BYTES and
         helper % HELPER_BYTES == 0, 'normal_helper_address')
    return helper + RECORD[kind]


def program(kind, helper):
    """Preserve x0/SP/LR/NZCV. Normal phase1 precedes the first MRS.

The caller must own and retain the entire bounded allocation, establish CPU0
mapping/observation and publish instructions. None establishes CPU1's mapping.
"""
    address = record_address(kind, helper)
    words = [0xd2800008 | ((address & 65535) << 5)]
    words += [0xf2800008 | (half << 21) | (((address >> (16*half)) & 65535) << 5)
              for half in (1, 2, 3)]
    words += [0xd2800029, 0xf9000109, 0xd5033f9f, 0xd53800a9,
              0xd3405d29, 0xf9000509, 0xd5033f9f, 0xd2800049,
              0xf9000109, 0xd5033f9f, branch(CODE[kind]+56, RESUME[kind])]
    body = struct.pack('<15I', *words)
    need(len(body) == BODY_BYTES, 'normal_prefix_size')
    labels = {name: CODE[kind]+offset for name, offset in
              [('first_store', 20), ('first_mrs', 28), ('identity_store', 36),
               ('identity_commit', 48), ('branch_to_existing', 56)]}
    return body, labels


def build(image, symbols=None):
    checked = audit.audit(image, symbols)
    return dict(schema=1, kind='smp31l_normal_first_prefix',
                entry_audit=checked, native_deployment_ready=False,
                native_execution='NOT RUN', code_offsets=CODE, entry_offsets=ENTRY,
                resume_offsets=RESUME, record_offsets=RECORD, record_bytes=RECORD_BYTES,
                body_bytes=BODY_BYTES, identity_offset=8,
                source_sha256=hashlib.sha256((HERE/'prefix.S').read_bytes()).hexdigest(),
                clobbers=['x8', 'x9'], incoming_x0_retained=True,
                sp_changed=False, lr_changed=False, nzcv_changed=False,
                system_register_writes=0, cache_operations=0, mmio_operations=0,
                negative_observation_excludes_execution=False,
                phase2_proves_existing_recorder_reached=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--symbols', type=Path)
    args = parser.parse_args()
    try:
        image = args.image.read_bytes()
        symbols = args.symbols.read_bytes() if args.symbols else None
        print(json.dumps(build(image, symbols), sort_keys=True))
    except (OSError, ValueError, UnicodeError):
        print(json.dumps(dict(result='OFFLINE_REFUSED', native_execution='NOT RUN')))
        raise SystemExit(1)

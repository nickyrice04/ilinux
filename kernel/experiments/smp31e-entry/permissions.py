#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Pure fixed-range CPU0 translation checks; no transport or target execution.

Successful AT checks are not proof that a hardware write will succeed. The
controller must also use guarded writes, immediate exception checks and exact
readback, and must stop on any discrepancy without changing protections.
"""
import hashlib
import struct

RW_ALIAS = 0xa0000000000
EXPECTED_HCR = 0x32488000038
HCR_REGIME_MASK = (1 << 34) | (1 << 27) | 1  # E2H, TGE, VM
HCR_VHE_HOST = (1 << 34) | (1 << 27)
PAR_PA = ((1 << 52) - 1) & ~0xfff
HELPER_OFFSETS = {'el1_read': 192, 'el1_write': 224,
                  'el2_read': 256, 'el2_write': 288, 'hcr': 320}
HELPER_TAIL_WORDS = (
    0xd5387402, 0xd5087800, 0xd5033fdf, 0xd5387400,
    0xd5187402, 0xd5033fdf, 0xd65f03c0, 0xd503201f,
    0xd5387402, 0xd5087820, 0xd5033fdf, 0xd5387400,
    0xd5187402, 0xd5033fdf, 0xd65f03c0, 0xd503201f,
    0xd5387402, 0xd50c7800, 0xd5033fdf, 0xd5387400,
    0xd5187402, 0xd5033fdf, 0xd65f03c0, 0xd503201f,
    0xd5387402, 0xd50c7820, 0xd5033fdf, 0xd5387400,
    0xd5187402, 0xd5033fdf, 0xd65f03c0, 0xd503201f,
    0xd5384240, 0xf100201f, 0x54000061, 0xd53c1100,
    0xd65f03c0, 0xaa1f03e0, 0xd65f03c0, 0xd503201f,
)
HELPER_TAIL = struct.pack('<40I', *HELPER_TAIL_WORDS)
HELPER_TAIL_SHA = '44dfcab7a9c4aa49f7e18b4e635061f2c3f5da2bf1b928862785e8bd485ca0db'


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def uint64(value):
    return type(value) is int and 0 <= value < 1 << 64


def select_regime(current_el, hcr=0):
    """Choose fixed AT helper entries; the caller checks CPU0 before starting.

    In EL2, the pinned proxy configures a VHE host regime with E2H/TGE set.
    Require E2H/TGE and no stage-2 enable; use S1E2 rather than guessing S1E1
    semantics. Unrelated bits may read as zero on unimplemented features and
    are not a basis for rejecting this translation regime.
    The HCR helper itself branches around the privileged read outside EL2.
    """
    need(type(current_el) is int and current_el in (4, 8), 'permission_current_el')
    need(uint64(hcr), 'permission_hcr_type')
    if current_el == 4:
        need(hcr == 0, 'permission_el1_hcr')
        return {'read_offset': 192, 'write_offset': 224}
    need(hcr & HCR_REGIME_MASK == HCR_VHE_HOST, 'permission_el2_regime')
    return {'read_offset': 256, 'write_offset': 288}


def probe_plan(base):
    """Sixteen read-only address-translation operations over fixed spans.

    Code hook/stub share a 4 KiB page, smaller than every supported granule.
    Both ends of the shared record likewise share one page. Repeated checks
    intentionally bind each named artifact, rather than accepting arbitrary
    caller-selected targets. No raw address belongs in public results.
    """
    need(uint64(base) and 0 < base < (1 << 41) and base % 0x4000 == 0,
         'permission_base')
    plan = []
    for name, offset in (('hook', 0x8fc), ('stub_first', 0xa00), ('stub_last', 0xac8)):
        pa = base + offset
        for suffix, address, write, fault in (
                ('identity_read', pa, False, False),
                ('alias_read', pa | RW_ALIAS, False, False),
                ('alias_write', pa | RW_ALIAS, True, False),
                ('identity_write', pa, True, True)):
            plan.append(dict(name=name + '_' + suffix, address=address,
                             physical=pa, write=write, permission_fault=fault,
                             attr=0xff, shareability=2))
    for name, offset in (('record_first', 0x90a40), ('record_last', 0x90a78)):
        for write in (False, True):
            plan.append(dict(name=name + ('_write' if write else '_read'),
                             address=base + offset, physical=base + offset,
                             write=write, permission_fault=False, attr=0,
                             shareability=None))
    return tuple(plan)


def validate_probe(probe, par):
    """Validate PAR without returning target addresses or raw register values."""
    need(uint64(par), 'permission_par_type')
    if probe['permission_fault']:
        # The pinned mapping is read/execute. Distinguish permission denial
        # from translation/address-size/access-flag faults: only the former
        # demonstrates that the expected mapping is present but not writable.
        need(par & 1 == 1 and (par >> 1) & 0x3f in (0xc, 0xd, 0xe, 0xf),
             'permission_identity_write_not_denied')
        return True
    need(par & 1 == 0, 'permission_translation_fault')
    physical = (par & PAR_PA) | (probe['address'] & 0xfff)
    need(physical == probe['physical'], 'permission_physical_mismatch')
    need(par >> 56 == probe['attr'], 'permission_memory_attribute')
    if probe['shareability'] is not None:
        need((par >> 7) & 3 == probe['shareability'], 'permission_shareability')
    return True


def verify_helper_tail(data):
    need(data == HELPER_TAIL and hashlib.sha256(data).hexdigest() == HELPER_TAIL_SHA,
         'permission_helper_bytes')
    return True

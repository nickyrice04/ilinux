#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Pad only the verified baseline Aura+inline-input layout, offline only.

Unlike frozen 31AH, temporary compressed input may exceed the 16 MiB Aura
runtime slot. The runtime still must fit there; retained Image/initrd data must
be heap-staged by the authenticated public payload parser before pool reuse.
The upstream wrapper must run in the isolated Linux VM, not on macOS.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import plistlib
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('direct31ai_inline_pad', HERE / 'inline.py')
inline = importlib.util.module_from_spec(spec);sys.modules[spec.name] = inline;spec.loader.exec_module(inline)
original_path = HERE.parents[1] / 'direct31ah/aura/pad_boot.py'
inline.require(inline.digest(original_path.read_bytes()) ==
               '0f3b95bc1075c35916963c30c37c4eee6642c2cae95f264ac4744154c84b6acf',
               'frozen original Mach-O reader changed')
pad = inline.trusted_module('direct31ai_frozen_macho_reader', original_path)


def wrapper_identity(data, raw, before):
    """Require the pinned wrapper's metadata, rather than only valid geometry."""
    identity = hashlib.sha256(raw).digest()[:16]
    member = before['segments']['__PRELINK_TEXT']['off']
    for header, flags in ((0, 0), (member, 0x80200001)):
        inline.require(pad.u32(data, header + 24) == flags and pad.u32(data, header + 28) == 0,
                       'wrapper header flags/reserved changed')
    uuid_count = 0
    for command, position, size in before['commands']:
        if command == 0x1b:
            inline.require(size == 24 and data[position + 8:position + 24] == identity,
                           'wrapper UUID disagrees with raw image')
            uuid_count += 1
        elif command == 0x32:
            inline.require(size == 24 and not any(data[position + 8:position + 24]),
                           'wrapper build version changed')
        elif command == pad.SEGMENT:
            inline.require(pad.u32(data, position + 68) == 0, 'wrapper segment flags changed')
        elif command == pad.FILESET:
            inline.require(pad.u32(data, position + 24) == 32 and pad.u32(data, position + 28) == 0,
                           'wrapper member identity layout changed')
    inline.require(uuid_count == 2, 'expected matching outer/member UUIDs')
    info = before['segments']['__PRELINK_INFO']
    try:
        value = plistlib.loads(data[info['off']:info['off'] + info['size']].rstrip(b'\0'))
    except Exception as error:
        raise ValueError('invalid bounded prelink identity plist') from error
    expected = {'KMBuildVersion': 'Aura', 'ManagerVersion': 1,
                'OSPrelinkInfoContainsUUIDs': True, '_PrelinkInfoDictionary': [], '_PrelinkKCID': identity}
    inline.require(value == expected and type(value.get('ManagerVersion')) is int and
                   type(value.get('OSPrelinkInfoContainsUUIDs')) is bool,
                   'prelink identity disagrees with raw image')


def plan(data, raw, image, dtb, initramfs):
    inline.require(len(data) <= 40 * inline.MIB and len(raw) <= inline.MAX_RAW,
                   'bounded input exceeded')
    before = pad.inspect(data)
    wrapper_identity(data, raw, before)
    code = before['code']
    footprint = struct.unpack_from('<Q', raw, 0x818)[0] if len(raw) >= 0x820 else 0
    inline.require(0 < footprint <= inline.SLOT and footprint % inline.PAGE == 0,
                   'invalid runtime footprint')
    inline.require(inline.digest(raw[:footprint]) == inline.BASELINE_SHA256,
                   'exact reviewed baseline runtime required')
    inline.require(footprint + len(dtb) < inline.SLOT,
                   'source DT must remain below earliest possible OS window')
    payload = raw[footprint:]
    payload_info = inline.verify_payload(payload, image, dtb, initramfs)
    inline.require(code['size'] == (len(raw) + inline.PAGE - 1) & ~(inline.PAGE - 1),
                   'wrapper raw extent disagrees')
    file_end = code['off'] + code['size']
    inline.require(data[code['off']:code['off'] + len(raw)] == raw and
                   not any(data[code['off'] + len(raw):file_end]),
                   'wrapper changed raw input or alignment padding')
    growth = pad.CODE_SIZE - code['size']
    inline.require(growth > 0 and len(data) + growth <= pad.MAX_OUTPUT,
                   'already expanded or oversized wrapper')
    patched = bytearray(data)
    old_end = code['vm'] + code['size']
    def put32(position, value):
        inline.require(0 <= value <= 0xffffffff, '32-bit offset overflow')
        struct.pack_into('<I', patched, position, value)
    for command, position, _ in before['commands']:
        if command == pad.SEGMENT:
            vm, _, offset = struct.unpack_from('<3Q', data, position + 24)
            name = data[position + 8:position + 24].split(b'\0', 1)[0]
            if name == b'__TEXT_EXEC':
                struct.pack_into('<Q', patched, position + 32, pad.CODE_SIZE)
                struct.pack_into('<Q', patched, position + 48, pad.CODE_SIZE)
            elif vm >= old_end:
                struct.pack_into('<Q', patched, position + 24, pad.add(vm, growth))
                struct.pack_into('<Q', patched, position + 40, pad.add(offset, growth))
                if pad.u32(data, position + 64):
                    section = position + 72
                    struct.pack_into('<Q', patched, section + 32, pad.add(pad.u64(data, section + 32), growth))
                    put32(section + 48, pad.u32(data, section + 48) + growth)
        elif command == pad.FIXUPS:
            inline.require(pad.u32(data, position + 8) >= file_end, 'fixups precede movable tail')
            put32(position + 8, pad.u32(data, position + 8) + growth)
    head, tail = bytes(patched[:file_end]), bytes(patched[file_end:])
    after = pad.inspect(head, len(data) + growth)
    inline.require(after['entry'] == before['entry'] and
                   head[code['off']:file_end] == data[code['off']:file_end],
                   'padding changed entry/raw bytes')
    return head, tail, growth, {
        'schema': 'ilinux-direct31ai-inline-window-v1', 'scope': 'OFFLINE_LAYOUT_ONLY',
        'baseline_aura_sha256': inline.BASELINE_SHA256, 'aura_runtime_bytes': footprint,
        'temporary_inline_bytes': len(payload), 'raw_inline_bytes': len(raw),
        'raw_inline_sha256': inline.digest(raw), 'payload': payload_info,
        'original_bytes': len(data), 'original_sha256': inline.digest(data),
        'output_bytes': len(data) + growth, 'padding_bytes': growth,
        'window_bytes': inline.POOL, 'aura_slot_bytes': inline.SLOT,
        'expected_kcbz': 0, 'expected_kcrz': code['off'] + pad.CODE_SIZE,
        'wrapper_identity_verified': True,
        'native_tested': False, 'enrolled': False, 'restart_ready': False}


def write_output(source, raw, image, dtb, initramfs, output):
    head, tail, growth, receipt = plan(source, raw, image, dtb, initramfs)
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    complete = False
    try:
        with os.fdopen(descriptor, 'wb', closefd=False) as stream:
            stream.write(head);stream.seek(growth, os.SEEK_CUR);stream.write(tail);stream.flush()
        os.fsync(descriptor)
        data = inline.read_regular(output, pad.MAX_OUTPUT)
        pad.inspect(data)
        inline.require(data[:len(head)] == head and data[-len(tail):] == tail and
                       not any(data[len(head):len(head) + growth]), 'expanded output verification failed')
        receipt['output_sha256'] = inline.digest(data)
        complete = True
        return receipt
    finally:
        os.close(descriptor)
        if not complete:
            Path(output).unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for option in ('macho', 'raw', 'image', 'dtb', 'initramfs', 'output'):
        parser.add_argument('--' + option, type=Path, required=True)
    args = parser.parse_args()
    result = write_output(inline.read_regular(args.macho, 40 * inline.MIB),
                          inline.read_regular(args.raw, inline.MAX_RAW),
                          inline.read_regular(args.image, inline.MAX_IMAGE),
                          inline.read_regular(args.dtb, 4 * inline.MIB),
                          inline.read_regular(args.initramfs, inline.MAX_INITRD), args.output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

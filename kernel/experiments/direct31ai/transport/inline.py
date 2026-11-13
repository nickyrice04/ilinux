#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build and verify bounded, autonomous Aura payload bytes, offline only.

No serial library, USB access, subprocess, MMIO or installation is implemented.
The compressed appended input is temporary; it is not Aura's runtime footprint.
Retained kernel/initrd bytes are staged in the heap by the public loader.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import stat
import struct
import sys
import zlib
from pathlib import Path

MIB = 1 << 20
PAGE = 0x4000
ALIGN = 2 * MIB
SLOT = 16 * MIB
POOL = 128 * MIB
MAX_RAW = 32 * MIB
MAX_IMAGE = 64 * MIB
MAX_INITRD = 8 * MIB
MAX_CPIO = 16 * MIB
END = bytes(64)
TAG = b'aura_initramfs'
BOOTARGS = 'console=tty0 earlycon keep_bootcon rdinit=/init ro loglevel=7 panic=0'
BASELINE_SHA256 = '2d272aa2b5551d27458826e88b3bdaf86684e2b4fff3aad4876de7021a1caaf3'


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def trusted_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ORIGINAL = Path(__file__).resolve().parents[2] / 'direct31ah/linux'
fdt = trusted_module('direct31ai_original_fdt', ORIGINAL / 'fdt_read.py')
dtcheck = trusted_module('direct31ai_original_dtcheck', ORIGINAL / 'check_dtb.py')


def read_regular(path, bound):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= bound,
                'not a bounded regular input')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            content = stream.read(bound + 1)
        require(len(content) == info.st_size, 'input size changed')
        return content
    finally:
        os.close(descriptor)


def qualify_source(root):
    pins = json.loads(Path(__file__).with_name('source-pins.json').read_text())
    for name, expected in pins['git_blobs'].items():
        content = read_regular(root / name, 4 * MIB)
        actual = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
        require(actual == expected, 'public source pin mismatch: ' + name)
    return pins


def gzip_bytes(data):
    # Explicit header avoids gzip.compress(mtime=0)'s platform-specific OS byte.
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    body = compressor.compress(data) + compressor.flush()
    return bytes.fromhex('1f8b08000000000002ff') + body + struct.pack('<II', zlib.crc32(data), len(data))


def gunzip_member(data, bound):
    require(data.startswith(b'\x1f\x8b\x08'), 'expected gzip member')
    decoder = zlib.decompressobj(31)
    try:
        plain = decoder.decompress(data, bound + 1)
    except zlib.error as error:
        raise ValueError('gzip checksum/stream failure') from error
    require(len(plain) <= bound and decoder.eof and not decoder.unconsumed_tail,
            'truncated or oversized gzip member')
    return plain, len(data) - len(decoder.unused_data)


def image_info(data):
    require(64 <= len(data) <= MAX_IMAGE and data[56:60] == b'ARM\x64', 'not a bounded arm64 Image')
    offset, memory, flags = struct.unpack_from('<3Q', data, 8)
    require(0 < memory <= MAX_IMAGE and len(data) <= memory, 'Image memory extent invalid')
    require(offset <= POOL - memory, 'Image offset/memory exceeds execution pool')
    require(((flags >> 1) & 3) == 2, 'Image must use 16 KiB pages')
    require(not flags & 1, 'Image must be little endian')
    return {'bytes': len(data), 'sha256': digest(data), 'memory_bytes': memory, 'text_offset': offset}


def dt_info(data):
    report = dtcheck.inspect(data)
    require(report['drom_properties'] == 0, 'per-unit DROM is forbidden')
    root, _, _ = fdt.parse(data)
    disabled = 0
    for _, node in fdt.walk(root):
        require('apple,j613-25g83-profile' not in node.props, 'unexpected special DT profile')
        compatibles = fdt.text(node.props['compatible']) if 'compatible' in node.props else []
        if any(value.startswith(('apple,t6050-usb4-', 'apple,t6050-sep', 'apple,t6050-isp'))
               for value in compatibles):
            require(node.props.get('status') == b'disabled\0', 'unqualified native peripheral enabled')
            disabled += 1
    return {'bytes': len(data), 'sha256': digest(data), 'cpu_nodes': report['cpu_count'],
            'cluster_core_types': report['cluster_core_types'], 'drom_properties': 0,
            'unqualified_nodes_disabled': disabled, 'propertyless_profile_rank': 1}


def initrd_info(compressed):
    require(0 < len(compressed) <= MAX_INITRD, 'compressed initramfs exceeds bound')
    content, used = gunzip_member(compressed, MAX_CPIO)
    require(used == len(compressed), 'trailing initramfs gzip member/data')
    entries = []
    position = 0
    executable = None
    while True:
        require(position + 110 <= len(content) and content[position:position + 6] == b'070701',
                'expected bounded newc record')
        fields = [content[position + 6 + i * 8:position + 14 + i * 8] for i in range(13)]
        require(all(len(field) == 8 and all(byte in b'0123456789abcdefABCDEF' for byte in field)
                    for field in fields), 'noncanonical newc numeric field')
        values = [int(field, 16) for field in fields]
        _, mode, uid, gid, links, _, size, devmajor, devminor, rdevmajor, rdevminor, namesize, check = values
        require(1 <= namesize <= 64 and position + 110 + namesize <= len(content), 'invalid newc name')
        namebytes = content[position + 110:position + 110 + namesize]
        require(namebytes[-1:] == b'\0' and b'\0' not in namebytes[:-1], 'invalid newc name terminator')
        name = namebytes[:-1].decode('ascii')
        position = (position + 110 + namesize + 3) & ~3
        require(position + size <= len(content), 'newc data exceeds archive')
        data = content[position:position + size]
        position = (position + size + 3) & ~3
        require(not any((uid, gid, devmajor, devminor, rdevmajor, rdevminor, check)) and links == 1,
                'unexpected newc ownership/device/check fields')
        if name == 'TRAILER!!!':
            require(size == 0 and mode == 0 and not any(content[position:]), 'invalid newc trailer')
            break
        require(name not in entries and len(entries) < 5, 'duplicate/excess initramfs entries')
        if name in ('dev', 'proc', 'sys', 'run'):
            require(mode == 0o040755 and not data, 'unexpected initramfs directory')
        elif name == 'init':
            require(mode == 0o100755 and len(data) >= 64, 'unexpected init mode/size')
            require(data[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<H', data, 18)[0] == 183,
                    'init is not ELF64 AArch64')
            require(struct.unpack_from('<H', data, 16)[0] in (2, 3) and
                    struct.unpack_from('<H', data, 52)[0] == 64, 'invalid init ELF type/header')
            phoff = struct.unpack_from('<Q', data, 32)[0]
            phsize, phnum = struct.unpack_from('<HH', data, 54)
            require(phsize == 56 and 1 <= phnum <= 128 and phoff >= 64 and
                    phoff + phsize * phnum <= len(data), 'invalid init program table')
            loads = 0
            for i in range(phnum):
                kind, _, off, _, _, filebytes, membytes, _ = struct.unpack_from('<II6Q', data, phoff + i * phsize)
                require(kind != 3, 'dynamic init requires an interpreter')
                if kind == 1:
                    require(off + filebytes <= len(data) and filebytes <= membytes, 'invalid init load')
                    loads += 1
            require(loads > 0, 'no init load segment')
            executable = {'bytes': len(data), 'sha256': digest(data)}
        else:
            raise ValueError('unexpected initramfs file')
        entries.append(name)
    require(entries == ['dev', 'proc', 'sys', 'run', 'init'] and executable, 'incomplete RAM root')
    return {'bytes': len(compressed), 'sha256': digest(compressed), 'cpio_bytes': len(content),
            'entries': entries, 'init': executable, 'modules': False}


def make_payload(image, dtb, initrd):
    image_info(image); dt_info(dtb); initrd_info(initrd)
    envelope = TAG + struct.pack('<I', len(initrd)) + initrd
    stream = dtb + gzip_bytes(image) + gzip_bytes(envelope) + ('chosen.bootargs=' + BOOTARGS + '\n').encode() + END
    require(len(stream) <= MAX_RAW, 'payload exceeds bound')
    verify_payload(stream, image, dtb, initrd)
    return stream


def verify_payload(stream, image, dtb, initrd):
    require(len(stream) <= MAX_RAW and stream.startswith(dtb), 'DT must be the exact first payload')
    image_info(image); dt_info(dtb); initrd_info(initrd)
    position = len(dtb)
    decoded, consumed = gunzip_member(stream[position:], MAX_IMAGE)
    require(decoded == image, 'kernel bytes differ from exact Image')
    position += consumed
    envelope_offset = position
    envelope, consumed = gunzip_member(stream[position:], MAX_INITRD + len(TAG) + 4)
    require(envelope.startswith(TAG) and len(envelope) >= len(TAG) + 4, 'missing tagged initramfs')
    declared = struct.unpack_from('<I', envelope, len(TAG))[0]
    require(declared == len(initrd) and envelope[len(TAG) + 4:] == initrd, 'initramfs length/bytes differ')
    position += consumed
    ending = ('chosen.bootargs=' + BOOTARGS + '\n').encode() + END
    require(stream[position:] == ending, 'unexpected config, order or trailing payload bytes')
    return {'dtb_offset': 0, 'kernel_gzip_offset': len(dtb),
            'initrd_envelope_gzip_offset': envelope_offset,
            'config_offset': position, 'payload_bytes': len(stream), 'payload_sha256': digest(stream)}


def layout_model(aura_base, runtime_bytes, raw_bytes, heap_base, armed_start, armed_end,
                 image, initrd_bytes, bootargs_range, retained_ranges=()):
    """Pure software gate for hypothetical addresses; never reads live registers."""
    require(all(isinstance(x, int) and 0 <= x < 1 << 64 for x in
                (aura_base, runtime_bytes, raw_bytes, heap_base, armed_start, armed_end, initrd_bytes)),
            'invalid model integer')
    require(aura_base % PAGE == 0 and 0 < runtime_bytes <= SLOT and runtime_bytes <= raw_bytes <= MAX_RAW,
            'invalid Aura runtime/input extent')
    window = (aura_base + SLOT + ALIGN - 1) & ~(ALIGN - 1)
    end = window + POOL
    require(end < 1 << 64 and armed_start <= aura_base and armed_end >= end, 'armed range too small')
    require(heap_base >= end and heap_base % PAGE == 0, 'heap must start beyond execution pool')
    def overlaps(start, size):
        require(start >= 0 and size > 0 and start + size < 1 << 64, 'invalid retained range')
        return start < end and start + size > window
    require(not overlaps(*bootargs_range), 'boot arguments overlap execution pool')
    for reserved in retained_ranges:
        require(not overlaps(*reserved), 'firmware/read-only range overlaps execution pool')
    require(image['text_offset'] + image['memory_bytes'] <= POOL, 'kernel cannot fit pool')
    kernel_staging = (heap_base + ALIGN - 1) & ~(ALIGN - 1)
    initrd_staging = (kernel_staging + image['memory_bytes'] + ALIGN - 1) & ~(ALIGN - 1)
    require(initrd_staging + initrd_bytes < 1 << 64, 'staging overflow')
    return {'scope': 'SYNTHETIC_LAYOUT_MODEL_ONLY', 'pool_start': window, 'pool_bytes': POOL,
            'kernel_final': window + image['text_offset'], 'kernel_staging': kernel_staging,
            'initrd_staging': initrd_staging, 'raw_input_overlaps_future_pool': aura_base + raw_bytes > window,
            'retained_initrd_outside_pool': True, 'native_qualified': False}


def build(aura, image, dtb, initrd):
    require(digest(aura) == BASELINE_SHA256, 'exact reviewed baseline Aura required')
    require(aura[0x808:0x810] == b'AURALOAD', 'missing Aura load header')
    runtime = struct.unpack_from('<Q', aura, 0x818)[0]
    require(runtime == len(aura) and runtime <= SLOT and runtime % PAGE == 0,
            'unexpected Aura footprint or preexisting payload')
    require(runtime + len(dtb) < SLOT, 'DT input must remain below earliest pool start')
    payload = make_payload(image, dtb, initrd)
    raw = aura + payload
    require(len(raw) <= MAX_RAW, 'raw inline image exceeds bound')
    plan = {'schema': 'ilinux-direct31ai-inline-v1', 'scope': 'OFFLINE_INPUT_FORMAT_ONLY',
            'route': 'autonomous-inline-baseline', 'baseline_aura_sha256': digest(aura),
            'aura_runtime_bytes': runtime, 'raw_inline_bytes': len(raw), 'raw_inline_sha256': digest(raw),
            'payload': verify_payload(payload, image, dtb, initrd), 'Image': image_info(image),
            'dtb': dt_info(dtb), 'initramfs': initrd_info(initrd), 'bootargs': BOOTARGS,
            'codec': {'python': sys.version.split()[0], 'zlib': zlib.ZLIB_VERSION},
            'runtime_requirements': ['direct Aura entry; confined OS enters at EL2',
                '128 MiB armed execution window after 16 MiB Aura slot',
                'heap, boot_args, firmware retained ranges outside execution pool',
                'native DT memory/framebuffer/spin-table/window fixups succeed',
                'NVMe shutdown, CPU setup, mitigations, PCIe and DAPF handoff succeed',
                'main final pending-call, NVMe, USB/exception/display cleanup and vectoring succeed'],
            'retained_payload_locations': {'Image': 'decompressed heap, then kboot moves into pool',
                'initramfs': 'outer-gzip envelope decompressed into heap',
                'dtb': 'inline below Aura slot limit, then kboot copies/fixes into heap'},
            'new_padding_required': True, 'existing_31ah_padding_input_limit_satisfied': len(raw) <= SLOT,
            'linux_usb_gadget_required': False, 'proxy_connection_required': False,
            'native_tested': False, 'enrolled': False, 'restart_ready': False}
    return raw, payload, plan


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--source-tree', type=Path, required=True)
    parser.add_argument('--aura', type=Path, required=True)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--dtb', type=Path, required=True)
    parser.add_argument('--initramfs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pins = qualify_source(args.source_tree)
    raw, payload, plan = build(read_regular(args.aura, SLOT), read_regular(args.image, MAX_IMAGE),
                               read_regular(args.dtb, 4 * MIB), read_regular(args.initramfs, MAX_INITRD))
    plan['upstream_commit'] = pins['commit']
    plan['source_pins_sha256'] = digest(Path(__file__).with_name('source-pins.json').read_bytes())
    args.output.mkdir(parents=True, exist_ok=False)
    for name, data in [('aura-inline.bin', raw), ('payload.bin', payload),
                       ('plan.json', (json.dumps(plan, indent=2) + '\n').encode())]:
        with (args.output / name).open('xb') as stream:
            stream.write(data)
    print(json.dumps({'status': 'OFFLINE_INPUTS_BUILT', 'raw_inline_bytes': len(raw),
                      'native_tested': False, 'restart_ready': False}))


if __name__ == '__main__':
    main()

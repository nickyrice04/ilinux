#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original host-safe refusal tests. Synthetic executable bytes are never run."""
import gzip
import importlib.util
import struct
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('direct31ai_inline_tests', HERE / 'inline.py')
tool = importlib.util.module_from_spec(spec);sys.modules[spec.name] = tool;spec.loader.exec_module(tool)
ram = tool.trusted_module('direct31ai_original_ram_fixture', tool.ORIGINAL / 'make_initramfs.py')


def image_fixture():
    data = bytearray(0x10000)
    struct.pack_into('<3Q', data, 8, 0, 0x20000, 4)
    data[56:60] = b'ARM\x64'
    return bytes(data)


def elf_fixture():
    data = bytearray(256)
    data[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<HH', data, 16, 2, 183)
    struct.pack_into('<Q', data, 32, 64)
    struct.pack_into('<HHH', data, 52, 64, 56, 1)
    struct.pack_into('<II6Q', data, 64, 1, 5, 0, 0, 0, len(data), len(data), 0x1000)
    return bytes(data)


def tree_fixture():
    root = tool.fdt.Node('', {'compatible': b'apple,j716c\0apple,t6050\0'})
    cpus = tool.fdt.Node('cpus')
    for index, mpidr in enumerate(tool.dtcheck.EXPECTED):
        cpus.children.append(tool.fdt.Node('cpu@%x' % mpidr, {
            'reg': struct.pack('>Q', mpidr), 'enable-method': b'spin-table\0',
            'cpu-release-addr': bytes(8), 'capacity-dmips-mhz': struct.pack('>I', 794 if index < 12 else 1024)}))
    root.children.append(cpus)
    return tool.fdt.encode(root, [], 0)


class InlineTests(unittest.TestCase):
    def setUp(self):
        self.image = image_fixture();self.dtb = tree_fixture();self.initrd = ram.build(elf_fixture())
        self.payload = tool.make_payload(self.image, self.dtb, self.initrd)

    def changed_tree(self, change):
        root, reserved, boot = tool.fdt.parse(self.dtb);change(root)
        return tool.fdt.encode(root, reserved, boot)

    def cpio_with_init(self, executable, mode=0o100755, extra=None):
        buf = b''.join(ram.newc_entry(name, b'', 0o040755, i + 1)
                       for i, name in enumerate(('dev','proc','sys','run')))
        buf += ram.newc_entry('init', executable, mode, 5)
        if extra:buf += ram.newc_entry(extra, b'fixture', 0o100600, 6)
        return tool.gzip_bytes(buf + ram.newc_entry('TRAILER!!!', b'', 0, 7))

    def model(self, **changes):
        base = 0x40000000  # Synthetic only, not a target address.
        args = dict(aura_base=base, runtime_bytes=4 * tool.MIB, raw_bytes=20 * tool.MIB,
                    heap_base=base + 160 * tool.MIB, armed_start=base - tool.PAGE,
                    armed_end=base + 150 * tool.MIB, image=tool.image_info(self.image),
                    initrd_bytes=len(self.initrd), bootargs_range=(base + 155 * tool.MIB, tool.PAGE))
        args.update(changes)
        return tool.layout_model(**args)

    def test_exact_payload_roundtrip(self):
        report = tool.verify_payload(self.payload, self.image, self.dtb, self.initrd)
        self.assertEqual(report['payload_sha256'], tool.digest(self.payload))
        self.assertEqual(report['kernel_gzip_offset'], len(self.dtb))

    def test_deterministic_header(self):
        encoded = tool.gzip_bytes(b'owned fixture')
        self.assertEqual(encoded[:10], bytes.fromhex('1f8b08000000000002ff'))
        self.assertEqual(tool.gunzip_member(encoded, 100), (b'owned fixture', len(encoded)))

    def test_noncanonical_compression_positions_are_actual(self):
        gz = gzip.compress(self.image, compresslevel=1, mtime=0)
        envelope = tool.TAG + struct.pack('<I', len(self.initrd)) + self.initrd
        data = self.dtb + gz + tool.gzip_bytes(envelope) + ('chosen.bootargs=' + tool.BOOTARGS + '\n').encode() + tool.END
        result = tool.verify_payload(data, self.image, self.dtb, self.initrd)
        self.assertEqual(result['initrd_envelope_gzip_offset'], len(self.dtb) + len(gz))

    def test_kernel_bytes_changed(self):
        changed = bytearray(self.image);changed[-1] ^= 1
        with self.assertRaises(ValueError):tool.verify_payload(self.payload, bytes(changed), self.dtb, self.initrd)

    def test_gzip_crc(self):
        changed = bytearray(tool.gzip_bytes(b'owned'));changed[-8] ^= 1
        with self.assertRaises(ValueError):tool.gunzip_member(bytes(changed), 100)

    def test_gzip_truncated(self):
        with self.assertRaises(ValueError):tool.gunzip_member(tool.gzip_bytes(b'owned')[:-1], 100)

    def test_gzip_bomb_bound(self):
        with self.assertRaises(ValueError):tool.gunzip_member(tool.gzip_bytes(bytes(10000)), 100)

    def test_wrong_pages(self):
        data = bytearray(self.image);struct.pack_into('<Q', data, 24, 2)
        with self.assertRaises(ValueError):tool.image_info(bytes(data))

    def test_short_memory_header(self):
        data = bytearray(self.image);struct.pack_into('<Q', data, 16, len(data) - 1)
        with self.assertRaises(ValueError):tool.image_info(bytes(data))

    def test_kernel_pool_overflow(self):
        data = bytearray(self.image);struct.pack_into('<Q', data, 8, tool.POOL)
        with self.assertRaises(ValueError):tool.image_info(bytes(data))

    def test_wrong_board(self):
        data = self.changed_tree(lambda root: root.props.update(compatible=b'apple,j716x\0apple,t6050\0'))
        with self.assertRaises(ValueError):tool.dt_info(data)

    def test_changed_core_capacity(self):
        data = self.changed_tree(lambda root: root.children[0].children[0].props.update(
            {'capacity-dmips-mhz': struct.pack('>I', 1024)}))
        with self.assertRaises(ValueError):tool.dt_info(data)

    def test_drom_refused(self):
        data = self.changed_tree(lambda root: root.props.update({'apple,thunderbolt-drom': b'owned fixture'}))
        with self.assertRaises(ValueError):tool.dt_info(data)

    def test_special_firmware_profile_refused(self):
        data = self.changed_tree(lambda root: root.children.append(tool.fdt.Node('dcp',
                                  {'apple,j613-25g83-profile': bytes(4)})))
        with self.assertRaises(ValueError):tool.dt_info(data)

    def test_unqualified_peripheral_enabled(self):
        data = self.changed_tree(lambda root: root.children.append(tool.fdt.Node('sep',
                                  {'compatible': b'apple,t6050-sep\0'})))
        with self.assertRaises(ValueError):tool.dt_info(data)

    def test_disabled_peripheral_is_accepted(self):
        data = self.changed_tree(lambda root: root.children.append(tool.fdt.Node('sep',
                        {'compatible': b'apple,t6050-sep\0', 'status': b'disabled\0'})))
        self.assertEqual(tool.dt_info(data)['unqualified_nodes_disabled'], 1)

    def test_initrd_extra_member(self):
        with self.assertRaises(ValueError):tool.initrd_info(self.initrd + self.initrd)

    def test_unexpected_initrd_file(self):
        with self.assertRaises(ValueError):tool.initrd_info(self.cpio_with_init(elf_fixture(), extra='extra'))

    def test_init_symlink_refused(self):
        with self.assertRaises(ValueError):tool.initrd_info(self.cpio_with_init(elf_fixture(), mode=0o120777))

    def test_dynamic_init_refused(self):
        exe = bytearray(elf_fixture());struct.pack_into('<I', exe, 64, 3)
        with self.assertRaises(ValueError):tool.initrd_info(self.cpio_with_init(bytes(exe)))

    def test_invalid_newc_length(self):
        plain, _ = tool.gunzip_member(self.initrd, tool.MAX_CPIO)
        changed = bytearray(plain);changed[94:102] = b'ffffffff'
        with self.assertRaises(ValueError):tool.initrd_info(tool.gzip_bytes(bytes(changed)))

    def reject_numeric_spellings(self, spellings):
        plain, _ = tool.gunzip_member(self.initrd, tool.MAX_CPIO)
        for field in range(13):
            for spelling in spellings:
                with self.subTest(field=field, spelling=spelling):
                    self.assertEqual(len(spelling), 8)
                    changed = bytearray(plain)
                    changed[6 + field * 8:14 + field * 8] = spelling
                    with self.assertRaisesRegex(ValueError, 'noncanonical newc numeric field'):
                        tool.initrd_info(tool.gzip_bytes(bytes(changed)))

    def test_signed_newc_numbers_refused_in_all_fields(self):
        self.reject_numeric_spellings((b'+0000000', b'-0000000'))

    def test_whitespace_newc_numbers_refused_in_all_fields(self):
        self.reject_numeric_spellings((b' 0000000', b'0000000 ', b'\t0000000'))

    def test_prefixed_or_nonhex_newc_numbers_refused_in_all_fields(self):
        self.reject_numeric_spellings((b'0x000000', b'0X000000', b'0_000000', b'0000000g', b'\xff0000000'))

    def test_truncated_newc_numeric_headers_refused(self):
        plain, _ = tool.gunzip_member(self.initrd, tool.MAX_CPIO)
        for length in (6, 13, 101, 109):
            with self.subTest(header_bytes=length):
                with self.assertRaises(ValueError):tool.initrd_info(tool.gzip_bytes(plain[:length]))

    def test_uppercase_newc_hex_is_accepted(self):
        plain, _ = tool.gunzip_member(self.initrd, tool.MAX_CPIO)
        changed = bytearray(plain);changed[6:110] = changed[6:110].upper()
        result = tool.initrd_info(tool.gzip_bytes(bytes(changed)))
        self.assertEqual(result['entries'], ['dev','proc','sys','run','init'])

    def test_tag_length_disagrees(self):
        positions = tool.verify_payload(self.payload, self.image, self.dtb, self.initrd)
        start = positions['initrd_envelope_gzip_offset'];end = positions['config_offset']
        wrong = tool.gzip_bytes(tool.TAG + struct.pack('<I', len(self.initrd) + 1) + self.initrd)
        with self.assertRaises(ValueError):tool.verify_payload(self.payload[:start] + wrong + self.payload[end:],
                                                             self.image, self.dtb, self.initrd)

    def test_additional_config_refused(self):
        changed = self.payload[:-len(tool.END)] + b'boot=unqualified\n' + tool.END
        with self.assertRaises(ValueError):tool.verify_payload(changed, self.image, self.dtb, self.initrd)

    def test_missing_terminator_refused(self):
        with self.assertRaises(ValueError):tool.verify_payload(self.payload[:-1], self.image, self.dtb, self.initrd)

    def test_temporary_input_may_overlap_but_retained_initrd_does_not(self):
        result = self.model()
        self.assertTrue(result['raw_input_overlaps_future_pool'])
        self.assertGreaterEqual(result['initrd_staging'], result['pool_start'] + result['pool_bytes'])

    def test_insufficient_armed_range(self):
        with self.assertRaises(ValueError):self.model(armed_end=0x40000000 + 140 * tool.MIB)

    def test_heap_overlaps_pool(self):
        with self.assertRaises(ValueError):self.model(heap_base=0x40000000 + 100 * tool.MIB)

    def test_bootargs_overlaps_pool(self):
        with self.assertRaises(ValueError):self.model(bootargs_range=(0x40000000 + 20 * tool.MIB, tool.PAGE))

    def test_firmware_ro_overlaps_pool(self):
        with self.assertRaises(ValueError):self.model(retained_ranges=((0x40000000 + 20 * tool.MIB, tool.PAGE),))

    def test_runtime_exceeds_slot(self):
        with self.assertRaises(ValueError):self.model(runtime_bytes=17 * tool.MIB)

    def test_wrong_baseline_hash_refused(self):
        with self.assertRaises(ValueError):tool.build(bytes(4096), self.image, self.dtb, self.initrd)

    def test_symlink_input_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory);(p/'input').write_bytes(b'owned');(p/'link').symlink_to(p/'input')
            with self.assertRaises(OSError):tool.read_regular(p/'link', 100)


if __name__ == '__main__':
    unittest.main(verbosity=2)

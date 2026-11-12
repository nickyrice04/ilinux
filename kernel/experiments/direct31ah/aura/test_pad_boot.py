#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run in Linux VM: original padding checks with the pinned public wrapper."""
import argparse
import hashlib
import importlib.util
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

# Keep external code loading explicit. The parent never runs this on macOS.
parser = argparse.ArgumentParser()
parser.add_argument('--wrapper', type=Path, required=True)
args, remaining = parser.parse_known_args()
if sys.platform != 'linux':
    raise SystemExit('Linux VM required for public dependency execution')
blob = args.wrapper.read_bytes()
if hashlib.sha256(blob).hexdigest() != '3e8fff2c09179fc34f89e6ef453e29f0b3bd7b488be296e9afce2257b67642d0':
    raise SystemExit('pinned wrapper hash mismatch')

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

wrapper = module('aura_wrapper', args.wrapper)
pad = module('ilinux_pad', Path(__file__).with_name('pad_boot.py'))


def fixture(size=0x40000):
    raw = bytearray(size)
    raw[0x808:0x810] = b'AURALOAD'
    struct.pack_into('<Q', raw, 0x818, 0x100000)
    raw[0x2000:0x2010] = b'OWNED-TEST-DATA!'
    return wrapper.wrap(bytes(raw))


class PaddingTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture()
        self.info = pad.inspect(self.data)

    def reject(self, mutated):
        with self.assertRaises((ValueError, UnicodeError, struct.error)):
            pad.plan(mutated)

    def first(self, cmd, member=False):
        cmds = self.info['commands']
        found = [(c,p,n) for c,p,n in cmds if c == cmd]
        return found[-1 if member else 0][1]

    def altered(self, offset, value, width=4):
        b=bytearray(self.data)
        struct.pack_into('<I' if width==4 else '<Q', b, offset, value)
        return bytes(b)

    def test_layout_and_entry_stay_linear(self):
        head, tail, growth, receipt = pad.plan(self.data)
        after=pad.inspect(head,receipt['output_bytes'])
        self.assertEqual(after['entry'],self.info['entry'])
        self.assertEqual(after['code']['size'],pad.CODE_SIZE)
        self.assertEqual(receipt['expected_kcbz'],0)
        self.assertEqual(receipt['window_bytes'],128<<20)
        self.assertEqual(receipt['expected_kcrz'],after['code']['off']+pad.CODE_SIZE)
        end=self.info['code']['off']+self.info['code']['size']
        self.assertEqual(head[self.info['code']['off']:],self.data[self.info['code']['off']:end])
        self.assertEqual(tail,self.data[end:])

    def test_unaligned_raw_input(self):
        pad.plan(fixture(0x40001))

    def test_larger_raw_input(self):
        pad.plan(fixture(3<<20))

    def test_write_and_full_reparse(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';dest=Path(tmp)/'padded'
            source.write_bytes(self.data)
            receipt=pad.pad_file(source,dest)
            self.assertEqual(dest.stat().st_size,receipt['output_bytes'])
            b=dest.read_bytes()
            self.assertEqual(hashlib.sha256(b).hexdigest(),receipt['output_sha256'])
            self.assertEqual(pad.inspect(b)['code']['size'],pad.CODE_SIZE)
            with self.assertRaises(ValueError):pad.plan(b)

    def test_wrong_magic(self): self.reject(self.altered(0,0))
    def test_wrong_cpu(self): self.reject(self.altered(4,7))
    def test_wrong_kind(self): self.reject(self.altered(12,2))
    def test_unknown_command(self): self.reject(self.altered(32,0xdead))
    def test_bad_command_length(self): self.reject(self.altered(36,7))
    def test_command_count(self): self.reject(self.altered(16,0xffffffff))

    def test_no_boot_exec_segment(self):
        b=bytearray(self.data);p=self.info['code']['command']
        b[p+8:p+24]=b'__TEXT_BOOT_EXEC'
        self.reject(bytes(b))

    def test_wrong_entry(self):
        p=self.first(pad.THREAD)
        self.reject(self.altered(p+16+32*8,self.info['entry']+4,8))

    def test_member_entry_disagrees(self):
        p=self.first(pad.THREAD,True)
        self.reject(self.altered(p+16+16*8,0,8))

    def test_duplicate_segment(self):
        b=bytearray(self.data);p=self.info['code']['command']
        b[p+8:p+24]=b'__TEXT\0'.ljust(16,b'\0');self.reject(bytes(b))

    def test_unbacked_code(self):
        p=self.info['code']['command'];self.reject(self.altered(p+48,0,8))

    def test_escaping_file_offset(self):
        p=self.info['code']['command'];self.reject(self.altered(p+40,0xffffffffffffc000,8))

    def test_runtime_memory_overflow(self):
        p=self.info['code']['off']+0x818;self.reject(self.altered(p,pad.SLOT+1,8))

    def test_missing_load_header(self):
        b=bytearray(self.data);p=self.info['code']['off']+0x808;b[p:p+8]=b'NOTAURA!'
        self.reject(bytes(b))

    def test_nonempty_chained_fixups(self):
        p=self.info['segments']['__LINKEDIT']['off'];self.reject(self.altered(p+32,1))

    def test_member_size_disagrees(self):
        p=[p for c,p,n in self.info['commands'] if c==pad.SEGMENT and
           self.data[p+8:p+24].rstrip(b'\0')==b'__TEXT_EXEC'][-1]
        self.reject(self.altered(p+32,0x80000,8))

    def test_member_header_overlaps_code(self):
        p=[p for c,p,n in self.info['commands'] if c==pad.SEGMENT and
           self.data[p+8:p+24].rstrip(b'\0')==b'__TEXT'][-1]
        b=bytearray(self.data)
        struct.pack_into('<Q',b,p+32,0x10000)
        struct.pack_into('<Q',b,p+48,0x10000)
        self.reject(bytes(b))

    def test_existing_output_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'src').write_bytes(self.data);(p/'dst').write_bytes(b'KEEP')
            with self.assertRaises(FileExistsError):pad.pad_file(p/'src',p/'dst')
            self.assertEqual((p/'dst').read_bytes(),b'KEEP')

    def test_symlink_input_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'src').write_bytes(self.data);(p/'link').symlink_to(p/'src')
            with self.assertRaises(OSError):pad.pad_file(p/'link',p/'out')

    def test_symlink_output_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'src').write_bytes(self.data);(p/'dst').write_bytes(b'KEEP')
            (p/'link').symlink_to(p/'dst')
            with self.assertRaises(OSError):pad.pad_file(p/'src',p/'link')
            self.assertEqual((p/'dst').read_bytes(),b'KEEP')


if __name__=='__main__':
    unittest.main(argv=[sys.argv[0],*remaining],verbosity=2)

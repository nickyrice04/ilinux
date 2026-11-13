#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original synthetic format/refusal tests; no public wrapper or code runs.

The independent fixture encoder implements the documented Mach-O record format.
Only a unittest context substitutes a synthetic baseline digest. Production
CLI admission retains the exact reviewed Aura digest with no override option.
"""
import hashlib
import importlib.util
import plistlib
import random
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    value = importlib.util.module_from_spec(spec);sys.modules[name] = value;spec.loader.exec_module(value)
    return value

adapter = module('direct31ai_extender_tests', 'extend_exec.py')
fixtures = module('direct31ai_input_fixtures', 'test_inline.py')
PAGE = 0x4000
VM = 0xfffffe0007004000


def synthetic_baseline(size=0x10000):
    data = bytearray(size)
    data[0x808:0x810] = b'AURALOAD'
    struct.pack_into('<Q', data, 0x818, size)
    return bytes(data)


def fixture_wrapper(raw):
    """MIT test encoder of metadata only; payload bytes are nonexecuted data."""
    def segment(name, offset, size, protection, section=None):
        out = struct.pack('<II16s4Q4I', 0x19, 72 + (80 if section else 0), name.encode(),
                          VM + offset, size, offset, size, protection, protection, bool(section), 0)
        if section:
            secname, secbytes, flags = section
            out += struct.pack('<16s16s2Q8I', secname.encode(), name.encode(), VM + offset,
                               secbytes, offset, 0, 0, 0, flags, 0, 0, 0)
        return out
    def header(kind, flags, commands):
        data = b''.join(commands)
        return struct.pack('<8I', 0xfeedfacf, 0x0100000c, 0xc0000002, kind,
                           len(commands), len(data), flags, 0) + data
    identity = hashlib.sha256(raw).digest()[:16]
    info = plistlib.dumps({'KMBuildVersion':'Aura','ManagerVersion':1,
                          'OSPrelinkInfoContainsUUIDs':True,'_PrelinkInfoDictionary':[],
                          '_PrelinkKCID':identity}, sort_keys=True)
    code_size = (len(raw) + PAGE - 1) & ~(PAGE - 1)
    info_off = 0x10000 + code_size
    data_off, link_off = info_off + PAGE, info_off + 2 * PAGE
    segments = [segment('__TEXT',0,0x8000,1),
                segment('__PRELINK_TEXT',0x8000,0x8000,1,('__text',0x8000,0x80000400)),
                segment('__TEXT_EXEC',0x10000,code_size,5),
                segment('__PRELINK_INFO',info_off,PAGE,3,('__info',len(info),0)),
                segment('__DATA',data_off,PAGE,3),segment('__LINKEDIT',link_off,PAGE,1)]
    registers = [0] * 34;registers[16] = VM + 0x10000;registers[32] = VM + 0x10800
    common = [struct.pack('<II16s',0x1b,24,identity),struct.pack('<6I',0x32,24,0,0,0,0),
              struct.pack('<4I34Q',5,288,6,68,*registers)]
    member_name = b'com.apple.kernel'
    member_size = (32 + len(member_name) + 1 + 7) & ~7
    member = struct.pack('<IIQQII',0x80000035,member_size,VM+0x8000,0x8000,32,0)
    member += member_name.ljust(member_size-32,b'\0')
    outer = header(12,0,common+[struct.pack('<4I',0x80000034,16,link_off,56)]+segments+[member])
    inner = header(2,0x80200001,[segment('__TEXT',0x8000,0x8000,1),segments[2],segments[4],segments[5],
                   struct.pack('<6I',2,24,0,0,0,0),struct.pack('<20I',0xb,80,*([0]*18))]+common)
    data = bytearray(link_off+PAGE)
    data[:len(outer)] = outer;data[0x8000:0x8000+len(inner)] = inner
    data[0x10000:0x10000+len(raw)] = raw;data[info_off:info_off+len(info)] = info
    data[link_off:link_off+56] = struct.pack('<14I',0,28,56,56,0,1,0,6,0,0,0,0,0,0)
    return bytes(data)


class ExtenderTests(unittest.TestCase):
    def setUp(self):
        self.image = fixtures.image_fixture();self.dtb = fixtures.tree_fixture()
        self.initrd = fixtures.ram.build(fixtures.elf_fixture())
        self.baseline = synthetic_baseline()
        self.payload = adapter.inline.make_payload(self.image,self.dtb,self.initrd)
        self.raw = self.baseline + self.payload;self.source = fixture_wrapper(self.raw)
        patch = mock.patch.object(adapter.inline,'BASELINE_SHA256',adapter.inline.digest(self.baseline))
        patch.start();self.addCleanup(patch.stop)
        self.info = adapter.pad.inspect(self.source)

    def plan(self, source=None, raw=None, image=None, dtb=None, initrd=None):
        return adapter.plan(self.source if source is None else source,self.raw if raw is None else raw,
                            self.image if image is None else image,self.dtb if dtb is None else dtb,
                            self.initrd if initrd is None else initrd)

    def command(self, kind, member=False):
        values = [p for c,p,n in self.info['commands'] if c == kind]
        return values[-1 if member else 0]

    def altered(self, offset, value, width=4):
        data = bytearray(self.source)
        struct.pack_into('<I' if width == 4 else '<Q',data,offset,value)
        return bytes(data)

    def test_valid_metadata_and_raw_preservation(self):
        head,tail,growth,report = self.plan()
        after = adapter.pad.inspect(head,report['output_bytes'])
        self.assertEqual(after['entry'],self.info['entry'])
        self.assertEqual(head[0x10000:0x10000+len(self.raw)],self.raw)
        self.assertGreater(growth,0);self.assertTrue(report['wrapper_identity_verified'])
        self.assertEqual(len(head)+growth+len(tail),report['output_bytes'])
        self.assertFalse(report['restart_ready'])

    def test_temporary_input_can_exceed_runtime_slot(self):
        image = bytearray(random.Random(31).randbytes(17 << 20))
        struct.pack_into('<3Q',image,8,0,len(image),4);image[56:60] = b'ARM\x64';image = bytes(image)
        raw = self.baseline + adapter.inline.make_payload(image,self.dtb,self.initrd)
        self.assertGreater(len(raw),adapter.inline.SLOT)
        _,_,_,report = self.plan(source=fixture_wrapper(raw),raw=raw,image=image)
        self.assertEqual(report['aura_runtime_bytes'],len(self.baseline))
        self.assertGreater(report['raw_inline_bytes'],report['aura_slot_bytes'])

    def test_nested_text_extent_overlap_refused(self):
        p = [p for c,p,n in self.info['commands'] if c == 0x19 and
             self.source[p+8:p+24].rstrip(b'\0') == b'__TEXT'][-1]
        data = bytearray(self.source);struct.pack_into('<Q',data,p+32,0x10000);struct.pack_into('<Q',data,p+48,0x10000)
        with self.assertRaises(ValueError):self.plan(source=bytes(data))

    def test_outer_entry_movement_refused(self):
        p = self.command(5)
        with self.assertRaises(ValueError):self.plan(source=self.altered(p+16+32*8,self.info['entry']+4,8))

    def test_member_vector_movement_refused(self):
        p = self.command(5,True)
        with self.assertRaises(ValueError):self.plan(source=self.altered(p+16+16*8,self.info['code']['vm']+PAGE,8))

    def test_outer_uuid_mismatch_refused(self):
        p = self.command(0x1b)
        with self.assertRaises(ValueError):self.plan(source=self.altered(p+8,0))

    def test_member_uuid_mismatch_refused(self):
        p = self.command(0x1b,True)
        with self.assertRaises(ValueError):self.plan(source=self.altered(p+8,0))

    def test_prelink_identity_mismatch_refused(self):
        segment = self.info['segments']['__PRELINK_INFO'];start = segment['off']
        info = plistlib.loads(self.source[start:start+PAGE].rstrip(b'\0'));info['_PrelinkKCID'] = bytes(16)
        changed = plistlib.dumps(info);data = bytearray(self.source)
        data[start:start+PAGE] = changed.ljust(PAGE,b'\0')
        with self.assertRaises(ValueError):self.plan(source=bytes(data))

    def test_prelink_boolean_integer_confusion_refused(self):
        start = self.info['segments']['__PRELINK_INFO']['off']
        info = plistlib.loads(self.source[start:start+PAGE].rstrip(b'\0'));info['ManagerVersion'] = True
        data = bytearray(self.source);data[start:start+PAGE] = plistlib.dumps(info).ljust(PAGE,b'\0')
        with self.assertRaises(ValueError):self.plan(source=bytes(data))

    def test_reserved_header_flags_refused(self):
        with self.assertRaises(ValueError):self.plan(source=self.altered(28,1))

    def test_member_header_flags_refused(self):
        with self.assertRaises(ValueError):self.plan(source=self.altered(0x8000+24,0))

    def test_build_version_change_refused(self):
        with self.assertRaises(ValueError):self.plan(source=self.altered(self.command(0x32)+8,1))

    def test_segment_flags_change_refused(self):
        with self.assertRaises(ValueError):self.plan(source=self.altered(self.info['code']['command']+68,1))

    def test_fixup_pointer_change_refused(self):
        with self.assertRaises(ValueError):self.plan(source=self.altered(self.command(adapter.pad.FIXUPS)+8,0x10000))

    def test_unbacked_exec_segment_refused(self):
        with self.assertRaises(ValueError):self.plan(source=self.altered(self.info['code']['command']+48,0,8))

    def test_raw_alignment_padding_nonzero_refused(self):
        offset = 0x10000 + len(self.raw)
        self.assertLess(offset,self.info['code']['off']+self.info['code']['size'])
        data = bytearray(self.source);data[offset] = 1
        with self.assertRaises(ValueError):self.plan(source=bytes(data))

    def test_changed_baseline_code_refused(self):
        raw = bytearray(self.raw);raw[0x1000] ^= 1;raw = bytes(raw)
        with self.assertRaises(ValueError):self.plan(source=fixture_wrapper(raw),raw=raw)

    def test_retained_initrd_without_heap_envelope_refused(self):
        info = adapter.inline.verify_payload(self.payload,self.image,self.dtb,self.initrd)
        start,end = info['initrd_envelope_gzip_offset'],info['config_offset']
        tag = adapter.inline.TAG + struct.pack('<I',len(self.initrd)) + self.initrd
        raw = self.baseline+self.payload[:start]+tag+self.payload[end:]
        with self.assertRaises(ValueError):self.plan(source=fixture_wrapper(raw),raw=raw)

    def test_kernel_crc_refused_with_consistent_wrapper_identity(self):
        info = adapter.inline.verify_payload(self.payload,self.image,self.dtb,self.initrd)
        raw = bytearray(self.raw);raw[len(self.baseline)+info['initrd_envelope_gzip_offset']-8] ^= 1;raw = bytes(raw)
        with self.assertRaises(ValueError):self.plan(source=fixture_wrapper(raw),raw=raw)

    def test_dt_source_at_runtime_slot_end_refused(self):
        baseline = synthetic_baseline(adapter.inline.SLOT);raw = baseline+self.payload
        with mock.patch.object(adapter.inline,'BASELINE_SHA256',adapter.inline.digest(baseline)):
            with self.assertRaises(ValueError):self.plan(source=fixture_wrapper(raw),raw=raw)

    def test_output_existing_file_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'existing';path.write_bytes(b'PRESERVE')
            with self.assertRaises(FileExistsError):adapter.write_output(self.source,self.raw,self.image,self.dtb,self.initrd,path)
            self.assertEqual(path.read_bytes(),b'PRESERVE')

    def test_output_symlink_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'existing';path.write_bytes(b'PRESERVE')
            link = Path(directory)/'link';link.symlink_to(path)
            with self.assertRaises(OSError):adapter.write_output(self.source,self.raw,self.image,self.dtb,self.initrd,link)
            self.assertEqual(path.read_bytes(),b'PRESERVE')


if __name__ == '__main__':
    unittest.main(verbosity=2)

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic parser/oracle tests; no firmware instruction is executed."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('dispatch31s', HERE / 'dispatch.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def fixture():
    image = bytearray(512)
    struct.pack_into('<4i', image, 256, -128, 0, 124, -4)
    layout = dict(schema=1, table_offset=256, entry_count=4, target_anchor=0x1080,
                  mappings=[dict(file_offset=0, address=0x1000, size=512)],
                  target_ranges=[[0x1000, 0x1100]], selectors=[0, 1, 2, 3])
    return bytes(image), layout


def resolve(image, layout):
    return M.resolve(image, hashlib.sha256(image).hexdigest(), layout)


class DispatchTests(unittest.TestCase):
    def test_separate_code_anchor_and_signed_targets(self):
        image, layout = fixture()
        value = resolve(image, layout)
        self.assertEqual([r['target'] for r in value['targets']], [0x1000, 0x1080, 0x10fc, 0x107c])
        self.assertEqual([r['target_file_offset'] for r in value['targets']], [0, 128, 252, 124])
        self.assertEqual([r['entry_offset'] for r in value['targets']], [256, 260, 264, 268])
        self.assertEqual(value['runtime_execution'], 'NOT_OBSERVED')
        self.assertEqual(value['permission_state'], 'UNKNOWN')
        self.assertEqual(value['hardware_operations'], 0)

    def test_inputs_not_modified_and_failure_no_partial_result(self):
        image, layout = fixture()
        before = copy.deepcopy(layout)
        resolve(image, layout)
        self.assertEqual(layout, before)
        layout['selectors'] = [0, 4]
        with self.assertRaisesRegex(ValueError, '^selector_bounds$'): resolve(image, layout)
        self.assertEqual(layout['selectors'], [0, 4])

    def test_hash_binding(self):
        image, layout = fixture()
        for digest in ('0'*64, hashlib.sha256(image).hexdigest().upper(), '', True):
            with self.assertRaises(ValueError): M.resolve(image, digest, layout)
        changed = bytearray(image); changed[0] = 1
        with self.assertRaisesRegex(ValueError, '^source_hash_mismatch$'):
            M.resolve(bytes(changed), hashlib.sha256(image).hexdigest(), layout)

    def test_image_type_and_size(self):
        image, layout = fixture()
        for item in (bytearray(image), memoryview(image), b'', None):
            with self.assertRaises(ValueError): M.resolve(item, '0'*64, layout)
        with patch.object(M, 'MAX_IMAGE', 511):
            with self.assertRaisesRegex(ValueError, '^image_extent$'): resolve(image, layout)

    def test_layout_strict_keys_and_schema(self):
        image, layout = fixture()
        for item in (None, dict(layout, extra=1), {k:v for k,v in layout.items() if k!='target_anchor'},
                     dict(layout, schema=True), dict(layout, schema=2)):
            with self.assertRaises(ValueError): resolve(image, item)

    def test_table_extent_and_alignment(self):
        image, layout = fixture()
        for field, value in [('table_offset', -4), ('table_offset', 258), ('table_offset', 512),
                             ('table_offset', 1<<64), ('table_offset', True), ('entry_count', 0),
                             ('entry_count', 4097), ('entry_count', True), ('target_anchor', -4),
                             ('target_anchor', 0x1081), ('target_anchor', 1<<64)]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                resolve(image, dict(layout, **{field:value}))

    def test_selector_bounds_and_duplicates(self):
        image, layout = fixture()
        for selectors in ([], [-1], [4], [True], [0,0], [1.0], tuple([1]), [0]*4097):
            with self.assertRaises(ValueError): resolve(image, dict(layout, selectors=selectors))

    def test_requested_selector_order_preserved(self):
        image, layout = fixture(); layout['selectors'] = [3,0,2]
        self.assertEqual([r['selector'] for r in resolve(image,layout)['targets']], [3,0,2])

    def test_mapping_extent_and_keys(self):
        image, layout = fixture()
        base = layout['mappings'][0]
        for mapping in (dict(base, size=0), dict(base, size=513), dict(base, address=(1<<64)-4),
                        dict(base, file_offset=True), dict(base, file_offset=-1), dict(base, extra=1)):
            with self.assertRaises(ValueError): resolve(image, dict(layout, mappings=[mapping]))
        for value in ([], None, [base]*129):
            with self.assertRaises(ValueError): resolve(image, dict(layout, mappings=value))

    def test_overlapping_virtual_or_file_mappings(self):
        image, layout = fixture()
        base = layout['mappings'][0]
        for mapping in (dict(file_offset=16,address=0x9000,size=4),
                        dict(file_offset=508,address=0x1000,size=4)):
            with self.assertRaisesRegex(ValueError, '^overlapping_mappings$'):
                resolve(image, dict(layout, mappings=[base,mapping]))

    def test_table_must_fit_one_mapping(self):
        image, layout = fixture()
        layout['mappings']=[dict(file_offset=0,address=0x1000,size=260),
                            dict(file_offset=260,address=0x1104,size=252)]
        with self.assertRaisesRegex(ValueError, '^table_not_in_one_mapping$'): resolve(image,layout)

    def test_target_ranges_and_whole_instruction(self):
        image, layout = fixture()
        for value in ([], None, [[0x1100,0x1000]], [[0x1001,0x1100]],
                      [[0x1000,0x10fe]], [[True,0x1100]], [[0x1000,0x1100,0x1200]],
                      [[0x1000,0x1100],[0x1080,0x1100]]):
            with self.assertRaises(ValueError): resolve(image,dict(layout,target_ranges=value))
        layout['target_ranges']=[[0x1000,0x10fc]]
        with self.assertRaisesRegex(ValueError, '^target_outside_allowed_ranges$'): resolve(image,layout)

    def test_target_requires_actual_mapping(self):
        image, layout = fixture()
        layout['mappings']=[dict(file_offset=256,address=0x1100,size=256)]
        with self.assertRaisesRegex(ValueError, '^target_mapping$'): resolve(image,layout)

    def test_whole_target_word_must_be_mapped(self):
        image, layout = fixture()
        layout['selectors'] = [1]
        layout['mappings'] = [dict(file_offset=0,address=0x1000,size=130),
                              dict(file_offset=256,address=0x2000,size=256)]
        with self.assertRaisesRegex(ValueError, '^target_mapping$'): resolve(image,layout)

    def test_target_file_alignment(self):
        image, layout = fixture(); layout['selectors']=[1]
        layout['mappings']=[dict(file_offset=0,address=0x1001,size=512)]
        with self.assertRaisesRegex(ValueError, '^target_file_alignment$'): resolve(image,layout)

    def test_unaligned_target_is_rejected(self):
        image, layout = fixture(); data=bytearray(image)
        struct.pack_into('<i',data,256,1)
        with self.assertRaisesRegex(ValueError, '^target_alignment$'): resolve(bytes(data),layout)

    def test_arithmetic_does_not_wrap(self):
        image=bytearray(32)
        layout=dict(schema=1,table_offset=0,entry_count=1,target_anchor=(1<<64)-4,
                    mappings=[dict(file_offset=0,address=(1<<64)-32,size=32)],
                    target_ranges=[[(1<<64)-32,1<<64]],selectors=[0])
        self.assertEqual(resolve(bytes(image),layout)['targets'][0]['target'],(1<<64)-4)
        struct.pack_into('<i',image,0,4)
        with self.assertRaisesRegex(ValueError, '^target_arithmetic$'): resolve(bytes(image),layout)
        struct.pack_into('<i',image,0,-4); layout['target_anchor']=0
        with self.assertRaisesRegex(ValueError, '^target_arithmetic$'): resolve(bytes(image),layout)

    def test_signed_extreme(self):
        image=struct.pack('<i',-(1<<31)) + bytes(4)
        layout=dict(schema=1,table_offset=0,entry_count=1,target_anchor=0x80001000,
                    mappings=[dict(file_offset=0,address=0x1000,size=8)],
                    target_ranges=[[0x1000,0x1008]],selectors=[0])
        self.assertEqual(resolve(image,layout)['targets'][0]['target'],0x1000)

    def test_page_grid_independent_arithmetic(self):
        # 1,024 distinct relative targets; expected file offsets follow a grid,
        # independent of the resolver's mapping search and signed unpacking.
        data=bytearray(8192); anchor=0x10000800
        for i in range(1024): struct.pack_into('<i',data,4096+4*i,4*i-2048)
        layout=dict(schema=1,table_offset=4096,entry_count=1024,target_anchor=anchor,
                    mappings=[dict(file_offset=0,address=0x10000000,size=8192)],
                    target_ranges=[[0x10000000,0x10001000]],selectors=list(range(1024)))
        rows=resolve(bytes(data),layout)['targets']
        self.assertEqual([r['target_file_offset'] for r in rows],list(range(0,4096,4)))

    def test_reader_rejects_link_directory_and_oversize(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); p=root/'image'; p.write_bytes(b'1234')
            self.assertEqual(M.read_regular(p,4),b'1234')
            with self.assertRaises(ValueError): M.read_regular(p,3)
            link=root/'link'; link.symlink_to(p.name)
            with self.assertRaisesRegex(ValueError,'^input_symlink$'): M.read_regular(link,4)
            with self.assertRaises(ValueError): M.read_regular(root,4096)

    def test_cli_outputs_metadata_only(self):
        image,layout=fixture()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'image').write_bytes(image)
            (root/'layout.json').write_text(json.dumps(layout))
            r=subprocess.run([sys.executable,'-I',str(HERE/'dispatch.py'),'--image',str(root/'image'),
                              '--sha256',hashlib.sha256(image).hexdigest(),'--layout',str(root/'layout.json')],
                             capture_output=True,text=True,timeout=10)
            self.assertEqual(r.returncode,0)
            self.assertEqual(json.loads(r.stdout),resolve(image,layout))
            self.assertNotIn(str(root),r.stdout+r.stderr)

    def test_cli_errors_do_not_expose_arguments(self):
        r=subprocess.run([sys.executable,'-I',str(HERE/'dispatch.py'),'--unknown','PRIVATE_SENTINEL'],
                         capture_output=True,text=True,timeout=10)
        self.assertEqual(r.returncode,1)
        self.assertNotIn('PRIVATE_SENTINEL',r.stdout+r.stderr)
        self.assertEqual(json.loads(r.stdout)['result'],'STATIC_RESOLUTION_REFUSED')


if __name__=='__main__': unittest.main()

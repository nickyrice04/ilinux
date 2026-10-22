#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Synthetic-only RCfg structural tests: no firmware or hardware imports."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('rcfg31o', Path(__file__).with_name('rcfg.py'))
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


def command(sequence=0, opcode=0x15, flags=1, operands=()):
    return struct.pack('<I', len(operands) | opcode << 8 | sequence << 18 | flags << 28) + \
        b''.join(struct.pack('<I', value) for value in operands)


def fixture(commands=None, names=None):
    commands = commands if commands is not None else [command(operands=(0xdeadbeef,)),
                                                      command(1, 0x3ff, 15), b'', b'']
    names = names if names is not None else [(0, b'synthetic-zero'), (1, b'synthetic-one'),
                                            (2, b'synthetic-empty')]
    assert len(commands) == 4
    data = bytearray(0x200)
    struct.pack_into('<IIQ', data, 0x110, 0x52436667, 5, 0x1b0)
    descriptors = []
    for kind, body in enumerate(commands):
        descriptors.append((kind, len(body), len(data)))
        data.extend(body)
    name_body = b''.join(struct.pack('<H', sequence) + name + b'\0' * (64 - len(name))
                         for sequence, name in names)
    descriptors.append((4, len(name_body), len(data)))
    data.extend(name_body)
    for index, descriptor in enumerate(descriptors):
        struct.pack_into('<IIQ', data, 0x1b0 + 16 * index, *descriptor)
    return bytes(data)


def changed(blob, offset, fmt, value):
    data = bytearray(blob)
    struct.pack_into(fmt, data, offset, value)
    return bytes(data)


class StructuralTests(unittest.TestCase):
    def refuse(self, data, reason):
        with self.assertRaises(r.RCfgError) as caught:
            r.decode(data)
        self.assertEqual(str(caught.exception), reason)

    def test_unknown_opcodes_flags_and_unused_names_stay_structural(self):
        result = r.decode(fixture())
        self.assertEqual(result['result'], 'RCfg_STRUCTURAL_PASS')
        self.assertEqual(result['command_count'], 2)
        self.assertEqual(result['opcode_histogram'], {'21': 1, '1023': 1})
        self.assertEqual(result['flag_histogram'], {'1': 1, '15': 1})
        self.assertEqual(result['sequence_record_counts'], {'0': 1, '1': 1, '2': 0})
        self.assertEqual(result['native_operations'], 0)
        for flag in ('evaluated_conditions', 'firmware_emulator',
                     'command_semantics_interpreted', 'nesting_validated'):
            self.assertIs(result[flag], False)
        serialized = json.dumps(result)
        self.assertNotIn('synthetic-', serialized)
        self.assertNotIn('deadbeef', serialized)
        self.assertNotIn(str(0xdeadbeef), serialized)

    def test_index_is_immutable_and_contains_no_operand_or_name(self):
        rows = r.parse_records(fixture())
        self.assertIsInstance(rows, tuple)
        self.assertEqual(rows[0], r.Record(0, 0x200, 0x15, 0, 1, 1))
        with self.assertRaises(AttributeError):
            rows[0].opcode = 0
        self.assertFalse(hasattr(rows[0], 'operands'))
        self.assertFalse(hasattr(rows[0], 'name'))

    def test_input_type_and_size(self):
        for value in (bytearray(fixture()), None, 'RCfg', 42):
            self.refuse(value, 'input_not_bytes')
        self.refuse(b'\0' * (r.MAX_INPUT_BYTES + 1), 'input_too_large')

    def test_header_truncation_magic_count(self):
        for length in (0, 0x110, 0x11f):
            self.refuse(fixture()[:length], 'header_truncated')
        self.refuse(changed(fixture(), 0x110, '<I', 0), 'header_magic')
        for count in (0, 4, 6, 0xffffffff):
            self.refuse(changed(fixture(), 0x114, '<I', count), 'section_count')

    def test_directory_bounds_and_header_overlap(self):
        self.refuse(changed(fixture(), 0x118, '<Q', (1 << 64) - 1), 'directory_bounds')
        self.refuse(changed(fixture(), 0x118, '<Q', len(fixture()) - 79), 'directory_bounds')
        self.refuse(changed(fixture(), 0x118, '<Q', 0x110), 'directory_header_overlap')

    def test_unknown_duplicate_and_out_of_bounds_sections(self):
        self.refuse(changed(fixture(), 0x1b0, '<I', 5), 'section_kind')
        self.refuse(changed(fixture(), 0x1c0, '<I', 0), 'duplicate_section_kind')
        self.refuse(changed(fixture(), 0x1b8, '<Q', 1 << 63), 'section_bounds')
        self.refuse(changed(fixture(), 0x1b4, '<I', 0xffffffff), 'section_bounds')

    def test_overlap_sections_header_and_directory(self):
        self.refuse(changed(fixture(), 0x1c8, '<Q', 0x200), 'section_overlap')
        self.refuse(changed(fixture(), 0x1b8, '<Q', 0x110), 'section_overlap')
        self.refuse(changed(fixture(), 0x1b8, '<Q', 0x1b0), 'section_overlap')

    def test_alignment_and_name_count(self):
        data = fixture()
        self.refuse(changed(data, 0x1b4, '<I', 7), 'command_section_alignment')
        self.refuse(changed(data, 0x1b8, '<Q', 0x201), 'command_section_alignment')
        self.refuse(changed(data, 0x1f4, '<I', 65), 'name_section_alignment')
        self.refuse(changed(data, 0x1f4, '<I', 0), 'name_count')
        too_many = [(index, ('name-%d' % index).encode()) for index in range(1025)]
        self.refuse(fixture(names=too_many), 'name_count')

    def test_operand_limit_and_record_truncation(self):
        self.refuse(fixture([command(operands=tuple(range(33))), b'', b'', b'']),
                    'operand_count_limit')
        self.refuse(fixture([command(operands=(1,))[:4], b'', b'', b'']), 'record_truncated')
        good = fixture([command(operands=tuple(range(32))), b'', b'', b''])
        self.assertEqual(r.decode(good)['maximum_operand_count'], 32)

    def test_unknown_sequence_and_duplicate_name_id(self):
        self.refuse(fixture([command(3), b'', b'', b'']), 'unknown_sequence_id')
        self.refuse(fixture(names=[(0, b'a'), (0, b'b')]), 'duplicate_sequence_id')
        self.refuse(fixture(names=[(0, b'a'), (1, b'a')]), 'duplicate_sequence_name')
        self.refuse(fixture(names=[(1024, b'a')]), 'sequence_id_range')

    def test_name_termination_ascii_and_padding(self):
        self.refuse(fixture(names=[(0, b'')]), 'name_termination')
        self.refuse(fixture(names=[(0, b'a' * 64)]), 'name_termination')
        self.refuse(fixture(names=[(0, b'not\x7fprintable')]), 'name_not_printable_ascii')
        self.refuse(fixture(names=[(0, b'a\0hidden')]), 'name_padding')

    def test_noncontiguous_sequence_ids_are_permitted(self):
        data = fixture([command(1023), b'', b'', b''], [(1023, b'last')])
        self.assertEqual(r.decode(data)['sequence_record_counts'], {'1023': 1})

    def test_descriptor_order_does_not_change_command_index(self):
        original = fixture()
        data = bytearray(original)
        data[0x1b0:0x200] = b''.join(original[start:start + 16]
                                    for start in reversed(range(0x1b0, 0x200, 16)))
        self.assertEqual(r.parse_records(bytes(data)), r.parse_records(original))

    def test_record_count_bound(self):
        data = fixture([command() * (r.MAX_RECORDS + 1), b'', b'', b''])
        self.refuse(data, 'record_count_limit')

    def test_conditional_tokens_are_not_evaluated_or_assumed_balanced(self):
        data = fixture([command(opcode=0xc8) + command(opcode=0xc7), b'', b'', b''])
        report = r.decode(data)
        self.assertEqual(report['command_count'], 2)
        self.assertIs(report['nesting_validated'], False)

    def test_cli_regular_input_and_private_refusal(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'sensitive-name.bin'
            path.write_bytes(fixture())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(r.main(['--input', str(path)]), 0)
            self.assertEqual(json.loads(output.getvalue())['command_count'], 2)
            self.assertNotIn(temporary, output.getvalue())
            path.write_bytes(b'private-artifact-content')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(r.main(['--input', str(path)]), 1)
            self.assertEqual(json.loads(output.getvalue())['reason'], 'header_truncated')
            self.assertNotIn('private-artifact-content', output.getvalue())
            self.assertNotIn('sensitive-name', output.getvalue())

    def test_cli_rejects_symlink_and_directory_without_path_disclosure(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = directory / 'data'
            path.write_bytes(fixture())
            alias = directory / 'alias'
            alias.symlink_to(path)
            for item in (alias, directory, directory / 'missing'):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(r.main(['--input', str(item)]), 1)
                self.assertEqual(json.loads(output.getvalue())['result'], 'RCfg_STRUCTURAL_REFUSAL')
                self.assertNotIn(temporary, output.getvalue())

    def test_cli_arguments_do_not_echo_unknown_values(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as caught:
            r.main(['--private-value', 'do-not-output'])
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(json.loads(output.getvalue())['reason'], 'arguments_invalid')
        self.assertNotIn('do-not-output', output.getvalue())

    def test_cli_rejects_fifo_without_waiting_for_a_writer(self):
        with tempfile.TemporaryDirectory() as temporary:
            fifo = Path(temporary) / 'fifo'
            os.mkfifo(fifo)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(r.main(['--input', str(fifo)]), 1)
            self.assertEqual(json.loads(output.getvalue())['reason'], 'input_not_regular_file')


if __name__ == '__main__':
    unittest.main()

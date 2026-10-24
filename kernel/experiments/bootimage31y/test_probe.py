#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Format bounds and false-success tests; no subprocess or hardware access."""
import importlib.util
from pathlib import Path
import plistlib
import struct
import unittest

spec = importlib.util.spec_from_file_location('probe31y', Path(__file__).with_name('probe.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def commands(blob):
    magic, cpu, subtype, kind, count, length, flags, reserved = struct.unpack_from('<8I', blob)
    assert (magic, cpu, subtype, reserved) == (0xfeedfacf, 0x100000c, 2, 0)
    offset = 32
    result = []
    for _ in range(count):
        command, size = struct.unpack_from('<II', blob, offset)
        assert size >= 8 and size % 8 == 0 and offset + size <= 32 + length
        result.append((command, blob[offset:offset+size]))
        offset += size
    assert offset == 32 + length and offset < 0x800
    return kind, result


class Fixtures(unittest.TestCase):
    def test_all_bounds_and_entry_mapping(self):
        count = 0
        for stage in probe.STAGES:
            for name, blob in probe.fixtures(stage).items():
                with self.subTest(stage=stage, name=name):
                    _, cmds = commands(blob)
                    spans = []
                    entry = None
                    for cmd, data in cmds:
                        if cmd == 0x19:
                            _, size, _, vm, memsize, off, length, maximum, initial, sections, _ = struct.unpack_from('<II16sQQQQiiII', data)
                            self.assertEqual(size, 72 + 80 * sections)
                            self.assertLessEqual(off + length, len(blob))
                            self.assertLessEqual(length, memsize)
                            self.assertEqual(initial & maximum, initial)
                            self.assertNotEqual(initial & 6, 6)  # No writable executable region.
                            spans.append((vm, memsize, off, initial))
                        elif cmd == 5:
                            self.assertEqual(struct.unpack_from('<IIII', data), (5, 288, 6, 68))
                            entry = struct.unpack_from('<Q', data, 16 + 256)[0]
                        else:
                            self.assertEqual(cmd, 0x80000035)
                    matches = [(vm, off) for vm, size, off, prot in spans
                               if prot & 4 and vm <= entry < vm + size]
                    self.assertEqual(len(matches), 1)
                    vm, off = matches[0]
                    self.assertEqual(struct.unpack_from('<I', blob, off + entry - vm)[0], 0x14000000)
                    count += 1
        self.assertEqual(count, 20)

    def test_embedded_fileset_header_and_identifier(self):
        for stage in probe.STAGES[:-1]:
            blob = probe.fixtures(stage)['one-entry-fileset']
            _, cmds = commands(blob)
            entry, = [data for cmd, data in cmds if cmd == 0x80000035]
            _, size, vm, off, nameoff, reserved = struct.unpack_from('<IIQQII', entry)
            self.assertEqual((vm, off, nameoff, reserved), (probe.BASE + probe.PAGE, probe.PAGE, 32, 0))
            self.assertEqual(entry[nameoff:].split(b'\0')[0], b'com.apple.kernel')
            self.assertEqual(struct.unpack_from('<I', blob, off)[0], 0xfeedfacf)
            self.assertEqual(size, len(entry))

    def test_fixture_metadata_is_synthetic_and_empty(self):
        for stage in probe.STAGES[1:]:
            for blob in probe.fixtures(stage).values():
                _, cmds = commands(blob)
                info, = [data for cmd, data in cmds if cmd == 0x19 and
                         data[8:24].split(b'\0')[0] == b'__PRELINK_INFO']
                size, off = struct.unpack_from('<QI', info, 72 + 40)
                metadata = plistlib.loads(blob[off:off+size])
                self.assertEqual(metadata['_PrelinkInfoDictionary'], [])
                if stage == 'metadata':
                    self.assertNotIn('_PrelinkKCID', metadata)
                else:
                    self.assertEqual(len(metadata['_PrelinkKCID']), 16)

    def test_ordering_negative_control(self):
        for stage, relation in [('linkedit', self.assertLess), ('ordered', self.assertGreater)]:
            for blob in probe.fixtures(stage).values():
                _, cmds = commands(blob)
                offsets = {d[8:24].split(b'\0')[0]: struct.unpack_from('<Q', d, 40)[0]
                           for cmd, d in cmds if cmd == 0x19}
                relation(offsets[b'__LINKEDIT'], offsets[b'__PRELINK_INFO'])

    def test_no_hardware_layout_inference(self):
        blob = probe.fixtures('boot-segments')['flat-fileset']
        _, cmds = commands(blob)
        names = [d[8:24].split(b'\0')[0] for cmd, d in cmds if cmd == 0x19]
        self.assertIn(b'__DATA_SPTM', names)
        self.assertIn(b'__TEXT_BOOT_EXEC', names)
        self.assertFalse(any(cmd == 0x80000035 for cmd, _ in cmds))
        self.assertEqual(len(blob), 6 * probe.PAGE)
        with self.assertRaises(ValueError):
            probe.fixtures('native-boot')


class Classification(unittest.TestCase):
    def output(self, values=None):
        values = values if values is not None else {k: 0 for k in probe.PROPERTIES}
        return probe.SUCCESS + '\n{\n' + ''.join(f'    {k} : {v}\n' for k, v in sorted(values.items())) + '}\n'

    def test_success_requires_full_explicit_property_block(self):
        parsed = probe.classify(0, self.output(), '')
        self.assertEqual(parsed['classification'], 'PROPERTIES_DERIVED')
        self.assertEqual(set(parsed['properties']), probe.PROPERTIES)

    def test_zero_exit_property_error_is_not_success(self):
        for message in ('Fileset Error: Failed to find __TEXT_EXEC segment',
                        'Arithmetic Error: arithmetic overflow detected'):
            result = probe.classify(0, 'Mach-O boot properties could not be derived: ' + message, '')
            self.assertEqual(result, {'classification': 'PROPERTY_ERROR', 'properties': None})

    def test_process_failure_overrides_success_text(self):
        for code in (-5, None):
            self.assertEqual(probe.classify(code, self.output(), '')['classification'], 'TOOL_ERROR')
        self.assertEqual(probe.classify(71, self.output(), '')['classification'], 'UNRECOGNIZED_OUTPUT')

    def test_unknown_negative_diagnostics_change_matrix_signature(self):
        cases = [(71, '', "No variant specified, falling back to release\nCould not parse binary: Unable to find '__info' section.\n"),
                 (0, 'Mach-O boot properties could not be derived: Fileset Error: Failed to find __TEXT_EXEC segment\n', '')]
        for code, stdout, stderr in cases:
            base = dict(stage='test', case='test', bytes=0, sha256='test', exit=code)
            reference = probe.signature(dict(base, diagnostic=probe.diagnostic(stdout, stderr),
                                              **probe.classify(code, stdout, stderr)))
            self.assertIn(reference['classification'], ('TOOL_ERROR', 'PROPERTY_ERROR'))
            for out, err in [(stdout + 'unknown warning\n', stderr),
                             ('unknown warning\n' + stdout, stderr),
                             (stdout, stderr + 'unknown warning\n'),
                             (stdout, 'unknown warning\n' + stderr)]:
                parsed = probe.classify(code, out, err)
                self.assertEqual(parsed['classification'], 'UNRECOGNIZED_OUTPUT')
                self.assertNotEqual(probe.signature(dict(base, diagnostic=probe.diagnostic(out, err), **parsed)), reference)

    def test_unknown_warning_refuses(self):
        self.assertEqual(probe.classify(0, self.output(), 'unknown warning')['classification'], 'UNRECOGNIZED_OUTPUT')

    def test_unknown_stdout_prefix_changes_matrix_signature(self):
        banner = 'boot kernel collection at fixture.macho (00000000-0000-0000-0000-000000000000):\n'
        good = banner + self.output()
        base = dict(stage='test', case='test', bytes=0, sha256='test', exit=0,
                    diagnostic=probe.diagnostic(good, ''))
        reference = probe.signature(dict(base, **probe.classify(0, good, '')))
        self.assertEqual(reference['classification'], 'PROPERTIES_DERIVED')
        for bad in ('unknown warning\n' + good, banner + 'unknown warning\n' + self.output(),
                    'unknown warning\n' + self.output(), banner + banner + self.output()):
            parsed = probe.classify(0, bad, '')
            self.assertEqual(parsed['classification'], 'UNRECOGNIZED_OUTPUT')
            self.assertNotEqual(probe.signature(dict(base, **parsed)), reference)

    def test_duplicates_and_multiple_results_refuse(self):
        for output in (self.output() + self.output(), self.output().replace('}', '    kclo : 0\n}')):
            self.assertEqual(probe.classify(0, output, '')['classification'], 'UNRECOGNIZED_OUTPUT')

    def test_missing_extra_and_invalid_values_refuse(self):
        base = {k: 0 for k in probe.PROPERTIES}
        missing = dict(base); del missing['kcbz']
        extra = dict(base, nope=0)
        for data in (missing, extra, dict(base, kcbz=-1), dict(base, kcbz=1 << 64)):
            self.assertEqual(probe.classify(0, self.output(data), '')['classification'], 'UNRECOGNIZED_OUTPUT')

    def test_missing_marker_and_trailing_garbage_refuse(self):
        for text in ('', '{}', self.output() + 'unexpected'):
            self.assertEqual(probe.classify(0, text, '')['classification'], 'UNRECOGNIZED_OUTPUT')


if __name__ == '__main__':
    unittest.main()

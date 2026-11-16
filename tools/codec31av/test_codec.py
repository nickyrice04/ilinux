#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise actual pinned C decoding; only generated or exact own inputs."""
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('codec31av_builder', HERE / 'build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
SANITIZE = '--sanitize' in sys.argv
if SANITIZE:
    sys.argv.remove('--sanitize')


def der(tag, body):
    size = len(body)
    width = max(1, (size.bit_length() + 7) // 8)
    length = bytes([size]) if size < 128 else bytes([0x80 + width]) + size.to_bytes(width, 'big')
    return bytes([tag]) + length + body


def integer(value):
    body = value.to_bytes(max(1, (value.bit_length() + 7) // 8), 'big')
    if body[0] & 128:
        body = b'\0' + body
    return der(2, body)


def declaration(size):
    return der(0x30, integer(1) + integer(size))


def im4p(body, extra=b''):
    return der(0x30, der(0x16, b'IM4P') + der(0x16, b'krnl') +
               der(0x16, b'OWN-CONTROL') + der(4, body) + extra)


def compress(plain):
    api = ctypes.CDLL('/usr/lib/libcompression.dylib')
    api.compression_encode_buffer.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
        ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_int]
    api.compression_encode_buffer.restype = ctypes.c_size_t
    source = ctypes.create_string_buffer(plain)
    result = ctypes.create_string_buffer(len(plain) * 2 + 4096)
    size = api.compression_encode_buffer(result, len(result), source, len(plain), None, 0x801)
    if not size:
        raise AssertionError('own encoding failed')
    return result.raw[:size]


class Codec(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform != 'darwin':
            raise unittest.SkipTest('installed Apple SDK required')
        base = ROOT / 'build/codec31av'
        base.mkdir(parents=True, exist_ok=True)
        cls.directory = Path(tempfile.mkdtemp(prefix='tests-', dir=base))
        cls.binary = builder.build(cls.directory / 'compiled', SANITIZE)
        cls.plain = bytes(((i * 17) ^ (i >> 4)) & 255 for i in range(65536))
        cls.encoded = compress(cls.plain)
        cls.index = 0

    def run_probe(self, *args):
        result = subprocess.run([str(self.binary), *map(str, args)],
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.stderr, '', result.stderr)
        return result

    def fixture(self, data):
        type(self).index += 1
        path = self.directory / ('fixture-' + str(self.index))
        path.write_bytes(data)
        result = self.run_probe('--fixture', path)
        self.assertEqual(result.returncode, 0, result.stdout)
        record = json.loads(result.stdout)
        self.assertNotIn(str(path), result.stdout)
        self.assertFalse(record['native_ready'])
        self.assertFalse(record['host_queries'])
        return record

    def test_actual_c_matrix_and_reproduced_counterexample(self):
        result = self.run_probe('--selftest')
        self.assertEqual(result.returncode, 0, result.stdout)
        (self.directory / 'matrix-result.jsonl').write_text(result.stdout)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(records[-1]['status'], 'PASS')
        self.assertEqual(records[-1]['cases'], 77)
        self.assertEqual(records[-1]['failures'], 0)
        cases = {r['case']: r for r in records if r['kind'] == 'case'}
        for method in range(2):
            name = 'generated_1048576_pattern2_encoder' + str(method)
            observed = cases[name]
            self.assertTrue(observed['frame_accepted'])
            self.assertFalse(observed['frozen_exact'])
            self.assertTrue(observed['buffer_exact'])
            self.assertTrue(observed['proposal_exact'])
            self.assertFalse(observed['proposal_known_exact'])
            chunks = [r for r in records if r['kind'] == 'source_chunk_trace' and r['case'] == name]
            self.assertEqual(len(chunks), 5)
            self.assertTrue(all(r['reason'] == 'EXACT' for r in chunks))
        self.assertTrue(cases['trailing_byte']['buffer_exact'])
        self.assertFalse(cases['trailing_byte']['proposal_exact'])
        self.assertFalse(cases['framed_invalid_lzvn']['proposal_exact'])

    def test_exact_owned_candidate_both_encoders(self):
        candidate = ROOT / 'build/ilinux-31au-kit-v2/candidate.macho'
        self.assertTrue(candidate.is_file(), 'genuine own candidate required')
        data = candidate.read_bytes()
        self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), builder.CANDIDATE)
        result = self.run_probe('--candidate', candidate)
        self.assertEqual(result.returncode, 0, result.stdout)
        (self.directory / 'candidate-result.jsonl').write_text(result.stdout)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(records[-1]['status'], 'PASS')
        for row in records:
            if row['kind'] == 'case':
                self.assertTrue(row['frozen_exact'])
                self.assertTrue(row['proposal_exact'])
                self.assertTrue(row['proposal_known_exact'])

    def test_raw_declared_and_img4_controls(self):
        records = [self.fixture(self.encoded),
                   self.fixture(im4p(self.encoded, declaration(len(self.plain)))),
                   self.fixture(der(0x30, der(0x16, b'IMG4') +
                       im4p(self.encoded, declaration(len(self.plain))) + der(0xa0, b'OWN')))]
        for row in records:
            self.assertTrue(row['proposal_completed'])
            self.assertFalse(row['proposal_exact'])
            self.assertEqual(row['reason'], 'DECODED_UNMATCHED')

    def test_keybag_still_blocks(self):
        row = self.fixture(im4p(self.encoded, der(4, b'OWN-SYNTHETIC-KEYBAG')))
        self.assertTrue(row['proposal_completed'])
        self.assertFalse(row['proposal_exact'])
        self.assertEqual(row['reason'], 'KEYBAG_BLOCKED')

    def test_wrong_declaration_and_output_counts(self):
        for value in (len(self.plain)-1, len(self.plain)+1):
            row = self.fixture(im4p(self.encoded, declaration(value)))
            self.assertFalse(row['proposal_completed'])
            self.assertEqual(row['reason'], 'DECLARED_SIZE_MISMATCH')
        self.assertIn(self.encoded[:4], (b'bvx2', b'bvxn'))
        for value in (len(self.plain)-1, len(self.plain)+1):
            changed = self.encoded[:4] + struct.pack('<I', value) + self.encoded[8:]
            row = self.fixture(changed)
            self.assertFalse(row['proposal_completed'])
            self.assertEqual(row['reason'], 'DECODE_REJECTED')

    def test_truncated_trailing_and_malformed_frame(self):
        controls = [self.encoded[:-1], self.encoded[:-4], self.encoded + b'\0',
                    self.encoded+b'bvx$', b'bvx2', b'bvx$TRAILER',
                    b'bvx-' + struct.pack('<I', 160*1024*1024+1),
                    b'bvxn'+struct.pack('<II',16,3)+b'\0\0\0bvx$']
        for data in controls:
            row = self.fixture(data)
            self.assertFalse(row['proposal_completed'])
            self.assertFalse(row['proposal_exact'])

    def test_changed_candidate_does_not_become_exact(self):
        plain = b'OWN-WRONG-HASH' * 2048
        row = self.fixture(compress(plain))
        self.assertTrue(row['proposal_completed'])
        self.assertFalse(row['proposal_exact'])
        self.assertFalse(row['proposal_candidate_exact'])
        path = self.directory / 'wrong-hash-same-size'
        with path.open('wb') as file:
            file.seek(builder.CANDIDATE[0]-1)
            file.write(b'\0')
        result = self.run_probe('--fixture', path)
        self.assertEqual(result.returncode, 0)
        row = json.loads(result.stdout)
        self.assertTrue(row['proposal_completed'])
        self.assertFalse(row['proposal_exact'])
        self.assertEqual(self.run_probe('--candidate', path).returncode, 2)

    def test_unsupported_der_declarations_and_gzip(self):
        controls = [b'\x30\x80', im4p(self.encoded)+b'\0',
                    im4p(self.encoded, declaration(0)),
                    im4p(self.encoded, declaration(160*1024*1024+1)),
                    im4p(self.encoded, der(0x30, integer(2)+integer(len(self.plain)))),
                    im4p(self.encoded, der(0x30, integer(1)+der(2,b'\0\x01'))),
                    b'\x1f\x8b\x08OWN']
        for data in controls:
            row = self.fixture(data)
            self.assertFalse(row['proposal_completed'])
            self.assertFalse(row['proposal_exact'])

    def test_compressed_raw_and_file_bounds(self):
        for name, length, prefix, expected_exit in (
            ('compressed-too-large', 32*1024*1024+1, b'bvx-', 0),
            ('raw-too-large', 160*1024*1024+1, b'OWN', 0),
            ('file-too-large', 161*1024*1024+1, b'OWN', 2)):
            path = self.directory / name
            with path.open('wb') as file:
                file.write(prefix)
                file.seek(length-1)
                file.write(b'\0')
            result = self.run_probe('--fixture', path)
            self.assertEqual(result.returncode, expected_exit)
            row = json.loads(result.stdout)
            if not expected_exit:
                self.assertFalse(row['proposal_completed'])
                self.assertFalse(row['proposal_exact'])

    def test_bad_cli_and_path_aliases_are_refused(self):
        self.assertEqual(json.loads(self.run_probe().stdout)['status'], 'INERT')
        paths = ['/etc/passwd', str(ROOT / 'build/../AGENTS.md'),
                 str(self.directory / '../..' / 'AGENTS.md')]
        own = self.directory / 'own'
        own.write_bytes(self.encoded)
        link = self.directory / 'alias'
        link.symlink_to(own)
        paths.append(str(link))
        for path in paths:
            for command in ('--fixture', '--candidate'):
                result = self.run_probe(command, path)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn(path, result.stdout)
        self.assertEqual(self.run_probe('--live').returncode, 2)

    def test_builder_refuses_reuse_alias_and_outside(self):
        for path in (self.directory / 'compiled', self.directory / '..' / 'alias-build', Path('/tmp/not-codec31av')):
            with self.assertRaises(ValueError):
                builder.build(path, SANITIZE)
        alias = self.directory / 'output-link'
        alias.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaises(ValueError):
            builder.build(alias / 'new', SANITIZE)

    def test_frozen_sources_unchanged(self):
        for name, digest in builder.PINS.items():
            source = ROOT / 'tools/boot-object31aj-native' / name
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), digest)


if __name__ == '__main__':
    unittest.main(verbosity=2)

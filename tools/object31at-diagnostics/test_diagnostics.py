#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Owned workspace fixtures only; no live, policy, selected-object or writer API."""
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('object31at_build', HERE / 'build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
SANITIZE = '--sanitize' in sys.argv
if SANITIZE:
    sys.argv.remove('--sanitize')
BASE = ROOT / 'build/object31at-diagnostic-tests'

ORACLE = b'''/* SPDX-License-Identifier: MIT */
#include "reader.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv){
 if(argc!=2||strncmp(argv[1],WORKSPACE_ROOT "/build/",strlen(WORKSPACE_ROOT "/build/")))return 2;
 uint8_t *data=NULL;size_t n=0;if(!read_file(argv[1],FILE_LIMIT,true,&data,&n))return 2;
 Identity id;bool completed=identify_object((Bytes){data,n},&id);
 printf("{\\"recognizer_completed\\":%s,\\"known_exact\\":%s,\\"candidate_exact\\":%s,\\"identity\\":\\"%s\\"}\\n",
 completed?"true":"false",completed&&id.exact?"true":"false",
 completed&&id.exact&&!strcmp(id.identity,"CANDIDATE")?"true":"false",id.identity);
 free(data);return 0;
}
'''

MEMORY_CONTROLS = b'''/* SPDX-License-Identifier: MIT */
#include "diagnostics.h"
#include <stdio.h>
#include <string.h>
int main(void){
 ObjectDiagnostics31AT d;uint8_t own=0;
 object_diagnostics31at((Bytes){NULL,0},&d);
 if(strcmp(d.stage,"INPUT_BOUND_REJECTED")||d.known_exact||d.recognizer_completed)return 1;
 object_diagnostics31at((Bytes){NULL,1},&d);
 if(strcmp(d.stage,"INPUT_BOUND_REJECTED")||d.known_exact||d.recognizer_completed)return 2;
 object_diagnostics31at((Bytes){&own,FILE_LIMIT+1},&d);
 if(strcmp(d.stage,"INPUT_BOUND_REJECTED")||d.known_exact||d.recognizer_completed)return 3;
 puts("MEMORY_CONTROLS_PASS");return 0;
}
'''


def der(tag, data):
    n = len(data)
    width = (n.bit_length() + 7) // 8
    return bytes([tag]) + (bytes([n]) if n < 128 else bytes([0x80 + width]) + n.to_bytes(width, 'big')) + data


def integer(n):
    data = n.to_bytes(max(1, (n.bit_length() + 7) // 8), 'big')
    if data[0] & 128:
        data = b'\0' + data
    return der(2, data)


def im4p(body, extra=b'', kind=b'krnl'):
    return der(0x30, der(0x16, b'IM4P') + der(0x16, kind) +
               der(0x16, b'OWN-SYNTHETIC-ONLY') + der(4, body) + extra)


def img4(body, extra=None):
    if extra is None:
        extra = der(0xa0, b'OWN-SYNTHETIC-MANIFEST')
    return der(0x30, der(0x16, b'IMG4') + body + extra)


def declaration(n):
    return der(0x30, integer(1) + integer(n))


def compress(data):
    api = ctypes.CDLL('/usr/lib/libcompression.dylib')
    api.compression_encode_buffer.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
        ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_int]
    api.compression_encode_buffer.restype = ctypes.c_size_t
    source = ctypes.create_string_buffer(data)
    out = ctypes.create_string_buffer(len(data) * 2 + 4096)
    n = api.compression_encode_buffer(out, len(out), source, len(data), None, 0x801)
    if not n:
        raise AssertionError('own LZFSE fixture encoding failed')
    return out.raw[:n]


class Diagnostics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform != 'darwin':
            raise unittest.SkipTest('Original core/decoder needs installed macOS SDK')
        BASE.mkdir(parents=True, exist_ok=True)
        cls.directory = Path(tempfile.mkdtemp(prefix='owned-', dir=BASE))
        cls.plain = b'\x30\x80' + bytes(((i * 17) ^ (i >> 4)) & 255 for i in range(65534))
        cls.encoded = compress(cls.plain)
        cls.binary = builder.build(cls.directory / 'synthetic-build', SANITIZE,
            (len(cls.plain), hashlib.sha256(cls.plain).hexdigest()), ORACLE)
        cls.oracle = cls.binary.parent / 'original-oracle'
        cls.production = builder.build(cls.directory / 'production-build', SANITIZE,
                                       oracle=ORACLE)
        source = cls.binary.parent / 'sources'
        (source / 'memory.c').write_bytes(MEMORY_CONTROLS)
        flags = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                 '-Wno-deprecated-declarations', '-I', str(source),
                 '-DWORKSPACE_ROOT=' + json.dumps(str(ROOT)),
                 '-DCANDIDATE_BYTES=' + str(len(cls.plain)),
                 '-DCANDIDATE_SHA256=' + json.dumps(hashlib.sha256(cls.plain).hexdigest())]
        if SANITIZE:
            flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        cls.memory = cls.directory / 'memory-controls'
        subprocess.run(['/usr/bin/xcrun', 'clang', *flags, str(source / 'diagnostics.c'),
            str(source / 'memory.c'), '-framework', 'CoreFoundation', '-lcompression',
            '-o', str(cls.memory)], check=True, capture_output=True, timeout=30)
        cls.index = 0

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'directory'):
            shutil.rmtree(cls.directory)

    def run_binary(self, args, binary=None):
        result = subprocess.run([str(binary or self.binary), *map(str, args)],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.stderr, '', result.stderr)
        return result

    def run_path(self, path, stage=None, binary=None):
        binary = binary or self.binary
        result = self.run_binary(['--fixture', path], binary)
        self.assertEqual(result.returncode, 0, result.stdout)
        observed = json.loads(result.stdout)
        if stage is not None:
            self.assertEqual(observed['stage'], stage)
        oracle = binary.parent / 'original-oracle'
        original = self.run_binary([path], oracle)
        self.assertEqual(original.returncode, 0)
        original_record = json.loads(original.stdout)
        for key in ('recognizer_completed', 'known_exact', 'candidate_exact', 'identity'):
            self.assertEqual(observed[key], original_record[key], key)
        self.assertFalse(observed['native_ready'])
        self.assertFalse(observed['selection_verified'])
        self.assertFalse(observed['private_values_returned'])
        self.assertNotIn(str(path), result.stdout)
        return observed

    def fixture(self, data, stage, binary=None):
        type(self).index += 1
        path = self.directory / ('fixture-' + str(self.index))
        path.write_bytes(data)
        return self.run_path(path, stage, binary)

    def test_raw_and_framed_exact_candidate(self):
        fixtures = [self.plain, im4p(self.plain), img4(im4p(self.plain)),
                    img4(im4p(self.plain), der(0xa0,b'OWN')+der(0xa1,b'OWN')),
                    im4p(self.plain, der(0xa0,b'OWN')), im4p(self.plain, kind=b'OWN!')]
        for data in fixtures:
            with self.subTest(size=len(data)):
                result = self.fixture(data, 'KNOWN_MATCHED')
                self.assertTrue(result['candidate_exact'])

    def test_lzfse_exact_raw_and_declared_img4(self):
        fixtures = [self.encoded, im4p(self.encoded),
                    img4(im4p(self.encoded, declaration(len(self.plain)))),
                    im4p(self.encoded, declaration(len(self.plain))+der(0xa0,b'OWN'))]
        for data in fixtures:
            with self.subTest(size=len(data)):
                result = self.fixture(data, 'KNOWN_MATCHED')
                self.assertTrue(result['candidate_exact'])
                self.assertEqual(result['codec'], 'LZFSE')

    def test_der_and_outer_trailer_refused(self):
        fixtures = [b'\x30\x80', b'\x30\x00', img4(im4p(self.plain))+b'\0',
                    im4p(self.plain)+b'PRIVATE_TRAILER',
                    img4(im4p(self.plain), der(0xa1,b'OWN')+der(0xa0,b'OWN')),
                    img4(im4p(self.plain), der(0xa0,b'OWN')+der(0xa0,b'OWN')),
                    im4p(self.plain, declaration(0)), im4p(self.plain, declaration(160*1024*1024+1))]
        for data in fixtures:
            with self.subTest(size=len(data)):
                r = self.fixture(data, 'DER_FRAMING_REJECTED')
                self.assertFalse(r['recognizer_completed'])
                self.assertFalse(r['known_exact'])

    def test_keybag_blocks_before_decoding_without_secrets(self):
        for body in (self.plain, self.encoded):
            r = self.fixture(im4p(body, der(4,b'OWN-SYNTHETIC-KEYBAG')), 'KEYBAG_BLOCKED')
            self.assertTrue(r['recognizer_completed'])
            self.assertFalse(r['known_exact'])
            self.assertEqual(r['codec'], 'KEYBAG_BLOCKED')

    def test_compressed_bound(self):
        path = self.directory / 'compressed-oversize'
        with path.open('wb') as stream:
            stream.write(b'bvx-')
            stream.seek(32*1024*1024)
            stream.write(b'x')
        self.run_path(path, 'COMPRESSED_BOUND_REJECTED')

    def test_lzfse_frame_and_trailer_rejection(self):
        for data in (b'bvx2', b'bvxn'+b'\0'*8,
                     self.encoded+b'\0', self.encoded[:-1], b'bvx$EXTRA',
                     b'bvx-'+struct.pack('<I',160*1024*1024+1)+b'bvx$'):
            with self.subTest(size=len(data)):
                self.fixture(data, 'LZFSE_FRAME_REJECTED')

    def test_declared_size_mismatch(self):
        self.fixture(im4p(self.encoded, declaration(len(self.plain)-1)),
                     'DECLARED_SIZE_MISMATCH')

    def test_decoder_rejection_after_valid_frame(self):
        bad_lzvn = b'bvxn'+struct.pack('<II',16,3)+b'\x00\x00\x00'+b'bvx$'
        r = self.fixture(bad_lzvn, 'DECODE_REJECTED')
        self.assertFalse(r['recognizer_completed'])

    def test_decoded_unmatched_is_not_known(self):
        r = self.fixture(compress(b'OWN-SYNTHETIC-UNMATCHED'*2048), 'DECODED_UNMATCHED')
        self.assertTrue(r['recognizer_completed'])
        self.assertFalse(r['known_exact'])

    def test_uncompressed_declaration_and_gzip(self):
        self.fixture(im4p(b'OWN', declaration(3)), 'UNCOMPRESSED_DECLARATION_REJECTED')
        self.fixture(b'\x1f\x8b\x08OWN', 'GZIP_UNSUPPORTED')

    def test_uncompressed_bound(self):
        path = self.directory / 'uncompressed-oversize'
        with path.open('wb') as stream:
            stream.write(b'OWN')
            stream.seek(160*1024*1024)
            stream.write(b'x')
        self.run_path(path, 'UNCOMPRESSED_BOUND_REJECTED')

    def test_uncompressed_unmatched_and_finite_output(self):
        private = b'PRIVATE_TEST_VALUE_DO_NOT_RETURN'
        r = self.fixture(private*10, 'UNCOMPRESSED_UNMATCHED')
        text = json.dumps(r)
        self.assertNotIn(private.decode(), text)
        self.assertNotIn(hashlib.sha256(private*10).hexdigest(), text)
        self.assertEqual(set(r), {'schema','scope','stage','identity','container','codec',
            'recognizer_completed','known_exact','candidate_exact','read_only',
            'host_queries','native_ready','selection_verified','private_values_returned'})

    def test_inert_help_and_no_live_dispatch(self):
        result = self.run_binary([])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['status'], 'INERT')
        self.assertEqual(self.run_binary(['--help']).returncode, 0)
        for args in (['--live'], ['--fixture'], ['--fixture','SECRET_PATH_VALUE','extra']):
            result = self.run_binary(args)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('SECRET', result.stdout)
            self.assertEqual(json.loads(result.stdout)['status'], 'REFUSED')

    def test_workspace_only_symlink_fifo_and_oversize_cli_refusals(self):
        good = self.directory / 'target'
        good.write_bytes(self.plain)
        link = self.directory / 'link'
        link.symlink_to(good)
        parent_link = self.directory / 'parent-link'
        parent_link.symlink_to(self.directory, target_is_directory=True)
        fifo = self.directory / 'fifo'
        os.mkfifo(fifo)
        empty = self.directory / 'empty'
        empty.touch()
        huge = self.directory / 'too-large'
        with huge.open('wb') as stream:
            stream.seek(161*1024*1024)
            stream.write(b'x')
        for path in (link, parent_link/'target', fifo, empty, huge,
                     ROOT/'AGENTS.md', Path('/dev/null'), self.directory/'../target'):
            with self.subTest(path=path):
                r = self.run_binary(['--fixture', path])
                self.assertEqual(r.returncode, 2)
                self.assertEqual(json.loads(r.stdout)['status'], 'REFUSED')

    def test_memory_input_bound_controls(self):
        result = self.run_binary([], self.memory)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, 'MEMORY_CONTROLS_PASS\n')

    def test_build_receipts_pin_original_sources_and_mode(self):
        r = json.loads((self.binary.parent/'build-result.json').read_bytes())
        self.assertEqual(r['original_source_sha256'], builder.PINNED)
        self.assertEqual(r['sanitized'], SANITIZE)
        self.assertTrue(r['synthetic_candidate_definition'])
        self.assertFalse(r['native_ready'])
        self.assertFalse(r['controller_integrated'])
        with self.assertRaises(ValueError):
            builder.build(self.binary.parent)
        with self.assertRaises(ValueError):
            builder.build(ROOT/'tools/not-a-build')

    def test_real_pinned_candidate_and_owned_codec_fixtures(self):
        candidate = ROOT/'build/ilinux-31ar-kit/candidate.macho'
        real = ROOT/'build/boot-object31aj-native/validation-v1'
        required = [candidate, real/'candidate_lzfse.bin', real/'candidate_img4_lzfse.bin',
                    real/'candidate_lzfse_with_trailer.bin']
        if not all(path.is_file() and not path.is_symlink() for path in required):
            self.skipTest('retained own candidate/codec fixtures unavailable')
        raw = candidate.read_bytes()
        self.assertEqual(len(raw), builder.REAL_CANDIDATE[0])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), builder.REAL_CANDIDATE[1])
        del raw
        for path in required[:3]:
            with self.subTest(name=path.name):
                result = self.run_path(path, 'KNOWN_MATCHED', self.production)
                self.assertTrue(result['candidate_exact'])
        self.run_path(required[3], 'LZFSE_FRAME_REJECTED', self.production)


if __name__ == '__main__':
    unittest.main()

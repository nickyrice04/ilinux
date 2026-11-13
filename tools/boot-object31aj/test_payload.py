#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tiny synthetic payloads and injected test codecs; no Apple calls or execution."""
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
import zlib

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('payload31aj_test',HERE/'payload.py')
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
SAMPLES={'31AI':b'synthetic-candidate-'+bytes(256),'BOOT021':b'synthetic-boot021','31AF':b'synthetic-observer-31af'}
PINS={k:(len(v),hashlib.sha256(v).hexdigest()) for k,v in SAMPLES.items()}
def der(tag,body):
    n=len(body);width=(n.bit_length()+7)//8
    length=bytes([n]) if n<128 else bytes([128+width])+n.to_bytes(width,'big')
    return bytes([tag])+length+body
def num(n):
    b=n.to_bytes(max(1,(n.bit_length()+7)//8),'big')
    return der(2,(b'\0' if b[0]&128 else b'')+b)
def im4p(payload,extra=b'',kind=b'krnl',description=b'synthetic-only'):
    return der(0x30,der(0x16,b'IM4P')+der(0x16,kind)+der(0x16,description)+der(4,payload)+extra)
def img4(payload,extra=b''):
    return der(0x30,der(0x16,b'IMG4')+payload+extra)
def compression(size):return der(0x30,num(1)+num(size))
def test_gzip_codec(family,encoded,limit):
    assert family=='GZIP'
    decoder=zlib.decompressobj(31);out=decoder.decompress(encoded,limit+1)
    return out,len(encoded)-len(decoder.unused_data)-len(decoder.unconsumed_tail),decoder.eof

class Payload(unittest.TestCase):
    def setUp(self):
        self.patch=mock.patch.object(tool,'KNOWN',PINS);self.patch.start();self.addCleanup(self.patch.stop)
    def inspect(self,data,codec=None):return tool.inspect_payload(data,codec)
    def test_all_three_exact_raw_labels(self):
        for name,data in SAMPLES.items():
            with self.subTest(label=name):
                r=self.inspect(data);self.assertEqual(r['payload_label'],name)
                self.assertEqual(r['status'],'EXACT_KNOWN_PAYLOAD')
    def test_unknown_raw_does_not_echo_bytes_or_digest(self):
        marker=b'SYNTHETIC_PRIVATE_MARKER';r=self.inspect(marker);out=json.dumps(r)
        self.assertEqual(r['payload_label'],'UNKNOWN');self.assertNotIn(marker.decode(),out)
        self.assertNotIn(hashlib.sha256(marker).hexdigest(),out)
        self.assertFalse(any('hash' in k or 'sha256' in k or 'path' in k for k in r))
    def test_exact_payload_under_opaque_img4_contexts(self):
        r=self.inspect(img4(im4p(SAMPLES['31AF'],der(0xa0,b'\xff\x80PRIVATE_A0')),
                              der(0xa0,b'PRIVATE_MANIFEST')+der(0xa1,b'PRIVATE_RESTORE')))
        self.assertEqual(r['payload_label'],'31AF');self.assertTrue(r['opaque_metadata_present'])
        self.assertNotIn('PRIVATE_',json.dumps(r))
        for k in ('container_authenticity_verified','opaque_semantics_verified','restoration_verified','bootability_verified','write_authorized'):
            self.assertIs(r[k],False)
    def test_other_printable_fourcc_preserves_contained_identity_without_echo(self):
        r=self.inspect(im4p(SAMPLES['31AF'],kind=b'QWER'))
        self.assertEqual(r['payload_label'],'31AF');self.assertNotIn('QWER',json.dumps(r))
        self.assertFalse(r['bootability_verified'])
    def test_invalid_payload_type_refused(self):self.assertEqual(self.inspect(im4p(SAMPLES['31AF'],kind=b'\x01abc'))['status'],'REFUSED')
    def test_known_payload_prefix_padding_never_matches(self):
        for suffix in (bytes(1),b'foreign'):
            for data in (SAMPLES['31AF']+suffix,im4p(SAMPLES['31AF']+suffix)):
                self.assertEqual(self.inspect(data)['payload_label'],'UNKNOWN')
    def test_outer_trailers_never_normalized(self):
        for suffix in (bytes(4),b'foreign'):
            r=self.inspect(im4p(SAMPLES['31AF'])+suffix)
            self.assertEqual(r['status'],'REFUSED');self.assertEqual(r['payload_label'],'UNKNOWN')
    def test_keybag_blocks_comparison_and_codec(self):
        codec=mock.Mock()
        for payload,extra in ((SAMPLES['31AF'],der(4,b'PRIVATE_KEYBAG')),
                              (b'bvx2synthetic',der(4,b'PRIVATE_KEYBAG')+compression(len(SAMPLES['31AF'])))):
            r=self.inspect(im4p(payload,extra),codec)
            self.assertEqual(r['payload_label'],'UNKNOWN');self.assertTrue(r['keybag_present'])
            self.assertEqual(r['reason'],'OPAQUE_KEYBAG_BLOCKED');self.assertNotIn('PRIVATE_KEYBAG',json.dumps(r))
        codec.assert_not_called()
    def test_duplicate_or_nonfinal_a0_refused(self):
        a0=der(0xa0,b'opaque')
        for extras in (a0+a0,a0+der(4,b'keybag'),a0+compression(10)):
            self.assertEqual(self.inspect(im4p(SAMPLES['31AF'],extras))['status'],'REFUSED')
    def test_opaque_and_description_bounds(self):
        for data in (im4p(SAMPLES['31AF'],der(0xa0,bytes(tool.MAX_OPAQUE+1))),
                     im4p(SAMPLES['31AF'],description=bytes(4097))):
            self.assertEqual(self.inspect(data)['status'],'REFUSED')
    def test_duplicate_or_other_outer_context_refused(self):
        for extras in (der(0xa0,b'a')*2,der(0xa2,b'a')):
            self.assertEqual(self.inspect(img4(im4p(SAMPLES['31AF']),extras))['status'],'REFUSED')
    def test_reversed_outer_context_order_refused(self):
        r=self.inspect(img4(im4p(SAMPLES['31AF']),der(0xa1,b'opaque')+der(0xa0,b'opaque')))
        self.assertEqual(r['status'],'REFUSED');self.assertEqual(r['payload_label'],'UNKNOWN')
    def test_der_malformed_lengths_and_high_tags(self):
        for data in (b'\x30\x80\0\0',b'\x30\x81\x01x',b'\x30\x82\0\x80'+bytes(128),
                     b'\x30\x85'+bytes(5),b'\x30\x7fshort',der(0x30,b'\x1f\x01x')):
            with self.subTest(size=len(data)):self.assertEqual(self.inspect(data)['status'],'REFUSED')
    def test_extra_field_budget(self):
        self.assertEqual(self.inspect(im4p(SAMPLES['31AF'],der(2,b'\x01')*20))['status'],'REFUSED')
    def test_empty_and_oversize_raw_bound(self):
        with mock.patch.object(tool,'MAX_RAW',1024):
            for data in (b'',bytes(1025),bytearray(b'not bytes')):
                self.assertEqual(self.inspect(data)['status'],'REFUSED')
    def test_compressed_input_bound_precedes_codec(self):
        codec=mock.Mock()
        with mock.patch.object(tool,'MAX_COMPRESSED',16):
            r=self.inspect(im4p(b'bvx2synthetic',compression(len(SAMPLES['31AF']))),codec)
        self.assertEqual(r['status'],'REFUSED');codec.assert_not_called()
    def test_lzfse_requires_explicit_injected_provider(self):
        r=self.inspect(im4p(b'bvx2synthetic',compression(len(SAMPLES['31AF']))))
        self.assertEqual(r['reason'],'INJECTED_CODEC_REQUIRED');self.assertFalse(r['decompressed'])
    def test_injected_codec_receives_exact_known_output_limit(self):
        encoded=b'bvx2synthetic';expected=SAMPLES['31AI']
        codec=mock.Mock(return_value=(expected,len(encoded),True))
        r=self.inspect(im4p(encoded,compression(len(expected))+der(0xa0,b'opaque')),codec)
        codec.assert_called_once_with('LZFSE_MAGIC',encoded,len(expected))
        self.assertEqual(r['payload_label'],'31AI');self.assertTrue(r['decompressed'])
        self.assertFalse(r['opaque_semantics_verified'])
    def test_unbound_declared_size_never_invokes_codec(self):
        codec=mock.Mock()
        r=self.inspect(im4p(b'bvx2synthetic',compression(12345)),codec)
        self.assertEqual(r['reason'],'DECLARED_SIZE_NOT_KNOWN');codec.assert_not_called()
    def test_raw_lzfse_without_size_never_invokes_codec(self):
        codec=mock.Mock();r=self.inspect(b'bvx2synthetic',codec)
        self.assertEqual(r['payload_label'],'UNKNOWN');codec.assert_not_called()
    def test_declared_size_overflow_negative_and_noncanonical(self):
        for n in (num(tool.MAX_RAW+1),num(0),der(2,b'\x80'),der(2,b'\0\x01')):
            r=self.inspect(im4p(b'bvx2synthetic',der(0x30,num(1)+n)))
            self.assertEqual(r['status'],'REFUSED')
    def test_lzfse_metadata_cannot_authorize_plaintext_identity(self):
        self.assertEqual(self.inspect(im4p(SAMPLES['31AF'],compression(len(SAMPLES['31AF']))))['status'],'REFUSED')
    def test_unsupported_lzss_never_invokes_codec(self):
        codec=mock.Mock();r=self.inspect(b'complzsssynthetic',codec)
        self.assertEqual(r['reason'],'CODEC_UNSUPPORTED');codec.assert_not_called()
    def test_codec_boundary_contract_failures(self):
        raw=SAMPLES['31AF'];encoded=b'bvx2synthetic'
        for returned in ((raw+b'x',len(encoded),True),(raw[:-1],len(encoded),True),
                         (raw,len(encoded)-1,True),(raw,float(len(encoded)),True),
                         (raw,len(encoded),False),(bytearray(raw),len(encoded),True),
                         [raw,len(encoded),True],(raw,len(encoded),True,'extra')):
            with self.subTest(form=str(type(returned))):
                r=self.inspect(im4p(encoded,compression(len(raw))),mock.Mock(return_value=returned))
                self.assertEqual(r['status'],'REFUSED');self.assertEqual(r['payload_label'],'UNKNOWN')
    def test_codec_exception_details_are_private(self):
        r=self.inspect(im4p(b'bvx2synthetic',compression(len(SAMPLES['31AF']))),mock.Mock(side_effect=RuntimeError('PRIVATE_CODEC_SECRET')))
        self.assertEqual(r['reason'],'CODEC_FAILED');self.assertNotIn('PRIVATE_CODEC_SECRET',json.dumps(r))
    def test_wrong_decoded_bytes_never_echoed(self):
        raw=b'X'*len(SAMPLES['31AF']);encoded=b'bvx2synthetic'
        r=self.inspect(im4p(encoded,compression(len(raw))),mock.Mock(return_value=(raw,len(encoded),True)))
        self.assertEqual(r['payload_label'],'UNKNOWN');self.assertNotIn(raw.decode(),json.dumps(r))
    def test_synthetic_gzip_with_bounded_test_provider(self):
        r=self.inspect(gzip.compress(SAMPLES['31AI'],mtime=0),test_gzip_codec)
        self.assertEqual(r['payload_label'],'31AI');self.assertTrue(r['decompressed'])
    def test_gzip_crc_and_truncated_stream_refused_by_provider(self):
        encoded=gzip.compress(SAMPLES['31AI'],mtime=0)
        corrupted=bytearray(encoded);corrupted[-8]^=1
        r=self.inspect(bytes(corrupted),test_gzip_codec);self.assertEqual(r['status'],'REFUSED')
        r=self.inspect(encoded[:-4]+struct.pack('<I',len(SAMPLES['31AI'])),mock.Mock(return_value=(SAMPLES['31AI'],len(encoded),False)))
        self.assertEqual(r['status'],'REFUSED')
    def test_gzip_concat_and_trailer_not_normalized(self):
        one=gzip.compress(SAMPLES['31AI'],mtime=0)
        for encoded in (one+one,one+b'trailer'+struct.pack('<I',len(SAMPLES['31AI']))):
            r=self.inspect(encoded,test_gzip_codec);self.assertEqual(r['status'],'REFUSED')
    def test_all_result_authority_flags_false_even_when_exact(self):
        r=self.inspect(SAMPLES['31AI'])
        for key in ('selection_verified','restoration_verified','bootability_verified','write_authorized',
                    'container_authenticity_verified','opaque_semantics_verified','decrypted'):
            self.assertIs(r[key],False)

class CLI(unittest.TestCase):
    def test_actual_frozen_pin_sources_unchanged(self):tool.verify_pin_sources()
    def test_default_and_help_have_no_reads(self):
        with mock.patch.object(tool,'verify_pin_sources') as pins,mock.patch.object(tool,'read_workspace') as read,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(tool.main([]),0);pins.assert_not_called();read.assert_not_called()
            with self.assertRaises(SystemExit):tool.main(['--help'])
            pins.assert_not_called();read.assert_not_called()
    def test_no_live_mode_exists(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):tool.main(['--live'])
    def test_outside_workspace_refused_without_private_output(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):rc=tool.main(['--fixture','/synthetic-private-outside/file'])
        self.assertEqual(rc,2);self.assertNotIn('synthetic-private-outside',out.getvalue())
    def test_fixture_symlink_refused_without_target_read(self):
        with tempfile.TemporaryDirectory(dir=HERE,prefix='.fixture-') as directory:
            target=Path(directory)/'target';target.write_bytes(b'PRIVATE_FIXTURE')
            link=Path(directory)/'link';link.symlink_to(target);out=io.StringIO()
            with contextlib.redirect_stdout(out):rc=tool.main(['--fixture',str(link)])
            self.assertEqual(rc,2);self.assertNotIn('PRIVATE_FIXTURE',out.getvalue())
    def test_frozen_source_mismatch_refused(self):
        with mock.patch.object(tool,'PIN_SOURCES',{'tools/boot-object31ag/read_selected.py':'0'*64}):
            with self.assertRaises(tool.Refusal):tool.verify_pin_sources()

if __name__=='__main__':unittest.main(verbosity=2)

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import copy
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('review31ah', Path(__file__).with_name('review31ah.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'ilinux-direct31ah-offline.tar.gz'
        self.names = [('ilinux-direct31ah/README.txt', b'offline only'),
                      ('ilinux-direct31ah/Image', b'owned synthetic payload')]
        self.make_archive(self.names)

    def make_archive(self, entries, special=None):
        with tarfile.open(self.path, 'w:gz', format=tarfile.USTAR_FORMAT) as tar:
            for name, data in entries:
                h = tarfile.TarInfo(name)
                h.size = len(data)
                tar.addfile(h, io.BytesIO(data))
            if special is not None:
                tar.addfile(special)
        b = self.path.read_bytes()
        self.m = {'schema':r.SCHEMA,'target':dict(r.TARGET),'native_authorized':False,
                  'restart_ready':False,'firmware_change_authorized':False,
                  'package':{'filename':self.path.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),
                  'files':{n:{'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()} for n,d in self.names}}}

    def set_raw(self, raw):
        """Bind mutated tar bytes to the manifest so parser checks are reached."""
        self.path.write_bytes(gzip.compress(raw, mtime=0))
        self.rehash_archive()

    def rehash_archive(self):
        compressed = self.path.read_bytes()
        self.m['package']['bytes'] = len(compressed)
        self.m['package']['sha256'] = hashlib.sha256(compressed).hexdigest()

    def raw(self):
        return gzip.decompress(self.path.read_bytes())

    def payload_end(self):
        return sum(512 + ((len(data)+511)//512)*512 for _,data in self.names)

    @staticmethod
    def extension_header(kind, size=0, format=tarfile.USTAR_FORMAT):
        header = tarfile.TarInfo('ilinux-direct31ah/METADATA')
        header.type = kind
        header.size = size
        return header.tobuf(format=format)

    def reject_extension(self, kind, size=0, body=b'', format=tarfile.USTAR_FORMAT):
        raw = self.extension_header(kind, size, format) + body + self.raw()
        self.set_raw(raw)
        with self.assertRaises(r.Refusal):
            r.review(self.m, self.path)

    def test_valid_without_extraction(self):
        result = r.review(self.m, self.path)
        self.assertEqual(result['status'], 'OFFLINE_INTEGRITY_PASS')
        self.assertFalse(result['native_ready'])
        self.assertFalse(result['extracted'])
        self.assertEqual(len(list(self.path.parent.iterdir())),1)

    def test_wrong_target(self):
        for target in ({'model':'Mac17,2','board':'j704','chip_id':'0x8142'}, {}, None):
            with self.subTest(target=target):
                m=copy.deepcopy(self.m);m['target']=target
                with self.assertRaises(r.Refusal):r.review(m,self.path)

    def test_native_flags_cannot_be_promoted(self):
        for key in ('native_authorized','restart_ready','firmware_change_authorized'):
            for value in (True,0,'false',None):
                m=copy.deepcopy(self.m);m[key]=value
                with self.subTest(key=key,value=value):
                    with self.assertRaises(r.Refusal):r.review(m,self.path)

    def test_compressed_corruption(self):
        with self.path.open('r+b') as f:
            f.seek(20);f.write(b'bad!')
        with self.assertRaises(r.Refusal):r.review(self.m,self.path)

    def test_member_digest(self):
        m=copy.deepcopy(self.m);m['package']['files'][self.names[0][0]]['sha256']='0'*64
        with self.assertRaises(r.Refusal):r.review(m,self.path)

    def test_member_size(self):
        m=copy.deepcopy(self.m);m['package']['files'][self.names[0][0]]['bytes']+=1
        with self.assertRaises(r.Refusal):r.review(m,self.path)

    def test_missing_member(self):
        self.make_archive(self.names[:1])
        with self.assertRaises(r.Refusal):r.review(self.m,self.path)

    def test_extra_member(self):
        self.make_archive(self.names+[('ilinux-direct31ah/EXTRA',b'x')])
        with self.assertRaises(r.Refusal):r.review(self.m,self.path)

    def test_duplicate_member(self):
        self.make_archive(self.names+self.names[:1])
        with self.assertRaises(r.Refusal):r.review(self.m,self.path)

    def test_symlink_member(self):
        h=tarfile.TarInfo('ilinux-direct31ah/README.txt');h.type=tarfile.SYMTYPE;h.linkname='/etc/passwd'
        self.make_archive(self.names[1:],h)
        with self.assertRaises(r.Refusal):r.review(self.m,self.path)

    def test_tar_path_traversal(self):
        for name in ('../escape','/ilinux-direct31ah/a','ilinux-direct31ah/../a','ilinux-direct31ah//a'):
            self.make_archive([(name,b'x')])
            with self.subTest(name=name):
                with self.assertRaises(r.Refusal):r.review(self.m,self.path)

    def test_manifest_path_traversal(self):
        m=copy.deepcopy(self.m);m['package']['files']['ilinux-direct31ah/../escape']=m['package']['files'].pop(self.names[0][0])
        with self.assertRaises(r.Refusal):r.review(m,self.path)

    def test_manifest_limits_and_boolean_size(self):
        for value in (True,-1,r.MAX_FILE+1):
            m=copy.deepcopy(self.m);m['package']['files'][self.names[0][0]]['bytes']=value
            with self.subTest(value=value):
                with self.assertRaises(r.Refusal):r.review(m,self.path)

    def test_archive_symlink(self):
        link=self.path.parent/'link';link.symlink_to(self.path)
        with self.assertRaises(r.Refusal):r.review(self.m,link)

    def test_duplicate_json_key(self):
        with self.assertRaises(r.Refusal):json.loads('{"schema":1,"schema":2}',object_pairs_hook=r.pairs)

    def test_valid_fixture_is_explicit_ustar(self):
        raw = self.raw()
        self.assertEqual(raw[257:265], b'ustar\x0000')
        self.assertEqual(r.review(self.m, self.path)['files_verified'], 2)

    def test_global_pax_header_refused(self):
        self.reject_extension(tarfile.XGLTYPE)

    def test_local_pax_header_refused(self):
        self.reject_extension(tarfile.XHDTYPE)

    def test_gnu_longname_header_refused(self):
        self.reject_extension(tarfile.GNUTYPE_LONGNAME)

    def test_gnu_longlink_header_refused(self):
        self.reject_extension(tarfile.GNUTYPE_LONGLINK)

    def test_gnu_sparse_header_refused(self):
        self.reject_extension(tarfile.GNUTYPE_SPARSE)

    def test_gnu_magic_refused_even_for_regular_file(self):
        raw = self.raw()
        name,data = self.names[0]
        header = tarfile.TarInfo(name)
        header.size = len(data)
        self.set_raw(header.tobuf(format=tarfile.GNU_FORMAT) + raw[512:])
        with self.assertRaises(r.Refusal):
            r.review(self.m, self.path)

    def test_metadata_size_is_rejected_before_reading_body(self):
        # A type marker is refused before a claimed giant metadata allocation.
        raw = self.extension_header(tarfile.XGLTYPE, r.MAX_TOTAL*4) + bytes(1024)
        self.set_raw(raw)
        with self.assertRaisesRegex(r.Refusal, 'nonregular_or_extension_header'):
            r.review(self.m, self.path)

    def test_former_hidden_pax_metadata_bound_regression(self):
        # This previously passed with expanded_bytes counting only file data.
        with tarfile.open(self.path, 'w:gz', format=tarfile.PAX_FORMAT,
                          pax_headers={'comment':'A'*65536}) as tar:
            for name,data in self.names:
                header = tarfile.TarInfo(name);header.size = len(data)
                tar.addfile(header, io.BytesIO(data))
        self.rehash_archive()
        self.assertLess(self.path.stat().st_size, 4096)
        with mock.patch.object(r, 'MAX_TOTAL', 4096):
            with self.assertRaisesRegex(r.Refusal, 'nonregular_or_extension_header'):
                r.review(self.m, self.path)

    def test_directory_header_refused(self):
        self.reject_extension(tarfile.DIRTYPE)

    def test_hardlink_header_refused(self):
        self.reject_extension(tarfile.LNKTYPE)

    def test_character_device_header_refused(self):
        self.reject_extension(tarfile.CHRTYPE)

    def test_fifo_header_refused(self):
        self.reject_extension(tarfile.FIFOTYPE)

    def test_nonzero_member_padding_refused(self):
        raw = bytearray(self.raw())
        raw[512+len(self.names[0][1])] = 1
        self.set_raw(bytes(raw))
        with self.assertRaisesRegex(r.Refusal, 'nonzero_member_padding'):
            r.review(self.m, self.path)

    def test_nonzero_data_after_archive_end_refused(self):
        self.set_raw(self.raw() + b'NONZERO TRAILER')
        with self.assertRaisesRegex(r.Refusal, 'data_after_tar_end'):
            r.review(self.m, self.path)

    def test_second_archive_after_end_refused(self):
        raw = self.raw()
        self.set_raw(raw + raw)
        with self.assertRaisesRegex(r.Refusal, 'data_after_tar_end'):
            r.review(self.m, self.path)

    def test_excessive_zero_trailer_refused(self):
        self.set_raw(self.raw()[:self.payload_end()+1024] + bytes(10241))
        with self.assertRaises(r.Refusal):
            r.review(self.m, self.path)

    def test_missing_both_tar_end_records_refused(self):
        self.set_raw(self.raw()[:self.payload_end()])
        with self.assertRaisesRegex(r.Refusal, 'missing_tar_end'):
            r.review(self.m, self.path)

    def test_missing_second_tar_end_record_refused(self):
        self.set_raw(self.raw()[:self.payload_end()+512])
        with self.assertRaisesRegex(r.Refusal, 'invalid_tar_end'):
            r.review(self.m, self.path)

    def test_nonzero_second_tar_end_record_refused(self):
        end = self.payload_end()
        raw = bytearray(self.raw()[:end+1024])
        raw[end+512] = 1
        self.set_raw(bytes(raw))
        with self.assertRaisesRegex(r.Refusal, 'invalid_tar_end'):
            r.review(self.m, self.path)

    def test_short_tar_header_refused(self):
        self.set_raw(self.raw()[:300])
        with self.assertRaisesRegex(r.Refusal, 'missing_tar_end'):
            r.review(self.m, self.path)

    def test_truncated_member_body_refused(self):
        self.set_raw(self.raw()[:512+len(self.names[0][1])-1])
        with self.assertRaisesRegex(r.Refusal, 'truncated_member'):
            r.review(self.m, self.path)

    def test_bad_header_checksum_refused(self):
        raw = bytearray(self.raw());raw[0] ^= 1
        self.set_raw(bytes(raw))
        with self.assertRaises(tarfile.HeaderError):
            r.review(self.m, self.path)

    def test_bad_gzip_crc_refused_after_package_digest_matches(self):
        compressed = bytearray(self.path.read_bytes());compressed[-8] ^= 1
        self.path.write_bytes(bytes(compressed));self.rehash_archive()
        with self.assertRaises(gzip.BadGzipFile):
            r.review(self.m, self.path)

    def test_truncated_gzip_trailer_refused(self):
        self.path.write_bytes(self.path.read_bytes()[:-4]);self.rehash_archive()
        with self.assertRaises(EOFError):
            r.review(self.m, self.path)

    def test_nongzip_bound_input_refused(self):
        self.path.write_bytes(b'NOT A GZIP FILE');self.rehash_archive()
        with self.assertRaises(gzip.BadGzipFile):
            r.review(self.m, self.path)

    def test_invalid_deflate_cli_has_controlled_json_refusal(self):
        # Valid gzip header, invalid DEFLATE BTYPE=3, then a dummy trailer.
        self.path.write_bytes(bytes.fromhex('1f8b08000000000002ff') + b'\x07' + bytes(8))
        self.rehash_archive()
        manifest = self.path.parent/'manifest.json'
        manifest.write_text(json.dumps(self.m))
        result = subprocess.run([sys.executable,'-I',str(Path(r.__file__)),
                                 '--manifest',str(manifest),'--package',str(self.path)],
                                capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout),
                         {'status':'REFUSED','read_only':True,'native_ready':False})
        self.assertNotIn('Traceback',result.stderr)

    def test_deep_manifest_cli_has_controlled_json_refusal(self):
        # Small malformed metadata must not escape the machine-readable refusal.
        manifest = self.path.parent/'manifest.json'
        manifest.write_text('['*2000 + '0' + ']'*2000)
        result = subprocess.run([sys.executable,'-I',str(Path(r.__file__)),
                                 '--manifest',str(manifest),'--package',str(self.path)],
                                capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout),
                         {'status':'REFUSED','read_only':True,'native_ready':False})
        self.assertNotIn('Traceback',result.stderr)

    def test_compressed_metadata_size_limits(self):
        for value in (True,0,r.MAX_COMPRESSED+1,'10'):
            changed = copy.deepcopy(self.m);changed['package']['bytes'] = value
            with self.subTest(value=value), self.assertRaises(r.Refusal):
                r.review(changed, self.path)

    def test_too_many_inventory_members_refused(self):
        changed = copy.deepcopy(self.m)
        changed['package']['files'] = {
            'ilinux-direct31ah/file'+str(i):{'bytes':1,'sha256':'0'*64}
            for i in range(r.MAX_FILES+1)}
        with self.assertRaisesRegex(r.Refusal, 'member_inventory'):
            r.review(changed, self.path)

    def test_total_inventory_size_refused_before_payload_read(self):
        changed = copy.deepcopy(self.m)
        changed['package']['files'] = {
            'ilinux-direct31ah/file'+str(i):{'bytes':r.MAX_FILE,'sha256':'0'*64}
            for i in range(5)}
        with self.assertRaisesRegex(r.Refusal, 'expanded_size'):
            r.review(changed, self.path)


if __name__ == '__main__':unittest.main()

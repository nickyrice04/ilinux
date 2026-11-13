#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic archive, RAM-root and scope refusals; no binaries are executed."""
import copy
import gzip
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest
from unittest import mock

spec=importlib.util.spec_from_file_location('direct31ai_package',Path(__file__).with_name('package.py'))
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool);p=tool.p

def manifest():
    entries={p.ROOT+n:{'bytes':1,'sha256':p.PINS.get(n,'0'*64)} for n in p.REQUIRED}
    return {'schema':tool.SCHEMA,'target':p.TARGET,'delivery':'SAME_USER_LOCAL_HANDOFF_ONLY',
        'bindings':copy.deepcopy(p.BINDINGS),'native_authorized':False,'restart_ready':False,
        'firmware_change_authorized':False,'public_binary_release':False,
        'package':{'filename':tool.FILENAME,'bytes':1,'sha256':'0'*64,'files':entries}}
def receipt():
    return {'schema':'ilinux-direct31ai-relink-v1','status':'PASS','scope':'GENERIC_LINUX_RELINK_ONLY',
        'collector_source_sha256':p.PINS['source/diag_init.c'],'object_sha256':'1'*64,
        'tested_executable_sha256':p.PINS['diagnostic/diag-init'],
        'relinked_executable_sha256':p.PINS['diagnostic/diag-init'],
        'byte_equal_to_tested_executable':True,'normal_selftest':'PASS','intentional_timeout_selftest':'PASS',
        'runtime_packages':{'glibc':'glibc 2.43+r22-2','gcc-libs':'gcc-libs 16.1.1-1'},
        'license_files':{name:{'bytes':4,'sha256':'2'*64} for name in p.NOTICE_PROVENANCE},
        'notice_provenance':copy.deepcopy(p.NOTICE_PROVENANCE),
        'runtime_specific_copyright_notices_complete':False,'public_libc_source_closure':'INCOMPLETE',
        'public_binary_release':False,'native_tested':False}
def tar_bytes(names=None,fmt=tarfile.USTAR_FORMAT,kind=tarfile.REGTYPE):
    names=names or [p.ROOT+'README.txt'];data=b'fixture';stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w',format=fmt) as tar:
        for name in names:
            info=tarfile.TarInfo(name);info.mode=0o644;info.type=kind
            if kind==tarfile.REGTYPE:info.size=len(data)
            else:info.linkname='outside'
            tar.addfile(info,io.BytesIO(data) if kind==tarfile.REGTYPE else None)
    entries={name:{'bytes':len(data),'sha256':p.sha(data)} for name in names}
    return stream.getvalue(),entries
def archive_check(raw,entries):
    encoded=gzip.compress(raw,mtime=0)
    return compressed_check(encoded,entries)
def compressed_check(encoded,entries):
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'bundle.tar.gz';path.write_bytes(encoded)
        return tool.read_archive(path,{'bytes':len(encoded),'sha256':p.sha(encoded),'files':entries})
def newc(name,content,mode,ino):
    encoded=name.encode()+b'\0';fields=[ino,mode,0,0,1,0,len(content),0,0,0,0,len(encoded),0]
    out=b'070701'+b''.join(f'{x:08x}'.encode() for x in fields)+encoded
    out+=b'\0'*(-len(out)%4);out+=content;out+=b'\0'*(-len(content)%4);return out
def root_blob(extra=False,mode=0o100755):
    body=b''
    for ino,name in enumerate(('dev','proc','sys','run'),1):body+=newc(name,b'',0o040755,ino)
    body+=newc('init',b'collector',mode,5)
    if extra:body+=newc('lib/modules/storage.ko',b'forbidden',0o100644,6)
    body+=newc('TRAILER!!!',b'',0,7)
    return gzip.compress(body,mtime=0)

class Manifest(unittest.TestCase):
    def test_local_scope(self):self.assertEqual(tool.validate_manifest(manifest())['filename'],tool.FILENAME)
    def test_public_release_rejected(self):
        m=manifest();m['public_binary_release']=True
        with self.assertRaises(p.Refusal):tool.validate_manifest(m)
    def test_native_authorization_not_inferred(self):
        m=manifest();m['native_authorized']=True
        with self.assertRaises(p.Refusal):tool.validate_manifest(m)
    def test_different_baseline_rejected(self):
        m=manifest();m['bindings']['baseline_aura_sha256']='f'*64
        with self.assertRaises(p.Refusal):tool.validate_manifest(m)
    def test_different_tested_kernel_rejected(self):
        m=manifest();m['package']['files'][p.ROOT+'linux/Image']['sha256']='f'*64
        with self.assertRaises(p.Refusal):tool.validate_manifest(m)
    def test_module_payload_rejected(self):
        m=manifest();m['package']['files'][p.ROOT+'modules/nvme.ko']={'bytes':0,'sha256':'0'*64}
        with self.assertRaises(p.Refusal):tool.validate_manifest(m)
    def test_traversal_rejected(self):
        with self.assertRaises(p.Refusal):tool.safe_name(p.ROOT+'licenses/glibc/../../secret')
    def test_duplicate_json_rejected(self):
        with self.assertRaises(p.Refusal):p.decode(b'{"public_binary_release":false,"public_binary_release":true}')
    def test_unknown_personal_metadata_rejected(self):
        m=manifest();m['serial']='SYNTHETIC_PRIVATE_MARKER'
        with self.assertRaises(p.Refusal):tool.validate_manifest(m)
    def test_unknown_package_metadata_rejected(self):
        m=manifest();m['package']['private_path']='SYNTHETIC_PRIVATE_MARKER'
        with self.assertRaises(p.Refusal):tool.validate_manifest(m)
    def test_nested_numeric_boolean_rejected(self):
        m=manifest();m['bindings']['native_authorized']=0
        with self.assertRaises(p.Refusal):tool.validate_manifest(m)
    def test_storage_policy_boolean_is_type_sensitive(self):
        policy=copy.deepcopy(p.STORAGE);policy['storage_filesystem_mounts_requested']=0
        self.assertFalse(p.typed_equal(policy,p.STORAGE))

class Archive(unittest.TestCase):
    def test_strict_memory_only_read(self):
        raw,entries=tar_bytes();files,total=archive_check(raw,entries)
        self.assertEqual(files[p.ROOT+'README.txt'],b'fixture');self.assertEqual(total,7)
    def test_duplicate_member_rejected(self):
        raw,entries=tar_bytes([p.ROOT+'README.txt']*2)
        with self.assertRaises(p.Refusal):archive_check(raw,entries)
    def test_symlink_member_rejected(self):
        raw,entries=tar_bytes(kind=tarfile.SYMTYPE)
        with self.assertRaises(p.Refusal):archive_check(raw,entries)
    def test_pax_metadata_rejected(self):
        raw,entries=tar_bytes([p.ROOT+'x'*120],fmt=tarfile.PAX_FORMAT)
        with self.assertRaises(p.Refusal):archive_check(raw,entries)
    def test_gnu_metadata_rejected(self):
        raw,entries=tar_bytes(fmt=tarfile.GNU_FORMAT)
        with self.assertRaises(p.Refusal):archive_check(raw,entries)
    def test_member_corruption_rejected(self):
        raw,entries=tar_bytes();raw=bytearray(raw);raw[512]^=1
        with self.assertRaises(p.Refusal):archive_check(raw,entries)
    def test_crc_corruption_rejected(self):
        raw,entries=tar_bytes();encoded=bytearray(gzip.compress(raw,mtime=0));encoded[-8]^=1
        with self.assertRaises(p.Refusal):compressed_check(encoded,entries)
    def test_concatenated_gzip_rejected(self):
        raw,entries=tar_bytes()
        with self.assertRaises(p.Refusal):compressed_check(gzip.compress(raw)+gzip.compress(b''),entries)
    def test_tar_hidden_payload_rejected(self):
        raw,entries=tar_bytes();raw=bytearray(raw);raw[-1]=1
        with self.assertRaises(p.Refusal):archive_check(raw,entries)
    def test_archive_truncation_rejected(self):
        raw,entries=tar_bytes()
        with self.assertRaises(p.Refusal):compressed_check(gzip.compress(raw)[:-1],entries)
    def test_compression_bomb_bound(self):
        raw,entries=tar_bytes()
        with mock.patch.object(tool,'MAX_TOTAL',16):
            with self.assertRaises(p.Refusal):archive_check(raw+bytes(2*1024*1024),entries)

class RAMRoot(unittest.TestCase):
    def test_only_whitelisted_ram_entries(self):self.assertEqual(p.initramfs(root_blob(),b'collector'),['dev','proc','sys','run','init'])
    def test_storage_module_rejected(self):
        with self.assertRaises(p.Refusal):p.initramfs(root_blob(extra=True),b'collector')
    def test_init_symlink_rejected(self):
        with self.assertRaises(p.Refusal):p.initramfs(root_blob(mode=0o120777),b'collector')
    def test_different_init_rejected(self):
        with self.assertRaises(p.Refusal):p.initramfs(root_blob(),b'other executable')
    def test_root_hidden_gzip_member_rejected(self):
        with self.assertRaises(p.Refusal):p.initramfs(root_blob()+gzip.compress(b''),b'collector')
    def test_wrong_elf_machine_rejected(self):
        data=bytearray(64);data[:6]=b'\x7fELF\x02\x01';struct.pack_into('<HH',data,16,2,62)
        with self.assertRaises(p.Refusal):p.elf(data,2)

class Relink(unittest.TestCase):
    def test_exact_local_receipt(self):self.assertIn('common/LGPL-2.1-or-later.txt',p.validate_relink(receipt()))
    def test_unproven_relink_rejected(self):
        r=receipt();r['byte_equal_to_tested_executable']=False
        with self.assertRaises(p.Refusal):p.validate_relink(r)
    def test_wrong_source_rejected(self):
        r=receipt();r['collector_source_sha256']='0'*64
        with self.assertRaises(p.Refusal):p.validate_relink(r)
    def test_license_path_escape_rejected_before_read(self):
        r=receipt();r['license_files']={'glibc/../../private':{'bytes':4,'sha256':'2'*64}}
        with self.assertRaises(p.Refusal):p.validate_relink(r)
    def test_personal_metadata_field_rejected(self):
        r=receipt();r['hostname']='SYNTHETIC_PRIVATE_VALUE'
        with self.assertRaises(p.Refusal):p.validate_relink(r)
    def test_runtime_version_path_rejected(self):
        r=receipt();r['runtime_packages']['glibc']='glibc /Users/private'
        with self.assertRaises(p.Refusal):p.validate_relink(r)
    def test_common_text_not_attribution_closure(self):
        r=receipt();r['runtime_specific_copyright_notices_complete']=True
        with self.assertRaises(p.Refusal):p.validate_relink(r)
    def test_common_text_source_cannot_be_relabelled(self):
        r=receipt();r['notice_provenance']['common/LGPL-2.1-or-later.txt']['kind']='COMPLETE_GLIBC_ATTRIBUTION'
        with self.assertRaises(p.Refusal):p.validate_relink(r)

class Publication(unittest.TestCase):
    def inputs(self,base):
        repo=base/'repo';kernel=base/'kernel';relink=base/'relink';vm=base/'vm.json'
        kernel.mkdir();relink.mkdir();vm.write_text('{}')
        for name in ('Image','kernel.config','t6050-j716c-diagnostic.dtb','diag-init','initramfs-direct31ah.cpio.gz','input-source-files.json'):(kernel/name).write_bytes(b'fixture')
        for path in ('kernel/experiments/direct31ah/linux/diag_init.c','native/boot/attempt31ah/manifest.json'):
            dest=repo/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b'fixture')
        (relink/'diag-init.o').write_bytes(b'fixture')
        (relink/'relink-result.json').write_text(json.dumps(receipt()))
        for name in p.NOTICE_PROVENANCE:
            path=relink/'licenses'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'copy')
        out=base/'output'/tool.FILENAME;manifest_path=base/'output'/'manifest.json'
        return repo,kernel,vm,relink,out,manifest_path
    def test_late_pin_failure_leaves_no_named_output(self):
        with tempfile.TemporaryDirectory() as directory:
            args=self.inputs(Path(directory))
            with mock.patch.object(p,'validate_payloads',return_value={}):
                with self.assertRaises(p.Refusal):tool.build(*args)
            self.assertFalse(args[-2].exists());self.assertFalse(args[-1].exists())
            self.assertEqual(list(args[-2].parent.iterdir()),[])
    def test_failed_manifest_publication_removes_only_own_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            args=self.inputs(Path(directory));real_link=os.link
            def link(source,dest):
                if Path(dest)==args[-1]:raise OSError('synthetic manifest publication failure')
                return real_link(source,dest)
            with mock.patch.object(p,'validate_payloads',return_value={}), \
                 mock.patch.object(tool,'validate_manifest',return_value={}), \
                 mock.patch.object(tool,'review',return_value={}), \
                 mock.patch.object(tool.os,'link',side_effect=link):
                with self.assertRaises(OSError):tool.build(*args)
            self.assertFalse(args[-2].exists());self.assertFalse(args[-1].exists())
            self.assertEqual(list(args[-2].parent.iterdir()),[])
    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            args=self.inputs(Path(directory));args[-2].parent.mkdir();args[-2].write_bytes(b'preserve')
            with self.assertRaises(p.Refusal):tool.build(*args)
            self.assertEqual(args[-2].read_bytes(),b'preserve')

if __name__=='__main__':unittest.main(verbosity=2)

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic kit intake/refusal controls; no binary execution, VM or Apple call."""
import contextlib
import copy
import gzip
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import tarfile
import tempfile
import types
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('kit31aj_test',HERE/'package.py')
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)

def files_fixture():
    return {name:('synthetic '+name).encode() for name in tool.MEMBERS}
def manifest_fixture():
    records={n:{'bytes':7,'sha256':tool.KERNEL_PINS.get(n,'1'*64)} for n in tool.MEMBERS}
    return {'schema':tool.SCHEMA,'target':dict(tool.TARGET),'delivery':'SAME_USER_LOCAL_HANDOFF_ONLY',
      'native_authorized':False,'restart_ready':False,'public_binary_release':False,
      'libc_source_closure':'INCOMPLETE','sources':dict(tool.HELPERS),
      'candidate':{'filename':'aura-31aj-inline.macho.gz','bytes':20,'sha256':'2'*64,
        'expanded_bytes':64,'expanded_sha256':'3'*64,'raw_bytes':tool.BASELINE_BYTES+1,'raw_sha256':'4'*64},
      'runtime':{'filename':'runtime-31aj.tar.gz','bytes':20,'sha256':'5'*64,'members':records},
      'readback':{'filename':'readback31aj','bytes':32,'sha256':'6'*64}}
def tar_fixture(files=None,names=None,mode=0o644,kind=tarfile.REGTYPE,fmt=tarfile.USTAR_FORMAT,pax=False):
    files=files or files_fixture();names=list(files) if names is None else names;out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w',format=fmt) as archive:
        for index,name in enumerate(names):
            info=tarfile.TarInfo(tool.PREFIX+name);info.mode=mode if index==0 else 0o644
            info.type=kind if index==0 else tarfile.REGTYPE
            info.mtime=0
            if pax and index==0:info.pax_headers={'comment':'SYNTHETIC_HIDDEN_METADATA'}
            if info.type==tarfile.REGTYPE:
                info.size=len(files[name]);archive.addfile(info,io.BytesIO(files[name]))
            else:info.linkname='outside';archive.addfile(info)
    return out.getvalue(),{name:tool.metadata(data) for name,data in files.items()}
def archived(raw):return gzip.compress(raw,mtime=0)
def static_elf(kind=2):
    data=bytearray(128);data[:6]=b'\x7fELF\x02\x01'
    struct.pack_into('<HH',data,16,kind,183);struct.pack_into('<H',data,52,64)
    if kind==2:
        struct.pack_into('<Q',data,32,64);struct.pack_into('<HH',data,54,56,1)
        struct.pack_into('<II6Q',data,64,1,5,0,0,0,len(data),len(data),4096)
    return bytes(data)

def semantic_fixture():
    files=files_fixture();files['diagnostic/init']=static_elf()
    files['relink/diag-init.o']=static_elf(1);files['notices/local-use.txt']=tool.NOTICE
    for name in ('diag_init.c','readable.h'):
        files['source/'+name]=(tool.ROOT/'kernel/experiments/direct31aj'/name).read_bytes()
    build={'status':'PASS','schema':'ilinux31aj-readable-build-v1','relink_equal_to_direct_build':True,
      'normal_selftest':'PASS','intentional_timeout_selftest':'PASS','native_tested':False,
      'source_binding':{'files':{n:tool.sha(files['source/'+n]) for n in ('diag_init.c','readable.h')}},
      'files':{'diag-init':tool.metadata(files['diagnostic/init']),
               'diag-init.o':tool.metadata(files['relink/diag-init.o']),
               'initramfs-direct31aj.cpio.gz':tool.metadata(files['diagnostic/initramfs.cpio.gz'])}}
    vm={'status':'PASS','scope':'GENERIC_ARM64_VZ_CONTROL','passing_cpu_ids':[0,1,2,3],
        'elapsed_monotonic_ns':60_000_000_001,'physical_m5_tested':False,
        'tested_inputs':{n:tool.metadata(files[n]) for n in
            ('linux/Image','diagnostic/initramfs.cpio.gz','diagnostic/init')}}
    files['evidence/build.json']=json.dumps(build).encode();files['evidence/vm.json']=json.dumps(vm).encode()
    base=0x1000;prefix=bytearray(base);struct.pack_into('<Q',prefix,0x818,base)
    raw=bytes(prefix)+b'synthetic-inline'
    candidate=bytes(0x10000)+raw+bytes(8192-len(raw))
    m=manifest_fixture();m['candidate'].update(raw_bytes=len(raw),raw_sha256=tool.sha(raw))
    inline=types.SimpleNamespace(verify_payload=mock.Mock(),initrd_info=mock.Mock(side_effect=lambda data:{'init':tool.metadata(files['diagnostic/init'])}))
    extended=types.SimpleNamespace(pad=types.SimpleNamespace(CODE_SIZE=8192,
        inspect=mock.Mock(return_value={'code':{'off':0x10000,'size':8192},'segments':{'one':{},'two':{}}})),
        inline=inline,wrapper_identity=mock.Mock())
    return files,m,candidate,base,tool.sha(bytes(prefix)),extended

class Manifest(unittest.TestCase):
    def test_complete_offline_manifest(self):self.assertIs(tool.manifest(manifest_fixture())['native_authorized'],False)
    def test_unknown_metadata_rejected(self):
        for where in ('top','record','runtime'):
            m=manifest_fixture()
            target=m if where=='top' else m['readback'] if where=='record' else m['runtime']
            target['secret']='SYNTHETIC_PRIVATE_MARKER'
            with self.assertRaises(tool.Refusal):tool.manifest(m)
    def test_authority_flags_require_literal_false(self):
        for name in ('native_authorized','restart_ready','public_binary_release'):
            for value in (True,0,None):
                m=manifest_fixture();m[name]=value
                with self.assertRaises(tool.Refusal):tool.manifest(m)
    def test_unchanged_kernel_pin_required(self):
        m=manifest_fixture();m['runtime']['members']['linux/Image']['sha256']='0'*64
        with self.assertRaises(tool.Refusal):tool.manifest(m)
    def test_unknown_member_or_source_traversal_rejected(self):
        for path in ('../outside','/absolute','source//empty'):
            m=manifest_fixture();m['sources'][path]='0'*64
            with self.assertRaises(tool.Refusal):tool.manifest(m)
        m=manifest_fixture();m['runtime']['members']['modules/storage.ko']={'bytes':1,'sha256':'0'*64}
        with self.assertRaises(tool.Refusal):tool.manifest(m)
    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(tool.Refusal):tool.decode(b'{"native_authorized":false,"native_authorized":true}')

class Framing(unittest.TestCase):
    def test_gzip_complete_stream_and_expansion_bound(self):
        blob=gzip.compress(b'fixture',mtime=0);self.assertEqual(tool.gunzip(blob,7),b'fixture')
        with self.assertRaises(tool.Refusal):tool.gunzip(blob,6)
        for changed in (blob[:-1],blob+gzip.compress(b''),blob+b'trailer'):
            with self.assertRaises(tool.Refusal):tool.gunzip(changed,100)
    def test_gzip_crc_corruption_rejected(self):
        blob=bytearray(gzip.compress(b'fixture',mtime=0));blob[-8]^=1
        with self.assertRaises(tool.Refusal):tool.gunzip(bytes(blob),100)
    def test_exact_fifteen_regular_members(self):
        raw,records=tar_fixture();actual=tool.archive(archived(raw),records)
        self.assertEqual(actual,files_fixture());self.assertEqual(len(actual),15)
    def test_duplicate_and_missing_members_rejected(self):
        files=files_fixture();names=list(files)
        for altered in (names+names[:1],names[:-1]):
            raw,records=tar_fixture(files,names=altered)
            with self.assertRaises(tool.Refusal):tool.archive(archived(raw),records)
    def test_permission_and_symlink_refusals(self):
        for options in ({'mode':0o755},{'kind':tarfile.SYMTYPE},{'kind':tarfile.DIRTYPE}):
            raw,records=tar_fixture(**options)
            with self.assertRaises(tool.Refusal):tool.archive(archived(raw),records)
    def test_hidden_pax_and_gnu_metadata_rejected(self):
        for options in ({'fmt':tarfile.PAX_FORMAT,'pax':True},{'fmt':tarfile.GNU_FORMAT}):
            raw,records=tar_fixture(**options)
            with self.assertRaises(tool.Refusal):tool.archive(archived(raw),records)
    def test_member_corruption_and_padding_refused(self):
        raw,records=tar_fixture();size=records[next(iter(records))]['bytes']
        for offset in (512,512+size):
            changed=bytearray(raw);changed[offset]^=1
            with self.assertRaises(tool.Refusal):tool.archive(archived(changed),records)
    def test_tar_tail_and_truncation_refused(self):
        raw,records=tar_fixture();changed=bytearray(raw);changed[-1]=1
        for altered in (changed,raw[:511]):
            with self.assertRaises(tool.Refusal):tool.archive(archived(altered),records)
    def test_regular_symlink_input_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'target';target.write_bytes(b'fixture')
            link=Path(directory)/'link';link.symlink_to(target)
            with self.assertRaises((tool.Refusal,OSError)):tool.regular(link,100)

class Semantics(unittest.TestCase):
    def inspect(self,fixture):
        files,m,candidate,base,digest,extended=fixture
        with mock.patch.object(tool,'BASELINE_BYTES',base),mock.patch.object(tool,'BASELINE',digest), \
             mock.patch.object(tool,'load_module',return_value=extended):
            return tool.inspect_payloads(files,m,candidate,tool.ROOT)
    def test_valid_metadata_and_byte_bindings_with_only_parser_dependencies_mocked(self):
        fixture=semantic_fixture();result=self.inspect(fixture)
        self.assertTrue(result['embedded_root_verified']);self.assertTrue(result['unchanged_kernel_verified'])
        self.assertEqual(fixture[-1].inline.verify_payload.call_count,1)
    def test_typed_vm_cpu_and_duration_required(self):
        for field,value in (('passing_cpu_ids',[False,True,2,3]),('elapsed_monotonic_ns',60_000_000_001.0),
                            ('elapsed_monotonic_ns',10**400),
                            ('physical_m5_tested',True),('scope','J716C_NATIVE')):
            fixture=semantic_fixture();vm=json.loads(fixture[0]['evidence/vm.json']);vm[field]=value
            fixture[0]['evidence/vm.json']=json.dumps(vm).encode()
            with self.assertRaises(tool.Refusal):self.inspect(fixture)
    def test_dynamic_interpreter_in_init_rejected(self):
        fixture=semantic_fixture();init=bytearray(fixture[0]['diagnostic/init']);struct.pack_into('<I',init,64,3)
        fixture[0]['diagnostic/init']=bytes(init)
        build=json.loads(fixture[0]['evidence/build.json']);build['files']['diag-init']=tool.metadata(bytes(init))
        fixture[0]['evidence/build.json']=json.dumps(build).encode()
        vm=json.loads(fixture[0]['evidence/vm.json']);vm['tested_inputs']['diagnostic/init']=tool.metadata(bytes(init))
        fixture[0]['evidence/vm.json']=json.dumps(vm).encode()
        with self.assertRaises(tool.Refusal):self.inspect(fixture)
    def test_stale_or_missing_vm_input_binding_rejected(self):
        for kind in ('missing','stale-root','extra'):
            fixture=semantic_fixture();vm=json.loads(fixture[0]['evidence/vm.json'])
            if kind=='missing':del vm['tested_inputs']
            elif kind=='stale-root':vm['tested_inputs']['diagnostic/initramfs.cpio.gz']['sha256']='0'*64
            else:vm['tested_inputs']['unknown']={'bytes':1,'sha256':'0'*64}
            fixture[0]['evidence/vm.json']=json.dumps(vm).encode()
            with self.assertRaises(tool.Refusal):self.inspect(fixture)
    def test_nonobject_evidence_refused_without_attribute_error(self):
        for name in ('evidence/build.json','evidence/vm.json'):
            fixture=semantic_fixture();fixture[0][name]=b'[]'
            with self.assertRaises(tool.Refusal):self.inspect(fixture)
    def test_changed_source_refused_before_import(self):
        fixture=semantic_fixture()
        with mock.patch.object(tool,'regular',return_value=b'changed'),mock.patch.object(tool,'load_module') as imported:
            with self.assertRaises(tool.Refusal):tool.inspect_payloads(fixture[0],fixture[1],fixture[2],tool.ROOT)
            imported.assert_not_called()

class WholeReader(unittest.TestCase):
    def prepared(self,folder):
        files=files_fixture();runtime=folder/'runtime-31aj.tar.gz'
        record,records=tool.build_archive(files,runtime)
        candidate=b'original-synthetic-candidate';compressed=gzip.compress(candidate,mtime=0)
        (folder/'aura-31aj-inline.macho.gz').write_bytes(compressed)
        helper=struct.pack('<II',0xfeedfacf,0x100000c)+bytes(24);(folder/'readback31aj').write_bytes(helper)
        (folder/'m1n1-boot021.bin').write_bytes(b'fixed-synthetic-rollback')
        m=manifest_fixture()
        m['runtime'].update(record,members=records)
        m['candidate'].update(tool.metadata(compressed),expanded_bytes=len(candidate),expanded_sha256=tool.sha(candidate))
        m['readback'].update(tool.metadata(helper))
        return m,files,candidate
    def test_full_container_flow_keeps_all_authority_false(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);m,files,candidate=self.prepared(folder)
            pins={name:tool.sha(files[name]) for name in tool.KERNEL_PINS}
            rollback=(folder/'m1n1-boot021.bin').read_bytes()
            with mock.patch.object(tool,'KERNEL_PINS',pins), \
                 mock.patch.object(tool,'ROLLBACK_BYTES',len(rollback)),mock.patch.object(tool,'ROLLBACK_SHA',tool.sha(rollback)), \
                 mock.patch.object(tool,'inspect_payloads',return_value={'embedded_root_verified':True}) as inspect:
                result=tool.review(m,folder)
            inspect.assert_called_once()
            self.assertEqual(result['files_verified'],4)
            self.assertEqual(inspect.call_args.args[0],files);self.assertEqual(inspect.call_args.args[2],candidate)
            for key in ('extracted','executed','device_opened','native_ready','native_authorized','public_binary_release'):
                self.assertIs(result[key],False)
    def test_changed_candidate_refused_before_semantic_import(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);m,files,_=self.prepared(folder)
            path=folder/m['candidate']['filename'];path.write_bytes(path.read_bytes()+b'x')
            with mock.patch.object(tool,'KERNEL_PINS',{n:tool.sha(files[n]) for n in tool.KERNEL_PINS}),mock.patch.object(tool,'inspect_payloads') as inspect:
                with self.assertRaises(tool.Refusal):tool.review(m,folder)
                inspect.assert_not_called()
    def test_missing_or_wrong_rollback_refused_before_semantics(self):
        for missing in (False,True):
            with tempfile.TemporaryDirectory() as directory:
                folder=Path(directory);m,files,_=self.prepared(folder)
                path=folder/'m1n1-boot021.bin';rollback=path.read_bytes()
                if missing:path.unlink()
                else:path.write_bytes(b'X'*len(rollback))
                with mock.patch.object(tool,'KERNEL_PINS',{n:tool.sha(files[n]) for n in tool.KERNEL_PINS}), \
                     mock.patch.object(tool,'ROLLBACK_BYTES',len(rollback)),mock.patch.object(tool,'ROLLBACK_SHA',tool.sha(rollback)), \
                     mock.patch.object(tool,'inspect_payloads') as inspect:
                    with self.assertRaises((tool.Refusal,OSError)):tool.review(m,folder)
                    inspect.assert_not_called()
    def test_cli_refusal_never_echoes_exception_or_private_path(self):
        output=io.StringIO()
        with mock.patch.object(sys,'argv',['package.py','--manifest','SYNTHETIC_PRIVATE_PATH','--folder','.']), \
             mock.patch.object(tool,'regular',side_effect=tool.Refusal('SYNTHETIC_PRIVATE_DETAIL')),contextlib.redirect_stdout(output):
            rc=tool.main()
        self.assertEqual(rc,2);self.assertNotIn('SYNTHETIC_PRIVATE',output.getvalue())
        self.assertFalse(json.loads(output.getvalue())['native_ready'])

if __name__=='__main__':unittest.main(verbosity=2)

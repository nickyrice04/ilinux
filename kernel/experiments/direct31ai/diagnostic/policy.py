# SPDX-License-Identifier: MIT
"""Frozen 31AH runtime identity reused by the separate 31AI local handoff."""
import hashlib
import importlib.util
import io
import json
import re
import struct
import sys
import zlib
from pathlib import Path

ROOT='ilinux-direct31ai/'
TARGET={'model':'Mac17,6','board':'j716c','chip_id':'0x6050'}
BASELINE_AURA='f73b8feea8f05a67408fb1a7e86b679ce33e9f2ff9ae97746549a126bf07cace'
AH_MANIFEST='bce19f957cbab84e09b3c575afce85d8ae619d3e4e64789cbefedce28d82f131'
FROZEN_BINDING='58d8989596dfa87c71dac3eb161148d5ae209d563c5ed4c85060bd6ba1c1ae03'
PINS={
 'linux/Image':'c01483f230aa64013b395291f8a5b8e38ed6c467b61e8a141c621938fda3a56f',
 'linux/kernel.config':'bba7ce251238c3cb6779d884a3442373443f7eed97e19f638afc08fdb9779fd8',
 'linux/t6050-j716c-diagnostic.dtb':'2c93df25dcbbc6939360ca84b76e21246ca30b6b7e2d0189afb0b1978332cb51',
 'diagnostic/diag-init':'c84152b6413e5dd60fdedd9f317035f61b57686c241ca10fd2bb1219a15c2c66',
 'diagnostic/initramfs.cpio.gz':'06254e6367b1a22f69db7b6edd0b03a8849d1ad9b7ebfb9698b72e88af688a56',
 'source/diag_init.c':'53b75d25c01b03a1c92832df91c51b875f03616847cbc674cce1c539cc729761',
 'evidence/source-bindings.json':FROZEN_BINDING,
 'evidence/vm.json':'bab097ae06e4984ba49e00ac59b093b732dfc31c2cdc316f304359738345fba2',
 'references/31ah-manifest.json':AH_MANIFEST,
}
REQUIRED=set(PINS)|{'README.txt','bindings.json','relink/diag-init.o','evidence/relink.json',
                    'policy/storage.json','notices/local-use.txt'}
STORAGE={'schema':'ilinux-direct31ai-storage-policy-v1','module_files_in_root':0,
 'module_loader_in_root':False,'block_device_opens_requested':False,
 'storage_filesystem_mounts_requested':False,'raw_mmio_access_requested':False,
 'frequency_writes_requested':False,'sep_driver_enabled':False,
 'nvme_sart':'MODULES_EXCLUDED_FROM_DIAGNOSTIC_ROOT',
 'persistent_storage_writes_requested':False,'native_behavior_verified':False}
NOTICE_PROVENANCE={
 'common/LGPL-2.1-or-later.txt':{'kind':'COMMON_SPDX_LICENSE_TEXT','source':'/usr/share/licenses/spdx/LGPL-2.1-or-later.txt'},
 'common/GPL-3.0-or-later.txt':{'kind':'COMMON_SPDX_LICENSE_TEXT','source':'/usr/share/licenses/spdx/GPL-3.0-or-later.txt'},
 'common/GPL-2.0-only.txt':{'kind':'COMMON_SPDX_LICENSE_TEXT','source':'/usr/share/licenses/spdx/GPL-2.0-only.txt'},
 'gcc/RUNTIME.LIBRARY.EXCEPTION':{'kind':'INSTALLED_GCC_PACKAGE_EXCEPTION','source':'/usr/share/licenses/gcc/RUNTIME.LIBRARY.EXCEPTION'}}
BINDINGS={'schema':'ilinux-direct31ai-runtime-binding-v1','target':TARGET,
 'baseline_aura_sha256':BASELINE_AURA,'prior_31ah_manifest_sha256':AH_MANIFEST,
 'tested_payload_sha256':PINS,'reconstructed_kernel_configuration':True,
 'physical_eighteen_core_tested':False,'native_authorized':False,'restart_ready':False,
 'public_binary_release':False,'glibc_public_source_closure':'INCOMPLETE'}
FROZEN_FILES={
 'virtualization/jobs/095-direct31ah-kernel/run.sh',
 'virtualization/jobs/095-direct31ah-kernel/diagnostic.config',
 *('kernel/experiments/direct31ah/linux/'+n for n in ('bind_sources.py','check_artifacts.py',
 'check_config.py','check_dtb.py','diag_init.c','fdt_read.py','make_diag_dt.py','make_initramfs.py','test_offline.py'))}

class Refusal(ValueError):pass
def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode('ascii')
def typed_equal(actual,expected):
    return type(actual) is type(expected) and canonical(actual)==canonical(expected)
def pairs(items):
    d={}
    for key,value in items:
        if key in d:raise Refusal('duplicate_json_key')
        d[key]=value
    return d
def decode(data):
    if len(data)>128*1024:raise Refusal('json_size_limit')
    try:return json.loads(data,object_pairs_hook=pairs)
    except (ValueError,UnicodeError,RecursionError):raise Refusal('invalid_json') from None

def initramfs(blob,executable):
    """Require the exact RAM-root whitelist, regular init and complete one gzip."""
    z=zlib.decompressobj(16+zlib.MAX_WBITS)
    try:data=z.decompress(blob,4*1024*1024+1)
    except zlib.error:raise Refusal('initramfs_gzip') from None
    if len(data)>4*1024*1024 or not z.eof or z.unused_data or z.unconsumed_tail:
        raise Refusal('initramfs_stream_bounds')
    at=0;names=[]
    for expected in ('dev','proc','sys','run','init','TRAILER!!!'):
        header=data[at:at+110]
        if len(header)!=110 or header[:6]!=b'070701':raise Refusal('initramfs_header')
        if any(c not in b'0123456789abcdefABCDEF' for c in header[6:]):raise Refusal('initramfs_numeric_encoding')
        try:h=[int(header[6+i*8:14+i*8],16) for i in range(13)]
        except ValueError:raise Refusal('initramfs_header') from None
        mode,uid,gid,links,mtime,size=h[1:7];namesize=h[11]
        wanted_mode=0 if expected=='TRAILER!!!' else 0o100755 if expected=='init' else 0o040755
        if mode!=wanted_mode or uid or gid or links!=1 or mtime or any(h[7:11]) or h[12] or namesize!=len(expected)+1:
            raise Refusal('initramfs_metadata')
        name=data[at+110:at+110+namesize]
        if name!=expected.encode()+b'\0':raise Refusal('initramfs_entry_whitelist')
        start=(at+110+namesize+3)&~3;end=start+size
        if end>len(data) or any(data[at+110+namesize:start]):raise Refusal('initramfs_bounds')
        content=data[start:end];after=(end+3)&~3
        if any(data[end:after]):raise Refusal('initramfs_padding')
        if expected=='init':
            if content!=executable:raise Refusal('initramfs_init_mismatch')
        elif content:raise Refusal('initramfs_unexpected_content')
        names.append(expected);at=after
    if at!=len(data):raise Refusal('initramfs_trailing_payload')
    return names[:-1]

def elf(data,kind):
    if len(data)<64 or data[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<HH',data,16)!=(kind,183):
        raise Refusal('elf_architecture_or_type')
    if kind==2:
        off=struct.unpack_from('<Q',data,32)[0];width,count=struct.unpack_from('<HH',data,54)
        if width!=56 or not 1<=count<=128 or off<64 or off+width*count>len(data):raise Refusal('elf_program_table')
        if any(struct.unpack_from('<I',data,off+i*width)[0]==3 for i in range(count)):
            raise Refusal('dynamic_interpreter_forbidden')

def validate_relink(r):
    if type(r) is not dict or r.get('schema')!='ilinux-direct31ai-relink-v1' or r.get('status')!='PASS' or r.get('scope')!='GENERIC_LINUX_RELINK_ONLY':raise Refusal('relink_scope')
    for name in ('collector_source_sha256','tested_executable_sha256','relinked_executable_sha256'):
        wanted=PINS['source/diag_init.c'] if name=='collector_source_sha256' else PINS['diagnostic/diag-init']
        if r.get(name)!=wanted:raise Refusal('relink_source_or_binary_identity')
    if r.get('byte_equal_to_tested_executable') is not True or r.get('normal_selftest')!='PASS' or r.get('intentional_timeout_selftest')!='PASS':raise Refusal('relink_control_failed')
    if r.get('public_binary_release') is not False or r.get('native_tested') is not False:raise Refusal('relink_scope_claim')
    wanted_keys={'schema','status','scope','collector_source_sha256','object_sha256',
     'tested_executable_sha256','relinked_executable_sha256','byte_equal_to_tested_executable',
     'normal_selftest','intentional_timeout_selftest','runtime_packages','license_files',
     'notice_provenance','runtime_specific_copyright_notices_complete','public_libc_source_closure',
     'public_binary_release','native_tested'}
    if set(r)!=wanted_keys or not re.fullmatch('[a-f0-9]{64}',str(r.get('object_sha256'))):raise Refusal('relink_fields')
    versions=r.get('runtime_packages');notices=r.get('license_files')
    if type(versions) is not dict or set(versions)!={'glibc','gcc-libs'}:raise Refusal('runtime_versions')
    for package,version in versions.items():
        if type(version) is not str or len(version)>160 or not version.startswith(package+' ') or not re.fullmatch(r'[A-Za-z0-9.:_+~ -]+',version):raise Refusal('runtime_version_encoding')
    if r.get('notice_provenance')!=NOTICE_PROVENANCE or r.get('runtime_specific_copyright_notices_complete') is not False or r.get('public_libc_source_closure')!='INCOMPLETE':raise Refusal('notice_provenance_or_closure')
    if type(notices) is not dict or set(notices)!=set(NOTICE_PROVENANCE):raise Refusal('runtime_notices')
    for name,record in notices.items():
        if type(name) is not str or name not in NOTICE_PROVENANCE:raise Refusal('runtime_notice_path')
        if type(record) is not dict or set(record)!={'bytes','sha256'} or type(record['bytes']) is not int or not 0<record['bytes']<=256*1024 or not re.fullmatch('[a-f0-9]{64}',str(record['sha256'])):raise Refusal('runtime_notice_metadata')
    return notices

def validate_payloads(files,repo):
    short={name.removeprefix(ROOT):data for name,data in files.items()}
    if not REQUIRED<=set(short):raise Refusal('missing_required_file')
    for name,digest in PINS.items():
        if sha(short[name])!=digest:raise Refusal('frozen_runtime_pin')
    if not typed_equal(decode(short['bindings.json']),BINDINGS) or not typed_equal(decode(short['policy/storage.json']),STORAGE):
        raise Refusal('runtime_or_storage_policy')
    ah=decode(short['references/31ah-manifest.json'])
    if ah['package']['files']['ilinux-direct31ah/aura/baseline/aura-boot-128m.macho']['sha256']!=BASELINE_AURA:raise Refusal('baseline_loader_identity')
    image=short['linux/Image']
    if len(image)<64 or image[56:60]!=b'ARM\x64':raise Refusal('arm64_image')
    _,size,flags=struct.unpack_from('<3Q',image,8)
    if ((flags>>1)&3)!=2 or not 0<size<=128*1024*1024 or len(image)>128*1024*1024:raise Refusal('image_pool_geometry')
    elf(short['diagnostic/diag-init'],2);elf(short['relink/diag-init.o'],1)
    entries=initramfs(short['diagnostic/initramfs.cpio.gz'],short['diagnostic/diag-init'])
    r=decode(short['evidence/relink.json']);notices=validate_relink(r)
    if sha(short['relink/diag-init.o'])!=r.get('object_sha256'):raise Refusal('relink_object_identity')
    if set(short)!=REQUIRED|{'licenses/'+n for n in notices}:raise Refusal('file_allowlist')
    for name,record in notices.items():
        content=short['licenses/'+name]
        if record!={'bytes':len(content),'sha256':sha(content)}:raise Refusal('license_file_identity')
        try:content.decode('utf-8')
        except UnicodeError:raise Refusal('license_text_encoding') from None
    binding=decode(short['evidence/source-bindings.json'])
    if binding.get('scope')!='OFFLINE_BUILD_SOURCE_BINDING' or set(binding.get('files',{}))!=FROZEN_FILES:raise Refusal('source_binding_inventory')
    for name,digest in binding['files'].items():
        path=Path(repo)/name
        if path.is_symlink() or sha(path.read_bytes())!=digest:raise Refusal('frozen_checkout_source_changed')
    helpers={}
    for name in ('check_config','check_dtb'):
        path=Path(repo)/'kernel/experiments/direct31ah/linux'/(name+'.py')
        spec=importlib.util.spec_from_file_location('direct31ai_'+name,path)
        module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);helpers[name]=module
    if helpers['check_config'].check(helpers['check_config'].parse(short['linux/kernel.config'].decode('ascii'))):raise Refusal('resolved_kernel_policy')
    dt=helpers['check_dtb'].inspect(short['linux/t6050-j716c-diagnostic.dtb'])
    if dt['drom_properties']!=0 or dt['native_qualified'] is not False:raise Refusal('dt_policy')
    vm=decode(short['evidence/vm.json'])
    if vm.get('scope')!='GENERIC_ARM64_VZ_CONTROL' or vm.get('status')!='PASS' or vm.get('passing_cpu_ids')!=[0,1,2,3] or vm.get('physical_m5_tested') is not False or vm.get('elapsed_monotonic_ns',0)<60000000000:raise Refusal('generic_vm_binding')
    return {'root_entries':entries,'cpu_nodes':dt['cpu_count'],'source_core_types':dt['cluster_core_types'],
            'source_core_types_are_not_online_evidence':True,'relink_equal_to_tested_binary':True,
            'module_files_in_root':0,'generic_vm_liveness_ns':vm['elapsed_monotonic_ns']}

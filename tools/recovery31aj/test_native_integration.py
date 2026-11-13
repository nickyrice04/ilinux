#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Cross-check the original C v2 phases using real own payloads and fake policy.

Only --snapshot-fixture / --validate-fixture-snapshot are invoked. No production
snapshot, RNG, capability, private-group, policy, volume or settings call occurs.
Temporary fixture data, fixed synthetic key and HMACs remain in ignored build/.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sp=importlib.util.spec_from_file_location('recovery31aj_flow_prepare',HERE/'prepare.py')
prep=importlib.util.module_from_spec(sp);sp.loader.exec_module(prep)


def require(ok):
    if not ok:raise ValueError('fixture flow refused')


def uuid(n):return f'{n:08x}-0000-0000-0000-{n:012x}' # Deliberately synthetic.


def policy(original=False,ctrr='enabled',selected=True):
    rows=['Security Mode: Full (smb0): absent' if original else 'Security Mode: Permissive (smb0, smb1): 1',
      'Current OS environment: one true recoveryOS','Pairing: '+('Unpaired' if original else 'Paired'),
      'Kernel CTRR Status: '+ctrr.title(),'(smb2): absent','(smb3): absent','(smb4): absent',
      '(sip0): 0','(sip1): absent','(sip3): absent','(sip2): '+('1' if ctrr=='disabled' else 'absent'),
      '(coih): '+('absent' if original or not selected else 'a'*96),'(nsih): '+'b'*96,
      '(lpnh): '+'c'*96,'(rpnh): '+'d'*96,'(rpnh): '+'e'*96,
      '(ronh): '+'f'*96,'(spih): '+'1'*96,'(stng): 3']
    return '\n'.join(rows)+'\n'


def metadata(selected,ctrr='enabled',has_object=True):
    def vol(name,role,n):return {'Name':name,'Roles':[role],'DeviceIdentifier':f'disk3s{n}','APFSVolumeUUID':uuid(n)}
    lab=vol('iLinux Boot Lab','System',1);original=vol('Macintosh HD','System',2)
    pb=vol('Preboot','Preboot',3);data=vol('iLinux Boot Lab - Data','Data',4)
    def info(v,mount,group):return {'Internal':True,'VolumeName':v['Name'],'MountPoint':mount,
      'VolumeUUID':v['APFSVolumeUUID'],'DeviceIdentifier':v['DeviceIdentifier'],
      'APFSContainerReference':'disk3','APFSVolumeGroupID':uuid(group)}
    return {'recovery':True,'root':True,'model':'Mac17,6',
      'lab_info':info(lab,'/Volumes/iLinux Boot Lab',11),'original_info':info(original,'/Volumes/Macintosh HD',22),
      'preboot_info':info(pb,'/Volumes/Preboot',33),'data_info':info(data,'/Volumes/iLinux Boot Lab - Data',11),
      'apfs_list':{'Containers':[{'ContainerReference':'disk3','Volumes':[lab,original,pb,data]}]},
      'lab_policy':policy(ctrr=ctrr,selected=has_object),'original_policy':policy(original=True),
      'selected_file':str(selected)}


def run(helper,profile_path,candidate,rollback,initial,root=ROOT):
    root=Path(root).resolve();pp=prep.checked_path(profile_path,root)
    require(0<pp.stat().st_size<=16384)
    raw=pp.read_bytes();p=prep.profile.load(raw)
    require(raw==prep.profile.canonical(p))
    paths={k:prep.checked_path(v,root) for k,v in {'helper':helper,'candidate':candidate,'rollback':rollback,'initial':initial}.items()}
    for role,item in p['files'].items():
        require(root/'build' in paths[role].parents)
        require(paths[role].stat().st_size==item['bytes'] and prep.sha_file(paths[role])==item['sha256'])
    require(root/'build' in paths['initial'].parents)
    require(paths['initial'].stat().st_size==442368 and prep.sha_file(paths['initial'])==prep.profile.INITIAL_SHA)
    checks=[]
    with tempfile.TemporaryDirectory(prefix='31aj-c-fixture-',dir=root/'build') as temp:
        work=Path(temp);key=work/'synthetic.key';key.write_bytes(b'SYNTHETIC-KEY-NOT-APPLE-00000000');key.chmod(0o600)
        # This fixed nonsecret synthetic key is never a production transaction key.
        require(key.stat().st_size==32)
        def invoke(args):
            require(args[0] in ('--snapshot-fixture','--validate-fixture-snapshot'))
            r=subprocess.run([str(paths['helper']),*map(str,args),'--profile',str(pp)],capture_output=True,timeout=20)
            require(not r.stderr and len(r.stdout)<=65536)
            return r.returncode,json.loads(r.stdout)
        count=0
        def snapshot(name,body,bound=True,ctrr='enabled',has_object=True,change=None):
            nonlocal count
            count+=1;v=metadata(body,ctrr,has_object)
            if change:change(v)
            f=work/(name+'.plist');f.write_bytes(plistlib.dumps(v));f.chmod(0o600)
            args=['--snapshot-fixture',f]+(['--comparison-key',key] if bound else [])
            rc,state=invoke(args);require(rc==0 and state['scope']=='SYNTHETIC_CONTROL')
            require(state['metadata_bound'] is bound and state['writes_authorized'] is False)
            out=work/(name+'.json');out.write_text(json.dumps(state));out.chmod(0o600)
            return out,state
        def phase(name,snapshot_path,expected=0,baseline=None,bound=True):
            args=['--validate-fixture-snapshot',snapshot_path,'--phase',name]
            if baseline is not None:args+=['--baseline',baseline]
            if bound:args+=['--comparison-key',key]
            rc,result=invoke(args);require(rc==expected)
            if expected==0:require(result['phase_valid'] is False and result['synthetic_control_pass'] is True)
            checks.append(name+':'+('synthetic-pass' if expected==0 else 'expected-refusal'))
        a,_=snapshot('admission',paths['initial'],bound=False);phase('initial-admission',a,bound=False)
        b,_=snapshot('baseline',paths['initial']);phase('initial',b)
        c,_=snapshot('candidate',paths['candidate']);phase('candidate',c,baseline=b)
        n,state=snapshot('none',paths['candidate'],ctrr='disabled',has_object=False)
        require(state['selected_payload']=='NONE');phase('raw-policy',n,baseline=b)
        phase('before-restore',n,baseline=b);phase('restored',n,expected=2,baseline=b)
        done,_=snapshot('restored',paths['rollback'],ctrr='disabled');phase('restored',done,baseline=b)
        changed,_=snapshot('changed-meta',paths['candidate'],change=lambda v:v.update(lab_policy=v['lab_policy'].replace('(stng): 3','(stng): 4')))
        phase('candidate',changed,expected=2,baseline=b)
        broken=work/'unknown-body';broken.write_bytes(b'SYNTHETIC UNKNOWN BODY')
        unknown,state=snapshot('unknown',broken);require(state['selected_payload']=='UNKNOWN')
        phase('initial',unknown,expected=2);phase('candidate',unknown,expected=2,baseline=b)
        phase('before-restore',unknown,baseline=b);phase('restored',unknown,expected=2,baseline=b)
        unreadable,state=snapshot('unreadable',work/'missing-body');require(state['selected_payload']=='UNKNOWN')
        phase('before-restore',unreadable,baseline=b);phase('restored',unreadable,expected=2,baseline=b)
        key.write_bytes(b'SYNTHETIC-SWAPPED-KEY-0000000000');require(key.stat().st_size==32)
        phase('candidate',c,expected=2,baseline=b)
    return {'schema':'ilinux31aj-real-c-fixture-flow-v1','checks':checks,'cf_fixture_snapshots':count,
      'artifact_identity':{'initial':'EXACT_31AF','candidate':'EXACT_CANDIDATE','rollback':'EXACT_BOOT021'},
      'policy_source':'SYNTHETIC_CF_FIXTURES','own_actual_payloads_verified':True,'synthetic_metadata_only':True,'system_rng_invoked':False,
      'live_recovery_invoked':False,'boot_settings_changed':False,'native_ready':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('helper','profile','candidate','rollback','initial'):parser.add_argument('--'+name,required=True,type=Path)
    a=parser.parse_args()
    try:result=run(a.helper,a.profile,a.candidate,a.rollback,a.initial)
    except (ValueError,OSError,KeyError,subprocess.SubprocessError):
        print('{"status":"REFUSED","live_recovery_invoked":false,"native_ready":false}');return 2
    print(json.dumps(result,sort_keys=True));return 0


if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Guest-only authentication/extraction into a fresh case-sensitive tmpfs."""
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import time

BAD={'BADSIG','ERRSIG','EXPSIG','EXPKEYSIG','REVKEYSIG','NO_PUBKEY','SIGEXPIRED','KEYREVOKED','FAILURE','ERROR','NODATA','UNEXPECTED'}


def load_pinned_manifest(inputs):
    """Use only this recipe's exact manifest, never a caller-supplied authority."""
    expected=Path(__file__).with_name('inputs.json').read_bytes()
    if not expected or len(expected)>65536:raise ValueError('recipe input manifest refused')
    descriptor=None
    try:
        descriptor=os.open(Path(inputs)/'manifest.json',os.O_RDONLY|os.O_NOFOLLOW)
        info=os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size!=len(expected):raise ValueError('input manifest differs from recipe')
        with os.fdopen(descriptor,'rb') as source:
            descriptor=None
            actual=source.read(len(expected)+1)
        if actual!=expected:raise ValueError('input manifest differs from recipe')
    except OSError:
        raise ValueError('input manifest unavailable or aliased') from None
    finally:
        if descriptor is not None:os.close(descriptor)
    return json.loads(expected)


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def selected_signer_current(home,fingerprint,expected_primary=None):
    if not re.fullmatch(r'[A-F0-9]{40}|[A-F0-9]{64}',fingerprint):raise ValueError('signer fingerprint refused')
    process=subprocess.run(['/usr/bin/gpg','--no-options','--homedir',str(home),'--batch','--no-autostart',
        '--with-colons','--fixed-list-mode','--list-keys',fingerprint],capture_output=True,text=True,timeout=20)
    if process.returncode:raise ValueError('selected signer key unavailable')
    selected=[];primary=[];pending=None
    for line in process.stdout.splitlines():
        row=line.split(':')
        if row[0] in ('pub','sub'):pending=row
        elif row[0]=='fpr' and pending is not None:
            if len(row)<10:raise ValueError('selected key record malformed')
            if pending[0]=='pub':primary.append((row[9],pending))
            if row[9]==fingerprint:selected.append(pending)
            pending=None
    if len(selected)!=1 or len(primary)!=1:raise ValueError('selected key not uniquely bound')
    if expected_primary is not None and primary[0][0]!=expected_primary:raise ValueError('signature primary key disagrees')
    for record in (primary[0][1],selected[0]):
        if len(record)<7 or record[1] in ('e','r','d','i'):raise ValueError('selected signer unusable')
        if len(record)>11 and 'D' in record[11]:raise ValueError('selected signer disabled')
        expires=record[6]
        if expires and expires!='0' and (not expires.isdecimal() or int(expires)<=int(time.time())):raise ValueError('selected signer expired')
    return True


def signature(home,signature,archive,require_trust,diagnostic=None):
    process=subprocess.run(['/usr/bin/gpg','--no-options','--homedir',str(home),'--batch',
        '--no-auto-key-retrieve','--no-auto-key-import','--no-autostart','--status-fd','1',
        '--verify',str(signature),str(archive)],capture_output=True,text=True,timeout=60)
    rows=[line[len('[GNUPG:] '):].split() for line in process.stdout.splitlines() if line.startswith('[GNUPG:] ')]
    if diagnostic is not None:
        diagnostic.write_text(json.dumps({'exit':process.returncode,'status':rows,'stderr':process.stderr[:16384]},indent=2)+'\n')
    if process.returncode or any(not row or row[0] in BAD for row in rows):raise ValueError('signature refused')
    valid=[r for r in rows if r[0]=='VALIDSIG'];good=[r for r in rows if r[0]=='GOODSIG']
    trust=[r[0] for r in rows if r[0] in ('TRUST_FULLY','TRUST_ULTIMATE')]
    all_trust=[r[0] for r in rows if r[0].startswith('TRUST_')]
    if len(valid)!=1 or len(good)!=1 or len(valid[0])<10 or len(good[0])<2 or (require_trust and (len(trust)!=1 or len(all_trust)!=1)):raise ValueError('signature authority incomplete')
    if valid[0][8] not in ('8','9','10','11'):raise ValueError('signature hash algorithm refused')
    if not valid[0][1].endswith(good[0][1]):raise ValueError('signature signer disagreement')
    if not require_trust and valid[0][1]!='108F66205EAEB0AAA8DD5E1C85AB96E6FA1BE5FE':raise ValueError('unexpected Rust release signer')
    selected_signer_current(home,valid[0][1],valid[0][10] if len(valid[0])>10 else None)
    # KEYEXPIRED can describe unrelated keys encountered during the whole
    # trustdb rebuild. It is not ignored on faith: actual signature expiry/
    # revocation statuses stay fatal and its exact primary/signing key must be
    # current above. No clock, weak-digest or trust override is used.
    return {'validsig':True,'signer_fingerprint':valid[0][1],'signature_hash_algorithm_id':int(valid[0][8]),'selected_signer_current':True,
        'unrelated_trustdb_expiry_notifications':sum(row[0]=='KEYEXPIRED' for row in rows),
        'existing_keyring_trust':trust[0] if trust else 'PINNED_OFFICIAL_RUST_KEY_ONLY'}


def extract(archive,target,kind):
    count=total=0
    with tarfile.open(archive,'r:*') as tar:
        for member in tar:
            parts=PurePosixPath(member.name).parts
            if not parts or member.name.startswith('/') or '..' in parts or '\0' in member.name:raise ValueError('archive path')
            if not (member.isfile() or member.isdir() or member.issym()):raise ValueError('archive type')
            if kind=='package':
                if parts[0]!='usr':continue
                relative=parts
            elif kind=='kernel':relative=parts[1:]
            else:
                if len(parts)<2 or parts[1]!=kind:continue
                relative=parts[2:]
            if not relative:continue
            count+=1;total+=member.size
            if count>200000 or member.size<0 or member.size>512*1024*1024 or total>8*1024**3:raise ValueError('archive bound')
            member.name='/'.join(relative)
            tar.extract(member,target,filter='data')
    return {'members':count,'expanded_bytes':total}


def main():
    inputs,work,out=map(Path,sys.argv[1:]);manifest=load_pinned_manifest(inputs)
    if work.exists() or out.is_symlink():raise ValueError('fresh guest work required')
    work.mkdir(mode=0o700)
    for row in manifest['files']:
        path=inputs/row['name']
        if path.is_symlink() or not path.is_file() or path.stat().st_size!=row['bytes'] or digest(path)!=row['sha256']:
            raise ValueError('input pin differs')
    public=work/'alarm-verification';public.mkdir(mode=0o700)
    for name in ('pubring.gpg','pubring.kbx','trustdb.gpg'):
        path=Path('/etc/pacman.d/gnupg')/name
        if path.is_file() and not path.is_symlink():shutil.copyfile(path,public/name)
    if not (public/'trustdb.gpg').is_file() or not any((public/name).is_file() for name in ('pubring.gpg','pubring.kbx')):
        raise ValueError('existing public trust missing')
    signatures=[];failures=[]
    for row in manifest['files']:
        if row['role']=='alarm_package':
            try:signatures.append(dict(name=row['name'],**signature(public,inputs/(row['name']+'.sig'),inputs/row['name'],True,out/(row['name']+'.signature-status.json'))))
            except ValueError:failures.append(row['name'])
    rust_home=work/'rust-verification';rust_home.mkdir(mode=0o700)
    subprocess.run(['/usr/bin/gpg','--no-options','--homedir',str(rust_home),'--batch','--no-autostart',
        '--import',str(inputs/'rust-key.gpg.ascii')],check=True,capture_output=True,timeout=20)
    try:signatures.append(dict(name='channel-rust-1.96.1.toml',**signature(rust_home,
        inputs/'channel-rust-1.96.1.toml.asc',inputs/'channel-rust-1.96.1.toml',False,out/'rust-manifest.signature-status.json')))
    except ValueError:failures.append('channel-rust-1.96.1.toml')
    (out/'signature-validation.json').write_text(json.dumps({'status':'REFUSED' if failures else 'PASS',
        'verified':signatures,'refused_inputs':failures,'package_extraction_started':False},indent=2)+'\n')
    if failures:raise ValueError('signature checks refused; no package extracted')
    tools=work/'toolchain';tools.mkdir(mode=0o700);rust=tools/'rust';rust.mkdir(mode=0o700)
    extracted=[]
    for row in manifest['files']:
        if row['role']=='alarm_package':extracted.append(dict(name=row['name'],**extract(inputs/row['name'],tools,'package')))
        elif row['role']=='rust_component':
            component={'rustc':'rustc','rust-std':'rust-std-aarch64-unknown-linux-gnu','rust-src':'rust-src'}[row['component']]
            extracted.append(dict(name=row['name'],**extract(inputs/row['name'],rust,component)))
    kernel=work/'linux';kernel.mkdir(mode=0o700)
    source=next(row for row in manifest['files'] if row['role']=='linux_source')
    extracted.append(dict(name=source['name'],**extract(inputs/source['name'],kernel,'kernel')))
    shutil.copyfile(inputs/'kernel.config',work/'kernel.config.source')
    shutil.copyfile(inputs/'kernel.config',kernel/'.config')
    # Versioned LLVM packages use a complete usr/lib/llvm22 prefix. Wrappers
    # confine their loader lookup without injecting LLVM libraries into Rust.
    llvm=tools/'usr/lib/llvm22';wrappers=tools/'bin';wrappers.mkdir(mode=0o700)
    library=':'.join(str(p) for p in (llvm/'lib',tools/'usr/lib'))
    for name in ('clang','clang++','ld.lld','llvm-ar','llvm-nm','llvm-objcopy','llvm-objdump','llvm-readelf','llvm-strip','llvm-ranlib','llvm-size','llvm-config'):
        target=llvm/'bin'/name
        if not target.is_file():raise ValueError('LLVM command absent '+name)
        path=wrappers/name
        path.write_text('#!/bin/sh\nLD_LIBRARY_PATH='+library+' exec '+str(target)+' "$@"\n');path.chmod(0o700)
    (wrappers/'rustc').write_text('#!/bin/sh\nunset LD_LIBRARY_PATH\nexec '+str(rust/'bin/rustc')+' "$@"\n');(wrappers/'rustc').chmod(0o700)
    bindgen=tools/'usr/bin/bindgen'
    (wrappers/'bindgen').write_text('#!/bin/sh\nLIBCLANG_PATH='+str(llvm/'lib')+' LD_LIBRARY_PATH='+library+' exec '+str(bindgen)+' "$@"\n');(wrappers/'bindgen').chmod(0o700)
    env=os.environ.copy();env['PATH']=str(wrappers)+':/usr/bin:/bin';env['RUST_LIB_SRC']=str(rust/'lib/rustlib/src/rust/library')
    versions={}
    for name in ('clang','ld.lld','rustc','bindgen'):
        process=subprocess.run([str(wrappers/name),'--version'],capture_output=True,text=True,check=True,env=env,timeout=20)
        versions[name]=process.stdout.strip()
    if not all(version in versions[name] for name,version in [('clang','22.1.8'),('ld.lld','22.1.8'),('rustc','1.96.1 (31fca3adb 2026-06-26)'),('bindgen','0.73.2')]):
        raise ValueError('exact tool version differs')
    if not (Path(env['RUST_LIB_SRC'])/'core/src/lib.rs').is_file():raise ValueError('Rust1.96 source missing')
    (out/'toolchain.json').write_text(json.dumps({'versions':versions,'signatures':signatures,
        'extracted':extracted,'bindgen_sha256':digest(bindgen),
        'publisher_bindgen_binary_identical':digest(bindgen)==manifest['publisher']['bindgen_binary_sha256'],
        'package_installations':0,'package_scripts_executed':0,'network_operations':0},indent=2)+'\n')
    (work/'environment.sh').write_text('export PATH='+str(wrappers)+':/usr/bin:/bin\nexport RUST_LIB_SRC='+env['RUST_LIB_SRC']+'\n')
    print('EXACT_VERSION_TOOLCHAIN_AUTHENTICATED_AND_ISOLATED')


if __name__=='__main__':main()

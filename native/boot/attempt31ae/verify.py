#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only delivery check. Trust the manifest only from the reviewed Git commit."""
import argparse,hashlib,json,tarfile,io
from pathlib import Path

def digest(b):return hashlib.sha256(b).hexdigest()
def verify(manifest, archive):
    meta=json.loads(Path(manifest).read_text());p=Path(archive)
    if p.is_symlink() or not p.is_file():raise ValueError('archive must be a regular file')
    expected=meta['archive'];size=expected['bytes']
    if type(size) is not int or not 0<size<=8*1024*1024 or p.stat().st_size!=size:raise ValueError('archive size mismatch')
    with p.open('rb') as f:data=f.read(size+1)
    if len(data)!=expected['bytes'] or len(data)>8*1024*1024 or digest(data)!=expected['sha256']:raise ValueError('archive size/hash mismatch')
    files=meta['files']
    if any(Path(n).name!=n or n in ('.','..') for n in files):raise ValueError('unsafe inventory name')
    wanted={'ilinux-31ae/'+n for n in files}|{'ilinux-31ae/SHA256SUMS'}
    sums=''.join(v['sha256']+'  '+n+'\n' for n,v in sorted(files.items())).encode()
    seen=set()
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
        for m in tar:
            if m.name not in wanted or m.name in seen or not m.isfile() or m.size>4*1024*1024:raise ValueError('unexpected, duplicate, linked or oversized member')
            seen.add(m.name);f=tar.extractfile(m)
            if f is None:raise ValueError('missing member content')
            b=f.read(m.size+1)
            if len(b)!=m.size:raise ValueError('member extent')
            n=m.name.removeprefix('ilinux-31ae/')
            if n=='SHA256SUMS':
                if b!=sums:raise ValueError('checksum inventory mismatch')
            elif len(b)!=files[n]['bytes'] or digest(b)!=files[n]['sha256']:raise ValueError('member hash mismatch')
    if seen!=wanted:raise ValueError('missing archive member')
    return {'status':'PASS','archive_sha256':digest(data),'verified_files':len(files),'native':'NOT_RUN','installation_performed':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,default=Path(__file__).with_name('manifest.json'));p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
    print(json.dumps(verify(a.manifest,a.archive),sort_keys=True))
if __name__=='__main__':main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Hash a source tar into Git objects without extracting or executing it."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import tarfile

COMMIT='a59e709c737777495c84541c6afb6c862bb79227'
TREE='5960d8ab03fef0f87e91e84fe1a8d969173da8de'


def object_hash(kind,data):
    return hashlib.sha1(kind+b' '+str(len(data)).encode()+b'\0'+data).digest()


def verify(path,expected_tree=TREE):
    archive_sha=hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):archive_sha.update(block)
    entries={};root=None;total=0;links=0
    with tarfile.open(path,'r|*') as source:
        for member in source:
            name=PurePosixPath(member.name)
            if name.is_absolute() or any(p in ('..','') for p in name.parts):raise ValueError('source path refused')
            if root is None:root=name.parts[0]
            if not name.parts or name.parts[0]!=root:raise ValueError('source root differs')
            relative=name.parts[1:]
            if not relative:
                if not member.isdir():raise ValueError('source root not directory')
                continue
            if '.git' in relative or len(relative)>64:raise ValueError('source path scope refused')
            if member.isdir():continue
            if relative in entries or len(entries)>=200000:raise ValueError('source duplicate/count refused')
            if member.issym():
                data=member.linkname.encode('utf-8','surrogateescape');mode=b'120000';links+=1
                digest=object_hash(b'blob',data);size=len(data)
            elif member.isfile():
                if member.size<0 or member.size>128*1024*1024:raise ValueError('source file bound')
                h=hashlib.sha1(b'blob '+str(member.size).encode()+b'\0');size=0
                stream=source.extractfile(member)
                for block in iter(lambda:stream.read(1024*1024),b''):h.update(block);size+=len(block)
                if size!=member.size:raise ValueError('source file truncated')
                digest=h.digest();mode=b'100755' if member.mode&0o111 else b'100644'
            else:raise ValueError('source special entry refused')
            total+=size
            if total>8*1024**3:raise ValueError('source expansion bound')
            entries[relative]=(mode,digest)
    directories={():{}}
    for parts,value in entries.items():
        for count in range(len(parts)):
            directory=parts[:count];directories.setdefault(directory,{})
            if count+1<len(parts):
                child=parts[:count+1]
                if parts[:count+1] in entries:raise ValueError('source file/directory collision')
                directories[directory][parts[count]]=child
            else:directories[directory][parts[count]]=value
    hashes={}
    for directory in sorted(directories,key=len,reverse=True):
        rows=[]
        for name,value in directories[directory].items():
            encoded=name.encode('utf-8','surrogateescape')
            if isinstance(value,tuple) and value and isinstance(value[0],bytes):mode,digest=value;sortkey=encoded
            else:mode,digest=b'40000',hashes[value];sortkey=encoded+b'/'
            rows.append((sortkey,mode+b' '+encoded+b'\0'+digest))
        hashes[directory]=object_hash(b'tree',b''.join(row for _,row in sorted(rows)))
    actual=hashes[()].hex()
    if actual!=expected_tree:raise ValueError('source Git tree mismatch')
    return {'schema':'ilinux096-source-tree-v1','archive_sha256':archive_sha.hexdigest(),
        'archive_bytes':Path(path).stat().st_size,'git_tree':actual,'files':len(entries),'expanded_bytes':total,
        'symlinks':links,'source_executed':False,'source_extracted_on_host':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('archive',type=Path)
    args=parser.parse_args();print(json.dumps(verify(args.archive),sort_keys=True))

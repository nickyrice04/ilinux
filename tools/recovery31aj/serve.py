#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Serve only the exact reviewed 31AJ Recovery page; no boot action or discovery.

Default binding is loopback with an ephemeral port. A later authorized operator
may explicitly supply one RFC1918 IPv4 address. Nothing starts on import or with
--check-only. No file downloads, listing, access log, upload or control API exist.
"""
import argparse
import hashlib
import importlib.util
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import select
import socket
import socketserver
import stat
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
INVENTORY='native/boot/attempt31aj-kit/source-sha256.txt'
PROFILE='native/boot/attempt31aj-kit/recovery-profile.json'
PAGE_LIMIT=256*1024
REQUEST_LIMIT=4096
CLIENT_SECONDS=1.0


def module(name):
    spec=importlib.util.spec_from_file_location('recovery31aj_serve_'+name,HERE/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


prepare=module('prepare')
profile=prepare.profile
renderer=prepare.renderer


def read_bounded(path,root,limit):
    """Bounded, same-fd regular-file read with no symlink path components."""
    checked=prepare.checked_path(path,root)
    parts=checked.relative_to(root).parts
    fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:
        for index,part in enumerate(parts):
            flags=os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NONBLOCK
            if index<len(parts)-1:flags|=os.O_DIRECTORY
            next_fd=os.open(part,flags,dir_fd=fd);os.close(fd);fd=next_fd
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 0<before.st_size<=limit:raise ValueError('file bound')
        pieces=[];total=0
        while True:
            data=os.read(fd,min(65536,limit+1-total))
            if not data:break
            pieces.append(data);total+=len(data)
            if total>limit:raise ValueError('file grew')
        after=os.fstat(fd)
        fields=('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns')
        if total!=before.st_size or any(getattr(before,k)!=getattr(after,k) for k in fields):raise ValueError('file changed')
        return b''.join(pieces)
    finally:os.close(fd)


def source_closure(root):
    """Validate the fixed inventory with prepare's path grammar and bounded reads."""
    inventory=read_bounded(INVENTORY,root,256*1024)
    records={}
    lines=inventory.decode('ascii').splitlines()
    if not 1<=len(lines)<=2048:raise ValueError('inventory count')
    for line in lines:
        match=re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)',line)
        if not match:raise ValueError('inventory grammar')
        digest,name=match.groups();path=PurePosixPath(name)
        if path.is_absolute() or str(path)!=name or '..' in path.parts or name in records:raise ValueError('inventory path')
        data=read_bounded(name,root,8*1024*1024)
        if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('inventory mismatch')
        records[name]=digest
    required={'tools/recovery31aj/'+n for n in ('profile.py','model.py','render.py','prepare.py','test_recovery.py','README.md','serve.py','test_serve.py')}
    if not required|{PROFILE}<=set(records):raise ValueError('incomplete source closure')
    return inventory,records


def load_page(page,root=ROOT):
    root=Path(root).resolve()
    path=prepare.checked_path(page,root)
    if root/'build' not in path.parents:raise ValueError('page must be below build')
    inventory,records=source_closure(root)
    data=read_bounded(PROFILE,root,16384)
    if hashlib.sha256(data).hexdigest()!=records[PROFILE]:raise ValueError('profile inventory binding')
    value=profile.load(data)
    if profile.canonical(value)!=data:raise ValueError('canonical Git profile required')
    expected=renderer.page(value).encode('utf-8')
    actual=read_bounded(path,root,PAGE_LIMIT)
    if actual!=expected or not 0<len(expected)<=PAGE_LIMIT:raise ValueError('exact rendered page required')
    # Recheck the fixed source closure after rendering; served bytes then stay in memory.
    if source_closure(root)!=(inventory,records):raise ValueError('source changed')
    return actual,{'schema':'ilinux31aj-fixed-page-v1','page_bytes':len(actual),
        'page_sha256':hashlib.sha256(actual).hexdigest(),
        'profile_sha256':profile.digest(value),
        'source_inventory_sha256':hashlib.sha256(inventory).hexdigest(),
        'verified_source_count':len(records),'write_authorized':False,'native_ready':False}


def bind_address(text):
    try:address=ipaddress.IPv4Address(text)
    except ipaddress.AddressValueError as error:raise ValueError('literal IPv4 required') from error
    private=tuple(ipaddress.IPv4Network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'))
    if str(address)!=text or not(address==ipaddress.IPv4Address('127.0.0.1') or any(address in net for net in private)):
        raise ValueError('loopback or explicit RFC1918 IPv4 required')
    return text


def request(data):
    """Narrow HTTP parser: bounded headers, GET/HEAD, exact two route strings."""
    if not data.endswith(b'\r\n\r\n') or len(data)>REQUEST_LIMIT:return 400,False
    lines=data[:-4].split(b'\r\n')
    if not 1<=len(lines)<=33:return 400,False
    if any(not line or len(line)>1024 or any(c<32 or c>=127 for c in line) for line in lines):return 400,False
    fields=lines[0].split(b' ')
    if len(fields)!=3 or fields[2] not in (b'HTTP/1.0',b'HTTP/1.1'):return 400,False
    method,path,_=fields
    seen=set()
    for line in lines[1:]:
        if b':' not in line:return 400,False
        name,value=line.split(b':',1);name=name.lower();value=value.strip()
        if not re.fullmatch(rb'[a-z0-9!#$%&\'*+.^_`|~-]+',name) or name in seen:return 400,False
        seen.add(name)
        if name==b'transfer-encoding' or(name==b'content-length' and value!=b'0'):return 400,False
    if method not in (b'GET',b'HEAD'):return 405,False
    if path not in (b'/',b'/31aj'):return 404,method==b'HEAD'
    return 200,method==b'HEAD'


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        end=min(self.server.deadline,time.monotonic()+CLIENT_SECONDS)
        client=self.request;client.setblocking(False);data=bytearray();code=400;head=False
        try:
            while time.monotonic()<end and len(data)<=REQUEST_LIMIT:
                remaining=end-time.monotonic()
                if remaining<=0 or not select.select([client],[],[],remaining)[0]:return
                chunk=client.recv(min(1024,REQUEST_LIMIT+1-len(data)))
                if not chunk:return
                data.extend(chunk)
                if b'\r\n\r\n' in data:code,head=request(bytes(data));break
            else:
                if time.monotonic()>=end:return
            body=self.server.page if code==200 else b'REFUSED\n'
            status={200:'OK',400:'Bad Request',404:'Not Found',405:'Method Not Allowed'}[code]
            header=(f'HTTP/1.0 {code} {status}\r\nContent-Length: {len(body)}\r\n'
                'Content-Type: text/html; charset=utf-8\r\nConnection: close\r\n'
                'Cache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n'
                "Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'\r\n\r\n").encode('ascii')
            output=memoryview(header+(b'' if head else body))
            while output and time.monotonic()<end:
                remaining=end-time.monotonic()
                if remaining<=0 or not select.select([],[client],[],remaining)[1]:return
                sent=client.send(output)
                if sent<=0:return
                output=output[sent:]
        except (OSError,ValueError):return


class Server(socketserver.TCPServer):
    allow_reuse_address=False
    request_queue_size=4
    def handle_error(self,request,client_address):pass


def make_server(page,bind='127.0.0.1',port=0):
    if type(page) is not bytes or not 0<len(page)<=PAGE_LIMIT:raise ValueError('page bound')
    bind=bind_address(bind)
    if type(port) is not int or not 0<=port<=65535:raise ValueError('port bound')
    server=Server((bind,port),Handler);server.page=page;server.deadline=time.monotonic()
    return server


def serve(server,seconds):
    if type(seconds) is not int or not 1<=seconds<=1800:raise ValueError('lifetime bound')
    server.deadline=time.monotonic()+seconds
    while time.monotonic()<server.deadline:
        server.timeout=min(0.1,max(0,server.deadline-time.monotonic()))
        server.handle_request()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--page',required=True,help='Exact generated recovery.html below workspace build/')
    parser.add_argument('--bind',type=bind_address,default='127.0.0.1',help='Default loopback; explicit RFC1918 literal only for later authorized LAN use')
    parser.add_argument('--port',type=int,default=0,help='0 selects an ephemeral port')
    parser.add_argument('--seconds',type=int,default=600,help='Bounded lifetime, 1 through 1800 seconds')
    parser.add_argument('--check-only',action='store_true',help='Verify bytes/closure only; do not create any socket')
    args=parser.parse_args()
    try:
        if not 0<=args.port<=65535 or not 1<=args.seconds<=1800:raise ValueError('bounds')
        page,report=load_page(args.page)
        if args.check_only:print(json.dumps(dict(report,status='EXACT_PAGE_VERIFIED',server_started=False),sort_keys=True));return 0
        with make_server(page,args.bind,args.port) as server:
            host,port=server.server_address
            print(json.dumps(dict(report,status='FIXED_PAGE_SERVING',url=f'http://{host}:{port}/31aj',seconds=args.seconds),sort_keys=True),flush=True)
            serve(server,args.seconds)
        return 0
    except KeyboardInterrupt:return 0
    except (ValueError,OSError,UnicodeError):
        print('{"status":"REFUSED","write_authorized":false,"native_ready":false}');return 2


if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic byte/closure controls and bounded loopback only; never LAN/Recovery."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('recovery31aj_fixed_server',HERE/'serve.py')
server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)


def sha(data):return hashlib.sha256(data).hexdigest()


class FixedPage(unittest.TestCase):
    def setUp(self):
        build=ROOT/'build/31aj-server-tests';build.mkdir(parents=True,exist_ok=True)
        self.root=Path(tempfile.mkdtemp(prefix='synthetic-',dir=build));self.addCleanup(shutil.rmtree,self.root)
        self.value={'schema':'ilinux31aj-recovery-profile-v1','target':server.profile.TARGET,
            'files':{'candidate':{'name':'candidate.macho','bytes':65536,'sha256':'a'*64},
                     'rollback':{'name':'m1n1-boot021.bin','bytes':server.profile.ROLLBACK_BYTES,'sha256':server.profile.ROLLBACK_SHA},
                     'helper':{'name':'ilinux31aj-reader','bytes':12345,'sha256':'b'*64}},
            'native_deadline_ms':90000,'raw_policy_strategy':'ctrr_only','initial_payload':'31AF',
            'final_payload':'BOOT021','publication_authorizes_writes':False}
        self.files={}
        for name in ('profile.py','model.py','render.py','prepare.py','test_recovery.py','README.md','serve.py','test_serve.py'):
            self.write('tools/recovery31aj/'+name,b'ORIGINAL SYNTHETIC SOURCE FIXTURE\n')
        self.write(server.PROFILE,server.profile.canonical(self.value))
        self.inventory=self.root/server.INVENTORY
        self.pin()
        self.page=self.root/'build/fixture/recovery.html';self.page.parent.mkdir(parents=True)
        self.expected=server.renderer.page(self.value).encode();self.page.write_bytes(self.expected)

    def write(self,name,data):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);self.files[name]=path

    def pin(self):
        data=''.join(sha(path.read_bytes())+'  '+name+'\n' for name,path in sorted(self.files.items()))
        self.inventory.parent.mkdir(parents=True,exist_ok=True);self.inventory.write_text(data)

    def load(self):return server.load_page(self.page,self.root)

    def test_exact_rendered_page_and_fixed_source_closure(self):
        page,report=self.load();self.assertEqual(page,self.expected);self.assertEqual(report['page_bytes'],len(page));self.assertEqual(report['page_sha256'],sha(page));self.assertEqual(report['verified_source_count'],9);self.assertFalse(report['native_ready']);self.assertFalse(report['write_authorized'])

    def test_page_changed_extra_or_truncated_bytes_refused(self):
        for data in (self.expected+b'X',self.expected[:-1],b'UNREVIEWED PRIVATE-MARKER'):
            self.page.write_bytes(data)
            with self.assertRaises(ValueError):self.load()

    def test_page_bound_empty_and_directory_refused(self):
        for data in (b'',b'x'*(server.PAGE_LIMIT+1)):
            self.page.write_bytes(data)
            with self.assertRaises(ValueError):self.load()
        self.page.unlink();self.page.mkdir()
        with self.assertRaises(ValueError):self.load()

    def test_page_must_be_below_build_without_symlink_or_traversal(self):
        outside=self.root/'recovery.html';outside.write_bytes(self.expected)
        with self.assertRaises(ValueError):server.load_page(outside,self.root)
        target=self.page.with_name('target.html');self.page.rename(target);self.page.symlink_to(target)
        with self.assertRaises(ValueError):self.load()
        with self.assertRaises(ValueError):server.load_page(self.root/'build/fixture/../fixture/target.html',self.root)

    def test_directory_symlink_refused(self):
        directory=self.page.parent;other=directory.with_name('other');directory.rename(other);directory.symlink_to(other,target_is_directory=True)
        with self.assertRaises(ValueError):self.load()

    def test_source_changed_or_missing_is_refused(self):
        path=self.files['tools/recovery31aj/render.py'];path.write_bytes(b'CHANGED SOURCE')
        with self.assertRaises(ValueError):self.load()
        path.unlink()
        with self.assertRaises(ValueError):self.load()

    def test_source_symlink_and_size_limit_refused(self):
        path=self.files['tools/recovery31aj/render.py'];target=path.with_name('other.py');path.rename(target);path.symlink_to(target)
        with self.assertRaises(ValueError):self.load()
        path.unlink();target.rename(path)
        with path.open('wb') as stream:stream.truncate(8*1024*1024+1)
        with self.assertRaises(ValueError):self.load()

    def test_inventory_grammar_duplicate_and_traversal_refused(self):
        original=self.inventory.read_text()
        for suffix in (original.splitlines()[0]+'\n','a'*64+'  ../outside\n','a'*64+'  /outside\n','NOT A SOURCE PIN\n'):
            self.inventory.write_text(original+suffix)
            with self.assertRaises(ValueError):self.load()

    def test_inventory_bound_symlink_and_missing_refused(self):
        self.inventory.write_bytes(b'x'*(256*1024+1))
        with self.assertRaises(ValueError):self.load()
        self.pin();target=self.inventory.with_name('other.txt');self.inventory.rename(target);self.inventory.symlink_to(target)
        with self.assertRaises(ValueError):self.load()
        self.inventory.unlink()
        with self.assertRaises(ValueError):self.load()

    def test_server_tests_and_canonical_profile_must_be_in_inventory(self):
        for name in ('tools/recovery31aj/serve.py','tools/recovery31aj/test_serve.py',server.PROFILE):
            path=self.files.pop(name);self.pin()
            with self.assertRaises(ValueError):self.load()
            self.files[name]=path
        self.pin()

    def test_profile_canonical_bytes_not_merely_json_equivalence(self):
        self.files[server.PROFILE].write_text(json.dumps(self.value));self.pin()
        with self.assertRaises(ValueError):self.load()

    def test_profile_invalid_scope_or_unknown_keys_refused(self):
        for field,value in (('publication_authorizes_writes',True),('personal_id','PRIVATE-MARKER')):
            invalid=dict(self.value);invalid[field]=value
            self.files[server.PROFILE].write_text(json.dumps(invalid));self.pin()
            with self.assertRaises(ValueError):self.load()

    def test_source_change_during_render_refused(self):
        render=server.renderer.page
        def changed(value):
            self.files['tools/recovery31aj/model.py'].write_bytes(b'CHANGED DURING RENDER')
            return render(value)
        with mock.patch.object(server.renderer,'page',side_effect=changed):
            with self.assertRaises(ValueError):self.load()

    def test_profile_render_read_is_bound_to_inventory_even_if_swap_reverts(self):
        original=server.read_bounded;calls=0
        altered=dict(self.value);altered['native_deadline_ms']=45000
        self.page.write_bytes(server.renderer.page(altered).encode())
        def swap(path,root,limit):
            nonlocal calls
            if str(path)==server.PROFILE:
                calls+=1
                if calls==2:return server.profile.canonical(altered)
            return original(path,root,limit)
        with mock.patch.object(server,'read_bounded',side_effect=swap):
            with self.assertRaisesRegex(ValueError,'profile inventory binding'):self.load()


class Protocol(unittest.TestCase):
    def test_bind_is_literal_loopback_or_rfc1918_only(self):
        for value in ('127.0.0.1','10.1.2.3','172.16.0.1','172.31.255.254','192.168.1.2'):
            self.assertEqual(server.bind_address(value),value)
        for value in ('0.0.0.0','localhost','example.com','8.8.8.8','169.254.1.2','172.32.0.1','::1','127.0.0.2','010.1.2.3','192.0.2.1'):
            with self.assertRaises(ValueError):server.bind_address(value)

    def test_get_and_head_only_two_exact_routes(self):
        for route in (b'/',b'/31aj'):
            for method,head in ((b'GET',False),(b'HEAD',True)):
                self.assertEqual(server.request(method+b' '+route+b' HTTP/1.1\r\nHost: localhost\r\n\r\n'),(200,head))

    def test_artifact_path_query_escape_and_other_routes_refused(self):
        for route in (b'/candidate.macho',b'/profile.json',b'/restore-paste.txt',b'/31aj?x=1',b'/31aj/',b'/%2e%2e/',b'/../',b'/favicon.ico',b'http://other/31aj'):
            self.assertEqual(server.request(b'GET '+route+b' HTTP/1.1\r\n\r\n')[0],404)

    def test_no_upload_body_or_header_smuggling(self):
        for value in (b'POST /31aj HTTP/1.1\r\n\r\n',b'PUT / HTTP/1.0\r\n\r\n'):
            self.assertEqual(server.request(value)[0],405)
        for value in (b'GET / HTTP/1.1\r\nContent-Length: 1\r\n\r\nX',b'GET / HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n',b'GET / HTTP/1.1\r\nHost: one\r\nHost: two\r\n\r\n',b'GET / HTTP/1.1\r\n folded\r\n\r\n',b'GET / HTTP/1.1\n\n',b'GET / HTTP/2\r\n\r\n'):
            self.assertEqual(server.request(value)[0],400)

    def test_header_bytes_count_and_line_lengths_bounded(self):
        for value in (b'GET / HTTP/1.0\r\nX: '+b'a'*1024+b'\r\n\r\n',b'GET / HTTP/1.0\r\n'+b'X: a\r\n'*33+b'\r\n',b'GET / HTTP/1.0\r\nX: '+b'a'*4096+b'\r\n\r\n',b'GET / HTTP/1.0\r\nX: \x00\r\n\r\n'):
            self.assertEqual(server.request(value)[0],400)

    def test_make_server_validates_before_binding(self):
        with mock.patch.object(server.Server,'__init__',side_effect=AssertionError('must not bind')):
            for page,bind,port in ((b'','127.0.0.1',0),(b'x','0.0.0.0',0),(b'x','127.0.0.1',65536),(b'x'*(server.PAGE_LIMIT+1),'127.0.0.1',0)):
                with self.assertRaises(ValueError):server.make_server(page,bind,port)

    def test_check_only_never_creates_socket_or_prints_private_paths(self):
        out=io.StringIO()
        with mock.patch.object(sys,'argv',['serve.py','--page','build/PRIVATE-MARKER/recovery.html','--check-only']),mock.patch.object(server,'load_page',return_value=(b'PUBLIC PAGE',{'write_authorized':False,'native_ready':False})),mock.patch.object(server,'make_server',side_effect=AssertionError('socket forbidden')),contextlib.redirect_stdout(out):
            self.assertEqual(server.main(),0)
        report=json.loads(out.getvalue());self.assertFalse(report['server_started']);self.assertNotIn('PRIVATE',out.getvalue())

    def test_invalid_lifetime_refuses_before_page_or_socket(self):
        for seconds in ('0','1801'):
            out=io.StringIO()
            with mock.patch.object(sys,'argv',['serve.py','--page','build/no-file','--seconds',seconds]),mock.patch.object(server,'load_page',side_effect=AssertionError('must not read')),contextlib.redirect_stdout(out):
                self.assertEqual(server.main(),2)
            self.assertEqual(json.loads(out.getvalue())['status'],'REFUSED')

    def test_bounded_loopback_exact_page_head_refusal_and_no_logs(self):
        out=io.StringIO();err=io.StringIO();page=b'PUBLIC SYNTHETIC RECOVERY PAGE'
        with server.make_server(page) as instance,contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            thread=threading.Thread(target=server.serve,args=(instance,1));thread.start()
            for method,route,status,body in ((b'GET',b'/',b'200 OK',page),(b'HEAD',b'/31aj',b'200 OK',b''),(b'GET',b'/candidate.macho',b'404 Not Found',b'REFUSED\n')):
                with socket.create_connection(instance.server_address,timeout=1) as client:
                    client.settimeout(1);client.sendall(method+b' '+route+b' HTTP/1.0\r\n\r\n');chunks=[]
                    while True:
                        chunk=client.recv(8192)
                        if not chunk:break
                        chunks.append(chunk)
                response=b''.join(chunks);header,result=response.split(b'\r\n\r\n',1)
                self.assertIn(status,header);self.assertEqual(result,body);self.assertIn(b'Cache-Control: no-store',header)
            thread.join(1.5);self.assertFalse(thread.is_alive())
        self.assertEqual(out.getvalue(),'');self.assertEqual(err.getvalue(),'')

    def test_stalled_dripping_client_cannot_extend_absolute_lifetime(self):
        with server.make_server(b'PUBLIC PAGE') as instance:
            start=time.monotonic();thread=threading.Thread(target=server.serve,args=(instance,1));thread.start()
            with socket.create_connection(instance.server_address,timeout=1) as client:
                client.settimeout(0.2);client.sendall(b'GET / HTTP/1.1\r\nX: ')
                for _ in range(15):
                    try:client.sendall(b'a')
                    except OSError:break
                    time.sleep(0.08)
                thread.join(0.4)
                self.assertFalse(thread.is_alive());self.assertLess(time.monotonic()-start,1.5)


if __name__=='__main__':unittest.main()

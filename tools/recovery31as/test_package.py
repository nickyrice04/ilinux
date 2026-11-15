#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute unchanged-boundary shell fixtures; no native controller or host query.

The harness maps every fixed tool path to original workspace utilities. It reads
genuine production artifact bytes, but intercepts both native invocations with
a deliberately synthetic controller fixture. This tests bootstrap composition,
not Recovery, Apple's writers, APFS mounts or native Linux.
"""
import contextlib
import ctypes
import html.parser
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('tested31as', Path(__file__).with_name('package.py'))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

UTILITY = r'''#!/usr/bin/python3 -I
import ctypes,hashlib,json,os,pathlib,shutil,sys,tempfile
base=pathlib.Path(__file__).resolve().parent.parent
config=json.loads((base/'configuration.json').read_text())
name=pathlib.Path(sys.argv[0]).name;a=sys.argv[1:]
if name=='id':print(0)
elif name=='stat':
 s=os.stat(a[-1],follow_symlinks=False);f=a[1]
 print(str(s.st_size) if f=='%z' else '0:'+format(s.st_mode&0o7777,'o') if f=='%u:%Lp' else str(s.st_dev)+':'+str(s.st_ino)+':0:'+format(s.st_mode&0o7777,'o'))
elif name=='mktemp':
 p=pathlib.Path(a[-1]);d=tempfile.mkdtemp(prefix=p.name.replace('XXXXXX',''),dir=p.parent);print(d)
elif name=='pwd':print(os.getcwd())
elif name=='cat':sys.stdout.buffer.write(sys.stdin.buffer.read())
elif name=='cp':
 src,dst=map(pathlib.Path,a);api=ctypes.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True)
 api.clonefile.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int]
 if api.clonefile(os.fsencode(src),os.fsencode(dst),0):raise OSError(ctypes.get_errno(),'fixture clone failed')
 if config.get('corrupt_copy')==src.name:
  with dst.open('r+b') as f:f.write(b'!')
elif name=='chmod':os.chmod(a[-1],int(a[0],8))
elif name=='rm':
 for p in a[1:]:pathlib.Path(p).unlink(missing_ok=True)
elif name=='rmdir':os.rmdir(a[-1])
elif name in ('sha256','shasum','openssl'):
 p=pathlib.Path(a[-1]);h=hashlib.sha256(p.read_bytes()).hexdigest()
 mode=config.get('hash_mode','normal')
 if mode=='malformed':h='NOT_A_DIGEST'
 if mode=='extra':h=h+'\nPRIVATE_SENTINEL'
 if name=='shasum':print(h+'  '+str(p))
 elif name=='openssl':print('SHA256('+str(p)+')= '+h)
 else:print(h)
 if mode=='extra_tail':print('PRIVATE_SENTINEL')
 if mode=='nonzero_valid':sys.exit(23)
elif name=='controller-fixture':
 with (base/'controller-calls.jsonl').open('a') as f:f.write(json.dumps(a)+'\n')
 if a[0]=='--transaction':print(json.dumps({'fixture_only':True,'operation':a[1]}))
 elif a[0]=='--validate-transaction-result':
  d=json.loads(pathlib.Path(a[1]).read_text());assert d['fixture_only'] is True;print(json.dumps(d))
 else:sys.exit(98)
else:
 with (base/'forbidden-tool.txt').open('a') as f:f.write(name+'\n')
 sys.exit(99)
'''


def clone(source, destination):
    api = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    api.clonefile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    if api.clonefile(os.fsencode(source), os.fsencode(destination), 0):
        raise OSError(ctypes.get_errno(), 'fixture clone failed')


class Boxes(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.boxes = []
        self.active = None

    def handle_starttag(self, tag, attrs):
        if tag == 'textarea':
            self.active = ''

    def handle_data(self, data):
        if self.active is not None:
            self.active += data

    def handle_endtag(self, tag):
        if tag == 'textarea' and self.active is not None:
            self.boxes.append(self.active)
            self.active = None


class Shell(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, cls.old = tool.frozen()
        cls.original, cls.value = cls.old[4:6]
        cls.kit = ROOT/'build/ilinux-31ar-kit'
        if not cls.kit.is_dir():
            raise unittest.SkipTest('Exact production kit absent; full bootstrap coverage not claimed')
        cls.module.read_kit(cls.kit, ROOT, cls.value)

    def setUp(self):
        base = ROOT/'build/31as-shell-tests';base.mkdir(parents=True, exist_ok=True)
        self.case = Path(tempfile.mkdtemp(prefix='fixture-', dir=base)).resolve()
        self.addCleanup(shutil.rmtree, self.case)
        self.kit = self.case/'kit';self.kit.mkdir(mode=0o700)
        self.work_parent = self.case/'work';self.work_parent.mkdir()
        for file in self.kit_source():
            clone(file, self.kit/file.name)
        self.bin = self.case/'bin';self.bin.mkdir()
        self.dispatch = self.bin/'dispatch';self.dispatch.write_text(UTILITY);self.dispatch.chmod(0o700)
        self.mapping = {name: self.bin/Path(name).name for name in tool.REQUIRED + ('/sbin/sha256','/usr/bin/shasum','/usr/bin/openssl')}
        for path in set(self.mapping.values()) | {self.bin/'controller-fixture'}:
            path.symlink_to(self.dispatch)
        self.config = {}
        self.configuration = self.case/'configuration.json'

    def kit_source(self):
        return (ROOT/'build/ilinux-31ar-kit').iterdir()

    def execute(self, operation='install', branch='sha256'):
        for name in ('sha256', 'shasum', 'openssl'):
            path = self.bin/name
            if name != branch and path.exists():path.unlink()
        self.configuration.write_text(json.dumps(self.config))
        text = tool.render(self.value, operation, self.original)
        # These are the only test-only edits. Both native calls are redirected;
        # genuine helper bytes are still checked before either intercepted call.
        native = '"$H" --transaction '+operation
        observe = '"$H" --validate-transaction-result'
        self.assertEqual(text.count(native),1);self.assertEqual(text.count(observe),1)
        fixture = '"'+str(self.bin/'controller-fixture')+'"'
        text = text.replace(native,fixture+' --transaction '+operation,1).replace(observe,fixture+' --validate-transaction-result',1)
        text = text.replace(self.original.KIT,str(self.kit)).replace('/private/tmp/ilinux31ar.XXXXXX',str(self.work_parent/'ilinux31ar.XXXXXX'))
        pattern = '|'.join(re.escape(name) for name in sorted(self.mapping,key=len,reverse=True))
        text = re.sub(pattern,lambda match:str(self.mapping[match.group(0)]),text)
        self.assertNotIn('/usr/bin/cmp',text);self.assertNotIn('/usr/bin/awk',text)
        result = subprocess.run(['/bin/bash'],input=text,text=True,capture_output=True,
                                cwd=self.case,timeout=40)
        self.assertFalse((self.case/'forbidden-tool.txt').exists())
        log=self.case/'controller-calls.jsonl'
        calls=[json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
        return result,calls

    def test_install_bootstrap_without_cmp_or_awk_with_genuine_artifacts(self):
        run,calls=self.execute()
        self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(len(calls),2)
        self.assertEqual(calls[0][0:2],['--transaction','install'])

    def test_restore_bootstrap_without_candidate_or_cmp_or_awk(self):
        (self.kit/'candidate.macho').unlink()
        run,calls=self.execute('restore')
        self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(len(calls),2)
        self.assertNotIn('candidate.macho',json.dumps(calls))

    def test_shasum_fallback_executes_without_awk(self):
        run,calls=self.execute('restore','shasum')
        self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(len(calls),2)

    def test_openssl_fallback_executes_without_awk(self):
        run,calls=self.execute('restore','openssl')
        self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(len(calls),2)

    def test_changed_staged_profile_refuses_before_controller(self):
        path=self.kit/'profile.json';raw=path.read_bytes();path.write_bytes(raw.replace(b'90000',b'80000'))
        run,calls=self.execute();self.assertNotEqual(run.returncode,0);self.assertEqual(calls,[])

    def test_extra_profile_byte_refuses_before_controller(self):
        path=self.kit/'profile.json';path.write_bytes(path.read_bytes()+b'\n')
        run,calls=self.execute();self.assertNotEqual(run.returncode,0);self.assertEqual(calls,[])

    def test_profile_copy_corruption_refuses_before_controller(self):
        self.config['corrupt_copy']='profile.json'
        run,calls=self.execute();self.assertNotEqual(run.returncode,0);self.assertEqual(calls,[])

    def test_artifact_copy_corruption_refuses_before_controller(self):
        self.config['corrupt_copy']='ilinux31aj-reader'
        run,calls=self.execute();self.assertNotEqual(run.returncode,0);self.assertEqual(calls,[])

    def test_correct_digest_with_nonzero_hash_status_refuses(self):
        self.config['hash_mode']='nonzero_valid'
        for branch in ('sha256','shasum','openssl'):
            with self.subTest(branch=branch):
                for name in ('sha256','shasum','openssl'):
                    p=self.bin/name
                    if not p.exists():p.symlink_to(self.dispatch)
                run,calls=self.execute('restore',branch)
                self.assertNotEqual(run.returncode,0);self.assertEqual(calls,[])

    def test_malformed_and_extra_hash_output_refuse(self):
        for branch in ('sha256','shasum','openssl'):
            for mode in ('malformed','extra','extra_tail'):
                with self.subTest(branch=branch,mode=mode):
                    for name in ('sha256','shasum','openssl'):
                        p=self.bin/name
                        if not p.exists():p.symlink_to(self.dispatch)
                    self.config['hash_mode']=mode
                    run,calls=self.execute('restore',branch)
                    self.assertNotEqual(run.returncode,0);self.assertEqual(calls,[])
                    self.assertNotIn('PRIVATE_SENTINEL',run.stdout)

    def test_no_hash_utility_refuses_before_controller(self):
        run,calls=self.execute('restore','none')
        self.assertNotEqual(run.returncode,0);self.assertEqual(calls,[])

    def test_every_required_utility_is_preflighted_before_controller(self):
        for name in tool.REQUIRED:
            with self.subTest(name=name):
                path=self.mapping[name];path.unlink()
                run,calls=self.execute('restore')
                self.assertNotEqual(run.returncode,0);self.assertEqual(calls,[])
                self.assertIn('ilinux31as-dependency-refusal-v1',run.stderr)
                path.symlink_to(self.dispatch)

    def test_symlink_profile_refuses_before_controller(self):
        p=self.kit/'profile.json';other=self.case/'profile.json';p.rename(other);p.symlink_to(other)
        run,calls=self.execute();self.assertNotEqual(run.returncode,0);self.assertEqual(calls,[])


class Package(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module,cls.old=tool.frozen()

    def test_exact_four_reversible_substitutions_and_unchanged_native_contract(self):
        original,value=self.old[4:6]
        for operation in ('install','restore'):
            text=tool.render(value,operation,original)
            self.assertIn('ilinux31ar.XXXXXX',text);self.assertIn(original.KIT,text)
            self.assertNotIn('/usr/bin/cmp',text);self.assertNotIn('/usr/bin/awk',text)
            self.assertIn('--transaction '+operation,text)
            self.assertEqual(subprocess.run(['/bin/bash','-n'],input=text,text=True,capture_output=True).returncode,0)

    def test_whole_combined_and_independent_boxes(self):
        original,value=self.old[4:6]
        for operation,ops in ((None,('install','restore')),('install',('install',)),('restore',('restore',))):
            parsed=Boxes();parsed.feed(tool.page(value,original,operation))
            self.assertEqual(parsed.boxes,[tool.render(value,item,original) for item in ops])

    def test_default_help_and_argument_errors_are_inert(self):
        for args,code in (([],0),(['--stage'],2),(['--prepare'],2),(['--page','x','--seconds','1801'],2)):
            with patch.object(tool,'prepare') as p,patch.object(tool,'service') as s,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(tool.main(args),code);p.assert_not_called();s.assert_not_called()

    def test_route_accepts_only_new_fixed_route_and_root(self):
        old=self.module.old_module('serve',self.old[3],ROOT)
        for path,expected in (('/',200),('/31as',200),('/31ar',404),('/31aj',404),('/31as/other',404)):
            raw=('GET '+path+' HTTP/1.1\r\nHost: test\r\n\r\n').encode()
            wrapped=lambda r:self.module.route_request(r,old.request)
            self.assertEqual(tool.route(raw,wrapped)[0],expected,path)

    def test_admission_exact_source_closure_and_frozen_sources(self):
        module,old,inventory,pins=tool.admitted()
        self.assertEqual(len(pins),167);self.assertEqual(old[2],self.old[2])

    def test_actual_prepare_and_checks_are_inert_and_no_overwrite(self):
        base=ROOT/'build/31as-package-tests';base.mkdir(parents=True,exist_ok=True)
        case=Path(tempfile.mkdtemp(prefix='fixture-',dir=base));self.addCleanup(shutil.rmtree,case)
        output=case/'page';result=tool.prepare(output)
        self.assertFalse(result['controller_run']);self.assertFalse(result['server_started'])
        for n in ('recovery.html','install.html','restore.html'):
            _,check=tool.check_page(output/n);self.assertEqual(check['status'],'EXACT_PAGE_VERIFIED')
        with self.assertRaises(ValueError):tool.prepare(output)
        (output/'recovery.html').write_text('corrupt')
        with self.assertRaises(ValueError):tool.check_page(output/'recovery.html')


if __name__ == '__main__':
    unittest.main(verbosity=2)

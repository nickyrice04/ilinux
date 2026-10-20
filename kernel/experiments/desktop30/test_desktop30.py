#!/usr/bin/env python3
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import unittest
from unittest.mock import MagicMock, patch
import subprocess

HERE = Path(__file__).resolve().parent
def load(name):
    spec=importlib.util.spec_from_file_location(name,HERE/(name+'.py'))
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
receiver=load('receive');collector=load('collect')

def bundle(extra=None, omit=None, bad_hash=False):
    files={'frameprobe':b'executable','samplecpu':b'module','collect.py':b'source'}
    a={'attempt':30,'sha256':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()}}
    if bad_hash:a['sha256']['frameprobe']='0'*64
    files['assets.json']=json.dumps(a).encode()
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w',format=tarfile.USTAR_FORMAT) as t:
        for n,b in files.items():
            if n==omit:continue
            info=tarfile.TarInfo(n);info.size=len(b);t.addfile(info,io.BytesIO(b))
        if extra:t.addfile(extra,io.BytesIO(b'x'*extra.size))
    return out.getvalue()

def validate(data):return receiver.validate(data,len(data),hashlib.sha256(data).hexdigest())

class BundleTests(unittest.TestCase):
    def test_exact(self):self.assertEqual(set(validate(bundle())),receiver.NAMES)
    def test_hash(self):
        with self.assertRaises(ValueError):receiver.validate(bundle(),len(bundle()),'0'*64)
    def test_size(self):
        with self.assertRaises(ValueError):receiver.validate(bundle(),1,'0'*64)
    def test_truncated(self):
        with self.assertRaises(ValueError):receiver.validate(bundle()[:-1],len(bundle()),hashlib.sha256(bundle()).hexdigest())
    def test_missing(self):
        with self.assertRaises(ValueError):validate(bundle(omit='frameprobe'))
    def test_asset_hash(self):
        with self.assertRaises(ValueError):validate(bundle(bad_hash=True))
    def test_unsafe_members(self):
        for name,kind in [('frameprobe',tarfile.REGTYPE),('../escape',tarfile.REGTYPE),
                          ('frameprobe',tarfile.SYMTYPE),('frameprobe',tarfile.LNKTYPE),
                          ('device',tarfile.CHRTYPE),('/absolute',tarfile.REGTYPE)]:
            with self.subTest(name=name,kind=kind):
                info=tarfile.TarInfo(name);info.type=kind
                with self.assertRaises(ValueError):validate(bundle(extra=info))
    def test_oversized(self):
        with self.assertRaises(ValueError):receiver.validate(b'x',receiver.LIMIT+1,'0'*64)

def frames():
    return [dict(event='frame',index=i,warmup=i<4,damage='cell' if i<12 else 'full',
                 callback_ms=17,width=3456,height=2160) for i in range(20)]+[dict(event='done',frames=20)]

class FrameTests(unittest.TestCase):
    def test_complete(self): self.assertEqual(collector.validate_frames(frames()),frames())
    def test_truncated_or_reordered(self):
        for rows in (frames()[:-1],frames()[1:],list(reversed(frames()))):
            with self.assertRaises(ValueError):collector.validate_frames(rows)
    def test_invalid_samples(self):
        for key,value in [('callback_ms',float('nan')),('callback_ms',-1),('width',4000),
                          ('warmup',False),('damage','unknown')]:
            rows=frames();rows[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):collector.validate_frames(rows)
    def test_resized(self):
        rows=frames();rows[8]['width']=3400
        with self.assertRaises(ValueError):collector.validate_frames(rows)

class CleanupTests(unittest.TestCase):
    def test_timed_out_workload_stops_both_children(self):
        sampler=MagicMock(pid=301);sampler.poll.return_value=None
        sampler.communicate.return_value=('{"status":"sampled","lost":0}', '')
        worker=MagicMock(pid=302);worker.poll.return_value=None
        worker.communicate.side_effect=subprocess.TimeoutExpired('frameprobe',40)
        with patch.object(collector,'cpu_times',return_value=(0,123)), \
             patch.object(collector,'request',return_value={'int':1000}), \
             patch.object(collector.subprocess,'Popen',side_effect=[sampler,worker]), \
             patch.object(collector.os,'killpg') as kill,patch.object(collector,'emit') as emit:
            with self.assertRaises(subprocess.TimeoutExpired):
                collector.phase('test',300,Path('/unused'),{},Path('/unused'))
            self.assertEqual({c.args[0] for c in kill.call_args_list},{301,302})
            self.assertEqual(emit.call_args.args[0],'phase_incomplete')
            self.assertEqual(emit.call_args.kwargs['reason'],'TimeoutExpired')
            self.assertEqual(emit.call_args.kwargs['cpu_samples']['status'],'sampled')
    def test_wrong_native_identity_stops_before_desktop_or_marker(self):
        observe=MagicMock();observe.identity.return_value={'mpidr':'0x1','kernel':'wrong'}
        with patch.dict(collector.sys.modules,{'observe28':observe,'measurement':MagicMock()}), \
             patch.object(collector.os,'geteuid',return_value=0), \
             patch.object(collector.signal,'signal'),patch.object(collector.signal,'alarm'), \
             patch.object(collector,'find_desktop') as desktop,patch.object(collector,'emit'):
            self.assertEqual(collector.main(),3)
            desktop.assert_not_called();observe.verify_assets.assert_not_called()

if __name__=='__main__':unittest.main()

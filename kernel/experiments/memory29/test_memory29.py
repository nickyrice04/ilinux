#!/usr/bin/env python3
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import unittest

HERE = Path(__file__).resolve().parent
def load(name):
    spec=importlib.util.spec_from_file_location(name,HERE/(name+'.py'))
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
receiver=load('receive');collector=load('collect')

def bundle(extra=None, omit=None, bad_hash=False):
    files={'memory29':b'executable','ilinux_mem29.ko':b'module','collect.py':b'source'}
    a={'attempt':29,'sha256':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()}}
    if bad_hash:a['sha256']['memory29']='0'*64
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
        with self.assertRaises(ValueError):validate(bundle(omit='memory29'))
    def test_asset_hash(self):
        with self.assertRaises(ValueError):validate(bundle(bad_hash=True))
    def test_unsafe_members(self):
        for name,kind in [('memory29',tarfile.REGTYPE),('../escape',tarfile.REGTYPE),
                          ('memory29',tarfile.SYMTYPE),('memory29',tarfile.LNKTYPE),
                          ('device',tarfile.CHRTYPE),('/absolute',tarfile.REGTYPE)]:
            with self.subTest(name=name,kind=kind):
                info=tarfile.TarInfo(name);info.type=kind
                with self.assertRaises(ValueError):validate(bundle(extra=info))
    def test_oversized(self):
        with self.assertRaises(ValueError):receiver.validate(b'x',receiver.LIMIT+1,'0'*64)

class DecodeTests(unittest.TestCase):
    def row(self,mair=0xff<<32,sctlr=0x1005):
        return ('ilinux_mem29 sctlr=%016x tcr=00000000b510b510 mair=%016x '
                'ctr=000000008444c004 clidr=0000000002000023 page_shift=14 level=2 attrs=0711 normal_index=4')%(sctlr,mair)
    def test_normal(self):
        x=collector.decode(self.row());self.assertEqual(x['sample_page_attribute'],255)
        self.assertEqual(x['normal_attribute'],255);self.assertTrue(x['dcache'])
        self.assertEqual(x['sh0'],3);self.assertEqual(x['tg0'],2)
        self.assertEqual(x['sample_page_shareability'],3)
    def test_uncached_not_assumed(self):
        x=collector.decode(self.row(mair=0x44<<32,sctlr=1))
        self.assertEqual(x['normal_attribute'],0x44);self.assertFalse(x['dcache'])
    def test_bad_input(self):
        with self.assertRaises(ValueError):collector.decode('unrelated log')
    def test_no_addresses(self):
        self.assertNotIn('address',collector.decode(self.row()))

if __name__=='__main__':unittest.main()

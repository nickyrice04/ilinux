# SPDX-License-Identifier: MIT
import hashlib,importlib.util,io,json,tarfile,tempfile,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('delivery31af',Path(__file__).with_name('verify.py'));v=importlib.util.module_from_spec(s);s.loader.exec_module(v)
class DeliveryTests(unittest.TestCase):
 def fixture(self,root,mutation=''):
  b=b'original synthetic fixture';name='ilinux-31af-immutable.macho';h=hashlib.sha256(b).hexdigest();sums=(h+'  '+name+'\n').encode();a=root/'data.tar.gz'
  with tarfile.open(a,'w:gz') as t:
   for n,data in [(name,b),('SHA256SUMS',sums)]:
    if mutation=='missing' and n=='SHA256SUMS':continue
    x=tarfile.TarInfo('ilinux-31af/'+n);x.size=len(data)
    if mutation=='link' and n==name:x.type=tarfile.SYMTYPE;x.linkname='/outside';x.size=0
    t.addfile(x,io.BytesIO(data))
    if mutation=='duplicate' and n==name:t.addfile(x,io.BytesIO(data))
   if mutation=='extra':
    x=tarfile.TarInfo('../outside');x.size=1;t.addfile(x,io.BytesIO(b'x'))
  m={'archive':{'bytes':a.stat().st_size,'sha256':hashlib.sha256(a.read_bytes()).hexdigest()},'files':{name:{'bytes':len(b),'sha256':h}}}
  if mutation=='memberhash':m['files'][name]['sha256']='0'*64
  if mutation=='unsafe':m['files']['../outside']=m['files'].pop(name)
  p=root/'manifest.json';p.write_text(json.dumps(m));return p,a
 def test_valid(self):
  with tempfile.TemporaryDirectory() as d:
   p,a=self.fixture(Path(d));self.assertEqual(v.verify(p,a)['status'],'PASS')
 def test_archive_hash(self):
  with tempfile.TemporaryDirectory() as d:
   p,a=self.fixture(Path(d));a.write_bytes(a.read_bytes()+b'x')
   with self.assertRaises(ValueError):v.verify(p,a)
 def test_namespace_and_contents(self):
  for mutation in ('missing','link','duplicate','extra','memberhash','unsafe'):
   with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as d:
    p,a=self.fixture(Path(d),mutation)
    with self.assertRaises(ValueError):v.verify(p,a)
if __name__=='__main__':unittest.main()

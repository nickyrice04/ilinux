"""Deterministic original-code-only bundle; no images, keys or Apple artifacts."""
import hashlib,json,tarfile
from pathlib import Path
o=Path('/mnt/job/out')
names=('frameprobe','samplecpu','collect.py')
a={'attempt':30,'modules_loaded':False,'frequency_writes':False,'renderer_changes':False,
   'sha256':{n:hashlib.sha256((o/n).read_bytes()).hexdigest() for n in names}}
(o/'assets.json').write_text(json.dumps(a,indent=2)+'\n')
with tarfile.open(o/'desktop30.tar','w',format=tarfile.USTAR_FORMAT) as t:
 for n in sorted([*names,'assets.json']):
  info=t.gettarinfo(str(o/n),arcname=n);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
  with (o/n).open('rb') as f:t.addfile(info,f)
b=(o/'desktop30.tar').read_bytes()
(o/'bundle.json').write_text(json.dumps({'attempt':30,'size_bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()},indent=2)+'\n')
print('PASS exact four-member userspace bundle; native NOT RUN')

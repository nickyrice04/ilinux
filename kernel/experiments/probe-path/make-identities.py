#!/usr/bin/env python3
"""Generate public node IDs from the exact packaged diagnostic DT, never host ADT."""
import hashlib, importlib.util, json
from pathlib import Path
import sys
here=Path(__file__).resolve().parent
repo=here.parents[2]
p=Path(sys.argv[1])
blob=p.read_bytes()
assert hashlib.sha256(blob).hexdigest()=='7adc1364687df9c358692489f2a574241e869cf03b67538eaaaaf0233b4365a7'
s=importlib.util.spec_from_file_location('fdt',repo/'native/boot/fdt.py')
f=importlib.util.module_from_spec(s);s.loader.exec_module(f)
nodes=f.properties(blob)
rows=[{'id':i,'hex':f'{i:04X}','path':path,'compatible':f.strings(n['compatible'])}
      for i,(path,n) in enumerate(sorted((p,n) for p,n in nodes.items() if 'compatible' in n),1)]
assert len(rows)<65536
(here/'device-identities.json').write_text(json.dumps({'dt_sha256':hashlib.sha256(blob).hexdigest(),'unknown_id':'0000','nodes':rows},indent=2)+'\n')
(here/'device-identities.h').write_text('/* Generated from the pinned public diagnostic DT; IDs are not hardware identifiers. */\n'+''.join('    { '+json.dumps(r['path'])+', NULL }, /* '+r['hex']+' */\n' for r in rows))
print('PASS:',len(rows),'stable public DT node IDs')

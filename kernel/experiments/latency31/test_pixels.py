#!/usr/bin/env python3
"""Independent small-image integer oracle for the portable pixel baseline."""
import json
from pathlib import Path
import subprocess
import sys

binary=Path(sys.argv[1]).resolve()
rows=[json.loads(s) for s in subprocess.check_output([str(binary),'64','32'],text=True).splitlines()]
assert len(rows)==18
expected={'copy':0,'alpha_over':0}
for i in range(64*32):
    b=0xff000000|(i&0xffffff)
    o=0x40000000|((i%65)<<16)|((i%33)<<8)|(i%17)
    out=0xff000000
    for shift in [0,8,16]:
        out|=(((o>>shift)&255)+(((b>>shift)&255)*191+127)//255)<<shift
    expected['copy']+=b*(i%251+1)
    expected['alpha_over']+=out*(i%251+1)
for row in rows:
    assert row['checksum']==expected[row['test']]
    # Tiny oracle runs can be below the host timer's resolution.
    assert row['wall_ns']>=0 and row['cpu_ns']>=0
    assert row['major_faults']==0
assert sum(r['wall_ns'] for r in rows)>0
for args in [('0','1'),('4000','2160'),('64','x'),('1',)]:
    assert subprocess.run([str(binary),*args],capture_output=True).returncode==2
print('18 pixel samples match independent oracle; 4 invalid inputs refused')

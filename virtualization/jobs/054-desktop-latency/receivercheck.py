"""VM-only end-to-end delivery/refusal checks; never included in the bundle."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

out = Path('/run/d30/results')
pin = json.loads((out/'bundle.json').read_text())
data = (out/'desktop30.tar').read_bytes()
assert len(data) == pin['size_bytes']
assert hashlib.sha256(data).hexdigest() == pin['sha256']
command = ['python3', '-I', '/run/d30/receive.py', str(len(data)), pin['sha256']]
p = subprocess.run(command, input=data, capture_output=True, timeout=10)
assert p.returncode == 3 and not p.stderr, (p.returncode, p.stderr)
rows = [json.loads(s) for s in p.stdout.splitlines()]
assert rows[-1]['event'] == 'stop' and 'devicetree' in rows[-1]['reason']
assert not Path('/run/ilinux-desktop30.started').exists()
dest = Path('/run/ilinux-desktop30')
assert dest.stat().st_uid == 0 and dest.stat().st_mode & 0o777 == 0o755
assets = json.loads((dest/'assets.json').read_text())
assert set(p.name for p in dest.iterdir()) == {'frameprobe', 'samplecpu', 'collect.py', 'assets.json'}
for name, digest in assets['sha256'].items():
    item = dest/name
    assert item.stat().st_uid == 0
    assert hashlib.sha256(item.read_bytes()).hexdigest() == digest
    assert item.stat().st_mode & 0o777 == (0o755 if name != 'collect.py' else 0o600)
access = 'import os; assert os.access("/run/ilinux-desktop30/frameprobe", os.X_OK); assert not os.access("/run/ilinux-desktop30/collect.py", os.R_OK)'
subprocess.run(['python3', '-I', '-c', access], user=1000, group=1000,
               extra_groups=[], check=True, timeout=5)
again = subprocess.run(command, input=data, capture_output=True, timeout=10)
assert again.returncode != 0 and b'FileExistsError' in again.stderr
assert not Path('/run/ilinux-desktop30.started').exists()
print('PASS exact bundle receiver, RAM-only permissions, native VM refusal, retry refusal')

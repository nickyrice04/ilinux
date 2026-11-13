#!/bin/bash
# SPDX-License-Identifier: MIT
# Existing isolated ARM64 Linux VM only; no kernel/USB/native boot operation.
set -euo pipefail
I=/mnt/ilinux
O=/mnt/job/out
P=$I/build/direct31ah-kernel/job/out
S=$I/kernel/experiments/direct31ah/linux/diag_init.c
mkdir -p "$O"
exec > "$O/relink.log" 2>&1
gcc -static -O2 -std=c11 -Wall -Wextra -Werror -pthread -c "$S" -o "$O/diag-init.o"
gcc -static -O2 -std=c11 -Wall -Wextra -Werror -pthread "$O/diag-init.o" -o "$O/diag-init-relinked"
cmp "$O/diag-init-relinked" "$P/diag-init"
"$O/diag-init-relinked" --selftest > "$O/selftest.jsonl"
"$O/diag-init-relinked" --selftest-timeout > "$O/timeout-selftest.jsonl"
python3 -I - "$I" "$O" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
root,out=map(Path,sys.argv[1:]);previous=root/'build/direct31ah-kernel/job/out'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=root/'kernel/experiments/direct31ah/linux/diag_init.c'
assert sha(source)=='53b75d25c01b03a1c92832df91c51b875f03616847cbc674cce1c539cc729761'
assert sha(out/'diag-init-relinked')==sha(previous/'diag-init')=='c84152b6413e5dd60fdedd9f317035f61b57686c241ca10fd2bb1219a15c2c66'
normal=[json.loads(x) for x in (out/'selftest.jsonl').read_text().splitlines()]
stall=[json.loads(x) for x in (out/'timeout-selftest.jsonl').read_text().splitlines()]
assert normal[-1].get('scope')=='GENERIC_LINUX_CONTROL' and normal[-1].get('selftest')=='PASS'
assert stall[-1].get('scope')=='GENERIC_LINUX_TIMEOUT_CONTROL' and stall[-1].get('selftest')=='PASS' and stall[-1].get('expected_timeout_observed') is True
packages={}
for name in ('glibc','gcc-libs'):
 packages[name]=subprocess.check_output(['pacman','-Q',name],text=True).strip()
provenance={
 'common/LGPL-2.1-or-later.txt':{'kind':'COMMON_SPDX_LICENSE_TEXT','source':'/usr/share/licenses/spdx/LGPL-2.1-or-later.txt'},
 'common/GPL-3.0-or-later.txt':{'kind':'COMMON_SPDX_LICENSE_TEXT','source':'/usr/share/licenses/spdx/GPL-3.0-or-later.txt'},
 'common/GPL-2.0-only.txt':{'kind':'COMMON_SPDX_LICENSE_TEXT','source':'/usr/share/licenses/spdx/GPL-2.0-only.txt'},
 'gcc/RUNTIME.LIBRARY.EXCEPTION':{'kind':'INSTALLED_GCC_PACKAGE_EXCEPTION','source':'/usr/share/licenses/gcc/RUNTIME.LIBRARY.EXCEPTION'}}
notices={}
for name,origin in provenance.items():
 path=Path(origin['source'])
 if not path.is_file() or not path.resolve().is_relative_to(Path('/usr/share/licenses')) or not 0<path.stat().st_size<=256*1024:raise ValueError('required common notice unavailable')
 data=path.read_bytes();data.decode('utf-8')
 dest=out/'licenses'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 notices[name]={'bytes':len(data),'sha256':sha(dest)}
receipt={'schema':'ilinux-direct31ai-relink-v1','status':'PASS','scope':'GENERIC_LINUX_RELINK_ONLY',
 'collector_source_sha256':sha(source),'object_sha256':sha(out/'diag-init.o'),
 'tested_executable_sha256':sha(previous/'diag-init'),'relinked_executable_sha256':sha(out/'diag-init-relinked'),
 'byte_equal_to_tested_executable':True,'normal_selftest':'PASS','intentional_timeout_selftest':'PASS',
 'runtime_packages':packages,'license_files':notices,'notice_provenance':provenance,
 'runtime_specific_copyright_notices_complete':False,'public_libc_source_closure':'INCOMPLETE',
 'public_binary_release':False,'native_tested':False}
(out/'relink-result.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('DIRECT31AI_RELINK_PASS_NO_NATIVE_ACTION')
PY

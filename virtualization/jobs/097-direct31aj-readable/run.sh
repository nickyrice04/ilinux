#!/bin/bash
# SPDX-License-Identifier: MIT
# Existing isolated ARM64 Linux VM only; parent owns VM lifecycle/locks.
set -euo pipefail
I=/mnt/ilinux
O=/mnt/job/out
S=$I/kernel/experiments/direct31aj
K=$I/build/direct31ah-kernel/job/out
mkdir -p "$O"
exec > "$O/build.log" 2>&1
python3 -I - "$S" "$O/source-binding.json" <<'PY'
import hashlib,json,sys
from pathlib import Path
source,out=map(Path,sys.argv[1:])
names=('diag_init.c','readable.h','test_readable.c')
out.write_text(json.dumps({'schema':'ilinux31aj-readable-source-v1','files':{n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in names}},indent=2)+'\n')
PY
gcc -std=c11 -O2 -Wall -Wextra -Werror "$S/test_readable.c" -o "$O/test-readable"
"$O/test-readable" > "$O/panel-tests.json"
gcc -static -O2 -std=c11 -Wall -Wextra -Werror -pthread -c "$S/diag_init.c" -o "$O/diag-init.o"
gcc -static -O2 -std=c11 -Wall -Wextra -Werror -pthread "$O/diag-init.o" -o "$O/diag-init"
gcc -static -O2 -std=c11 -Wall -Wextra -Werror -pthread "$S/diag_init.c" -o "$O/diag-init-direct"
cmp "$O/diag-init" "$O/diag-init-direct"
"$O/diag-init" --selftest > "$O/collector-selftest.json"
"$O/diag-init" --selftest-timeout > "$O/collector-timeout-selftest.json"
"$O/diag-init" --display-test > "$O/display-test.txt"
python3 -I "$I/kernel/experiments/direct31ah/linux/make_initramfs.py" \
 "$O/diag-init" "$O/initramfs-direct31aj.cpio.gz" > "$O/initramfs-build.json"
python3 -I - "$I" "$S" "$K" "$O" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
repo,source,kernel,out=map(Path,sys.argv[1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
binding=json.loads((out/'source-binding.json').read_text())
assert all(sha(source/n)==v for n,v in binding['files'].items()),'readable sources changed during build'
pins={'Image':'c01483f230aa64013b395291f8a5b8e38ed6c467b61e8a141c621938fda3a56f',
 'kernel.config':'bba7ce251238c3cb6779d884a3442373443f7eed97e19f638afc08fdb9779fd8',
 't6050-j716c-diagnostic.dtb':'2c93df25dcbbc6939360ca84b76e21246ca30b6b7e2d0189afb0b1978332cb51'}
for name,digest in pins.items():assert sha(kernel/name)==digest
normal=[json.loads(x) for x in (out/'collector-selftest.json').read_text().splitlines()]
stall=[json.loads(x) for x in (out/'collector-timeout-selftest.json').read_text().splitlines()]
assert normal[-1]['scope']=='GENERIC_LINUX_CONTROL' and normal[-1]['selftest']=='PASS'
assert stall[-1]['scope']=='GENERIC_LINUX_TIMEOUT_CONTROL' and stall[-1]['selftest']=='PASS' and stall[-1]['expected_timeout_observed'] is True
assert json.loads((out/'panel-tests.json').read_text())['status']=='PASS'
demo=(out/'display-test.txt').read_text();assert 'SYNTHETIC_PANEL_DEMO' in demo and 'UNAVAILABLE' not in demo
provenance={
 'common/LGPL-2.1-or-later.txt':{'kind':'COMMON_SPDX_LICENSE_TEXT','source':'/usr/share/licenses/spdx/LGPL-2.1-or-later.txt'},
 'common/GPL-3.0-or-later.txt':{'kind':'COMMON_SPDX_LICENSE_TEXT','source':'/usr/share/licenses/spdx/GPL-3.0-or-later.txt'},
 'common/GPL-2.0-only.txt':{'kind':'COMMON_SPDX_LICENSE_TEXT','source':'/usr/share/licenses/spdx/GPL-2.0-only.txt'},
 'gcc/RUNTIME.LIBRARY.EXCEPTION':{'kind':'INSTALLED_GCC_PACKAGE_EXCEPTION','source':'/usr/share/licenses/gcc/RUNTIME.LIBRARY.EXCEPTION'}}
notices={}
for name,origin in provenance.items():
 path=Path(origin['source']);assert path.is_file() and 0<path.stat().st_size<=256*1024
 data=path.read_bytes();data.decode('utf-8');dest=out/'licenses'/name
 dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 notices[name]={'bytes':len(data),'sha256':sha(dest)}
files={n:{'bytes':(out/n).stat().st_size,'sha256':sha(out/n)} for n in
 ('diag-init','diag-init.o','initramfs-direct31aj.cpio.gz','display-test.txt','panel-tests.json','source-binding.json')}
result={'schema':'ilinux31aj-readable-build-v1','status':'PASS','scope':'ISOLATED_GENERIC_LINUX_BUILD_AND_SELFTEST',
 'source_binding':binding,'files':files,'unchanged_kernel_inputs':pins,'kernel_rebuilt':False,
 'relink_equal_to_direct_build':True,'normal_selftest':'PASS','intentional_timeout_selftest':'PASS',
 'panel_columns':78,'panel_rows':35,'panel_period_existing_loop_ticks':5,'new_sleeps':0,
 'font_framebuffer_backlight_access':False,'native_readability_qualified':False,
 'runtime_packages':{p:subprocess.check_output(['pacman','-Q',p],text=True).strip() for p in ('glibc','gcc-libs')},
 'license_files':notices,'notice_provenance':provenance,'runtime_specific_copyright_notices_complete':False,
 'public_libc_source_closure':'INCOMPLETE','public_binary_release':False,'native_tested':False,'restart_ready':False}
(out/'build-result.json').write_text(json.dumps(result,indent=2)+'\n')
print('DIRECT31AJ_READABLE_BUILD_PASS_OFFLINE_ONLY')
PY

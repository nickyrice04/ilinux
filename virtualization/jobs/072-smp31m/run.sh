#!/bin/bash
# Offline original models and pinned client serialization; no physical target.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out
mkdir -p "$I" "$O" /mnt/m1n1-source
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
mountpoint -q /mnt/m1n1-source || mount -t virtiofs m1n1-source /mnt/m1n1-source
exec > "$O/run.log" 2>&1
test "$(git -c safe.directory=/mnt/m1n1-source -C /mnt/m1n1-source rev-parse HEAD)" = 57a9339ffd1876e78297b17d34dece8cff8fa1ba
test -z "$(git -c safe.directory=/mnt/m1n1-source -C /mnt/m1n1-source status --porcelain --untracked-files=all)"
IMAGE="$I/virtualization/jobs/069-smp31k/out/boot021.bin"
SYMBOLS="$I/virtualization/jobs/069-smp31k/out/m1n1-symbols.txt"
as -o "$O/ctr.o" "$I/kernel/experiments/smp31m-observer/ctr.S"
objcopy -O binary -j .text "$O/ctr.o" "$O/ctr.bin"
python3 -I - "$I" "$O" "$IMAGE" <<'CHECK'
import importlib.util,json,pathlib,sys
root,out,image=map(pathlib.Path,sys.argv[1:])
def module(name,file):
 spec=importlib.util.spec_from_file_location(name,root/file)
 m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m)
 return m
m=module('m','kernel/experiments/smp31m-observer/observer.py')
a=module('a','kernel/experiments/smp31m-observer/audit.py')
assert (out/'ctr.bin').read_bytes()==m.CTR_LEAF
(out/'assembly.json').write_text(json.dumps(dict(result='PASS',assembler='GNU as',original_leaf_bytes=8,comparison_count=1)))
(out/'cache-path.json').write_text(json.dumps(a.verify_image(image.read_bytes()),indent=2))
CHECK
python3 -I "$I/kernel/experiments/smp31m-observer/test_observer.py"
python3 -I "$I/kernel/experiments/smp31m-observer/test_audit.py" --image "$IMAGE"
python3 -I "$I/native/boot/test_smp31m.py"
python3 -I "$I/tools/m1n1-client/test_attempt31m_offline.py"
python3 -I "$I/tools/m1n1-client/test_attempt31m_supervisor.py"
python3 -I "$I/kernel/experiments/smp31/test_client31m_vm.py" /mnt/m1n1-source/proxyclient > "$O/wire.log"
if [ -f "$I/native/boot/attempt31m/source-sha256.txt" ]; then
 python3 -I "$I/tools/m1n1-client/attempt31m-offline.py" --image "$IMAGE" --symbols "$SYMBOLS" > "$O/intake-full.json"
 python3 -I "$I/tools/m1n1-client/attempt31m-offline.py" --image "$IMAGE" > "$O/intake-image.json"
fi
python3 --version > "$O/toolchain.txt"
uname -srm >> "$O/toolchain.txt"
as --version | head -1 >> "$O/toolchain.txt"
echo SMP31M-OFFLINE-PASS

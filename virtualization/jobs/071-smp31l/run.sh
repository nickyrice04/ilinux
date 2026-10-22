#!/bin/bash
# Original offline source/image/serializer validation. No physical target.
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
as -o "$O/prefix.o" "$I/kernel/experiments/smp31l-candidate/prefix.S"
python3 -I - "$I" "$O" <<'CHECK'
import importlib.util,json,pathlib,subprocess,sys
root,out=map(pathlib.Path,sys.argv[1:])
spec=importlib.util.spec_from_file_location('b',root/'kernel/experiments/smp31l-candidate/builder.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
addresses=(0x800000000,0x8ffffc000,0x10000000000,0x100ffffc000,0x1ffffff8000)
for helper in addresses:
    subprocess.run(['ld','-Ttext=0','-e','normal_vector_prefix','--defsym','normal_helper='+hex(helper),
                    '--defsym','existing_vector_recorder=0xa00','--defsym','existing_cold_recorder=0xb00',
                    '-o',str(out/'prefix.elf'),str(out/'prefix.o')],check=True)
    subprocess.run(['objcopy','-O','binary','-j','.text',str(out/'prefix.elf'),str(out/'prefix.bin')],check=True)
    data=(out/'prefix.bin').read_bytes()
    for name,offset in b.CODE.items():
        assert data[offset:offset+60]==b.program(name,helper)[0]
(out/'assembly.json').write_text(json.dumps(dict(result='PASS',assembler='GNU as',addresses=len(addresses),prefix_comparisons=2*len(addresses))))
CHECK
python3 -I "$I/kernel/experiments/smp31l-candidate/test_candidate.py" --image "$IMAGE" --symbols "$SYMBOLS"
python3 -I "$I/kernel/experiments/smp31l-observer/test_observer.py"
python3 -I "$I/native/boot/test_smp31l.py"
python3 -I "$I/tools/m1n1-client/test_attempt31l_offline.py"
python3 -I "$I/tools/m1n1-client/test_attempt31l_supervisor.py"
python3 -I "$I/kernel/experiments/smp31/test_client31l_vm.py" /mnt/m1n1-source/proxyclient > "$O/wire.log"
if [ -f "$I/native/boot/attempt31l/source-sha256.txt" ]; then
    python3 -I "$I/tools/m1n1-client/attempt31l-offline.py" --image "$IMAGE" --symbols "$SYMBOLS" > "$O/intake-full.json"
    python3 -I "$I/tools/m1n1-client/attempt31l-offline.py" --image "$IMAGE" > "$O/intake-image.json"
fi
python3 --version > "$O/toolchain.txt"
uname -srm >> "$O/toolchain.txt"
as --version | head -1 >> "$O/toolchain.txt"
echo SMP31L-OFFLINE-PASS

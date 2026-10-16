#!/bin/bash
# job 043: offline compile/validation check of the updated t6050 patch series (0005 NVMMU status
# array + lo/hi stores, 0007 SMC + mailbox DT nodes).  Nothing boots, nothing touches the M5, no
# network: a clean git worktree of the pinned base commit is taken from the tree job 020 fetched
# (/var/tmp/t6050-build/linux, tag "base"); if that tree is missing the job stops instead of fetching.
#  1. private copy of the base tree, reset to the pinned base commit (77cb8f24), series applied;
#  2. defconfig + the apple options, drivers/nvme/host/apple.o and drivers/soc/apple/sart.o with W=1;
#  3. the t6050 DTB (and CHECK_DTBS/dt-validate when dtschema is installed: informational);
#  4. checkpatch --strict on the three regenerated patches (informational);
#  5. probe-audit of the regenerated DT against the tree's drivers.
set -u
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
OUT=/mnt/job/out
IN=/mnt/job/in
BASE=/var/tmp/t6050-build/linux
WORK=/var/tmp/ilinux-nvme-smc/linux
BASE_COMMIT=77cb8f24c2381a8abb7272d7bbdec548d6426a8a
JOBS=$(nproc)
log() { printf '[%s] %s\n' "$(date +%T)" "$*"; }
rm -rf "$OUT"/*; mkdir -p "$OUT"
exec > "$OUT/script.log" 2>&1
export KBUILD_BUILD_TIMESTAMP='@0' KBUILD_BUILD_USER=ilinux KBUILD_BUILD_HOST=job043

log "1. inputs"
{ uname -srm; gcc --version | head -1; dtc --version; python3 --version; dt-validate --version 2>/dev/null || echo "dt-validate: not installed"; } | tee "$OUT/toolchain.txt"
ls -la "$IN/patches" | tee "$OUT/inputs.txt"
if [ ! -d "$BASE/.git" ]; then echo "NO BASE TREE at $BASE (job 020 never ran here): stopping, no fetch" | tee "$OUT/RESULT.txt"; exit 2; fi
mkdir -p "$(dirname "$WORK")"
cd "$BASE"
git worktree remove --force "$WORK" 2>/dev/null; rm -rf "$WORK"; git worktree prune
log "clean worktree of the pinned base -> $WORK (no build artifacts, no network)"
git worktree add --detach "$WORK" "$BASE_COMMIT" 2>/dev/null || git worktree add --detach "$WORK" base || { echo "cannot create a worktree at the base commit" | tee "$OUT/RESULT.txt"; exit 2; }
cd "$WORK"
git log -1 --format='base %H %s' | tee "$OUT/base.txt"
git -c user.name=ilinux -c user.email=ilinux@localhost am "$IN"/patches/000*.patch > "$OUT/am.log" 2>&1
echo "git am exit=$?" | tee -a "$OUT/am.log"
git log --oneline -8 | tee "$OUT/series.txt"

log "2. config + driver objects (W=1)"
make -j"$JOBS" ARCH=arm64 defconfig > "$OUT/config.log" 2>&1
for s in ARCH_APPLE APPLE_SART NVME_APPLE APPLE_RTKIT APPLE_MAILBOX APPLE_DART APPLE_PMGR_PWRSTATE MFD_MACSMC GPIO_MACSMC SENSORS_MACSMC; do ./scripts/config --enable "$s" 2>/dev/null; done
make -j"$JOBS" ARCH=arm64 olddefconfig >> "$OUT/config.log" 2>&1
grep -E 'CONFIG_(APPLE_SART|NVME_APPLE|ARCH_APPLE|MFD_MACSMC|APPLE_MAILBOX)=' .config | tee "$OUT/config.txt"
make -j"$JOBS" ARCH=arm64 W=1 drivers/nvme/host/apple.o drivers/soc/apple/sart.o > "$OUT/compile.log" 2>&1
rc=$?; echo "driver compile exit=$rc" | tee -a "$OUT/compile.log"
grep -E 'warning:|error:' "$OUT/compile.log" | tee "$OUT/compile-warnings.txt"

log "3. DTB"
make -j"$JOBS" ARCH=arm64 apple/t6050-j716c.dtb > "$OUT/dtb.log" 2>&1
echo "dtb exit=$?" | tee -a "$OUT/dtb.log"
grep -E -i 'warning|error' "$OUT/dtb.log" | grep -v '^make' | tee "$OUT/dtb-warnings.txt"
ls -la arch/arm64/boot/dts/apple/t6050-j716c.dtb | tee -a "$OUT/dtb.log"
if command -v dt-validate >/dev/null 2>&1; then
  make -j"$JOBS" ARCH=arm64 CHECK_DTBS=y apple/t6050-j716c.dtb > "$OUT/dtbs-check.log" 2>&1
  echo "CHECK_DTBS exit=$? (informational)" | tee -a "$OUT/dtbs-check.log"
  grep -c -E "smc|mbox@28c608000" "$OUT/dtbs-check.log" | sed 's/^/schema lines mentioning smc nodes: /' | tee -a "$OUT/dtbs-check.log"
else
  echo "dt-validate not installed: CHECK_DTBS skipped" | tee "$OUT/dtbs-check.log"
fi

log "4. checkpatch (informational)"
for p in "$IN"/patches/0005-*.patch "$IN"/patches/0007-*.patch; do
  echo "== $(basename "$p")"; ./scripts/checkpatch.pl --strict --no-signoff "$p" 2>&1
done > "$OUT/checkpatch.txt" 2>&1
grep -E '^(ERROR|WARNING|CHECK):' "$OUT/checkpatch.txt" | sort | uniq -c | sort -rn > "$OUT/checkpatch-summary.txt"

log "5. probe audit"
bash "$IN/probe-audit.sh" arch/arm64/boot/dts/apple/t6050.dtsi > "$OUT/probe-audit.txt" 2>&1 || true
grep -E "smc|mailbox|nvme" "$OUT/probe-audit.txt" | tee "$OUT/probe-audit-smc-nvme.txt"

{
  echo "am: $(grep -c '^Applying' "$OUT/am.log") patches applied, exit $(grep -o 'exit=[0-9]*' "$OUT/am.log" | tail -1)"
  echo "compile: $(grep -o 'exit=[0-9]*' "$OUT/compile.log" | tail -1), warnings in our files: $(grep -c -E 'apple\.c|sart\.c' "$OUT/compile-warnings.txt")"
  echo "dtb: $(grep -o 'exit=[0-9]*' "$OUT/dtb.log" | head -1), dtc warnings: $(wc -l < "$OUT/dtb-warnings.txt")"
  echo "dtbs_check: $(head -1 "$OUT/dtbs-check.log" | cut -c1-120)"
} | tee "$OUT/RESULT.txt"
log "done"

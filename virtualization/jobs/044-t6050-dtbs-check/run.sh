#!/bin/bash
# job 044: DT schema validation of the draft t6050 (M5 Max, J716c) device tree, offline.
# Nothing boots, nothing touches the M5, no network.  Like job 043, a clean git worktree of
# the pinned base commit is taken from the tree job 020 fetched (/var/tmp/t6050-build/linux,
# tag "base"); if that tree is missing the job stops instead of fetching.  dtschema comes
# from the venv job 020 created (/var/tmp/t6050-build/dtvenv, used by jobs 032/038/040-042);
# if that venv is missing or broken the job stops instead of installing anything.
#  1. inputs + toolchain (dtschema, pylibfdt, jsonschema versions from the venv);
#  2. private worktree of the base commit, series 0001-0007 applied with git am;
#  3. make dt_binding_check DT_SCHEMA_FILES=apple (every binding whose path contains
#     "apple", incl. the ones the series touches, with their examples);
#  4. make CHECK_DTBS=y apple/t6050-j716c.dtb (full processed schema, every binding);
#  5. the same CHECK_DTBS on two Asahi reference boards (t8132-j715 = M4 Max 16", t6031-j516c
#     = M3 Max 16"), so that tree-wide/pre-existing findings can be told from ours;
#  6. CHECK_DTBS of the t6050 DTB without the series' three binding patches (0001/0004/0006
#     reverted on the DT only) is NOT done: the series is validated as a whole;
#  7. copies of the binding files that matter to the triage (GPL/BSD Linux docs) into out/.
set -u
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
OUT=/mnt/job/out
IN=/mnt/job/in
BASE=/var/tmp/t6050-build/linux
VENV=/var/tmp/t6050-build/dtvenv
WORK=/var/tmp/ilinux-dtbs-check/linux
BASE_COMMIT=77cb8f24c2381a8abb7272d7bbdec548d6426a8a
DTB=apple/t6050-j716c.dtb
REF_DTBS="apple/t8132-j715.dtb apple/t6031-j516c.dtb"
JOBS=$(nproc)
log() { printf '[%s] %s\n' "$(date +%T)" "$*"; }
rm -rf "$OUT"/*; mkdir -p "$OUT"
exec > "$OUT/script.log" 2>&1
export KBUILD_BUILD_TIMESTAMP='@0' KBUILD_BUILD_USER=ilinux KBUILD_BUILD_HOST=job044

log "1. inputs + toolchain"
ls -la "$IN/patches" | tee "$OUT/inputs.txt"
sha256sum "$IN"/patches/*.patch > "$OUT/inputs-sha256.txt"
if [ ! -d "$BASE/.git" ]; then echo "NO BASE TREE at $BASE (job 020 never ran here): stopping, no fetch" | tee "$OUT/RESULT.txt"; exit 2; fi
if [ ! -x "$VENV/bin/dt-validate" ]; then
  { echo "NO DTSCHEMA VENV at $VENV (job 020's): stopping, nothing installed";
    echo "system python: $(python3 --version 2>&1); pip: $(python3 -m pip --version 2>&1 | head -1)";
    ls -la "$VENV" 2>&1; find /var/tmp -maxdepth 4 -name dt-validate 2>/dev/null; } | tee "$OUT/RESULT.txt"
  exit 3
fi
export PATH="$VENV/bin:$PATH"
{ uname -srm; gcc --version | head -1; dtc --version; echo "system python: $(python3 --version 2>&1)";
  echo "venv python: $("$VENV/bin/python3" --version 2>&1) ($(readlink -f "$VENV/bin/python3"))";
  echo "dt-validate: $(dt-validate --version 2>&1)";
  "$VENV/bin/python3" -m pip list 2>/dev/null | grep -i -E 'dtschema|libfdt|jsonschema|ruamel|rfc3987|yamllint|^pip ' ;
  "$VENV/bin/python3" -c 'import dtschema, libfdt; print("import dtschema+libfdt OK")' 2>&1; } | tee "$OUT/toolchain.txt"
if ! "$VENV/bin/python3" -c 'import dtschema, libfdt' 2>/dev/null; then
  echo "DTSCHEMA VENV BROKEN (import fails, see toolchain.txt): stopping, nothing installed" | tee "$OUT/RESULT.txt"; exit 3
fi
# job 020's own dtbs_check output, if it is still there (reference only: older 0007)
for f in dtbs-check-exit.txt dtbs_check-t6050.txt; do
  [ -f "/var/tmp/t6050-build/out/$f" ] && cp "/var/tmp/t6050-build/out/$f" "$OUT/job020-$f"
done

log "2. worktree + series"
mkdir -p "$(dirname "$WORK")"
cd "$BASE"
git worktree remove --force "$WORK" 2>/dev/null; rm -rf "$WORK"; git worktree prune
git worktree add --detach "$WORK" "$BASE_COMMIT" 2>/dev/null || git worktree add --detach "$WORK" base || { echo "cannot create a worktree at the base commit" | tee "$OUT/RESULT.txt"; exit 2; }
cd "$WORK"
git log -1 --format='base %H %s' | tee "$OUT/base.txt"
git -c user.name=ilinux -c user.email=ilinux@localhost am "$IN"/patches/000*.patch > "$OUT/am.log" 2>&1
echo "git am exit=$?" | tee -a "$OUT/am.log"
git log --oneline -8 | tee "$OUT/series.txt"
grep -n DT_SCHEMA_MIN_VERSION Documentation/devicetree/bindings/Makefile | head -1 | tee -a "$OUT/toolchain.txt"
make -j"$JOBS" ARCH=arm64 defconfig > "$OUT/config.log" 2>&1
grep -E 'CONFIG_ARCH_APPLE=' .config | tee -a "$OUT/config.log"

log "3. dt_binding_check DT_SCHEMA_FILES=apple"
make -j"$JOBS" ARCH=arm64 dt_binding_check DT_SCHEMA_FILES=apple > "$OUT/dt_binding_check.log" 2>&1
echo "dt_binding_check exit=$?" | tee -a "$OUT/dt_binding_check.log"
# findings = lines that are not make/kbuild chatter
grep -v -E '^(make|  (CHKDT|LINT|DTC|DTEX|SCHEMA|DTB|UPD|HOSTCC|HOSTLD|CC|LD|YACC|LEX|GEN|WRAP|SYSHDR|SYSTBL|MKDIR|CALL)\b|#|dt_binding_check exit)' "$OUT/dt_binding_check.log" \
  | grep -v -E '^\s*$' > "$OUT/dt_binding_check-findings.txt" || true
echo "dt_binding_check findings: $(wc -l < "$OUT/dt_binding_check-findings.txt") lines" | tee -a "$OUT/dt_binding_check.log"
ls -la Documentation/devicetree/bindings/processed-schema.json 2>&1 | tee -a "$OUT/dt_binding_check.log"

log "4. CHECK_DTBS=y $DTB (full schema)"
rm -f Documentation/devicetree/bindings/processed-schema.json
make -j"$JOBS" ARCH=arm64 CHECK_DTBS=y "$DTB" > "$OUT/dtbs-check.log" 2>&1
echo "CHECK_DTBS exit=$?" | tee -a "$OUT/dtbs-check.log"
grep -E '^arch/arm64/boot/dts/apple/t6050-j716c\.dtb:' "$OUT/dtbs-check.log" > "$OUT/dtbs-check-t6050.txt" || true
# "from schema" continuation lines belong to the preceding finding: keep the raw block too
awk '/^arch\/arm64\/boot\/dts\/apple\/t6050-j716c\.dtb:/{p=1; print; next} /^\t/{if(p) print; next} {p=0}' "$OUT/dtbs-check.log" > "$OUT/dtbs-check-t6050-full.txt"
sed -E 's/^arch\/arm64\/boot\/dts\/apple\/t6050-j716c\.dtb: //; s/@[0-9a-f]+//g; s/\[[^]]*\]/[..]/g' "$OUT/dtbs-check-t6050.txt" \
  | sort | uniq -c | sort -rn > "$OUT/dtbs-check-t6050-summary.txt"
echo "t6050-j716c.dtb findings: $(wc -l < "$OUT/dtbs-check-t6050.txt")" | tee -a "$OUT/dtbs-check.log"
ls -la arch/arm64/boot/dts/apple/t6050-j716c.dtb | tee -a "$OUT/dtbs-check.log"

log "5. CHECK_DTBS=y reference boards: $REF_DTBS"
make -j"$JOBS" ARCH=arm64 CHECK_DTBS=y $REF_DTBS > "$OUT/dtbs-check-ref.log" 2>&1
echo "CHECK_DTBS (reference) exit=$?" | tee -a "$OUT/dtbs-check-ref.log"
for d in $REF_DTBS; do
  b=$(basename "$d" .dtb)
  grep -E "^arch/arm64/boot/dts/apple/$b\.dtb:" "$OUT/dtbs-check-ref.log" > "$OUT/dtbs-check-$b.txt" || true
  sed -E "s/^arch\/arm64\/boot\/dts\/apple\/$b\.dtb: //; s/@[0-9a-f]+//g; s/\[[^]]*\]/[..]/g" "$OUT/dtbs-check-$b.txt" \
    | sort | uniq -c | sort -rn > "$OUT/dtbs-check-$b-summary.txt"
  echo "$b.dtb findings: $(wc -l < "$OUT/dtbs-check-$b.txt")" | tee -a "$OUT/dtbs-check-ref.log"
done

log "7. binding files for the triage"
mkdir -p "$OUT/bindings"
for f in mfd/apple,smc.yaml gpio/apple,smc-gpio.yaml hwmon/apple,smc-hwmon.yaml \
         serial/samsung_uart.yaml arm/cpus.yaml opp/opp-v2.yaml opp/opp-v2-base.yaml \
         nvme/apple,nvme-ans.yaml iommu/apple,sart.yaml arm/apple.yaml \
         interrupt-controller/apple,aic2.yaml mailbox/apple,mailbox.yaml; do
  [ -f "Documentation/devicetree/bindings/$f" ] && { mkdir -p "$OUT/bindings/$(dirname $f)"; cp "Documentation/devicetree/bindings/$f" "$OUT/bindings/$f"; }
done
ls Documentation/devicetree/bindings/mfd/ | grep -i apple > "$OUT/bindings/mfd-apple-list.txt" 2>&1
grep -rl "apple,smc" Documentation/devicetree/bindings/ > "$OUT/bindings/files-mentioning-apple-smc.txt" 2>&1
grep -n "compatible" drivers/mfd/macsmc.c | head -20 > "$OUT/bindings/macsmc-c-compatibles.txt" 2>&1
grep -rn "apple,.*-smc\|apple,smc\"" arch/arm64/boot/dts/apple/*.dtsi | grep compatible | sort -u > "$OUT/bindings/dts-smc-compatibles.txt" 2>&1
ls "$OUT/bindings"

{
  echo "am: $(grep -c '^Applying' "$OUT/am.log") patches applied, $(grep -o 'exit=[0-9]*' "$OUT/am.log" | tail -1)"
  echo "dtschema: $(grep -i '^dtschema ' "$OUT/toolchain.txt" | head -1 | tr -s ' '); $(grep 'dt-validate:' "$OUT/toolchain.txt")"
  echo "dt_binding_check (DT_SCHEMA_FILES=apple): $(grep -o 'exit=[0-9]*' "$OUT/dt_binding_check.log" | head -1), $(wc -l < "$OUT/dt_binding_check-findings.txt") finding lines"
  echo "dtbs_check t6050-j716c.dtb: $(grep -o 'CHECK_DTBS exit=[0-9]*' "$OUT/dtbs-check.log" | head -1), $(wc -l < "$OUT/dtbs-check-t6050.txt") findings"
  for d in $REF_DTBS; do b=$(basename "$d" .dtb); echo "dtbs_check $b.dtb (reference): $(wc -l < "$OUT/dtbs-check-$b.txt") findings"; done
} | tee "$OUT/RESULT.txt"
log "done"

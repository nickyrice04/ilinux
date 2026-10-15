#!/bin/bash
# boot035: the boot034 payload with the seven SMC-owned PMGR domains removed from the
# Stage-B DT (Asahi exposes no smc_* power domain on any SoC). Image, config, initramfs
# and m1n1 stay byte-identical to boot034; only t6050-j716c-stage-b.dtb changes.
set -euo pipefail
mkdir -p /mnt/ilinux
mount -t virtiofs ilinux /mnt/ilinux
OUT=/mnt/job/out
SRC=/mnt/ilinux/build/native-boot034/verified
DTB=t6050-j716c-stage-b.dtb
BOOT034_DTB=4b3adee52465b809e9c8a1946b7610c63f1ae3c0b24f7334cd485260da84adce
PMGR=/soc/power-management@288300000
mkdir -p "$OUT/export"
test "$(sha256sum "$SRC/$DTB" | cut -d' ' -f1)" = "$BOOT034_DTB"
cp -a "$SRC/." "$OUT/export/"
for off in 8028 8030 8038 8040 8048 8050 8058; do
    label=$(fdtget -t s "$OUT/export/$DTB" "$PMGR/power-controller@$off" label)
    case "$label" in smc_i2cm[0-6]) ;; *) echo "unexpected node at $off: $label"; exit 1 ;; esac
    fdtput -r "$OUT/export/$DTB" "$PMGR/power-controller@$off"
done
# Exactly seven nodes gone, nothing else changed: compare the decompiled sources.
dtc -q -I dtb -O dts -s "$SRC/$DTB" > "$OUT/before.dts"
dtc -q -I dtb -O dts -s "$OUT/export/$DTB" > "$OUT/after.dts"
diff -u "$OUT/before.dts" "$OUT/after.dts" > "$OUT/dt.diff" || test "$?" = 1
grep -c '^-.*power-controller@80[2-5][08] {' "$OUT/dt.diff" > "$OUT/removed-nodes.txt"
test "$(cat "$OUT/removed-nodes.txt")" = 7
! grep -q '^+' <(tail -n +3 "$OUT/dt.diff")
! grep -qi 'smc_' "$OUT/after.dts"
grep -c 'pmgr-pwrstate' "$OUT/after.dts" > "$OUT/pwrstate-nodes.txt"
# Schema check of the changed binding (same tools as job 032).
export PATH=/var/tmp/t6050-build/dtvenv/bin:$PATH
WORK=/var/tmp/ilinux-boot034/linux
dt-validate -l apple,pmgr-pwrstate -s "$WORK/Documentation/devicetree/bindings/processed-schema.json" "$OUT/export/$DTB" > "$OUT/dt-check.log" 2>&1 || true
dt-validate -s "$WORK/Documentation/devicetree/bindings/processed-schema.json" "$OUT/export/$DTB" > "$OUT/dt-check-full.log" 2>&1 || true
dt-validate -s "$WORK/Documentation/devicetree/bindings/processed-schema.json" "$SRC/$DTB" > "$OUT/dt-check-full-before.log" 2>&1 || true
{ uname -srm; dtc --version; } > "$OUT/toolchain-dt.txt"
(cd "$OUT/export" && sha256sum Image "$DTB" > ../export-sha256.txt)
echo "PASS: boot035 Stage-B DT = boot034 minus 7 smc_i2cm nodes; $(cat "$OUT/pwrstate-nodes.txt") pwrstate nodes remain"

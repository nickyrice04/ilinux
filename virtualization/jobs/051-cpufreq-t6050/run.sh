#!/bin/bash
# Offline only. Build a module against boot042 without changing that tree or its Image.
set -euo pipefail
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
I=/mnt/ilinux
X=$I/kernel/experiments/cpufreq-t6050
OUT=/mnt/job/out
K=/var/tmp/ilinux-boot042/linux
B=/var/tmp/ilinux-cpufreq-051
mkdir -p "$OUT" "$B"
exec > "$OUT/run-detail.log" 2>&1
BASE_C=e4efe79b653dc07c18a2bacc607fe69f8144ead11bf10cd4ef9407396ca808d2
printf '%s  %s\n' "$BASE_C" "$K/drivers/cpufreq/apple-soc-cpufreq.c" | sha256sum -c -
cmp "$K/.config" "$I/build/native-boot042/verified/kernel.config"
cmp "$K/arch/arm64/boot/Image" "$I/build/native-boot042/verified/Image"
grep -q '^CONFIG_ARM_APPLE_SOC_CPUFREQ=m$' "$K/.config"
{ uname -srm; gcc --version | head -1; ld --version | head -1; dtc --version; python3 --version; } > "$OUT/toolchain.txt"
mkdir -p "$B/drivers/cpufreq"
cp "$K/drivers/cpufreq/apple-soc-cpufreq.c" "$B/drivers/cpufreq/"
patch --batch --fuzz=0 -d "$B" -p1 < "$X/patches/0001-cpufreq-apple-soc-cpufreq-t6050-M5-Max-cluster-DVFS.patch"
# An external build reuses the exact boot042 generated headers and Module.symvers.
printf 'obj-m := apple-soc-cpufreq.o\n' > "$B/drivers/cpufreq/Makefile"
make -C "$K" M="$B/drivers/cpufreq" -j2 W=1 modules > "$OUT/build.log" 2>&1
if grep -E 'warning:|error:' "$OUT/build.log"; then exit 1; fi
cp "$B/drivers/cpufreq/apple-soc-cpufreq.ko" "$OUT/"
modinfo "$OUT/apple-soc-cpufreq.ko" > "$OUT/modinfo.txt"
objdump -dr "$OUT/apple-soc-cpufreq.ko" > "$OUT/module-disassembly.txt"
python3 -I "$X/test_driver.py" "$B/drivers/cpufreq/apple-soc-cpufreq.c" "$B/tests" > "$OUT/driver-tests.txt" 2>&1
python3 -I "$X/test_make_cpufreq_dt.py" > "$OUT/dt-tests.txt" 2>&1
python3 -I "$X/test_allowance.py" > "$OUT/allowance-tests.txt" 2>&1
python3 -I "$X/test_measurement.py" > "$OUT/measurement-tests.txt" 2>&1
python3 -I "$X/make_cpufreq_dt.py" "$I/build/native-boot042/verified/t6050-j716c-stage-b.dtb" \
    "$I/hardware/adt/adt-sanitized.json" "$OUT/candidate.dtb" "$OUT/delta.json"
dtc -I dtb -O dts "$OUT/candidate.dtb" > "$OUT/candidate.dts" 2> "$OUT/dtc.log"
# A narrow candidate binding. No assertion of full-board schema cleanliness.
export PATH=/var/tmp/t6050-build/dtvenv/bin:$PATH
SCHEMA=$B/schemas/cpufreq/apple,t6050-cluster-cpufreq.yaml
mkdir -p "$(dirname "$SCHEMA")"
cp "$X/dt/apple,t6050-cluster-cpufreq.yaml" "$SCHEMA"
dt-doc-validate "$SCHEMA" > "$OUT/schema-doc.log" 2>&1
[ ! -s "$OUT/schema-doc.log" ]
dt-validate -s "$SCHEMA" -l apple,t6050-cluster-cpufreq "$OUT/candidate.dtb" > "$OUT/schema.log" 2>&1
[ ! -s "$OUT/schema.log" ]
# Prove the baseline still matches. No module load, native register access, or boot.
cmp "$K/.config" "$I/build/native-boot042/verified/kernel.config"
cmp "$K/arch/arm64/boot/Image" "$I/build/native-boot042/verified/Image"
(cd "$OUT" && sha256sum apple-soc-cpufreq.ko candidate.dtb) > "$OUT/SHA256SUMS"
echo 'PASS: offline module build, extracted callback ASan/UBSan tests, candidate DT and allowance tests; native NOT RUN' > "$OUT/summary.txt"

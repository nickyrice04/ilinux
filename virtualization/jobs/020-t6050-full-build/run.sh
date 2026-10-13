#!/bin/bash
# Job 020: full native t6050 kernel build + DT validation + dockchannel-HID
# driver build (baseline vs hardened) + a minimal diagnostic initramfs.
#
# Reproducible: fetches the pinned AsahiLinux/linux commit (shallow), applies
# the committed t6050 series (0001-0007), builds Image+modules+DTBs, validates
# the DT, builds the real in-tree dockchannel-hid driver with and without the
# a351bff hardening patch, and assembles a RAM diagnostic initramfs.
#
# Inputs expected under $SRC (pushed by the host before launch):
#   patches/t6050/000*.patch         the 7-patch native series
#   patches/dockchannel/0001-*.patch B's input-bounds hardening patch
# Writes artifacts and logs to $OUT. Never boots anything.
set -u
SRC=/var/tmp/t6050-build
OUT=$SRC/out
ASAHI_COMMIT=77cb8f24c2381a8abb7272d7bbdec548d6426a8a
KDIR=$SRC/linux
JOBS=$(nproc)
mkdir -p "$OUT"
export KBUILD_BUILD_TIMESTAMP='@0' KBUILD_BUILD_USER=ilinux KBUILD_BUILD_HOST=t6050build
log() { echo "== $* =="; }
sect() { echo; echo "######## $* ########"; }

sect "0. environment"
{ date -u; uname -a; gcc --version | head -1; ld --version | head -1
  make --version | head -1; pahole --version 2>/dev/null; python3 --version
} | tee "$OUT/env.txt"

sect "1. fetch pinned source + apply t6050 series (idempotent)"
if [ ! -d "$KDIR/.git" ]; then
  rm -rf "$KDIR"; mkdir -p "$KDIR"; cd "$KDIR"
  git init -q
  git remote add origin https://github.com/AsahiLinux/linux.git
  git fetch -q --depth 1 origin "$ASAHI_COMMIT" || { echo "FETCH FAILED"; exit 1; }
  git checkout -q FETCH_HEAD
  git tag base
fi
cd "$KDIR"
# clean slate every run so the build and patch set are reproducible
git am --abort 2>/dev/null || true
git reset -q --hard base
git clean -qfdx
git log -1 --format='base %H %ad' | tee "$OUT/base.txt"
git -c user.name=ilinux -c user.email=ilinux@localhost am "$SRC"/patches/t6050/000*.patch \
  > "$OUT/am.log" 2>&1
echo "t6050 am exit=$?" | tee -a "$OUT/am.log"
git log --oneline -8 | tee "$OUT/series.txt"

sect "2. configure (bring-up: 16K pages, framebuffer console, initrd, apple drivers)"
make -j"$JOBS" ARCH=arm64 defconfig > "$OUT/config.log" 2>&1
# 16 KiB pages (Asahi) and the single-core framebuffer bring-up essentials =y
ENABLE="ARM64_16K_PAGES ARCH_APPLE APPLE_RTKIT APPLE_MAILBOX APPLE_SART APPLE_DART
  NVME_APPLE PINCTRL_APPLE_GPIO APPLE_PMGR_PWRSTATE APPLE_WATCHDOG GPIO_MACSMC
  DRM DRM_SIMPLEDRM FB SYSFB_SIMPLEFB FRAMEBUFFER_CONSOLE FRAMEBUFFER_CONSOLE_DETECT_PRIMARY
  BLK_DEV_INITRD RD_GZIP DEVTMPFS DEVTMPFS_MOUNT PRINTK_TIME
  APPLE_DOCKCHANNEL HID_DOCKCHANNEL HID"
for s in $ENABLE; do ./scripts/config --enable "$s" 2>/dev/null; done
./scripts/config --disable ARM64_4K_PAGES 2>/dev/null
# never imply SVE (SME-only hardware, D-009); defconfig does not, so just record march
make -j"$JOBS" ARCH=arm64 olddefconfig >> "$OUT/config.log" 2>&1
grep -E "CONFIG_(ARM64_16K_PAGES|ARCH_APPLE|APPLE_SART|NVME_APPLE|APPLE_DART|APPLE_RTKIT|DRM_SIMPLEDRM|FRAMEBUFFER_CONSOLE|BLK_DEV_INITRD|HID_DOCKCHANNEL|APPLE_PMGR_PWRSTATE)=" .config \
  | sort | tee "$OUT/config-selected.txt"
echo "--- requested but NOT set (missing symbols): ---" | tee -a "$OUT/config-selected.txt"
for s in $ENABLE; do grep -q "CONFIG_$s=" .config || echo "CONFIG_$s unset/absent" ; done \
  | tee -a "$OUT/config-selected.txt"

sect "3. build Image + modules + dtbs"
t0=$(date +%s)
make -j"$JOBS" ARCH=arm64 Image modules dtbs > "$OUT/build.log" 2>&1
rc=$?
echo "build exit=$rc  wall=$(( $(date +%s) - t0 ))s" | tee "$OUT/build-exit.txt"
grep -E "Error|error:|\bwarning:" "$OUT/build.log" | sort | uniq -c | sort -rn > "$OUT/build-warnings.txt" || true
echo "distinct warning/error lines: $(wc -l < "$OUT/build-warnings.txt")" | tee -a "$OUT/build-exit.txt"
ls -l arch/arm64/boot/Image 2>&1 | tee -a "$OUT/build-exit.txt"

sect "4. device-tree validation (dtbs_check)"
python3 -m venv "$SRC/dtvenv" 2>/dev/null && . "$SRC/dtvenv/bin/activate"
pip -q install dtschema yamllint > "$OUT/dtschema-install.log" 2>&1 && \
  echo "dtschema $(python3 -c 'import dtschema,sys;print(dtschema.__version__)' 2>/dev/null)" | tee "$OUT/dtbs-check-exit.txt"
make -j"$JOBS" ARCH=arm64 dtbs_check > "$OUT/dtbs_check-full.log" 2>&1
echo "dtbs_check exit=$?" | tee -a "$OUT/dtbs-check-exit.txt"
grep -iE "t6050|j716c" "$OUT/dtbs_check-full.log" > "$OUT/dtbs_check-t6050.txt" || true
echo "t6050 dtbs_check lines: $(wc -l < "$OUT/dtbs_check-t6050.txt")" | tee -a "$OUT/dtbs-check-exit.txt"
deactivate 2>/dev/null || true

sect "5. dockchannel-hid: real in-tree driver, baseline vs hardened"
DCH=drivers/hid/dockchannel-hid
if [ -d "$DCH" ]; then
  make -j"$JOBS" ARCH=arm64 W=1 "$DCH/" > "$OUT/dch-baseline.log" 2>&1
  echo "dch baseline build exit=$?" | tee "$OUT/dch-exit.txt"
  grep -E "warning:|error:" "$OUT/dch-baseline.log" | sed 's/^[^:]*linux\///' | sort > "$OUT/dch-baseline-warnings.txt" || true
  git apply --stat "$SRC"/patches/dockchannel/0001-*.patch >> "$OUT/dch-exit.txt" 2>&1
  if git apply "$SRC"/patches/dockchannel/0001-*.patch 2>>"$OUT/dch-exit.txt"; then
    echo "dockchannel patch applied" | tee -a "$OUT/dch-exit.txt"
    make -j"$JOBS" ARCH=arm64 W=1 "$DCH/" > "$OUT/dch-patched.log" 2>&1
    echo "dch patched build exit=$?" | tee -a "$OUT/dch-exit.txt"
    grep -E "warning:|error:" "$OUT/dch-patched.log" | sed 's/^[^:]*linux\///' | sort > "$OUT/dch-patched-warnings.txt" || true
    echo "--- NEW warnings introduced by the patch (patched minus baseline): ---" | tee -a "$OUT/dch-exit.txt"
    comm -13 "$OUT/dch-baseline-warnings.txt" "$OUT/dch-patched-warnings.txt" | tee -a "$OUT/dch-exit.txt"
    echo "--- warnings REMOVED by the patch: ---" | tee -a "$OUT/dch-exit.txt"
    comm -23 "$OUT/dch-baseline-warnings.txt" "$OUT/dch-patched-warnings.txt" | tee -a "$OUT/dch-exit.txt"
    git checkout -- "$DCH" 2>/dev/null
  else
    echo "DOCKCHANNEL PATCH DID NOT APPLY to the real tree" | tee -a "$OUT/dch-exit.txt"
  fi
else
  echo "no $DCH in this tree (symbol/driver absent)" | tee "$OUT/dch-exit.txt"
fi

sect "6. minimal diagnostic initramfs (RAM, non-interactive, logs to console)"
IRD=$SRC/initramfs
rm -rf "$IRD"; mkdir -p "$IRD"/{proc,sys,dev}
gcc -static -O2 -o "$IRD/init" "$SRC/diag-init.c" 2> "$OUT/initramfs.log"
echo "diag-init static build exit=$?  size=$(stat -c %s "$IRD/init" 2>/dev/null)" | tee -a "$OUT/initramfs.log"
( cd "$IRD" && find . | cpio -o -H newc 2>>"$OUT/initramfs.log" | gzip -9 > "$SRC/initramfs.cpio.gz" )
echo "initramfs size=$(stat -c %s "$SRC/initramfs.cpio.gz" 2>/dev/null)" | tee -a "$OUT/initramfs.log"

sect "7. artifact digests"
{
  for f in "$KDIR/arch/arm64/boot/Image" \
           "$KDIR/arch/arm64/boot/dts/apple/t6050-j716c.dtb" \
           "$SRC/initramfs.cpio.gz"; do
    [ -f "$f" ] && printf "%s  %s  %s bytes\n" "$(sha256sum "$f" | cut -d' ' -f1)" "$(basename "$f")" "$(stat -c %s "$f")"
  done
  echo "modules: $(find "$KDIR" -name '*.ko' | wc -l) built"
} | tee "$OUT/artifacts.txt"
cp "$KDIR/.config" "$OUT/kernel.config"
sect "DONE"

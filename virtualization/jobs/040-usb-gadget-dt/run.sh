#!/bin/bash
# job 040: offline checks for the USB device-mode Stage-B DT candidate (DT only).
# kernel/experiments/usb-gadget-dt = boot035's Stage-B DT plus three snps,dwc3 peripheral
# nodes and their DARTs, with the atc0-2 PMGR domains disabled. Nothing here boots or
# changes the boot035 package; the kernel tree is only read.
#  1. regenerate the candidate in this VM, compare with the host build, run the tests;
#  2. decompiled diff, dtc warnings, schema checks, probe audit;
#  3. kernel facts from the exact tree that built the boot034 = boot035 Image;
#  4. libcomposite, u_ether and usb_f_eem as external modules for that Image.
set -euo pipefail
mkdir -p /mnt/ilinux
mount -t virtiofs ilinux /mnt/ilinux
OUT=/mnt/job/out
EXP=/mnt/ilinux/kernel/experiments/usb-gadget-dt
SRC=/mnt/ilinux/build/native-boot035/verified
HOST=/mnt/ilinux/build/usb-gadget-dt/t6050-j716c-stage-b.dtb
KTREE=/var/tmp/ilinux-boot034/linux
BASE_SHA=b1105bbf2c207c8c816c4b9cc0231ecc1d49543e05fe4b772bcb153019e186db
IMAGE_SHA=1131a1af5e4d5cfa3206c5eb0afe1a6d72d86a2761a8d906b592e33556882579
mkdir -p "$OUT"
g() { grep "$@" || echo "    (no match: grep $*)"; }   # facts log: a miss is recorded, not fatal

test "$(sha256sum < "$SRC/t6050-j716c-stage-b.dtb" | cut -d' ' -f1)" = "$BASE_SHA"
test "$(sha256sum < "$SRC/Image" | cut -d' ' -f1)" = "$IMAGE_SHA"
test "$(sha256sum < "$KTREE/arch/arm64/boot/Image" | cut -d' ' -f1)" = "$IMAGE_SHA"
{ uname -srm; python3 --version; dtc --version; gcc --version | head -1; } > "$OUT/toolchain.txt"

# ---- 1. same candidate from this VM's Python; unit and mutation tests ------------------
python3 -I "$EXP/make_dt.py" "$SRC/t6050-j716c-stage-b.dtb" /mnt/ilinux/hardware/adt/adt-sanitized.json \
    "$OUT/candidate.dtb" "$OUT/dt-delta.json" > "$OUT/make-dt.log"
cmp "$OUT/candidate.dtb" "$HOST"
python3 -I "$EXP/test_usb_dt.py" -v > "$OUT/tests.log" 2>&1
tail -1 "$OUT/tests.log"
python3 -I "$EXP/audit_domains.py" "$SRC/t6050-j716c-stage-b.dtb" "$OUT/candidate.dtb" > "$OUT/domain-audit.json"

# ---- 2. DT checks ------------------------------------------------------------------------
dtc -I dtb -O dts -s "$SRC/t6050-j716c-stage-b.dtb" > "$OUT/before.dts" 2> "$OUT/dtc-warnings-before.log"
dtc -I dtb -O dts -s "$OUT/candidate.dtb" > "$OUT/after.dts" 2> "$OUT/dtc-warnings.log"
# no new dtc warnings (this dtc may report pre-existing ones that the host's 1.8.1 does not)
diff <(sed 's/^[^:]*: //' "$OUT/dtc-warnings-before.log" | sort) \
     <(sed 's/^[^:]*: //' "$OUT/dtc-warnings.log" | sort) > "$OUT/dtc-new-warnings.diff" ||
    { cat "$OUT/dtc-new-warnings.diff"; exit 1; }
diff -u "$OUT/before.dts" "$OUT/after.dts" > "$OUT/dt.diff" || test "$?" = 1
test "$(grep -c '^+[^+]' "$OUT/dt.diff")" = 84     # 3 x 13 node lines, 39 status, 6 phandles
test "$(grep -c '^-[^-]' "$OUT/dt.diff")" = 12     # 6 DART status, 6 DART power-domains
export PATH=/var/tmp/t6050-build/dtvenv/bin:$PATH
SCHEMA=$KTREE/Documentation/devicetree/bindings/processed-schema.json
for s in snps,dwc3 apple,dart apple,pmgr-pwrstate; do
    dt-validate -l "$s" -s "$SCHEMA" "$OUT/candidate.dtb" > "$OUT/dt-check-$s.log" 2>&1 || true
done
dt-validate -s "$SCHEMA" "$OUT/candidate.dtb" > "$OUT/dt-check-full.log" 2>&1 || true
dt-validate -s "$SCHEMA" "$SRC/t6050-j716c-stage-b.dtb" > "$OUT/dt-check-full-before.log" 2>&1 || true
wc -l "$OUT"/dt-check-*.log > "$OUT/dt-check-summary.txt"
if [ -d /var/tmp/t6050-build/linux ]; then
    bash /mnt/ilinux/kernel/experiments/t6050-dt/probe-audit.sh "$OUT/after.dts" > "$OUT/probe-audit.txt" 2>&1
else
    echo "no /var/tmp/t6050-build/linux; generic probe audit skipped" > "$OUT/probe-audit.txt"
fi

# ---- 3. kernel facts from the exact tree (read only) -------------------------------------
{
echo "kernel release: $(cat "$KTREE/include/config/kernel.release")"
echo "== .config of the boot034 = boot035 Image"
g -E '^(# )?CONFIG_(USB_DWC3|USB_DWC3_DUAL_ROLE|USB_DWC3_GADGET|USB_DWC3_HOST|USB_DWC3_APPLE|USB_GADGET|USB_LIBCOMPOSITE|USB_CONFIGFS|USB_CONFIGFS_EEM|USB_CONFIGFS_NCM|USB_F_EEM|USB_F_NCM|USB_U_ETHER|USB_ETH|USB_ETH_EEM|USB_ETH_RNDIS|IP_PNP|PHY_APPLE_ATC|APPLE_DART|MODULES)( is not set|=)' "$KTREE/.config"
echo "== dwc3 core: compatible, mode, speed and the four quirks the candidate sets"
g -n -E '"snps,dwc3"|usb_get_dr_mode|usb_get_maximum_speed|snps,usb2-gadget-lpm-disable|snps,dis_u2_susphy_quirk|snps,dis_u3_susphy_quirk|snps,dis_enblslpm_quirk' "$KTREE/drivers/usb/dwc3/core.c"
echo "== dwc3 glue drivers that could also match (compatible strings)"
for f in "$KTREE"/drivers/usb/dwc3/dwc3-*.c; do g -H -n -E '\.compatible *= *"(snps|apple),' "$f"; done
echo "== EEM: endpoint types (bulk only expected)"
g -n -E 'USB_ENDPOINT_XFER_[A-Z]+' "$KTREE/drivers/usb/gadget/function/f_eem.c"
echo "== NCM: endpoint types (an interrupt notify endpoint expected)"
g -n -E 'USB_ENDPOINT_XFER_[A-Z]+' "$KTREE/drivers/usb/gadget/function/f_ncm.c"
echo "== legacy Ethernet gadget Kconfig"
awk '/^config USB_ETH$/,/^config USB_G_NCM$/' "$KTREE/drivers/usb/gadget/legacy/Kconfig"
echo "== how precomposed (legacy) gadgets are chosen"
g -n -B2 -A8 'USB Gadget precomposed configurations' "$KTREE/drivers/usb/gadget/Kconfig"
echo "== legacy ether.c: IDs and configuration order"
g -n -E 'define (EEM|CDC|RNDIS)_(VENDOR|PRODUCT)_NUM|usb_add_config|has_rndis\(\)|use_eem' "$KTREE/drivers/usb/gadget/legacy/ether.c"
echo "== UDC selection for legacy and configfs gadgets"
g -n -E 'udc_name|gadget_driver_pending_list|check_pending_gadget_drivers' "$KTREE/drivers/usb/gadget/udc/core.c"
echo "== apple-dart: shared fault IRQ, several DARTs per master, locked DARTs"
g -n -E 'IRQF_SHARED|MAX_DARTS_PER_DEVICE|locked' "$KTREE/drivers/iommu/apple-dart.c"
echo "== initcall_debug probe line (the native pass signal)"
g -n -E 'probe of %s returned' "$KTREE/drivers/base/dd.c"
echo "== dwc3 core soft reset (what a lost PHY clock looks like)"
g -n -E 'dwc3_core_soft_reset|ETIMEDOUT|-110|failed to initialize core' "$KTREE/drivers/usb/dwc3/core.c"
} > "$OUT/kernel-facts.txt" 2>&1

# ---- 4. EEM gadget modules for the exact Image (built outside the read-only tree) ---------
KREL=$(cat "$KTREE/include/config/kernel.release")
KM=/tmp/ilinux-usb-eem
rm -rf "$KM"
mkdir -p "$KM/gadget/function"
cp "$KTREE"/drivers/usb/gadget/*.[ch] "$KM/gadget/"
cp "$KTREE"/drivers/usb/gadget/function/*.[ch] "$KM/gadget/function/"
cat > "$KM/gadget/Kbuild" <<'EOF'
ccflags-y := -I$(srctree)/drivers/usb/gadget/udc
obj-m := libcomposite.o function/
libcomposite-y := usbstring.o config.o epautoconf.o composite.o functions.o configfs.o u_f.o
EOF
cat > "$KM/gadget/function/Kbuild" <<'EOF'
ccflags-y := -I$(src)/.. -I$(srctree)/drivers/usb/gadget/udc -I$(src)
obj-m := u_ether.o usb_f_eem.o
usb_f_eem-y := f_eem.o
EOF
make -C "$KTREE" M="$KM/gadget" -j"$(nproc)" modules > "$OUT/eem-modules-build.log" 2>&1 ||
    { tail -30 "$OUT/eem-modules-build.log"; exit 1; }
mkdir -p "$OUT/eem-modules"
for m in libcomposite u_ether usb_f_eem; do
    f=$(find "$KM" -name "$m.ko")
    cp "$f" "$OUT/eem-modules/"
    modinfo -F vermagic "$f"
done > "$OUT/eem-vermagic.txt"
test "$(sort -u "$OUT/eem-vermagic.txt" | wc -l)" = 1
vermagic=$(head -1 "$OUT/eem-vermagic.txt")
case "$vermagic" in "$KREL "*) ;; *) echo "vermagic $vermagic is not release $KREL"; exit 1 ;; esac
strings -n 20 "$SRC/Image" | grep -qxF "$vermagic"
modinfo "$OUT/eem-modules/usb_f_eem.ko" | g -E '^(alias|depends|vermagic|license|name):' > "$OUT/eem-modinfo.txt"
(cd "$OUT/eem-modules" && sha256sum *.ko > ../eem-modules-sha256.txt)

echo "PASS: candidate $(sha256sum < "$OUT/candidate.dtb" | cut -c1-16) reproduced; dt diff +84/-12; EEM modules built for $KREL"

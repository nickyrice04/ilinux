#!/bin/bash
# Native Omarchy acceptance checks (agent C). Read-only and safe:
#   * never writes to any block device or mounts anything;
#   * never attempts suspend (it only reports what the kernel advertises);
#   * never touches macOS/APFS volumes.
# Classifies each check pass / DEGRADED (expected-absent hardware) / FAIL.
# Usage: acceptance-checks.sh > native-acceptance-$(date +%F).txt
set -u
pass() { printf '[ PASS ] %s\n' "$*"; }
degr() { printf '[DEGRAD] %s\n' "$*"; }
fail() { printf '[ FAIL ] %s\n' "$*"; }
info() { printf '         %s\n' "$*"; }

echo "=== native Omarchy acceptance checks $(date -u +%FT%TZ) ==="
uname -a
[ -r /proc/device-tree/model ] && info "DT model: $(tr -d '\0' < /proc/device-tree/model)"

echo; echo "--- CPUs ---"
online=$(nproc)
total=$(ls -d /sys/devices/system/cpu/cpu[0-9]* 2>/dev/null | wc -l)
info "online $online of $total present"
[ "$online" -ge 2 ] && pass "SMP: $online cores online" || degr "single-core only ($online) — SMP unresolved (plan 1.2)"
caps=$(cat /sys/devices/system/cpu/cpu*/cpu_capacity 2>/dev/null | sort -u | tr '\n' ' ')
[ -n "$caps" ] && info "cpu_capacity values: $caps" || degr "no cpu_capacity (capacity/EAS not set up)"

echo; echo "--- storage (READ-ONLY) ---"
if command -v nvme >/dev/null && [ -e /dev/nvme0 ]; then
  nvme list 2>/dev/null | sed 's/^/         /' && pass "NVMe controller responds"
else
  info "nvme-cli or /dev/nvme0 not present"; degr "NVMe not enumerated (patches 0001-0005 unvalidated)"
fi
mnt=$(mount | grep -iE 'apfs|/dev/nvme.*macos' || true)
[ -z "$mnt" ] && pass "no macOS/APFS volume mounted" || fail "a macOS/APFS volume is mounted: $mnt"

echo; echo "--- display ---"
if [ -e /dev/fb0 ] || ls /sys/class/graphics/fb[0-9]* >/dev/null 2>&1; then
  pass "framebuffer present ($(ls /sys/class/graphics/ 2>/dev/null | grep -c fb) fb)"
else
  fail "no framebuffer"
fi
ls /sys/class/drm/card*/device/driver 2>/dev/null | sed 's/^/         drm: /'
glr=$(command -v glxinfo >/dev/null && glxinfo 2>/dev/null | grep -i 'OpenGL renderer' | head -1)
[ -n "$glr" ] && info "$glr (llvmpipe expected without a G17 driver)"

echo; echo "--- input ---"
if grep -qiE 'keyboard|dockchannel|hid' /proc/bus/input/devices 2>/dev/null; then
  pass "a keyboard/HID input device exists"; grep -iE 'Name=' /proc/bus/input/devices | sed 's/^/         /'
else
  degr "no keyboard yet (use USB; native MTP not up)"
fi

echo; echo "--- audio ---"
if [ -e /proc/asound/cards ] && grep -qvi 'no soundcards' /proc/asound/cards; then
  pass "sound card present"; sed 's/^/         /' /proc/asound/cards
else
  degr "no audio (expected — not brought up)"
fi

echo; echo "--- idle / power ---"
drv=$(cat /sys/devices/system/cpu/cpuidle/current_driver 2>/dev/null)
info "cpuidle driver: ${drv:-none}; cmdline: $(cat /proc/cmdline)"
grep -q 'idle=nop' /proc/cmdline && pass "idle=nop workaround present (M4+ WFI state loss)" \
  || degr "idle=nop not on cmdline — check WFI safety before relying on idle"
for z in /sys/class/thermal/thermal_zone*/temp; do [ -r "$z" ] && info "temp $(basename $(dirname $z)): $(cat $z)"; done

echo; echo "--- suspend (REPORT ONLY, never attempted) ---"
info "/sys/power/state advertises: $(cat /sys/power/state 2>/dev/null || echo none)"
degr "suspend expected NOT to work yet; not attempted"

echo; echo "--- Omarchy shell tests (if present) ---"
if [ -d "${OMARCHY_PATH:-/usr/share/omarchy}/test" ]; then
  info "run: ${OMARCHY_PATH:-/usr/share/omarchy}/test/all  (review which apply on this hardware)"
else
  info "Omarchy test tree not found; skip"
fi
echo; echo "=== end. Degraded = expected-absent hardware; investigate any FAIL or an unexpected DEGRAD. ==="

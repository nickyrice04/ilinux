#!/bin/sh
# test-wait-usb-host.sh: link-overlay/usr/local/lib/ilinux/wait-usb-host against a fake configfs and UDC
# class in a scratch directory (WAIT_USB_HOST_ROOT). Runs on the Mac or in the job VM; no root, no USB.
# A port no host has configured (not attached, powered, default, addressed) waits silently; configured
# or suspended returns within about a second; a tty no gadget owns, or a UDC that goes away, fails.
set -u
H=$(cd "$(dirname "$0")" && pwd)/link-overlay/usr/local/lib/ilinux/wait-usb-host
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
export WAIT_USB_HOST_ROOT=$T
fails=0
ok() { echo "PASS $*"; }
bad() { echo "FAIL $*"; fails=$((fails + 1)); }
# gadget NAME TTYNUM UDC STATE: one gadget whose gser.ssh is /dev/ttyGS<TTYNUM>, bound to UDC in STATE
gadget() {
    mkdir -p "$T/sys/kernel/config/usb_gadget/ilinux-$1/functions/gser.ssh" "$T/sys/class/udc/$3"
    echo "$2" > "$T/sys/kernel/config/usb_gadget/ilinux-$1/functions/gser.ssh/port_num"
    echo "$3" > "$T/sys/kernel/config/usb_gadget/ilinux-$1/UDC"
    echo "$4" > "$T/sys/class/udc/$3/state"
}
# waits TTY SECONDS: 0 if the helper is still waiting after SECONDS (and said nothing), else 1
waits() {
    sh "$H" "$1" > "$T/out" 2>&1 &
    pid=$!
    sleep "$2"
    if kill -0 "$pid" 2> /dev/null; then kill "$pid"; wait "$pid" 2> /dev/null; [ ! -s "$T/out" ]; return; fi
    wait "$pid" 2> /dev/null
    return 1
}
gadget a 1 2a2280000.usb configured
gadget b 3 2aa280000.usb "not attached"
gadget c 5 382280000.usb suspended
for s in "not attached" powered default addressed; do
    echo "$s" > "$T/sys/class/udc/2aa280000.usb/state"
    if waits ttyGS3 2; then ok "state '$s': waits, silently"; else bad "state '$s': did not wait silently ($(cat "$T/out"))"; fi
done
t0=$(date +%s)
if sh "$H" ttyGS1 > "$T/out" 2>&1 && [ ! -s "$T/out" ]; then ok "configured: returns at once"; else bad "configured: $(cat "$T/out")"; fi
if sh "$H" ttyGS5 > "$T/out" 2>&1; then ok "suspended: returns"; else bad "suspended: $(cat "$T/out")"; fi
[ $(( $(date +%s) - t0 )) -le 1 ] && ok "no delay when configured" || bad "configured took more than a second"
echo "not attached" > "$T/sys/class/udc/2aa280000.usb/state"
sh "$H" ttyGS3 > "$T/out" 2>&1 &
pid=$!
sleep 1.5
echo configured > "$T/sys/class/udc/2aa280000.usb/state"
for _ in 1 2 3 4 5; do kill -0 "$pid" 2> /dev/null || break; sleep 0.5; done
if kill -0 "$pid" 2> /dev/null; then kill "$pid"; bad "did not return after the host configured the port"
else wait "$pid"; rc=$?; [ "$rc" = 0 ] && ok "returns within ~1 s once a host configures the port" || bad "exit $rc after configuration"; fi
if sh "$H" ttyGS7 > "$T/out" 2>&1; then bad "a tty no gadget owns: exit 0"; else ok "a tty no gadget owns: fails ($(cat "$T/out"))"; fi
echo "not attached" > "$T/sys/class/udc/2aa280000.usb/state"
sh "$H" ttyGS3 > "$T/out" 2>&1 &
pid=$!
sleep 1.5
rm -rf "$T/sys/class/udc/2aa280000.usb"
for _ in 1 2 3 4 5; do kill -0 "$pid" 2> /dev/null || break; sleep 0.5; done
if kill -0 "$pid" 2> /dev/null; then kill "$pid"; bad "kept waiting for a UDC that is gone"
else wait "$pid"; rc=$?; [ "$rc" = 1 ] && ok "a UDC that goes away: fails ($(cat "$T/out"))" || bad "exit $rc when the UDC went away"; fi
[ "$fails" = 0 ] && echo "wait-usb-host: all PASS" || { echo "wait-usb-host: $fails FAIL"; exit 1; }

#!/bin/sh
# VM-only self-test of the boot039 bulk-only log port. Never shipped: it lives in the
# separate overlay cpio, and the packager refuses a Stage-B initramfs containing
# /etc/ilinux. In the test kernel, dummy_hcd makes the same kernel the gser gadget's
# USB host, and the host side's generic usb-serial driver (test kernel only) reads the
# kernel log from the bulk-IN endpoint, as the M1's reader will. boot039 has no USB
# network, so dropbear's key-only login is checked over loopback.
set -u
say() { echo "[selftest] $*"; }
fail() { say "FAIL: $*"; exit 1; }
KEY=/etc/ilinux/test-key

say "start: waiting for the gadget on the host side (dummy_hcd)"
dev=
i=0
while [ $i -lt 30 ] && [ -z "$dev" ]; do
    for d in /sys/bus/usb/devices/*; do
        [ -f "$d/idVendor" ] && [ "$(cat "$d/idVendor")" = 1d6b ] && [ "$(cat "$d/idProduct")" = 0104 ] && dev=$d
    done
    [ -n "$dev" ] || sleep 1
    i=$((i + 1))
done
[ -n "$dev" ] || fail "no 1d6b:0104 device on the host side after 30 s"
intf=$dev:1.0
say "host sees $(cat "$dev/idVendor"):$(cat "$dev/idProduct") bcdDevice $(cat "$dev/bcdDevice"), \"$(cat "$dev/product")\", configuration \"$(cat "$dev/configuration")\""
[ "$(cat "$dev/bcdDevice")" = 0139 ] || fail "bcdDevice is not 0139"
[ "$(cat "$dev/bDeviceClass")" = 00 ] || fail "device class is not 00 (interface-defined)"
[ "$(tr -d ' ' < "$dev/bNumInterfaces")" = 1 ] || fail "not exactly one interface"
[ "$(cat "$intf/bInterfaceClass")" = ff ] || fail "interface class is not vendor-specific (ff)"
[ "$(cat "$intf/bNumEndpoints")" = 02 ] || fail "interface does not have two endpoints"
bulk=$(cat "$intf"/ep_*/type | grep -c '^Bulk$')
[ "$bulk" = 2 ] || fail "the interface's endpoints are not two bulk endpoints: $(cat "$intf"/ep_*/type | tr '\n' ' ')"
grep -l Interrupt "$dev"/ep_*/type "$intf"/ep_*/type > /dev/null 2>&1 && fail "an interrupt endpoint exists"
say "descriptors: one vendor-specific interface (ff), two bulk endpoints ($(cd "$intf" && ls -d ep_* | tr '\n' ' ')), no interrupt endpoint"

# The host's generic usb-serial driver binds only to IDs it is given.
echo "1d6b 0104" > /sys/bus/usb-serial/drivers/generic/new_id || fail "give 1d6b:0104 to the generic usb-serial driver"
port=
i=0
while [ $i -lt 10 ] && [ -z "$port" ]; do
    port=$(cd "$intf" 2>/dev/null && ls -d ttyUSB* 2>/dev/null | head -1)
    [ -n "$port" ] || sleep 1
    i=$((i + 1))
done
[ -n "$port" ] || fail "the generic usb-serial driver did not bind the interface"
tty=/dev/$port
say "host side $tty (driver $(basename "$(readlink "$intf/driver")"))"
ls /dev/ttyACM* > /dev/null 2>&1 && fail "a host-side CDC-ACM port exists"
for d in /sys/class/net/*; do
    case "$(readlink "$d/device/driver" 2>/dev/null)" in
        */cdc_ether|*/cdc_eem|*/cdc_ncm) fail "a host-side CDC network interface exists: ${d##*/}" ;;
    esac
done
say "no CDC-ACM, ECM, EEM or NCM function on the host side"

# The log: what the M5 streams from boot on, read from the bulk-IN endpoint. One open
# serves stty and cat, so no data arrives between two opens and is dropped at a close;
# stty makes the host's own tty raw, so it does not echo the stream back. Subshells open
# the port: this shell leads its session and would make the tty its controlling terminal.
( stty raw -echo 2> /dev/null; timeout 8 cat ) < "$tty" > /tmp/log.txt || true
grep -q '\[ctl\]' /tmp/log.txt || fail "no kernel log over the bulk port $tty"
grep -q 'UDC dummy_udc.0 bound, GSER bulk-only' /tmp/log.txt || fail "the stream lacks the records from before the host opened it"
crlf=$(grep -c "$(printf '\r')\$" /tmp/log.txt)
double=$(grep -c "$(printf '\r\r')\$" /tmp/log.txt)
[ "$double" = 0 ] || fail "lines end in CR CR LF: the M5's port is not raw"
say "bulk log port: $(wc -l < /tmp/log.txt) lines received over $tty ($crlf end in CR LF); first: $(head -1 /tmp/log.txt | tr -d '\r' | cut -c1-80)"

# The M5's port is raw and its streamer never reads: a probe the host writes must not
# come back, and the stream must go on.
( printf 'ILINUX-ECHO-PROBE\r\n' ) > "$tty" || fail "write the echo probe"
( timeout 7 cat ) < "$tty" > /tmp/after.txt || true
grep -q ILINUX-ECHO-PROBE /tmp/after.txt && fail "the M5 side echoed host data back"
grep -q '\[diag\] heartbeat' /tmp/after.txt || fail "the stream stopped after the host wrote"
say "no echo: the host's probe did not come back; the stream went on ($(wc -l < /tmp/after.txt) more lines)"
say "UDC state $(cat /sys/class/udc/*/state 2> /dev/null | tr '\n' ' ')"
[ -d /sys/kernel/debug/usb ] || fail "debugfs is not mounted"
say "debugfs: /sys/kernel/debug/usb present (dummy_udc has no dwc3 directory)"

out=$(dbclient -y -i "$KEY" root@::1 'echo SSH-OK $(uname -r) $(hostname) uid=$(id -u)' 2>&1 < /dev/null)
say "ssh with the key over loopback: $out"
case "$out" in *SSH-OK*uid=0*) ;; *) fail "ssh with the key" ;; esac
out=$(dbclient -y root@::1 'echo SHOULD-NOT-RUN' 2>&1 < /dev/null)
case "$out" in *SHOULD-NOT-RUN*) fail "login without the key succeeded" ;; esac
say "login without the key refused: $(echo "$out" | tail -1)"
say "PASS"

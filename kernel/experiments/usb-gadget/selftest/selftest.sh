#!/bin/sh
# VM-only self-test of the boot036 control channel. Never shipped: it lives in the
# separate overlay cpio, and the packager refuses a Stage-B initramfs containing
# /etc/ilinux. In the test kernel, dummy_hcd makes the same kernel the EEM gadget's
# USB host: the host-side cdc_eem interface moves into its own network namespace,
# so ping and SSH really cross the (virtual) USB link to the gadget's dropbear.
set -u
say() { echo "[selftest] $*"; }
fail() { say "FAIL: $*"; exit 1; }
KEY=/etc/ilinux/test-key
LL=fe80::69:6cff:fe69:6e04      # port 4: the first UDC that is not one of the M5's dwc3 cores

say "start: waiting for the host-side cdc_eem interface"
host_if=
i=0
while [ $i -lt 30 ] && [ -z "$host_if" ]; do
    for d in /sys/class/net/*; do
        case "$(readlink "$d/device/driver" 2>/dev/null)" in */cdc_eem) host_if=${d##*/} ;; esac
    done
    [ -n "$host_if" ] || sleep 1
    i=$((i + 1))
done
[ -n "$host_if" ] || fail "no cdc_eem host interface after 30 s"
say "host side $host_if (cdc_eem); gadget side $(cat /sys/kernel/config/usb_gadget/g4/functions/eem.usb/ifname 2>/dev/null)"
say "UDC state $(cat /sys/class/udc/*/state 2>/dev/null | tr '\n' ' ')"

unshare --net sleep 600 &
ns=$!
sleep 1
ip link set "$host_if" netns "$ns" || fail "move $host_if into a network namespace"
in_ns() { nsenter --target "$ns" --net "$@"; }
in_ns ip link set lo up
in_ns ip link set "$host_if" up || fail "bring $host_if up"

i=0
until in_ns ping -6 -c 1 -W 1 "$LL%$host_if" > /dev/null 2>&1; do
    i=$((i + 1))
    [ $i -lt 30 ] || fail "no ping reply from $LL within 30 s"
    sleep 1
done
in_ns ping -6 -c 3 "$LL%$host_if" || fail "ping"

out=$(in_ns dbclient -y -i "$KEY" "root@$LL%$host_if" 'echo SSH-OK $(uname -r) $(hostname) uid=$(id -u)' 2>&1 < /dev/null)
say "ssh with the key: $out"
case "$out" in *SSH-OK*uid=0*) ;; *) fail "ssh with the key" ;; esac

out=$(in_ns dbclient -y "root@$LL%$host_if" 'echo SHOULD-NOT-RUN' 2>&1 < /dev/null)
case "$out" in *SHOULD-NOT-RUN*) fail "login without the key succeeded" ;; esac
say "login without the key refused: $(echo "$out" | tail -1)"

dd if=/dev/urandom of=/tmp/blob bs=65536 count=128 2> /dev/null
t0=$(date +%s)
in_ns dbclient -y -i "$KEY" "root@$LL%$host_if" 'cat > /tmp/blob.copy' < /tmp/blob || fail "copy over ssh"
t1=$(date +%s)
cmp /tmp/blob /tmp/blob.copy || fail "8 MiB copy differs"
say "8 MiB through ssh intact in $((t1 - t0)) s (virtual link; not a speed measurement)"

kill "$ns"
say "PASS"

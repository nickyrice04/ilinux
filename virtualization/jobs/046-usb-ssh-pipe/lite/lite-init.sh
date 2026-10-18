#!/bin/sh
# Job 046 "lite" self-test, PID 1 in a busybox initramfs (job 041's Stage-B initramfs and its
# dbclient overlay). No systemd and no OpenSSH: dropbear stands in for sshd. What it still runs for
# real: the RAM root's usb-gadget.sh (two gser functions, the raw ttyGS port, the sshd branch with
# its input drain), the kernel's gadget and dummy_hcd host side, the generic usb-serial driver, and the
# static Linux build of tools/m1n1-client/usb-pipe as dbclient's -J command, with its banner sync.
export PATH=/usr/bin:/usr/sbin:/bin:/sbin
say() { echo "[lite] $*"; }
fail() {
    say "FAIL: $*"
    echo "--- usb-pipe log"; tail -20 /tmp/usb-pipe.log 2> /dev/null
    echo "--- sshd loop"; tail -20 /tmp/sshd-loop.log 2> /dev/null; echo "--- dropbear"; tail -20 /tmp/dropbear.log 2> /dev/null
    say "END"
    exec sleep 100000
}
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev 2> /dev/null
mkdir -p /dev/pts /tmp
mount -t devpts devpts /dev/pts 2> /dev/null
mount -t tmpfs tmpfs /tmp
mount -t configfs configfs /sys/kernel/config
say "start: $(uname -r)"

timeout 0.05 sleep 1 2> /tmp/timeout.err; say "busybox timeout 0.05 (for the record): exit $? $(cat /tmp/timeout.err)"
udc=$(ls /sys/class/udc | head -1)
[ -n "$udc" ] || fail "no UDC"
/usr/local/lib/ilinux/usb-gadget.sh start "$udc" || fail "usb-gadget.sh start failed"
G=/sys/kernel/config/usb_gadget/ilinux-$(printf '%s' "$udc" | tr -c 'A-Za-z0-9' '_')
[ "$(cat "$G/bcdDevice")" = 0x0039 ] || fail "bcdDevice $(cat "$G/bcdDevice")"
log_port=$(cat "$G/functions/gser.log/port_num")
ssh_port=$(cat "$G/functions/gser.ssh/port_num")
for _ in $(seq 30); do [ "$(cat /sys/class/udc/$udc/state)" = configured ] && break; sleep 1; done
say "M5 side: gadget bound to $udc, UDC $(cat /sys/class/udc/$udc/state), gser.log on ttyGS$log_port, gser.ssh on ttyGS$ssh_port, configuration \"$(cat $G/configs/c.1/strings/0x409/configuration)\""

# The sshd stand-in: dropbear as a daemon on loopback (the bridge in /usr/bin/sshd connects to it).
ifconfig lo 127.0.0.1 up
/usr/bin/dropbear -R -E -s -j -k -F -p 127.0.0.1:2222 > /tmp/dropbear.log 2>&1 &
# What systemd does with ilinux-sshd-tty@.service: Restart=always, RestartSec=100ms.
( while :; do /usr/local/lib/ilinux/usb-gadget.sh sshd "ttyGS$ssh_port"; sleep 0.1; done ) > /tmp/sshd-loop.log 2>&1 &

dev=
for _ in $(seq 30); do
    for d in /sys/bus/usb/devices/*; do
        [ -f "$d/idVendor" ] && [ "$(cat "$d/idVendor")" = 1d6b ] && [ "$(cat "$d/idProduct")" = 0104 ] && dev=$d
    done
    [ -n "$dev" ] && break
    sleep 1
done
[ -n "$dev" ] || fail "no 1d6b:0104 device on the host side"
[ "$(cat "$dev/bcdDevice")" = 0039 ] || fail "host bcdDevice $(cat "$dev/bcdDevice")"
for n in 0 1; do
    [ "$(cat "$dev:1.$n/bInterfaceClass")" = ff ] || fail "interface $n is not class ff"
    [ "$(cat "$dev:1.$n"/ep_*/type | grep -c '^Bulk$')" = 2 ] || fail "interface $n: not two bulk endpoints"
done
say "host sees 1d6b:0104 bcdDevice 0039 \"$(cat "$dev/product")\": $(cat "$dev/configuration"); two vendor interfaces, bulk only"
echo "1d6b 0104" > /sys/bus/usb-serial/drivers/generic/new_id
for _ in $(seq 15); do
    tty_ssh=$(cd "$dev:1.1" 2> /dev/null && ls -d ttyUSB* 2> /dev/null | head -1)
    [ -n "$tty_ssh" ] && break
    sleep 1
done
[ -n "$tty_ssh" ] || fail "no host-side serial port for interface 1"
say "host side: interface 1 -> /dev/$tty_ssh"

KEY=/etc/ilinux/test-key
# OpenSSH's sshd -i ends by itself when the session ends (the pipe carries no hang-up); dropbear's
# server does not end its connection after a command, so the stand-in is told: the bridge is killed
# after each session, which ends the "sshd" the gadget script started, and the loop starts the next one.
# (That sshd -i really exits at the end of a session is what the full test with OpenSSH shows.)
# lite.kill=now on the kernel command line kills the bridge the moment dbclient returns, which ends the server
# before the client's last packets are in: the harshest case for the M5's input drain.
if grep -q 'lite.kill=now' /proc/cmdline; then SERVER_WAIT=0; else SERVER_WAIT=0.3; fi
endsession() { [ "$SERVER_WAIT" = 0 ] || sleep "$SERVER_WAIT"; kill $(pidof nc) 2> /dev/null; sleep 0.5; }
ssh() {  # ssh COMMAND: dbclient with usb-pipe as the -J command, as ssh's ProxyCommand on the M1
    dbclient -T -y -i "$KEY" -J "/usr/local/bin/usb-pipe --tty /dev/$tty_ssh --banner-wait 20 --log /tmp/usb-pipe.log" root@m5 "$@"
    rc=$?
    sleep 0.3
    left=$(pidof usb-pipe 2> /dev/null)
    [ -z "$left" ] || echo "[lite] note: usb-pipe still running 0.3 s after dbclient: pid $left ($(tr '\0' ' ' < /proc/${left%% *}/cmdline 2> /dev/null | cut -c1-60); stdin $(readlink /proc/${left%% *}/fd/0 2> /dev/null))" >&2
    endsession
    return $rc
}
t0=$(date +%s)
out=$(ssh 'echo SSH-OK uid=$(id -u) $(uname -r)' 2> /tmp/ssh1.err) || fail "first session failed: $(tail -3 /tmp/ssh1.err | tr '\n' ' ')"
say "session 1 ($(( $(date +%s) - t0 )) s): $out"
case "$out" in *SSH-OK*uid=0*) ;; *) fail "session 1 output" ;; esac
grep -q 'banner after' /tmp/usb-pipe.log || fail "no banner line in the usb-pipe log"
say "usb-pipe: $(grep 'banner after' /tmp/usb-pipe.log | tail -1 | cut -d' ' -f2-)"

# Sessions in a row: sshd ends after each, the loop starts the next one, the tool drops what is stale.
for i in 2 3 4 5 6 7; do
    out=$(ssh "echo SESSION-$i-OK" 2> /tmp/ssh$i.err) || fail "session $i failed: $(tail -3 /tmp/ssh$i.err | tr '\n' ' ')"
    [ "$out" = "SESSION-$i-OK" ] || fail "session $i output: $out"
done
say "sessions 2 to 7 in a row: ok"

# 2 MiB each way. The two sides share /tmp here, so the names differ.
head -c 2097152 /dev/urandom > /tmp/up.bin
t1=$(date +%s)
remote=$(ssh 'cat > /tmp/m5-up.bin; sha256sum /tmp/m5-up.bin' < /tmp/up.bin 2> /tmp/ssh-up.err | cut -d' ' -f1) || fail "upload failed: $(tail -3 /tmp/ssh-up.err | tr '\n' ' ')"
local_sum=$(sha256sum /tmp/up.bin | cut -d' ' -f1)
[ "$remote" = "$local_sum" ] || fail "2 MiB upload digest mismatch ($remote / $local_sum)"
t2=$(date +%s)
ssh 'head -c 2097152 /dev/urandom > /tmp/m5-down.bin; cat /tmp/m5-down.bin' > /tmp/m1-down.bin 2> /tmp/ssh-down.err || fail "download failed: $(tail -3 /tmp/ssh-down.err | tr '\n' ' ')"
remote=$(ssh 'sha256sum /tmp/m5-down.bin' 2> /dev/null | cut -d' ' -f1)
local_sum=$(sha256sum /tmp/m1-down.bin | cut -d' ' -f1)
[ -n "$remote" ] && [ "$remote" = "$local_sum" ] || fail "2 MiB download digest mismatch ($remote / $local_sum)"
t3=$(date +%s)
say "transfer: 2 MiB up in $((t2 - t1)) s and 2 MiB down in $((t3 - t2)) s, digests equal (dummy_hcd, no real USB timing)"

# A key the server does not know is refused.
if dbclient -T -y -i /etc/ilinux/no-such-key -J "/usr/local/bin/usb-pipe --tty /dev/$tty_ssh --banner-wait 20 --log /tmp/usb-pipe.log" root@m5 'echo SHOULD-NOT-RUN' > /tmp/nokey.out 2>&1; then
    grep -q SHOULD-NOT-RUN /tmp/nokey.out && fail "a missing key ran a command"
fi
endsession
say "login without a usable key: $(tail -1 /tmp/nokey.out | cut -c1-70)"
out=$(ssh 'echo STILL-FINE' 2> /dev/null) || fail "session after the refused login failed"
say "session after the refused login: $out"

# What the tool saw: one banner line per session, and how many stale bytes it dropped before each.
say "usb-pipe sessions: $(grep -c 'banner after' /tmp/usb-pipe.log); stale bytes dropped before the banners: $(grep -o '([0-9]* stale' /tmp/usb-pipe.log | tr -d '(' | cut -d' ' -f1 | tr '\n' ' ')"
say "dropbear connections: $(grep -c 'Child connection' /tmp/dropbear.log)"
say "PASS at $(( $(date +%s) - t0 )) s"
say "END"
exec sleep 100000

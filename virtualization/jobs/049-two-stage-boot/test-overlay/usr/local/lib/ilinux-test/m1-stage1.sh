#!/bin/bash
# VM test only (job 049, appended by run-qemu.sh, never in the delivered stage one): the M1's part
# against stage one, the way job 046 tests the link: dummy_hcd makes this kernel the host of its own
# gadget, so one boot holds both computers.
#  * The M5 is stage one as built: udev starts ilinux-usb-gadget@dummy_udc.0 (gser.log, gser.ssh),
#    ilinux-ssh-hostkey makes this boot's key, ilinux-sshd-tty@ttyGS1 runs sshd -i on the pipe, the
#    panel shows the state.
#  * The M1 is this script, with the M1's own files from the working tree: tools/m1n1-client/m5-stage2.py,
#    m5-ssh-config (host m5s, unchanged), native/boot/omarchy-root-manifest.json, the Linux usb-pipe as
#    the ProxyCommand on the host's usb-serial port of interface 1, and stage two read from a virtio disk
#    (the M1 keeps it in build/).
# Order: the link; three attempts stage one must refuse and survive (an image it is not pinned to, a
# session that ends after 64 MiB, the right size with one byte changed: the SHA-256 check), each with
# its reason in the journal, on the panel (a capture) and in the session; then m5-stage2.py with the
# real image, which ends in the switch. "ILINUX049-..." console markers; files on the results share.
set -u
T=/usr/local/lib/ilinux-test
. "$T/common.sh"
LOGNAME_049=m1-stage1
KEYS=$T/keys
USBPIPE=$T/usb-pipe
M1=$T/m1
D=/run/ilinux049/m1data
results
fail() { mark FAIL "$*"; say "FAIL: $*"; journalctl -b --no-pager -o short-monotonic > "$RES/stage1-journal-at-fail.txt" 2>&1; exit 1; }
mark M1-START "$(uname -r); stage one $(sed -n 1p /usr/share/ilinux/build-info.txt)"

# ---- the M5 side ---------------------------------------------------------------------------------------
gadget_up || fail "stage one's gadget or sshd did not come up: $(systemctl --failed --no-legend | tr '\n' ' ')"
[ "$(cat "$GADGET/bcdDevice")" = 0x0039 ] || fail "bcdDevice $(cat "$GADGET/bcdDevice")"
[ -n "$HOSTFP" ] || fail "no host key fingerprint in the journal"
mark LINK-UP "udc $UDC $(cat "/sys/class/udc/$UDC/state"); $SSH_UNIT active; host key $HOSTFP (this boot)"

# ---- the M1 side: the device as the host sees it ---------------------------------------------------------
usb_device || fail "the host side does not see the gadget's two ports"
[ "$(cat "$DEV/bcdDevice")" = 0039 ] || fail "host sees bcdDevice $(cat "$DEV/bcdDevice")"
raw_pipe
mark HOST-SIDE "$(cat "$DEV/product"); interface 0 /dev/$TTY_LOG, interface 1 /dev/$TTY_SSH"
# the bulk-log reader's stand-in: interface 0's journal, for as long as stage one lives
( stty raw -echo 2> /dev/null; exec cat ) < "/dev/$TTY_LOG" > "$RES/stage1-interface0.log" 2> /dev/null &
mkdir -p "$D"
mountpoint -q "$D" || mount -t tmpfs -o size=6G,mode=0700 ilinux049-m1 "$D"
m1_tree "$M1"
rm -f "$M1/build/control/known_hosts-stage1"
SSH=(ssh -F "$M1/tools/m1n1-client/m5-ssh-config" -o BatchMode=yes)
read -r SIZE SHA < <(python3 -I -c 'import json, sys; r = json.load(open(sys.argv[1])); print(r["size"], r["sha256"])' \
    "$M1/native/boot/omarchy-root-manifest.json")
t1=$(up)
head -c "$SIZE" /dev/vda > "$D/ramroot.cpio.zst"
[ "$(sha256sum < "$D/ramroot.cpio.zst" | cut -d' ' -f1)" = "$SHA" ] || fail "the virtio disk does not hold the pinned image"
mark IMAGE-READY "$SIZE bytes from the virtio disk in $(awk -v a="$t1" -v b="$(up)" 'BEGIN { printf "%.1f", b - a }') s, SHA-256 equal to the manifest"

# check_after NAME KIND REASON: after a failed attempt, stage one waits again, the panel's last outcome is
# "KIND: ...REASON..." (KIND REFUSED or FAILED), the journal has REASON, nothing is left mounted
check_after() {
    local name=$1 kind=$2 want=$3 last phase
    sleep 2
    last=$(cut -d' ' -f2- /run/ilinux-stage2/last 2> /dev/null)
    phase=$(sed -n 's/^phase=//p' /run/ilinux-stage2/state 2> /dev/null)
    case $last in "$kind: "*"$want"*) ;; *) fail "$name: the panel's reason is '$last', expected '$kind: ...$want'" ;; esac
    journalctl -b -t ilinux-stage2 -o cat --no-pager | grep -q -F "$want" || fail "$name: the journal lacks '$want'"
    [ "${phase:-waiting}" = waiting ] || fail "$name: stage one is in phase '$phase', not waiting"
    mountpoint -q /run/ilinux-stage2/incoming && fail "$name: the incoming tmpfs is still mounted"
    mountpoint -q /run/nextroot && fail "$name: /run/nextroot is still mounted"
    systemctl is-active -q "$SSH_UNIT" || sleep 2
    mark "SHOT" "$name"
    sleep 3
}

# Stage one authorizes the operator's key for root and omarchy in root-owned 0644 files (job 039's fix:
# sshd reads the file as the user who logs in); the test overlay put the VM key in omarchy's the same way.
out=$(cd "$M1" && "${SSH[@]}" -o User=omarchy m5s 'id -un; stat -c "%U:%G %a" /etc/ssh/authorized_keys.d/omarchy' 2> "$RES/stage1-omarchy.err" | tr '\n' ' ')
case $out in "omarchy root:root 644 ") ;; *) fail "ssh as omarchy on stage one: '$out' $(tail -2 "$RES/stage1-omarchy.err" | tr '\n' ' ')" ;; esac
mark STAGE1-OMARCHY "ssh as omarchy: omarchy, /etc/ssh/authorized_keys.d/omarchy root:root 644"

# The timing run (run-qemu.sh with NEGATIVES=0) sends the real image as soon as the link is up.
negatives=1
grep -q 'ilinux049.negatives=0' /proc/cmdline && negatives=0
if [ "$negatives" = 1 ]; then
# ---- 1. an image stage one is not pinned to: refused before a byte is sent ---------------------------------
# A small stand-in "other image" with its own manifest: the tool's local check passes, its offer does not.
head -c 1048576 "$D/ramroot.cpio.zst" > "$D/other.zst"
python3 -I -c 'import hashlib, json, sys; d = open(sys.argv[1], "rb").read()
json.dump({"size": len(d), "sha256": hashlib.sha256(d).hexdigest()}, open(sys.argv[2], "w"))' "$D/other.zst" "$D/other.json"
t1=$(up)
python3 -I "$M1/tools/m1n1-client/m5-stage2.py" --image "$D/other.zst" --manifest "$D/other.json" > "$RES/neg1-other-image.log" 2>&1
rc=$?
[ "$rc" = 1 ] || fail "neg 1 (other image): m5-stage2.py exit $rc, expected 1: $(tail -3 "$RES/neg1-other-image.log" | tr '\n' ' ')"
grep -q 'stage one refused: the M1 offers 1,048,576 bytes' "$RES/neg1-other-image.log" || fail "neg 1: no refusal line"
grep -q 'sent all\|sending' "$RES/neg1-other-image.log" && fail "neg 1: the tool sent data after a refusal"
check_after neg1-other-image REFUSED "the M1 offers 1,048,576 bytes"
mark NEG-OTHER-IMAGE "exit $rc in $(awk -v a="$t1" -v b="$(up)" 'BEGIN { printf "%.1f", b - a }') s: $(grep -o 'stage one refused: .*' "$RES/neg1-other-image.log" | cut -c1-160)"

# ---- 2. the session ends after 64 MiB: a short transfer ---------------------------------------------------------
t1=$(up)
head -c 67108864 "$D/ramroot.cpio.zst" | (cd "$M1" && "${SSH[@]}" m5s /usr/local/lib/ilinux/ilinux-stage2 receive "$SIZE" "$SHA") \
    > "$RES/neg2-short.log" 2> "$RES/neg2-short.err"
rc=$?
[ "$rc" = 4 ] || fail "neg 2 (short): exit $rc, expected 4: $(tail -3 "$RES/neg2-short.log" "$RES/neg2-short.err" | tr '\n' ' ')"
grep -q 'failed: the transfer ended after 67,108,864 of' "$RES/neg2-short.log" || fail "neg 2: no short-transfer line"
check_after neg2-short FAILED "the transfer ended after 67,108,864 of"
mark NEG-SHORT "exit $rc in $(awk -v a="$t1" -v b="$(up)" 'BEGIN { printf "%.1f", b - a }') s: $(grep -o 'failed: .*' "$RES/neg2-short.log" | cut -c1-160)"

# ---- 3. the pinned size with one byte changed: stage one's SHA-256 check (a whole transfer) ------------------
cp "$D/ramroot.cpio.zst" "$D/corrupt.zst"
printf '\xff' | dd of="$D/corrupt.zst" bs=1 seek=$((SIZE / 2)) conv=notrunc status=none
cmp -s "$D/ramroot.cpio.zst" "$D/corrupt.zst" && printf '\x00' | dd of="$D/corrupt.zst" bs=1 seek=$((SIZE / 2)) conv=notrunc status=none
t1=$(up)
(cd "$M1" && "${SSH[@]}" m5s /usr/local/lib/ilinux/ilinux-stage2 receive "$SIZE" "$SHA") < "$D/corrupt.zst" \
    > "$RES/neg3-corrupt.log" 2> "$RES/neg3-corrupt.err"
rc=$?
rm -f "$D/corrupt.zst"
[ "$rc" = 4 ] || fail "neg 3 (corrupt): exit $rc, expected 4: $(tail -3 "$RES/neg3-corrupt.log" "$RES/neg3-corrupt.err" | tr '\n' ' ')"
grep -q 'failed: SHA-256 [0-9a-f]* of the received image differs from the pin' "$RES/neg3-corrupt.log" || fail "neg 3: no SHA-256 line"
check_after neg3-corrupt FAILED "of the received image differs from the pin $SHA"
mark NEG-CORRUPT "exit $rc in $(awk -v a="$t1" -v b="$(up)" 'BEGIN { printf "%.1f", b - a }') s; $(grep -o 'received [0-9]* bytes in .*' "$RES/neg3-corrupt.log")"

fi

# ---- 4. the real image with the M1's tool: verified, unpacked, switched ---------------------------------------------
( sleep 40; mark SHOT receiving ) &
shotpid=$!
t1=$(up)
mark M1-SEND "python3 -I tools/m1n1-client/m5-stage2.py --image (stage two)"
python3 -I "$M1/tools/m1n1-client/m5-stage2.py" --image "$D/ramroot.cpio.zst" > "$RES/m5-stage2.log" 2>&1
rc=$?
kill "$shotpid" 2> /dev/null
grep -E 'm5-stage2: (stage one: |PASS|sent all|image PASS)' "$RES/m5-stage2.log" | while read -r l; do mark M1-SAYS "$l"; done
[ "$rc" = 0 ] || fail "m5-stage2.py exit $rc: $(tail -4 "$RES/m5-stage2.log" | tr '\n' ' ')"
mark M1-SENT "exit 0 after $(awk -v a="$t1" -v b="$(up)" 'BEGIN { printf "%.1f", b - a }') s"
# stage one now stops its units and soft-reboots into stage two; this process ends with it

#!/bin/bash
# VM test only (job 049; the test hook adds it to the unpacked stage two before the switch): stage two
# after the soft-reboot. Records what the system is (the pinned image's build-info, the root mount, the
# soft-reboot count), follows Omarchy's boot to the desktop with job 045's definition of ready (the shell
# answers its IPC ping and Hyprland has mapped layer surfaces), asks for a capture, then plays the M1
# against stage two's own link as attempt 25's M1 used it: the journal on interface 0 up to this boot's
# host key, and SSH as omarchy on the byte pipe with m5-ssh-config's m5o entry and the Linux usb-pipe.
# Last, one journal for both stages (stage one's records stay in /run across the soft-reboot) and the
# failed units. "ILINUX049-..." console markers; files on the results share.
set -u
D=/usr/local/lib/ilinux049
. "$D/common.sh"
LOGNAME_049=stage2
KEYS=$D/keys
USBPIPE=$D/usb-pipe
M1=$D/m1
results
fail() {
    mark FAIL "stage two: $*"
    journalctl -b -o short-monotonic --no-pager > "$RES/journal.txt" 2>&1
    systemctl --failed --no-pager > "$RES/failed-units.txt" 2>&1
    mark DONE "failed"
    exit 1
}
mark S2-START "$(uname -n); root $(findmnt -n -o SOURCE,FSTYPE /); soft-reboots $(systemctl show -p SoftRebootsCount --value 2> /dev/null); $(tr '\n' ' ' < /usr/share/ilinux/build-info.txt)"
{ cat /usr/share/ilinux/build-info.txt; findmnt -n -o SOURCE,FSTYPE,SIZE,USED,OPTIONS /; cat /proc/cmdline
  systemctl show -p SoftRebootsCount -p UserspaceTimestampMonotonic -p FinishTimestampMonotonic; } > "$RES/stage2-identity.txt" 2>&1

# ---- boot to the desktop ---------------------------------------------------------------------------------
U=omarchy
uid=$(id -u "$U")
RUN=/run/user/$uid
sig() { local d; d=$(ls -td "$RUN"/hypr/*/ 2> /dev/null | head -1); d=${d%/}; echo "${d##*/}"; }
wl() { local s; s=$(ls -t "$RUN"/wayland-[0-9]* 2> /dev/null | grep -v '\.lock$' | head -1); echo "${s##*/}"; }
as_user() {
    setpriv --reuid="$uid" --regid="$(id -g "$U")" --init-groups env -i HOME=/home/$U USER=$U \
        LOGNAME=$U XDG_RUNTIME_DIR="$RUN" DBUS_SESSION_BUS_ADDRESS=unix:path=$RUN/bus \
        WAYLAND_DISPLAY="$(wl)" HYPRLAND_INSTANCE_SIGNATURE="$(sig)" OMARCHY_PATH=/usr/share/omarchy \
        PATH=/home/$U/.local/bin:/usr/share/omarchy/bin:/usr/local/bin:/usr/bin LANG=en_US.UTF-8 "$@"
}
declare -A seen=()
once() { [ -n "${seen[$1]:-}" ] && return 1; seen[$1]=1; mark "$1" "${2:-}"; }
ready= layers=
deadline=$((SECONDS + 1200))
while [ "$SECONDS" -lt "$deadline" ]; do
    pgrep -x sddm > /dev/null && once SDDM
    loginctl list-sessions --no-legend 2> /dev/null | grep -q " $U " && once SESSION
    pgrep -u "$uid" -x Hyprland > /dev/null && once HYPRLAND
    pgrep -u "$uid" -x quickshell > /dev/null && once SHELL-PROCESS
    if [ -n "${seen[SHELL-PROCESS]:-}" ] && [ -n "$(sig)" ]; then
        [ -n "${seen[SHELL-PING]:-}" ] ||
            { as_user env OMARCHY_SHELL_IPC_TIMEOUT=10s timeout 15 omarchy-shell shell ping > /dev/null 2>&1 && once SHELL-PING; }
        layers=$(as_user timeout 15 hyprctl -j layers 2> /dev/null | grep -o '"namespace": "[^"]*"' | cut -d'"' -f4 | sort -u | tr '\n' ' ')
    fi
    if [ -n "${seen[SHELL-PING]:-}" ] && [ -n "$layers" ]; then ready=1; mark READY "layers: $layers"; break; fi
    sleep 1
done
[ -n "$ready" ] || fail "no desktop within 1200 s (seen: ${!seen[*]})"
sleep 20
mark SHOT desktop
sleep 5

# ---- stage two's link, as the M1 uses it after the switch ---------------------------------------------------
gadget_up || fail "stage two's gadget or sshd did not come up: $(systemctl --failed --no-legend | tr '\n' ' ')"
usb_device || fail "the host side does not see stage two's gadget"
raw_pipe
( stty raw -echo 2> /dev/null; exec timeout 300 cat ) < "/dev/$TTY_LOG" > "$RES/stage2-interface0.log" 2> /dev/null &
lpid=$!
for _ in $(seq 300); do grep -a -q -F "$HOSTFP" "$RES/stage2-interface0.log" 2> /dev/null && break; sleep 1; done
grep -a -q -F "$HOSTFP" "$RES/stage2-interface0.log" || fail "this boot's host key $HOSTFP is not in the journal on interface 0"
kill "$lpid" 2> /dev/null
s1=$(grep -a -c 'ilinux-stage2' "$RES/stage2-interface0.log")
mark LINK2-UP "udc $UDC; $SSH_UNIT; host key $HOSTFP in the journal on interface 0 ($(wc -l < "$RES/stage2-interface0.log") lines, $s1 of them stage one's ilinux-stage2)"
# the VM key for omarchy, test only (the image's own file holds the operator's key, root-owned 0644)
install -d -m 0700 -o "$uid" -g "$(id -g "$U")" /home/$U/.ssh
install -m 0600 -o "$uid" -g "$(id -g "$U")" "$KEYS/id_ed25519.pub" /home/$U/.ssh/authorized_keys
m1_tree "$M1"
rm -f "$M1/build/control/known_hosts-omarchy"
t1=$(up)
(cd "$M1" && timeout 300 ssh -F tools/m1n1-client/m5-ssh-config -o BatchMode=yes m5o \
    'echo "SSH-OK $(id -un)@$(uname -n) sudo-uid=$(sudo -n id -u 2>&1); root $(findmnt -n -o SOURCE,FSTYPE /); soft-reboots $(systemctl show -p SoftRebootsCount --value); $(sed -n 1p /usr/share/ilinux/build-info.txt), $(sed -n "s/^options //p" /usr/share/ilinux/build-info.txt | sed "s/^/options /")"') \
    > "$RES/stage2-ssh.txt" 2> "$RES/stage2-ssh.err"
rc=$?
[ "$rc" = 0 ] || fail "ssh m5o exit $rc: $(tail -3 "$RES/stage2-ssh.err" | tr '\n' ' ')"
grep -q '^SSH-OK omarchy@omarchy sudo-uid=0; ' "$RES/stage2-ssh.txt" || fail "unexpected session: $(head -1 "$RES/stage2-ssh.txt")"
knownfp=$(ssh-keygen -l -f "$M1/build/control/known_hosts-omarchy" | awk '{print $2}' | head -1)
[ "$knownfp" = "$HOSTFP" ] || fail "ssh recorded $knownfp, the journal says $HOSTFP"
mark LINK2 "ssh m5o in $(awk -v a="$t1" -v b="$(up)" 'BEGIN { printf "%.1f", b - a }') s: $(head -1 "$RES/stage2-ssh.txt")"

# The new root's fixes must survive the soft-reboot, not merely a direct boot.
# These are read-only checks. The VM has no Apple MTP controller.
as_user timeout 20 hyprctl -j getoption input:repeat_delay > "$RES/repeat-delay.json" ||
    fail "cannot query the effective repeat delay after the switch"
python3 -I -c 'import json,sys; assert json.load(open(sys.argv[1]))["int"] == 1000' "$RES/repeat-delay.json" ||
    fail "repeat delay is not 1000 after the switch"
as_user env OMARCHY_SHELL_IPC_TIMEOUT=20s timeout 25 omarchy-shell shell listShellConfig \
    > "$RES/shell-config.json" 2> "$RES/shell-config.err" ||
    fail "cannot query the effective shell configuration after the switch"
python3 -I -c 'import json,sys
c=json.load(open(sys.argv[1])); assert c["version"] == 1
layout=c["bar"]["layout"]; assert isinstance(layout,dict) and layout
assert "omarchy.weather" not in [e["id"] for entries in layout.values() for e in entries]' "$RES/shell-config.json" ||
    fail "runtime weather configuration is invalid or still enabled after the switch"
[ "$(systemctl is-enabled ilinux-keyboard.service)" = enabled ] ||
    fail "keyboard service is not enabled in stage two"
[ "$(systemctl show -p ConditionResult --value ilinux-keyboard.service)" = no ] &&
    [ "$(systemctl show -p ActiveState --value ilinux-keyboard.service)" = inactive ] ||
    fail "keyboard service did not skip the VM's absent MTP"
[ "$(cat /sys/devices/system/cpu/online)" = 0 ] || fail "expected one online CPU"
mark IMAGE-FIXES "repeat_delay=1000; runtime weather absent; keyboard enabled and skipped without MTP; online CPU 0"

# Optional attempt-28 payload: validate the shipped assets and exercise its
# refusal on virtual hardware. Never pretend this VM has Apple DVFS registers.
if [ -d /usr/local/lib/ilinux-cpu28 ]; then
    python3 -I - > "$RES/cpu28-assets.txt" 2>&1 <<'PY'
import importlib.util, struct
from pathlib import Path
p = Path('/usr/local/lib/ilinux-cpu28/observe28.py')
s = importlib.util.spec_from_file_location('observe28', p)
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
assert m.verify_assets()['frequency_writes'] is False
try:
    m.identity()
except (OSError, ValueError):
    pass
except struct.error:
    # QEMU's synthetic CPU reg uses one cell; the pinned t6050 tree uses two.
    # This is a refusal before any module load, though the native CLI currently
    # reports this malformed/non-native layout as a traceback rather than JSON.
    assert len(Path('/sys/devices/system/cpu/cpu0/of_node/reg').read_bytes()) == 4
else:
    raise AssertionError('virtual hardware passed the native identity gate')
assert not Path('/sys/module/apple_soc_cpufreq').exists()
print('assets verified; virtual hardware refused before module load')
PY
    [ "$?" = 0 ] || fail "CPU observation asset/virtual-hardware refusal check"
    mark CPU28-ASSETS "verified; virtual hardware refused; no module load or DVFS writes"
fi

# ---- the record ------------------------------------------------------------------------------------------------
journalctl -b -o short-monotonic --no-pager > "$RES/journal.txt" 2>&1
systemctl --failed --no-pager --plain > "$RES/failed-units.txt" 2>&1
free -m > "$RES/free.txt"
grep -E 'ilinux-stage2|Soft-reboot|soft-reboot|Startup finished|Reached target Graphical|sddm.*selected|uwsm|ilinux-ssh-hostkey|usb-gadget.sh' \
    "$RES/journal.txt" | cut -c1-240 > "$RES/journal-timeline.txt"
mark FAILED-UNITS "$(systemctl --failed --no-legend --plain | awk '{print $1}' | tr '\n' ' ')"
mark MEMORY "$(awk '/MemTotal/ {t=$2} /MemAvailable/ {a=$2} END {printf "used_mib=%d", (t - a) / 1024}' /proc/meminfo)"
mark DONE "pass"

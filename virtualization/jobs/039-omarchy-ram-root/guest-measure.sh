#!/bin/bash
# Runs as root inside the RAM-root guest (ssh ... bash -s < guest-measure.sh) once the
# desktop is up. Prints "=== name" sections that summarize.py parses.
sec() { echo "=== $1"; }
hypr() {
    local sig
    sig=$(ls -t /run/user/1000/hypr 2>/dev/null | head -1)   # newest: the running instance
    setpriv --reuid=1000 --regid=1000 --init-groups \
        env XDG_RUNTIME_DIR=/run/user/1000 HYPRLAND_INSTANCE_SIGNATURE="$sig" hyprctl "$@"
}
proc_cpu() {  # utime+stime ticks of each process whose name matches $1
    for p in /proc/[0-9]*; do
        [ "$(cat "$p/comm" 2>/dev/null)" = "$1" ] || continue
        awk '{print $14 + $15}' "$p/stat" 2>/dev/null
    done | awk '{s += $1} END {print s + 0}'
}

sec uname; uname -a
sec pagesize; getconf PAGESIZE
sec nproc; nproc
sec cmdline; cat /proc/cmdline
sec desktop-ready; cat /run/ilinux/desktop-ready
sec session-start  # Hyprland under start-hyprland, its watchdog (without it, a 15 s notice on screen)
pgrep -a -x start-hyprland || echo "no start-hyprland process"
for p in $(pidof Hyprland); do
    pp=$(awk '/^PPid:/ {print $2}' /proc/$p/status)
    echo "Hyprland pid $p, parent $pp ($(cat /proc/$pp/comm 2>/dev/null)), cmdline: $(tr '\0' ' ' < /proc/$p/cmdline)"
done
echo "warning lines in the journal: $(journalctl -b --no-pager -o cat | grep -c -i 'without start-hyprland')"
sec bench-status  # ilinux-bench, started by the status screen once the desktop was ready
cat /run/ilinux/bench/status 2>&1
echo "--- steps"; cat /run/ilinux/bench/steps.txt 2>&1
echo "--- done (total seconds): $(cat /run/ilinux/bench/done 2>&1)"
sec bench-env; cat /run/ilinux/bench/env.txt 2>&1
sec bench-results; cat /run/ilinux/bench/results.jsonl 2>&1
sec bench-errors; cat /run/ilinux/bench/errors.txt 2>&1
sec status-screen  # ilinux-status: its log, the kernel-log copy it shows, its processes
cat /run/ilinux/status.log 2>&1
echo "--- kernel log follower: $(wc -l < /run/ilinux/kmsg.txt 2>/dev/null) lines, last 12"
tail -n 12 /run/ilinux/kmsg.txt 2>&1
echo "--- processes"
pgrep -a -f 'ilinux-status|ilinux-bench|journalctl -k|dmesg -w|foot' 2>&1
sec systemd-analyze; systemd-analyze
sec critical-chain; systemd-analyze critical-chain ilinux-desktop.service --no-pager
sec blame; systemd-analyze blame --no-pager | head -40
sec failed-units; systemctl --failed --no-pager --plain
sec meminfo; cat /proc/meminfo
sec free; free -k
sec rootfs; df -k /
sec processes
printf '%8s %8s %8s %s\n' PID RSS_KB PSS_KB COMMAND
for p in /proc/[0-9]*; do
    pss=$(awk '/^Pss:/ {print $2}' "$p/smaps_rollup" 2>/dev/null)
    rss=$(awk '/^Rss:/ {print $2}' "$p/smaps_rollup" 2>/dev/null)
    [ -n "$pss" ] && printf '%8s %8s %8s %s\n' "${p#/proc/}" "$rss" "$pss" "$(tr '\0' ' ' < "$p/cmdline" | cut -c1-80)"
done | sort -k3 -n -r | head -40
sec cpu-10s
names="Hyprland waybar swaybg foot Xwayland"
declare -A before
for n in $names; do before[$n]=$(proc_cpu "$n"); done
read -r _ u1 n1 s1 i1 w1 q1 sq1 st1 _ < /proc/stat
sleep 10
read -r _ u2 n2 s2 i2 w2 q2 sq2 st2 _ < /proc/stat
busy=$(( (u2 + n2 + s2 + q2 + sq2 + st2) - (u1 + n1 + s1 + q1 + sq1 + st1) ))
total=$(( busy + (i2 + w2) - (i1 + w1) ))
echo "system busy ticks $busy of $total (USER_HZ $(getconf CLK_TCK))"
for n in $names; do echo "$n ticks $(( $(proc_cpu "$n") - ${before[$n]:-0} ))"; done
sec drm
ls -l /dev/dri
echo "card0 driver: $(basename "$(readlink -f /sys/class/drm/card0/device/driver)")"
cat /sys/class/drm/card0-*/modes 2>/dev/null
cat /sys/class/graphics/fb0/virtual_size 2>/dev/null
sec renderer  # llvmpipe names its rasterizer threads; libgallium and libLLVM are mapped
p=$(pidof Hyprland)
cat /proc/$p/task/*/comm | sort | uniq -c
grep -o -E '/usr/lib/[^ ]*(gallium|LLVM|EGL_mesa|gbm)[^ ]*' /proc/$p/maps | sort -u
sec hyprland-instances; ls -la --time-style=+%s /run/user/1000/hypr/
sec bwrap
bwrap --ro-bind / / --dev /dev true 2>&1 && echo "bubblewrap as root: OK" || echo "bubblewrap as root: failed"
# The way glycin starts its image loaders, as the desktop user:
setpriv --reuid=1000 --regid=1000 --init-groups bwrap --unshare-all --die-with-parent --chdir / \
    --ro-bind /usr /usr --dev /dev --symlink /usr/lib /lib /usr/bin/true 2>&1 &&
    echo "bubblewrap as user, unshare-all: OK" || echo "bubblewrap as user, unshare-all: failed"
sysctl user.max_user_namespaces kernel.unprivileged_userns_clone 2>&1
# glycin's loader in the same sandbox, without its seccomp filter and D-Bus peer:
setpriv --reuid=1000 --regid=1000 --init-groups bwrap --unshare-all --die-with-parent --chdir / \
    --ro-bind /usr /usr --dev /dev --ro-bind-try /etc/ld.so.cache /etc/ld.so.cache \
    --tmpfs /tmp-home --tmpfs /tmp-run --clearenv --setenv HOME /tmp-home \
    --setenv XDG_RUNTIME_DIR /run/user/1000 --symlink /usr/lib /lib \
    /usr/lib/glycin-loaders/2+/glycin-image-rs --help 2>&1 | head -12; echo "loader exit ${PIPESTATUS[0]}"
sec glycin; tr '\0' '\n' < /proc/$(pidof swaybg)/environ | grep -E '^GLYCIN' || echo "swaybg: no GLYCIN_* variable"
journalctl -b -t swaybg --no-pager -o cat | grep -i -E 'glycin|sandbox|load' | tail -5
sec gdk-pixbuf-loaders  # the module for each image format; glycin's runs its decoders in bubblewrap
grep -A1 '^"/' /usr/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache | grep -v '^--'
sec glycin-sandbox  # with bwrap-trace.sh as the test overlay's /usr/local/bin/bwrap: glycin's calls
grep -E '^(Seccomp|Seccomp_filters|NoNewPrivs):' /proc/self/status
echo "actions_avail: $(cat /proc/sys/kernel/seccomp/actions_avail 2>&1)"
echo "actions_logged: $(cat /proc/sys/kernel/seccomp/actions_logged 2>&1)"
G=
for a in /run/ilinux/bwrap/*.args; do
    grep -q glycin-loaders "$a" 2>/dev/null || continue
    b=${a%.args}
    echo "--- call ${b##*/}"
    cat "$a"
    [ -s "$b.bpf" ] && echo "bpf $(stat -c %s "$b.bpf") bytes, sha256 $(sha256sum < "$b.bpf" | cut -c1-64)"
    echo "stderr:"; head -20 "$b.stderr" 2>/dev/null
    [ -z "$G" ] && [ -s "$b.bpf" ] && G=$b.bpf
done
if [ -n "$G" ]; then
    echo "--- bpf base64 ($G)"; base64 -w 0 "$G"; echo
    # By hand, as the desktop user, in glycin's sandbox: without and with glycin's seccomp
    # program (fd 13). fd 12, glycin's D-Bus socket, is /dev/null here.
    box=(--unshare-all --die-with-parent --chdir / --ro-bind /usr /usr --dev /dev
         --ro-bind-try /etc/ld.so.cache /etc/ld.so.cache --tmpfs /tmp-home --tmpfs /tmp-run
         --clearenv --setenv HOME /tmp-home --setenv XDG_RUNTIME_DIR /tmp-run --symlink /usr/lib /lib)
    for prog in /usr/bin/true "/usr/lib/glycin-loaders/2+/glycin-image-rs --dbus-fd 12"; do
        for s in none seccomp; do
            extra=(); [ $s = seccomp ] && extra=(--seccomp 13)
            # $prog unquoted on purpose: program and arguments
            out=$(setpriv --reuid=1000 --regid=1000 --init-groups /usr/bin/bwrap "${box[@]}" \
                  "${extra[@]}" $prog 13< "$G" 12< /dev/null 2>&1)
            echo "[$s] ${prog%% *}: exit $? $(printf '%s' "$out" | head -c 600 | tr '\n' ' ')"
        done
    done
fi
echo "--- kernel seccomp and audit records"
dmesg | grep -E 'type=1326|seccomp' | tail -20
sec caps  # bwrap refuses to run for a non-root caller that has any permitted capability
printf '%-6s %-5s %-16s %-16s %-16s %-16s %s\n' PID UID CapInh CapPrm CapEff CapAmb COMMAND
for p in /proc/[0-9]*; do
    u=$(awk '/^Uid:/ {print $2}' "$p/status" 2>/dev/null)
    [ -n "$u" ] && [ "$u" != 0 ] || continue
    awk -v pid="${p#/proc/}" -v uid="$u" -v cmd="$(tr '\0' ' ' < "$p/cmdline" | cut -c1-60)" '
        /^Cap(Inh|Prm|Eff|Amb):/ {c[$1] = $2}
        END {printf "%-6s %-5s %-16s %-16s %-16s %-16s %s\n", pid, uid,
             c["CapInh:"], c["CapPrm:"], c["CapEff:"], c["CapAmb:"], cmd}' "$p/status"
done
echo "--- ilinux-desktop.service main process and its ancestors' sets"
m=$(systemctl show -p MainPID --value ilinux-desktop.service)
while [ -n "$m" ] && [ "$m" -gt 1 ]; do
    echo "$m $(tr '\0' ' ' < /proc/$m/cmdline | cut -c1-50): $(grep -E '^Cap(Prm|Amb)' /proc/$m/status | tr '\n\t' '  ')"
    m=$(awk '/^PPid:/ {print $2}' /proc/$m/status)
done
echo "--- file capabilities in the image"
fc=$(getcap -r /usr/bin /usr/lib /usr/local 2>/dev/null | head -20)
echo "${fc:-none}"
sec root-mount; findmnt -n -o SOURCE,FSTYPE,OPTIONS /; findmnt -n -o TARGET,FSTYPE /mnt 2>&1 | head -2
sec coredump-info; coredumpctl info --no-pager 2>&1 | head -60
sec hyprland-crash-report; cat /home/omarchy/.cache/hyprland/hyprlandCrashReport*.txt 2>&1 | head -120
sec hyprctl-version; hypr version
sec hyprctl-monitors; hypr monitors
sec hyprctl-layers; hypr layers
sec hyprctl-clients; hypr clients
sec hyprctl-systeminfo; hypr systeminfo
sec usb-link; ip -details address show usb0; networkctl status usb0 --no-pager 2>&1 | head -30
sec usb-gadget-check  # bounded: run 27 hung here while a check step could block forever
timeout --kill-after=2 40 /usr/local/lib/ilinux/usb-gadget.sh check 2>&1 || echo "check: exit $?"
ls /sys/class/udc 2>&1
lsmod | grep -E '^(libcomposite|u_ether|u_serial|usb_f_)' || echo "no gadget modules loaded (built in?)"
systemd-analyze verify /etc/systemd/system/ilinux-usb-gadget@.service 2>&1 | head -5
echo "units for ttyGS ports: $(systemctl list-units --all --no-legend 'serial-getty@ttyGS*' 2>/dev/null | wc -l) getty"
sec ssh-socket; systemctl status ilinux-sshd.socket --no-pager 2>&1 | head -12
sec modules; lsmod
sec coredumps; coredumpctl list --no-pager 2>&1 | tail -20
sec journal-warnings; journalctl -b -p warning -o short-monotonic --no-pager | tail -150
sec update-units; systemctl status ldconfig.service systemd-journal-catalog-update.service --no-pager 2>&1 | grep -E 'Active|Condition' 
sec bench  # the same work run.sh times in the build VM, to scale this guest's timings
TIMEFORMAT='%R'
echo "bench_gzip_llvm_s_guest $( { time gzip -6 -c /usr/lib/libLLVM.so.23.1 > /dev/null; } 2>&1 )"
echo "bench_zstd_llvm_s_guest $( { time zstd -q -3 -T1 -c /usr/lib/libLLVM.so.23.1 > /dev/null; } 2>&1 )"
sec end

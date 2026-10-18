#!/bin/sh
# usb-gadget.sh start|log|stop UDC | sshd TTY | stream TTY | check
# The USB control channel on one device-mode controller (UDC), so the link works whichever USB-C
# port the second computer's cable is in (the M5 has three). ilinux-usb-gadget@<udc>.service
# runs start, then log as its main process, then stop.
# FUNCTION=gser (the default, /etc/default/ilinux-usb-gadget): one configuration with two
# instances of the kernel's generic serial function, as boot039's Stage-B init has one. Each is
# a vendor-class (0xff) interface with one bulk-IN and one bulk-OUT endpoint: no interrupt
# endpoint (attempt 18's CDC-ACM + CDC-ECM device stopped answering control transfers right
# after macOS set the configuration) and no class requests. macOS binds no driver to them; the
# second computer's own user-space tools open the interfaces:
#  * gser.log, interface 0: the journal, written only by this side and read by the M1's
#    bulk-log reader (tools/m1n1-client/bulk-log-reader-brief.md). Nothing reads from it.
#  * gser.ssh, interface 1: a raw byte pipe. ilinux-sshd-tty@<tty>.service runs sshd -i on it,
#    one connection at a time; on the M1, tools/m1n1-client/usb-pipe is ssh's ProxyCommand.
# FUNCTION=ecm (or ncm, eem): the earlier design, a CDC network function, with ACM=1 adding a
# CDC-ACM journal port before it (macOS 26.0.1 loads ECM and ACM; it has no usable EEM
# driver). This end is then usb<N> from u_ether (networkd: 10.66.0.2/24 and a DHCP server,
# see 20-usb.network) and SSH listens on 10.66.0.2:22 (ilinux-sshd.socket).
# usb-gadget.sh stream TTY: the journal to a serial port (what log runs, and check tries).
# usb-gadget.sh sshd TTY: sshd -i on a raw serial port (what ilinux-sshd-tty@.service runs).
# usb-gadget.sh check: create the functions in configfs without binding a UDC.
# Ports and USB strings are those of the Stage-B inits (kernel/experiments/usb-gadget/init.c),
# so the second computer reaches both stages the same way: usb-drd0..2 are ports 1..3, any other
# UDC (VM tests) 4+ in sorted order. bcdDevice 0x0039 here (Stage-B: 0x0036 in boot036, 0x0038
# in boot038, 0x0139 in boot039) tells the stages apart in ioreg. For the network functions,
# port N has dev_addr 02:69:6c:69:6e:0N and host_addr 02:69:6c:69:6f:0N, so this end is
# fe80::69:6cff:fe69:6e0N. Fixed, locally administered values; no machine identifiers.
set -eu
FUNCTION=gser
ACM=0
[ -r /etc/default/ilinux-usb-gadget ] && . /etc/default/ilinux-usb-gadget
CFG=/sys/kernel/config/usb_gadget
KNOWN='2a2280000\.usb|2aa280000\.usb|382280000\.usb'
action=${1:-}
udc=${2:-}
name=ilinux-$(printf '%s' "$udc" | tr -c 'A-Za-z0-9' '_')
G=$CFG/$name

# libcomposite is a module up to boot035 and built in from boot036. Creating a function
# directory loads usb_f_<function> through its "usbfunc:" alias when that is a module.
gadget_core() {
    [ -d "$CFG" ] || modprobe libcomposite
}

port_index() {
    case "$1" in
    2a2280000.usb) echo 1 ;;
    2aa280000.usb) echo 2 ;;
    382280000.usb) echo 3 ;;
    *) ls /sys/class/udc | sort | grep -v -x -E "$KNOWN" | grep -n -x -F "$1" |
           cut -d: -f1 | awk '{print $1 + 3}' ;;
    esac
}

network_name() {
    case "$FUNCTION" in
    ecm) echo "CDC ECM" ;;
    ncm) echo "CDC NCM" ;;
    eem) echo "CDC EEM" ;;
    *) echo "$FUNCTION" ;;
    esac
}

# The serial port (/dev/ttyGS<n>) of a gadget's serial function (gser.log, gser.ssh, acm.GS0),
# or nothing. u_serial numbers the ports as the functions are created.
function_tty() {
    n=$(cat "$1/functions/$2/port_num" 2>/dev/null) || return 0
    [ -n "$n" ] && echo "/dev/ttyGS$n"
}

# The journal's port: the bulk-only log function if there is one, else the ACM port.
log_tty() {
    tty=$(function_tty "$1" gser.log)
    [ -n "$tty" ] || tty=$(function_tty "$1" acm.GS0)
    echo "$tty"
}

# The unit that runs sshd on a gadget's gser.ssh port, or nothing.
sshd_unit() {
    tty=$(function_tty "$1" gser.ssh)
    [ -n "$tty" ] && echo "ilinux-sshd-tty@${tty#/dev/}.service"
}

have_systemd() {
    [ -d /run/systemd/system ] && command -v systemctl > /dev/null 2>&1
}

case "$action" in
stream)
    # stream TTY: the whole boot's journal, then the new records, to that serial port until journalctl
    # ends (hang-up or error). Without -n all, -f would start at the last ten lines.
    # With no host reading, the port's 8 KiB buffer fills and the write blocks; journalctl
    # blocks SIGTERM while it follows, so only SIGKILL ends it then.
    tty=$udc
    stty -F "$tty" -echo -icanon -isig -ixon 2> /dev/null || true
    exec journalctl -b -f -n all -o short-monotonic --no-pager --no-hostname > "$tty" 2> /dev/null
    ;;
sshd)
    # sshd TTY (ttyGS<n>): sshd in inetd mode on that serial port, made raw first, so the port
    # is a transparent byte pipe: no echo, no line discipline, no signal or CR/LF handling.
    # sshd sends its banner at once and then waits for the client's; the M1's usb-pipe only
    # forwards ssh after it has seen that banner. One connection per sshd; the unit restarts
    # it (sshd_config.d/25-ilinux-usb-pipe.conf bounds a session whose client vanished). The
    # port stays open for sshd's whole life; the stop action below stops the unit before it
    # removes the function, which would otherwise wait for the port to close.
    tty=/dev/$udc
    [ -c "$tty" ] || { echo "$tty does not exist" >&2; sleep 5; exit 1; }
    exec 3<> "$tty"
    stty raw -echo -echoe -echok -echoctl -echoke -echonl <&3
    # The client's last packets (its disconnect) can reach the port after the previous sshd has already
    # exited, either queued while the port was closed or still being sent by the host. Read and drop
    # whatever arrives until the port has been quiet for 0.2 s (VMIN 0, VTIME 2: a read returns 0 after
    # that long), at most 2 s, so that the new sshd starts at a clean boundary. The M1's tool sends
    # nothing before it has seen this sshd's banner, which comes after this.
    # This unit's process is a session leader, so opening the port made it the controlling terminal. GNU
    # timeout would put dd in a background process group, and a background read from the controlling
    # terminal stops with SIGTTIN (the drain then read nothing and only waited): --foreground avoids that.
    stty min 0 time 2 <&3
    cap="timeout 2"
    timeout --foreground 1 true 2> /dev/null && cap="timeout --foreground 2"
    dropped=$($cap dd bs=65536 <&3 2> /dev/null | wc -c | tr -d ' ')
    [ "${dropped:-0}" -eq 0 ] 2> /dev/null || echo "dropped $dropped stale bytes from $tty before starting sshd" >&2
    stty min 1 time 0 <&3
    exec /usr/bin/sshd -i -e <&3 >&3
    ;;
start)
    [ -n "$udc" ] || { echo "usage: $0 start UDC" >&2; exit 2; }
    [ -e "$G/UDC" ] && [ -n "$(cat "$G/UDC")" ] && exit 0
    gadget_core
    n=$(port_index "$udc")
    mkdir -p "$G/strings/0x409" "$G/configs/c.1/strings/0x409"
    echo 0x1d6b > "$G/idVendor"     # Linux Foundation
    echo 0x0104 > "$G/idProduct"    # Multifunction Composite Gadget
    echo 0x0039 > "$G/bcdDevice"    # job 039's RAM root (BCD only: configfs refuses 0x003a)
    echo 0x0200 > "$G/bcdUSB"
    echo iLinux > "$G/strings/0x409/manufacturer"
    echo "iLinux J716c control channel, port $n" > "$G/strings/0x409/product"
    echo "ilinux-port$n" > "$G/strings/0x409/serialnumber"   # not a hardware serial
    if [ "$FUNCTION" = gser ]; then
        # The link order sets the interface order: the log on interface 0, SSH on 1.
        mkdir -p "$G/functions/gser.log" "$G/functions/gser.ssh"
        functions="gser.log gser.ssh"
        config="Bulk-only kernel log port + SSH byte pipe"
    else
        acm=
        if [ "$ACM" = 1 ]; then
            if mkdir -p "$G/functions/acm.GS0" 2> /dev/null; then
                acm=acm.GS0
            else
                echo "no CDC-ACM gadget function in this kernel: network only" >&2
            fi
        fi
        mkdir -p "$G/functions/$FUNCTION.usb"
        printf '02:69:6c:69:6e:%02x\n' "$n" > "$G/functions/$FUNCTION.usb/dev_addr"
        printf '02:69:6c:69:6f:%02x\n' "$n" > "$G/functions/$FUNCTION.usb/host_addr"
        # ACM first (interfaces 0-1), then the network (2-3).
        functions="$acm $FUNCTION.usb"
        config=$(network_name)
        [ -n "$acm" ] && config="CDC ACM log port + $config network"
    fi
    echo "$config" > "$G/configs/c.1/strings/0x409/configuration"
    echo 250 > "$G/configs/c.1/MaxPower"
    for f in $functions; do
        [ -e "$G/configs/c.1/$f" ] || ln -s "$G/functions/$f" "$G/configs/c.1/"
    done
    echo "$udc" > "$G/UDC"
    unit=$(sshd_unit "$G")
    if [ -n "$unit" ] && have_systemd; then
        # A port that vanished with an earlier gadget leaves the unit failed; clear that.
        systemctl reset-failed "$unit" 2> /dev/null || true
        systemctl start --no-block "$unit"
    fi
    echo "gadget $name bound to $udc as port $n: $config; log on $(log_tty "$G"), sshd on $(function_tty "$G" gser.ssh)"
    ;;
log)
    # The unit's main process: the journal on the log port for as long as the gadget exists.
    # A hang-up (cable out) ends journalctl; it starts again from the boot's start.
    tty=$(log_tty "$G")
    [ -n "$tty" ] || exec sleep infinity
    while :; do
        "$0" stream "$tty" || true
        sleep 2
    done
    ;;
stop)
    # Runs after the log process has ended. Removing a serial function waits until nothing
    # has its port open, so sshd's unit goes first. Best effort, so a half-made gadget goes too.
    [ -d "$G" ] || exit 0
    set +e
    unit=$(sshd_unit "$G")
    [ -n "$unit" ] && have_systemd && systemctl stop "$unit"
    echo "" > "$G/UDC" 2> /dev/null
    for f in "$G"/configs/c.1/*; do
        if [ -L "$f" ]; then rm -f "$f"; fi
    done
    rmdir "$G/configs/c.1/strings/0x409" "$G/configs/c.1" "$G"/functions/* \
          "$G/strings/0x409" "$G"
    ;;
check)
    gadget_core
    C=$CFG/ilinux-check
    if [ "$FUNCTION" = gser ]; then
        mkdir -p "$C/functions/gser.log" "$C/functions/gser.ssh"
        for f in gser.log gser.ssh; do
            tty=$(function_tty "$C" "$f")
            [ -c "$tty" ] && state=exists || state=missing
            echo "configfs function $f created (no UDC bound): serial port $tty ($state)"
        done
        tty=$(function_tty "$C" gser.log)
        rc=0
        timeout --kill-after=1 2 "$0" stream "$tty" || rc=$?
        echo "journal to $tty for 2 s: exit $rc (124: ended by SIGTERM, 137: by SIGKILL)"
        /usr/bin/sshd -t && echo "sshd configuration test passed"
        rmdir "$C/functions/gser.ssh" "$C/functions/gser.log" "$C"
        echo "functions removed"
    else
        mkdir -p "$C/functions/$FUNCTION.usb"
        echo "configfs function $FUNCTION.usb created (no UDC bound)"
        if [ "$ACM" = 1 ] && mkdir -p "$C/functions/acm.GS0" 2> /dev/null; then
            tty=$(function_tty "$C" acm.GS0)
            [ -c "$tty" ] && state=exists || state=missing
            echo "configfs function acm.GS0 created: serial port $tty ($state)"
            rc=0
            timeout --kill-after=1 2 "$0" stream "$tty" || rc=$?
            echo "journal to $tty for 2 s: exit $rc (124: ended by SIGTERM, 137: by SIGKILL)"
            rmdir "$C/functions/acm.GS0"
            echo "acm.GS0 removed"
        else
            echo "no CDC-ACM gadget function (ACM=$ACM)"
        fi
        rmdir "$C/functions/$FUNCTION.usb" "$C"
    fi
    ;;
*)
    echo "usage: $0 start|log|stop UDC | sshd TTY | stream TTY | check" >&2
    exit 2
    ;;
esac

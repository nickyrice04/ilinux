#!/bin/sh
# usb-gadget.sh start|log|stop UDC: the USB control channel on one device-mode controller, so
# the link works whichever USB-C port the second computer's cable is in (the M5 has three).
# ilinux-usb-gadget@<udc>.service runs start, then log as its main process, then stop.
# Like boot038's Stage-B init, one configuration holds two functions:
#  * CDC-ACM: a serial port that carries the journal to the second computer, read-only.
#    Nothing reads from it and there is no login on it (macOS: /dev/cu.usbmodem*).
#    ACM=0 in /etc/default/ilinux-usb-gadget leaves it out.
#  * The network: CDC-ECM, unless that file sets FUNCTION=ncm or eem. The controller's macOS
#    26.0.1 loads ECM but has no usable EEM driver (attempt 17). This end is usb<N> from u_ether
#    (networkd: 10.66.0.2/24 and a DHCP server, see 20-usb.network).
# usb-gadget.sh stream TTY: the journal to a serial port (what log runs, and check tries).
# usb-gadget.sh check: create the functions in configfs without binding a UDC.
# Ports, MACs and USB strings are those of boot036's and boot038's Stage-B init
# (kernel/experiments/usb-gadget/init.c), so the second computer reaches both stages the same
# way: usb-drd0..2 are ports 1..3, any other UDC (VM tests) 4+ in sorted order; port N has
# dev_addr 02:69:6c:69:6e:0N and host_addr 02:69:6c:69:6f:0N, so this end is
# fe80::69:6cff:fe69:6e0N. Fixed, locally administered values; no machine identifiers.
set -eu
FUNCTION=ecm
ACM=1
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

# The serial port of the gadget's ACM function (/dev/ttyGS<n>), or nothing.
acm_tty() {
    n=$(cat "$1/functions/acm.GS0/port_num" 2>/dev/null) || return 0
    [ -n "$n" ] && echo "/dev/ttyGS$n"
}

case "$action" in
stream)
    # stream TTY: the journal to that serial port until journalctl ends (hang-up or error).
    # With no host reading, the port's 8 KiB buffer fills and the write blocks; journalctl
    # blocks SIGTERM while it follows, so only SIGKILL ends it then.
    tty=$udc
    stty -F "$tty" -echo -icanon -isig -ixon 2> /dev/null || true
    exec journalctl -b -f -o short-monotonic --no-pager --no-hostname > "$tty" 2> /dev/null
    ;;
start)
    [ -n "$udc" ] || { echo "usage: $0 start UDC" >&2; exit 2; }
    [ -e "$G/UDC" ] && [ -n "$(cat "$G/UDC")" ] && exit 0
    gadget_core
    n=$(port_index "$udc")
    mkdir -p "$G/strings/0x409" "$G/configs/c.1/strings/0x409"
    acm=
    if [ "$ACM" = 1 ]; then
        if mkdir -p "$G/functions/acm.GS0" 2> /dev/null; then
            acm=acm.GS0
        else
            echo "no CDC-ACM gadget function in this kernel: network only" >&2
        fi
    fi
    mkdir -p "$G/functions/$FUNCTION.usb"
    echo 0x1d6b > "$G/idVendor"     # Linux Foundation
    echo 0x0104 > "$G/idProduct"    # Multifunction Composite Gadget
    echo 0x0039 > "$G/bcdDevice"    # job 039's RAM root (Stage-B: 0x0036 in boot036, 0x0038 in boot038)
    echo 0x0200 > "$G/bcdUSB"
    echo iLinux > "$G/strings/0x409/manufacturer"
    echo "iLinux J716c control channel, port $n" > "$G/strings/0x409/product"
    echo "ilinux-port$n" > "$G/strings/0x409/serialnumber"   # not a hardware serial
    config=$(network_name)
    [ -n "$acm" ] && config="CDC ACM log port + $config network"
    echo "$config" > "$G/configs/c.1/strings/0x409/configuration"
    echo 250 > "$G/configs/c.1/MaxPower"
    printf '02:69:6c:69:6e:%02x\n' "$n" > "$G/functions/$FUNCTION.usb/dev_addr"
    printf '02:69:6c:69:6f:%02x\n' "$n" > "$G/functions/$FUNCTION.usb/host_addr"
    # ACM first (interfaces 0-1), then the network (2-3): the link order sets the interface order.
    for f in $acm "$FUNCTION.usb"; do
        [ -e "$G/configs/c.1/$f" ] || ln -s "$G/functions/$f" "$G/configs/c.1/"
    done
    echo "$udc" > "$G/UDC"
    ;;
log)
    # The unit's main process: the journal on the ACM serial port for as long as the gadget
    # exists. A hang-up (cable out) ends journalctl; it starts again from the boot's start.
    tty=$(acm_tty "$G")
    [ -n "$tty" ] || exec sleep infinity
    while :; do
        "$0" stream "$tty" || true
        sleep 2
    done
    ;;
stop)
    # Runs after the log process has ended: removing an ACM function waits until nothing
    # has its serial port open. Best effort, so a half-made gadget goes too.
    [ -d "$G" ] || exit 0
    set +e
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
    mkdir -p "$C/functions/$FUNCTION.usb"
    echo "configfs function $FUNCTION.usb created (no UDC bound)"
    if [ "$ACM" = 1 ] && mkdir -p "$C/functions/acm.GS0" 2> /dev/null; then
        tty=$(acm_tty "$C")
        [ -c "$tty" ] && state=exists || state=missing
        echo "configfs function acm.GS0 created: serial port $tty ($state)"
        # The log loop's step for 2 s with no host attached, then the unit's teardown order:
        # the writer ends (SIGKILL if SIGTERM does not do it) before the function goes.
        rc=0
        timeout --kill-after=1 2 "$0" stream "$tty" || rc=$?
        echo "journal to $tty for 2 s: exit $rc (124: ended by SIGTERM, 137: by SIGKILL)"
        rmdir "$C/functions/acm.GS0"
        echo "acm.GS0 removed"
    else
        echo "no CDC-ACM gadget function (ACM=$ACM)"
    fi
    rmdir "$C/functions/$FUNCTION.usb" "$C"
    ;;
*)
    echo "usage: $0 start|log|stop UDC | stream TTY | check" >&2
    exit 2
    ;;
esac

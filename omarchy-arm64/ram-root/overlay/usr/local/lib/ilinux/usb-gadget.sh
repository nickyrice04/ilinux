#!/bin/sh
# usb-gadget.sh start|stop UDC: one USB network function on the given device-mode controller,
# so the link works whichever USB-C port the second computer's cable is in (the M5 has three).
# The M5 is the USB device; its interface is usb<N> from u_ether (networkd: 10.66.0.2/24 and a
# DHCP server, see 20-usb.network).
# usb-gadget.sh check: create the function in configfs without binding a UDC.
# The function is CDC-EEM unless /etc/default/ilinux-usb-gadget sets FUNCTION=ncm or ecm:
# the ADT marks the M5's ports ncm-interrupt-ep-disabled, NCM stalled on this SoC elsewhere,
# and macOS ships AppleUSBEEM.
# Ports, MACs and USB strings are those of boot036's Stage-B init
# (kernel/experiments/usb-gadget/init.c), so the second computer reaches both stages the same
# way: usb-drd0..2 are ports 1..3, any other UDC (VM tests) 4+ in sorted order; port N has
# dev_addr 02:69:6c:69:6e:0N and host_addr 02:69:6c:69:6f:0N, so this end is
# fe80::69:6cff:fe69:6e0N. Fixed, locally administered values; no machine identifiers.
set -eu
FUNCTION=eem
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

case "$action" in
start)
    [ -n "$udc" ] || { echo "usage: $0 start UDC" >&2; exit 2; }
    [ -e "$G/UDC" ] && [ -n "$(cat "$G/UDC")" ] && exit 0
    gadget_core
    n=$(port_index "$udc")
    mkdir -p "$G/strings/0x409" "$G/configs/c.1/strings/0x409" "$G/functions/$FUNCTION.usb"
    echo 0x1d6b > "$G/idVendor"     # Linux Foundation
    echo 0x0104 > "$G/idProduct"    # Multifunction Composite Gadget
    echo 0x0039 > "$G/bcdDevice"    # job 039's RAM root (boot036's Stage-B init uses 0x0036)
    echo 0x0200 > "$G/bcdUSB"
    echo iLinux > "$G/strings/0x409/manufacturer"
    echo "iLinux J716c control channel, port $n" > "$G/strings/0x409/product"
    echo "ilinux-port$n" > "$G/strings/0x409/serialnumber"   # not a hardware serial
    if [ "$FUNCTION" = eem ]; then
        echo "CDC EEM" > "$G/configs/c.1/strings/0x409/configuration"
    else
        echo "$FUNCTION" > "$G/configs/c.1/strings/0x409/configuration"
    fi
    echo 250 > "$G/configs/c.1/MaxPower"
    printf '02:69:6c:69:6e:%02x\n' "$n" > "$G/functions/$FUNCTION.usb/dev_addr"
    printf '02:69:6c:69:6f:%02x\n' "$n" > "$G/functions/$FUNCTION.usb/host_addr"
    [ -e "$G/configs/c.1/$FUNCTION.usb" ] || ln -s "$G/functions/$FUNCTION.usb" "$G/configs/c.1/"
    echo "$udc" > "$G/UDC"
    ;;
stop)
    [ -d "$G" ] || exit 0
    echo "" > "$G/UDC" || true
    rm -f "$G/configs/c.1/$FUNCTION.usb"
    rmdir "$G/configs/c.1/strings/0x409" "$G/configs/c.1" "$G/functions/$FUNCTION.usb" \
          "$G/strings/0x409" "$G"
    ;;
check)
    gadget_core
    mkdir -p "$CFG/ilinux-check/functions/$FUNCTION.usb"
    echo "configfs function $FUNCTION.usb created (no UDC bound)"
    rmdir "$CFG/ilinux-check/functions/$FUNCTION.usb" "$CFG/ilinux-check"
    ;;
*)
    echo "usage: $0 start|stop UDC | check" >&2
    exit 2
    ;;
esac

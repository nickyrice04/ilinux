# VM test only (job 049): helpers for both halves of the test, sourced. Markers go to the virtio
# console (ILINUX049-<NAME> <seconds since kernel start> <detail>), which run-qemu.sh reads; files go to
# the 9p results share. Both stages share one kernel, so the uptime is one time line from the
# "handoff" (QEMU's kernel entry) through the switch to the Omarchy desktop.
CON=/dev/hvc0
RES=/run/ilinux049/results
up() { cut -d' ' -f1 /proc/uptime; }
mark() {   # mark NAME [DETAIL]
    local t; t=$(up)
    echo "ILINUX049-$1 $t ${2:-}" | cut -c1-400 > "$CON"
    echo "$t $1 ${2:-}" >> "$RES/timeline.txt"
}
say() { echo "[$(up)] $*" >> "$RES/${LOGNAME_049:-test}.log"; }
results() {
    mkdir -p "$RES"
    mountpoint -q "$RES" || mount -t 9p -o trans=virtio,version=9p2000.L,msize=262144 results "$RES"
}
# usb_device: the host side's view of the gadget (dummy_hcd makes this kernel its own host): sets DEV,
# TTY_LOG (interface 0) and TTY_SSH (interface 1), the generic usb-serial ports
usb_device() {
    DEV= TTY_LOG= TTY_SSH=
    local d
    # the generic usb-serial driver binds only IDs it is given (job 046); the kernel keeps the ID
    # across the soft-reboot, so in stage two this write fails with EEXIST, which is fine
    echo "1d6b 0104" > /sys/bus/usb-serial/drivers/generic/new_id 2> /dev/null || true
    for _ in $(seq 120); do
        for d in /sys/bus/usb/devices/*; do
            [ -f "$d/idVendor" ] && [ "$(cat "$d/idVendor")" = 1d6b ] && [ "$(cat "$d/idProduct")" = 0104 ] && DEV=$d
        done
        if [ -n "$DEV" ]; then
            TTY_LOG=$(cd "$DEV:1.0" 2> /dev/null && ls -d ttyUSB* 2> /dev/null | head -1)
            TTY_SSH=$(cd "$DEV:1.1" 2> /dev/null && ls -d ttyUSB* 2> /dev/null | head -1)
            [ -n "$TTY_LOG" ] && [ -n "$TTY_SSH" ] && return 0
        fi
        sleep 1
    done
    return 1
}
# gadget_up: the M5 side as the root's units run it: sets UDC, GADGET, SSH_UNIT, HOSTFP
gadget_up() {
    UDC= GADGET= SSH_UNIT= HOSTFP=
    for _ in $(seq 120); do UDC=$(ls /sys/class/udc 2> /dev/null | head -1); [ -n "$UDC" ] && break; sleep 1; done
    [ -n "$UDC" ] || return 1
    local unit=ilinux-usb-gadget@$UDC.service
    for _ in $(seq 180); do systemctl is-active -q "$unit" && break; sleep 1; done
    systemctl is-active -q "$unit" || return 1
    GADGET=/sys/kernel/config/usb_gadget/ilinux-$(printf '%s' "$UDC" | tr -c 'A-Za-z0-9' '_')
    SSH_UNIT=ilinux-sshd-tty@ttyGS$(cat "$GADGET/functions/gser.ssh/port_num").service
    for _ in $(seq 120); do systemctl is-active -q "$SSH_UNIT" && break; sleep 1; done
    systemctl is-active -q "$SSH_UNIT" || return 1
    for _ in $(seq 60); do [ "$(cat "/sys/class/udc/$UDC/state")" = configured ] && break; sleep 1; done
    HOSTFP=$(journalctl -b -u ilinux-ssh-hostkey.service -o cat --no-pager | grep -o 'SHA256:[A-Za-z0-9+/]*' | tail -1)
    return 0
}
# raw_pipe: Linux's usb-serial tty opens with echo on, which would echo the M5 sshd's banner back to it
# (job 045 saw "Bad packet length"); the M1's usb-pipe talks IOUSBHost with no tty between. So the
# host's port is made raw once (the kernel keeps the setting) and the M5's sshd starts afresh.
raw_pipe() {
    stty -F "/dev/$TTY_SSH" raw -echo -echoe -echok -echoctl -echoke -echonl
    systemctl restart "$SSH_UNIT"
    for _ in $(seq 60); do systemctl is-active -q "$SSH_UNIT" && break; sleep 1; done
}
# m1_tree DIR: the M1's build/control in a copy of the repository's tools (the real m5-ssh-config):
# the VM key as m1-control and usb-pipe as a wrapper that gives the Linux build the host's tty
m1_tree() {
    local d=$1
    mkdir -p "$d/build/control" "$d/build/native-intake"
    install -m 0600 "$KEYS/id_ed25519" "$d/build/control/m1-control"
    printf '#!/bin/sh\nexec %s --tty /dev/%s --banner-wait 30 "$@"\n' "$USBPIPE" "$TTY_SSH" > "$d/build/control/usb-pipe"
    chmod 0755 "$d/build/control/usb-pipe"
}

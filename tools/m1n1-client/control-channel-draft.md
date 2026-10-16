# Attempt 18, the USB control channel (boot038): M1-side steps

**Active for attempt 17, 2026-10-15.** The checklist is
`stage-b-instructions.md`; this file holds the M1-side detail it refers to.
Attempt 16 (boot035) reached `ladder complete` and the first stable baseline,
which this attempt builds on.

Design and evidence: `kernel/experiments/usb-gadget/README.md`. Everything in
the Stage-B checklist (`stage-b-instructions.md`) still applies: Full Security
on Macintosh HD, no volume, security or installed-m1n1 change, no automatic
retries, film the M5 screen, Macintosh HD afterwards.

## What is new for the M1

After the handoff, the M5 no longer goes silent on USB. About 5–15 s after PID
1, Linux presents a new USB device on the same cable: "iLinux J716c control
channel, port N", VID:PID `1d6b:0104`, with two functions: a **CDC-ACM serial
port** that carries the M5's kernel log (the M5 never reads from it) and a
**CDC-ECM network** function. Attempt 17 proved the enumeration path on this
device with CDC-EEM, which macOS 26.0.1 cannot bind; ACM and ECM drivers are
loaded on the M1. It is a different device from m1n1's (`1209:316d`). Its
`bcdDevice` is `0x0038` (boot038's Stage-B init; boot036 was `0x0036`). The
later Arch RAM root answers on the same port, MAC and link-local address with
`bcdDevice` `0x0039`, so `ioreg` tells the stages apart.

## Before the attempt (offline, read-only)

1. macOS driver present (expect `2`, `12`, `7`):

   ```sh
   sw_vers
   plutil -p /System/Library/Extensions/AppleUSBEEM.kext/Contents/Info.plist \
     | grep -E 'CFBundleVersion|bInterface(Class|SubClass|Protocol)'
   ```

   If the kext is missing, stop and report: boot036 would need NCM or ECM, which
   the M5's ports flag `ncm-interrupt-ep-disabled`.
2. SSH key: **done** (commit `a6717b0`). The M1's own key
   `build/control/m1-control` (private half, mode 600, never leaves the M1);
   its public half is `kernel/experiments/usb-gadget/authorized_keys`,
   fingerprint `SHA256:o7wtpNY0RUOIIGTyIJvspZFOetYFFG2oeMw5ecZc3yI`. boot036
   authorizes exactly this key and nothing else.
3. Record the interfaces before the handoff: `ifconfig -l > build/native-intake/ifaces-before.txt`.

## During the attempt

Restart the M1 fresh, keep it on power under `caffeinate -i`, and launch exactly
as in the Stage-B checklist. Once the launcher reports the handoff, it has
closed the serial port; do not reopen it.

On the M5 screen, after the usual dumps, expect:

* `[ctl] USB control channel: CDC-ACM log port + CDC-ECM per UDC, IPv6 link-local, SSH key only`
* one `[ctl] port N: UDC <name> bound, ACM+ECM 1d6b:0104, interface usbX up, log on ttyGSn` line per
  port (three), naming the address `fe80::69:6cff:fe69:6e0N`
* `[ctl] dropbear start 1`
* each heartbeat, `[ctl] port1 <state> ... | port2 ... | port3 ...`; the port with
  the cable should reach `configured`, then show rising `rx=`/`tx=` counts and
  its link-local address.

On the M1 (read-only commands; N is the port whose state is `configured`):

```sh
ioreg -p IOUSB -l -w0 | grep -i -A3 'iLinux'
ifconfig -l > build/native-intake/ifaces-after.txt
diff build/native-intake/ifaces-before.txt build/native-intake/ifaces-after.txt
ifconfig enX                        # the new interface; look for inet6 fe80::...%enX
ping6 -c 3 fe80::69:6cff:fe69:6e0N%enX
ssh -i build/control/m1-control -o UserKnownHostsFile=build/control/known_hosts \
    -o StrictHostKeyChecking=accept-new root@fe80::69:6cff:fe69:6e0N%enX \
    'uname -a; cat /proc/cmdline; cat /sys/class/udc/*/state; dmesg | tail -n 80'
```

Optional, once SSH works: a timed 256 MiB transfer (it sizes the RAM-root
upload).

```sh
time (dd if=/dev/zero bs=1m count=256 | ssh -i build/control/m1-control \
    -o UserKnownHostsFile=build/control/known_hosts root@fe80::69:6cff:fe69:6e0N%enX 'cat > /dev/null')
```

Keep `dmesg` output local in `build/native-intake/`. Commit only excerpts after
checking them for serials and MACs. Never copy `/proc/device-tree`: m1n1 adds the
target's serial there.

If macOS shows the interface but no `inet6` address, it has not set up IPv6 on
the new interface. Do not change settings; report it. Adding the network service
in System Settings is a settings change that needs the user's approval.

## Reading the result

| M5 screen | M1 | Meaning |
|---|---|---|
| a port reaches `configured`, rx/tx rise | new `enX`, ping and SSH work | **Control channel works**: the first remote shell into native Linux |
| `dwc3 ... -110` or `timeout` during probe | no device | the core cannot soft-reset: PHY or power state differs from what m1n1 left |
| `apple-dart ... fault` | device seen, then traffic dies | DMA mapping wrong: next try both DART instances (Asahi's layout) |
| ports stay `not attached` / `default` | no device | no pull-up or no PHY: report the states |
| `configured` | kernel log arrives on the new `cu.usbmodem*` | the ACM log port works; save the capture |
| `configured` | device in `ioreg`, no new `cu.usbmodem*`, no `enX` | macOS bound neither driver: report the `ioreg` interface lines |
| `configured`, rx stays 0 | `enX` without `inet6` | macOS IPv6 not set up on `enX` (see above) |
| silent reset, black screen | | as in attempt 16: note the time and the last lines |

Stop on any M1 panic or SoC reset. Power off the M5 and return to Macintosh HD
afterwards, as always.

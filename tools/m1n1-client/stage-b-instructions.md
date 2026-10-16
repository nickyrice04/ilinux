# Stage B — attempt 18 / boot038: the USB control channel, ACM + ECM

**M5 handoff, 2026-10-16.** Pull latest main with `git pull --ff-only`, preserving
local work and stopping on divergence. Read `coordination.md`, this file,
`native/boot/boot036-control-channel-2026-10-15.md` (boot038 section) and
`tools/m1n1-client/control-channel-draft.md` (the M1-side steps).
Attempt 17 is consumed: boot036's three USB controllers, gadget and dropbear
all worked on the M5 and the M1 enumerated the device in 8 s, but the M1's
macOS 26.0.1 has no CDC-EEM driver, so no interface appeared
(`native/boot/stage-b-2026-10-16-attempt17-result.md`).
**Native attempt 18 / boot038 / live checks NOT RUN at this handoff.**

**Continue the existing installation.** Installed boot021 m1n1 and clean client
pin remain unchanged. Do not repeat provisioning, Stage A, Recovery, macOS
installation, `bputil`, `kmutil`, partitioning or m1n1 installation. Keep
Macintosh HD at Full Security and as default. No volume/security changes, and
**no network-settings changes on the M1** without the human's approval.

## What changed and why

boot038 is boot036 with **one change: the gadget's USB functions**. Image,
kernel config, Stage-B DT, m1n1, the generic initramfs, the launcher and its
fixed arguments are byte-identical to boot036; only `initramfs-stage-b.cpio.gz`
and its source `diag-init.c` differ.

* Each controller's gadget now has **two functions in one configuration**:
  * **CDC-ACM** (interfaces 0–1): a serial port. The M5 side only writes to
    it: a child of `/init` copies the kernel log (`/dev/kmsg`) to it as
    `[sec.usec] text` lines. macOS binds its ACM driver (loaded on the M1 per
    attempt 17) and creates `/dev/cu.usbmodem*`, so the M1 can read `dmesg`
    even if networking fails. Nothing is read from the port on the M5 side.
  * **CDC-ECM** (interfaces 2–3): the network link, same MACs and link-local
    address as boot036 (port N = `fe80::69:6cff:fe69:6e0N`), key-only
    dropbear for root with the M1's key (`a6717b0`,
    `SHA256:o7wtpNY0RUOIIGTyIJvspZFOetYFFG2oeMw5ecZc3yI`). macOS's ECM driver
    was loaded on the M1 in attempt 17.
* `bcdDevice` is `0x0038` (boot036 was `0x0036`), configuration string
  "CDC ACM log port + CDC ECM network".
* Why not EEM: attempt 17 showed `com.apple.driver.usb.cdc.eem` is a stub on
  macOS 26.0.1 and is never loaded. Why both ACM and ECM: both need an
  interrupt-IN notification endpoint, which the ADT flags
  `ncm-interrupt-ep-disabled` for Apple's own NCM; if that endpoint cannot
  transmit on this hardware, the ACM port's silence and the ECM link's state
  show it, and the boot still reports everything on screen.

Offline: VM job 041 rebuilt the initramfs; generic-VM liveness PASS; the VM
self-test with a virtual USB host PASS (ACM+ECM enumeration, kernel log over
the ACM port, ping, SSH with the key, refusal without it, an 8 MiB copy). The
macOS drivers and the interrupt endpoint are what this attempt tests.

## Offline intake before the human restarts

Download only private `native-j716c-boot038`; verify the archive against current
Git **before extraction**. Preserve every earlier package/receipt/result. Stop
on a mismatch. The following performs no live USB action.

```sh
(
set -e
mkdir -p build/native-boot038-download
if [ ! -f build/native-boot038-download/ilinux-j716c-boot038.tar.gz ]; then
  gh release download native-j716c-boot038 --repo nickyrice04/ilinux \
    --pattern ilinux-j716c-boot038.tar.gz --dir build/native-boot038-download
fi
(
  cd build/native-boot038-download
  shasum -a 256 -c ../../native/boot/archive-sha256.txt
  if [ ! -d ilinux-j716c-boot038 ]; then tar -xzf ilinux-j716c-boot038.tar.gz; fi
)
mkdir -p build/native-intake/receipts build/native-intake/results
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot038-download/ilinux-j716c-boot038 \
  --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
  > build/native-intake/receipts/boot038-attempt18.json
python3 -I native/boot/launch.py --package build/native-boot038-download/ilinux-j716c-boot038
python3 -I native/boot/test_launcher.py
python3 -I native/boot/test_gpio_guard.py
python3 -I native/boot/test_entry_guard.py
python3 -I native/boot/test_dapf_guard.py
python3 -I native/boot/test_framebuffer.py
python3 -I native/boot/test_hardware.py
tools/m1n1-client/run.sh native/boot/test_dapf_guard_adt.py
tools/m1n1-client/run.sh native/boot/test_launcher_adt.py
M1N1_SOURCE="$PWD/third_party/m1n1" tools/m1n1-client/run.sh native/boot/test_protocol.py
python3 -I native/boot/test_usb_dt.py
python3 -I native/boot/test_control_channel.py
python3 -I native/boot/test_kconfig_guard.py
python3 -I native/boot/test_ramroot.py
grep -x "$(cut -d' ' -f1,2 kernel/experiments/usb-gadget/authorized_keys)" <(
  python3 -I -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))["control_channel_authorized_key"].split()[:2]))' \
    build/native-boot038-download/ilinux-j716c-boot038/package-manifest.json)
)
```

Require the reviewed **37 + 10 + 6 + 16 + 5 + 19 + 2 + 6 + 1 = 102 cases PASS**,
plus the three boot036 suites (6 + 6 + 7 tests; their real-package cases skip
without the M5's `build/` directories) and the launcher's RAM-root profile
suite (30 tests), package PASS, 13 receipt files, the
clean client pin `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, and the last
command printing the M1's own public key (the package authorizes exactly that
key). Also confirm `build/control/m1-control` (the private half) is present
with mode 600. No kernel/REA setup on M1.

Archive **18,904,584 bytes**, SHA-256:
`09f5a5d723461bccfba3c29aacb084c3318203d074e522c1527d650186e05f70`.
Image **44,681,728 bytes**, SHA-256 (byte-identical to boot036):
`e0e531130a6f6bd7a5768393200a4c6e42f19a65c54c3deb390d53756edef3f7`.
Stage-B DT SHA-256 (byte-identical to boot036):
`a676087bda3cffa178604ca0cf128558d9ab2a620073314d054c79a685ecefa5`.
Stage-B initramfs **2,392,929 bytes** (boot036: 2,392,627), SHA-256:
`30800bdd96b68251dbf1ab704f2d241c1cb9cb5698dfc0e112aeb45d162cef39`.
SHA256SUMS digest:
`efba5795f6d2499ddf617b4a84051aa4a9253d0aca2e403daaca8c4af568a186`.
Everything except `initramfs-stage-b.cpio.gz` and `diag-init.c` is byte-identical
to boot036 (the packager enforces this). Git manifests are authoritative; stop
on disagreement.

Reviewed controller digests (also record the checked-out Git commit). Only
`launch.py` changed since attempt 16: commit `9ee6b2f` added the RAM-root
profile (`--profile ramroot`). Attempt 17 uses the default `stage-b` profile,
whose initramfs, fixed arguments, append check, confirmation string and
180-second deadline are unchanged (reviewed diff; `test_launcher.py` 37 and
`test_ramroot.py` 30 tests pass; the launcher verifies the boot036 package).
The other five files are unchanged.

* `native/boot/launch.py`: `4d55f0c9641f7c572129c7ed374aacd6b91656e41fbb54a7ce05b5d209af840b`
* `native/boot/gpio_guard.py`: `a3c038d036e2bc97679bd29d78d16e42b3db06d96775918abaeb01a53434a755`
* `native/boot/entry_guard.py`: `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713`
* `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
* `native/boot/fdt.py`: `ee577a08bb48242e84dbc50cd1f40a8d1f47a4d4481ca6dd6503829f53615ad3`
* `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

Before the attempt, run the read-only M1 preparation in
`tools/m1n1-client/control-channel-draft.md` ("Before the attempt"), plus the
**loaded-driver check** attempt 17 taught us (a bundle on disk proves nothing):

```sh
for id in com.apple.driver.usb.cdc.acm com.apple.driver.usb.cdc.ecm com.apple.driver.usb.cdc; do
  printf '%s: ' "$id"; kmutil showloaded --bundle-identifier "$id" --show all 2>/dev/null | tail -n +2 | wc -l
done
ls /dev/cu.usbmodem* 2>/dev/null; ifconfig -l > build/native-intake/ifaces-before.txt
```

Expect a nonzero count for all three (attempt 17 saw `cdc.acm` and `cdc.ecm`
loaded). Record the `cu.usbmodem*` names present before the handoff (m1n1's own
serial port is one of them) so the new one can be told apart.

Prepare fresh ignored `boot038-stage-b-attempt18.json`/`.md` records with the
source/procedure/controller/payload/receipt hashes. Push sanitized readiness
in `progress.md` and `coordination.md`, keeping native/live checks NOT RUN.
Tell the human when ready. M1 readiness plus the human's start suffice.

## One human-started RAM boot, filmed and reached over SSH

1. Both Macs on power, same direct cable. **Restart the M1 fresh shortly
   before the run**, keep it awake with `caffeinate -i`, close any serial tool.
   Film the M5 screen **before launching**, at **1080p or 4K**, phone fixed in
   a stand and never moved (portrait is fine). Frame the left part of the
   screen down to the bottom edge, where the newest lines start. Transfer the
   **original** file afterwards (AirDrop or cable, not Messages, which
   compresses it: attempt 16's copy was 320×568 and its digits were unreadable).
2. Human saves work, shuts down the M5, holds power for startup options and
   selects **iLinux Boot Lab → Continue**. Keep Macintosh HD as default.
3. After the human reports the proxy, invoke this **once**:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot038-download/ilinux-j716c-boot038 \
     --launch --device auto --confirm BOOT-J716C-RAM-DIAGNOSTIC
   ```

   The existing sanitized wrapper may call the same `main(argv)` once. No
   `m1n1.setup`, shell, separate handshake, reconnect or automatic retry. When
   it reports the handoff, the launcher has closed the serial port: do not
   reopen it.
4. Record the controller result as in attempt 16 (times, elapsed, exit, all
   preflight and final Hardware DT checks, GPIO exclusions, DAPF, framebuffer
   descriptor, kboot reply). Exit 0 is not Linux success.
5. **On the M5 screen**, expect the attempt-16 lines (PID 1, `online_cpus=1`,
   the genpd lines, `ladder complete: N domains released`, now **without any
   `atc0_`/`atc1_`/`atc2_` domain**) plus:
   * `[ctl] USB control channel: CDC-ACM log port + CDC-ECM per UDC, IPv6 link-local, SSH key only`
   * one `[ctl] port N: UDC <name> bound, ACM+ECM 1d6b:0104, interface usbX up, log on ttyGSn`
     line per port (three), and `[ctl] dropbear start 1`;
   * each heartbeat: `[ctl] port1 <state> ... | port2 ... | port3 ...`. The
     cabled port should reach `configured`, then show rising `rx=`/`tx=` and
     its `fe80::` address;
   * any `[ctl] log streamer for port N exited` line (report it; it restarts).
6. **On the M1, read-only** (N = the port whose state is `configured`; the
   draft has the full command lines). **Serial first**, it needs no network:
   * `ioreg -p IOUSB -l -w0 | grep -i -A3 iLinux` (the device, `bcdDevice` 0x0038,
     four interfaces: 2/2/1, 10/0/0, 2/6/0, 10/0/0);
   * `ls /dev/cu.usbmodem*`: one **new** name is the M5's ACM port. Read it
     into an ignored file, with no writes to it:
     `cat /dev/cu.usbmodemNEW > build/native-intake/attempt18-serial.txt`
     (no `stty`, no writes: the port is read only)
     and stop it with Ctrl-C after a minute. Expect the kernel log from
     `Linux version` onward, then the `[ctl]` and heartbeat lines live. That
     file is the `dmesg` even if networking fails.
   * `ifconfig -l` diffed against the "before" list, then `ifconfig enX`
     (look for `inet6 fe80::…%enX`);
   * `ping6 -c 3 fe80::69:6cff:fe69:6e0N%enX`;
   * SSH with `build/control/m1-control` (own `known_hosts` file under
     `build/control/`, `StrictHostKeyChecking=accept-new`) as root, and save to
     ignored `build/native-intake/`:
     `uname -a; cat /proc/cmdline; cat /sys/class/udc/*/state; cat /proc/interrupts; dmesg`.
   * Optional, once SSH works: the timed 256 MiB transfer from the draft.
   Keep the SSH session read-only: no writes to `/sys` or `/dev`, no module or
   configfs changes, no `reboot`/`poweroff`. If `enX` has no `inet6` address,
   report it and change nothing (adding a network service is a settings change
   that needs the human's approval).
7. Stop criterion: **10 minutes from handoff**, or earlier on a reset, a kernel
   panic, an M1 panic, or once the SSH captures above are saved. Then the human
   powers the M5 off (hold power), selects **Macintosh HD → Continue** and
   confirms the usual desktop return.

   | M5 screen | M1 | Meaning |
   |---|---|---|
   | a port reaches `configured`, rx/tx rise | new `enX`, ping and SSH work | **Control channel works**: the first remote shell into native Linux. Save `dmesg`. |
   | `configured` | kernel log arrives on `cu.usbmodemNEW` | **The ACM log port works**: the interrupt endpoint transmits (ACM's notification completes first). Save the serial capture even if ECM fails. |
   | `configured` | `cu.usbmodemNEW` exists but stays silent | the ACM data endpoint or its notification stalls; report `ioreg`'s interface lines and the `[ctl]` lines |
   | `configured` | device in `ioreg`, no new `cu.usbmodem*` and no `enX` | macOS bound neither driver: report which drivers `ioreg` shows under each interface |
   | `configured`, rx stays 0 | `enX` exists without `inet6` | macOS has not set up IPv6 on `enX`; serial still gives the log |
   | `dwc3 … -110`, `apple-dart … fault`, ports stay `not attached` | | not expected after attempt 17 (all PASS there); report verbatim |
   | reset or black screen | | as in attempts 14–16: note the time and the last lines |

8. Push the sanitized attempt-18 report and progress/coordination updates. Commit
   only checked excerpts of `dmesg`: no serial numbers, MACs other than the
   fixed `02:69:6c:69:6e/6f` gadget ones, or other identifiers. Never copy
   `/proc/device-tree` (m1n1 adds the target's serial there). Full logs and
   media stay local.

## Path toward Omarchy

Attempt 19 boots the Arch RAM root (Hyprland on `simpledrm`, software
rendering, one CPU) on boot038's kernel and DT (boot036's Image) through the RAM-root launcher
profile, and uses this link to measure it: the first visual Omarchy boot.
Keyboard and trackpad input is being reverse-engineered from macOS's own
drivers in parallel. See `roadmap.md`.

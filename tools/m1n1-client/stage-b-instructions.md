# Stage B — attempt 17 / boot036: the USB control channel

**M5 handoff, 2026-10-15.** Pull latest main with `git pull --ff-only`, preserving
local work and stopping on divergence. Read `coordination.md`, this file,
`native/boot/boot036-control-channel-2026-10-15.md` and
`tools/m1n1-client/control-channel-draft.md` (the M1-side network steps).
Attempt 16 is consumed and gave **the first stable native baseline**: boot035
ran the whole 74-domain release ladder and stayed alive past 108 s
(`native/boot/stage-b-2026-10-15-attempt16-result.md`).
**Native attempt 17 / boot036 / live checks NOT RUN at this handoff.**

**Continue the existing installation.** Installed boot021 m1n1 and clean client
pin remain unchanged. Do not repeat provisioning, Stage A, Recovery, macOS
installation, `bputil`, `kmutil`, partitioning or m1n1 installation. Keep
Macintosh HD at Full Security and as default. No volume/security changes, and
**no network-settings changes on the M1** without the human's approval.

## What changed and why

boot036 is boot035 plus a **USB network link into native Linux over this same
cable**, so the M1 can log in and read the kernel log instead of a video:

* **Kernel:** the boot034 tree with `USB_LIBCOMPOSITE=y` and `USB_CONFIGFS=y`
  (the 14 gadget lines from m to y, nothing else). The genpd fix and release
  ladder are unchanged. The shipped `kernel.config` is now the Image's own
  (the packager checks it against the config embedded in the Image).
* **Stage-B DT:** boot035's plus three `snps,dwc3` USB controllers in device
  mode at USB 2.0 speed, on the PHY state m1n1 leaves, with DMA through each
  port's second USB DART. All 39 power domains of USB-C ports 1–3 are
  **disabled**, so Linux never touches them and the release ladder skips them.
* **`/init`:** the same diagnostics and heartbeats, then one **CDC-EEM** USB
  network gadget per controller and **dropbear SSH** for root, **key-only**
  (the M1's key from commit `a6717b0`, fingerprint
  `SHA256:o7wtpNY0RUOIIGTyIJvspZFOetYFFG2oeMw5ecZc3yI`). Port N's Linux end is
  `fe80::69:6cff:fe69:6e0N` (IPv6 link-local only: no IPv4, no DHCP, no routes).
  Each heartbeat adds a `[ctl]` status line per port.
* m1n1, the generic initramfs, the full DT, the launcher and its fixed
  arguments are unchanged.

Offline: VM job 041 built everything; generic-VM liveness PASS; a VM self-test
with a virtual USB host PASS (enumeration, ping, SSH with a key, refusal
without it, an 8 MiB copy). The macOS host, the real dwc3 cores, the DARTs and
the PHY state are what this attempt tests.

## Offline intake before the human restarts

Download only private `native-j716c-boot036`; verify the archive against current
Git **before extraction**. Preserve every earlier package/receipt/result. Stop
on a mismatch. The following performs no live USB action.

```sh
(
set -e
mkdir -p build/native-boot036-download
if [ ! -f build/native-boot036-download/ilinux-j716c-boot036.tar.gz ]; then
  gh release download native-j716c-boot036 --repo nickyrice04/ilinux \
    --pattern ilinux-j716c-boot036.tar.gz --dir build/native-boot036-download
fi
(
  cd build/native-boot036-download
  shasum -a 256 -c ../../native/boot/archive-sha256.txt
  if [ ! -d ilinux-j716c-boot036 ]; then tar -xzf ilinux-j716c-boot036.tar.gz; fi
)
mkdir -p build/native-intake/receipts build/native-intake/results
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot036-download/ilinux-j716c-boot036 \
  --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
  > build/native-intake/receipts/boot036-attempt17.json
python3 -I native/boot/launch.py --package build/native-boot036-download/ilinux-j716c-boot036
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
grep -x "$(cut -d' ' -f1,2 kernel/experiments/usb-gadget/authorized_keys)" <(
  python3 -I -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))["control_channel_authorized_key"].split()[:2]))' \
    build/native-boot036-download/ilinux-j716c-boot036/package-manifest.json)
)
```

Require the reviewed **37 + 10 + 6 + 16 + 5 + 19 + 2 + 6 + 1 = 102 cases PASS**,
plus the three boot036 suites (6 + 6 + 7 tests; their real-package cases skip
without the M5's `build/` directories), package PASS, 13 receipt files, the
clean client pin `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, and the last
command printing the M1's own public key (the package authorizes exactly that
key). Also confirm `build/control/m1-control` (the private half) is present
with mode 600. No kernel/REA setup on M1.

Archive **18,902,541 bytes**, SHA-256:
`f09a00000925aea64a6ea7ab6dace05958d779d2367fc6aec233becc58ca71a3`.
Image **44,681,728 bytes**, SHA-256 (two VM builds gave the same bytes):
`e0e531130a6f6bd7a5768393200a4c6e42f19a65c54c3deb390d53756edef3f7`.
Stage-B DT SHA-256 (boot035 was `b1105bbf…86db`):
`a676087bda3cffa178604ca0cf128558d9ab2a620073314d054c79a685ecefa5`.
Stage-B initramfs **2,392,627 bytes** (boot035: 302,464), SHA-256:
`5f4b478b6005fe3f137733fbd8c361a4e1d16573b08af1334fc8837689b4b248`.
SHA256SUMS digest:
`4fbd64d401917f28ebb21841e284a864e1290286c1dd6d78ff973d0354f6442f`.
m1n1, the full DT and the generic initramfs are byte-identical to boot035.
Git manifests are authoritative; stop on disagreement.

Reviewed controller digests (unchanged from attempt 16; also record the
checked-out Git commit):

* `native/boot/launch.py`: `65ece2537fdb9ece0ed54dc234f8ee253bc2f3c44aac8c012014079b6366cfe0`
* `native/boot/gpio_guard.py`: `a3c038d036e2bc97679bd29d78d16e42b3db06d96775918abaeb01a53434a755`
* `native/boot/entry_guard.py`: `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713`
* `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
* `native/boot/fdt.py`: `ee577a08bb48242e84dbc50cd1f40a8d1f47a4d4481ca6dd6503829f53615ad3`
* `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

Before the attempt, run the read-only M1 preparation in
`tools/m1n1-client/control-channel-draft.md` ("Before the attempt"): the
`AppleUSBEEM.kext` check is already reported (macOS 26.0.1, 2/12/7); record
`ifconfig -l` before the handoff.

Prepare fresh ignored `boot036-stage-b-attempt17.json`/`.md` records with the
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
     --package build/native-boot036-download/ilinux-j716c-boot036 \
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
   * `[ctl] USB control channel: CDC-EEM gadget per UDC, IPv6 link-local, SSH key only`
   * one `[ctl] port N: UDC <name> bound, EEM 1d6b:0104, interface usbX up` line
     per port (three), and `[ctl] dropbear start 1`;
   * each heartbeat: `[ctl] port1 <state> ... | port2 ... | port3 ...`. The
     cabled port should reach `configured`, then show rising `rx=`/`tx=` and
     its `fe80::` address.
6. **On the M1, read-only** (N = the port whose state is `configured`; the
   draft has the full command lines):
   * `ioreg -p IOUSB -l -w0 | grep -i -A3 iLinux` (the device, `bcdDevice` 0x0036);
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
   | `dwc3 … -110` or a timeout during probe | no device | the core cannot soft-reset on the PHY state m1n1 left |
   | `apple-dart … fault` | device seen, traffic dies | DMA mapping wrong: the next step is both DART instances |
   | ports stay `not attached` / `default` | no device | no pull-up or no PHY: report the states |
   | `configured` | device in `ioreg`, no `enX` | macOS bound no EEM driver: report the `ioreg` interface lines |
   | `configured`, rx stays 0 | `enX` without `inet6` | macOS has not set up IPv6 on `enX` |
   | reset or black screen | | as in attempts 14–16: note the time and the last lines |

8. Push the sanitized attempt-17 report and progress/coordination updates. Commit
   only checked excerpts of `dmesg`: no serial numbers, MACs other than the
   fixed `02:69:6c:69:6e/6f` gadget ones, or other identifiers. Never copy
   `/proc/device-tree` (m1n1 adds the target's serial there). Full logs and
   media stay local.

## Path toward Omarchy

Attempt 18 boots the Arch RAM root (Hyprland on `simpledrm`, software
rendering, one CPU) on boot036's kernel and DT through the RAM-root launcher
profile, and uses this link to measure it: the first visual Omarchy boot.
Keyboard and trackpad input is being reverse-engineered from macOS's own
drivers in parallel. See `roadmap.md`.

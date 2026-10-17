# Stage B — attempt 21 / boot039: a bulk-only USB log port, read by the M1's own reader

**M5 handoff, 2026-10-16.** Pull latest main with `git pull --ff-only`, preserving
local work and stopping on divergence. Read `coordination.md`, this file,
`native/boot/boot039-bulk-log-2026-10-16.md` (what boot039 tests and how to read the
screen) and `tools/m1n1-client/bulk-log-reader-brief.md` (the reader you build).
Attempt 20 is consumed: the run-33 RAM root ran ten stable minutes with its benchmarks
on screen (`native/boot/stage-b-2026-10-16-attempt20-result.md`). Attempt 21 goes back
to the USB link, with the diagnostic Stage-B initramfs (the launcher's default
`stage-b` profile, as in attempts 16–18). It asks attempt 18's question with one
variable. **Native attempt 21 / boot039 / live checks NOT RUN at this handoff.**

**Continue the existing installation.** Installed boot021 m1n1 and clean client
pin remain unchanged. Do not repeat provisioning, Stage A, Recovery, macOS
installation, `bputil`, `kmutil` changes, partitioning or m1n1 installation. Keep
Macintosh HD at Full Security and as default. No volume, security or
network-settings changes. **Install nothing**: no Xcode or Command Line Tools
installation, no Homebrew, pip or third-party package, kext, system extension or
entitlement. The reader is built only with what this Mac already has.

## What changes and why

In attempt 18, macOS enumerated boot038's ACM + ECM device and selected configuration 1.
Then the device's control endpoint timed out four times, and no interface was ever
published (`native/boot/stage-b-2026-10-16-attempt18-result.md`). Both of those
functions add an interrupt-IN notification endpoint, and the ADT flags these ports
`ncm-interrupt-ep-disabled`. **boot039 removes every interrupt endpoint** and changes
nothing outside `/init`:

| | boot038 (attempt 18) | **boot039 (attempt 21)** |
|---|---|---|
| Function per controller | CDC-ACM + CDC-ECM | **`gser`, the kernel's generic serial function**: one vendor-class (`0xff`) interface, one bulk-IN and one bulk-OUT endpoint, **no interrupt endpoint**, no class requests |
| `bcdDevice` | `0x0038` | **`0x0139`** (configfs accepts only BCD; the RAM root is `0x0039`) |
| Kernel log to the M1 | over ACM, through macOS's driver | **over bulk IN, read by the M1's own read-only tool**; no macOS driver binds a vendor interface |
| Network, SSH | ECM, key-only dropbear | **none** (dropbear runs on loopback only) |
| M5 status line | UDC state, link, counters | **UDC state, the log counters, and per dwc3 core** the link state, SOF frame, pending events, interrupt count, last EP0 OUT/IN command and enabled endpoints' TRB rings, plus one line per core with its TX FIFO sizes |
| Image, config, DTs, m1n1, launcher | | byte-identical to boot036; only `initramfs-stage-b.cpio.gz` (its `/init`) and `diag-init.c` differ (packager-enforced) |

Offline, on the M5:

* VM job 041 PASS. It checks the kernel facts the status line relies on against the
  exact tree, and runs the status line on fixture trees, plain and under ASan+UBSan.
* Generic-VM liveness PASS.
* dummy_hcd self-test PASS. Linux's generic usb-serial driver, standing in for your
  reader, saw one vendor interface with two bulk endpoints and no interrupt endpoint.
  It read 1,926 kernel-log lines over bulk IN, and a probe it wrote was not echoed.

What macOS does with the device, and how the M5's real dwc3 cores behave, is what this
attempt tests.

## Offline intake before the human restarts

1. **The package.** Download only `native-j716c-boot039` (prerelease, public). Verify
   the archive against current Git **before extraction**. Preserve every earlier
   package, receipt and result, and stop on a mismatch. This performs no live USB
   action.

   ```sh
   (
   set -e
   mkdir -p build/native-boot039-download
   if [ ! -f build/native-boot039-download/ilinux-j716c-boot039.tar.gz ]; then
     gh release download native-j716c-boot039 --repo nickyrice04/ilinux \
       --pattern ilinux-j716c-boot039.tar.gz --dir build/native-boot039-download
   fi
   (
     cd build/native-boot039-download
     shasum -a 256 -c ../../native/boot/archive-sha256.txt
     if [ ! -d ilinux-j716c-boot039 ]; then tar -xzf ilinux-j716c-boot039.tar.gz; fi
   )
   mkdir -p build/native-intake/receipts build/native-intake/results
   tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
     build/native-boot039-download/ilinux-j716c-boot039 \
     --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
     > build/native-intake/receipts/boot039-attempt21.json
   python3 -I native/boot/launch.py --package build/native-boot039-download/ilinux-j716c-boot039
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
   python3 -I native/boot/test_boot039_package.py
   python3 -I native/boot/test_ramroot.py
   grep -x "$(cut -d' ' -f1,2 kernel/experiments/usb-gadget/authorized_keys)" <(
     python3 -I -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))["control_channel_authorized_key"].split()[:2]))' \
       build/native-boot039-download/ilinux-j716c-boot039/package-manifest.json)
   )
   ```

   Require all of the following:
   * the reviewed **37 + 10 + 6 + 16 + 5 + 19 + 2 + 6 + 1 = 102 cases PASS**;
   * the USB suites `test_usb_dt.py` (6), `test_control_channel.py` (10) and
     `test_kconfig_guard.py` (7). Their real-package cases skip without the M5's
     `build/` directories, and `test_boot039_package.py` (8) skips entirely for the
     same reason;
   * `test_ramroot.py` (30);
   * `Package PASS`, a receipt with 13 files, and the clean client pin
     `57a9339ffd1876e78297b17d34dece8cff8fa1ba`;
   * the last command printing the M1's own public key (the package's dropbear still
     authorizes exactly that key, though this attempt has no network).

   | | Bytes | SHA-256 |
   |---|---:|---|
   | archive `ilinux-j716c-boot039.tar.gz` | 18,915,359 | `b85c8d45552f21de475e46009599a06b3d723b44e66cbc0087ff5fdf00b57d51` (GitHub's asset digest equals it) |
   | SHA256SUMS | | `883464897e2e3233a96ed27c8af0e50d73474edf107f89ec9c40ab84e3684df5` |
   | `Image` (= boot036) | 44,681,728 | `e0e531130a6f6bd7a5768393200a4c6e42f19a65c54c3deb390d53756edef3f7` |
   | `t6050-j716c-stage-b.dtb` (= boot036) | 62,043 | `a676087bda3cffa178604ca0cf128558d9ab2a620073314d054c79a685ecefa5` |
   | `initramfs-stage-b.cpio.gz` (boot036's apart from `/init`) | 2,397,729 | `19e5e366f427de97d8f506d3c0e084837790ae0b01a2a1d01affe4b5096cc44c` |
   | `diag-init.c` | 29,064 | `8ba20c9352694df9dc99a13ab0f83980ba5508c3bf688cc8649ce8da4c69d7c5` |

   Git manifests are authoritative; stop on disagreement.

2. **Reviewed controller digests**, unchanged since attempt 18 (record the checked-out
   Git commit too). Attempt 21 uses the default `stage-b` profile: the diagnostic
   initramfs, the fixed arguments, the append check, `BOOT-J716C-RAM-DIAGNOSTIC` and
   the 180-second deadline, all as in attempts 16–18.

   * `native/boot/launch.py`: `4d55f0c9641f7c572129c7ed374aacd6b91656e41fbb54a7ce05b5d209af840b`
   * `native/boot/gpio_guard.py`: `a3c038d036e2bc97679bd29d78d16e42b3db06d96775918abaeb01a53434a755`
   * `native/boot/entry_guard.py`: `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713`
   * `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
   * `native/boot/fdt.py`: `ee577a08bb48242e84dbc50cd1f40a8d1f47a4d4481ca6dd6503829f53615ad3`
   * `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

3. **Build the read-only bulk-log reader** from `tools/m1n1-client/bulk-log-reader-brief.md`,
   with only what this Mac already provides:

   ```sh
   xcode-select -p && xcrun --show-sdk-path && clang --version
   ls "$(xcrun --show-sdk-path)/System/Library/Frameworks/IOUSBHost.framework/Headers/IOUSBHostPipe.h"
   ```

   If any of these fails, **stop and report**. Installing the Command Line Tools is a
   host install that needs the user's approval, and so is accepting an installer
   prompt. Otherwise:
   * Write `tools/m1n1-client/bulk-log-reader.m` (Objective-C, IOUSBHost) as the brief
     specifies: the fixed identity, the interface only, the bulk-IN pipe only, never a
     write, and the fail-safe table.
   * Write its static check `tools/m1n1-client/test_bulk_log_reader.py`. It fails if the
     source names any forbidden call or the OUT direction.
   * Build to the ignored `build/control/bulk-log-reader`:
     `clang -fobjc-arc -O2 -Wall -Wextra -framework Foundation -framework IOKit -framework IOUSBHost`.
   * Test it offline as the brief says:
     * the static check PASS;
     * `--dry-run` with no M5 attached exits 2 after `--wait`, writing only the
       sidecar;
     * `--dry-run` with m1n1's device attached (`1209:316d`) also finds nothing;
     * an existing `--out` and a second instance are refused before any IOKit call;
     * a short `--seconds` run and Ctrl-C both stop cleanly.

   Record the source, the static check and the binary's SHA-256 in the readiness
   record. Commit the source and its test with the readiness report. The binary stays
   ignored.

4. **Read-only USB picture before the handoff:** `ioreg -p IOUSB -l -w0` saved to the
   ignored `build/native-intake/attempt21-ioreg-before.txt`. There should be no
   `1d6b:0104` device; m1n1's own is `1209:316d`.

Prepare fresh ignored `boot039-stage-b-attempt21.json`/`.md` records with the
source/procedure/controller/payload/receipt hashes and the reader's digests. Push
sanitized readiness in `progress.md` and `coordination.md`, keeping native/live
checks NOT RUN. Tell the human when ready. M1 readiness plus the human's start
suffice.

## One human-started boot, filmed, read by the reader

1. Both Macs on power, same direct cable. **Restart the M1 fresh**, keep it awake with
   `caffeinate -i`, and **re-seat the cable after the restart**. In attempts 17 and 18
   the read-only gate saw no device until the cable was re-seated. Run the read-only USB
   gate and close any serial tool. Keep the M1 unlocked: macOS's accessory check holds
   a new USB device until it is authorized.
2. **Start recording before the launch command**, at 1080p or 4K. Put the phone in a
   stand that does not move for the whole run, framing **the whole screen** square-on.
   The `[ctl]` status line is long and wraps, and its dwc3 fields are the evidence if
   USB fails, so the bottom lines must be legible. Dim what the glossy panel reflects.
   Transfer the original file afterwards (AirDrop or cable, not Messages).
3. Human saves work, shuts down the M5, holds power for startup options and selects
   **iLinux Boot Lab → Continue**. Keep Macintosh HD as default.
4. Start the read-only host USB log capture with the same filter as attempt 18. It
   recorded attempt 18's EP0 timeouts, so it decides the main question.
5. After the human reports `Running proxy...` and the gate passes, invoke this
   **once**:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot039-download/ilinux-j716c-boot039 \
     --launch --device auto --confirm BOOT-J716C-RAM-DIAGNOSTIC
   ```

   The existing sanitized wrapper may call the same `main(argv)` once. There is no
   `m1n1.setup`, shell, separate handshake, reconnect or automatic retry. When it reports
   the handoff, the launcher has closed the serial port: do not reopen it.
6. **Right after the handoff, start the reader once:**
   `build/control/bulk-log-reader --out build/native-intake/attempt21-bulk-log.bin`.
   It waits up to 120 s for the device and stops by itself after 600 s or when the
   device goes away. Do not restart it, and do not run anything else against the
   device. Save `ioreg -p IOUSB -l -w0` and
   `ioreg -p IOService -l -w0 -r -c IOUSBHostInterface` at about +5 s and +60 s to
   ignored files.
7. Record the controller result as in attempts 16–18: times, elapsed, exit, every gate,
   the final Hardware DT checks, GPIO exclusions, DAPF, framebuffer descriptor and kboot
   reply. Exit 0 is not Linux success.
8. **On the M5 screen**, expect the attempt-18 baseline: PID 1, `online_cpus=1`, the
   genpd lines, and `ladder complete: N domains released` with no `atc0_`-`atc2_`
   domain. In addition, expect:
   * `[ctl] debugfs on /sys/kernel/debug: dwc3 state in every status line`;
   * `[ctl] USB control channel: GSER bulk-only kernel log port per UDC, no interrupt endpoint, no network`;
   * one `[ctl] port N: UDC <name> bound, GSER bulk-only 1d6b:0104 bcdDevice 0x0139, no interrupt endpoint, log on ttyGSn`
     line per port (three), then `[ctl] dropbear start 1`;
   * at heartbeat 000, once per port: `[ctl] portN dwc3: core 0x…, N endpoints (M IN),
     MDWIDTH W; TX FIFO words 0:… 1:… …; RX FIFO words …`. **Read these numbers from the
     video.** A TX FIFO of 0 or near 0 for endpoints 2–4 would point at a FIFO cause for
     attempt 18;
   * each heartbeat:
     `[ctl] port1 <state> log <n>L <n>B q<n> dwc3 <link> f<n> ev<n> irq<n> ep0 o:<cmd> i:<cmd> 1out bulk h<n> d<n> 1in bulk h<n> d<n> | port2 … | port3 …`.
     The legend is in `native/boot/boot039-bulk-log-2026-10-16.md`. In short:
     * `B` rising and `q` near 0 mean your reader is draining the port;
     * `f` changing means the host sends SOFs;
     * `ev` above 0 means events are waiting;
     * `*` after a command means it is stuck active;
     * `STOPPED`, `HALTED`, `BUSERR` or `INTERRUPT` should never appear;
   * any `[ctl] dwc3 status reader … did not finish in 2 s` or `[ctl] log streamer for
     port N exited` line (report it; the heartbeat goes on).
9. Stop criterion: **10 minutes from the handoff**, or earlier on a reset, a kernel
   panic or an M1 panic. Keep filming until then: if USB fails, the status lines are the
   record. Then the human powers the M5 off (hold power), selects **Macintosh HD →
   Continue** and confirms the usual desktop return.

   | M5 screen | M1 | Meaning |
   |---|---|---|
   | port `configured`, `B` rising, `q` near 0, `1in` dequeue advancing | interface published, the reader streams the log, no EP0 timeout in the host log | **The bulk path works.** Attempt 18's wedge needed something only ACM/ECM had: the interrupt endpoint (Likely) or their CDC descriptors and requests, the second function, or IN endpoints 2–4. Save the capture; read the FIFO lines. |
   | port `configured`, `q8192`, `1in bulk h1+` with `d` frozen, `f` changing | interface published; the reader opens it, reads only time out | bulk-IN transfers queue but never complete: an IN-path problem (FIFO 1, DMA), not EP0; look for `BUSERR` |
   | the log flowed, then `q` climbs and `d` stops | bytes, then silence | the device stopped transmitting mid-stream: read the dwc3 line at that moment |
   | **EP0 timeouts again** after the configuration | no interface, or the reader cannot open or read | **Not the interrupt endpoint.** Read the dwc3 line from the timeout's time on: `ev` > 0 with `irq` frozen = events unhandled (interrupt path); `irq` rising, `ev0` = the core sees traffic and the reply is lost; `*` = a command never finished; `STOPPED`/`HALTED` = the controller stopped; `BUSERR` = DMA (DART) |
   | port `configured` | device seen, no interface, no timeouts | macOS did not publish the interface: report the driver at device level from `ioreg` |
   | `[ctl] dwc3 status reader … did not finish in 2 s` | | a debugfs read blocked: itself evidence of a driver-level hang |
   | port stays `default` / `addressed` | device not configured | enumeration stops earlier than in attempt 18 |
   | `dwc3 … -110`, `apple-dart … fault`, ports stay `not attached` | | not expected after attempts 17–18: report verbatim |
   | a panic at the first status line (≈ 3.5 s), a reset or a black screen | | as in attempts 14–16; a panic at the first status line points at the debugfs reads. Note the time and the last lines |
   | controller rejection (upload, DT or argument gate) | | report the line verbatim; no retry |

10. Push the sanitized attempt-21 report and the progress/coordination updates. The
    reader's capture and sidecar, the host USB log, `ioreg` dumps and the media stay
    local. Commit only excerpts, after checking them for serial numbers, MAC addresses
    and other identifiers. Never copy `/proc/device-tree`: m1n1 adds the target's
    serial there.

## Path toward Omarchy

Attempt 20 put a stable Omarchy desktop on the M5 screen, view-only. A working USB
link turns that into a machine the M1 can reach. If boot039's bulk path works, the
next candidate carries networking over bulk endpoints only, for SSH into the RAM root
and proper measurements. Then come the built-in keyboard and trackpad (the MTP input
work and the E1 read-only probe), then storage and efficiency. See `roadmap.md`.

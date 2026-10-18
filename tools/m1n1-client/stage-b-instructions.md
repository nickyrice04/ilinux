# Stage B — attempt 23 / boot040: attempt 21's bulk-only log port with the DART fault made visible

**M5 handoff, 2026-10-18.** Pull latest main with `git pull --ff-only`, preserving local work
and stopping on divergence. Read `coordination.md`, this file,
`native/boot/boot040-dart-fault-2026-10-18.md` (what boot040 adds and how to read the screen),
`kernel/experiments/usb-gadget/dart-diag/README.md` (the DART audit and the fix candidates) and
`native/boot/stage-b-2026-10-18-attempt21-result.md`. Attempt 22 is consumed: the installer-built
Omarchy desktop came up on boot035 and stayed up for the filmed ten minutes
(`native/boot/stage-b-2026-10-18-attempt22-result.md`). Attempt 23 returns to the USB link with the
launcher's default `stage-b` profile and the diagnostic Stage-B initramfs, as attempt 21 did.
**Native attempt 23 / boot040 / live checks NOT RUN at this handoff.** The M1's reader needs no
change (attempt 21: it opened, read and stopped cleanly).

**Continue the existing installation.** Installed boot021 m1n1 and clean client pin remain
unchanged. Do not repeat provisioning, Stage A, Recovery, macOS installation, `bputil`, `kmutil`
changes, partitioning or m1n1 installation. Keep Macintosh HD at Full Security and as default.
No volume, security or network-settings changes. Install nothing.

## What changes and why

Attempt 21 (boot039) answered attempt 18's question: with no interrupt endpoint, EP0 stayed
healthy for ten minutes and the M1 read 36,909 bytes over bulk IN. Then port 1's dwc3 flagged a
bus error (`BUSERR`), its interrupts froze, and Linux disabled IRQ 43 (`apple-dart fault handler`,
port 1's DART) after an unreported interrupt storm. boot040 changes nothing about the link and
adds diagnostics only, so this film shows **the first fault** instead of the storm:

| | boot039 (attempt 21) | **boot040** |
|---|---|---|
| Gadget | `gser`, bulk IN + bulk OUT, `bcdDevice 0x0139` | **same** |
| Stage-B DT, kernel config, m1n1, generic files | boot036's | **same** (packager-enforced) |
| Image | boot036's | **+ the apple-dart fault-report patches**: part 1, the t8110 fault handler prints its raw registers when the interrupt arrives without the error flag, acknowledges what is pending, and names each DART instance at probe; part 2, a DART whose PARAMS3 reports version 2.2 or later (macOS's own driver switches its fault-register layout there, per the REA of this Mac's DART driver) is reported and acknowledged in that layout, with a bound of 256 acknowledged interrupts; inert below 2.2. Translation and protection untouched |
| `/init` | dwc3 state per heartbeat | **+** the failing DMA address at a bus error (`BUSERR@<hex>`), the DART identity per port (instance, stream, fault IRQ, the sibling instance the DT leaves out), a read-only DART register snapshot of both instances at bind and at the first bus error, a short `[usbN]` line per port each heartbeat (about 100 columns), and the log streamer stopped for good at the first bus error |
| M1 side | the read-only bulk-log reader | **same binary, same procedure** |

Offline, on the M5: VM job 041 PASS (kernel facts incl. the DART facts, the patched DART object
with W=1, the status fixture plain and under ASan+UBSan), the generic-VM liveness and the dummy_hcd
self-test PASS, the package rebuilds byte-identically and refuses every other payload change.

## Offline intake before the human restarts

1. **The package.** Download only `native-j716c-boot040` (prerelease, public; GitHub's asset digest equals the table's).
   Verify the archive against current Git **before extraction**; preserve every earlier package,
   receipt and result; stop on a mismatch. No live USB action.

   ```sh
   (
   set -e
   mkdir -p build/native-boot040-download
   if [ ! -f build/native-boot040-download/ilinux-j716c-boot040.tar.gz ]; then
     gh release download native-j716c-boot040 --repo nickyrice04/ilinux \
       --pattern ilinux-j716c-boot040.tar.gz --dir build/native-boot040-download
   fi
   (
     cd build/native-boot040-download
     shasum -a 256 -c ../../native/boot/archive-sha256.txt
     if [ ! -d ilinux-j716c-boot040 ]; then tar -xzf ilinux-j716c-boot040.tar.gz; fi
   )
   mkdir -p build/native-intake/receipts build/native-intake/results
   tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
     build/native-boot040-download/ilinux-j716c-boot040 \
     --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
     > build/native-intake/receipts/boot040.json
   python3 -I native/boot/launch.py --package build/native-boot040-download/ilinux-j716c-boot040
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
   python3 -I native/boot/test_boot040_package.py
   python3 -I native/boot/test_ramroot.py
   python3 -I kernel/experiments/usb-gadget/dart-diag/test_dart_diag.py \
     build/native-boot040-download/apple-dart-check.c 2>/dev/null || true   # see note below
   grep -x "$(cut -d' ' -f1,2 kernel/experiments/usb-gadget/authorized_keys)" <(
     python3 -I -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))["control_channel_authorized_key"].split()[:2]))' \
       build/native-boot040-download/ilinux-j716c-boot040/package-manifest.json)
   )
   ```

   (The `test_dart_diag.py` line needs a patched `apple-dart.c`, which the package does not carry;
   the M5's job 041 ran it. Skip it unless you have the Asahi tree at `77cb8f24` to apply
   `kernel/experiments/usb-gadget/dart-diag/apply.py` to; then point the test at that file.)

   Require: the reviewed **102** controller cases plus `test_ramroot.py` (**44**) PASS, the USB suites
   `test_usb_dt.py` (6), `test_control_channel.py` (13; its real-package cases skip without the M5's
   `build/` directories) and `test_kconfig_guard.py` (7), `test_boot040_package.py` (10, skips without
   the extracted packages), `test_ramroot.py`, `Package PASS`, a receipt with 13 files, the clean client
   pin `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, and the last command printing the M1's own public key.

   | | Bytes | SHA-256 |
   |---|---:|---|
   | archive `ilinux-j716c-boot040.tar.gz` | 18,921,232 | `1d7f5c8de17608b21eb9d047d4ee8470c785e3d2ba252fc7b156b4aee46166cf` |
   | SHA256SUMS | | `4ee2f1f343a2539e18e5e19f9c4ed190e8e730ad685933e2f238bbc65174e4c9` |
   | `Image` (boot036's tree and config + the two DART fault-report patches) | 44,681,728 | `a53d1d47467480d4b56d87c7b1365e9a5c28fd9ee9e5f0164a3e734f85526ad9` |
   | `kernel.config` (= boot036-039) | 321,820 | `caa8e71a095aca35024688ced8025a8cc03925e641e3988587627d7f5f3e3887` |
   | `t6050-j716c-stage-b.dtb` (= boot036-039) | 62,043 | `a676087bda3cffa178604ca0cf128558d9ab2a620073314d054c79a685ecefa5` |
   | `initramfs-stage-b.cpio.gz` (boot039's apart from `/init`) | 2,402,470 | `59bc2afcb1db341bad739efdddef43b097011aed04f70e678f76e9ccc5acaad6` |
   | `diag-init.c` | 45,907 | `58c68268b2f05ad2d5f5f1e25478814ec019211a405342e7c9cc256c359e22de` |

   Git manifests are authoritative; stop on disagreement.

2. **Reviewed controller digests** (record the checked-out commit): the `stage-b` profile, the
   fixed arguments, the append check, `BOOT-J716C-RAM-DIAGNOSTIC` and the 180-second deadline, as in
   attempts 16-18 and 21. The committed launcher is the attempt-22 one (the `omarchy` profile added);
   the `stage-b` profile in it is unchanged.

   * `native/boot/launch.py`: `b14ec7a1d6957197d808609a9c4888995598e23ce4c63707db2a58476a9e0740`
   * `native/boot/gpio_guard.py`: `a3c038d036e2bc97679bd29d78d16e42b3db06d96775918abaeb01a53434a755`
   * `native/boot/entry_guard.py`: `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713`
   * `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
   * `native/boot/fdt.py`: `ee577a08bb48242e84dbc50cd1f40a8d1f47a4d4481ca6dd6503829f53615ad3`
   * `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

3. **The reader** is attempt 21's `build/control/bulk-log-reader` (built from the committed
   `tools/m1n1-client/bulk-log-reader.m`). Re-run its static check and `--dry-run` with no M5
   attached; record its digest. No change is needed.

4. **Read-only USB picture before the handoff:** `ioreg -p IOUSB -l -w0` to the ignored
   `build/native-intake/boot040-ioreg-before.txt`. No `1d6b:0104`; m1n1's own device is `1209:316d`.

Prepare the ignored records, push sanitized readiness in `progress.md` and `coordination.md`
(native/live NOT RUN), tell the human when ready.

## One human-started boot, filmed, read by the reader

Attempt 21's procedure notes are folded in (steps 1, 5 and 6).

1. Both Macs on power, same direct cable. **Restart the M1 fresh**, keep it awake with
   `caffeinate -i`, **re-seat the cable after the restart**, run the read-only USB gate. **If the gate
   sees no device even after re-seats, boot the M5 into the iLinux Boot Lab again**: in attempt 21 the
   M5 was invisible after the fresh M1 restart until a second Boot Lab boot (two re-seats alone did
   not help). Keep the M1 unlocked.
2. **Start recording before the launch command**, 1080p or better 4K, phone in a stand, the whole
   screen square-on, reflections dimmed. The evidence now sits in **short lines** (`[usbN] …`,
   `[usbN] dartN …`, the `apple-dart …` kernel lines): frame so the left two thirds of the console are
   as large as possible if you cannot do 4K. Transfer the original file afterwards (AirDrop or cable).
3. Human saves work, shuts down the M5, holds power for startup options, selects **iLinux Boot Lab →
   Continue**. Keep Macintosh HD as default.
4. Start the read-only host USB log capture with attempt 18's filter.
5. After `Running proxy...` and the gate passes, invoke **once**:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot040-download/ilinux-j716c-boot040 \
     --launch --device auto --confirm BOOT-J716C-RAM-DIAGNOSTIC
   ```

   No `m1n1.setup`, shell, handshake, reconnect or retry. After the handoff the serial port is
   closed: do not reopen it. **Expect a macOS prompt to allow the new USB accessory within the first
   seconds** (attempt 21: it appeared early and was accepted quickly; the reader waits up to 120 s for
   the device, so a slow answer is fine). Accept it.
6. **Right after the handoff, start the reader once:**
   `build/control/bulk-log-reader --out build/native-intake/boot040-bulk-log.bin`. It stops by
   itself after 600 s or when the device goes away. Save `ioreg -p IOUSB -l -w0` and
   `ioreg -p IOService -l -w0 -r -c IOUSBHostInterface` at about +5 s and +60 s to ignored files.
7. Record the controller result as in attempts 16-21. Exit 0 is not Linux success.
8. **On the M5 screen**, expect attempt 21's baseline (PID 1, `online_cpus=1`, the genpd lines,
   the ladder) and, new:
   * at ≈ 2-3 s, three `apple-dart 2a2f80000.iommu: t8110-class DART v<maj>.<min>: PARAMS …,
     N clients, fault IRQ <n>, ERROR 0x…` lines (and `2aaf80000`, `382f80000`): **read `<n>`, the
     version and PARAMS** (they say the VA/PA widths and how many streams). **The version decides
     the attempt's second question**: `v2.2` or later means Linux's fault handling was blind on
     this DART and part 2 is active (a `v2.2 fault layout: PENDING … (before reset)` line follows);
     below 2.2 part 2 did nothing;
   * after each `port N: UDC … bound` line: `[usbN] <udc> irq 58b(<a>) dart1 2a2f80000 sid 1 fault
     irq 58f(<n>); dart0 2a2f00000 not in DT`, then `[ctl] port N: reading DART registers at …`, then
     **four register lines** (`[usbN] dart0 @… p1 … p4 … prot … en …`, `[usbN] dart0 err … strm … addr …
     tcr …/… ttbr …/… tlb … mask …`, and the same two for `dart1`). **Read them**: they are the state
     before any traffic;
   * each heartbeat: `[diag] heartbeat NNN`, then one short line per port, `[usb1] configured On f<n>
     irq<n> dart<n> <B>B q<n> 1o h<n> d<n> 1i h<n> d<n>`, then the long `[ctl]` line as before.
     `dart<n>` is the DART fault-interrupt count: it should stay small;
   * **if a bus error happens**: the short line ends in `BUSERR@<hex>` (the failing DMA address), the
     next lines are `[ctl] port N: dwc3 bus error at DMA address 0x…: log streamer stopped; …` and the
     two `err …` register lines per instance again (three on a version ≥ 2.2 DART: the `v2.2 pend …`
     line has the pending streams and the error blocks), and around the same time the kernel prints
     one of: `apple-dart …: translation fault: … at 0x… (fault #1, IRQ <n>, streams …)` (pre-2.2
     layout), `apple-dart …: translation fault (v2.2 layout): stream N code C (name) level L at 0x…
     (fault #1, IRQ <n>)` (part 2), or `apple-dart …: fault IRQ <n> without the error flag (#1): ERROR
     0x… MASK 0x… STREAMS 0x… 0x… ADDR 0x… TLB_CMD 0x…` / `… (v2.2 layout) with nothing pending (#1):
     PENDING 0x… MASK 0x… PROT_STATUS 0x… CTRL 0x… TLB_CMD 0x…` (up to four, then every 25,000th).
     **Read every digit of these lines**; they are the result of the attempt. `irq <n>: nobody cared`
     may still follow if the handler found nothing pending; `fault IRQ <n> acknowledged 256 times;
     disabling it` means the acknowledgement is incomplete for this DART;
   * any `[ctl] dwc3 status reader … did not finish in 2 s` line (report it; the heartbeat goes on).
9. Stop criterion: **10 minutes from the handoff**, or earlier on a reset, a kernel panic or an M1
   panic. Then the human powers the M5 off (hold power), selects **Macintosh HD → Continue** and
   confirms the desktop return.

   | M5 screen | M1 | Meaning |
   |---|---|---|
   | short lines with `B` rising, `q` near 0, `1i d` advancing, no `BUSERR`, `dart<n>` small | the reader streams the whole log, no timeouts | **the bulk path works this time**; attempt 21's fault did not recur: report the full capture (it now holds the `[usbN]` and DART lines too) and treat the fault as intermittent (then candidate D in the dart-diag README matters) |
| `BUSERR@<addr>` + `translation fault … at <addr2> … stream:<s> code:… (<name>)` with `addr == addr2` | bytes, then silence | the DART in the DT faulted on that DMA: `NO TTBR`/`NO PGD`/`NO PMD`/`NO PTE` = a mapping or table-depth problem at that IOVA (candidate C if the address is above 2^36; else the page-table path), `READ/WRITE FAULT` = a protection bit. The IRQ stays alive: later faults print too |
| probe line `v2.2` or later + `BUSERR@<addr>` + `translation fault (v2.2 layout): stream <s> code <c> (<name>) level <l> at <addr2>` and **no** `nobody cared` | bytes, then silence | **candidate B confirmed**: Linux was blind to this DART's faults until part 2; the fault itself (code, level, address) is now the lead, read as in the row above. If the fault then recurs without stopping the link, the bulk path may even keep going: watch `B` and `1i d` |
| probe line `v2.2` or later + `fault IRQ <n> acknowledged 256 times; disabling it` | silence | the acknowledgement sequence is incomplete for this DART (open item T6 of `rea-dart-2026-10-18.md`: bit 15 and the 0x600 write after flushes); report the preceding fault lines verbatim |
| `BUSERR@<addr>` + `fault IRQ <n> without the error flag … ERROR 0x0 … STREAMS 0x0 0x0` + `nobody cared` | silence | instance 1 did not raise the line: look at `dart0`'s `err`/`strm` lines after the bus error; a `FAULT` or stream bit there = the sibling instance carries traffic: **candidate A** (Asahi's two-DART wiring) |
| `BUSERR@<addr>` + `fault IRQ … without the error flag … ERROR 0x<nonzero>` | silence | instance 1 reports an error in another layout: **candidate B**; the raw words decide the layout |
| `BUSERR` without any `apple-dart` line and `dart<n>` unchanged | silence | the bus error is not a DART fault (fabric, GAPF/PS_PROT, an address outside the DART's path): compare `BUSERR@` with the DART snapshot's `ttbr` and the IOVA range |
| `dart0` snapshot: `regs n/a (…)`, or the M5 resets right after `reading DART registers` | | the sibling instance is not readable through `/dev/mem` (power or protection): report the exact line; the dwc3 state line still runs |
| EP0 timeouts, `not attached`, `-110`, a panic at the first status line | | as attempt 21's table; report verbatim |

10. Push the sanitized report and the progress/coordination updates. The capture, sidecar, host USB
    log, `ioreg` dumps and media stay local; commit only checked excerpts. Never copy
    `/proc/device-tree`.

## Path toward Omarchy

Attempt 22 put the installer-built Omarchy desktop on the M5, view-only and offline. A working USB
link turns it into a machine the M1 can reach: the SSH byte pipe and web proxy are VM-proven (job
046), and a link-enabled Omarchy root pinned to boot040's kernel is being prepared in the VM.
boot040 names the fault in that link and carries the one fix candidate that selects itself by the
DART's version; whichever candidate the film selects is the next boot, and then the combined boot:
Omarchy on the fixed USB kernel, reached over SSH, with agents running on the machine.

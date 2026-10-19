# Stage B — attempt N / boot041 (DRAFT): boot040 with both DART instances per dwc3 core in the Stage-B DT

**Draft, 2026-10-18, M5 side session. Not a handoff:** nothing here is committed or released; the
attempt number, the release and the order relative to the attempt-24 draft
(`stage-b-attempt24-draft.md`, the Omarchy root with the link) are the M5's to decide at the handoff,
which restates the digests below. Read `coordination.md`, this file,
`native/boot/boot041-two-darts-2026-10-18.md` (what boot041 changes and how to read the screen),
`native/boot/stage-b-2026-10-18-attempt23-result.md` (why) and `kernel/experiments/usb-gadget/dart-diag/README.md`
(the fix candidates). **Native boot041 / live checks NOT RUN.** The M1's reader needs no change.

**Continue the existing installation.** Installed boot021 m1n1 and clean client pin remain
unchanged. Do not repeat provisioning, Stage A, Recovery, macOS installation, `bputil`, `kmutil`
changes, partitioning or m1n1 installation. Keep Macintosh HD at Full Security and as default.
No volume, security or network-settings changes. Install nothing.

## What changes and why

Attempt 23 (boot040) showed the USB DART is version 2.4 and, at the first bus error, the fault pending
on DART instance 0, which the Stage-B DT left out: Linux had never reset or programmed it and had no
handler for it on the shared fault interrupt (instance 1's handler found nothing pending through the
whole storm). boot041 gives each dwc3 core both instances, the way every Asahi device tree does, and
changes nothing else that the hardware sees:

| | boot040 (attempt 23) | **boot041** |
|---|---|---|
| Stage-B DT | boot036's: each dwc3 core `iommus = <dart1 1>`, instance 0 disabled | **each core `iommus = <dart0 0>, <dart1 1>`; instance 0 enabled without `power-domains`, as instance 1 was; nothing else** (packager-enforced exact delta) |
| Image | boot036's tree and config + the two apple-dart fault-report patches | **byte-identical** (`a53d1d47…`; the attempt-24 Omarchy root is pinned to it) |
| Kernel config, m1n1, generic files, gadget | boot039's | **same** (packager-enforced) |
| `/init` | DART identity, register snapshot, short `[usbN]` lines | **same lines, plus** both instances in the identity line (with the number of fault handlers on the line), a setup line at bind (`: both set up`), and both instances' pending-fault words in the short line (`pend <instance 0>/<instance 1>`) |
| M1 side | the read-only bulk-log reader | **same binary, same procedure** |

Offline, on the M5: VM job 041 PASS (the Image reproduced byte for byte, kernel facts incl. the two-DART
facts, the status fixture plain and under ASan+UBSan, the DT with its three expected schema findings),
the generic-VM liveness and the dummy_hcd self-test PASS, the package rebuilds byte-identically and
refuses every other payload change, and the committed launcher passes it offline.

## Offline intake before the human restarts

1. **The package.** Download only `native-j716c-boot041` (the release name the handoff will confirm).
   Verify the archive against current Git **before extraction**; preserve every earlier package,
   receipt and result; stop on a mismatch. No live USB action.

   ```sh
   (
   set -e
   mkdir -p build/native-boot041-download
   if [ ! -f build/native-boot041-download/ilinux-j716c-boot041.tar.gz ]; then
     gh release download native-j716c-boot041 --repo nickyrice04/ilinux \
       --pattern ilinux-j716c-boot041.tar.gz --dir build/native-boot041-download
   fi
   (
     cd build/native-boot041-download
     shasum -a 256 -c ../../native/boot/archive-sha256.txt
     if [ ! -d ilinux-j716c-boot041 ]; then tar -xzf ilinux-j716c-boot041.tar.gz; fi
   )
   mkdir -p build/native-intake/receipts build/native-intake/results
   tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
     build/native-boot041-download/ilinux-j716c-boot041 \
     --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
     > build/native-intake/receipts/boot041.json
   python3 -I native/boot/launch.py --package build/native-boot041-download/ilinux-j716c-boot041
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
   python3 -I native/boot/test_boot041_package.py
   python3 -I native/boot/test_ramroot.py
   # The DT and initramfs deltas against attempt 23's own boot040 download, independently of the M5's build/:
   python3 -I -c 'import sys; sys.path.insert(0, "native/boot"); import usb_dt, control_channel as cc
   from fdt import properties
   a, b = (sys.argv[1] + "/build/native-boot04%d-download/ilinux-j716c-boot04%d/" % (n, n) for n in (0, 1))
   usb_dt.check_both_darts_delta(properties(open(a + "t6050-j716c-stage-b.dtb", "rb").read()),
                                 properties(open(b + "t6050-j716c-stage-b.dtb", "rb").read()))
   cc.check_init_only_delta(open(a + "initramfs-stage-b.cpio.gz", "rb").read(), open(b + "initramfs-stage-b.cpio.gz", "rb").read())
   for name in ("Image", "kernel.config", "m1n1.bin", "t6050-j716c.dtb", "initramfs.cpio.gz", "toolchain.txt"):
       assert open(a + name, "rb").read() == open(b + name, "rb").read(), name
   print("boot041 = boot040 + the two-DART DT delta + /init only")' "$PWD"
   grep -x "$(cut -d' ' -f1,2 kernel/experiments/usb-gadget/authorized_keys)" <(
     python3 -I -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))["control_channel_authorized_key"].split()[:2]))' \
       build/native-boot041-download/ilinux-j716c-boot041/package-manifest.json)
   )
   ```

   Require: the reviewed **102** controller cases plus `test_ramroot.py` (**45** with the attempt-24
   root's re-pin committed, 44 before) PASS, the USB suites
   `test_usb_dt.py` (12; the real-DT cases skip without the M5's `build/` directories),
   `test_control_channel.py` (16; its real-package cases skip likewise) and `test_kconfig_guard.py` (7),
   `test_boot041_package.py` (11, skips without the extracted packages), `Package PASS`, a receipt with
   13 files, the clean client pin `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, the delta line
   `boot041 = boot040 + the two-DART DT delta + /init only` (it needs attempt 23's
   `build/native-boot040-download`), and the last command printing the M1's own public key.

   | | Bytes | SHA-256 |
   |---|---:|---|
   | archive `ilinux-j716c-boot041.tar.gz` | 18,926,067 | `ab49e307239a600f0652ea180ee15aa2b153ddf3c28e910bf8b5f97317944d28` |
   | SHA256SUMS | | `593c449265c2cbd930f0c57db95939af59f37191c0d8934b4ff1146e34f280a1` |
   | `Image` (= boot040) | 44,681,728 | `a53d1d47467480d4b56d87c7b1365e9a5c28fd9ee9e5f0164a3e734f85526ad9` |
   | `kernel.config` (= boot036-040) | 321,820 | `caa8e71a095aca35024688ced8025a8cc03925e641e3988587627d7f5f3e3887` |
   | `t6050-j716c-stage-b.dtb` (boot040's + both DART instances per dwc3) | 61,995 | `b053f248be2980e39beda4e6e001457ad7074344dc789872a4952e92773f232a` |
   | `initramfs-stage-b.cpio.gz` (boot040's apart from `/init`) | 2,403,156 | `2731488005ce2136bc1170915235fefdc4f14db1291a5c4c80cc7040098f403c` |
   | `diag-init.c` | 56,086 | `2e2e99231176e49275f06e952af64f2c6d893802c3e862ca00122d01d2404810` |

   Git manifests are authoritative; stop on disagreement.

2. **Reviewed controller digests** (record the checked-out commit): the `stage-b` profile, the
   fixed arguments, the append check, `BOOT-J716C-RAM-DIAGNOSTIC` and the 180-second deadline, as in
   attempts 16-18, 21 and 23. The launcher is attempt 23's, unchanged.

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
   `build/native-intake/boot041-ioreg-before.txt`. No `1d6b:0104`; m1n1's own device is `1209:316d`.

Prepare the ignored records, push sanitized readiness in `progress.md` and `coordination.md`
(native/live NOT RUN), tell the human when ready.

## One human-started boot, filmed, read by the reader

Attempts 21 and 23's procedure, unchanged apart from the package.

1. Both Macs on power, same direct cable. **Restart the M1 fresh**, keep it awake with
   `caffeinate -i`, **re-seat the cable after the restart**, run the read-only USB gate. If the gate
   sees no device even after re-seats, boot the M5 into the iLinux Boot Lab again (attempt 21). Keep
   the M1 unlocked.
2. **Start recording before the launch command**, 1080p or better 4K, phone in a stand, the whole
   screen square-on, reflections dimmed; portrait with the left two thirds of the console framed
   worked in attempt 23. The evidence sits in **short lines** (`[usbN] …`, the `apple-dart …` kernel
   lines); the first minute carries most of it. Transfer the original file afterwards.
3. Human saves work, shuts down the M5, holds power for startup options, selects **iLinux Boot Lab →
   Continue**. Keep Macintosh HD as default.
4. Start the read-only host USB log capture with attempt 18's filter.
5. After `Running proxy...` and the gate passes, invoke **once**:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot041-download/ilinux-j716c-boot041 \
     --launch --device auto --confirm BOOT-J716C-RAM-DIAGNOSTIC
   ```

   No `m1n1.setup`, shell, handshake, reconnect or retry. After the handoff the serial port is
   closed: do not reopen it. **Accept the macOS USB accessory prompt** when it appears.
6. **Right after the handoff, start the reader once:**
   `build/control/bulk-log-reader --out build/native-intake/boot041-bulk-log.bin`. It stops by
   itself after 600 s or when the device goes away. Save `ioreg -p IOUSB -l -w0` and
   `ioreg -p IOService -l -w0 -r -c IOUSBHostInterface` at about +5 s and +60 s to ignored files.
7. Record the controller result as in attempts 16-23. Exit 0 is not Linux success.
8. **On the M5 screen**, expect attempt 23's baseline (PID 1, `online_cpus=1`, the genpd lines,
   the ladder) and, new or changed:
   * at ≈ 2-3 s, **six** `apple-dart <base>.iommu: t8110-class DART v2.4: PARAMS …, N clients, fault
     IRQ <n>, ERROR 0x…` lines, two per port: `2a2f00000` (new) and `2a2f80000`, `2aaf00000` and
     `2aaf80000`, `382f00000` and `382f80000`; both of a port name **the same fault IRQ**. Each is
     followed by `v2.2 fault layout: PENDING … (before reset)` (instance 0's is whatever iBoot left)
     and later a `DART [pagesize …, 16 streams, …, locked: <l>, AS … -> …] initialized` line: **read
     instance 0's `locked:`** (attempt 23's `prot 0` predicts 0);
   * after each `port N: UDC … bound` line: `[usbN] <udc> irq 58b(<a>) dart0 2a2f00000 sid 0 + dart1
     2a2f80000 sid 1 fault irq 58f(<n>) x2` (`x2` = both instances' fault handlers on the line), then
     `[ctl] port N: reading DART registers at …`, the **six register lines** (three per instance on a
     v2.4 DART: `@… p1 … prot … en …`, `err … tcr …/… ttbr …/…`, `v2.4 pend …`), then **`[usbN] dart0
     sid 0 bound tcr 9 ttbr <t> + dart1 sid 1 bound tcr 9 ttbr <t>: both set up`**. Read instance 0's
     `en` (attempt 23: `0`, now expected `ffff`), its `tcr` (expected `9/0`) and that both `ttbr`
     values are the same;
   * each heartbeat: `[diag] heartbeat NNN`, then one short line per port, `[usb1] configured On f<n>
     irq<n> dart<n> pend <a>/<b> <B>B q<n> 1o h<n> d<n> 1i h<n> d<n>`, then the long `[ctl]` line.
     `pend` is the pending-fault bitmap of instance 0 / instance 1 (bit 0 = stream 0, bit 1 = stream 1);
     `dart<n>` the fault-interrupt count;
   * **if a fault or bus error happens**: the kernel's `translation fault (v2.2 layout): stream N code
     C (name) level L at 0x… (fault #k, IRQ <n>)` line names the instance by its base (`2a2f00000` or
     `2a2f80000`), the short line's `pend` shows it until it is acknowledged, a bus error adds
     `BUSERR@<hex>`, `[ctl] port N: dwc3 bus error …` and the register lines again. **Read every digit
     of these lines.**
9. Stop criterion: **10 minutes from the handoff**, or earlier on a reset, a kernel panic or an M1
   panic. Then the human powers the M5 off (hold power), selects **Macintosh HD → Continue** and
   confirms the desktop return.

   | M5 screen | M1 | Meaning |
   |---|---|---|
   | `: both set up`; short lines with `pend 0/0`, `dart<n>` small and steady, `B` rising, `q` near 0, `1i d` advancing; no `BUSERR` | the reader streams the whole log for ten minutes, no timeouts | **candidate A confirmed**: the stall of attempts 21 and 23 was the sibling instance Linux never set up. Report the capture (it now holds the `[usbN]` lines). Next: the Omarchy root with the link on boot041's package (the Image is the same, so the launcher's `omarchy` profile accepts it) |
   | `: both set up`, then `translation fault (v2.2 layout): stream 0 … at 0x…` on `2a2f00000` or `2a2f80000` | bytes, then maybe silence | a real fault, now reported and acknowledged on the instance that took it: the code, level and address decide. `TABLE WALK` at `PTE`/`STE` on an IOVA nobody mapped = the mapping path (candidate C, confining the IOVA range); compare the address with `BUSERR@` |
   | a fault on instance 0's **stream 1** or instance 1's **stream 0** (`pend 2/0`, `pend 0/1`, or the kernel line naming that stream) | bytes, then silence | the hardware also uses the other stream on that instance (macOS programs stream 1 on both and remaps 0 → 1): the next DT gives both instances both streams, `<dart0 0>, <dart0 1>, <dart1 0>, <dart1 1>` |
   | `fault IRQ <n> acknowledged 256 times; disabling it` | silence | the v2.2 acknowledgement is incomplete on this chip (open item T6 of `rea-dart-2026-10-18.md`): report the fault lines before it verbatim |
   | `pend` stays nonzero over several heartbeats while `dart<n>` no longer rises | | a fault left unacknowledged: the line was disabled or its handler failed; report the kernel lines around it |
   | `irq <n>: nobody cared` with `x2` and `pend 0/0` | silence | neither instance raised the line: the two GAPF "PS_PROT" units on the same interrupt (ADT `reg[2]`/`reg[3]`, in no DT) are the next suspect |
   | `BUSERR@<addr>` with `pend 0/0` and no `apple-dart` line | silence | not a DART fault: fabric, GAPF, an address outside the DART's path |
   | `: dart0 NOT set up` (`unbound`, or `tcr`/`ttbr` 0 on stream 0 of instance 0), or no `t8110-class DART` line for `2a2f00000` | | the kernel did not set instance 0 up: report its probe lines (`locked: 1`? an error?) and any `iommu`/`dwc3` probe error verbatim |
   | no `[usbN]` lines, `[ctl] no UDC yet`, `probe of 2a2280000.usb returned -22` (or a deferral that never ends) | nothing enumerates | the kernel refused the two-DART wiring for the core (for example instances whose PARAMS differ); report the probe lines; the fallback is boot040's DT |
   | the M5 resets or freezes at the DART probe lines (≈ 2-3 s, before any UDC binds) | | Linux's reset of instance 0 is not safe on this chip: report the last line and its time |
   | `[usbN] … bases not confirmed` and `dart regs not read …` on a real port | | `/init` could not match the DT's DARTs to the port's ADT pair: report the line; the kernel's own `apple-dart` lines still show the wiring |
   | EP0 timeouts, `not attached`, `-110`, a panic at the first status line | | as attempt 21's table; report verbatim |

10. Push the sanitized report and the progress/coordination updates. The capture, sidecar, host USB
    log, `ioreg` dumps and media stay local; commit only checked excerpts. Never copy
    `/proc/device-tree`. The m1n1 screen shows the Mac's serial-number line before the handoff: never
    transcribe or share it.

## Path toward Omarchy

Attempt 22 put the installer-built Omarchy desktop on the M5, view-only. The attempt-24 root (job 045
with the link, Claude Code and passwordless sudo) is pinned to boot040's Image, which boot041 keeps byte
for byte; the launcher's `omarchy` profile already accepts boot041's package with that root offline
(`RAM root PASS`). If boot041's link carries data, the combined boot is that root on boot041's package:
Omarchy reached over SSH on the fixed USB wiring, with agents running on the machine. If it does not,
the row it lands in names the next single change.

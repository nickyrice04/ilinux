# boot040: attempt 21's bulk-only log port with the DART fault made visible, prepared offline

2026-10-18, M5 side session. **Native boot040 NOT RUN.** Published as the prerelease
`native-j716c-boot040` (GitHub's asset digest verified) and handed off as attempt 23 the same day. It
builds on `boot039-bulk-log-2026-10-16.md` and the attempt-21 result
(`stage-b-2026-10-18-attempt21-result.md`). Labels: Confirmed / Likely / Hypothesis /
Unknown; "Confirmed" means by source, ADT, VM or package check, never on the M5's hardware.

## Summary

* **Attempt 21** answered attempt 18's question (no interrupt endpoint: EP0 healthy for ten
  minutes, 36,909 bytes read over bulk IN) and left a new stop: port 1's dwc3 flagged a bus
  error, its interrupts froze at 146 with 17 IN TRBs queued at dequeue 105, and Linux disabled
  IRQ 43 (`apple-dart fault handler`, port 1's DART) after an interrupt storm that produced no
  fault report. **boot040 changes nothing about the link** (same `gser` gadget, DT, config,
  m1n1, reader) **and adds diagnostics only**, so the next film shows the first fault:
  * **Image, part 1:** the apple-dart t8110 fault handler reports an interrupt it does not
    recognise (raw ERROR, ERROR_MASK, ERROR_STREAMS, ERROR_ADDR, TLB_CMD; the first four,
    then every 25,000th), acknowledges a pending ERROR or stream bit, otherwise returns
    IRQ_NONE, and names each DART instance at probe (version, PARAMS1-4, client count,
    Linux fault IRQ). The IOMMU's translation and protection settings are untouched
    (`kernel/experiments/usb-gadget/dart-diag/`).
  * **Image, part 2 (added after the REA result below):** a DART whose PARAMS3 reports
    version 2.2 or later keeps its fault state in a layout Linux does not know (pending
    bitmap 0x4000, per-stream error blocks 0x8000 + 0x40·SID, mask 0x4060); for such a
    DART, and only then, the handler reports and acknowledges in that layout (pending words
    written back, protection status cleared, TLB flush-unlock when register 0x210 asks),
    returns IRQ_NONE when nothing is pending and disables the line itself after 256
    acknowledged interrupts. This is fix candidate B in a form that selects itself by the
    hardware's version register; a DART below 2.2 runs the unchanged paths.
  * **`/init`:** the failing DMA address (GBUSERRADDR1:0) at a bus error; at bind, which DART
    instance, stream and fault interrupt serve each dwc3 core (from sysfs) and a read-only
    register snapshot of both DART instances of the port, the one in the DT and the sibling
    the DT leaves out, through `/dev/mem`; a short `[usbN]` line per port each heartbeat
    (about 100 columns); the port's log streamer stopped for good at its first bus error,
    with the snapshot repeated.
* **Audit** of the Linux DART driver against the ADT, Asahi's wiring and m1n1: seven
  findings D1-D7 (`dart-diag/README.md`). The weightiest two: the Stage-B DT gives each dwc3
  one DART instance while **every Asahi generation gives it both, on one shared fault
  interrupt**, so the instance the DT leaves out has no Linux handler (exactly how `nobody
  cared` arises); and, from the REA of this Mac's own macOS DART driver and SPTM done by a
  side session (`dart-diag/rea-dart-2026-10-18.md`, behaviours only), **macOS selects the
  fault-register layout by the DART version in PARAMS3, and from version 2.2 on the layout is
  one Linux neither reads nor clears**, which on such a DART produces attempt 21's storm
  exactly. The t6050's version is readable only from the hardware (boot040 prints it), so
  the cause is not settled offline; boot040 ships the diagnostics and the one change that
  selects itself by that register (part 2). The other fix candidates (A two-DART wiring,
  C IOVA range) stay written down with the evidence that would select them.
* **Package** `ilinux-j716c-boot040.tar.gz`: 18,921,232 bytes, SHA-256
  `1d7f5c8de17608b21eb9d047d4ee8470c785e3d2ba252fc7b156b4aee46166cf`; SHA256SUMS digest
  `4ee2f1f343a2539e18e5e19f9c4ed190e8e730ad685933e2f238bbc65174e4c9`. Records in
  `build/native-boot040/records/`, copied to `native/boot/` at the attempt-23 handoff.
  An earlier boot040 archive of this day (`387cfc05…`, part 1 only, before the REA result) is
  superseded and was not published.
* **VM:** job 041 PASS (kernel facts incl. the DART facts; `apple-dart.o` with W=1, no
  warning; the status fixture plain and under ASan+UBSan; the DART strings in the Image);
  `selftest/run-vz.sh both` PASS (liveness 34 heartbeats, 60 s milestone; dummy_hcd
  self-test 27/27 present + 14/14 absent: 1,929 log lines over bulk IN, no echo, the `[usb4]`
  lines, no DART register read for the unknown UDC). The packager rebuilds the archive
  byte-identically and refuses every other payload change (10 cases). The committed launcher
  (`b14ec7a1…0740`) passes the package offline: `Package PASS … Mode: OFFLINE ONLY`.

## What boot040 changes

| File | boot039 | **boot040** | Enforced by |
|---|---|---|---|
| `Image` | boot036's (`e0e53113…`) | **`a53d1d47…`**, 44,681,728 bytes: boot036's tree and config plus `dart-diag/dart-diag.patch` and `dart-diag-2-gen22.patch` on `drivers/iommu/apple-dart.c` (`f48a05cf…` → `1ed5acf9…` → `b3eb0da8…`, digest-gated two-stage `apply.py`) | `make-package.py`: `IMAGE_SOURCE` pin, `check_dart_diag_image`, the embedded config = `kernel.config` |
| `initramfs-stage-b.cpio.gz` | `19e5e366…`, 2,397,729 | **`59bc2afc…`**, 2,402,470: boot039's apart from `/init` | `check_init_only_delta` against boot039's |
| `diag-init.c` | `8ba20c93…`, 29,064 | **`58c68268…`**, 45,907 | `INIT_SOURCE` pin, `check_bulk_only_init`, `check_dart_diag_init` |
| `kernel.config`, `t6050-j716c-stage-b.dtb`, `t6050-j716c.dtb`, `initramfs.cpio.gz`, m1n1 (4), `toolchain.txt` | | **byte-identical** | baseline comparison (`boot039-package-manifest.json`) |

### The kernel change, part 1 (`dart-diag.patch`, 5 hunks)

Before: `apple_dart_t8110_irq` reads ERROR, ERROR_ADDR_LO/HI and returns IRQ_NONE when bit 31
(the flag) is clear; nothing is printed, nothing acknowledged. After: it also reads the
per-stream bitmap; without the flag it prints `fault IRQ <n> without the error flag (#<k>):
ERROR … MASK … STREAMS … … ADDR … TLB_CMD …` for the first four interrupts and every 25,000th,
writes a nonzero ERROR back, clears set stream bits and returns IRQ_HANDLED, or IRQ_NONE when
nothing was pending (so the kernel's spurious-interrupt protection still ends a storm the DART
did not raise). The recognised-fault report gains the fault number, the IRQ and the stream
bitmap. At probe each t8110 instance prints `t8110-class DART v<maj>.<min>: PARAMS … , <n>
clients, fault IRQ <irq>, ERROR …`. `test_dart_diag.py` (run by job 041 and on the Mac against a
patched scratch copy) requires that the handler writes only ERROR and ERROR_STREAMS and that
the translation, bypass, TTBR, protection, reset and TLB paths are unchanged.

**Confirmed (source):** nothing in the patch changes which streams translate, their tables,
bypass or protection; the handler's only new writes are the two acknowledgement registers the
unpatched handler already writes on a recognised fault.

### The kernel change, part 2 (`dart-diag-2-gen22.patch`, 6 hunks): the version 2.2 layout

The REA side session found, in this Mac's own `AppleT8110DART` driver and SPTM, that the fault
registers of a DART of version 2.2 or later (PARAMS3 bits 15:0 ≥ 0x202) are a per-stream
pending bitmap at 0x4000 (write-one-to-clear), a 64-byte error block per stream at 0x8000 +
0x40·SID (summary with the code in bits 3:0 and the table level in 13:12, the address at
+0x08/+0x0c, AXI ids), the mask at 0x4060, a protection-unit status at 0x704 (0x4204 from 2.4)
on the same line, and that the acknowledgement is the pending words written back followed by
a TLB "flush-unlock" (op 4) when register 0x210 bit 1 is set (`rea-dart-2026-10-18.md`, G1-G6,
E6, T1, T4, T6; Confirmed from control flow). Part 2 implements exactly that behind a gate:
`g22_layout` is set at probe when the version is ≥ 2.2 and the register window holds the
blocks (the ADT gives these DARTs 0xc000; the M2's were 0x4000), the reset then also clears the
pending words and the protection status and writes 0 to the v2.2 mask, and the fault handler
takes the v2.2 path first. The TLB-flush path (bit 15 of the command word and the write to
0x600 that the SPTM adds on these versions, T6) is **not** changed: its need is Unknown and it
is a different variable. On a DART below 2.2 part 2 changes nothing.

**Confirmed (source, `test_dart_diag.py`):** the gate precedes every pre-2.2 register read;
the v2.2 handler writes only the pending words and the protection status; flush-unlock is one
TLB_CMD write under the DART lock with the driver's bounded busy wait; the reset adds only
those writes plus the mask; translation, bypass, TTBR, protection and the ordinary TLB-flush
paths are untouched. **Not tested on hardware:** every v2.2 behaviour (the REA read it from
the binaries' control flow, not from the chip).

### The `/init` change

| Line | When | Source |
|---|---|---|
| `[usb1] 2a2280000.usb irq 58b(<a>) dart1 2a2f80000 sid 1 fault irq 58f(<n>); dart0 2a2f00000 not in DT` | at bind | `/sys/class/udc/<udc>/device/iommu` (the IOMMU core's link to the DART's class device under its platform device), the dwc3 node's `iommus`, the DART node's `interrupts`, `/sys/kernel/irq/*` with action `apple-dart fault handler`; instance 0's base from a table keyed by the UDC, used only when the kernel's link confirms instance 1's base |
| `[ctl] port 1: reading DART registers at 0x2a2f00000 and 0x2a2f80000 through /dev/mem` then `[usb1] dart0 @… p1 … p2 … p3 … p4 … prot … en …`, `[usb1] dart0 err … strm … addr … tcr …/… ttbr …/… tlb … mask …` and, on a version ≥ 2.2 DART, `[usb1] dart0 v2.2 pend … mask … ctl … prot … s0 …@… s1 …@…`; the same for `dart1` | at bind, and the `err` (and `v2.2`) lines again at the first bus error | `/dev/mem` (CONFIG_DEVMEM=y, STRICT_DEVMEM allows MMIO), 32-bit loads at the t8110 offsets within the 0xc000 instance window, never a write; the v2.2 registers only when PARAMS3 says so (`check_kernel_facts.py` pins the offsets to the patched driver's) |
| `[usb1] configured On f<n> irq<n> dart<n> <B>B q<n> 1o h<n> d<n> 1i h<n> d<n> [STOPPED] [HALTED] [BUSERR@<hex>]` | each heartbeat, before the long `[ctl]` line | the same debugfs reads as boot039 plus GBUSERRADDR0/1 and the DART IRQ count |
| `[ctl] port 1: dwc3 bus error at DMA address 0x…: log streamer stopped; kernel messages stay on the console` | once, at the first bus error | the status child records GSTS bit 4 and the address in shared memory; PID 1 kills the streamer, does not restart it (`nostream` replaces the counters in the short line) |

**Likely:** instance 0 answers the register reads. Both instances share the ADT's
`clock-gates` entry (0x245 for port 1) and m1n1 powers the whole `dart-usbN` node before
Linux; instance 1 has answered the kernel driver's reads in attempts 17-21. **Not tested on
this hardware**: a read of an unclocked register on these SoCs can stall the bus, which is why
the read is announced on the line before it (`reading DART registers at …`) and happens at bind,
before any USB traffic. If the M5 stops right after that line, the sibling instance is the
cause, and the next package drops the instance-0 read.

**Confirmed (fixture, VM):** the parsing and the text, including the sysfs link resolution,
the stream id, the fault IRQ lookup, the bus-error address, the short lines' width (every
realistic line ≤ 100 columns; a wedge with three endpoints, two halt flags and a bus error
reaches 104) and the no-`/dev/mem` and unknown-UDC paths. The VM cannot show a dwc3, a DART or
a real `/dev/mem` read: those are the attempt's questions.

## Findings (short; evidence and confidence in `dart-diag/README.md`)

| # | Finding | Confidence |
|---|---|---|
| D1 | One DART instance per core in our DT vs both in every Asahi DT (`<dart0 0>, <dart1 1>`); both share one fault IRQ; the left-out instance has no Linux handler, which is the `nobody cared` path | mismatch Confirmed; relevance Unknown (m1n1's gadget uses instance 1 alone) |
| D2 | The handler reports nothing without ERROR bit 31 and never reads the stream bitmap in that case. **REA:** macOS selects the fault layout by the PARAMS3 version; from 2.2 on the layout differs (0x4000 / 0x8000 + 0x40·SID / 0x4060) and Linux is blind to it; the t6050's version is unknown until boot040 prints it | layout switch Confirmed (binaries); t6050 version Unknown; mechanism Likely |
| D3 | Linux flushes the stream's TLB on every map and (strict mode) every unmap; the ADT tells macOS to avoid the TLBI in map on every t6050 DART (`avoid-tlbi-in-map`, `flush-by-dva 0`, `dart-options 39`) | mismatch Confirmed; relevance Unknown |
| D4 | Linux uses the DART's full VA width (4-level tables above 36 bits) and allocates IOVAs top-down from it with a 64-bit dwc3 mask; m1n1 used four 32-bit IOVAs and 3-level tables; macOS a 4 GiB window at 1 TiB (`vm-base`, `remap 256`) | mismatch Confirmed; relevance Unknown |
| D5 | Acknowledgement: write ERROR back, clear ERROR_STREAMS, `ERROR_MASK = 0` at reset; attempt 21 shows an interrupt never recognised, not one failed to clear | Unknown |
| D6 | m1n1 leaves instance 1 / stream 1 in bypass at handoff; Linux's reset blocks all 16 streams before enabling stream 1; instance 0 is touched by nobody | Confirmed (source); instance 0's state Unknown |
| D7 | No `dma-coherent`, no Apple glue, no DRD/fabric tunables on our node (m1n1 applies none either) | differences Confirmed; relevance Unknown |

Fix candidates: **A** Asahi's two-DART wiring (DT only; the variant exists in
`kernel/experiments/usb-gadget-dt/`; the REA supports it: macOS programs every stream on every
instance), **B** the version 2.2 fault layout (in boot040 as part 2, gated on the hardware's
version register), **C** `apple,dma-range` on the USB DARTs (32- or 36-bit IOVAs, DT only; the
REA shows macOS using a 4 GiB window at 1 TiB with 3-level tables), **D** TLB policy: ruled out
as a correctness issue by the REA (Linux's flushes are a superset), with one open item on
versions ≥ 2.2 (bit 15 in the command word and a write to 0x600 after flushes).

## Results

| Check | Result |
|---|---|
| VM job 041 (`WAIT=1 host-run.sh boot040`, 2026-10-18 21:43:02-21:44:28Z; three earlier runs that day: two stopped on a symbol-list and a fixture-column error of this preparation, one built part 1 alone before the REA result; `vm` lock taken and released each time) | **PASS.** `apply.py`: `apple-dart.c` `f48a05cf…` → `1ed5acf9…` → `b3eb0da8…`; `test_dart_diag.py` PASS (both parts); `apple-dart.o` with W=1: no warning; Image, test Image, Stage-B DT (`a676087b…`, unchanged), initramfs built; config delta PASS; ELF 16 KiB pages PASS; the boot040 DART strings (both parts) in the Image; `init.c` and the fixture build with `-Wall -Wextra` and no warning |
| Kernel facts (`check_kernel_facts.py`, the exact patched tree) | **PASS**, now also: GBUSERRADDR0/1 in the regdump (75 of 309 names read), GSTS bit 4, the shared `apple-dart fault handler` action, the `<device>/iommu` class link, the ten t8110 offsets `dart_peek` reads, and the v2.2 offsets in the patched driver and in `dart_peek` (gated on PARAMS3), reads only |
| Status fixture (`status_fixture.c`, 31 checks) | **PASS** plain `-O2` and under ASan+UBSan: the identity line, the dartinfo from the sysfs links, streaming, attempt 21's picture (`BUSERR@3ffffffc000`, `dart99900`, `1i h17 d105`), the bus-error line, the snapshot without `/dev/mem`, the stopped port, the register lines for a version 2.1 and a version 2.2 DART, the wedge, the VM-style ports, no UDC, bounded buffers, every short line within its column limit |
| Generic VM, shipped Image + initramfs, 95 s (run twice: on the part-1 build and on the final one, same results) | **PASS**: PID 1, one CPU, debugfs, the boot040 banner, `no UDC`, dropbear, 34 heartbeats, the 60 s milestone; no `[usb` line, no DART read, no status-reader, write or debugfs failure |
| Generic VM, test Image + overlay, 120 s (dummy_hcd; run twice, same results) | **PASS**: gadget bound as `1d6b:0104 bcdDevice 0139`, one vendor interface with two bulk endpoints, no interrupt endpoint, `usbserial_generic` on `/dev/ttyUSB0`, **1,929 log lines over bulk IN**, no echo, no CDC function, `port4 configured … dwc3 n/a`, `[usb4] configured <B>B q<n> dwc3 n/a`, `[usb4] dummy_udc.0 irq 0(-1) no iommu link in sysfs`, `[usb4] dart regs not read (no confirmed DART bases for dummy_udc.0)`, SSH with the key `uid=0`, refused without; no DART register read, no bus error, no streamer restart |
| Packager (`test_boot040_package.py`, 10) | **PASS**: rebuilds the archive byte-identically, also after `init.c` moves on; refuses boot039's or a changed `diag-init.c`, boot039's Image (no DART patch) or any other Image (pin), boot039's initramfs (no DART diagnostics), an initramfs changed beyond `/init`, a changed `toolchain.txt`, `m1n1.bin`, `kernel.config`, DT or generic initramfs, boot038 as the baseline, missing flags, another key |
| `test_control_channel.py` (13, incl. the real boot040 package), `test_boot039_package.py` (8), `test_kconfig_guard.py` (7), `test_mtp_input.py` (33), `test_usb_dt.py` (6) | PASS |
| Committed launcher `b14ec7a1…0740` (the attempt-22 one), offline, from a scratch copy next to boot040's records | `Package PASS: all files match the repository manifest. Mode: OFFLINE ONLY; USB not opened`; the fixed arguments unchanged |

Evidence (ignored): `virtualization/jobs/041-usb-gadget/out/runs/boot040-2026-10-18/` (run logs
incl. the two failed preparation runs, digests, kernel facts, fixture output, DART checks, both
console logs).

## Reading the attempt

`dart-diag/README.md` has the line-by-line legend and `tools/m1n1-client/stage-b-instructions.md`
(attempt 23) the outcome table. In short: the first bus error now comes with its DMA address, the DART's own
view (a recognised fault with code and address, or the raw registers of an interrupt without the
flag), the sibling instance's registers, and the fault-interrupt count in every short line.
`ERROR 0 … STREAMS 0 0` on instance 1 with a `FAULT` or stream bit on instance 0 points at
candidate A; a nonzero ERROR without bit 31 at candidate B; a fault address at or above 2^36
with a `NO PGD`/`NO PMD` code at candidate C; a bus error with no DART line at all at the fabric
or the GAPF/PS_PROT units.

## NOT RUN / Unknown

* **NOT RUN:** native boot040 (attempt 23) and the M1's offline readiness for it. The release and
  the handoff are done (2026-10-18).
* **Unknown:** everything attempt 21 left unknown (which instance raised IRQ 43, the fault
  address, stream and code, bulk OUT, instance 0's state); whether instance 0 answers a
  `/dev/mem` read (Likely yes, see above); the t6050 DART's version and widths (printed at
  probe), and with it whether part 2 is active at all; whether the v2.2 acknowledgement as
  read from the binaries is complete for this chip (the 256-acknowledgement bound covers the
  case that it is not).

## Reproduce

```sh
WAIT=1 virtualization/jobs/041-usb-gadget/host-run.sh boot040                 # the vm lock, ~90 s
kernel/experiments/usb-gadget/selftest/run-vz.sh both                         # Mac, ~4 min
python3 -I native/boot/make-package.py --out virtualization/jobs/041-usb-gadget/out \
    --destination build/native-boot040 --name ilinux-j716c-boot040 \
    --previous-package build/native-boot039/verified \
    --authorized-key kernel/experiments/usb-gadget/authorized_keys \
    --record-dir build/native-boot040/records
python3 -I native/boot/test_boot040_package.py
```

## Files

* New: `kernel/experiments/usb-gadget/dart-diag/` (`dart-diag.patch`, `dart-diag-2-gen22.patch`,
  `apply.py`, `test_dart_diag.py`, `README.md`; `rea-dart-2026-10-18.md` by the REA side
  session), `native/boot/test_boot040_package.py`,
  `native/boot/boot039-package-manifest.json` (the boot039 manifest as the boot040 baseline),
  this report; the draft checklist became `tools/m1n1-client/stage-b-instructions.md` at the
  attempt-23 handoff.
* Changed: `kernel/experiments/usb-gadget/init.c`, `selftest/status_fixture.c`,
  `selftest/check_kernel_facts.py`, `selftest/run-vz.sh`, `README.md`;
  `virtualization/jobs/041-usb-gadget/run.sh`; `native/boot/make-package.py` (boot040 entry,
  `IMAGE_SOURCE`), `native/boot/control_channel.py` (`check_dart_diag_image`,
  `check_dart_diag_init`), `native/boot/test_control_channel.py`.
* Untouched: `native/boot/launch.py`, `test_ramroot.py`, `omarchy-root-manifest.json`,
  `package-manifest.json`, `archive-sha256.txt`, `intake-manifest-sha256.txt`,
  `tools/m1n1-client/stage-b-instructions.md`, the DT, `omarchy-arm64/`, job 045.
  Nothing committed, pushed or released.

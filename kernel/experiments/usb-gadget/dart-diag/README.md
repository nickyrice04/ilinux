# boot040: make the USB DART fault visible (after attempt 21)

Prepared offline 2026-10-18, M5 side session. **Native boot040 NOT RUN.** Labels:
Confirmed / Likely / Hypothesis / Unknown. "Confirmed" means confirmed by source, ADT,
VM or package check, never on the M5's hardware.

## What attempt 21 left

With boot039's bulk-only `gser` port, macOS published the vendor interface and the M1's
reader received 36,909 bytes of kernel log. Then, within a second, port 1's dwc3 read
`BUSERR` (GSTS.BUS_ERR_ADDR_VLD), its interrupt count froze at 146 and the bulk-IN ring
stopped with 17 TRBs owned by hardware at dequeue 105; at 9.956 s Linux printed `irq 43:
nobody cared` with `apple_dart_irq` as the only handler and disabled the IRQ. No
`apple-dart … translation fault` line ever appeared. IRQ 43 is AIC hwirq 66959 = DT
interrupt 0x58f = `dart-usb0`'s interrupt (the ADT's 1423): port 1's DART, the one the
M1 was cabled to (`native/boot/stage-b-2026-10-18-attempt21-result.md`).

## What boot040 adds (diagnostics only; nothing in the IOMMU's translation or protection changes)

| Where | Change | Checked by |
|---|---|---|
| Image: `drivers/iommu/apple-dart.c`, part 1 (`dart-diag.patch`, applied by `apply.py`, digest-gated on the asahi@77cb8f24 file) | The t8110 fault handler, when the interrupt fires **without** the error flag (bit 31 of ERROR), prints the raw ERROR, ERROR_MASK, ERROR_STREAMS, ERROR_ADDR and TLB_CMD (the first four times, then every 25,000th), writes back a nonzero ERROR and clears set stream bits, and returns IRQ_HANDLED only if something was pending; otherwise IRQ_NONE, so the kernel's spurious-interrupt protection still disables a line nobody owns. The recognised-fault path also prints the fault number, the IRQ and the stream bitmap. At probe every t8110 instance prints its version, PARAMS1-4, client count, Linux fault IRQ and ERROR. | `test_dart_diag.py` (handler writes only ERROR and ERROR_STREAMS; TCR, TTBR, PROTECT, ENABLE/DISABLE_STREAMS, TLB and reset paths untouched); W=1 build of `apple-dart.o`; the message strings in the Image (job 041, `control_channel.check_dart_diag_image`) |
| Image, part 2 (`dart-diag-2-gen22.patch`, applied after part 1; **the version-gated form of fix candidate B**, added after the REA result `rea-dart-2026-10-18.md`) | A DART whose PARAMS3 bits 15:0 report **version 2.2 or later** keeps its fault state in a per-stream pending bitmap (0x4000), a 64-byte error block per stream (0x8000 + 0x40·SID: summary, address) and a mask (0x4060), not in ERROR/ERROR_MASK/ERROR_STREAMS; Linux reads those and so would never see or clear such a fault. For such a DART (and only then: `g22_layout`, which also needs the 0xc000 register window the ADT gives these DARTs) the handler reads the pending words, the protection-unit status (0x704, 0x4204 from 2.4) and the control register 0x210, reports each pending stream's block (`translation fault (v2.2 layout): stream N code C (name) level L at 0x…`), acknowledges by writing the pending words back and all ones to the protection status, runs the TLB flush-unlock (op 4, bit 15) when 0x210 bit 1 asks, returns IRQ_NONE when nothing is pending, and disables the line itself after 256 acknowledged interrupts (a line that stays asserted through acknowledgements would otherwise spin the single CPU: the kernel's protection counts only unhandled interrupts). Reset clears the pending words and the protection status and writes 0 to the v2.2 mask. At probe the v2.2 state is printed before reset. **A DART below 2.2 runs the unchanged paths.** | `test_dart_diag.py` (gate at the top of the handler before any pre-2.2 read; the v2.2 handler writes only the pending words and the protection status; flush-unlock is one TLB_CMD write under the lock with a bounded wait; reset adds only those writes plus the mask; defines pinned); W=1; the message strings in the Image |
| `/init` (`kernel/experiments/usb-gadget/init.c`) | When GSTS flags a bus error, GBUSERRADDR1:0 (the first failing DMA address) joins the status line as `BUSERR@<hex>`. At bind, one identity line per port from the kernel's own sysfs: the dwc3 IRQ, the DART instance (`<dwc3>/iommu` link), the stream (`iommus`), the DART fault IRQ (DT interrupt and Linux number) and the sibling instance 0 the DT leaves out. Then a read-only register snapshot of **both** instances through `/dev/mem` (PARAMS1-4, PROTECT, ENABLE_STREAMS, ERROR, ERROR_STREAMS, ERROR_ADDR, TCR and TTBR of streams 0-1, TLB_CMD, ERROR_MASK, and, when PARAMS3 reports version 2.2 or later, the v2.2 pending bitmap, mask, control, protection status and the error blocks of streams 0-1), repeated at the first bus error. A short `[usbN]` line per port each heartbeat (about 100 columns). At the first bus error the port's log streamer is stopped for good. | `selftest/status_fixture.c` (fixture trees, plain and ASan/UBSan, every short line ≤ 100 columns), `selftest/check_kernel_facts.py` (register offsets, action name, sysfs link, GBUSERRADDR names), the dummy_hcd self-test (`[usb4]` line, no DART read for an unknown UDC) |

The Stage-B DT, kernel config, m1n1 and the generic files are boot039's. The packager
(`native/boot/make-package.py --name ilinux-j716c-boot040`, baseline
`native/boot/boot039-package-manifest.json`) allows only `Image`,
`initramfs-stage-b.cpio.gz` and `diag-init.c` to differ from boot039, pins `diag-init.c`
and the `Image` by digest (`INIT_SOURCE`, `IMAGE_SOURCE`: job 041's reproducible build),
requires the DART strings in the Image and in `/init`, and the initramfs to equal
boot039's apart from `/init` (`native/boot/test_boot040_package.py`, 10 cases).

## Audit: the Linux DART driver against what is known about the t6050 USB DARTs

Sources: the sanitized ADT (`hardware/adt/adt-sanitized.json`, `dart-usb0/1/2`,
`mapper-usbN`, `usb-drdN`), `drivers/iommu/apple-dart.c` and `io-pgtable-dart.c` at
asahi@77cb8f24 (byte-identical in the sparse clone and the v2 worktree), Asahi's M3 DTs
(`t8122.dtsi`, `t6030.dtsi` in the research clone), m1n1 `src/dart.c`, `src/usb.c`,
`src/usb_dwc3.c` at the pinned client, `build/native-boot039/verified/kernel.config`, job
041's kernel sources (`out/build/kernel-src`), and the attempt-21 observations.

| # | Finding | Evidence | Confidence |
|---|---|---|---|
| D1 | **The Stage-B DT gives each dwc3 one DART instance (instance 1, stream 1); Asahi gives every generation both instances, `<dart0 0>, <dart1 1>`, and both instances share one fault interrupt.** The ADT lists two DART register windows per `dart-usbN` (`reg[0]` 0x…f00000, `reg[1]` 0x…f80000, each 0xc000; `instance` records `DART/0`, `DART/1`, then two `GAPF` "PS_PROT" windows) and **one** interrupt (1423 for port 1). The Linux handler is requested `IRQF_SHARED`. With instance 0 left out of the DT, an interrupt raised by instance 0 (or by the GAPF units on the same line, Unknown) has no Linux handler: every handler returns IRQ_NONE, which is exactly the `nobody cared` path (`kernel/irq/spurious.c`: 99,900 unhandled of 100,000). | ADT; `native/boot/usb_dt.py` PORTS; `t8122.dtsi:1261-1300` (`dwc3_0` with `iommus = <&dwc3_0_dart_0 0>, <&dwc3_0_dart_1 1>`, both DARTs on `AIC_IRQ 976`), `t6030.dtsi:1383`; `apple-dart.c` probe (`request_irq … IRQF_SHARED`) | Mismatch **Confirmed**. Whether the t6050 dwc3 in device mode sends any transaction through instance 0 is **Unknown**: m1n1's gadget maps only instance 1 / stream 1 and carries bulk traffic (the whole 44 MB upload), so the ordinary device-mode path is instance 1 (Confirmed, m1n1 source and attempts 17-21). boot040's identity line and snapshot of instance 0 (ERROR, ERROR_STREAMS, TCR, TTBR, PROTECT) answer it. |
| D2 | **The handler reports nothing unless ERROR bit 31 is set, and in that case it never looks at the per-stream bitmap. Updated by the REA result (`rea-dart-2026-10-18.md`, §1-3): macOS's own driver selects the fault-register layout by the DART version in PARAMS3 bits 15:0; below 2.2 it is the layout Linux implements, from 2.2 on it is a different one (pending bitmap 0x4000, per-stream error blocks 0x8000 + 0x40·SID, mask 0x4060) that Linux neither reads nor clears.** On such a DART the storm of attempt 21 is exactly what the Linux handler produces (reads 0x100, finds no bit 31, IRQ_NONE, never clears 0x4000). The t6050's version is not in the ADT or IORegistry; the ADT's 0xc000 register window (0x4000 on the M2) fits the larger map. | REA of `AppleT8110DART` and the SPTM (G1-G6, V1-V3, Confirmed from control flow); `apple-dart.c`; attempt 21 | Layout switch **Confirmed** (macOS binaries); t6050 version **Unknown** (boot040 prints it); mechanism **Likely**. boot040 part 2 handles both layouts by the version the hardware reports. |
| D3 | **TLB invalidation: Linux flushes the stream's TLB on every map and every unmap; the ADT tells macOS to avoid the TLBI in map on every t6050 DART.** `apple_dart_iotlb_sync_map` flushes after each `dma_map_single` (each queued USB request), and `CONFIG_IOMMU_DEFAULT_DMA_STRICT=y` flushes synchronously on each unmap (no flush queue). Every `dart-*` node in the ADT carries `avoid-tlbi-in-map` (empty = set) and the USB DARTs `flush-by-dva = 0` (display and ACIO DARTs: 1). `dart-options` is 39 for the USB DARTs (37 MTP, 55 PCIe, 101 display); its bits are not decoded here. | ADT; `apple-dart.c` ops table; `kernel.config` | Mismatch **Confirmed**; relevance **Unknown**. About 105 IN TRBs completed under this policy before the fault, so a per-map TLBI is not fatal by itself. Decoding `avoid-tlbi-in-map` and `dart-options` needs REA of `AppleT8110DART` on this Mac (allowed: decompile freely, publish behaviours only) and is proposed as a follow-up, not done here. |
| D4 | **IOVA width and table depth: Linux uses the DART's full VA width with 4-level tables when it exceeds 36 bits and allocates IOVAs top-down from that limit (64-bit dwc3 DMA mask when GHWPARAMS0.AWIDTH is 64); m1n1 used 3-level tables and four fixed 32-bit IOVAs; macOS confines USB DMA to a 4 GiB window at 1 TiB.** `apple_dart_probe` sets `ias` from PARAMS3, `four_level = ias > 36`; `io-pgtable-dart` derives the levels from `ias`; `dma-iommu` allocates from `min(dma mask, aperture end)` downward. m1n1: `SCRATCHPAD_IOVA 0xbeef0000`, `EVENT_BUFFER_IOVA 0xdead0000`, `XFER_BUFFER_IOVA 0xbabe0000`, `TRB_BUFFER_IOVA 0xf00d0000`, one L1 table (36-bit space). ADT: `vm-base` 0x100_0000_4000, `vm-size` 0xffff0000, `remap = 256` (0x100, the 1 TiB window's upper bits; the driver's `DART_T8110_TCR_REMAP` field is defined but unused by Linux and m1n1). So if AWIDTH is 64 and PARAMS3 reports more than 36 VA bits, every Linux buffer sits in an IOVA range (near 2^ias) that no other software has exercised on this hardware, and EP0, the event buffer and the first 105 TRBs worked there. | `apple-dart.c:1367-1399`, `io-pgtable-dart.c:365-396`, `dma-iommu` (job 041 kernel-src), `dwc3/core.c:2291-2296`, m1n1 `usb_dwc3.c:57-60`, ADT | Mismatch **Confirmed**; relevance **Unknown**. boot040 prints PARAMS3/4 (VA/PA width, version) at probe and the failing DMA address (GBUSERRADDR) at the bus error: an address above 2^36 or outside the top of the aperture, or a DART fault code `NO PGD`/`NO PMD` at that address, would make this the lead. |
| D5 | **Acknowledgement path.** The driver acknowledges a fault by writing ERROR back and clearing ERROR_STREAMS, and unmasks all errors (`ERROR_MASK = 0`) at reset. Whether the t6050 needs a different acknowledgement is Unknown; the attempt-21 storm shows an interrupt that the driver did not acknowledge at all (it never recognised one), not one it failed to clear. | `apple-dart.c` `apple_dart_hw_reset`, `apple_dart_t8110_irq` | **Unknown**; boot040's handler acknowledges a pending ERROR or stream bit even without the flag, and reports when nothing is pending. |
| D6 | **m1n1 leaves instance 1 / stream 1 in bypass at handoff** (`dart_shutdown`: `tcr_disabled` = `BYPASS_DAPF | BYPASS_DART`, TTBR cleared, TLB invalidated); Linux's `apple_dart_hw_reset` then sets TCR = 0 (translation off, no bypass: faults) for all 16 streams, clears every TTBR, enables all streams, clears ERROR and unmasks, and enables translation on stream 1 only when the dwc3 attaches. **Instance 0 is touched by nobody** (m1n1 uses instance 1 only; Linux has no node), so it stays as iBoot/macOS left it: Unknown. | m1n1 `dart.c:733-760`, `usb_dwc3.c:1312`; `apple-dart.c:552-574` | **Confirmed** (source); instance 0's state **Unknown** until the boot040 snapshot. |
| D7 | Smaller differences from Asahi's wiring, none a fault source by itself: our dwc3 node has no `dma-coherent` (Linux then does cache maintenance and uses non-cacheable coherent buffers: safe either way), no Apple glue (`apple,t8103-dwc3`) and none of macOS's `tunable_DRD_USB31_GBL_DEFAULT` / `tunable_BULK_FABRIC_DEFAULT` register writes, which m1n1 does not apply either. | `usb_dt.py`, `t8122.dtsi`, ADT `usb-drd0` tunables, m1n1 `usb.c:145-192` | **Confirmed** (differences), **Unknown** (relevance) |

**None of D1-D7 explains attempt 21 by itself offline** (the version that decides D2 is
unknown), so boot040 ships diagnostics plus one change that selects itself by the hardware's
version register: part 2, candidate B in its version-gated form. The other candidates are
written down so the next step is one decision, not a search.

## Fix candidates (proposals, not in boot040)

* **A. Asahi's two-DART wiring (DT only):** enable `dart_usb0_0` (and the other ports'
  instance 0) and give each dwc3 `iommus = <&dartN_0 0>, <&dartN_1 1>`, as every Asahi
  generation does; the two-DART Stage-B variant already exists in
  `kernel/experiments/usb-gadget-dt/` (job 040 PASS, one deliberate `snps,dwc3` schema
  finding). **Take it if** boot040 shows instance 1 with `ERROR 0 STREAMS 0` while the
  line storms, or instance 0's snapshot shows `FAULT` in its ERROR / a set stream bit, or
  TCR 0 (translation off, no bypass) on instance 0's stream 0 together with the bus error.
  This keeps translation on; instance 0 would then be reset and programmed by Linux like
  instance 1.
* **B. The version 2.2 fault layout (driver): in boot040 as part 2, gated on PARAMS3.**
  The REA result gives the layout and the acknowledgement sequence; the patch applies them
  only when the hardware reports version 2.2 or later and is inert otherwise. If boot040's
  probe line reports a version below 2.2, part 2 did nothing and B is ruled out (Linux's
  layout and acknowledgement match macOS's there). If it reports 2.2 or later and the fault
  is then reported and acknowledged (`translation fault (v2.2 layout) …` without `nobody
  cared`), B is confirmed and the remaining open item is T6 of the REA file (bit 15 and the
  0x600 write after ordinary TLB flushes), which boot040 does not change.
* **C. Confine the USB DARTs' IOVA space (DT only):** `apple,dma-range` on the three
  USB DART nodes to a 32-bit (or 36-bit, three-level) window, as macOS's 4 GiB window and
  m1n1's 32-bit IOVAs do. **Take it if** GBUSERRADDR shows an address at or above 2^36
  with PARAMS3 reporting a wider VA, or the DART reports `NO PGD`/`NO PMD` there.
  Translation stays enabled; only the allocator's range changes.
* **D. TLB policy:** nothing to change on this evidence. If the fault address is a
  request buffer that had just been mapped or unmapped, `iommu.strict=0` is a launcher
  argument change (not allowed by the fixed arguments) and dropping `iotlb_sync_map`
  would need the REA finding on `avoid-tlbi-in-map` first.
* **REA (done 2026-10-18, `rea-dart-2026-10-18.md`):** `AppleT8110DART` and the SPTM on
  this Mac: the fault layout switch at version 2.2 (above), `dart-options` bits, `remap` as a
  stream remap (stream 0 → 1 on the USB DARTs), the 1 TiB window with 3-level tables,
  `avoid-tlbi-in-map` as an optimisation only, every stream write applied to every instance,
  and both USB drivers using stream 1. It supports A, makes B version-gated (part 2),
  supports C as a mirror of macOS, and rules D out as a correctness issue.

## Reading boot040 on the screen

| Line | Meaning |
|---|---|
| `apple-dart 2a2f80000.iommu: t8110-class DART v<maj>.<min>: PARAMS … , N clients, fault IRQ <n>, ERROR 0x…` (at probe, ≈ 2-3 s) | the instance's version and widths; `<n>` is the Linux IRQ the `nobody cared` trace would name. **`v2.2` or later** means part 2 is active and a second line follows: `v2.2 fault layout: PENDING … MASK … CTRL … PROT_STATUS … (before reset)` |
| `[usb1] dart1 v2.2 pend … mask … ctl … prot … s0 …@… s1 …@…` (third snapshot line, only on version ≥ 2.2) | the v2.2 fault state: pending streams, mask, control (bit 1 = flush-unlock needed), protection status, and the error blocks of streams 0 and 1 (summary@address) |
| `apple-dart …: translation fault (v2.2 layout): stream N code C (name) level L at 0x… AXI id … summary … (fault #k, IRQ <m>)` | part 2 recognised and acknowledged a fault in the v2.2 layout; `nobody cared` must not follow. Compare the address with `BUSERR@`; code 0 = table walk with the level named (TTBR/CTE/STE/PTE) |
| `apple-dart …: fault IRQ <m> acknowledged 256 times; disabling it` | the line stayed asserted through acknowledgements: the acknowledgement sequence is incomplete for this DART (open item T6 of the REA file) |
| `[usb1] 2a2280000.usb irq 58b(<n>) dart1 2a2f80000 sid 1 fault irq 58f(<m>); dart0 2a2f00000 not in DT` | the mapping, from sysfs; `<m>` must equal the stormed IRQ |
| `[usb1] dart0 @2a2f00000 p1 … p2 … p3 … p4 … prot … en …` and `[usb1] dart0 err … strm … addr … tcr a/b ttbr c/d tlb … mask …` (then the same for `dart1`) | the snapshot at bind, before any traffic. `prot` bit 0 = locked. `tcr` bit 0 = translate, bits 2:1 = bypass; `ttbr` bit 0 = valid. `FAULT` after `err` = bit 31 |
| `[usb1] configured On f<n> irq<n> dart<n> <B>B q<n> 1o h<n> d<n> 1i h<n> d<n> [BUSERR@<hex>]` (each heartbeat) | the short line: `dart<n>` is the fault-interrupt count (a jump to ~100000 is the storm); `BUSERR@` carries GBUSERRADDR1:0 |
| `[ctl] port 1: dwc3 bus error at DMA address 0x…: log streamer stopped; …` then the two `err …` lines again | the state at the first bus error |
| `apple-dart 2a2f80000.iommu: fault IRQ <m> without the error flag (#1): ERROR 0x… MASK 0x… STREAMS 0x… 0x… ADDR 0x… TLB_CMD 0x…` | the handler saw the line with no flag: all zero = instance 1 did not raise it (D1); nonzero = D2 |
| `apple-dart …: translation fault: status:… stream:… code:… (…) at 0x… (fault #1, IRQ <m>, streams …)` | a recognised fault; compare its address with `BUSERR@` |
| `irq <m>: nobody cared` | still possible if nothing on instance 1 is pending: then the storm comes from the sibling or the GAPF units (D1) |

## Files

`dart-diag.patch` (part 1, 5 hunks), `dart-diag-2-gen22.patch` (part 2, 6 hunks),
`apply.py` (digest-gated, two stages), `test_dart_diag.py` (contract check of both parts, run
by job 041 and runnable on the Mac against a patched scratch copy), `rea-dart-2026-10-18.md`
(the REA findings, by the REA side session), this README. The `/init` side is in `../init.c`;
its fixture test in `../selftest/status_fixture.c`; the kernel facts in
`../selftest/check_kernel_facts.py`.

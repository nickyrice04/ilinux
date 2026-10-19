# Stage B attempt 23 (boot040): the USB DART is version 2.4, instance 1's fault line finds nothing pending, and at the first bus error the sibling instance the DT omits holds the fault

2026-10-18 (handoff 10:17:47 PM Eastern, 2026-10-19T02:17:46.781Z). **One RAM attempt consumed.
Controller PASS, no host panic.** boot040 is attempt 21's bulk-only `gser` port plus the DART fault diagnostics. The M5's
panel was filmed in portrait for 130 s (to +122 s after the handoff); the human stopped filming because the screen repeated
attempt 21's pattern, and powered the M5 off at +3 min 36 s.

* **Controller:** exit 0 in 10.965 s (upload 8.90 s), handoff `02:17:46.781Z`, every gate PASS.
* **M1 side (read-only):** the gadget enumerated at +3.89 s and macOS selected configuration 1 at once (no
  `transport restrictions` line this time); the reader opened the vendor interface at +4.0 s and captured **25,911 bytes**
  (325 intact records of the M5's early log, kernel 0.0645 to 0.0731 s), then nothing. It ran to the M5's power-off at
  +215.7 s and stopped itself (exit 0). **No endpoint-0 error on the iLinux device, no M1 panic.**
* **From the video (short lines, legible):**
  * **The DART is version 2.4**: every DART instance line reads `p3 2a2a0204`, so boot040's part 2 (the v2.2 fault layout)
    was active and the kernel says `(v2.2 layout)`.
  * Port 1's controller `2a2280000.usb` has its DART fault interrupt at **Linux IRQ 43** (hwirq `0x58f`); the DT lists one
    instance (`2a2f80000`, stream 1), the sibling `2a2f00000` is **not in the DT**. The sibling answered the `/dev/mem`
    reads (no stall).
  * A fault-interrupt storm starts at kernel **3.9288 s**; in every reported interrupt (#1-#4, then #25000 to #100000) the
    v2.2 handler on instance 1 finds **nothing pending** (`PENDING 0x00000000 MASK 0x00000000 PROT_STATUS 0x00000000 CTRL
    0x00000000 TLB_CMD 0x07000101`); at 5.78-5.81 s Linux prints `irq 43: nobody cared`, `handlers: … apple_dart_irq` and
    `Disabling IRQ #43`.
  * At the first bus error (heartbeat 001, 8.64 s): `BUSERR@0` (the dwc3's own address register reads 0), the streamer is
    stopped, and the snapshot shows **instance 0 (the one the DT omits) with `pend 1`**, its stream block holding summary
    `0x00000000` and address **`0x3ffff35800`**, while **instance 1 has `pend 0`**.
* **Reading (Likely):** the controller's DMA also goes through the sibling instance, which Linux never programs
  (`en 0`); the fault is recorded there and raises the shared fault line, and the only handler reads instance 1. That is
  **candidate A** (Asahi's two-DART wiring) in the M5's own table. The v2.2 layout's pending word and stream block read as
  the REA described, on instance 0.
* Linux itself stayed healthy: the 50-domain ladder completed at ≈ 45.0 s and the heartbeats ran to at least 023 (119.6 s).
* Fresh policy/default checks: **NOT CHECKED.** No retry or settings change.

## Reviewed inputs and controller execution

* M5 handoff `c5ae860` (release target `d125b61`); M1 readiness `8f2f389` (the launch ran on that commit, clean tree, record at
  0 attempts before the launch).
* The boot040 package (prerelease `native-j716c-boot040`, GitHub's asset digest equal to Git): archive 18,921,232 bytes,
  SHA-256 `1d7f5c8d…66cf`, verified against Git before extraction; `verify-package` receipt (SHA256SUMS digest `4ee2f1f3…e4c9`,
  13 files, clean client pin `57a9339`) PASS; launcher `b14ec7a1…`.
* One invocation through `build/native-intake/run-attempt23.py` (the sanitized one-shot wrapper):

| Item | Result |
|---|---|
| Invocation count | 1 |
| Start / handoff UTC | 2026-10-19T02:17:36.033 / 02:17:46.781 |
| Elapsed / exit | **10.965 s / 0** (`Uploading…` 0.88 s, `RAM upload complete…` 9.78 s, handoff 10.75 s) |
| Package, mode | PASS; `Mode: LIVE RAM LAUNCH` (default `stage-b` profile, 180 s deadline) |
| Fixed arguments | as attempt 21: `console=tty0 fbcon=nodefer rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 idle=nop arm64.nowfxt pd_ignore_unused clk_ignore_unused loglevel=8 ignore_loglevel printk.time=1 panic=0 earlycon=ilinuxfb initcall_debug initcall_blacklist=clk_debug_init ilinux_probe_diag=1` |
| Primary interface, target | PASS: 1209:316d, CDC data interface 1; t6050, boot021 marker, no started secondaries |
| GPIO ADT, board/framebuffer, DAPF layout and correction | PASS (221 pins / 7 groups, exclusions 5,6,7,112,141; 96-byte correction) |
| Final hardware DT, framebuffer descriptor | PASS (16-byte descriptor, readback verified) |
| kboot reply / USB close | PASS |

* **M1 host:** freshly restarted (uptime about 6.5 min at the launch; the launch waited until the CPU was at least 88% idle with
  the load average below 8), `caffeinate -di` running, the read-only gate passed on the first try, no panic report during or
  after the run (the newest report on file is attempt 15's). The reader is attempt 21's binary (`77677ee3…`), unchanged.

## Media and method

`Attempt23.MOV` (it arrived in the repository root and was moved into the ignored inbox before any commit): **130.2 s, portrait
(1080×1920 oriented), 30 fps, original file** (260 MB). It starts about 3 s after the launch, on m1n1's proxy screen, and ends
at +122 s after the handoff. Time mapping: the single-frame brightness dip at video 7.6 s and the flash after it are the handoff, so
**video ≈ handoff + 7.7 s (±0.2 s)** and **kernel ≈ video − 8.0 s (±0.5 s)** (checked against heartbeats 001, 011 and 023
appearing where predicted). The phone was framed on the left two thirds of the console, as the checklist asked; the short lines
(about 100 columns) are about 6 px per character and were read by eye from upscaled single frames at video 14, 21, 70 and 129.5 s.
Digits are good to about one; long hexadecimal words (the `s0`/`s1` blocks) and the stream-block address are the weakest
readings. **The m1n1 screen prints the Mac's serial-number line during the last second before the handoff: no frame earlier than
video 14 s was opened by eye, and nothing from that line is in this report.** Review images deleted; the media stays local.

## M5 screen, literal observations

Kernel seconds on the M5's console; PARAMS and register words as printed (the register lines are `[usbN] …` lines of `/init`).

| Kernel s | Observation |
|---:|---|
| ≈ 3.3 | `[ctl] USB control channel: GSER bulk-only kernel log port per UDC, no interrupt endpoint, no network; boot040: DART identity and registers, bus-error address, short [usbN] lines` |
| 3.42-3.45 | `[ctl] port 1: UDC 2a2280000.usb bound, GSER bulk-only 1d6b:0104 bcdDevice 0x0139, no interrupt endpoint, log on ttyGS0`; `[usb1] 2a2280000.usb irq 58b(46) dart1 2a2f80000 sid 1 fault irq 58f(43); dart0 2a2f00000 not in DT`; `[ctl] port 1: reading DART registers at 0x2a2f00000 and 0x2a2f80000 through /dev/mem` |
| 3.44 | `[usb1] dart0 @2a2f00000 p1 0e311020 p2 30111003 p3 2a2a0204 p4 00010010 prot 0 en 0`; `dart0 err 00000000 strm 0 addr 00000000 tcr 1/1 ttbr 17e7fffc/3fdbf7fc tlb 970d mask 0`; `dart0 v2.4 pend 0 mask 0 ctl 0 prot 0 s0 …@… s1 …@…` (both blocks read as long, random-looking words); then `dart1 @2a2f80000` with the same `p1…p4`, **`en ffff`**, `err 00000000 strm 0 addr 00000000 tcr 0/9 ttbr 0/1000cc5d tlb 7000101 mask 0`, `dart1 v2.4 pend 0 mask 0 ctl 0 prot 0` and blocks that also read as random-looking words. The same pattern for ports 2 and 3 (their `p3` also `2a2a0204`, read at lower resolution) |
| 3.585 | heartbeat 000; per-port `dwc3: core 0x33313130, 32 endpoints (16 IN), MDWIDTH 128; TX FIFO words 0:35 1:199 … 15:199; RX FIFO words 1000` (as attempt 21); `[usb1] addressed On f14614 irq1 dart0 8192B q8192`; ports 2 and 3 `not attached Suspend` |
| **3.9288** | the first `apple-dart 2a2f80000.iommu: fault IRQ 43 (v2.2 layout) with nothing pending (#1)`: `PENDING 0x00000000 MASK 0x00000000 PROT_STATUS 0x00000000 CTRL 0x00000000 TLB_CMD 0x07000101`; #2 at 3.9300, #3 at 3.9312, #4 at 3.9324 |
| 4.39 / 4.86 / 5.32 / 5.78 | the same line for #25000, #50000, #75000, #100000, every one with all five fields as above (about 54,000 interrupts per second) |
| 5.78-5.81 | `irq 43: nobody cared (try booting with the "irqpoll" option)`, `CPU: 0 … Comm: swapper/0 … PREEMPT`, a call trace (`__report_bad_irq`, `note_interrupt`, `handle_irq_event`, `handle_fasteoi_irq`, `generic_handle_domain_irq`, `aic_handle_irq` … `do_idle`, `cpu_startup_entry`), `handlers:` with `apple_dart_irq`, **`Disabling IRQ #43`** |
| **8.64** | heartbeat 001: **`[usb1] configured On f5880 irq102 dart100000 35125B q8192 1o h17 d0 1i h17 d68 BUSERR@0`**; ports 2 and 3 `not attached Suspend f0 irq0 dart0 8192B q8192`; `[ctl] port 1: dwc3 bus error at DMA address 0x0: log streamer stopped; kernel messages stay on the console`; `[ctl] port 1: reading DART registers …` |
| 8.69-8.70 | the snapshot at the first bus error: `dart0 err 00000000 strm 0 addr 00000000 tcr 1/1 ttbr 17e7fffc/3fdbf7fc tlb 970d mask 0`; **`dart0 v2.4 pend 1 mask 0 ctl 0 prot 0 s0 00000000@3ffff35800 s1 00000000@3ffff35800`**; `dart1 err 00000000 strm 0 addr 00000000 tcr 0/9 ttbr 0/1000cc5d tlb 7000101 mask 0`; **`dart1 v2.4 pend 0 mask 0 ctl 0 prot 0`**, its blocks unchanged from bind (random-looking words) |
| ≈ 19.4-45.0 | the release ladder; **`ladder complete: 50 domains released` at 45.02 s** (as attempts 17, 18 and 21) |
| 33.9 → 119.6 | heartbeats 006-023 every ≈ 5.0 s: `[usb1] configured On f<changing> irq102 dart100000 nostream 1o h17 d0 1i h17 d68 BUSERR@0`; ports 2 and 3 unchanged; `irq102`, `dart100000`, `h17 d0`, `h17 d68` never change again; the frame number `f` changes at every heartbeat |

The counters of attempt 21 and attempt 23 differ in their values (`irq146`/`irq102`, `d105`/`d68`, 46,250 B/35,125 B accepted,
36,909 B/25,911 B captured) and agree in kind. This time the streamer was stopped at the first bus error, by design, so the
capture holds only the early log and none of the new lines.

## M1-side observations (read-only)

Times relative to the handoff `T0 = 02:17:46.781Z` (the host log is local Eastern time, UTC−4):

| +s | Event |
|---:|---|
| +0.10 | one endpoint-0 transaction error on the generic device at the port (m1n1's device being torn down), as at the handoffs of attempts 21 and 22 |
| +0.21 | m1n1's device destroyed (`hardware connection lost`) |
| +3.886 | enumerated `0x1d6b/0104/0139`, "iLinux J716c control channel, port 1", 480 Mbps (no `transport restrictions` line this time) |
| +3.891 | `AppleUSBHostCompositeDevice selected configuration 1` |
| +4.0 | reader: identity checked, interface 0 class `0xff`, one bulk IN `0x81`, one other bulk `0x01`; reading starts |
| +9.3 | first sidecar status: a 5 s read times out after **25,911 bytes**; **41** such timeouts follow, all the reader's own (`endpoint 0x81` in the kernel log), never a STALL |
| +215.7 | the reader sees `not responding`, stops by itself (exit 0), releases its lock |
| +215.8 | the iLinux device is gone (`hardware connection lost`), followed by port power-off/on events: the human's power-off of the M5 |

* The capture (`SHA-256 8564c476…`, ignored): 325 records, each ending in exactly one CR LF, kernel 0.064496 to 0.073076 s,
  monotonic, ending on a record boundary (`calling virtio_mmio_init … @ 1`). It holds no `dwc3`, DART or `[usbN]` line.
* `ioreg` at +5 s and +60 s (saved locally): device-level driver `AppleUSBHostCompositeDevice`, one `IOUSBHostInterface` (255/0/0,
  two endpoints) whose only client is `AppleUSBHostFrameworkInterfaceClient [bulk-log-reader]`.
* The M1 stayed healthy: no panic report, load settled.

## Interpretation (bounded)

**Confirmed (video, M1 logs):**

* The USB DART of this t6050 is **version 2.4** (PARAMS3 `0x2a2a0204`, all instances read), so boot040's part 2 ran on
  hardware: instance 1's handler in the v2.2 layout found nothing pending throughout the storm.
* The storm is on Linux IRQ 43, port 1's DART fault interrupt (DT instance 1, stream 1); it ran at about 54 kHz from 3.93 s
  until the kernel disabled the line after 100,000 unhandled interrupts, with no `translation fault` line ever printed.
* **At the first bus error the fault is on the sibling instance (the one the DT omits)**: `pend 1`, a stream block with
  address `0x3ffff35800`, while instance 1 reports `pend 0`. The sibling instance was readable through `/dev/mem`, enabled no
  streams (`en 0`, never programmed by Linux), and its stream block changed from random-looking words at bind to a plausible
  fault record at the bus error.
* The link behaves as in attempt 21 otherwise: enumeration and configuration, no endpoint-0 error, bulk-IN data for under a
  second (25,911 bytes captured), the dwc3 interrupt count frozen (`irq102`), 17 IN TRBs queued with the dequeue index stuck
  (`d68`), `BUSERR` flagged, Linux healthy to at least heartbeat 023.

**Likely (not tested):**

* **Candidate A:** the controller's DMA reaches memory through both DART instances (Asahi lists `<dart0 0>, <dart1 1>` for
  each controller; the Stage-B DT lists only instance 1), so a transaction on stream 0 of instance 0, which has no
  translation set up, faults there; instance 0 shares the fault line with instance 1, the only registered handler reads
  instance 1 and returns `IRQ_NONE`, the line stays asserted and storms, and the stalled DMA wedges the IN endpoint. This
  matches the M5's decision-table row "instance 1 did not raise the line; a stream bit on dart0 = the sibling carries
  traffic".
* Decoded with part 2's own tables, the stream block's summary `0x00000000` reads as code 0 (`TABLE WALK`) at level `TTBR`: a
  walk that found no valid table base, which is what an instance Linux never programmed would give.
* The v2.2 layout of the REA is right at least for the pending bitmap (word 0 at `0x4000`) and the per-stream block
  (address at `+0x08`/`+0x0c`): both changed on instance 0 exactly when the fault happened. The REA's acknowledgement
  sequence was not exercised on a real pending fault (instance 1 never had one).

**Hypothesis:**

* The dwc3's own `GBUSERRADDR` reads 0 because it does not latch the faulting IOVA on this fabric, or because a different
  master faulted; the DART's `0x3ffff35800` is the lead. It is a top-down address under the 38-bit aperture's end
  (`0x4000000000`), which is where Linux's IOVA allocator hands out buffers.
* Attempt 21's stop had the same cause (instance 0 was never read there).

**Not established:** that enabling instance 0 stops the stall; whether stream 0 on instance 0 carries the data or the
descriptors; bulk OUT; a working log stream, SSH or web access; why instance 1's and instance 0's unused stream blocks read as
random-looking words.

## Return and next handoff

* The human stopped filming about 2 minutes after the handoff and powered the M5 off at +3 min 36 s, returning it to
  Macintosh HD (reported: "powered off and back on the Macintosh HD desktop"; the M1's host log fits it). The human's panel
  description arrived empty; the video is the evidence. Fresh policy/default/installed-object checks: **NOT CHECKED.**
  Attempt 23 is consumed; no retry or settings change. The fixed E1 probe is still **NOT RUN**.
* **For the M5 (proposals, not authorization):**
  * **Try candidate A**: list both DART instances for each dwc3 in the Stage-B DT (`kernel/experiments/usb-gadget-dt/` has the
    variant) so Linux programs instance 0 as well as instance 1 and registers a handler for both on the shared fault
    interrupt; keep the part 1 and part 2 reporting, the short lines and the register snapshot (they worked, and the
    `/dev/mem` read of the sibling did not stall).
  * Add a line at bind that proves both instances are enabled (`en` on instance 0 nonzero) and, on the next failure, the
    pending bitmap of **both** instances in the short line, since the fault was only visible on instance 0.
  * Keep the dwc3 `BUSERR@` but do not rely on it for the address: it read 0 here.
  * The film worked: a 130 s portrait clip with the left two thirds framed made the whole sequence legible; the first
    minute carries everything.
* The reader needs no change.

No media, capture, `ioreg` dumps or identifiers beyond the fixed hardware names are committed. Earlier reports are unchanged.

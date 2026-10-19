# Stage B attempt 24 (boot041): both DART instances per dwc3 core remove the stall — the USB log streams for the full ten minutes

2026-10-18 (handoff 11:38:34 PM Eastern, 2026-10-19T03:38:34.430Z). **One RAM attempt consumed. Controller PASS, no host
panic.** boot041 is boot040 with both DART instances per dwc3 core in the Stage-B DT. The M5's panel was filmed in portrait for
600.8 s (to +594 s after the handoff); the human powered the M5 off at +11 min 12 s and returned to Macintosh HD.

* **Controller:** exit 0 in 11.197 s (upload 9.14 s), handoff `03:38:34.430Z`, every gate PASS.
* **M1 side (read-only):** the gadget enumerated at +3.87 s and macOS selected configuration 1 at once; the reader opened the
  vendor interface at +4.05 s and captured **218,079 bytes: 2,580 intact records, kernel 0.065 to 604.261 s, heartbeats 000 to
  119 with no gap**. It stopped itself at its 600 s limit (exit 0); the iLinux device was still enumerated afterwards. **No
  endpoint-0 error on the iLinux device, no M1 panic.**
* **On the M5 (capture and video):**
  * **All six DART instances probed (version 2.4) and, on every port, both were reset and bound to the same translation table
    (`both set up`).** The three shared fault lines (Linux IRQ 43, 44, 45) now each list **two** `apple-dart fault handler`s (the
    `/proc/interrupts` table, screen only).
  * **Not one fault of any kind in ten minutes:** the DART fault-interrupt count is 0 and both pending words are `pend 0/0` on
    every one of the 357 per-port heartbeat lines (3 ports × 119); no `BUSERR`, `STOPPED`, `HALTED`, `CSR-TIMEOUT` or `EVBUSY`
    flag, no `translation fault`, no `nobody cared`, no oops or call trace. Attempts 21 and 23 stopped within about 10 s.
  * Port 1's IN queue read **`q0` on every line from kernel 10 s on**, the dwc3 interrupt count rose from 499 (13.7 s) to
    1180 (599.2 s), and **the M5's accepted-byte counter matches the capture's offset at all 117 port-1 status lines from 10 s
    on**: exactly, or short by the 56-byte heartbeat line printed just before the status line (difference 0 on 12 lines, 56 on
    105, never anything else). The M1 received every byte the M5 wrote.
  * Linux itself: PID 1 at 3.27 s, the 50-domain release ladder complete at **45.056 s**, the 60 s milestone line at 64.03 s,
    heartbeats every 5.048 s (5.032 to 5.062) to 119 (604.3 s), one CPU.
* **Reading:** with the Image byte-identical to boot040's and the gadget unchanged, the DT change (six nodes; `/init` adds only
  reads) is what removed the stall (**Confirmed as a comparison, one passing run**); the cause is **Likely** attempt 23's
  candidate A, the unprogrammed sibling instance.
* Fresh policy/default checks: **NOT CHECKED.** No retry or settings change.

## Reviewed inputs and controller execution

* M5 handoff `b5ef90d` (release target `88d392c`); M1 readiness `717f9b8` (the launch ran on that commit, clean tree, record at 0
  attempts before the launch).
* The boot041 package (prerelease `native-j716c-boot041`, GitHub's asset digest equal to Git): archive 18,926,067 bytes,
  SHA-256 `ab49e307…4d28`, verified against Git before extraction; `verify-package` receipt (manifest digest `593c4492…`,
  13 files, clean client pin `57a9339`) PASS; launcher `b14ec7a1…` (unchanged). Against the M1's own boot040 download the delta
  was exactly the two-DART DT change plus `/init` (Image, config, m1n1, initramfs byte-identical); the M1's property-level DT diff
  found six nodes (the three instance-0 DART nodes enabled, the three controllers' `iommus` extended).
* One invocation through `build/native-intake/run-attempt24.py` (the sanitized one-shot wrapper):

| Item | Result |
|---|---|
| Invocation count | 1 |
| Start / handoff UTC | 2026-10-19T03:38:23.451 / 03:38:34.430 |
| Elapsed / exit | **11.197 s / 0** (`Uploading…` 0.87 s, `RAM upload complete…` 10.01 s, handoff 10.98 s) |
| Package, mode | PASS; `Mode: LIVE RAM LAUNCH` (default `stage-b` profile, 180 s deadline) |
| Fixed arguments | as attempt 23: `console=tty0 fbcon=nodefer rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 idle=nop arm64.nowfxt pd_ignore_unused clk_ignore_unused loglevel=8 ignore_loglevel printk.time=1 panic=0 earlycon=ilinuxfb initcall_debug initcall_blacklist=clk_debug_init ilinux_probe_diag=1` |
| Primary interface, target | PASS: 1209:316d, CDC data interface 1; t6050, boot021 marker, no started secondaries |
| GPIO ADT, board/framebuffer, DAPF layout and correction | PASS (221 pins / 7 groups, exclusions 5,6,7,112,141; 96-byte correction) |
| Final hardware DT, framebuffer descriptor | PASS (16-byte descriptor, readback verified) |
| kboot reply / USB close | PASS |

* **M1 host:** freshly restarted (uptime 371 s at the reader's start; the launch waited until the CPU was at least 88% idle with
  the load average below 8), `caffeinate -di` running, the read-only gate passed on the first try (the loaded-driver check listed
  the ACM, ECM and CDC base drivers), no panic report during or after the run (the newest report on file is attempt 15's). The
  reader is attempt 21's binary (`77677ee3…`), unchanged.

## Media and method

`Attempt24.MOV` (it arrived in the repository root as `24.MOV` and was moved into the ignored inbox before any commit):
**600.8 s, portrait (1080×1920 oriented), 30 fps, original file** (1.2 GB). It starts on m1n1's proxy screen about 6.5 s before the
handoff and ends at kernel ≈ 594 s, so the last ten seconds of the window (heartbeats 118 and 119) are in the capture only.
Time mapping: the single-frame brightness dip at video 6.4 s and the flash at 6.6 s are the handoff, so **video ≈ handoff + 6.5 s
(±0.2 s)** and **kernel ≈ video − 6.7 s (±0.4 s)** (checked: the `PID 1 reached` line, kernel 3.27 s, reads at video 10 s;
heartbeat 116, printed at 589.11 s, is the last block on the final frame at video 600.5 s; heartbeat 114 is the last block at
video 590). **The phone was moved or refocused at video 60.5 to 61.0 s** (a brightness step in the trace; frames before and
after show the same console at a different position and zoom); the trace is otherwise flat (mean luma 48 to 78 at 5 s steps),
with no blackout or restart. Frames were read by eye at video 20 (full, then two zooms), 50, 66, 590 (zoom) and 600.5 s; at
1.6 to 2.4× zoom the short lines were clear. **The m1n1 screen prints the Mac's serial-number line before the handoff: no frame
earlier than video 20 s was opened by eye; frames at 0 to 10 s were read only through OCR with serial-like text withheld, and
nothing from m1n1's screens is in this report.** Review images deleted; the media stays local.

The capture (`SHA-256 f50d734c…`, ignored) is the primary evidence: every record ends in exactly one CR LF (2,580 of each), the
rest is ASCII text, kernel time is monotonic. The video adds what the capture lacks: `/init` writes the
`/proc/interrupts` table and the CPU description straight to the console, not through `/dev/kmsg`, so they are on the screen only.

## M5 screen and capture, literal observations

Kernel seconds on the M5's console; register words as printed (`[usbN] …` lines come from `/init`). "C" = in the capture, "V" =
on the video.

| Kernel s | Src | Observation |
|---:|:-:|---|
| 0.0798-0.0806 | C | six `apple-dart <base>.iommu: t8110-class DART v2.4: PARAMS 0x8e311020 0x30111083 0x2a2a0204 0x00010010, 1 clients, fault IRQ 43/43/44/44/45/45, ERROR 0x00000000`, each with `v2.2 fault layout: PENDING 0x00000000 MASK 0x00000000 CTRL 0x00000000 PROT_STATUS 0x00000000 (before reset)` and `DART [pagesize 4000, 16 streams, bypass support: 1, bypass forced: 0, locked: 0, AS 42 -> 42] initialized`; bases `2a2f00000`/`2a2f80000`, `2aaf00000`/`2aaf80000`, `382f00000`/`382f80000` (each port's instance 0 probes just before its instance 1) |
| 0.0801 | C | `platform 2a2280000.usb: Adding to iommu group 0` |
| 3.27 | C | `PID 1 reached: the kernel booted and ran userspace.` |
| ≈ 3.3 | V | the `--- interrupts (/proc/interrupts) ---` table: IRQ 43, 44 and 45 (hwirq 66959, 66991, 67023 on `AIC2`), count 0, each reading **`apple-dart fault handler, apple-dart fault handler`** |
| 3.340 | C | `[ctl] USB control channel: GSER bulk-only kernel log port per UDC, no interrupt endpoint, no network; boot041: both DART instances per port in the DT, their setup at bind, both pending-fault words …` |
| 3.369 / 3.437 / 3.505 | C | `[ctl] port N: UDC <controller>.usb bound, GSER bulk-only 1d6b:0104 bcdDevice 0x0139, no interrupt endpoint, log on ttyGS0/1/2` |
| 3.371 | C, V | `[usb1] 2a2280000.usb irq 58b(46) dart0 2a2f00000 sid 0 + dart1 2a2f80000 sid 1 fault irq 58f(43) x2` (port 2: `2aa280000.usb irq 5ab(47)`, fault `5af(44)`; port 3: `382280000.usb irq 5cb(48)`, fault `5cf(45)`) |
| 3.382-3.399 | C, V | port 1 snapshot: `dart0 @2a2f00000 p1 8e311020 p2 30111083 p3 2a2a0204 p4 00010010 prot 0 en ffff`; `dart0 err 00000000 strm 0 addr 000000000 tcr 9/0 ttbr 1000cc61/0 tlb 5000100 mask 0`; `dart0 v2.4 pend 0 mask 0 ctl 0 prot 0 s0 … s1 …` (both blocks long, random-looking words); `dart1 @2a2f80000 … en ffff`; `dart1 err 00000000 strm 0 addr 000000000 tcr 0/9 ttbr 0/1000cc61 tlb 7000101 mask 0`; `dart1 v2.4 pend 0 mask 0 ctl 0 prot 0 …`. **Instance 0 now reads `en ffff` (attempt 23: `en 0`)** |
| 3.404 | C | **`[usb1] dart0 sid 0 bound tcr 9 ttbr 1000cc61 + dart1 sid 1 bound tcr 9 ttbr 1000cc61: both set up`**; ports 2 and 3 the same at 3.469 s (`ttbr 1000cc6d`) and 3.539 s (`ttbr 1000cc7d`); no `NOT set up` anywhere |
| 3.557-3.581 | C | heartbeat 000; per-port `dwc3: core 0x33313130, 32 endpoints (16 IN), MDWIDTH 128; TX FIFO words 0:35 1:199 … 15:199` (as attempts 21 and 23); `[usb1] configured On f8958 irq43 dart0 pend 0/0 8192B q8192 1o h17 d0 1i h18 d0`; ports 2 and 3 `not attached Suspend f0 irq0 dart0 pend 0/0 8192B q8192` |
| 1.42-45.056 | C | the release ladder: `ladder armed: first release in 17000 ms, then one domain per 500 ms` (1.42 s), `ladder complete: 50 domains released` at **45.056 s** (as attempts 17, 18, 21 and 23) |
| 13.7 → 599.2 | C | every heartbeat (5.05 s): `[usb1] configured On f<changing> irq<499 → 1180> dart0 pend 0/0 <bytes>B q0 1o h17 d0 1i h1 d<changing>`; accepted bytes 150,289 (≈ 54 s) → 217,401 (599.2 s); ports 2 and 3 unchanged (`not attached Suspend f0 irq0 dart0 pend 0/0 8192B q8192`) |
| 64.03 | C | `[diag] 60s elapsed; still alive. Observe the M5 framebuffer and the M1's bulk log reader.` (the only line after 46 s that is not a heartbeat block) |
| 604.261 | C | heartbeat 119, the last record |

After the ladder the console prints nothing but the heartbeat block (five lines every 5 s). The OUT endpoint stays at `1o h17 d0` for
the whole run: 17 hardware TRBs queued and no OUT transfer ever completed, as expected, since the reader never writes.

## M1-side observations (read-only)

Times relative to the handoff `T0 = 03:38:34.430Z` (the host log is local Eastern time, UTC−4):

| +s | Event |
|---:|---|
| +0.14 | one endpoint-0 transaction error on the generic device at the port (m1n1's device being torn down), as at the handoffs of attempts 21 to 23 |
| +0.24 | m1n1's device destroyed (`hardware connection lost`) |
| +3.866 | enumerated `0x1d6b/0104/0139`, "iLinux J716c control channel, port 1", 480 Mbps (no `transport restrictions` line) |
| +3.871 | `AppleUSBHostCompositeDevice selected configuration 1` |
| +4.05 | reader: identity checked, interface 0 class `0xff`, one bulk IN `0x81`, one other bulk `0x01`; reading starts |
| +5.08 | first progress line: **114,398 bytes** already in the capture (the M5 replays its log from boot: the capture starts at kernel 0.065 s) |
| +130 … +595 | seven 5 s read timeouts with 0 bytes (at +130, +211, +428, +519, +539, +579 and +595 s), all the reader's own (`endpoint 0x81` in the kernel log), never a STALL; the heartbeat sequence and the byte counters show nothing was lost around any of them |
| +604.6 | the reader reaches its limit: `stopped: --seconds reached; 218079 bytes captured`, exit 0, lock released |
| +618.6 | the iLinux device is still in the USB plane; its interface has no client any more |
| +672.5 | `hardware connection lost`, then port power-off/on events: the human's power-off of the M5 (+11 min 12 s) |
| +835.7 | a macOS device named "Mac" enumerates at the port: the M5 is back on Macintosh HD |

* `ioreg` at +5 s and +60 s (saved locally): device-level driver `AppleUSBHostCompositeDevice`, one `IOUSBHostInterface` (255/0/0, two
  endpoints) whose only client is `AppleUSBHostFrameworkInterfaceClient [bulk-log-reader]`; macOS bound no driver to the vendor
  interface and the reader opened it without an entitlement (as attempt 21).
* The M1 stayed healthy: no panic report, load settled (the 15-minute average was still falling from the restart).

## Interpretation (bounded)

**Confirmed (capture, video, M1 logs):**

* The ten-minute stream that attempts 21 and 23 could not deliver ran to the end: 218,079 bytes, no missing heartbeat, no
  loss between the M5's writes and the M1's reads, `q0` throughout, the dwc3 interrupt count rising steadily (about 1.2 per
  second after boot).
* **Both DART instances of each USB port were probed, reset, enabled and bound** (`en ffff` on both, stream 0 of instance 0 and
  stream 1 of instance 1 each at `tcr 9`, one shared `ttbr`), and each fault line carries two handlers. The new hardware-facing
  step, Linux resetting and programming instance 0 for the first time on this chip, **did not freeze or reset the SoC**.
* **No fault was recorded anywhere:** fault-interrupt count 0, `pend 0/0`, no `BUSERR`, no `translation fault` over 357 port
  heartbeat lines and ten minutes. The version-2.4 DART and the v2.2 fault layout the M5 decoded from the REA are therefore
  quiet when both instances are programmed; the reporting itself was not exercised on a real fault this time.
* The Image, gadget, `/init` mechanics and fixed arguments match attempt 23's; the stall that appeared within 10 s in
  attempts 21 and 23 did not appear. The difference is the DT's DART wiring (and `/init`'s extra reads).

**Likely (one run; not tested otherwise):**

* **Candidate A was the cause**: the controller's DMA also goes through DART instance 0, which Linux never programmed in
  attempts 21 and 23, so a transaction there faulted, the shared line stormed and the IN endpoint wedged (attempt 23's snapshot
  showed exactly that fault on instance 0). Listing both instances is what worked.

**Hypothesis:**

* Attempt 18's ACM + ECM stop (endpoint-0 timeouts after configuration, no interface published) may share this cause: all of
  the controller's DMA goes through the DART, and attempt 21's bulk-only gadget, which had no EP0 problem, still hit the fault.
  Attempt 18 never printed the bus error or the DART state, so this cannot be checked from its record.

**Not established:** bulk OUT (host to device: the reader never writes); a console or shell on the port; ECM, NCM, SSH or any
network; throughput (the reader samples once per second and the log is nearly idle after boot); stability beyond ten minutes,
under load or with more than one controller attached (ports 2 and 3 had no cable); what a second reader, or a reopen, sees;
which DMA class (descriptors, data, events) uses which stream (the driver set up both streams and nothing faulted either way);
the real-fault path of part 1 and part 2 on a v2.4 DART.

## Return and next handoff

* The human stopped filming at +594 s, powered the M5 off at +11 min 12 s and returned it to Macintosh HD (reported: "powered
  off and back on the Macintosh HD desktop"; the M1's host log shows a "Mac" device enumerating at +13 min 56 s). No panel
  description beyond that arrived; the capture and video are the evidence. Fresh policy/default/installed-object checks:
  **NOT CHECKED.** Attempt 24 is consumed; no retry or settings change. The fixed E1 probe is still **NOT RUN**.
* **For the M5 (proposals, not authorization):**
  * The log link works one way. Next in the M5's own order: the Omarchy root with the SSH link, or first a bulk-OUT test. A
    console or network needs the M1 to read **and write**; the reader never writes by design, so a read/write client is new code
    the M1 would write and review on request, with the M5's brief.
  * Reconsider a network function (ECM or NCM) on boot041's DT: macOS on the M1 loads the ACM, ECM and CDC base drivers, and
    attempt 18's failure may have been this DMA fault (Hypothesis above).
  * Keep the `pend a/b` and `dart<N>` fields in the short lines: they cost nothing and proved the absence of a fault. Consider
    also writing the `/proc/interrupts` table through `/dev/kmsg`, so it lands in the capture and not only on the screen.
  * The capture was complete without the film. For runs like this one, a film of the first minute and of the end is enough.
* The reader needs no change for the log.

No media, capture, `ioreg` dumps or identifiers beyond the fixed hardware names are committed. Earlier reports are unchanged.

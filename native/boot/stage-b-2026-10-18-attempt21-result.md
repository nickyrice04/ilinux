# Stage B attempt 21: macOS publishes the bulk-only interface and the reader streams 36,909 bytes; then the M5's dwc3 flags a DMA bus error, an apple-dart interrupt storm follows, and the stream stops

2026-10-18 (handoff 15:23:33 Eastern, 2026-10-18T19:23:32.987Z). **One RAM attempt consumed.
Controller PASS, no host panic.** boot039: one vendor-class `gser` function per controller, bulk IN and
bulk OUT only, no interrupt endpoint, `bcdDevice 0x0139`. The M5's screen was filmed for ten minutes
(the recording started before the launch) and the M1 read the port with its own read-only reader.

* **Controller:** exit 0 in 10.95 s (upload 8.89 s), handoff `19:23:32.987Z`, every gate PASS.
* **No EP0 timeout, no transaction error, in 10 minutes.** The M1 enumerated the device 3.88 s after
  the handoff, macOS selected configuration 1 at +8.05 s, the device stayed enumerated and configured
  until the human rebooted the M5 at +614.8 s. Attempt 18's wedge (four EP0 timeouts right after the
  configuration) **did not recur** with a bulk-only function.
* **macOS publishes the vendor interface, binds no driver, and the reader opens it** (interface only,
  IN pipe only, no entitlement): `IOUSBHostInterface` interface 0, class `0xff`, two endpoints (bulk IN
  `0x81`, bulk OUT `0x01`). The reader opened it at +8.1 s.
* **Bulk-IN data flowed, then stopped.** The capture is **36,909 bytes: 476 intact, ordered records of
  the M5's kernel log, kernel time 0.064256 to 0.076303 s** (the oldest records still in its buffer).
  Nothing more arrived in the next 10 minutes: the reader's 5 s reads timed out 119 times with 0 bytes
  and no STALL status.
* **On the M5's screen (read from the video):** from the first heartbeat after the host configured the
  device (kernel 8.49 s) and in **every** heartbeat after it (to the last one visible, 116 at 587.3 s),
  port 1 reads `configured … dwc3 On … ev0 BUSERR irq146 … 1in bulk h17 d105`, with `q8192` (log FIFO
  full) and counters that never change again except the frame number `f`. At kernel 9.956 s Linux
  printed **`irq 43: nobody cared`** with a call trace, `handlers: … apple_dart_irq` and
  **`Disabling IRQ #43`** (the digit is the one uncertain reading, see Media and method).
* **Linux itself stayed healthy:** one CPU, the 50-domain release ladder complete at ≈ 45.0 s, the 60 s
  milestone line at ≈ 63 s, heartbeats 000-116 every ≈ 5.03 s with no reset and no panic.
* **The first dwc3 register reads on this hardware were harmless**, and the TX FIFOs are sane:
  `32 endpoints (16 IN), MDWIDTH 128; TX FIFO words 0:35 1:199 2:199 … 15:199; RX FIFO words 1000`.
* Human-reported: the M5 had to be booted into the iLinux Boot Lab **again** before the M1 saw the
  m1n1 device (two cable re-seats alone did not help); a macOS permission prompt appeared on the M1
  early in the run and was accepted quickly; the M5 was rebooted into Macintosh HD right when ten
  minutes were up.
* Fresh policy/default checks: **NOT CHECKED.** No retry or settings change.

## Reviewed inputs and controller execution

* M5 handoff `7905adb`; M1 readiness `38f9f9f` (the launch ran on that commit, clean tree, record at 0
  attempts before the launch).
* The boot039 package, verified against Git before extraction and not re-downloaded: archive 18,915,359
  bytes, SHA-256 `b85c8d45…7d51`, manifest digest `88346489…4df5`; launcher `4d55f0c9…` unchanged; client pin
  `57a9339`; the reader binary (built from the committed source, 55,520 bytes, `77677ee3…`) matched the record.
* One invocation through `build/native-intake/run-attempt21.py` (the sanitized one-shot wrapper):

| Item | Result |
|---|---|
| Invocation count | 1 |
| Start / handoff UTC | 2026-10-18T19:23:22.254 / 19:23:32.987 |
| Elapsed / exit | **10.95 s / 0** (upload 0.87-9.76 s, 8.89 s) |
| Package, mode | PASS; `Mode: LIVE RAM LAUNCH` |
| Fixed arguments | `console=tty0 fbcon=nodefer rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 idle=nop arm64.nowfxt pd_ignore_unused clk_ignore_unused loglevel=8 ignore_loglevel printk.time=1 panic=0 earlycon=ilinuxfb initcall_debug initcall_blacklist=clk_debug_init ilinux_probe_diag=1` |
| Primary interface, target | PASS: 1209:316d, CDC data interface 1; t6050, boot021 marker, no started secondaries |
| GPIO ADT | PASS: 221 pins / 7 groups, exclusions 5,6,7,112,141 |
| Board/framebuffer, DAPF layout and correction | PASS (96-byte correction, readback verified) |
| Final hardware DT, framebuffer descriptor | PASS (16-byte descriptor, readback verified) |
| kboot reply / USB close | PASS |

* **M1 host:** freshly restarted (uptime about 14 min at the launch; the CPU was 88% idle), `caffeinate -di` running,
  no panic report during or after the run (the newest report on file is attempt 15's).

## Before the launch

* The pre-flight (19:15:38Z, host up 6 min) was clean, but the read-only USB gate **failed**: the M1 saw no USB device
  at all, not even the M5's m1n1 (the gate stops with an empty registry listing). A 60 s poll saw none. After the
  human's first cable re-seat (19:19:27Z) still none for 30 s. The human then booted the M5 into the Boot Lab
  again; the gate passed at 19:21:42Z (the m1n1 device present). This is the same "invisible after a fresh M1
  restart" condition as attempts 17 and 18, but here the re-seats alone did not clear it.
* The reader's `--dry-run` with only the m1n1 attached (19:21:57Z) found no `1d6b:0104` device, exited 2, created no
  capture and left no lock. The registry picture before the launch was saved locally (one device).
* No port was opened and nothing was sent before the launch at 19:23:22Z.

## Media and method

`Attempt21.MOV` (it arrived in the repository root and was moved into the ignored inbox before any commit):
**601.0 s, 1920×1080 landscape, 29.97 fps, original file** (1.2 GB). It starts about 9 s before the handoff, on m1n1's
`Running proxy...` screen, and ends at kernel ≈ 591 s. **Kernel ≈ video − 9.5 s (±1 s)**: the first Linux frame is
between video 8 and 10 s, and heartbeats 045 and 116 are the last ones visible at video 240 s and 598 s.

The console is 432 columns wide, so at 1080p a character is about 3 px wide and the long `[ctl]` lines are small.
Apple's Vision text recognition returned nothing on this footage, and a frame-averaging helper only smeared the picture,
so **every value below was read by eye from upscaled single frames.** Whole words and the repeated lines are
unambiguous (`configured`, `BUSERR`, `q8192`, `h17 d0`, `h17 d105`, `irq146`, `nobody cared`, `apple_dart_irq`,
`Disabling IRQ`, `ladder complete: 50 domains released`); the digits in `605L`, `46250B`, `f…`, `core 0x33313130`
and the timestamps are good to about one digit. **The IRQ number in the trace is the weakest reading:** it reads `43` in the
sharper frames (video 24, 26 and 33 s) and looked like `83` in blurrier ones; `43` is also the first of the three
`apple-dart fault handler` IRQs registered at 3.3 s, which is why this report uses it (Likely, not certain).
The late frames (t = 598 s) are the sharpest; a count that reads the same in every frame of the run (`irq146`, `h17`,
`d105`, `q8192`) is reliable. Review images deleted; the media stays local.

## M5 screen, literal observations

| Kernel s | Observation |
|---:|---|
| ≈ 3.3 | PID 1's `/proc/interrupts`: `arch_timer` (33), **three `apple-dart fault handler` lines at IRQ 43, 44, 45** (AIC2 hwirq 66959, 66991, 67023), mailbox IRQs 63 and 64. `[ctl] debugfs on /sys/kernel/debug: dwc3 state in every status line` |
| 3.3-3.65 | `[ctl] USB control channel: GSER bulk-only kernel log port per UDC, no interrupt endpoint, no network`; three `port N: UDC … bound, GSER bulk-only 1d6b:0104 bcdDevice 0x0139, no interrupt endpoint, log on ttyGS0/1/2` lines; `dropbear start 1: … port 22, key-only root` |
| 3.45-3.48 | heartbeat 000 `online_cpus=1`. One-time line per port, identical for all three: `dwc3: core 0x33313130, 32 endpoints (16 IN), MDWIDTH 128; TX FIFO words 0:35 1:199 2:199 3:199 … 15:199; RX FIFO words 1000`. Status lines: all three ports `not attached`, `log 104L / 103L / 102L 8192B q8192 dwc3 Suspend f0 ev0 irq0 ep0 o:start i:rsc` |
| **8.49** | heartbeat 001. **Port 1: `configured log 605L 46250B q8192 dwc3 On f14975 ev0 BUSERR irq146 ep0 o:start i:start 1out bulk h17 d0 1in bulk h17 d105`.** Ports 2 and 3 unchanged (`not attached`, `Suspend`, `f0`, `irq0`, `q8192`) |
| **9.956-9.98** | `irq 43: nobody cared (try booting with the "irqpoll" option)`; `CPU: 0 … Comm: swapper/0 … PREEMPT`; `Hardware name: Apple MacBook Pro (16-inch, M5 Max)`; a call trace (`show_stack`, `dump_stack_lvl`, `__report_bad_irq`, `note_interrupt`, `handle_irq_event`, `handle_fasteoi_irq`, `generic_handle_domain_irq`, `aic_handle_irq`, `call_on_irq_stack`, `el1h_64_irq` … `arch_cpu_idle`, `do_idle`, `cpu_startup_entry`, `rest_init`, `start_kernel`); `handlers:` with one entry, `apple_dart_irq`; **`Disabling IRQ #43`** |
| 13.55 | heartbeat 002: port 1 unchanged except `f` |
| 19.4-45.0 | the release ladder (`ladder 1: release atc3_usb_aon` at 19.42 s), one domain per ≈ 0.5 s, **`ladder complete: 50 domains released` at ≈ 45.0 s** (as attempts 17 and 18) |
| ≈ 63.2 | `[diag] 60s elapsed: still alive. Observe the M5 framebuffer and the M1's bulk log reader.` |
| 13.55 → 587.34 | heartbeats 002-116 every ≈ 5.03 s. Port 1's line is the same string every time except `f` (a different frame number at every heartbeat, so the host keeps sending SOFs and the link stays `On`): `BUSERR`, `ev0`, `irq146`, `605L 46250B q8192`, `ep0 o:start i:start`, `1out bulk h17 d0`, `1in bulk h17 d105`. Ports 2 and 3: `not attached`, `Suspend`, `f0`, `irq0` throughout. **No other line appears between heartbeats** except the ladder lines and the 60 s line (checked in frames at video 33, 66, 120, 150, 240, 300, 360, 420, 480, 545 and 598 s, which together show every heartbeat block 000-116). Neither `[ctl] dwc3 status reader … did not finish in 2 s` nor `[ctl] log streamer for port N exited` appears |

Reading the fields with the M5's legend (`native/boot/boot039-bulk-log-2026-10-16.md`): `BUSERR` is GSTS's bus-error bit;
`irq146` is the dwc3 interrupt count and it never moved after heartbeat 001; `ev0` means no event is waiting; `h17 d105` is
17 TRBs owned by the hardware on endpoint 1 IN with the dequeue index stuck at 105; `q8192` is the 8 KiB tty FIFO full.
`B` (≈ 46,250) is the bytes the tty accepted: with `q8192` that is ≈ 38,058 B handed to the gadget, of which the M1
captured 36,909; about 1.1 KB (Likely) was queued in the controller and never reached the host.

## M1-side observations (read-only)

Times relative to the handoff `T0 = 19:23:32.987Z` (the host log is local Eastern time, UTC−4):

| +s | Event |
|---:|---|
| +0.24 | m1n1's device destroyed (`hardware connection lost`) |
| +3.88 | enumerated `0x1d6b/0104/0139`, "iLinux J716c control channel, port 1", 480 Mbps; **`device functionality blocked by transport restrictions`**, `device will not be registered for matching` |
| **+8.05** | `AppleUSBHostCompositeDevice selected configuration 1` (4.2 s after the block; the human reports accepting a macOS permission prompt early in the run, not identified further) |
| +8.1 | reader: identity checked (`bcdDevice 0x0139`, interface 0, class `0xff`, configuration 1), registry path `…usb-drd2-port-hs@02100000/iLinux J716c control channel, port 1@02100000/IOUSBHostInterface@0`, speed 3; descriptors: one bulk IN `0x81`, one other bulk `0x01`; reading starts |
| +8.1 to +13.4 | **36,909 bytes** (consistent with two full 16,384-byte reads and a third of 4,141 B; the first sidecar total is at +13.4 s) |
| +13.4 to +611.7 | **119** reads of 5 s each time out with 0 bytes (`endpoint 0x81: status 0xe00002d6 (timeout)` in the kernel log, each one the reader's own request); never a STALL, never another status |
| +611.7 | reader stops by itself (`--seconds` reached), exit 0, lock released, capture and sidecar written |
| +614.78 | the iLinux device is gone (`hardware connection lost`), 3.0 s after the reader exited, followed by port power-off/on events within 2 s: consistent with the human's reboot of the M5 at the ten-minute mark (reported) |

* **Host kernel log (filter as attempt 18): 134 lines; endpoint-0 timeouts: 0; transaction errors: 0.** The 119 timeouts are
  all on the bulk-IN endpoint `0x81` and are the reader's own 5 s requests. In attempt 18 the same filter showed four
  endpoint-0 timeouts and a transaction error.
* **`ioreg` at +5 s and +60 s (saved locally, summaries only below):** device-level driver `AppleUSBHostCompositeDevice`;
  one `IOUSBHostInterface` (interface 0, alternate 0, class/subclass/protocol 255/0/0, two endpoints) whose only client is
  `AppleUSBHostFrameworkInterfaceClient [bulk-log-reader]`; plus the device-level `AppleUSBHostDeviceUserClient`s. No driver
  bound the interface. **Confirmed: a user client can open a vendor-class interface of this device without an entitlement.**
* **The capture** (`SHA-256 e71a29b6…`, 36,909 bytes, ignored): 476 records, each ending in exactly one CR LF (no bare CR or
  LF, no non-printable byte), kernel timestamps 0.064256 to 0.076303 s and monotonic, ending on a record boundary (the last
  record is an initcall `calling … @ 1` line). It holds no `dwc3`, gadget or `[ctl]` line: it covers the first 12 ms of the
  M5's boot log, and the stream stopped long before the log reached the interesting part.
* No `/dev/cu.usbmodem*` and no network interface were expected or seen (no function binds on the M1).

## Cross-check against attempts 17 and 18

The same screen region was checked in the attempt-17 and attempt-18 videos: PID 1's output from the start to kernel ≈ 31 s
(attempt 17, EEM, no host driver) and ≈ 20 s (attempt 18, ACM + ECM) holds **no** `nobody cared` trace and no
`apple-dart` message (one frame each; `apple-pmgr-purstate … sync_state() pending` lines only). The interrupt storm is new
in attempt 21, which is also the first run in which the host actually read bulk-IN data.

## Interpretation (bounded)

**Confirmed:**

* The reader works as designed on real hardware (identity, interface-only open, IN-only reads, timeouts kept, own stop and
  lock release), and macOS 26.0.1 lets it open the vendor interface.
* With **no interrupt endpoint**, EP0 stayed healthy for 10 minutes: configuration, SOF counting, no timeout, no transaction
  error. Attempt 18's EP0 wedge is **not** reproduced by a bulk-only function, so it needed something only ACM/ECM had
  (the interrupt endpoint, their class descriptors and requests, the second function, or IN endpoints 2-4).
* The TX FIFOs are not the problem: all 16 IN endpoints have 199 words (3,184 bytes), the RX FIFO 1000 words. The M5's
  "FIFO alternative" for attempt 18 is not supported by these numbers.
* Bulk-IN data moved (36,909 bytes, intact and in order) and then stopped, with the link up and SOFs counting. The M5's own
  dwc3 line says the controller flagged **`BUSERR`** and stopped taking interrupts (`irq146`, `ev0`), with 17 hardware TRBs
  queued on `1in` and its dequeue index frozen; Linux then took an unhandled **apple-dart** interrupt storm and disabled IRQ 43.
* The failure happened within about a second of the reader's first read (the port-1 state is already final at kernel 8.49 s,
  and the reader started reading about 0.7 s earlier by the M1's clock) and **before** the release ladder started (first release
  at 19.42 s), so the ladder is not the cause.

**Likely (not tested):**

* The stall is a **DMA bus error on the dwc3's path through its DART**, as the M5's own reading table says for `BUSERR`
  ("the DART mapping (stream id, window) is suspect"). It appeared with the first bulk-IN traffic: in attempts 17 and 18 the host
  exchanged only EP0 traffic (descriptor replies) with the device and no driver ever bound a bulk interface, so bulk-IN DMA had
  not run on this hardware before.
* The storm means a DART interrupt was asserted and `apple_dart_irq` returned `IRQ_NONE` roughly 100,000 times (the
  kernel's "nobody cared" threshold), so the error was neither reported (no `apple-dart … fault` message ever appeared)
  nor cleared.

**Hypothesis:**

* The t6050 DART's error-status layout or flag differs from what the Linux handler checks, so the handler never recognises
  the fault. IRQ 43 is the first of the three `apple-dart fault handler` lines registered at 3.3 s; which DART that is
  was not read (the DT order suggests the one in front of port 1's controller, which is the one the M1 was cabled to).
* Attempt 18's EP0 wedge may or may not share this DMA cause; nothing here tests it.

**Not established:** which DART IRQ 43 is, with certainty (the digit and the mapping); the faulting address, stream or window; whether the first IN TRBs, the data
buffers or the TRB ring crossed an unmapped range (36,909 bytes passed first); bulk OUT; a working log stream, SSH or
web access; anything about the M5's log beyond kernel 0.076 s; power, performance, input or storage.

Against the M5's reading table the run is the row **"port `configured`, log flowed, then `q` climbs and `d` stops"** with the
dwc3 line showing **`BUSERR`**, not the "bulk path works" row.

## Return and next handoff

* The human rebooted the M5 into Macintosh HD right when ten minutes were up ("not sure if I should have waited"): waiting
  would not have added information, because every field except `f` was static from heartbeat 001 on. The return to the
  Macintosh HD desktop is human-reported; the M1's host log fits it (device lost at +614.78 s, ports power-cycled).
  Fresh policy/default/installed-object checks: **NOT CHECKED.** Attempt 21 is consumed; no retry or settings change. The
  fixed E1 probe is still **NOT RUN**.
* **Procedure notes for the next attempt:** (1) after a fresh M1 restart the gate may see nothing even after re-seats;
  booting the M5 into the Boot Lab again cleared it this time; (2) a macOS permission prompt appeared on the M1 within
  the first seconds and the human accepted it: the reader's 120 s wait covers a slow answer, but the checklist should
  tell the human to expect it (whether it appeared in attempts 17 and 18 was not reported to the M1).
* **For the M5 (proposals, not authorization):**
  * **Confirm the IRQ number and the DART behind each dwc3 core**: print the `/proc/interrupts` rows (and the DT node names) of every
    `apple-dart fault handler` after the USB cores bind and again at the first `BUSERR`, and say which one stormed (IRQ 43 here).
  * **Catch the fault before the storm**: have the status reader add GBUSERRADDR (lo/hi) from `regdump` when `BUSERR` is set,
    and have a diagnostic DART handler print the DART's error status and address once before returning, so the first fault is
    on the screen (and in the bulk stream) instead of the storm.
  * **Compare the DART setup with what macOS does** for the USB DARTs (stream ids, translation window, bypass or error
    registers) with REA, recording behaviours only (addresses, sequences, timings), and check how the t8110 handler's error
    flag and fields map onto t6050.
  * **Keep the evidence readable:** at 1080p the 432-column `[ctl]` lines are about 3 px per character. Add a short line of
    at most about 100 columns per port, such as `USB1 BUSERR irq146 B46250 q8192 h17 d105 f…`, or print the key fields in a
    larger console font, so the next film can be read without guessing digits.
  * Stop the streamer at the first `BUSERR` (or mirror the last N log lines to the framebuffer) so a stalled bulk path
    does not leave the interesting kernel messages un-streamed.
* The reader needs no change for the next attempt: it opened, read and stopped cleanly.

No media, raw target output, `ioreg` dumps, capture, RAM image or identifiers beyond the fixed gadget ones are committed.
Earlier reports are unchanged.

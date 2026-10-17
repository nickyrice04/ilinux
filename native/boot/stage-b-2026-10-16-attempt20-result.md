# Stage B attempt 20: a stable ten-minute Omarchy desktop with its live status screen and on-screen benchmarks

2026-10-16 (handoff 21:50:36 Eastern, 2026-10-17T01:50:36Z). **One RAM attempt consumed.
Controller PASS, no host panic.** The same boot as attempt 19 with the run-33 RAM root, filmed
for ten minutes with the recording started before the launch.

* **Controller:** exit 0 in 44.553 s, handoff 2026-10-17T01:50:36.135Z, every gate PASS. The
  227,080,994-byte upload took **42.38 s (5.36 MB/s)**.
* **As intended:** the status screen appears about 7 s after the handoff flash; the RAM root's own
  timer reads **`desktop ready 8.50 s after kernel start`**; Hyprland 0.56.2 runs "under
  start-hyprland (its watchdog)"; **no red notice** appears in any sampled frame. The counter
  reads `0:09:59` at the end of the clip (kernel ≈ 600 s).
* **Stable:** the counter and the waybar clock advanced for the whole clip (the clock `Thursday
  23:46` to `23:56`, at the real-time rate), memory in use stayed at 1.83-1.88 GiB after startup, and the kernel-log
  pane did not change after `ladder complete: 74 domains released` at kernel 55.268 s. The display
  extension domains (`dispext0`-`3_sys`) were released at 52.2-54.8 s and the screen kept updating.
  The M1's host log shows no USB event for 13 minutes after the handoff.
* **On-screen numbers (native, attempt 20; one CPU, software rendering running beside them, gcc
  16.1.1 `-O3 -march=armv8.4-a`; no parity claim):** the eleven benchmark steps finished in **348 s,
  11 of 11 OK** (the checklist expected about 75 s). Values below.
* **Observed, cause unknown:** DRAM-sized pointer chases read **604 ns (32 MiB) and 617 ns
  (128 MiB)**, which is what made the run slow; single-thread CPU and STREAM numbers sit at about a
  fifth of this machine's macOS baseline (context table below, no parity claim).
* View-only as designed; no USB device appeared on the M1 after the handoff (the boot035 DT has no
  controllers).
* Fresh policy/default checks: **NOT CHECKED.** No retry or settings change.

## Reviewed inputs and controller execution

* M5 handoff `3f7b24d`; M1 readiness `6d3f5b4` (the launch ran on that commit, clean tree).
* The boot035 package, re-verified against the Git pin and not re-downloaded: archive 16,723,179 bytes,
  SHA-256 `81cbbd1c…`, manifest digest `7635c5e4…`, Image `1131a1af…`.
* The RAM root run 33: 182,420,823 bytes, SHA-256 `67f25732…d3f7` (VM job 039, image built
  2026-10-17T00:43:51Z). It reached the M1 by AirDrop into the repository root (untracked, not ignored)
  and was moved into the ignored `build/ramroot/` before any commit. **Its content was not decompressed or
  inspected on the M1** (no zstd tool, nothing installed); the overlay source in Git was reviewed before the
  run (it writes only to tmpfs, runs the benchmarks under `timeout`, uses no network or disk).
* One invocation through `build/native-intake/run-attempt20.py`:

| Item | Result |
|---|---|
| Invocation count | 1 |
| Start / handoff UTC | 2026-10-17T01:49:51.9 / 01:50:36.135 |
| Elapsed / exit | **44.553 s / 0** (upload 42.38 s) |
| Package, RAM root, operator key | PASS; `RAM root PASS 182,420,823 bytes` (run 33); `Operator key: none` |
| Fixed arguments / m1n1 append | `console=tty0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 pd_ignore_unused clk_ignore_unused quiet`; m1n1 must append `idle=nop arm64.nowfxt` |
| Target, marker, secondaries | PASS: t6050, boot021 marker, none started |
| GPIO ADT | PASS: 221 pins / 7 groups, exclusions 5,6,7,112,141 |
| Board/framebuffer, DAPF layout and correction | PASS |
| Final hardware DT, framebuffer descriptor | PASS |
| kboot reply / USB close | PASS |

* **M1 host:** freshly restarted (uptime about 3 min at the launch; the launch waited about 40 s for the
  CPU to be at least 78% idle), `caffeinate -i` running, no panic report during or after the run (the
  newest report on file is attempt 15's).

## Before the launch

The pre-flight and the read-only USB gate passed at 01:49:06Z on the first try (cable re-seated after the
restart, the M5 booted into the Boot Lab, the recording started before the launch command). The M1's load
average was 201 at 2 minutes of uptime, so the launch waited about 40 s for the CPU to reach 78% idle,
as in attempt 19. No port was opened and nothing was sent before the launch at 01:49:51Z.

## Media and method

`Attempt20.MOV` (the file arrived in the repository root under another name and was moved and renamed into the
ignored inbox before any commit): **646.435 s, 1920×1080 landscape, 29.94 fps, original file** (1.29 GB). It starts
about 43 s before the handoff flash, so **it holds the m1n1 proxy screen, the upload and the handoff**, and
ends at kernel ≈ 601 s. The phone was fixed and the whole panel is in frame.

Time mapping: the brightness dip at video 42.8 s is the handoff; the first kernel lines are on screen by
44.5 s; the status counter reads `0:00:05` at video 50.2 s and `0:09:59` at 644 s. So **kernel ≈ video −
44 s (±1 s)**. Reviewed locally with AVFoundation (brightness traces, frames, upscaled crops) and Apple's Vision
text recognition (about 50 frames at 6-15 s intervals, read for the counter, CPU, load, clock, memory, benchmark status
and log lines; the rows in the table were also read by eye from three frames and agree). Review images deleted;
media stays local.

## M5 screen, literal observations

| Video s | Kernel s | Observation |
|---:|---:|---|
| 0-42 | n/a | m1n1's proxy screen (`Running proxy...`, `Heap limit`, its logo); the upload is silent |
| 42.8 | ≈ 0 | handoff flash |
| 44.5 | 0.03-0.06 | early kernel lines at the top left (the same five error-level lines as attempt 19: `kvm_arch_timer` invalid virtual timer IRQ, `apple-pmgr-pwrstate … PS cs: Failed to reach power state`, `PM: always-on PM domain cs is not on`, `pm_genpd_init failed`, probe error -22) |
| **49.8-50.2** | ≈ 5 | **first status-screen frame**: counter `0:00:05`, `desktop not ready yet`, benchmarks `waiting for the desktop`, kernel-log pane showing systemd lines stamped 2.271-2.316 |
| 53 | 7-8 | waybar visible; counter `0:00:07`; `cpu 100% busy`; clock `Thursday 23:46` |
| 58-70 | ≈ 14-26 | benchmark steps 2-10 run; `running membench latency (11/11)` from video ≈ 70 s |
| 140 | ≈ 96 | counter `0:01:36`; `desktop ready 8.50 s after kernel start`; ladder lines 70-74 and `ladder complete: 74 domains released` at 55.268 in the pane; clock `Thursday 23:47` |
| ≈ 400 | ≈ 357 | `done in 348 s · 11 of 11 steps OK` (first seen between video 390 and 405 s); CPU busy falls from 100% to 38-40% |
| 644 | ≈ 600 | counter `0:09:59`, `cpu 40% busy`, load `0.44 0.83 0.58`, clock `Thursday 23:56`, pane unchanged since 55.268 |

The status screen at the end (read at 644 s):

```
iLinux RAM root · Omarchy-style Hyprland desktop · one CPU · software rendering · view-only
kernel   7.1.9-g863199d8b4a3-dirty · 16384-byte pages · 1 CPU · image built 2026-10-17T00:43:51Z
display  card0 on simple-framebuffer · 3456x2160@60 · scale 2 · Mesa 26.2.4 llvmpipe (software rendering)
session  Hyprland 0.56.2 under start-hyprland (its watchdog) · desktop ready 8.50 s after kernel start
memory   1880 MiB in use (MemTotal - MemFree) · 127047 MiB available of 129351 · load 0.44 0.83 0.58

since kernel start  0:09:59  (599 s)    cpu 40% busy over the last second

benchmarks  single thread · gcc 16.1.1 -O3 -march=armv8.4-a · done in 348 s · 11 of 11 steps OK
cpu      freq 2.65 GHz est   fma_asm 29.8 GFLOP/s   fma 28.5 GFLOP/s   intmix 5.00 Gop/s
         sort 4.94 Melem/s   sgemm 11.6 GFLOP/s     syscall 352 ns     pingpong 3.99 us (both ends on the one CPU)
stream   copy 28.2 · scale 19.9 · add 25.0 · triad 24.7 GB/s (median of 4, 3 × 128 MiB arrays)
latency  16 KiB 2.37 · 4 MiB 15.3 · 32 MiB 604 · 128 MiB 617 ns (random pointer chase, 128-byte lines)
fault    first touch 42.7 GB/s · 1 GiB mapped and touched, 16384-byte pages
```

The rows already filled at video 140 s and 300 s (all but the two largest latency sizes) are identical to the
final ones. Steps 1-10 took 16 s in total (the status header reads `running membench latency (11/11) · 16 s so
far` from then on); the pointer chase (step 11) took about 332 s. Ladder step 4 (`atc2_usb_aon`) was
stamped 18.916, so the ladder started at ≈ 17.4 s (one step per 0.512 s); step 68 (`atc2_common`) was stamped 51.688.

**Context only, not a parity claim.** This machine's own macOS baseline in `benchmarks/results/macos-2026-10-11-ac-lpm/`
(single thread, a performance core, Apple clang 21, STREAM arrays of 1 GiB, taken on AC power with Low Power Mode on
per its `env-start.txt`):

| Row | macOS baseline | Native, attempt 20 | Ratio |
|---|---:|---:|---:|
| fma | 125.0 GFLOP/s | 28.5 | 0.23 |
| intmix | 20.9 Gop/s | 5.00 | 0.24 |
| sort | 23.4 Melem/s | 4.94 | 0.21 |
| sgemm | 60.2 GFLOP/s | 11.6 | 0.19 |
| STREAM copy / scale / add / triad | 138.6 / 122.4 / 123.6 / 123.2 GB/s | 28.2 / 19.9 / 25.0 / 24.7 | 0.20 / 0.16 / 0.20 / 0.20 |
| chase 16 KiB | 0.85 ns | 2.37 | 2.8× |
| chase 4 MiB | 7.72 ns | 15.3 | 2.0× |
| chase 32 MiB | 51.3 ns | 604 | 11.8× |
| chase 128 MiB | 106.2 ns | 617 | 5.8× |
| first touch | 31.5 GB/s | 42.7 | 1.36 |

## M1-side observations (read-only)

* No USB device appeared on the M1 after the handoff. The host kernel log has one line at the handoff: m1n1's
  device destroyed (`hardware connection lost`) 0.21 s after it; then **no USB event for 13 minutes**; at 22:03:48
  Eastern the port powered off and on (consistent with the M5 being shut down), after which a USB device named
  `Mac` appeared (consistent with the M5 back in macOS; not independently verified).
* The M1 stayed healthy (load settled, no panic).

## Interpretation (bounded)

**Confirmed:**

* The run-33 image does what its handoff said: the session goes through `start-hyprland` with no notice, the
  status screen is live (counter, CPU, memory, load, kernel-log tail), and all eleven benchmark steps finished.
* The native desktop is stable for ten filmed minutes on one CPU with software rendering: counter and clock
  advance, memory use is flat, and the kernel logs nothing after the release ladder. The ladder (hidden by `quiet`
  on the console, shown in the pane) completed all 74 domains at 55.268 s, as in attempt 16, and the display
  survived the release of the display extension domains.
* Time to the status screen: about 7 s after the handoff flash, about 5 s after kernel start; ready at 8.50 s.

**Observed, effect unknown:**

* **The chase is slow:** 604 and 617 ns at 32 and 128 MiB against 51 and 106 ns in the macOS baseline; the larger
  chase sizes dominated the 348 s. The 16 KiB and 4 MiB rows are 2-3× the baseline.
* **Single-thread throughput is about a fifth of the baseline's** in every compute row and in STREAM.
  *Hypothesis:* CPU 0 is an efficiency-class core at about 2.65 GHz with no frequency scaling (`freq 2.65 GHz est`;
  `fma_asm` gives about 11 FLOP/cycle at that estimate; the baseline's 125 GFLOP/s would be about 28 FLOP/cycle if its
  core ran near 4.5 GHz, which was not measured, and that would fit two FMA pipes against four).
  *Hypothesis:* the STREAM gap follows from the long DRAM latency, since one core's bandwidth is bounded by its
  outstanding misses. First-touch at 42.7 GB/s is above the baseline, so writes to fresh pages are not slow.
  Nothing here identifies the core; `/proc/cpuinfo` was not displayed.
* **Order matters:** steps 1-10 ran at kernel ≈ 10-26 s; the ladder started at ≈ 17.4 s, so STREAM (step 9, at
  ≈ 23-25 s) ran after about a dozen of the 74 ladder steps and the CPU kernels mostly before it. The latency step
  began at ≈ 26 s, during the ladder, and its 32 and 128 MiB rows were measured minutes after it. So the STREAM gap
  was already there before most domains were released, but the DRAM-latency rows were measured after the whole ladder.
* **The idle desktop is not idle:** after the benchmark, CPU busy stays at 38-40% over each second (waybar, the
  status screen's per-second redraw and llvmpipe on one CPU).

**Not established:** parity with anything, power and thermals, GPU acceleration, input, storage, networking, USB,
SMP or idle states, and the RAM-root image content. One run; one CPU of unknown class.

## Return and next handoff

* The human stopped recording, powered the M5 off and returned it to the Macintosh HD desktop (reported; the M1's
  host log fits it, as above). Fresh policy/default/installed-object checks: **NOT CHECKED.** Attempt 20 is consumed;
  no retry or settings change. The fixed E1 probe is still **NOT RUN**.
* **For M5 (proposals, not authorization):**
  * show the core: print `/proc/cpuinfo`'s implementer and part (and the cluster, if the DT names it) on the status
    screen, and decide whether the next measurement should run on a performance core (SMP bring-up or another boot
    CPU), since every number so far is the boot CPU's;
  * separate the memory question: run one 128 MiB chase before the release ladder starts (kernel < 18 s) and the
    same chase again after it (> 60 s), then compare with the macOS baseline's 106 ns;
  * shorten the benchmark's long step (fewer chase sizes) or move it last, so the first ten numbers do not wait on
    it; consider a slower redraw during long runs so the idle CPU reading means something;
  * the USB link (boot039, bulk-only) remains the route to SSH and proper measurement; the M1 can build and
    offline-test a user-space reader once the function is chosen.

No media, raw target output, RAM-root image or identifiers beyond the fixed gadget ones are committed. Earlier
reports are unchanged.

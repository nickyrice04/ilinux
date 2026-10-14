# Stage B — attempt 8 / boot027 deferred-probe diagnostics

**Attempt 8 is consumed (2026-10-14).** M1 readiness `174419e`; controller exit
0 and native counter PASS/25 ticks observed. Phase 1/timer status last visible;
phase 2 and diagnostic userspace/liveness NOT OBSERVED. Macintosh HD return
human-confirmed. See `native/boot/stage-b-2026-10-14-attempt8-result.md`.
M5 read-only return checks and offline analysis next. **Do not rerun the launch
below**; it is retained as the reviewed procedure for the completed attempt.

**Reviewed pre-attempt instructions for M1.** Pull latest main with `git pull --ff-only`;
preserve local work and stop on divergence. Read `coordination.md` and this
file. Attempt 7 is consumed: it reached `deferred_probe_initcall` after the
previous clock boundary, with no diagnostic userspace observed. Boot027 keeps
that progress and adds bounded phase/timer diagnostics; it does not establish
the root cause. **At publication: attempt 8 / native boot027 / live checks NOT RUN.**

**Continue the existing installation.** The lab entry, original Macintosh HD,
installed boot021 m1n1 and clean client pin remain correct. Do not repeat Stage
A, provisioning, Recovery, macOS installation, `bputil`, `kmutil`, partitioning,
security changes or m1n1 installation. Keep Macintosh HD at Full Security and
as the default. No new SMP, DVFS, storage or peripheral experiment is included.

## What changed

* New private release `native-j716c-boot027`: only **Image** changes from
  boot025. DT, initramfs, config, installed/staged m1n1 and client are unchanged.
  Keep earlier packages and records. Boot026 was a controller-only experiment;
  there is no missing package to install.
* Fixed args retain the single `initcall_blacklist=clk_debug_init`, adding only
  `ilinux_probe_diag=1`. No additional skipped initializer.
* Stricter offline/final-DT validation checks the t6050 CPU topology, AIC3 core/
  event layout, unique parent and named host/guest timer routes. The existing
  live chip/board/version, no-secondary, DAPF and framebuffer checks remain.
* The kernel reports target/EL/CPU count, a 100 ms counter/tick test, architectural timer/mask status, phases of
  deferred probing, and at most six five-second watchdog messages. A failed
  timer check explicitly stops the RAM test. Driver probes are not bypassed.
* M5 full Image link and **11 actual-helper sanitizer scenarios PASS**;
  **90 controller cases**, **13-file intake**, exact ELF/Image bytes and generic
  one-CPU VM timer/phases/PID-1/60-second liveness PASS. Native behavior untested.
  Read `kernel/experiments/deferred-probe/README.md` for evidence and limits.

## Return protection prerequisite — already PASS

Fresh post-attempt-7 user JSON: original **Full**, lab **Permissive**, both exit
0. M5 independently read root Macintosh HD, build 25G83, FileVault=true, SIP
on, and unchanged staged m1n1 SHA. Default selection/installed boot object/
authenticated-root were not separately re-queried. No settings changed. Do not
request the same check again or introduce another M1↔M5 approval loop unless
new evidence changes the state.

## Offline intake before the human restarts

Run from the repository root, stopping on any failure. No USB is opened here.
Download only this new package. Verify its archive against current Git before
extracting. Stop on mismatch; never overwrite a previous package to hide it.

```sh
(
set -e
mkdir -p build/native-boot027-download
if [ ! -f build/native-boot027-download/ilinux-j716c-boot027.tar.gz ]; then
  gh release download native-j716c-boot027 --repo nickyrice04/ilinux \
    --pattern ilinux-j716c-boot027.tar.gz --dir build/native-boot027-download
fi
(
  cd build/native-boot027-download
  shasum -a 256 -c ../../native/boot/archive-sha256.txt
  if [ ! -d ilinux-j716c-boot027 ]; then tar -xzf ilinux-j716c-boot027.tar.gz; fi
)
mkdir -p build/native-intake/receipts build/native-intake/results
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot027-download/ilinux-j716c-boot027 \
  --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
  > build/native-intake/receipts/boot027-attempt8.json
python3 -I native/boot/launch.py --package build/native-boot027-download/ilinux-j716c-boot027
python3 -I native/boot/test_launcher.py
python3 -I native/boot/test_entry_guard.py
python3 -I native/boot/test_dapf_guard.py
python3 -I native/boot/test_framebuffer.py
python3 -I native/boot/test_hardware.py
tools/m1n1-client/run.sh native/boot/test_dapf_guard_adt.py
tools/m1n1-client/run.sh native/boot/test_launcher_adt.py
M1N1_SOURCE="$PWD/third_party/m1n1" tools/m1n1-client/run.sh native/boot/test_protocol.py
)
```

Require **37 + 6 + 16 + 5 + 19 + 2 + 4 + 1 = 90 cases PASS**, package PASS,
13 verified receipt files and the clean pinned client. No kernel build or REA
setup needed on M1. The corrected receipt `next` refers to this current stage;
the receipt itself is not a live-boot authorization.

Archive **16,721,223 bytes**, SHA-256:
`33c7ff4d1f8e93c929a5024ebb19b7dee825cb14e1c7bf93f7df8c5526bf6a8c`.
Image (44,468,736 bytes):
`5a5ca64eaf2c3389e9fca226d7244150edbc8975738fe11a9304c0c996e29b64`.
SHA256SUMS digest:
`3006253a5747677845576c1ba71b67da48c33326d70fa52c7ea8f0c74bf2d6a4`.
Current Git manifests are authoritative. Stop on disagreement.

Reviewed controller digests (also record checked-out Git commit):

* `native/boot/launch.py`: `c2d2cd0b067b78ead957463e70f8c4694cdeee5dc5b7b54bd6ebf2b7f7fc0279`
* `native/boot/entry_guard.py`: `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713`
* `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
* `native/boot/fdt.py`: `d9522761837e78f7b444b936a7501fc9f847697d783b57de1f446a4b8da32b6b`
* `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

Prepare fresh ignored `boot027-stage-b-attempt8.json`/`.md` with source,
procedure/controller/payload hashes and receipt. Push sanitized readiness in
`progress.md` and `coordination.md`, leaving native/live checks NOT RUN. Tell the
human when ready. Once they choose to restart and report `Running proxy...`,
proceed once; no extra M5 review round trip for unchanged verified instructions.

## One human-started, filmed RAM boot

1. Both Macs on power, same direct cable/primary USB interface, M5 built-in
   display visible. Start a focused phone video **before launch**, 60 fps if
   available. Stop at readiness if recording cannot be arranged; do not spend
   another attempt without readable evidence. Full media stays local.
2. Human saves work, shuts down, holds power for startup options, selects
   **iLinux Boot Lab → Continue**. Keep Macintosh HD as default. If already at
   `Running proxy...` for this attempt, do not restart again.
3. On the human's start and matching proxy, call the reviewed launcher **once**:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot027-download/ilinux-j716c-boot027 \
     --launch --device auto --confirm BOOT-J716C-RAM-DIAGNOSTIC
   ```

   The existing sanitized wrapper may call this same `main(argv)` once. Never
   import `m1n1.setup`, start a shell, issue a separate handshake or auto-retry.
4. Record start/end/elapsed/exit, both DAPF checks, **Hardware DT PASS**, the
   framebuffer descriptor PASS, preflight/handoff and kboot reply. Preserve all
   gates. No raw target output, ADT, registers, memory or serial-bearing paths.
   For unexpected controller failure retain safe function/line/type and reviewed
   fixed message only; no locals. Stop on rejection; do not weaken detection.
5. USB proxy ends at handoff. Exit 0 is not a Linux success. Review the video,
   pausing it to recover the diagnostic messages rather than relying on the
   final photo alone. Record only sanitized checkpoint text:

   | Evidence | Interpretation / next action |
   |---|---|
   | `ilinux-probe: target=j716c-t6050 mode=EL2 cpus=1` (or actual reported EL) | Kernel identity/mode checkpoint. Wrong target/CPU count: stop, no override. |
   | `timer counter=PASS ticks=N` with **N > 0** | Counter and tick interrupt progress during 100 ms; not full driver validation. |
   | `timer counter=FAIL`, zero ticks, or diagnostic panic | Stop and return. M5 investigates timer/routing; do not skip the check. |
   | Phase 3 but no phase 4 | Debugfs operation is the next boundary to analyze. |
   | Phase 4 but no phase 5 | Deferred trigger/list mutex boundary. |
   | Phase 5 or 7 with heartbeat | Workqueue wait; record worker subphase, retry count and last compatible begin/end. |
   | Phase 9 | Deferred initializer finished; capture following initialization/PID-1 milestones. |
   | No new diagnostic line | Capture earlier last completed/called initializer or panic; do not assume this initializer ran. |
   | PID 1 + `online_cpus=1` + 60 seconds alive | Diagnostic userspace/liveness observed. Stop and return; next work is Linux control/input, not automatic installation. |

   Retain the `timer phys=N virt=N irq_masked=N fiq_masked=N` line. The low
   timer control bits mean enabled=1, masked=2, pending=4 (e.g. 5 is enabled,
   unmasked and pending). Pending is meaningful only when enabled; ignore that
   bit for a disabled timer. These are status observations, not a routing fix.
   A zero-tick result still requires a stop, regardless of these bits.

   Main phase meanings: 1 timer check, 2 watchdog armed, 3 debugfs entry,
   4 debugfs returned/trigger, 5 first flush, 6 first flush returned, 7 second
   flush, 8 second flush returned, 9 done. Heartbeat worker states: 0 not entered,
   1 initial mutex, 2 list processing, 3 PM ordering, 4 bus probe, 5 probe
   returned, 6 mutex reacquisition, 7 worker returned. Retry detail caps at 32;
   heartbeat caps at six (30 seconds). Missing heartbeat is not itself proof
   of an interrupt fault: console/softirq delivery can also stop.
6. Stop on controller failure or kernel panic, on the 60-second userspace
   milestone, or at **120 seconds from handoff**, whichever applies first.
   Calculate/report the exact deadline. The controller's own 180-second total /
   15-second transport limits remain. Do not reconnect, retry, expand the
   blacklist, enable storage/cores or change any setting during this attempt.
7. Guide the human back: hold power to shut down if needed, hold power for
   startup options, choose **Macintosh HD → Continue**. Confirm the usual
   desktop return. Do not assert fresh policies until read-only checks occur.
8. Push sanitized attempt-8 result and progress/coordination updates, retaining
   all prior results. Separate controller gates, native kernel, timer/phase,
   PID 1/CPU/liveness and return status. Report anything not observed as such.
   No full video/photo, raw dumps, personal identifiers or proprietary binaries.

M5 reviews the new evidence and applies the next targeted repair. Boot027 is
an observation improvement, not a claimed root-cause repair, Omarchy desktop,
GPU acceleration, all-core support or macOS-equivalent efficiency. The existing
installation and previous successful handoff milestones remain the baseline.

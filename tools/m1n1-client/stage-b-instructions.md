# Stage B — attempt 9 / boot028 scheduling-boundary diagnostics

**Attempt 9 is consumed (2026-10-14).** Readiness `87a80dd`; controller exit 0.
Reviewed video observes timer PASS/25 ticks, phases 1/10/11/12 and final
`reschedule pending=1 strip=0`. Phase 13, literal strip lanes/heartbeat and
userspace/liveness NOT OBSERVED. Macintosh HD return human-confirmed.
See `native/boot/stage-b-2026-10-14-attempt9-result.md`.
M5 read-only return checks and offline analysis next. **Do not rerun the launch
below**; the procedure is retained as the record of the completed attempt.

**Reviewed pre-attempt handoff.** Pull latest main with `git pull --ff-only`; preserve local
work and stop on divergence. Read `coordination.md` and this file. Attempt 8
is consumed: native counter/ticks passed, but phase 2 and diagnostic userspace
were not observed. Result: `native/boot/stage-b-2026-10-14-attempt8-result.md`.
**At this handoff: attempt 9 / native boot028 / live checks NOT RUN.**

**Continue the existing installation.** Installed boot021 m1n1 and the clean
client pin remain unchanged. Do not repeat provisioning, Stage A, Recovery,
macOS installation, `bputil`, `kmutil`, partitioning or m1n1 installation. Keep
Macintosh HD at Full Security and as the default. No volume/security changes.

## What changed and why

REA and linked instructions show that boot027 could reschedule before arming
its watchdog. Boot028 fixes that diagnostic gap, adds scheduler checkpoints
and a small bottom-left `P:xx S:xx W:xx H:xx` status strip. It can report a
boundary without printk/timer interrupts, if the existing scanout remains
visible. **Root cause remains unknown; this is not a confirmed hang repair.**

Only **Image** changes from boot027. The full kernel build, helper/renderer
ASan/UBSan checks, 90 controller cases, 13-file intake and exact-image generic
VM PID-1/one-CPU/60-second liveness PASS. The VM has no J716c framebuffer or
AIC and does not validate native behavior. See
`kernel/experiments/schedule-boundary/README.md` and `validation.json`.

DT/config/initramfs/m1n1 and all fixed args/hardware gates stay unchanged.
Retain the single `initcall_blacklist=clk_debug_init`; no wider skip. The compiled
idle NOP branch is already present. No new CPU, frequency or storage experiment.

## Return protection prerequisite — already PASS

Fresh post-attempt-8 human JSON: original **Full**, lab **Permissive**, both
exit 0. M5 independently read root Macintosh HD/build 25G83/FileVault=true/SIP
on and unchanged staged m1n1 checksum. Default selection/installed object/
authenticated-root were not independently re-queried. No settings changed.
Do not request the same check again or add another M1↔M5 approval loop unless
new evidence changes the state.

## Offline intake before the human restarts

Download only private `native-j716c-boot028`; verify the archive against current
Git **before extraction**. Preserve every earlier package/receipt/result. Stop
on a mismatch. The following performs no live USB action.

```sh
(
set -e
mkdir -p build/native-boot028-download
if [ ! -f build/native-boot028-download/ilinux-j716c-boot028.tar.gz ]; then
  gh release download native-j716c-boot028 --repo nickyrice04/ilinux \
    --pattern ilinux-j716c-boot028.tar.gz --dir build/native-boot028-download
fi
(
  cd build/native-boot028-download
  shasum -a 256 -c ../../native/boot/archive-sha256.txt
  if [ ! -d ilinux-j716c-boot028 ]; then tar -xzf ilinux-j716c-boot028.tar.gz; fi
)
mkdir -p build/native-intake/receipts build/native-intake/results
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot028-download/ilinux-j716c-boot028 \
  --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
  > build/native-intake/receipts/boot028-attempt9.json
python3 -I native/boot/launch.py --package build/native-boot028-download/ilinux-j716c-boot028
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
13 receipt files and the clean client pin `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
No kernel/REA setup on M1. The receipt verifies files, not live authorization.

Archive **16,722,641 bytes**, SHA-256:
`689fce13b00c4e59af61e5a23666509579985b89920a0477e4b107c6cf5944e9`.
Image **44,468,736 bytes**, SHA-256:
`514dde0c48c17d77d1979fb98b13f5ecb45096839e8b10a72d24adcf9df0778f`.
SHA256SUMS digest:
`0120ed68ecf994204a94b2ac2ef3e57a66ea37b9db1e7f61becaf5f4482b87b2`.
Git manifests are authoritative; stop on disagreement.

Reviewed controller digests (also record checked-out Git commit):

* `native/boot/launch.py`: `c2d2cd0b067b78ead957463e70f8c4694cdeee5dc5b7b54bd6ebf2b7f7fc0279`
* `native/boot/entry_guard.py`: `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713`
* `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
* `native/boot/fdt.py`: `d9522761837e78f7b444b936a7501fc9f847697d783b57de1f446a4b8da32b6b`
* `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

Prepare fresh ignored `boot028-stage-b-attempt9.json`/`.md` records with the
source/procedure/controller/payload/receipt hashes. Push sanitized readiness
in `progress.md` and `coordination.md`, keeping native/live checks NOT RUN.
Tell the human when ready. M1 readiness plus the human's start suffice; no
extra M5 review round trip for these unchanged verified instructions.

## One human-started, filmed RAM boot

1. Both Macs on power, same direct cable/primary USB interface. Film the M5
   built-in screen **before launching**, 60 fps if available. Include the bottom
   left edge where the new small status strip appears. Stop at readiness if
   recording cannot be arranged. Full media stays local.
2. Human saves work, shuts down, holds power for startup options and selects
   **iLinux Boot Lab → Continue**. Keep Macintosh HD as default. If already at
   `Running proxy...` for this attempt, do not restart again.
3. After the human starts and reports the proxy, invoke this **once**:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot028-download/ilinux-j716c-boot028 \
     --launch --device auto --confirm BOOT-J716C-RAM-DIAGNOSTIC
   ```

   The existing sanitized wrapper may call the same `main(argv)` once. No
   `m1n1.setup`, shell, separate handshake, reconnect or automatic retry.
4. Record times/elapsed/exit, all preflight and final Hardware DT checks,
   both DAPF checks/readback, framebuffer descriptor/readback and kboot reply.
   Preserve all gates. No raw target output/ADT/memory/register dumps or
   serial-bearing paths. Unexpected error: safe function/line/type and reviewed
   fixed message only; no locals, no weakening detection.
5. USB proxy ends at handoff. Exit 0 is not Linux success. Capture these:

   * Kernel `target=j716c-t6050 mode=EL2 cpus=1` (or actual reported EL),
     `timer counter=PASS ticks=N` and timer/mask status. N must be positive.
   * Phases 10, 11, 12; `reschedule pending=N strip=N`; phase 13 if it returns.
     `strip=1` means a mapping was available, not that every mark was visible.
   * **A close photo/paused frame of `P:xx S:xx W:xx H:xx`** at the bottom left.
     Values are hexadecimal; copy literally. Record changes over time, not just
     a final value. If absent/overwritten/unreadable, mark NOT OBSERVED.
   * Watchdog heartbeat, scheduler summary, first stack's symbolic function
     names/offsets, deferred retry compatible begin/end and later initcalls.
     Do not substitute inferred stack frames or collect unrelated identifiers.
   * Diagnostic PID 1, `online_cpus=1`, and the 60-second liveness milestone.

   P sequence is `01 → 0A → 0B → 0C → 0D → 02 ... 09`, so record the **last
   phase and sequence**, not the largest number. Printed decimal phases 10–13
   correspond to P=0A–0D. P=0C is before preempt_enable, P=0D after it.
   P=03 debugfs entry, 04 trigger, 05/07 worker flushes, 09 complete.
   S=01 scheduler entry, 02 before runqueue lock, 03 lock held, 04 task
   selection, 05 selected, 06 context-switch entry, 07 finish_task_switch,
   08 context_switch returned, 09 scheduler exit. S=07 can be normal for a
   newly created thread. W retains worker phases 0–7; H counts heartbeats 1–6.
   These are last boundaries, **not exact blocking PCs or diagnoses**.

   | Observation | M5 follow-up |
   |---|---|
   | P=0A/0B persists | Investigate watchdog initialization/arming and visibility |
   | P=0C persists | Use S and any heartbeat/stack to locate the scheduling boundary |
   | P=0D then P=03+ | Rescheduling returned; follow deferred-probe checkpoints |
   | Heartbeat with stack | Analyze interrupted task and symbolic frames |
   | No heartbeat but readable strip | Record frozen/changing P/S/W/H; no guessed interrupt fault |
   | P=09 | Capture later initialization and userspace |
   | PID 1 + one CPU + 60-second liveness | Diagnostic RAM userspace success; return, no install |

   Review the recording by pausing it **before publishing the result**. If the
   agent cannot access it, have the human pause/transcribe the relevant frames.
   If it remains unavailable, explicitly report that limitation. Avoid spending
   another restart with only an unreviewed recording and ambiguous last line.
6. Stop on controller rejection/kernel panic, the 60-second userspace milestone,
   or **120 seconds from handoff**, whichever applies first. Calculate/report
   the deadline. The controller retains 180-second total/15-second transport
   limits. No retry, extra blacklist, new cores/storage or settings change.
7. Return: hold power to shut down if needed, hold power for startup options,
   choose **Macintosh HD → Continue**. Confirm the usual desktop return.
   Do not assert fresh policies until the next read-only check.
8. Push sanitized attempt-9 report and progress/coordination updates. Separate
   controller, native kernel, strip/timer/scheduler, PID-1/liveness and return
   status. Preserve earlier reports; mark unobserved evidence honestly. Keep
   full media/raw data/proprietary binaries out of Git.

## Path toward Omarchy

Do not restart installation. The immediate gate is stable native diagnostic
userspace. Then M5 prepares Linux-side USB/input/control and a usable RAM root;
the Linux-side agent can handle packages, configuration and desktop tests once
that channel exists. GPU, SMP and efficient idle/DVFS need independent native
validation. Boot028 alone cannot establish Omarchy or macOS performance parity.

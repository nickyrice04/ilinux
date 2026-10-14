# Stage B — attempt 10 / boot029 display and context-switch checkpoints

**Attempt 10 consumed — 2026-10-14.** One boot029 launch completed with
controller exit 0; reviewed video shows native Linux and **P:05 S:09 W:04**.
H/diagnostic userspace/liveness are unobserved; small fields not confirmed.
Human confirms Macintosh HD return. Fresh protection/default checks pending
M5 read-only review. No automatic retry. See
`native/boot/stage-b-2026-10-14-attempt10-result.md`.
The checklist below is retained as the reviewed pre-attempt procedure.

**Reviewed pre-attempt M5 handoff, 2026-10-14.** Pull latest main with `git pull --ff-only`;
preserve local work and stop on divergence. Read `coordination.md` and this
file. Attempt 9 is consumed: reviewed video shows timer PASS/25 ticks, phases
1/10/11/12, then `reschedule pending=1 strip=0`. Phase 13, literal strip lanes
and diagnostic userspace/liveness were not observed. Macintosh HD return is
confirmed. See `native/boot/stage-b-2026-10-14-attempt9-result.md`.
**At this handoff: attempt 10 / native boot029 / live checks NOT RUN.**

**Continue the existing installation.** Installed boot021 m1n1 and the clean
client pin remain unchanged. Do not repeat provisioning, Stage A, Recovery,
macOS installation, `bputil`, `kmutil`, partitioning or m1n1 installation. Keep
Macintosh HD at Full Security and as the default. No volume/security changes.

## What changed and why

REA, exact source and a regression test confirm that the previous diagnostic
mapper skips initialization if the early console is absent or retired. Boot029
initializes independently from the validated DT, reports mapping/failure state,
enlarges the bottom-left `P:xx S:xx W:xx H:xx` strip to 4× glyphs and adds
context-switch subphases. The exact native `strip=0` prerequisite remains
unknown; native screen visibility must be checked.
**This repairs a confirmed diagnostic defect, not a proven native hang cause.**

Only **Image** changes from boot028. Full kernel build/ELF roundtrip, actual
helper/renderer/parser/mapper ASan/UBSan checks, old-defect reproduction,
90 controller cases, 13-file intake and exact-image generic VM PID-1/one-CPU/
60-second liveness PASS. The VM has no J716c framebuffer or AIC and does not
validate native behavior. See `kernel/experiments/context-display/README.md`
and its `evidence.json` / `validation.json`. REA omitted some context-switch
alternative paths; the full source/LLVM audit accounts for them.

DT/config/initramfs/m1n1 and all fixed args/hardware gates stay unchanged.
Retain the single `initcall_blacklist=clk_debug_init`; no wider skip. The compiled
idle NOP branch is already present. No new CPU, frequency or storage experiment.

## Return protection prerequisite — already PASS

Fresh post-attempt-9 human JSON: original **Full**, lab **Permissive**, both
exit 0. M5 independently read root Macintosh HD/build 25G83/FileVault=true/SIP
on and unchanged staged m1n1 checksum. Default selection/installed object/
authenticated-root were not independently re-queried. No settings changed.
Do not request the same check again or add another M1↔M5 approval loop unless
new evidence changes the state.

## Offline intake before the human restarts

Download only private `native-j716c-boot029`; verify the archive against current
Git **before extraction**. Preserve every earlier package/receipt/result. Stop
on a mismatch. The following performs no live USB action.

```sh
(
set -e
mkdir -p build/native-boot029-download
if [ ! -f build/native-boot029-download/ilinux-j716c-boot029.tar.gz ]; then
  gh release download native-j716c-boot029 --repo nickyrice04/ilinux \
    --pattern ilinux-j716c-boot029.tar.gz --dir build/native-boot029-download
fi
(
  cd build/native-boot029-download
  shasum -a 256 -c ../../native/boot/archive-sha256.txt
  if [ ! -d ilinux-j716c-boot029 ]; then tar -xzf ilinux-j716c-boot029.tar.gz; fi
)
mkdir -p build/native-intake/receipts build/native-intake/results
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot029-download/ilinux-j716c-boot029 \
  --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
  > build/native-intake/receipts/boot029-attempt10.json
python3 -I native/boot/launch.py --package build/native-boot029-download/ilinux-j716c-boot029
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

Archive **16,722,976 bytes**, SHA-256:
`ebed9be8b34c3684aaf01ef06b8fc108e0c548960c1f83a25ed411c5ef42ce16`.
Image **44,468,736 bytes**, SHA-256:
`53f5f2c5a7a2d9d0d2ae92961222090c97f0c266bb4066408acd577660e7cc32`.
SHA256SUMS digest:
`1eeef3e32ef45f6ed1266da2c3888066c49bc3b1a70e61dc6328bee52c0bdccc`.
Git manifests are authoritative; stop on disagreement.

Reviewed controller digests (also record checked-out Git commit):

* `native/boot/launch.py`: `c2d2cd0b067b78ead957463e70f8c4694cdeee5dc5b7b54bd6ebf2b7f7fc0279`
* `native/boot/entry_guard.py`: `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713`
* `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
* `native/boot/fdt.py`: `d9522761837e78f7b444b936a7501fc9f847697d783b57de1f446a4b8da32b6b`
* `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

Prepare fresh ignored `boot029-stage-b-attempt10.json`/`.md` records with the
source/procedure/controller/payload/receipt hashes. Push sanitized readiness
in `progress.md` and `coordination.md`, keeping native/live checks NOT RUN.
Tell the human when ready. M1 readiness plus the human's start suffice; no
extra M5 review round trip for these unchanged verified instructions.

## One human-started, filmed RAM boot

1. Both Macs on power, same direct cable/primary USB interface. Film the M5
   built-in screen **before launching**, 60 fps if available. Include the bottom
   left edge where the enlarged status strip should appear. Stop at readiness if
   recording cannot be arranged. Full media stays local.
2. Human saves work, shuts down, holds power for startup options and selects
   **iLinux Boot Lab → Continue**. Keep Macintosh HD as default. If already at
   `Running proxy...` for this attempt, do not restart again.
3. After the human starts and reports the proxy, invoke this **once**:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot029-download/ilinux-j716c-boot029 \
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
   * `ilinux-display: state=N console_setup=N`, if visible. Console setup
     does not mean it is still registered. Record this without inferring it.
   * Phases 10, 11, 12; `reschedule pending=N strip=N display=N`; phase 13
     if it returns. `strip=1` / `display=6` mean a mapping was available,
     not that every mark was visible. The repeated display state helps if the
     earlier mapping log has scrolled away.
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
   S=01–09 retain the scheduler entry/lock/selection/finish/exit meanings.
   New **hex S=10–17** bracket generic `context_switch`; **S=20–31** bracket
   ARM64 `__switch_to`, including feature-dependent operations and DSB.
   The complete value-to-operation table is in
   `kernel/experiments/context-display/README.md`; copy literal values first.
   S=07 can be normal for a new thread; S=31 is not required on its first start.
   W retains worker phases 0–7; H counts heartbeats 1–6. These are last
   boundaries, **not exact blocking PCs or register-fault diagnoses**.
   Diagnostic rendering adds overhead and another console could overwrite it.

   Display state is decimal: 0 no outcome, 1 target/active framebuffer absent,
   2 rejected DT properties, 3 invalid font, 4 strip too wide, 5 mapping failed,
   6 mapping exists. Report any failure code; do not alter DT or addresses live.

   | Observation | M5 follow-up |
   |---|---|
   | P=0A/0B persists | Investigate watchdog initialization/arming and visibility |
   | Display 1–5 or strip absent | Report exact state/text and reviewed screen evidence; investigate that prerequisite offline |
   | P=0C persists | Use new S subphase and any heartbeat/stack to locate the scheduling boundary |
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
8. Push sanitized attempt-10 report and progress/coordination updates. Separate
   controller, native kernel, strip/timer/scheduler, PID-1/liveness and return
   status. Preserve earlier reports; mark unobserved evidence honestly. Keep
   full media/raw data/proprietary binaries out of Git.

## Path toward Omarchy

Do not restart installation. The immediate gate is stable native diagnostic
userspace. Then M5 prepares Linux-side USB/input/control and a usable RAM root;
the Linux-side agent can handle packages, configuration and desktop tests once
that channel exists. GPU, SMP and efficient idle/DVFS need independent native
validation. Boot028 alone cannot establish Omarchy or macOS performance parity.

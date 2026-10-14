# Stage B — attempt 11 / boot030 deferred-device and probe-path diagnostics

**Attempt 11 consumed — 2026-10-14.** One boot030 launch passed controller
checks. Reviewed video/detailed photo shows phase 13 and phases 2–5 and final
**P05 S09 W04 H02 D0059 B63 C0059**, decoded to the pin-controller platform
probe callback boundary. Diagnostic userspace/liveness unobserved.
Return instructed at deadline; **Macintosh HD confirmation pending**.
No automatic retry. See `native/boot/stage-b-2026-10-14-attempt11-result.md`.
The procedure below is retained as the reviewed pre-attempt checklist.

**Reviewed pre-attempt M5 handoff, 2026-10-14.** Pull latest main with `git pull --ff-only`;
preserve local work and stop on divergence. Read `coordination.md` and this file.
Attempt 10 is consumed. Its reviewed video observes **P:05 S:09 W:04**; the
previous three strip lanes now work, but H/small fields/userspace are unconfirmed
or unobserved. Source places that at the first flush and entry to device probing;
no exact driver/fault is established. Macintosh HD return is confirmed.
See `native/boot/stage-b-2026-10-14-attempt10-result.md`.
**At this handoff: native attempt 11 / boot030 / live checks NOT RUN.**

**Continue the existing installation.** Installed boot021 m1n1 and the clean
client pin remain unchanged. Do not repeat provisioning, Stage A, Recovery,
macOS installation, `bputil`, `kmutil`, partitioning or m1n1 installation. Keep
Macintosh HD at Full Security and as the default. No volume/security changes.

## What changed and why

Boot030 adds a readable public device index and 56 boundaries across device
locks, runtime PM, DMA/pinctrl, clocks, power domains, driver callbacks and
cleanup. The compact four-row panel moves H next to W and repaints saved values;
heartbeat updates before printk. These changes address evidence lost in
attempt 10; **the native hang remains unresolved**. Exact REA/Ghidra/source/
LLVM/linked-byte evidence is in `kernel/experiments/probe-path/README.md`.

Only **Image** changes from boot029. Full link/ELF roundtrip, actual diagnostic,
identity, panel, platform-probe and parser/mapper sanitizer tests, 90 controller
cases, 13-file intake and exact-image generic VM PID-1/60-second liveness PASS.
VM success does not validate native hardware. DT/config/initramfs/m1n1, fixed
args and all hardware gates remain unchanged. The only existing skip remains
`initcall_blacklist=clk_debug_init`; no new skip or speculative register change.

## Return protection prerequisite — already PASS

Fresh post-attempt-10 human JSON: original **Full**, lab **Permissive**, both
exit 0. M5 independently read root Macintosh HD/build 25G83/FileVault=true/SIP
on and unchanged staged m1n1 checksum. Default selection/installed object/
authenticated-root were not independently re-queried. No settings changed.
Do not request the same check again or add another M1↔M5 approval loop unless
new evidence changes the state.

## Offline intake before the human restarts

Download only private `native-j716c-boot030`; verify the archive against current
Git **before extraction**. Preserve every earlier package/receipt/result. Stop
on a mismatch. The following performs no live USB action.

```sh
(
set -e
mkdir -p build/native-boot030-download
if [ ! -f build/native-boot030-download/ilinux-j716c-boot030.tar.gz ]; then
  gh release download native-j716c-boot030 --repo nickyrice04/ilinux \
    --pattern ilinux-j716c-boot030.tar.gz --dir build/native-boot030-download
fi
(
  cd build/native-boot030-download
  shasum -a 256 -c ../../native/boot/archive-sha256.txt
  if [ ! -d ilinux-j716c-boot030 ]; then tar -xzf ilinux-j716c-boot030.tar.gz; fi
)
mkdir -p build/native-intake/receipts build/native-intake/results
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot030-download/ilinux-j716c-boot030 \
  --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
  > build/native-intake/receipts/boot030-attempt11.json
python3 -I native/boot/launch.py --package build/native-boot030-download/ilinux-j716c-boot030
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

Archive **16,724,043 bytes**, SHA-256:
`260f57106007b654a522480e3c20fb2b3630338a5b90edaa64bd067fa0ec2c16`.
Image **44,599,808 bytes**, SHA-256:
`190cd86d5f823326f5a44277f5efb96cc01c85b3a3f9ffbde16d9cb7abe35067`.
SHA256SUMS digest:
`8772c4585be4b646eec28873d203928d17ea1855d8177d9ca1d729c315afabad`.
Git manifests are authoritative; stop on disagreement.

Reviewed controller digests (also record checked-out Git commit):

* `native/boot/launch.py`: `c2d2cd0b067b78ead957463e70f8c4694cdeee5dc5b7b54bd6ebf2b7f7fc0279`
* `native/boot/entry_guard.py`: `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713`
* `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
* `native/boot/fdt.py`: `d9522761837e78f7b444b936a7501fc9f847697d783b57de1f446a4b8da32b6b`
* `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

Prepare fresh ignored `boot030-stage-b-attempt11.json`/`.md` records with the
source/procedure/controller/payload/receipt hashes. Push sanitized readiness
in `progress.md` and `coordination.md`, keeping native/live checks NOT RUN.
Tell the human when ready. M1 readiness plus the human's start suffice; no
extra M5 review round trip for these unchanged verified instructions.

## One human-started, filmed RAM boot

1. Both Macs on power, same direct cable/primary USB interface. Film the M5
   built-in screen **before launching**, 60 fps if available. Include the bottom
   left corner where the new **four-row panel** should appear. Keep recording
   through the stop criterion, including a close final frame. Stop at readiness
   if recording cannot be arranged. Full media stays local.
2. Human saves work, shuts down, holds power for startup options and selects
   **iLinux Boot Lab → Continue**. Keep Macintosh HD as default. If already at
   `Running proxy...` for this attempt, do not restart again.
3. After the human starts and reports the proxy, invoke this **once**:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot030-download/ilinux-j716c-boot030 \
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
   * **A close photo/paused frame of all four rows**, including literal hex:

     ```text
     P:xx S:xx
     W:xx H:xx
     D:xxxx
     B:xx C:xxxx
     ```

     P/S/W/H retain their meanings. **D** is the root deferred device;
     **C** is the device supplied to the last marked operation; **B** is that
     operation's boundary. D/C are public table indexes, not hardware IDs.
     Copy literal values before interpreting them. Missing/overwritten lanes
     stay NOT OBSERVED; 0000 means unknown only when actually readable.
   * Use `python3 -I kernel/experiments/probe-path/decode.py --device D_HEX
     --current C_HEX --phase B_HEX`, replacing the three placeholders with
     actual readable hex. It is an offline lookup. `device-identities.json`
     and `phases.json` are the authoritative tables; no hardware/REA setup on M1.
   * Watchdog heartbeat, scheduler summary, first stack's symbolic function
     names/offsets, retry-compatible begin/end and later initcalls, if readable.
     No inferred stack frames or unrelated identifiers. H now updates before
     printk, so a visible change can survive blocked text logging.
   * Diagnostic PID 1, `online_cpus=1`, and the 60-second liveness milestone.

   P order remains `01 → 0A → 0B → 0C → 0D → 02 ... 09`. P=05/07 marks the
   first/second work flush. W=04 precedes bus probing; W=05 follows its return.
   B=10 brackets device locking; 31–33 runtime PM/barrier; 42 pinctrl; 43 DMA;
   61 clock defaults; 62 power-domain attachment; 63 platform driver callback.
   The complete **56-code** table is in `phases.json`. Correlate D/C/B with
   P/W/S/H; these are last boundaries, not blocking PCs or proven faults.
   Task gating excludes unrelated asynchronous workers. Lanes are not an atomic
   snapshot, a camera may miss transitions and another console may overwrite
   them. Repainting adds overhead; do not benchmark this diagnostic build.

   Display state is decimal: 0 no outcome, 1 target/framebuffer absent,
   2 rejected DT, 3 invalid font/panel height, 4 panel too wide, 5 mapping failed,
   6 mapping exists. A valid map still needs visible screen confirmation.

   | Observation | Follow-up after returning to macOS |
   |---|---|
   | P=05/07 and W=04 | Record D/C/B to locate the deferred device and operation |
   | Readable B=62 | Inspect domain provider/dependencies for the decoded device |
   | Readable B=63 | Inspect the decoded device's actual platform driver |
   | W=05/07 or P=09 | Capture subsequent driver/initcall progress |
   | H changes / symbolic stack | Record time and actual frames; distinguish logging from worker progress |
   | Panel absent/unreadable | Report mapping text and visibility limit; no guessed values |
   | PID 1 + one CPU + 60-second liveness | Diagnostic RAM userspace success; return, no install |

   Review the recording by pausing it **before publishing the result**. Include
   early progress and the final stopped screen; sample around 30/60/90 seconds
   when those times occur before the stop criterion. State the video duration
   and reviewed times. Earlier short clips did not cover the full window. If the
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
8. Push sanitized attempt-11 report and progress/coordination updates. Separate
   controller, native kernel, strip/timer/scheduler, PID-1/liveness and return
   status. Preserve earlier reports; mark unobserved evidence honestly. Keep
   full media/raw data/proprietary binaries out of Git.

## Path toward Omarchy

Do not restart installation. The immediate gate is stable native diagnostic
userspace. Then M5 prepares Linux-side USB/input/control and a usable RAM root;
the Linux-side agent can handle packages, configuration and desktop tests once
that channel exists. GPU, SMP and efficient idle/DVFS need independent native
validation. Boot030 alone cannot establish Omarchy or macOS performance parity.

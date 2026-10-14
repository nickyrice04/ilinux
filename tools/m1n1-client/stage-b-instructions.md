# Stage B — attempt 14 / boot033 scheduler diagnostics in RAM

**M5 handoff, 2026-10-14.** Pull latest main with `git pull --ff-only`, preserving
local work and stopping on divergence. Read `coordination.md` and this file.
Attempt 13 is consumed: controller/GPIO gates PASS, final photo
**P05/W00/H06/D0000/I000/B00/C0000**, S unclear. No attributed GPIO result or
PID 1 was observed. I000 is not evidence of a pin-0 read.
See `native/boot/stage-b-2026-10-14-attempt13-result.md`.
**Native attempt 14 / boot033 / live checks NOT RUN at this handoff.**

**Continue the existing installation.** Installed boot021 m1n1 and clean client
pin remain unchanged. Do not repeat provisioning, Stage A, Recovery, macOS
installation, `bputil`, `kmutil`, partitioning or m1n1 installation. Keep
Macintosh HD at Full Security and as default. No volume/security changes.

## What changed and why

Our scheduler checkpoints repaint the entire diagnostic panel in sensitive
scheduler/context-switch paths. Boot033 removes those calls and retains phase,
PID and selection counters in RAM. The existing bounded five-second watchdog
samples S before H and before printk. **S is now a sampled last checkpoint, not
an immediately painted boundary.** Zero before the first watchdog or a stable
S afterwards does not prove a stall; the six-sample watchdog remains bounded.
Other marks repaint the saved S value without resampling it. P/W/H/D/I/B/C keep
their meanings. This repairs confirmed instrumentation overhead; whether that
explains native progress is a hypothesis, not a successful hardware fix yet.

Only **Image** changes among payloads. Retain boot032's reserved pins
**5,6,7,112,141**, sparse permitted cache defaults, guarded GPIO/IRQ paths,
live-ADT/effective-DT checks, indexed diagnostics and all 286 D/C node IDs.
No driver bypass or extra initcall skip is added. DT/config/initramfs/m1n1,
fixed arguments, one CPU and DAPF/framebuffer corrections remain unchanged.

Full Image/ELF roundtrip and actual-hook ASan/UBSan regression PASS: 30,000 new
checkpoints cause zero renderer calls while preserving state, compared with
10,000 renderer calls from 10,000 old checkpoints. Linked code has 14 instructions
and zero calls, verified against packaged Image. 102 controller cases,
13-file intake, 13 intake-adversarial and 8 evidence cases PASS. Exact Image/
initramfs reaches PID 1, one CPU and 60s liveness in an isolated diskless,
networkless VM; this does not validate native GPIO/MMIO/interrupts or efficiency.
See `kernel/experiments/scheduler-ram-only/README.md` and `validation.json`.
Own source/linked disassembly answered this question; no new proprietary REA
analysis was needed. Prior GPIO REA evidence and limitations remain intact.

## Return protection prerequisite — confirmed after attempt 13

User reports original **Full**, lab **Permissive**; no fresh exit-code JSON was
supplied this turn. M5 independently read root Macintosh HD/build 25G83/
FileVault=true/SIP enabled and unchanged staged m1n1 SHA. This supersedes the
report's pending return status. Default selection/installed boot object/
authenticated-root were not independently re-queried. No settings changed.
Do not repeat the same check or add an M1↔M5 approval loop without new evidence.

## Offline intake before the human restarts

Download only private `native-j716c-boot033`; verify the archive against current
Git **before extraction**. Preserve every earlier package/receipt/result. Stop
on a mismatch. The following performs no live USB action.

```sh
(
set -e
mkdir -p build/native-boot033-download
if [ ! -f build/native-boot033-download/ilinux-j716c-boot033.tar.gz ]; then
  gh release download native-j716c-boot033 --repo nickyrice04/ilinux \
    --pattern ilinux-j716c-boot033.tar.gz --dir build/native-boot033-download
fi
(
  cd build/native-boot033-download
  shasum -a 256 -c ../../native/boot/archive-sha256.txt
  if [ ! -d ilinux-j716c-boot033 ]; then tar -xzf ilinux-j716c-boot033.tar.gz; fi
)
mkdir -p build/native-intake/receipts build/native-intake/results
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot033-download/ilinux-j716c-boot033 \
  --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
  > build/native-intake/receipts/boot033-attempt14.json
python3 -I native/boot/launch.py --package build/native-boot033-download/ilinux-j716c-boot033
python3 -I native/boot/test_launcher.py
python3 -I native/boot/test_gpio_guard.py
python3 -I native/boot/test_entry_guard.py
python3 -I native/boot/test_dapf_guard.py
python3 -I native/boot/test_framebuffer.py
python3 -I native/boot/test_hardware.py
tools/m1n1-client/run.sh native/boot/test_dapf_guard_adt.py
tools/m1n1-client/run.sh native/boot/test_launcher_adt.py
M1N1_SOURCE="$PWD/third_party/m1n1" tools/m1n1-client/run.sh native/boot/test_protocol.py
)
```

Require **37 + 10 + 6 + 16 + 5 + 19 + 2 + 6 + 1 = 102 cases PASS**, package PASS,
13 receipt files and the clean client pin `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
No kernel/REA setup on M1. The receipt verifies files, not live authorization.

Archive **16,723,317 bytes**, SHA-256:
`6cbf5d1396ddd2b5f79255e65c6c776f8122921b06327271e1102f7b7f0d55cd`.
Image **44,534,272 bytes**, SHA-256:
`250d9ff58e5f5397e1bb54682f2bd8a7a679f44f2863629ef7b89ec45ad1eb15`.
Stage-B DT SHA-256:
`4b3adee52465b809e9c8a1946b7610c63f1ae3c0b24f7334cd485260da84adce`.
SHA256SUMS digest:
`817035e6934111ed742398aec31be3f9b7cc9354e03254bd339fa1ea218f4d9b`.
Git manifests are authoritative; stop on disagreement.

Reviewed controller digests (also record checked-out Git commit):

* `native/boot/launch.py`: `65ece2537fdb9ece0ed54dc234f8ee253bc2f3c44aac8c012014079b6366cfe0`
* `native/boot/gpio_guard.py`: `a3c038d036e2bc97679bd29d78d16e42b3db06d96775918abaeb01a53434a755`
* `native/boot/entry_guard.py`: `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713`
* `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
* `native/boot/fdt.py`: `ee577a08bb48242e84dbc50cd1f40a8d1f47a4d4481ca6dd6503829f53615ad3`
* `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

Prepare fresh ignored `boot033-stage-b-attempt14.json`/`.md` records with the
source/procedure/controller/payload/receipt hashes. Push sanitized readiness
in `progress.md` and `coordination.md`, keeping native/live checks NOT RUN.
Tell the human when ready. M1 readiness plus the human's start suffice; no
extra M5 review round trip for these unchanged verified instructions.

## One human-started, filmed RAM boot

1. Both Macs on power, same direct cable/primary USB interface. Film the M5
   built-in screen **before launching**, 60 fps if available. Include the bottom
   left corner where the **four-row panel** should appear. Keep recording
   through the stop criterion, including a close final frame. Stop at readiness
   if recording cannot be arranged. Full media stays local.
2. Human saves work, shuts down, holds power for startup options and selects
   **iLinux Boot Lab → Continue**. Keep Macintosh HD as default. If already at
   `Running proxy...` for this attempt, do not restart again.
3. After the human starts and reports the proxy, invoke this **once**:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot033-download/ilinux-j716c-boot033 \
     --launch --device auto --confirm BOOT-J716C-RAM-DIAGNOSTIC
   ```

   The existing sanitized wrapper may call the same `main(argv)` once. No
   `m1n1.setup`, shell, separate handshake, reconnect or automatic retry.
4. Record times/elapsed/exit, all preflight and final Hardware DT checks,
   retained GPIO ADT exclusion check, both DAPF checks/readback, framebuffer descriptor/readback and kboot reply.
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
     D:xxxx I:xxx
     B:xx C:xxxx
     ```

     P/W/H retain their meanings; S is the watchdog-sampled last scheduler
     phase. **D** is the root deferred device;
     **C** is the device supplied to the last marked operation; **B** is that
     operation's boundary. D/C are public table indexes, not hardware IDs.
     **I** is a hexadecimal GPIO pin index, 000–1FF; **FFF** means inactive.
     B91 is before that permitted pin's MMIO read. It is not a faulting PC.
     Copy literal values before interpreting them. Missing/overwritten lanes
     stay NOT OBSERVED; 0000 means unknown only when actually readable.
   * Use `python3 -I kernel/experiments/probe-path/decode.py --device D_HEX
     --current C_HEX --phase B_HEX --pin I_HEX`, replacing the four placeholders with
     actual readable hex. Omit --pin if I is unreadable. It is an offline lookup. `device-identities.json`
     and `phases.json` are the authoritative tables; no hardware/REA setup on M1.
   * Watchdog heartbeat, scheduler summary, first stack's symbolic function
     names/offsets, retry-compatible begin/end and later initcalls, if readable.
     No inferred stack frames or unrelated identifiers. H now updates before
     printk, so a visible change can survive blocked text logging.
   * GPIO probe messages: `GPIO cache: pins=N readable=N reserved=N`,
     `t6050 IRQ handoff: pins=N parents=N masked=N`, each probe return/error,
     and any `pending reserved GPIO IRQ`, locked-pin or mask-readback error.
     Main cache expectation is 221/216/5; NUB=61 and AOP=85 are inventory
     expectations, not observations. Record actual numbers. B90 validates DT
     exclusions; B91 reads the permitted pin in I; B92 completes defaults;
     B73 now initializes the explicit sparse cache; B93 checks reserved pending
     sources before parent enable; B80–84 covers the retained IRQ handoff.
     Completion of a helper does not establish full peripheral support.
   * Diagnostic PID 1, `online_cpus=1`, and the 60-second liveness milestone.

   P order remains `01 → 0A → 0B → 0C → 0D → 02 ... 09`. P=05/07 marks the
   first/second work flush. W=04 precedes bus probing; W=05 follows its return.
   B=10 brackets device locking; 31–33 runtime PM/barrier; 42 pinctrl; 43 DMA;
   61 clock defaults; 62 power-domain attachment; 63 platform driver callback.
   The complete **77-code** table is in `phases.json`. Correlate D/C/B with
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
   | B=70–7B / 80–84 / 90–93 | Decode exact GPIO stage; record I/counts/errors and whether D=C=0059 changes |
   | GPIO error followed by PID 1 | Report userspace plus failed GPIO; do not claim peripheral support |
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
6. Set a visible timer/deadline immediately at handoff. Do not wait for media
   transfer or review before stopping the target. Keep filming through the stop
   criterion (up to 120 seconds); earlier 40-second clips missed the later window.
   Stop on controller rejection/kernel panic, the 60-second userspace milestone,
   or **120 seconds from handoff**, whichever applies first. Calculate/report
   the deadline. The controller retains 180-second total/15-second transport
   limits. No retry, extra blacklist, new cores/storage or settings change.
7. Return: hold power to shut down if needed, hold power for startup options,
   choose **Macintosh HD → Continue**. Confirm the usual desktop return.
   Do not assert fresh policies until the next read-only check.
8. Push sanitized attempt-14 report and progress/coordination updates. Separate
   controller, native kernel, strip/timer/scheduler, PID-1/liveness and return
   status. Preserve earlier reports; mark unobserved evidence honestly. Keep
   full media/raw data/proprietary binaries out of Git.

## Path toward Omarchy

Do not restart installation. The immediate gate is stable native diagnostic
userspace. Then M5 prepares Linux-side USB/input/control and a usable RAM root;
the Linux-side agent can handle packages, configuration and desktop tests once
that channel exists. GPU, SMP and efficient idle/DVFS need independent native
validation. Boot033 alone cannot establish Omarchy or macOS performance parity.

# Stage B — attempt 13 / boot032 reserved GPIO pins

**M5 handoff, 2026-10-14.** Pull latest main with `git pull --ff-only`, preserving
local work and stopping on divergence. Read `coordination.md` and this file.
Attempt 12 is consumed: final **P05 S09 W04 H02 D0059 B73 C0059** identifies
main GPIO register-cache initialization; NUB IRQ handoff 61/7/1 and return 0
were observed. No main-controller completion or PID 1 was observed. See
`native/boot/stage-b-2026-10-14-attempt12-result.md`.
**Native attempt 13 / boot032 / live checks NOT RUN at this handoff.**

**Continue the existing installation.** Installed boot021 m1n1 and clean client
pin remain unchanged. Do not repeat provisioning, Stage A, Recovery, macOS
installation, `bputil`, `kmutil`, partitioning or m1n1 installation. Keep
Macintosh HD at Full Security and as default. No volume/security changes.

## What changed and why

The observed macOS ADT excludes main GPIO pins **5,6,7,112,141** during Apple's
initialization. REA plus independent byte/disassembly checks connect the property
to the skipped reads; whole-function Apple pseudocode is not accepted as source.
Boot031's cache initialization still reads these pins. Boot032 uses the standard
Linux `gpio-reserved-ranges` property, strictly validates it and creates explicit
cache defaults only from permitted pins. GPIO/pinmux/IRQ paths also exclude them.
A pending excluded IRQ at initialization produces an explicit controller error
before parent registration. It never overrides a pad lock or touches those pins.
This is a **candidate repair**, not a proven explanation of the native stall.

The launcher now checks live GPIO geometry/exclusions before uploads and checks
the same property in the effective DT. Only **Image and Stage-B DT** change among
payloads; the DT delta is exactly one GPIO exclusion property. All 286 public
D/C node IDs remain unchanged. The panel adds **I:xxx** for the current GPIO pin.
See `kernel/experiments/gpio-reserved/README.md`, `dt-delta.json` and validation.

Full Image/ELF roundtrip, ASan/UBSan helpers/renderer, GPIO binding/DT schema,
102 controller cases, 13-file intake and source-recipe reproduction PASS.
Exact-image generic VM liveness is recorded in `validation.json`; it cannot
validate native GPIO/MMIO/interrupts. Config/initramfs, fixed arguments, one CPU,
DAPF/framebuffer corrections and hardware gates remain. The only existing skip
is `initcall_blacklist=clk_debug_init`; no new skip or alternate install path.

## Return protection prerequisite — already PASS

Post-attempt-12 user JSON: original **Full**, lab **Permissive**, both exit 0.
M5 independently read root Macintosh HD/build 25G83/FileVault=true/SIP enabled
and the unchanged staged m1n1 SHA. This supersedes the report's pending return
status. Default selection/installed boot object/authenticated-root were not
independently re-queried. No settings changed. Do not ask for the same check
again or add an M1↔M5 approval loop unless new evidence changes the state.

## Offline intake before the human restarts

Download only private `native-j716c-boot032`; verify the archive against current
Git **before extraction**. Preserve every earlier package/receipt/result. Stop
on a mismatch. The following performs no live USB action.

```sh
(
set -e
mkdir -p build/native-boot032-download
if [ ! -f build/native-boot032-download/ilinux-j716c-boot032.tar.gz ]; then
  gh release download native-j716c-boot032 --repo nickyrice04/ilinux \
    --pattern ilinux-j716c-boot032.tar.gz --dir build/native-boot032-download
fi
(
  cd build/native-boot032-download
  shasum -a 256 -c ../../native/boot/archive-sha256.txt
  if [ ! -d ilinux-j716c-boot032 ]; then tar -xzf ilinux-j716c-boot032.tar.gz; fi
)
mkdir -p build/native-intake/receipts build/native-intake/results
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot032-download/ilinux-j716c-boot032 \
  --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
  > build/native-intake/receipts/boot032-attempt13.json
python3 -I native/boot/launch.py --package build/native-boot032-download/ilinux-j716c-boot032
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

Archive **16,723,345 bytes**, SHA-256:
`001ef39cd64d8fef7c3779c5169c00726474d6ebc56cea90b9f6f5d9c9bd0500`.
Image **44,534,272 bytes**, SHA-256:
`589c33577d1bc2ddeb2f96e544f87b9ead6bc52e774410567170a7235dd70bcb`.
Stage-B DT SHA-256:
`4b3adee52465b809e9c8a1946b7610c63f1ae3c0b24f7334cd485260da84adce`.
SHA256SUMS digest:
`0f0a1a65d793d4d0a5f0238efbc9f371532a8c7c1927ceff417d1b78418c060e`.
Git manifests are authoritative; stop on disagreement.

Reviewed controller digests (also record checked-out Git commit):

* `native/boot/launch.py`: `65ece2537fdb9ece0ed54dc234f8ee253bc2f3c44aac8c012014079b6366cfe0`
* `native/boot/gpio_guard.py`: `a3c038d036e2bc97679bd29d78d16e42b3db06d96775918abaeb01a53434a755`
* `native/boot/entry_guard.py`: `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713`
* `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
* `native/boot/fdt.py`: `ee577a08bb48242e84dbc50cd1f40a8d1f47a4d4481ca6dd6503829f53615ad3`
* `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

Prepare fresh ignored `boot032-stage-b-attempt13.json`/`.md` records with the
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
     --package build/native-boot032-download/ilinux-j716c-boot032 \
     --launch --device auto --confirm BOOT-J716C-RAM-DIAGNOSTIC
   ```

   The existing sanitized wrapper may call the same `main(argv)` once. No
   `m1n1.setup`, shell, separate handshake, reconnect or automatic retry.
4. Record times/elapsed/exit, all preflight and final Hardware DT checks,
   new GPIO ADT exclusion check, both DAPF checks/readback, framebuffer descriptor/readback and kboot reply.
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

     P/S/W/H retain their meanings. **D** is the root deferred device;
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
6. Stop on controller rejection/kernel panic, the 60-second userspace milestone,
   or **120 seconds from handoff**, whichever applies first. Calculate/report
   the deadline. The controller retains 180-second total/15-second transport
   limits. No retry, extra blacklist, new cores/storage or settings change.
7. Return: hold power to shut down if needed, hold power for startup options,
   choose **Macintosh HD → Continue**. Confirm the usual desktop return.
   Do not assert fresh policies until the next read-only check.
8. Push sanitized attempt-13 report and progress/coordination updates. Separate
   controller, native kernel, strip/timer/scheduler, PID-1/liveness and return
   status. Preserve earlier reports; mark unobserved evidence honestly. Keep
   full media/raw data/proprietary binaries out of Git.

## Path toward Omarchy

Do not restart installation. The immediate gate is stable native diagnostic
userspace. Then M5 prepares Linux-side USB/input/control and a usable RAM root;
the Linux-side agent can handle packages, configuration and desktop tests once
that channel exists. GPU, SMP and efficient idle/DVFS need independent native
validation. Boot032 alone cannot establish Omarchy or macOS performance parity.

# Stage B — attempt 16 / boot035: the Stage-B DT without the SMC-owned domains

**M5 handoff, 2026-10-15.** Pull latest main with `git pull --ff-only`, preserving
local work and stopping on divergence. Read `coordination.md`, this file and
`native/boot/attempt15-review-2026-10-15.md`.
Attempt 15 is consumed: boot034 **outlived attempt 14's 8.8 s reset** (PID 1,
heartbeats 000–004, a 17-step ladder), then reset silently at kernel ≈ 27.7 s,
≈ 5.7 s after the sixth `smc_i2cm` release. The M1 host panicked at the handoff.
See `native/boot/stage-b-2026-10-15-attempt15-result.md`.
**Native attempt 16 / boot035 / live checks NOT RUN at this handoff.**

**Continue the existing installation.** Installed boot021 m1n1 and clean client
pin remain unchanged. Do not repeat provisioning, Stage A, Recovery, macOS
installation, `bputil`, `kmutil`, partitioning or m1n1 installation. Keep
Macintosh HD at Full Security and as default. No volume/security changes.

## What changed and why

The seven `smc_i2cm0`–`6` power domains are the SMC coprocessor's own I2C
masters. No Asahi PMGR device tree (M1 through M3) exposes any `smc_*` domain.
Our generated t6050 draft did, and Linux treated them as unclaimed. Attempt 14's
reset (5.6 s after the bulk power-off) and attempt 15's (5.7 s after the last
SMC release) fit one mechanism: **Linux cutting an SMC I2C master makes the SMC
reset the SoC ≈ 5.6 s later** (Likely, not proven).

Boot035 changes **one** thing: those seven nodes are **removed** from the
Stage-B DT. Image (the boot034 kernel with the sync_state fix and the release
ladder), initramfs, m1n1, config, fixed arguments, one CPU, GPIO exclusions,
all hardware gates and the reviewed controller are **byte-identical** to
boot034. The ladder now walks the remaining **145** unclaimed, not-always-on
domains that are on at boot, from ≈ 19 s kernel time, one per ≈ 0.51 s, ending
≈ 94 s.

Offline: VM job 038 removed exactly the seven nodes (`fdtput -r`; decompiled
diff shows nothing else), schema validation is clean before and after, and the
package builder refuses any DT delta other than these seven nodes. No native
effect is established. See the review for evidence and limits.

## Return protection prerequisite — confirmed after attempt 13

User reports original **Full**, lab **Permissive**; no fresh exit-code JSON was
supplied this turn. M5 independently read root Macintosh HD/build 25G83/
FileVault=true/SIP enabled and unchanged staged m1n1 SHA. This supersedes the
report's pending return status. Default selection/installed boot object/
authenticated-root were not independently re-queried. No settings changed.
Do not repeat the same check or add an M1↔M5 approval loop without new evidence.

## Offline intake before the human restarts

Download only private `native-j716c-boot035`; verify the archive against current
Git **before extraction**. Preserve every earlier package/receipt/result. Stop
on a mismatch. The following performs no live USB action.

```sh
(
set -e
mkdir -p build/native-boot035-download
if [ ! -f build/native-boot035-download/ilinux-j716c-boot035.tar.gz ]; then
  gh release download native-j716c-boot035 --repo nickyrice04/ilinux \
    --pattern ilinux-j716c-boot035.tar.gz --dir build/native-boot035-download
fi
(
  cd build/native-boot035-download
  shasum -a 256 -c ../../native/boot/archive-sha256.txt
  if [ ! -d ilinux-j716c-boot035 ]; then tar -xzf ilinux-j716c-boot035.tar.gz; fi
)
mkdir -p build/native-intake/receipts build/native-intake/results
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot035-download/ilinux-j716c-boot035 \
  --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
  > build/native-intake/receipts/boot035-attempt16.json
python3 -I native/boot/launch.py --package build/native-boot035-download/ilinux-j716c-boot035
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

Archive **16,723,179 bytes**, SHA-256:
`81cbbd1ca09ec53bbfe8f616e578c07d7f878a26a7629c2d1de40d969be966e7`.
Image **44,599,808 bytes**, SHA-256 (unchanged from boot034):
`1131a1af5e4d5cfa3206c5eb0afe1a6d72d86a2761a8d906b592e33556882579`.
Stage-B DT SHA-256 (boot034 was `4b3adee5…adce`):
`b1105bbf2c207c8c816c4b9cc0231ecc1d49543e05fe4b772bcb153019e186db`.
SHA256SUMS digest:
`7635c5e4a25b051fa933ad969e2407c3f6a63cea876570f58052a474cf162f8d`.
Git manifests are authoritative; stop on disagreement.

Reviewed controller digests (also record checked-out Git commit):

* `native/boot/launch.py`: `65ece2537fdb9ece0ed54dc234f8ee253bc2f3c44aac8c012014079b6366cfe0`
* `native/boot/gpio_guard.py`: `a3c038d036e2bc97679bd29d78d16e42b3db06d96775918abaeb01a53434a755`
* `native/boot/entry_guard.py`: `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713`
* `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
* `native/boot/fdt.py`: `ee577a08bb48242e84dbc50cd1f40a8d1f47a4d4481ca6dd6503829f53615ad3`
* `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

Prepare fresh ignored `boot035-stage-b-attempt16.json`/`.md` records with the
source/procedure/controller/payload/receipt hashes. Push sanitized readiness
in `progress.md` and `coordination.md`, keeping native/live checks NOT RUN.
Tell the human when ready. M1 readiness plus the human's start suffice; no
extra M5 review round trip for these unchanged verified instructions.

## One human-started, filmed RAM boot

1. Both Macs on power, same direct cable/primary USB interface. **Restart the
   M1 fresh shortly before the run** (attempt 15's host panicked in Apple's USB
   CDC driver about six minutes after a sleep/wake), keep it awake with
   `caffeinate -i`, close any other serial tool, and do not let it sleep.
   Film the M5 built-in screen **before launching**, 60 fps if available,
   with the phone **fixed in landscape** (stand or tripod) and **never moved**:
   attempt 15 lost the domain-name digits when the phone was rotated. Frame
   the **bottom-left quarter** of the screen, where the newest console lines and
   the four-row panel are. Keep recording through the stop criterion, including
   a close final frame. Stop at readiness if recording cannot be arranged. Full
   media stays local.
2. Human saves work, shuts down, holds power for startup options and selects
   **iLinux Boot Lab → Continue**. Keep Macintosh HD as default. If already at
   `Running proxy...` for this attempt, do not restart again.
3. After the human starts and reports the proxy, invoke this **once**:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot035-download/ilinux-j716c-boot035 \
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
   * **genpd lines (boot035, same kernel as boot034).** Copy literally, with
     their `printk.time` stamps:
     * `PM: ilinux-genpd: sync_state keeps unused power domains on (pd_ignore_unused)`
       (attempt 15 showed it twice, at ≈ 3.24 s);
     * `PM: ilinux-genpd: ladder armed: first release in 17000 ms, then one
       domain per 500 ms`;
     * every `PM: ilinux-genpd: power off NAME` line, including any **before**
       ≈ 20 s, which would be a runtime-PM power-off the fix does not cover;
     * `ilinux-genpd: ladder N: release NAME` and `ladder complete: N domains
       released`;
     * **no `smc_i2cm` name may appear anywhere** (they are gone from the DT);
       report it at once if one does;
     * **the last genpd line visible before the screen goes black**, with the
       **time of the black frame** (video time − the heartbeat anchor). Attempts
       14 and 15 reset ≈ 5.6 s after the culprit release, so report both the last
       line and the release that preceded the black frame by ≈ 5.6 s;
     * whether the screen **froze or went black without a restart** (the Mac does
       not reach the macOS login within about 60 s): that is a display-domain
       release, not a reset. Note the last line and time, keep filming to the
       stop criterion, then power off.

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
   | Survives the whole ladder (`ladder complete: N domains released`) with heartbeats to 180 s | The SMC domains were the trigger (strong support). **First stable, power-managed native baseline.** Report N. |
   | Reset ≈ 5.6 s after a ladder release | A second domain with the same mechanism. Report that line and ±2 steps. |
   | Reset with no ladder release in the preceding ≈ 6 s, or before ≈ 19 s | Not a domain release. Report the last lines and the time. |
   | Screen frozen or black, no restart to Macintosh HD | Display-domain release; not a reset. Keep the timer running. |
   | Any `smc_i2cm` line | The wrong DT was loaded. Stop and report. |

   Review the recording by pausing it **before publishing the result**. Include
   early progress and the final stopped screen; sample around 30/60/90 seconds
   when those times occur before the stop criterion. State the video duration
   and reviewed times. Earlier short clips did not cover the full window. If the
   agent cannot access it, have the human pause/transcribe the relevant frames.
   If it remains unavailable, explicitly report that limitation. Avoid spending
   another restart with only an unreviewed recording and ambiguous last line.
6. Set a visible timer/deadline immediately at handoff. Do not wait for media
   transfer or review before stopping the target. **Keep filming until the
   target resets or 180 seconds from handoff**, even after `ladder complete`:
   the ladder runs from ≈ 19 s to ≈ 94 s of kernel time, and the minutes after
   it are the stability evidence. Also stop on controller rejection or
   kernel panic. Calculate/report the deadline. The controller retains
   180-second total/15-second transport limits. No retry, extra blacklist, new
   cores/storage or settings change.
7. Return: hold power to shut down if needed, hold power for startup options,
   choose **Macintosh HD → Continue**. Confirm the usual desktop return.
   Do not assert fresh policies until the next read-only check.
8. Push sanitized attempt-16 report and progress/coordination updates. Separate
   controller, native kernel, strip/timer/scheduler, PID-1/liveness and return
   status. Preserve earlier reports; mark unobserved evidence honestly. Keep
   full media/raw data/proprietary binaries out of Git.

## Path toward Omarchy

Do not restart installation. Attempt 16 is meant to give the first stable,
power-managed native baseline. Next M5 prepares a control channel into Linux
(USB networking over the same cable), a RAM root with a real Arch userspace,
then Hyprland on `simpledrm` with software rendering: a visual Omarchy boot on
one CPU. The Linux-side agent can handle packages, configuration and desktop
tests once the channel exists. GPU, SMP and efficient idle/DVFS need
independent native validation. See `roadmap.md`. Boot035 alone cannot
establish Omarchy or macOS performance parity.

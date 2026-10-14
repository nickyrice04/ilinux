# Stage B — attempt 4 consumed; controller PASS, Linux not observed

**Current result:** attempt 4 ran once at `d4209d3`: both DAPF checkpoints,
all preflight gates and kboot request/reply passed, exit 0 in 10.458 s. Human
reports logo/unreadably fast text; kernel/PID 1/one-CPU/60-second liveness
NOT OBSERVED. Screen limit ended; user confirms Macintosh HD return.
See [attempt 4 result](../../native/boot/stage-b-2026-10-13-attempt4-result.md).
**No retry/new live session authorized.** The commands/readiness below are
consumed history. Next: read-only return checks and offline
work to establish readable early-boot evidence.

Attempt 3 reached handoff with all gates passing, then m1n1 raised an SError.
Read [the preserved result](../../native/boot/stage-b-2026-10-13-attempt3-result.md)
and [the correction/evidence](../../kernel/experiments/dapf-handoff/README.md).
**Native correction NOT TESTED; Linux execution NOT OBSERVED.** Earlier attempts
are consumed. This task prepares a reviewed correction; do not launch or retry
until the human starts the next documented attempt after this verification.

## M1 readiness — PASS, awaiting explicit human start

M1 pulled `2773a73`: existing boot022 package verification and all 13 retained
receipt-file hashes PASS; archive/manifest/source hashes and clean client pin
match. **31 launcher + 16 RAM-guard + 2 pinned DAPF-parser + 4 root-ADT cases
PASS**. New ignored attempt-4 evidence is prepared, including both DAPF
checkpoints. No USB opened; no correction applied to the target. Attempt 4
NOT RUN. The human explicitly starts the attempt after this readiness report;
no duplicate policy check or M5-agent round trip is required.

## What changes

The existing **boot022 payload and installed boot021 m1n1 remain unchanged**.
No download, m1n1 reinstall, Recovery, volume/security/default/boot-object change.
Original Macintosh HD stays Full Security. The new controller checks the live
DAPF work-list and ADT layout, then changes exactly 96 bytes of m1n1 RAM data
immediately before handoff to omit an absent AOP DAPF. It verifies readback.
It does not change code, GAPF registers, firmware filter policy or other entries.
Single-core/NVMe/cpufreq/framebuffer/version/board gates and time bounds remain.

Post-attempt-3 policy prerequisite **PASS**: user-supplied read-only JSON reports
original Full/lab Permissive, both exit 0; M5 reviewed it, not independently rerun.
Independent original root/build 25G83, System/Data FileVault, SIP/authenticated-root
and staged m1n1 hash checks PASS. Default/installed object not independently read.
Do not repeat this policy check before the proposed attempt unless state changes.

## M1 preparation — offline only, while M5 stays in macOS

Preserve local changes and `git pull --ff-only`. Stop on divergence; no reset or
force. Reuse the existing verified directory and clean m1n1 pin
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Marker **boot021** is still correct.

```sh
(
set -e
python3 -I native/boot/launch.py --package build/native-boot022-download/ilinux-j716c-boot022
python3 -I native/boot/test_launcher.py
python3 -I native/boot/test_dapf_guard.py
tools/m1n1-client/run.sh native/boot/test_dapf_guard_adt.py
tools/m1n1-client/run.sh native/boot/test_launcher_adt.py
)
```

Require package PASS and **31 launcher + 16 RAM-guard + 2 real-parser + 4 root-ADT
cases PASS**. Previously tested USB selector/framebuffer/intake code is unchanged.
No C compiler or decompiler setup on M1 is needed. Existing boot022 intake
receipt remains valid if payload bytes are unchanged. Preserve all prior results;
create a new ignored attempt-4 record with actual Git/source/payload digests.

Reviewed source hashes:

* `native/boot/launch.py`: `a9d14ec1019de2c728c81779472b84a90265620969f0d8d23f1b411e924ece89`
* `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
* `native/boot/fdt.py`: `98ff4d58a0ca5b5abb68689b901aef526726704fa70925e96db6f1bbf836a591`
* `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

Report readiness to the human. **Stop offline** until they choose to begin one
new attempt with the described RAM correction. Their explicit start can proceed
directly under this checklist; no additional M5-agent review round trip is needed
for unchanged verified code. Do not interpret a test/receipt as authorization.

## Attempt 4 — after the human starts it and reports m1n1 running

1. Both Macs on power, direct USB data cable, M5 display visible. If the human
   already booted the lab to `Running proxy...` for this attempt, do not reboot
   again. Otherwise save M5 work; human shuts down, holds power continuously to startup options and selects
   **iLinux Boot Lab → Continue** once. Keep Macintosh HD as default; no
   Recovery, bputil, kmutil or security commands.
2. M1 executes the following **once**, only after matching m1n1 is running:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot022-download/ilinux-j716c-boot022 \
     --launch --device auto --confirm BOOT-J716C-RAM-DIAGNOSTIC
   ```

   The launcher selects exactly one descriptor-verified primary, sends its
   own P_NOP, checks the chip/build marker/secondary flags/board/framebuffer,
   validates the DAPF layout, uploads to RAM and checks m1n1's effective DT.
   It then applies and reads back the bounded DAPF table correction before handoff. It never
   requests secondary startup or cpufreq initialization. Internal NVMe is
   disabled in the Linux DT; initramfs mounts only proc/sys/devtmpfs. Hardware
   setup and RAM/register writes occur; this is not a read-only P_NOP session.
3. Record start/end times, command exit and the last printed checkpoint:
   package, primary, target marker/secondary flags, **Initializing controller
   RAM utilities**, **Reading target ADT root compatibility**, board/framebuffer,
   RAM upload, DT preparation, then **DAPF RAM table corrected** and
   preflight/handoff. Also capture **DAPF layout PASS** before upload. Preserve these exact
   non-sensitive checkpoint messages and any reviewed fixed STOP explanation;
   do not reduce all diagnostic output to just an exception type. For unexpected
   errors record only safe module/function/line metadata without locals or
   raw exception arguments; no target memory/identifiers. Never record raw registry,
   ADT, callout identifiers or target memory. Stop on any rejection or timeout;
   do not bypass checks, try another port or retry automatically.
4. The controller is bounded to 180 seconds once the transport phase starts;
   descriptor discovery has its own 15-second bound. Linux handoff ends the
   USB proxy. A disconnect/controller error after handoff alone is neither
   Linux success nor Linux failure: the M5 screen supplies that evidence.
5. Human records first/last readable kernel lines and any non-sensitive error.
   Look for **`PID 1 reached`**, **`online_cpus=1`** and the **60-second
   liveness message**. Stop after that message, explicit panic/failure, or
   **120 seconds after the handoff message**, whichever comes first.
   A blank screen is NOT OBSERVED, not an inferred driver diagnosis. Establish
   an observation path before proposing another blind attempt.
6. After pass or failure, human holds power until off, releases it, then
   holds continuously to startup options; **Macintosh HD → Continue**.
   Verify return; M5 agent/user performs the read-only protection checks.
   If return fails, stop and report; no automatic revive/restore or policy work.
7. Publish only sanitized results in `progress.md` and `coordination.md` and
   push them. Distinguish requested handoff, observed kernel execution, PID 1,
   timed liveness and return. A pass requires all screen milestones and return;
   a controller PASS alone is insufficient. Do not claim hardware/performance parity.

## Decision after attempt 4

* **Preflight rejection:** fix the specific validated mismatch offline. A
  marker mismatch requires investigating provenance, not removing the check.
* **No visible Linux output:** instrument the earliest missing observation
  before another attempt; do not assume AIC, SMP or display is the cause.
* **Kernel panic/early stop:** use the actual last line/checkpoint to choose
  the next kernel/DT change and isolated test.
* **PID 1 plus 60-second liveness:** establish a repeatable native diagnostic
  baseline, then design separate SMP/idle-power and Linux USB/access tests.
  The configuration agent starts only once Linux has tested input/network
  access and a separately approved persistent root environment. This initramfs
  has no shell, SSH, networking, package manager or resident agent.

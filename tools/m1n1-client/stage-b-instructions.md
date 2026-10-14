# Stage B — boot022, one reviewed attempt 3

Attempt 2 at `993a6af` stopped after upload, before Linux handoff, because
boot021 had no `/chosen/framebuffer` placeholder. Pinned m1n1 updates this
node but does not create it. **Linux remains NOT RUN.** Preserve both previous
attempt records. [Job 022](../../virtualization/jobs/022-framebuffer-handoff/RESULTS.md)
reproduces the defect with actual pinned C code and tests the minimal correction.

## Scope and readiness

The user's next-boot direction is carried into one reviewed corrected RAM
attempt, after the checks below and a human-selected lab boot. It does not
permit repeated attempts or changed boot settings. Original Macintosh HD stays
at Full Security. No volume, security, default-startup or boot-object changes;
no m1n1 reinstall, SMP start, storage enablement or installation.

**M5 offline work: complete. M1 boot022 intake: PASS. Post-attempt-2 policy
check: PASS (user-supplied JSON, original Full/lab Permissive, both exit 0).
Attempt 3: NOT RUN.** Do intake while M5 is still in macOS so download/testing
does not waste a restart. Once intake passes, M1 can confirm ready directly
to the human. No extra M5/M1 agent approval round
trip is needed. The human then saves work and boots the existing lab entry once.

M5 independently verified original root/build 26.6.2/25G83, System/Data FileVault,
SIP/authenticated-root, AC power and the unchanged staged m1n1 hash. Default
startup and installed boot object were not independently queried. The fresh
post-return policy JSON was supplied by the user and reviewed by M5; the
privileged query was not independently rerun. Do not request it again before
this attempt unless the relevant state changes.

M1 intake completed after pulling `3c7eae1`: archive checked before extraction,
offline package/13-file receipt PASS, 31 launcher + 5 framebuffer + 4 pinned-ADT
cases PASS. Receipt retained separately; source hashes and clean client pin
match. Ready for the authorized attempt 3; USB/current live checks NOT RUN.
Do not redownload or overwrite the verified package/receipt below.

## M1 preparation — offline only

Preserve local changes; `git pull --ff-only` in the existing checkout. Stop on
divergence; no reset/force. Use the existing clean pinned client
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`. The **boot021 m1n1 marker remains
correct** in boot022 because the bootloader binary did not change.

Download once into a new directory (if it already exists, verify rather than
overwrite). Do not extract until the checksum succeeds:

```sh
(
set -e
mkdir -p build/native-boot022-download
gh release download native-j716c-boot022 --repo nickyrice04/ilinux \
  --pattern ilinux-j716c-boot022.tar.gz --dir build/native-boot022-download
(cd build/native-boot022-download && shasum -a 256 -c ../../native/boot/archive-sha256.txt)
tar -xzf build/native-boot022-download/ilinux-j716c-boot022.tar.gz -C build/native-boot022-download
python3 -I native/boot/launch.py --package build/native-boot022-download/ilinux-j716c-boot022
python3 -I native/boot/test_launcher.py
python3 -I native/boot/test_framebuffer.py
mkdir -p build/native-intake/receipts
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot022-download/ilinux-j716c-boot022 \
  --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
  > build/native-intake/receipts/boot022.json
)
```

Require package PASS, **31 launcher + 5 framebuffer tests**, and a complete
13-file intake receipt. M5 has also run six actual pinned C-function cases with
ASan/UBSan, one real serializer case and seven intake tests. Prior M1 four ADT
and 20 USB tests remain applicable if client/code/environment are unchanged;
rerun those only if changed. No kernel rebuild or C compiler setup on M1.
The receipt's generic `next` field is historical first-intake wording; this
checklist controls the current sequence. `boot_authorized: false` correctly
means checksum verification itself grants no permission.

Record the Git commit, archive/manifest digest and these source hashes:

* `native/boot/launch.py`: `d3dcebceaaab2716cf7e4dc51dfaac10be8cb01eca308409f7574311b69b821f`
* `native/boot/fdt.py`: `98ff4d58a0ca5b5abb68689b901aef526726704fa70925e96db6f1bbf836a591`
* `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`
* Archive SHA-256: `b59db87bee50f5a2b57f65ea54e9ecd9fc07d410251bb38175001ac056ee6862`
* Intake manifest SHA-256: `862391dd99ee93d07c196e502196cefc869b2549274d6139d781f564b4bc50a0`

Create a new ignored attempt-3 record using `boot-result-template.md`; keep all
previous results. Confirm readiness to the user before they leave macOS. If any
check fails, stop offline and report. Do not open USB to diagnose an intake error.

## Attempt 3 — execute once after the human reports m1n1 running

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
   uploads to RAM and checks m1n1's effective DT before handoff. It never
   requests secondary startup or cpufreq initialization. Internal NVMe is
   disabled in the Linux DT; initramfs mounts only proc/sys/devtmpfs. Hardware
   setup and RAM/register writes occur; this is not a read-only P_NOP session.
3. Record start/end times, command exit and the last printed checkpoint:
   package, primary, target marker/secondary flags, **Initializing controller
   RAM utilities**, **Reading target ADT root compatibility**, board/framebuffer,
   RAM upload, DT preparation, then preflight/handoff. Preserve these exact
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

## Decision after the result

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

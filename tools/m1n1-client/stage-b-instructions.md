# Stage B — attempt 2 stopped; authorization consumed; Linux NOT RUN

**Current result:** attempt 2 ran once at `993a6af`, exited 1 in 10.202 s.
Corrected ADT/board checks and RAM upload passed; prepared-DT framebuffer gate
rejected `no enabled boot framebuffer; observation path absent`. No handoff;
Linux NOT RUN. User confirms Macintosh HD return; fresh checks pending. See
[attempt 2 result](../../native/boot/stage-b-2026-10-13-attempt2-result.md).
**Do not execute the historical command below again.** No retry or new live
session is authorized; next work is read-only return checks and offline review.
The following readiness/authorization procedure is preserved as consumed history.

Target: **this Mac17,6 / J716c / t6050 M5 Max**. The first Stage B attempt
stopped before payload upload/handoff with KeyError; live chip, packaged
m1n1 marker and secondary-state checks passed. M1 fixed the confirmed ADT
root-lookup API defect offline in `1635ff0`. Read the preserved
[first result](../../native/boot/stage-b-2026-10-13-result.md). The likely
cause is fixed; only a physical attempt can validate that explanation.

## Current authorization and readiness — 2026-10-13

The user has now requested review of M1's result, preparation for the next boot,
and a repository handoff they can give M1 after booting the lab. This is one
new, reviewed Stage B attempt using the corrected launcher, **not an automatic
retry under the consumed first-session approval**. No repeat permission question
is needed. Preserve Macintosh HD at Full Security; no volume, security, default
startup or boot-object changes, no installation, and no expansion to SMP/storage.

M5 reviewed `1635ff0`, independently checked the pinned ADT API, reran all 31
launcher tests and verified the real boot021 package. M1 already passed 31
launcher plus four actual pinned-parser regressions with synthetic bytes after
the fix; the unchanged 20 USB and seven intake cases passed at prior readiness.
No execution code or payload was changed in the M5 review. These results satisfy
offline readiness; **no new readiness-message round trip is required**.

Read-only M5 return checks confirm original Macintosh HD, build 25G83, original
System/Data FileVault, SIP/authenticated-root, AC power, no project VM processes,
and staged m1n1 matching boot021. The user's fresh helper JSON reports original
Full/lab Permissive, both exit 0. B reviewed that supplied policy output; the
installed boot object and default selection were not independently queried.

The human may now save work and shut down M5, hold power to startup options,
and select **iLinux Boot Lab → Continue** once. M1 must pull/read this handoff
and confirm the files/payload/pin below before opening USB. If preparation fails
while M5 waits at proxy, stop and return to Macintosh HD; do not improvise.
All attempt-2 runtime results remain **NOT RUN** until actually observed.

## M1 preparation now — offline only

From `~/Documents/ilinux`, preserve local changes; pull with `git pull --ff-only`.
If Git diverges, stop and reconcile without reset/force. Keep boot021 and the
clean client pinned to `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
Use the already downloaded payload; no rebuild/redownload is required.

```sh
tools/m1n1-client/run.sh native/boot/launch.py \
  --package build/native-boot-download/ilinux-j716c-boot021
tools/m1n1-client/run.sh native/boot/test_launcher.py
tools/m1n1-client/run.sh native/boot/test_launcher_adt.py
tools/m1n1-client/run.sh tools/m1n1-client/test_usb_check.py
tools/m1n1-client/run.sh tools/m1n1-client/test_package.py
```

Existing validated suites (rerun only if code/environment differs): package PASS, **31 launcher + 4
pinned-ADT, 20 USB and 7 intake** cases. The pinned-ADT suite uses synthetic
binary ADT bytes, the actual pinned upstream parser and fake transport. No
target-dependent check runs in offline mode. The fix run passed 31+4 and
package verification; the unchanged USB/intake suites last passed at readiness.

Preserve attempt 1's record and hashes. Create a separate ignored attempt-2
record before USB access. Pull this handoff with `git pull --ff-only`; confirm
that the local files match these reviewed hashes and the existing client pin:

* `native/boot/launch.py`: `d3dcebceaaab2716cf7e4dc51dfaac10be8cb01eca308409f7574311b69b821f`
* `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`
* m1n1 pin: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, clean tracked files.

Run the ordinary offline package verification once after pulling. If code and
environment are unchanged, the recorded passing suites need not be repeated.
Record the actual handoff Git revision and both source hashes; don't reuse the
old pre-fix launcher hash from `fff8b95`. Then proceed with this authorized
single attempt when the human reports m1n1 running on the lab entry.

## Attempt 2 — execute once after the human reports m1n1 running

1. Both Macs on power, direct USB data cable, M5 display visible. If the human
   already booted the lab to `Running proxy...` for this attempt, do not reboot
   again. Otherwise save M5 work; human shuts down, holds power continuously to startup options and selects
   **iLinux Boot Lab → Continue** once. Keep Macintosh HD as default; no
   Recovery, bputil, kmutil or security commands.
2. M1 executes the following **once**, only after matching m1n1 is running:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot-download/ilinux-j716c-boot021 \
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

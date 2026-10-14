# Stage B — preflight failed; Linux NOT RUN; no retries

Target: **this Mac17,6 / J716c / t6050 M5 Max**. Stage A passed (M1 report
`974e894`): one P_NOP, 0.158 seconds, exit 0, then user-confirmed Macintosh HD
return. M5 subsequently verified original build 26.6.2/25G83, FileVault,
SIP/authenticated-root and the unchanged staged m1n1 hash. The user's fresh
read-only policy JSON reports **original Full / lab Permissive, both exit 0**.
Default startup selection has not been independently queried this review.

The one authorized attempt was used: preflight stopped with **KeyError**, exit 1,
1.135 seconds, after target chip/packaged-marker/secondary checks passed. No
payload upload or handoff occurred; **Linux NOT RUN**. User confirms Macintosh
HD return. Live packaged-marker verification is now **PASS**. Read the
[result and offline diagnosis](../../native/boot/stage-b-2026-10-13-result.md).
Current instruction is **no retries**. The local root-lookup fix is tested only
offline; boot021/client pin remain unchanged. Fresh return protection checks
are pending M5 review. The remaining session procedure is historical reference,
not a new authorization or instruction to reboot.

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

Expected for future offline verification: package PASS, **31 launcher + 4
pinned-ADT, 20 USB and 7 intake** cases. The pinned-ADT suite uses synthetic
binary ADT bytes, the actual pinned upstream parser and fake transport. No
target-dependent check runs in offline mode. The fix run passed 31+4 and
package verification; the unchanged USB/intake suites last passed at readiness.

Preserve the completed attempt record and its original code/procedure hashes.
Do not overwrite it with new preparation or reuse the consumed authorization.
Any future user-directed session needs its own evidence record and readiness.

## Historical session procedure — no retry authorized

1. Both Macs on power, direct USB data cable, M5 display visible. Save M5 work.
   Human shuts down, holds power continuously to startup options and selects
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
   package, primary, target marker/secondary flags, board/framebuffer, RAM
   upload, DT preparation, then preflight/handoff. Never record raw registry,
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

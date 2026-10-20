# Attempt 28 — CPU observation in the working two-stage Omarchy boot

**Native attempt 28 and live CPU checks: NOT RUN.** Read the published
[validation record](../../native/boot/attempt28/validation.md) and the exact
[stage-one](../../native/boot/attempt28/ramroot-manifest.json),
[root](../../native/boot/attempt28/omarchy-root-manifest.json) and
[CPU asset](../../native/boot/attempt28/assets.json) pins. This replaces the
consumed attempt-27 checklist. Storage is deferred to a separate experiment.

The user authorized preparation and publication. First report M1 offline
readiness; then wait for the human to select the existing iLinux Boot Lab entry
and start this one attempt. No new installer, Recovery, security, default-disk,
volume, firmware or m1n1 change. Macintosh HD remains intact, Full Security and
the default. Routine policy rechecks remain waived; those policies are last
reported, not freshly measured. Preserve all attempt-27 evidence.

## Purpose and limits

Identify the actual boot core and its requested CPU state, collect independent
short work-rate estimates and cache/DRAM results, and see whether the candidate
cpufreq policy initializes. **No frequency/voltage request is authorized in
this attempt.** It does not promise faster menus. The evidence chooses the
first bounded frequency experiment and separates CPU-clock from memory/rendering
limits. Firmware can change a clock independently; a command-register field
is not proof of actual frequency.

Keep boot042 Image, installed boot021/client `57a9339`, one core, USB, keyboard,
RAM root, `idle=nop arm64.nowfxt`, and disabled NVMe. The dedicated `cpu-observe`
profile changes only the reviewed CPU DT properties and selects the already
built-in userspace governor instead of disabling cpufreq. No module autoload:
the bounded collector explicitly loads the module once with immutable
`ilinux_enable_writes=0 ilinux_max_pstate=0`. It never reads the unknown STATUS
register. No additional cores, storage, Wi-Fi, idle, graphics or agent setup.

## M1 offline intake — before the M5 restarts

From the repository root, preserve local work and `git pull --ff-only`; stop on
divergence. Record `git rev-parse HEAD`. Read AGENTS.md and coordination.md.
Privately receive the two new files into ignored `build/attempt28/`:
`stage1.cpio.zst` and `ramroot.cpio.zst`. Old attempt-27 files will be refused.
Never publish either image, a test overlay, raw journal or private key.

```sh
mkdir -p build/native-intake/attempt28 build/attempt28
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot042-download/ilinux-j716c-boot042 \
  --manifest-sha256 60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd \
  > build/native-intake/attempt28/package-receipt.json
python3 -I tools/m1n1-client/verify-two-stage.py \
  --records native/boot/attempt28 \
  --stage1 build/attempt28/stage1.cpio.zst \
  --stage2 build/attempt28/ramroot.cpio.zst \
  > build/native-intake/attempt28/pair-receipt.json
```

Require both exits 0 and PASS. Then read one member of the verified root,
without extracting or executing an image:

```sh
/usr/bin/tar -xOf build/attempt28/ramroot.cpio.zst \
  usr/local/lib/ilinux-cpu28/assets.json \
  > build/native-intake/attempt28/embedded-assets.json
cmp native/boot/attempt28/assets.json build/native-intake/attempt28/embedded-assets.json
python3 -I native/boot/launch.py \
  --package build/native-boot042-download/ilinux-j716c-boot042 \
  --profile cpu-observe --ramroot build/attempt28/stage1.cpio.zst
python3 -I tools/m1n1-client/m5-stage2.py \
  --manifest native/boot/attempt28/omarchy-root-manifest.json \
  --image build/attempt28/ramroot.cpio.zst --dry-run
```

Require package/RAM-root/CPU-observation PASS, OFFLINE ONLY, userspace governor,
300-second launcher deadline, and sender `dry run: no session opened`.
Do not pass `--operator-key`, substitute a DT or use the old ramroot profile.
Read the changed launcher, `cpu_observe.py`, `observe28.py` and M1 collector.
Verify the source digests in `native/boot/attempt28/source-sha256.txt`.

```sh
shasum -a 256 -c native/boot/attempt28/source-sha256.txt
ILINUX_BOOT042=build/native-boot042-download/ilinux-j716c-boot042 \
  python3 -I native/boot/test_cpu_observe.py
python3 -I native/boot/test_ramroot.py
python3 -I kernel/experiments/cpufreq-t6050/test_observe28.py
python3 -I tools/m1n1-client/test_attempt28_collect.py
python3 -I tools/m1n1-client/test_verify_two_stage.py
python3 -I tools/m1n1-client/test_m5_stage2.py
tools/m1n1-client/run.sh -m unittest discover -s native/boot -p 'test_launcher*.py'
```

Report failures and absent legacy fixtures explicitly. Keep the previously
verified USB reader/pipe, SSH config and operator key; recheck their recorded
pins/public key. Verify `ssh -G -F tools/m1n1-client/m5-ssh-config m5s` and `m5o`.
Only one SSH connection may use interface 1 at once. No proxy or clock step is
needed for this experiment; use monotonic measurements and no forwarding.
Publish a sanitized readiness record, with native/live **NOT RUN**, and stop.

## One human-started boot

Both Macs on power, direct cable, established fresh-M1-restart/reseat/unlocked
open-lid procedure, bounded `caffeinate -i` session. Film the M5 from launch
through return; keep serial-number lines and all raw video private. The human
shuts down the M5, holds power, selects **existing iLinux Boot Lab** for this boot
and waits at `Running proxy...`. Do not change the default startup disk.

On the M1, require the existing read-only discovery gate, clear only the two
lab key files from the previous boot, then launch **once**:

```sh
tools/m1n1-client/run.sh tools/m1n1-client/usb-check.py
rm -f build/control/known_hosts-stage1 build/control/known_hosts-omarchy
tools/m1n1-client/run.sh native/boot/launch.py \
  --package build/native-boot042-download/ilinux-j716c-boot042 \
  --profile cpu-observe --ramroot build/attempt28/stage1.cpio.zst \
  --launch --device auto --confirm BOOT-J716C-CPU-OBSERVE-28
```

Any STOP ends the attempt. Record exit/handoff duration, require Hardware DT
PASS. No auto-retry or live gate edits. Start interface-0 reader in its own
terminal, then use the sender sequentially with no other SSH session:

```sh
build/control/bulk-log-reader \
  --out build/native-intake/attempt28/stage1-journal.txt --wait 120 --seconds 600
```

Require stage one's panel and link within 120 seconds; compare its panel key
with its journal, check for controller faults. Accept only the ordinary
accessory prompt if shown. Then, in the control terminal:

```sh
python3 -I tools/m1n1-client/m5-stage2.py \
  --manifest native/boot/attempt28/omarchy-root-manifest.json \
  --image build/attempt28/ramroot.cpio.zst \
  > build/native-intake/attempt28/stage2-send.log 2>&1
```

Record the actual exit; require 0 plus the pinned hash and `switching` record.
Stop on refusal/fault, 60 seconds without progress, or no switch by ten minutes
from sender start. No second send. Do not repeat the VM's deliberate failures.
Sender success proves only the switch request, not Omarchy/link success.

## Fixed observation window and key-gated collection

At the switch, immediately arm the observation clock. Do this before reviewing
logs. Also set a human-visible ten-minute timer; it must not be extended. If
arming fails or the start was missed, retain evidence and end the attempt.

```sh
python3 -I tools/m1n1-client/attempt28-collect.py arm \
  --state build/native-intake/attempt28/window.json
```

The helper refuses rearming and refuses collections that cannot fit in the
remaining window. CPU collection has a 180-second internal alarm, 190-second
systemd runtime bound and 210-second M1 bound; desktop collection has a
40-second remote timeout and 45-second M1 bound. These stop collectors, not the
physical Mac: the human returns the M5 to Macintosh HD by the timer. If anything
fails, end early. Stop the first reader when its gadget goes away, then start
the second with its own file. Never run two readers on the same interface:

```sh
build/control/bulk-log-reader \
  --out build/native-intake/attempt28/stage2-journal.txt --wait 120 --seconds 600
```

Allow at most 180 seconds for the desktop/link. A failed link is a recorded
outcome; do not reset or reprobe drivers. If the root's key is present in the
journal, bootstrap only the SSH handshake (`true`, no measurements), with
forwarding disabled and a 15-second connection timeout:

```sh
ssh -F tools/m1n1-client/m5-ssh-config -o BatchMode=yes \
  -o ClearAllForwardings=yes -o HashKnownHosts=no -o UpdateHostKeys=no \
  -o ConnectTimeout=15 -o ConnectionAttempts=1 m5o true
```

Thereafter the helper verifies the journal's unique `ilinux-m5-boot` fingerprint
against the exact `m5-omarchy` known-host key **before opening observation SSH**.
It deliberately ignores the retained `ilinux-m5-stage1` record. Any mismatch
ends the attempt; do not bypass the check or continue manually.

Run CPU collection first, with the desktop idle, once:

```sh
python3 -I tools/m1n1-client/attempt28-collect.py cpu \
  --state build/native-intake/attempt28/window.json \
  --journal build/native-intake/attempt28/stage2-journal.txt \
  --output build/native-intake/attempt28/cpu.jsonl
```

Require exit 0 and final `done`, `frequency_writes:false`. Both
`OBSERVED_WITH_POLICY` and `OBSERVED_NO_POLICY` are useful diagnostic outcomes.
A refusal/fault/timeout is a stop, not permission to unload/reload or request a
frequency. Preserve the before-module baseline even if initialization fails.
Unknown OPP, missing temperature/power data or a high existing frequency must
be reported literally. Never invent a frequency from the requested value.

If time remains, run `desktop` mode to `desktop-before.txt`, ask the human to
open/close one menu, terminal and file manager and type `omarchy`, then run
`desktop` to **a different** `desktop-after.txt`. Use the same state/journal
arguments as above. Check for leftover menu pollers and record human latency;
video is optional evidence, not a measured frame-time distribution. Do not
change render/CPU/keyboard settings or begin sign-in/setup. A skipped after
snapshot is INCONCLUSIVE. End sooner if the fixed timer is close.

## Return and reporting

Return to Macintosh HD by the ten-minute observation deadline, or earlier on
any fault, freeze, abnormal thermal behavior or stop. If normal return is
unavailable, use the established human power-off/startup-options return;
never change boot settings. Stop this run's reader/caffeinate processes. Do not
ask for another routine policy check.

Publish only a sanitized result: exact Git/pair/asset pins, one launch and one
send, verified hardware/core identity, raw **DVFS command only**, requested OPP,
independent short estimates/throughput/cache/DRAM data, available thermal data
(or null), module/policy outcome, desktop/menu observations, deadlines and
return confirmation. Raw journals, video, identifiers and keys stay private.
Record compiler flags and that no voltage/frequency write, SMP or storage test
ran. CPU parity/efficiency and native DVFS transitions remain unproven.

Next-package decisions: resolve an unknown state mapping from the observed
command and REA evidence; if the OPP is known, establish thermal observation
and an explicit conservative cap before the first bounded transition. If the
clock is already adequate, prioritize the measured memory/rendering cause.
SMP entry and N1/storage preparation continue as distinct work, not live
additions to this attempt.

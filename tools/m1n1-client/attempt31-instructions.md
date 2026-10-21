# Attempt31 — verified final-copy experiment

Native/live **NOT RUN**. Attempt30 is consumed. Read
`kernel/experiments/desktop31/PLAN.md` and `native/boot/attempt31/validation.md`.
This is one new boot and root send after M1 offline readiness and human start.
No routine security check, installation, volume, boot-policy/default, firmware,
installed m1n1, DVFS, SMP, storage or Wi-Fi operation is requested.

## What changes

A new **matched image pair** carries an original, opt-in Hyprland final-copy
optimization. The exact attempt28 root is the base. Only the compositor and
experiment assets change; the existing login, Omarchy configuration, keyboard,
USB transport, boot042 kernel and reviewed CPU-observation DT remain. Stage
one changes only its pairing pin. **Do not mix attempt28 and attempt31 images.**

The executable starts with `debug:ilinux_copy31=0`, using its original draw
path. The collector runs an off/on/on/off crossover, requires pixel-equivalence
and actual-path evidence, offers a 45-second human test with the candidate on,
then resets to the original draw path. A separate `ExecStopPost` reset runs
even after collector termination. The experimental executable remains only in
the RAM root until shutdown; no persistent native installation is made.

The copy only applies to the unrotated 3456x2160 llvmpipe final pass with matching
8-bit format semantics, no zoom, color conversion or final effect. The first
eligible frame for each buffer pair is checked byte-for-byte against the old
draw. A mismatch or GL error disables the candidate for the session. The
on-screen result is still a native test gate. This is not CPU/GPU/energy parity.

## Offline intake — do this before asking for a restart

Preserve local work; `git pull --ff-only`; record HEAD. Privately receive the
two new images into ignored `build/attempt31/` as `stage1.cpio.zst` and
`ramroot.cpio.zst`. Their exact sizes/digests are in the two manifests under
`native/boot/attempt31/`. Keep the prior pair for reference; never replay its
consumed collectors. Nothing is downloaded from a public Release.

```sh
mkdir -p build/native-intake/attempt31
shasum -a 256 -c native/boot/attempt31/source-sha256.txt
python3 -I tools/m1n1-client/verify-two-stage.py \
  --records native/boot/attempt31 \
  --stage1 build/attempt31/stage1.cpio.zst \
  --stage2 build/attempt31/ramroot.cpio.zst \
  > build/native-intake/attempt31/pair-receipt.json
python3 -I tools/m1n1-client/verify-desktop31-image.py \
  build/attempt31/ramroot.cpio.zst \
  > build/native-intake/attempt31/assets-receipt.json
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot042-download/ilinux-j716c-boot042 \
  --manifest-sha256 60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd
python3 -I native/boot/launch.py \
  --package build/native-boot042-download/ilinux-j716c-boot042 \
  --profile desktop-copy --ramroot build/attempt31/stage1.cpio.zst
python3 -I tools/m1n1-client/m5-stage2.py \
  --manifest native/boot/attempt31/omarchy-root-manifest.json \
  --image build/attempt31/ramroot.cpio.zst --dry-run
ILINUX_BOOT042=build/native-boot042-download/ilinux-j716c-boot042 \
  python3 -I native/boot/test_cpu_observe.py
python3 -I native/boot/test_ramroot.py
python3 -I kernel/experiments/desktop31/test_desktop31.py
python3 -I tools/m1n1-client/test_attempt31_collect.py
```

Also verify embedded `/usr/local/lib/ilinux-desktop31/assets.json` equals the
published `assets.json`, all six asset hashes match, `/usr/bin/Hyprland` matches
`Hyprland-copy31`, and collector/baseline/reset sources equal Git. Inspect with
an archive reader only; do not execute ARM Linux artifacts on macOS. The old
CPU28 assets remain byte-identical. Verify the existing client `57a9339`, reader,
SSH configuration/operator public key and no-forwarding pins using the prior
successful intake procedure. Record legacy-fixture skips explicitly.

Require offline-only output, the new `Desktop copy PASS` line, unchanged
single-core boot arguments and a 300-second launch deadline. Publish sanitized
readiness to the repository with native/live NOT RUN and launch/send counts 0.
Wait for the human's start. Readiness is not permission to begin early.

## One boot, one root send

Use the established direct-cable, power, unlocked/open-lid, bounded caffeinate,
reader and filming procedure. Report restart history accurately; do not infer
a fresh M1 restart from a human report when measured uptime disagrees.
The human selects the existing **iLinux Boot Lab** entry for this boot and
waits at `Running proxy...`. Macintosh HD remains the default, at Full Security.

```sh
tools/m1n1-client/run.sh tools/m1n1-client/usb-check.py
rm -f build/control/known_hosts-stage1 build/control/known_hosts-omarchy
tools/m1n1-client/run.sh native/boot/launch.py \
  --package build/native-boot042-download/ilinux-j716c-boot042 \
  --profile desktop-copy --ramroot build/attempt31/stage1.cpio.zst \
  --launch --device auto --confirm BOOT-J716C-DESKTOP-COPY-31
```

Require all live hardware/version gates and controller exit 0. STOP means no
retry or gate edits. Start the first reader separately:

```sh
build/control/bulk-log-reader \
  --out build/native-intake/attempt31/stage1-journal.txt --wait 120 --seconds 600
```

Within 120 seconds require stage one's panel/link and matching panel/journal key.
Send the new root once, without a competing SSH session:

```sh
python3 -I tools/m1n1-client/m5-stage2.py \
  --manifest native/boot/attempt31/omarchy-root-manifest.json \
  --image build/attempt31/ramroot.cpio.zst \
  > build/native-intake/attempt31/stage2-send.log 2>&1
```

Stop on refusal/fault, 60 seconds without progress, or no switch by ten minutes
from send start. Require exit 0, matching hash and switch record. Immediately
at the switch, arm once and set the human-visible **600-second return timer**:

```sh
python3 -I tools/m1n1-client/attempt31-collect.py arm \
  --state build/native-intake/attempt31/window.json
```

Stop the first reader when the gadget disappears, then start the second. Never
overlap readers. Require the desktop/link within 180 seconds or return:

```sh
build/control/bulk-log-reader \
  --out build/native-intake/attempt31/stage2-journal.txt --wait 120 --seconds 600
ssh -F tools/m1n1-client/m5-ssh-config -o BatchMode=yes \
  -o ClearAllForwardings=yes -o HashKnownHosts=no -o UpdateHostKeys=no \
  -o ConnectTimeout=15 -o ConnectionAttempts=1 m5o true
```

Only `true` bootstraps the key; the helper verifies this run's root journal key
against the exact known-host entry before every subsequent SSH operation.

## Bounded crossover and return

Tell the human: keep hands off during the four fullscreen gradient controls.
The first candidate frames include pixel checks and are excluded as warm-ups.
At the explicit `human_window` cue, open the menu, type `omarchy` without
pressing Enter, and open the file manager within 45 seconds. Record the actual
action times and whether each completed; record colors, orientation, stale
pixels, tearing, typing accuracy and perceived delay. No setup commands.

At least **380 seconds must remain** for collection. Run once in a background
terminal so its cue can be read while it runs:

```sh
python3 -I tools/m1n1-client/attempt31-collect.py latency \
  --state build/native-intake/attempt31/window.json \
  --journal build/native-intake/attempt31/stage2-journal.txt \
  --output build/native-intake/attempt31/copy.jsonl
```

The remote unit caps the collector at 300 seconds; its independent reset has
a 40-second stop bound. The helper's maximum wait is 380 seconds and never
extends the original 600-second window. Require `reference_path_restored`,
`COPY31_OBSERVED`, the following independent `COPY31_REFERENCE_PATH_RESTORED`
receipt, helper exit 0, pixel-check success and positive copy counts.
No candidate activation, error, changed display/options, failed reset, visible
corruption or deadline loss means record the evidence and return—no retry,
fallback tuning, module loading or extra experiments.

Return to **Macintosh HD before 600 seconds from the root switch**. Stop only
the reader/SSH/caffeinate processes owned by this run. No policy recheck is
required; preserve the last reported Full/Permissive state without claiming a
fresh verification.

Publish a sanitized result with all 80 control callbacks, IPC/CPU observations,
numeric copy-path records, human action timings and limitations, clock estimate
before/after, launch/send counts and return time. Keep raw journals/video,
session IDs, keys, proprietary bytes and images private. Do not label anonymous
samples as Mesa automatically or claim energy savings without energy data.
Report native/live facts separately from VM results and mark unfinished work
NOT RUN. Push the report for the M5 agent; do not schedule another boot.

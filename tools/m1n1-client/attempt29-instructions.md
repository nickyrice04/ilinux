# Attempt 29 — isolate memory costs on the working Omarchy boot

**Native attempt29 NOT RUN.** Attempt28 is consumed. This is one new boot,
one root send, and one memory collection, after offline readiness and human
start. Preserve Macintosh HD, its default/Full Security status and the existing
Boot Lab entry. No installer, security, volume, firmware or installed-m1n1 change.
Routine policy rechecks stay waived; historical policies are not freshly verified.

Read `native/boot/attempt29/validation.md` and
`kernel/experiments/memory29/README.md`. The goal is to distinguish translation,
cache/locality and CPU-state effects before choosing a performance change.
This run does **not** promise a desktop speedup or perform a frequency increase.

## What is reused, and what changes

Keep the **exact attempt28 stage one and root already on the M1**, boot042
Image/config, installed boot021 and client `57a9339`. Same one core, keyboard,
USB SSH, disabled NVMe and `idle=nop arm64.nowfxt`. The new `memory-observe`
profile has the same fixed arguments and DT, but its own confirmation token.
Do not invoke the consumed attempt28 collector or load its CPU module.

Only one new private file is needed: `memory29.tar`, under 2 MiB, pinned in
`native/boot/attempt29/bundle.json`. It contains original Linux code and is
delivered over the already verified SSH link into `/run` tmpfs. It loads one
module that reads standard architectural registers and the memory attributes
of its loader's stack page, without emitting addresses or contents. Benchmarks
apply base/huge-page advice only to their own short-lived mappings; the advice
may be refused or produce no huge pages. No global VM, cache, memory-controller,
voltage/frequency, idle, SMP, rendering or storage changes are included.

## M1 offline intake

Preserve local work, pull main with `git pull --ff-only`, and record HEAD.
Privately receive `memory29.tar` into ignored `build/attempt29/`; retain
`build/attempt28/stage1.cpio.zst` and `build/attempt28/ramroot.cpio.zst`.
Create `build/native-intake/attempt29/`. Never publish raw journals or images.

```sh
mkdir -p build/attempt29 build/native-intake/attempt29
shasum -a 256 -c native/boot/attempt29/source-sha256.txt
python3 -I tools/m1n1-client/verify-two-stage.py \
  --records native/boot/attempt28 \
  --stage1 build/attempt28/stage1.cpio.zst \
  --stage2 build/attempt28/ramroot.cpio.zst \
  > build/native-intake/attempt29/pair-receipt.json
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot042-download/ilinux-j716c-boot042 \
  --manifest-sha256 60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd \
  > build/native-intake/attempt29/package-receipt.json
python3 -I tools/m1n1-client/verify-memory29.py build/attempt29/memory29.tar
python3 -I native/boot/launch.py \
  --package build/native-boot042-download/ilinux-j716c-boot042 \
  --profile memory-observe --ramroot build/attempt28/stage1.cpio.zst
python3 -I tools/m1n1-client/m5-stage2.py \
  --manifest native/boot/attempt28/omarchy-root-manifest.json \
  --image build/attempt28/ramroot.cpio.zst --dry-run
ILINUX_BOOT042=build/native-boot042-download/ilinux-j716c-boot042 \
  python3 -I native/boot/test_cpu_observe.py
python3 -I native/boot/test_ramroot.py
python3 -I kernel/experiments/memory29/test_memory29.py
python3 -I tools/m1n1-client/test_attempt29_collect.py
```

Require all exits 0; record any legacy-fixture skips. Recheck the existing
reader/pipe, SSH config and operator public-key pins from attempt28 readiness.
Use the new source-pin file: the historical attempt28 launcher digest has
intentionally changed to add attempt29. Never modify its old record.
Confirm OFFLINE ONLY, Memory observation PASS, same userspace arguments,
300-second launch deadline, and sender dry-run/no connection. Review the new
receiver, module, benchmark and collector. Publish sanitized offline readiness
with native/live NOT RUN; wait for the human's start.

## One boot and one transfer

Use the established fresh-M1-restart, direct-cable/reseat, power, unlocked/open
lid, bounded `caffeinate -i` and filming procedure. The human shuts down the M5,
holds power, selects the **existing iLinux Boot Lab** for this boot and waits
at `Running proxy...`. Keep serial/identifier lines and video private.

```sh
tools/m1n1-client/run.sh tools/m1n1-client/usb-check.py
rm -f build/control/known_hosts-stage1 build/control/known_hosts-omarchy
tools/m1n1-client/run.sh native/boot/launch.py \
  --package build/native-boot042-download/ilinux-j716c-boot042 \
  --profile memory-observe --ramroot build/attempt28/stage1.cpio.zst \
  --launch --device auto --confirm BOOT-J716C-MEMORY-OBSERVE-29
```

Require live hardware checks and controller exit0. Any STOP ends this attempt,
without gate edits or retry. Start the first reader separately:

```sh
build/control/bulk-log-reader \
  --out build/native-intake/attempt29/stage1-journal.txt --wait 120 --seconds 600
```

Within 120 seconds require stage one's panel/link, matching panel/journal key
and no controller fault. Accept the ordinary accessory prompt if shown. Send
the existing root once, with no competing SSH connection:

```sh
python3 -I tools/m1n1-client/m5-stage2.py \
  --manifest native/boot/attempt28/omarchy-root-manifest.json \
  --image build/attempt28/ramroot.cpio.zst \
  > build/native-intake/attempt29/stage2-send.log 2>&1
```

Stop on refusal/fault, 60 seconds without progress or no switch by ten minutes
from send start. Require sender exit0, matching hash and switch record.

## Switch-time deadline and collection

Immediately when the sender records switching, arm once (before log review)
and set the human-visible ten-minute return timer. Do not extend either:

```sh
python3 -I tools/m1n1-client/attempt29-collect.py arm \
  --state build/native-intake/attempt29/window.json
```

Stop the first reader after gadget disappearance; start the second with a new
file. Never have two readers on one interface. Require desktop/link within
180 seconds; otherwise end and report the outcome.

```sh
build/control/bulk-log-reader \
  --out build/native-intake/attempt29/stage2-journal.txt --wait 120 --seconds 600
ssh -F tools/m1n1-client/m5-ssh-config -o BatchMode=yes \
  -o ClearAllForwardings=yes -o HashKnownHosts=no -o UpdateHostKeys=no \
  -o ConnectTimeout=15 -o ConnectionAttempts=1 m5o true
```

Only the `true` handshake bootstraps SSH. Each subsequent helper invocation
verifies the unique root journal key against the exact known-host entry before
connecting. Mismatch ends the attempt. Keep the desktop idle; do not open menus
or type during memory collection:

```sh
python3 -I tools/m1n1-client/attempt29-collect.py memory \
  --state build/native-intake/attempt29/window.json \
  --journal build/native-intake/attempt29/stage2-journal.txt \
  --bundle build/attempt29/memory29.tar \
  --output build/native-intake/attempt29/memory.jsonl
```

Require exit0 and final `MEMORY_OBSERVED`, frequency_writes=false and
global_vm_writes=false. One load only; no unload, retry, manual extra probe or
CPU module. Any stop is useful evidence and ends the attempt. Missing telemetry,
unknown attributes or zero huge-page backing is a result, never permission to
change a global knob or clock. Bounds: collector160s, systemd170s +5s cleanup,
M1 190s; it refuses to start without enough window remaining.

If time remains, use the same helper's `desktop` mode with new output files
before and after one human menu/terminal/file-manager/`omarchy` sequence.
Keep all state/journal arguments; omit --bundle. Each desktop snapshot requires
45 seconds remaining. Skipped after-snapshot is INCONCLUSIVE. No desktop setting
changes. These timers stop collectors, **not the physical Mac**.

## Return and report

Return to Macintosh HD by the fixed +600-second deadline, sooner on any fault,
freeze or abnormal thermal behavior. Use the established human return method
if normal shutdown is unavailable. Stop only this run's reader/caffeine tasks.
No further routine policy check or boot/default change.

Publish sanitized pins, launch/send/load counts, identity, decoded MMU/cache
attributes (no addresses), pre/post clock estimates, unchanged chase28 results,
the 48-row memory matrix, per-sample faults/context switches, actual huge-page
coverage, desktop observations, faults, timings and confirmed return. Preserve
the distinction between the old and new benchmark layouts and the OS/QoS/core/
compiler limitations. A memory hint is not a measured huge-page allocation.
Efficiency and desktop causality remain unproven. The next decision follows
the README's outcome table; do not add another experiment during this boot.

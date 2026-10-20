# Attempt30 — attribute the native desktop stalls

**Native attempt30 NOT RUN; M1 offline readiness pending.** Attempt29 is
consumed. This is one new boot, one root send and one userspace bundle delivery,
after offline readiness and human start. Preserve Macintosh HD, its default/
Full Security status and the existing Boot Lab entry. Routine policy checks
remain waived. No installer, volume, security, firmware or installed-m1n1 change.

Read `native/boot/attempt30/validation.md`, its REA findings and
`kernel/experiments/desktop30/README.md`. This run measures where time is spent;
it does not promise a native speedup. Memory observations did not establish a
cacheability or controller defect. Accurate typing and slow menus can coexist.

## Retained payloads and new small bundle

Keep the exact attempt28 stage one/root already on M1, boot042, installed
boot021 and client `57a9339`. Same single M core, keyboard, USB SSH and disabled
NVMe. The new `desktop-latency` profile uses the same pinned DT and arguments,
including `idle=nop arm64.nowfxt`, with its own confirmation token. Do not load
the CPU28 or memory29 module or run either consumed collector.

Privately receive only `desktop30.tar`: **163,840 bytes**, SHA-256
`26a36600de24360b744728aef2af1cf0b8176be172fd51b0b58f48a8bbee1f07`.
Four regular members: original Wayland client, software CPU-clock sampler,
collector and asset manifest. Verified delivery into `/run` tmpfs only; no
module or Apple artifact. Collector checks the actual native core, kernel,
exact Hyprland binary, session, display and unchanged policies. No frequency,
renderer-policy, idle, extra-core, storage or Wi-Fi change is included.

## M1 offline intake

Preserve local work, pull main with `git pull --ff-only`, and record HEAD.
Privately receive `desktop30.tar` into ignored `build/attempt30/`; retain
`build/attempt28/stage1.cpio.zst` and `build/attempt28/ramroot.cpio.zst`.
Create `build/native-intake/attempt30/`. Never publish raw journals or images.

```sh
mkdir -p build/attempt30 build/native-intake/attempt30
shasum -a 256 -c native/boot/attempt30/source-sha256.txt
python3 -I tools/m1n1-client/verify-two-stage.py \
  --records native/boot/attempt28 \
  --stage1 build/attempt28/stage1.cpio.zst \
  --stage2 build/attempt28/ramroot.cpio.zst \
  > build/native-intake/attempt30/pair-receipt.json
tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
  build/native-boot042-download/ilinux-j716c-boot042 \
  --manifest-sha256 60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd \
  > build/native-intake/attempt30/package-receipt.json
python3 -I tools/m1n1-client/verify-desktop30.py build/attempt30/desktop30.tar
python3 -I native/boot/launch.py \
  --package build/native-boot042-download/ilinux-j716c-boot042 \
  --profile desktop-latency --ramroot build/attempt28/stage1.cpio.zst
python3 -I tools/m1n1-client/m5-stage2.py \
  --manifest native/boot/attempt28/omarchy-root-manifest.json \
  --image build/attempt28/ramroot.cpio.zst --dry-run
ILINUX_BOOT042=build/native-boot042-download/ilinux-j716c-boot042 \
  python3 -I native/boot/test_cpu_observe.py
python3 -I native/boot/test_ramroot.py
python3 -I kernel/experiments/desktop30/test_desktop30.py
python3 -I tools/m1n1-client/test_attempt30_collect.py
```

Require all exits 0; record any legacy-fixture skips. Recheck the existing
reader/pipe, SSH config and operator public-key pins from attempt28 readiness.
Use the new source-pin file: the historical attempt28 launcher digest has
intentionally changed to add attempt30. Never modify its old record.
Confirm OFFLINE ONLY, Desktop latency PASS, same userspace arguments,
300-second launch deadline, and sender dry-run/no connection. Review the new
receiver, userspace workload, sampler and collector. Publish sanitized offline readiness
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
  --profile desktop-latency --ramroot build/attempt28/stage1.cpio.zst \
  --launch --device auto --confirm BOOT-J716C-DESKTOP-LATENCY-30
```

Require live hardware checks and controller exit 0. Any STOP ends this attempt,
without gate edits or retry. Start the first reader separately:

```sh
build/control/bulk-log-reader \
  --out build/native-intake/attempt30/stage1-journal.txt --wait 120 --seconds 600
```

Within 120 seconds require stage one's panel/link, matching panel/journal key
and no controller fault. Accept the ordinary accessory prompt if shown. Send
the existing root once, with no competing SSH connection:

```sh
python3 -I tools/m1n1-client/m5-stage2.py \
  --manifest native/boot/attempt28/omarchy-root-manifest.json \
  --image build/attempt28/ramroot.cpio.zst \
  > build/native-intake/attempt30/stage2-send.log 2>&1
```

Stop on refusal/fault, 60 seconds without progress or no switch by ten minutes
from send start. Require sender exit 0, matching hash and switch record.

## Switch-time deadline and collection

Immediately when the sender records switching, arm once (before log review)
and set the human-visible 600s return timer. Do not extend either:

```sh
python3 -I tools/m1n1-client/attempt30-collect.py arm \
  --state build/native-intake/attempt30/window.json
```

Stop the first reader after gadget disappearance; start the second with a new
file. Never overlap readers on one interface. Require desktop/link within 180s;
otherwise return and report. Bootstrap the root SSH key once:

```sh
build/control/bulk-log-reader \
  --out build/native-intake/attempt30/stage2-journal.txt --wait 120 --seconds 600
ssh -F tools/m1n1-client/m5-ssh-config -o BatchMode=yes \
  -o ClearAllForwardings=yes -o HashKnownHosts=no -o UpdateHostKeys=no \
  -o ConnectTimeout=15 -o ConnectionAttempts=1 m5o true
```

Only `true` bootstraps SSH. Each subsequent helper invocation verifies the unique
root journal key against the exact known-host entry. Mismatch ends the attempt.

Tell the human before starting: two fullscreen gradient windows will appear
and close automatically. Keep hands off during both controls. **After the
collector emits `human_window`, the human has 45s to open the menu, type
`omarchy` in a terminal without pressing Enter, and open the file manager.**
Do not change settings or enter setup commands.

Run this once as a background local task or in a separate terminal so the
M1 agent can read the output file while it runs:

```sh
python3 -I tools/m1n1-client/attempt30-collect.py latency \
  --state build/native-intake/attempt30/window.json \
  --journal build/native-intake/attempt30/stage2-journal.txt \
  --bundle build/attempt30/desktop30.tar \
  --output build/native-intake/attempt30/latency.jsonl
```

Watch **the local file**, not another SSH session, for `human_window`; tell the
human to start promptly. If the cue is missed, record it; do not rerun. Two
controls each contain 4 warm-up + 8 small-damage + 8 full-damage callbacks. Then the 45s
human window records compositor CPU time, main-thread software samples and
read-only IPC service delay. No injected keys, screen capture or policy writes.
A live JSONL reader must tolerate its final incomplete line until completed.

Require exit 0 and final `LATENCY_OBSERVED`, frequency_writes=false,
renderer_changes=false, modules_loaded=false. `phase_incomplete`/`stop` is a
partial outcome, never success. Preserve partial evidence and return. Sampler
`unavailable` with errno is a supported limited observation: do not enable
kernel/PMU features or retry. Retain lost/unmapped samples. Bounds: collector 170s,
systemd 180s + 10s cleanup, M1 helper 220s + 5s cleanup. The helper requires 220s remaining
before starting. Timers stop collectors, **not the physical Mac**. Never extend
the fixed 600s return window.

Optional: one `desktop` helper snapshot before/after collection, with distinct
output names and the same state/journal arguments (omit --bundle), only if 45s
remain and no fault occurred. Never overlap with collection. No other collectors,
module loads, SSH tuning, extra tests or automatic retries.

## Return and report

Return to Macintosh HD by +600s from root switch, sooner on fault, freeze or
abnormal thermal behavior. Use the established human return method if normal
shutdown is unavailable. Stop only this run's reader/caffeine tasks. No new
policy check or boot/default change.

Publish sanitized source/payload hashes, launch/send counts, identity/geometry,
all callback and IPC samples (including warm-ups), process CPU seconds, sample
counts/lost/unmapped/unavailable errors, clock estimates, completion/partial
status and human actions/timing. Describe menu/typing/file-manager delay and
whether the 45s cue was followed. Include faults, deadline and confirmed return.
No raw journals, identifiers, keys, addresses, Apple artifacts or home paths.

Use the README outcome table. VM results validate functionality only; anonymous
executable samples do not alone identify LLVM raster code, and callbacks are
not photon latency. Efficiency and macOS parity remain unmeasured. No additional
experiment during this boot. Keep all original settings and the existing entry.

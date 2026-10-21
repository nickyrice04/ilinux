# M1 handoff after 31D — offline 31E preparation, no restart yet

**Native launch HOLD. Stay in macOS on both computers.** This handoff contains
offline tests and design work, not a replacement live command. 31D is consumed;
do not replay it or erase any prior receipt. No new image or root needs AirDrop.

The report was reviewed: both startup writes were acknowledged, the UART RAM
zeroes were published, and 171 samples saw no reset record. The precise point
where CPU1 stops remains unknown. Additional guessed power writes or a longer
wait would not resolve that uncertainty.

## M1 offline work

Preserve local work, then `git pull --ff-only`; stop on divergence. Record the
commit. Read `native/boot/attempt31e/review.md` and
`research/testing-strategy-31e.md`. From repository root:

```sh
python3 -I tools/m1n1-client/attempt31e-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

This original standard-library runner checks the new source pins, runs the
offline suites and interprets the exact pinned public reset instructions with
synthetic inputs. It does not import a USB client, allocate target RAM, reserve
a native attempt or execute privileged instructions. Expected final result:
`OFFLINE_CHECKS_PASS_NATIVE_HOLD`, `restart_ready: false`.

The retained package does not include the original full symbol listing. The
image-only emulator mode therefore says `reviewed_layout_only`; it verifies the
full image hash and uses the pinned, reviewed symbol offsets. This is not a
claim that M1 checked the absent symbol file. M5's separate VM validation uses
the complete pinned symbol file as well. Do not invent, reconstruct or weaken
an expected digest to pass intake.

Optional report replay, also entirely offline:

```sh
python3 -I tools/boot-campaign/campaign.py history \
  native/boot/attempt31d-controller-2026-10-21.json
python3 -I tools/boot-campaign/campaign.py plan
python3 -I tools/boot-campaign/campaign.py replay \
  tools/boot-campaign/fixtures/synthetic-partial-entry.json
```

Report the commit, exit codes, method count, source pin count, image-only symbol
mode and any refusal. Keep native31E, CPU1 entry and Linux SMP **NOT RUN**.
Publish only a short original summary, never private receipts, target memory,
Apple artifacts, device identifiers or home-directory paths. If a check fails,
record it; do not edit a guard or run an older native command to compensate.

## What M5 is preparing next

The source/image audit found that the old observer rejects a valid MPIDR-first
partial reset record. The new observer handles both partial orders and reads
the arrival flag before the identities it validates. That defect did not cause
31D's untouched-record timeout.

The emulator reproduces the first C frame using the actual public boot021
instructions. This supports earlier observations, but does not model physical
reset, Apple registers, caches or firmware. A proposed stack in shared Device
memory remains on hold because the CPU's entry MMU state and alternate C paths
are not established. The preferred follow-up is a reviewed earlier recorder
that leaves the normal C stack intact, with runtime publication checked before
any CPU1 start.

The eventual native session should collect all reviewed baseline information
first, then one CPU1 transition, early entry observations and—only on verified
arrival—a bounded series of timer requests and park checks. No Linux handoff
from an unknown secondary state. The campaign's payload-echo and later Linux
phases remain designs until implemented and independently checked.

## Reduce unnecessary helper restarts

An unconditional M1 reboot is not the future default. Attempt30 succeeded
with a recorded reader-start uptime of 20,933 seconds. That supports a helper
health gate rather than a universal reboot requirement: powered/awake helper,
one owned reader, no unresolved panic or USB failure, expected device discovery
before target mutations. A restart remains a recovery option when that gate
fails. After an uncertain target mutation, do not restart/reconnect the helper
to continue that same target session.

The M5 still needs a separately reviewed native entry procedure and a fresh
human start. Routine boot-policy checks remain waived. Original macOS, volumes,
startup security and installed boot021 remain unchanged.

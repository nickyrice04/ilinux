# M1: review the complete 31AR transaction offline

Do not restart yet. This handoff requests source, test and exact package review.
It does not authorize staging, page service, Recovery, Preboot mounting, boot
installation/restoration, Startup Disk changes or a native attempt. M5 owns the
later physical cue after reviewing your result and confirming delivery/staging.

31AP passed real Recovery collection, initial admission and owned read-only
cleanup. The earlier parser blocker is cleared; do not repeat its check or ask
for another routine Full/Permissive desktop probe. Macintosh HD desktop/default
return is human-confirmed. Boot021 restoration remains OUTSTANDING.

## What changed

31AR adds the complete native transaction controller and fresh durable state,
using the qualified policy parser and preserved phase validators. It prepares
owned RO observation, verified RW capability for the fixed lab Apple command,
fresh readback and known cleanup before a boot cue. Its independent restore
reuses this new transaction's exact private key/baseline/profile/target binding,
conditionally prepares only lab CTRR, and restores the exact raw boot021 object.
No Original policy writer, raw device write, partition/volume creation, firmware
replacement, automatic retry, forced unmount, automatic boot or old-state reset
is part of this procedure.

The candidate is unchanged: 153,190,400 bytes,
SHA-256 1ea24f0de4aa7d3e82c70a1b35f815791a48342db1a060100226b84dca7d7d01.
The rollback is unchanged: 3,932,160 bytes,
SHA-256 ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664.
The new helper/profile exact delivery is recorded in
native/boot/attempt31ar-package/delivery.json. Do not substitute an M1 rebuild
for the pinned M5 production helper.

## Offline review

1. Pull the commit containing this handoff. Verify every entry in
   native/boot/attempt31ar-package/source-sha256.txt, retaining all 143 old
   inputs and both old inventory identities. Preserve old source, profiles,
   receipts, media, keys, baselines and consumed markers.
2. Review the new native controller/build/tests and production build receipt.
   Check file/directory persistence before each spent marker and writer,
   cross-visit private exact target binding, fresh phase validation, actual mount
   flags/source checks, owned-only cleanup, and refusal after ambiguous outcomes.
3. Confirm the install and independent restore path both work in the offline
   harness. Distinguish actual fixture execution from modeled assertions. Check
   absence of the candidate cannot prevent restoration. Unknown or changed
   Original policy, target identity, private metadata, readback or cleanup must
   prevent a restart cue.
4. Review/run the focused renderer and package tests as useful. Reuse unchanged
   older evidence; avoid repeating large suite/build inventories or invoking
   live capability/controller modes. An independent native test build must use
   a new workspace output and genuine retained own reference bytes in synthetic
   framing; never mock selected identity or use Apple manifest bytes.
   The native test_pty.py exercises only own synthetic child commands and PTY
   interruption, not Apple commands; reuse M5's recorded evidence if unchanged.
   The package's actual four-file copy test explicitly skips if the production
   kit is absent. Report that missing coverage separately; do not count it as
   a pass or manufacture replacement artifacts to avoid the skip.
5. Review both complete paste blocks. Recovery cannot keep the browser and
   Terminal open simultaneously: each box must be copied as a whole, browser
   quit, then pasted once. No preliminary clipboard demonstration is needed.

The new kit destination is Users/Shared/iLinuxBoot/31ar-kit on lab Data.
The fresh private transaction lives at private/var/db/ilinux31ar-state on lab
Data, under its existing root-owned parent. No existing mode/ownership is
changed. Never adopt, remove, reset or migrate old transaction state.

## Exact kit and page preparation

The M5-local four-file kit is build/ilinux-31ar-kit. Git deliberately contains
source/public profile and receipts, not compiled binaries. Reuse already held
verified candidate and boot021; only the new small helper and public profile
need private transfer if absent. Report any missing delivery, without rebuilding
or fetching a large image just to review the page.

The ignored build/ilinux-31ar-helper-transfer folder contains exactly those two
new files: the 125,168-byte helper and 823-byte profile, 125,991 bytes total.
Use the established private sharing method if M1 needs them. Their exact
individual hashes are in delivery.json; no new helper binary is published.

If the exact four-file kit is present on M1, prepare/check inertly:

    python3 -I tools/recovery31ar/package.py --prepare \
      --kit build/ilinux-31ar-kit --output build/31ar-m1-review-page
    python3 -I tools/recovery31ar/package.py \
      --page build/31ar-m1-review-page/recovery.html --check-only

If the helper has not arrived, source-profile preparation can verify exactly
the same page without claiming delivery:

    python3 -I tools/recovery31ar/package.py --prepare-source-page \
      --output build/31ar-m1-source-page
    python3 -I tools/recovery31ar/package.py \
      --page build/31ar-m1-source-page/recovery.html --check-only

Compare the exact generated profile, install/restore pastes and all three pages
with M5's offline preparation receipt. This opens no socket and executes no
helper. Both operations have independent one-box HTML pages as well as the
combined two-box recovery.html. Record production delivery separately from
source-profile page verification.

## Later physical test, not yet a restart cue

After M5 reviews your PASS, exact lab staging and the reviewed live page must be
confirmed. A fresh explicit physical scope must cover temporary shared-Preboot
RW access, one lab candidate installation, one bounded diagnostic boot,
conditional lab-only CTRR preparation, boot021 restoration and temporary
lab/default return. Macintosh HD must remain at Full Security throughout.

Before installation the restore page and exact rollback must be independently
accessible from Recovery, even if the native guest or USB link never comes up.
Keep camera recording OFF throughout Recovery/authentication and Apple command
output. After complete install/readback/cleanup success, record the single
native window, bounded by an independent 90-second deadline. No M1 restart or
USB proxy is required for the embedded diagnostic.

A passing result-display validator is not installation success: it deliberately
prints well-formed REFUSED records safely. A native boot cue requires the actual
controller INSTALL_COMPLETE, candidate/readback and cleanup success, writer
exit zero, and the final shell success record with helper exit zero. Any missing
record or refusal means no boot or retry. Restore likewise requires actual
RESTORE_COMPLETE, verified boot021 and cleanup plus final shell success; a
verified already-restored no-op can report writer exit minus one.

Observe Aura entry, Linux entry and the finite test summary separately. A CPU
list alone is not all-core execution: require the distinct pinned workers,
checksums/timer results and 60-second liveness evidence. Tick labels are not an
independent wall clock. The current candidate does not boot the Omarchy desktop
or prove macOS-level CPU/GPU/memory/storage/network/power behavior.

Return to paired lab Recovery for the independent boot021 restore. A successful
restore requires exact boot021 identity, intended lab CTRR state, preserved
Original guard and known owned cleanup. Restore Macintosh HD as Startup Disk
separately; no payload result proves the default selection. Stop on any refusal
or uncertainty, retain all private state and report rather than retrying.

Publish only sanitized finite review/test results in a new M1 report. Keep
actual Recovery/RW mount/install/restore/native Linux/SMP/performance NOT RUN
until observed. No private paths, LAN addresses, identifiers, raw policy output,
credentials, media or proprietary artifacts belong in Git.

# 31AU M1 handoff: new transaction source/package review

Read the newest project rules/status and the 31AU build/research records before
review. Preserve every earlier kit, private key/baseline/transaction, consumed
receipt and evidence file. Never reset or replay the spent 31AR transaction.
Keep Macintosh HD at Full Security. No restart follows an offline pass alone.

## What changed

31AT's M1 review passed with clearly recorded missing-input limits. It supplied
offline diagnostic components, not a deployed controller. Owner-authenticated
saved-state observations established candidate UNKNOWN and explicitly disabled
lab Kernel CTRR; all preservation predicates passed, and the saved restored
capture passed exact BOOT021/disabled-CTRR. Human restoration and Original desktop/
default return remain closed. No current-policy repetition is needed.

31AU creates a new profile/helper/state namespace and integrates finite object
diagnostics into the controller. It starts from exact BOOT021, preserving the
restored system instead of requiring the obsolete 31AF object or old key. The
same candidate and boot021 remain pinned; no accelerated Linux image is implied.
Candidate exactness and policy requirements remain enforced. The separate CTRR
qualification record distinguishes supported evidence from any remaining blocker.

## Review scope

1. Verify `native/boot/attempt31au-package/source-sha256.txt` and the retained
   167-source 31AS closure. Verify new public profile/build/delivery binding and
   the genuine four-file kit when the new helper is present. Missing production
   inputs must remain NOT RUN; do not substitute old helpers or synthetic bytes.
2. Review `tools/boot-object31au-native/`: new state/scratch/profile/helper names;
   exact BOOT021 initial baseline; fresh own key/target binding; durable spent
   markers; guarded mount/writer/readback lifecycle; precise finite diagnostics;
   strict result validation; independent candidate-free boot021 restore.
3. Review `tools/recovery31au/`: reversible original-source transformations,
   full retained AS utility/hash/profile repair, correct new helper executable
   mode, fixed kit/state and route, source/build/profile rechecks and copy guards.
   The original recognizer remains the only acceptance authority.
4. Run only the new focused controller and package tests using their README
   commands. Attribute M5 evidence separately and record exact local skips.
   Do not rerun historical suites or rebuild frozen production helpers merely
   to fill missing coverage. No actual policy/private-state query is required.
5. Read `research/attempt31au-ctrr-2026-11-15.md` and its finite JSON evidence.
   It qualifies no enable-only policy writer; the candidate guard remains
   enabled, and a diagnostic visit must stop on a failed postcondition.
   Reject any interpretation that silently weakens
   the guard, proves hardware from a VM, or treats a reported other-board boot
   as native SMP/performance evidence on this machine.

## Package and later serving

The active four-file kit is `build/ilinux-31au-kit-v2`; public pins live under
`native/boot/attempt31au-package/`. The new page uses route `/31au`, with a
combined page and separate one-box install/restore pages. The M1 operator can
manage its server and private URL directly; no repeated page-readiness approval,
M1 restart, proxy or clipboard calibration is requested for this offline review.

Source-only pages may be prepared without binary delivery:

```sh
python3 -I tools/recovery31au/package.py --prepare-source-page \
  --output build/31au-source-page-v2
python3 -I tools/recovery31au/package.py \
  --page build/31au-source-page-v2/recovery.html --check-only
```

The M5 owner stages only the reviewed new kit, with local administrator
authentication, after its concrete source/binary review. Staging is a lab Data
copy and does not install a boot object or change Startup Disk/security. Do not
start a Recovery transaction or direct a restart until the explicit M5 cue.

## Return report

Publish a concise review with actionable findings, exact pins and actual local
test counts/skips. Preserve old state and received genuine artifacts. Record
host staging, controller/Recovery/writer actions, native Linux/SMP/GPU/performance
and OS/firmware/security changes as NOT RUN unless separately observed and
authorized. Keep private data, raw policies, identifiers, Apple bytes, credentials
and private URLs out of Git.

After acceptance, the later authorized workflow uses one complete install box,
stops on refusal, and retains independent exact boot021 rollback and separate
Macintosh HD default/desktop return. This file is an offline review handoff,
not authorization to execute that workflow.

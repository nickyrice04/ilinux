# 31AU: M5 accepted the review; prepare the diagnostic window

November 15, 2026. M5 accepts M1's `9faac49` review with its explicit coverage
limits. All 190 inputs and six prepared outputs match the reviewed V2 package;
the four production files are already owner-confirmed staged on M5 lab Data.
Do not substitute the locally built M1 helper for the pinned production helper.
No repeat review suite, image transfer, staging, policy check, M1 restart, proxy
or clipboard calibration is requested.

At publication of this handoff, the owner has been asked for the concrete 31AU
boot-change authorization. **Wait for that authorization and the M5 cue before
any restart, Startup Disk selection, Recovery writer or native test.** This
document records accepted preparation; it does not supply that authorization.
Macintosh HD must remain at Full Security.

## M1 preparation

Reuse the exact source-only pages already prepared during review. Serve the
combined V2 page at `/31au` using `tools/recovery31au/package.py`; the ordinary
server command is documented in its README. Its body is 18,133 bytes, SHA-256
`2361cfc8be8e1664da1cfe24117f760e45756ed5430766f7cdf8293fb8acc3c4`.
M1 manages serving directly and gives its private URL to the owner. No separate
M5 live-URL approval round is needed. Keep the independent restore box available
through the entire visit; a read-only server refresh must never replay install.

The original `attempt31au-instructions.md`, profile, helper, kit and 190-source
closure stay exact. Missing genuine compressed/copy/bootstrap inputs remain
attributed to the existing M5 evidence, not silently recounted as M1 passes.
M1's reported 37 normal and 37 sanitized controller methods, 12 ordinary package
methods plus one skip, and seven renderer methods are accepted as stated.

## Later authorized sequence

1. M5 temporarily selects **iLinux Boot Lab** as Startup Disk, then stops before
   restarting. The owner handles local authentication directly in macOS.
2. After the explicit cue, the owner shuts down, holds power for Startup Options,
   and chooses **Options → Continue** for the lab's paired Recovery. Do not select
   the lab tile as a substitute for entering Recovery before installation.
3. Keep camera recording off during Recovery/authentication and Apple commands.
   Open M1's `/31au` page, copy the complete **install** box, switch to Terminal
   and paste it once. No simultaneous browser/Terminal windows are required.
4. On refusal, preserve the finite diagnostic and stop candidate execution.
   Copy the complete independent **restore** box and run it once in that Recovery
   session. Do not reset state, edit commands, accept an unknown payload or retry
   the spent install. If restore refuses, preserve its result and return safely
   to Macintosh HD without claiming rollback succeeded.
5. Only `INSTALL_COMPLETE`, `candidate_verified=true`, `cleanup_verified=true`
   and final shell helper exit zero permit the separately authorized candidate
   boot. The helper's exact candidate, enabled CTRR and preservation predicates
   must all pass; a result-validator display pass is insufficient.
6. If permitted, observe **one** Linux RAM window, at most **90 seconds**, with
   the owner/M1 external timer. Record loader/Linux entry, CPU/concurrent-work
   and liveness output if present. The image is the existing RAM diagnostic,
   not an accelerated Omarchy desktop. Stop on a reset or the deadline; do not
   let a default lab selection cause repeated candidate boots. Recording can
   start only after authentication is over.
7. Return to the lab's paired Recovery for the complete independent restore box.
   Require `RESTORE_COMPLETE`, `rollback_verified=true`, `cleanup_verified=true`
   and final shell helper exit zero. No success is inferred from a desktop return
   or an Apple writer exit alone.
8. Restore **Macintosh HD** as default Startup Disk, return to its normal desktop,
   and confirm both separately. Keep credentials, raw policies and private URLs
   out of the public report; transcribe only finite result/diagnostic fields.

The later scope is limited to the reviewed lab candidate, conditional existing
lab-only CTRR preparation for raw rollback, exact boot021 restoration and default
return. No new volume, Original policy writer, firmware update, force/reset,
candidate guard relaxation or extra native window is introduced.

## Decision value and report

The CTRR cause remains unqualified. That does not block a guarded diagnostic
Recovery visit: this controller distinguishes unchanged selection, selected-file
read failure, framing/codec/decode mismatch and actual policy mismatch before
allowing a boot. It still refuses native entry on the failed postcondition.

Report the actual install result and nested diagnostics, whether a native window
occurred, its duration and observed markers, the actual restore result, and the
separate Original desktop/default confirmations. Keep Linux/SMP/GPU/performance
NOT RUN when no corresponding hardware test ran. Preserve all prior state and
consumed receipts. No physical behavior or macOS parity follows from this review.

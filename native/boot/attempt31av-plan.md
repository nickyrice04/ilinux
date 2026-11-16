# 31AV: repair and qualify readback before another boot

November 15, 2026. **Offline work only; no restart or replacement kit is ready.**

## What 31AU actually established

M1's closed report at `9a6411c` records a refused installation after Apple writer
exit zero. The selected reference changed, its file was read successfully, and
the original recognizer reached `IMG4 / LZFSE / DECODE_REJECTED`. Framing, bounded
compressed extent and declared-size checks therefore passed. Decoding did not
complete; this is not a successful decoded comparison against the candidate.
Lab Kernel CTRR remained explicitly disabled, independently failing the required
candidate contract. No Linux or physical secondary-core test occurred.

The owner explicitly confirmed `RESTORE_COMPLETE`, rollback and cleanup true,
and final helper exit zero, then separately confirmed the Macintosh HD desktop
and default. These are human-confirmed observations; a raw restoration transcript
and separate Apple writer status were not supplied. The safe return is closed,
and another manual policy check is unnecessary. See the
[M1 result](attempt31au-recovery-2026-11-15-result.md).

## Work that can proceed without a reboot

1. **Reproduce the decoder failure using project-owned inputs.** Compare the
   unchanged original stream recognizer with Apple's buffer decoder, using
   deterministic generated content, both encoder APIs, source/output chunk
   boundaries, genuine project candidate round trips and malformed controls.
   A valid desktop counterexample has already been reproduced. That establishes
   a verifier compatibility defect on those inputs, not the cause of the
   unavailable historical Recovery carrier.
2. **Implement a bounded alternative in a new module.** Preserve strict complete
   LZFSE framing, declared-size limits and exact known size/SHA-256 identity.
   Allocate the independently framed size plus one byte: the buffer API can
   return its entire destination capacity on truncated output. A decoder return
   alone must never authorize a candidate. Keep the frozen recognizer and all
   consumed AU state unchanged; qualify the proposal before any integration.
3. **Trace the separate CTRR request across its actual library boundary.** REA
   and independent instruction-byte checks extend the earlier `kmutil` trace
   into the generic `libbootpolicy` client. Distinguish request construction
   from service-side policy semantics, and the desktop library from the actual
   historical Recovery runtime. No direct API call or policy writer is part of
   this investigation. Findings belong in the
   [CTRR record](../../research/attempt31av-ctrr-2026-11-15.md).
4. **Get M1's offline review of the new code and findings.** M1 needs no reboot,
   proxy, server, staging or new large transfer for this review. Report positive
   tests, deliberate refusals, runtime differences and missing inputs separately.

The [isolated decoder proposal](../../tools/codec31av/README.md) is now implemented.
Producer checks passed 12 methods normally and 12 under ASan/UBSan, zero skips.
Each mode includes a 77-control matrix, both genuine owned-candidate encoder
round trips and strict refusal controls. Independent review reproduced the
77-control/474-stream-trial matrix; root separately passed four focused methods,
including genuine candidate and malformed/count/path controls. A suite PASS means
the proposal and expected counterexamples behaved correctly; it does not mean
every recorded original stream call succeeded. Temporary decoded output can
reach 160 MiB plus one byte, with allocation failure refused. This memory tradeoff
and the actual Recovery runtime remain unqualified for integration.

REA plus independent cache/repack/LLVM checks matched 712 instruction words in
the generic library trace. Root reran the five-range verifier successfully.
The Mach-O request reaches the BootPolicy service; its effect on the existing
disabled CTRR flag is still Unknown. Detailed, separately attributed evidence is
in the [offline receipt](attempt31av-offline-2026-11-15.json).

## The next native test must answer new questions

Do not repeat the consumed 31AU install or weaken its exactness or enabled-CTRR
requirements. A future separately reviewed kit should check bounded synthetic
codec positive/negative controls before its writer, and distinguish initialization,
processing error, no progress, leftover input and output-count disagreement.
The actual AU transaction did not invoke the older reader's codec self-test.

Only a qualified decoder integration **and** an evidence-backed CTRR strategy
justify proposing another installation window. If the remaining distinction is
the Recovery/runtime version, collect only that bounded provenance rather than
repeating unchanged installation. Any new boot or policy/firmware operation
requires its own concrete owner authorization, independent boot021 rollback,
and Macintosh HD default/desktop return. Original remains at Full Security.

## Path from entry to useful Omarchy

The exact-board J716c public reference already reports all 18 physical cores,
native GPU tests and networking on a matched newer kernel/Aura/firmware/runtime
stack. It supports continued software work; 31AU does not establish an
Apple-only dead end. Reuse that stack as a unit after installation and entry
are qualified, retaining its thermal guardian and bounded operating envelope.
It is not evidence of performance parity or a reason to run a Pro-only installer
on this Max. See the [existing exact-board comparison](../../research/attempt31ar-shared-m5-code-2026-11-15.md)
and [full graphics configuration admission](../../kernel/experiments/j716c-graphics-profile/README.md).

Then measure concurrent work across all core types, frequency/thermal behavior,
memory throughput, hardware rendering and input latency, followed by networking
and storage. Compare the same workloads against macOS before claiming parity
or moving daily development into Linux. Native Linux/SMP/GPU/performance remain
**NOT RUN** in this closed attempt.

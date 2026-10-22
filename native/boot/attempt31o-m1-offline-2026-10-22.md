# 31O — independent M1 offline review

**OFFLINE_REVIEW_PASS_NATIVE_HOLD, 2026-10-22 Eastern. Native31O HOLD / NOT RUN;
CPU1 execution UNVERIFIED; Linux SMP NOT RUN.** No restart or physical attempt.
Main fast-forwarded cleanly from `922aeb3` to
`220d8c7027639e8aaf82a0cc8e8b9d4cd8d44cfe`; no local changes discarded.
Reviewed metadata: [M1 result JSON](attempt31o-m1-offline-2026-10-22.json).

## Independently executed checks

The documented `python3 -I tools/m1n1-client/attempt31o-offline.py --image ...`
command exited **0**, result **OFFLINE_REVIEW_PASS_NATIVE_HOLD**. **348 pins and
63 methods PASS**, no skips or repairs. Python3.13.5; elapsed2.127s.

| Suite | Methods PASS |
|---|---:|
| Consumed-report consistency/classification | 33 |
| Synthetic RCfg structure/refusals | 19 |
| Offline intake/closure/input safety | 11 |
| Total | 63 |

The exact-image entry contract and Normal-prefix audit also passed:
56 address cases,112 explicitly assumed translation cases,1,371 relocations.
Mode **reviewed_layout_only**. **Full-symbol validation NOT RUN**, exact symbols
not supplied; allocated-symbol exclusion and complete computed-reference proof
are not established by this mode. These audits do not execute CPU1 or emulate
Apple reset behavior. The earlier932-method native31N intake was not rerun;
this release intentionally selects its new63 offline methods.

**Actual firmware parsing NOT RUN on M1**: no optional private iBootData supplied.
Synthetic decoder tests did run. No firmware was searched for, downloaded,
transferred or published to fill that field. M5's matching-payload structural
result,22,855 commands/417 names, remains separate evidence, not reproduced here.
Likewise M5's VM074/full-symbol outputs and REA706-word findings were not rerun
or independently decoded on M1.

## Consumed reports, independently reclassified

| Report | Classification | Canonical SHA-256 |
|---|---|---|
| 31M | NATURAL_TIMEOUT_WITHOUT_VISIBLE_ENTRY | `5a74a9593b69abf17958cb772bdfaef505084b1c590f7c35a51e8fc20fbd1002` |
| 31N | NATURAL_TIMEOUT_WITHOUT_VISIBLE_ENTRY | `3521be6cb2d92bdf772d404c6f3e5adb20764b204de7ca0d2556867fd6bc7e4d` |

Both classifications and canonical digests match the released validation.
Both retain CPU1 execution UNVERIFIED, first instruction fetch/firmware cause
UNKNOWN, negative_excludes_execution=false and native_ready=false. The tool's
report_authenticity=NOT_ESTABLISHED describes its logical classification scope;
it does not independently authenticate recordings or reconstruct target state.
The original consumed reports and human-return records are preserved.

Count checks retain the distinction between31M's4 actual power/state phases and
31N's3 phases with after_first_start explicitly omitted. 31N arrival_samples63
and Device-vector samples64 remain separate, not adjusted. A completed local
pair, power transition or successful CPU0 control never becomes CPU1 execution
proof. Missing/faulted data is incomplete; contradictory metadata is refused;
possible positive metadata requires committed-record review, not automatic proof.

## Independent source review

Read the complete offline runner, evidence classifier and structural decoder,
their regressions, handoff, controller audit, firmware/upstream research and next-
work plan. No code-level blocker was found for the documented offline scope.

The runner has no live argument, supervisor, client import, discovery or target
command. Its fixed repository subprocesses are isolated Python with bounded
execution, input sizes and source closure. It checks the retained image contract
without feeding the newer31N report into an older31K-only schema. Optional
private parsing binds the reopened child payload's hash/size/counts as well as
the initial read. No optional private child was run here.

The classifier validates selected report counters, completion ordering, phase
and identity consistency, controls and unsupported claims. Strict JSON rejects
duplicate keys, non-finite numbers, non-regular inputs and structural excess.
Returned diagnostics are fixed labels/counts/hashes, not arbitrary report text.
It is a consistency checker of supplied sanitized evidence, not a hardware model,
independent authenticity check or exhaustive revalidation of every preflight.

The RCfg parser bounds directory/sections, overlaps, alignment, names, record
lengths, sequence references and counts. Unknown opcodes/flags stay opaque; no
operand/name bytes are emitted. It does not validate nesting, evaluate conditions,
interpret semantics or execute/replay a command. Structural validity cannot
identify the active raw-boot firmware branch or authorize additional MMIO.

The reviewed research correctly keeps attributed external failures, static
conditional restore findings and native measurements distinct. M1 reviewed those
notes as supplied; it did not refetch their external sources or inspect Apple
decompiler output. They do not prove this machine's precise cause or that a
software solution is impossible. Normal/Device markers share a first-store path;
their negative observations are not wholly independent. Pre-start reset mirrors
also do not establish persistence through the power transition or CPU1's PC.

## Inputs and preservation

348-file manifest SHA-256:
`e95055bc87a7b395fdf9a2ce89937cc0007b2ed0e8e2acf729789de0efe80f39`.
Frozen N330/M306/L281/K254/J226/I202/H186/host6 independently verified unchanged.
Retained3,932,160-byte boot021 SHA-256:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
All13 retained-package file hashes/sizes match the earlier verified local receipt.
Client checkout remains clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`,
checked using Git only; no client module or downloaded code was imported/run.

Before/after digests of prior attempt31 receipts and offline evidence match.
No consumed file was cleared, renamed, overwritten or forced. No31O native use
file was created. Private full output, digest snapshots and bookkeeping remain
ignored under `build/native-intake/attempt31o-offline/`. Git receives reviewed
metadata and original notes only. Bounded owned caffeine assertion handled;
no sleep setting changed.

**New discovery queries0/device opens0/target requests0/native invocations0.**
Neither device restarted. No live/version/security check, install, transfer,
Recovery, volume/security/default/firmware change, VM/REA run or native runner.
Original Full/lab Permissive/Macintosh HD default remain last reported, not
freshly verified. Installed boot021, retained boot042 and client pin unchanged.

## Decision

Publish this independent offline review, then wait. **This pass is not boot
readiness: native31O remains HOLD / NOT RUN.** M5 owns the next firmware-
prerequisite investigation and separate offline GPU work. No physical follow-up,
equivalent-marker repetition, debug probe, firmware replay or consumed-runner
reuse follows. A future proposal needs a fresh identity, specific discriminating
condition, complete operation/fault contract and separate offline review.
CPU1/all-core execution and performance/energy parity remain unverified.

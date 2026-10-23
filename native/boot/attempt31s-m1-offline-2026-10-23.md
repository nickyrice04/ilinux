# 31S — independent M1 offline CPU/GPU review

**OFFLINE_PASS_NATIVE_HOLD, 2026-10-23 Eastern. Native31S HOLD / NOT RUN;
Linux SMP/native GPU acceleration NOT RUN; CPU1 execution UNVERIFIED.**
Neither Mac restarted. Main fast-forwarded cleanly from `ff1ed8e` to
`58ca707029eeb0bf3a0dcbe3b72ff03b00edd25f`, preserving earlier evidence.
This review follows [the M1 handoff](../../tools/m1n1-client/attempt31s-instructions.md).
[Reviewed metadata](attempt31s-m1-offline-2026-10-23.json) accompanies this report.

## Independent execution

The documented isolated-Python command using retained boot021 content inside
boot042 exited **0 in 6.574 seconds**. **441 pins /207 Python methods /74 portable
C groups PASS**, with no skips, source repairs or installs. Actual M1 tools:
**Python 3.13.5; Apple clang 17.0.0 (clang-1700.3.19.1)**.

| Coverage | PASS |
|---|---:|
| Repeated31R Python review | 176 methods |
| New synthetic relative-dispatch resolver | 22 methods |
| New intake/source/refusal checks | 9 methods |
| Python total | 207 methods |
| Repeated descriptor/planner/GPTBAT/lifecycle C | 60 groups |
| New bootstrap codec/injected transport C | 14 groups |
| Portable C total | 74 groups |

Original C compiled as C11 with `-Wall -Wextra -Werror -pedantic -O2`; exact
success tokens were required. The new resolver tests cover signed arithmetic,
independent table/target anchors, full table extent, explicit mappings, whole
instruction containment, strict schema/type checks, private CLI errors and
1,024 grid destinations. Bootstrap tests cover literal encoding boundaries,
all20 non-address-bit mutations, 10,000 address roundtrips, all65,536 upper-word
patterns for the receive discriminator, output preservation and exactly-once/
zero-on-refusal mock callback behavior. These are software cases, not hardware
coverage or a device handshake.

The complete review output is byte-identical to the released host, curated-host
and VM output, SHA-256:
`85d12acd463ebfe54a7132cd037f2319d2cd12a6fdc1bb8ab3b971cecb0e1e39`.
Compiler temporary directories for all five C components stayed under ignored
build storage and were removed. **Linux ASan/UBSan NOT RUN on M1**; M5's VM079
sanitizer pass for the new14 groups is separate evidence. Its prior60 C groups
were repeated portably, not re-sanitized. Matching JSON does not reproduce REA,
private firmware integration or a VM execution on this M1.

## Independent implementation review

Read the handoff, runner, original Python/C implementations, headers, both test
suites, component READMEs, all three research notes, private-integration metadata
and CPU/GPU/job validation records. **No code-level blocker found for the
documented offline contracts.** Production and test sources were unchanged.

The resolver keeps the table file offset separate from the branch-target anchor.
It binds immutable image bytes to an explicit SHA-256, bounds the full table and
selector list, rejects bools as integer fields, interprets signed LE32 offsets,
refuses64-bit arithmetic wrap, and requires aligned four-byte targets in exactly
one file mapping and an allowed code range. Virtual overlaps/file aliases and
duplicate selectors are refused; requested selector order is preserved. Failure
returns no partial metadata and leaves input objects unchanged.

The supplied layout is a premise. Hash agreement does not authenticate its
origin, infer instruction semantics, discover live mappings or establish runtime
permissions. Only requested targets are resolved; checking the full table extent
does not qualify every destination. The CLI was tested with synthetic files;
M1 did not supply the private retained generic firmware to this resolver.
Its local reader assumes stable local files during the read; it is not a
concurrent filesystem security boundary. No input instruction executes.

The GPU encoder preserves a distinct firmware-address type, requires the full
outgoing fixed header and reserved gap, and rejects values at/above2^44 before
publishing output or calling the injected transport. Zero and unaligned values
are format-representable, not qualified firmware addresses. The decoder checks
all20 non-address bits. No CPU physical/GPU virtual translation is performed.

Submission requires the explicit service endpoint and a non-null callback, then
calls that callback exactly once with the word by value. It preserves the opaque
32-bit callback result, including errors. Adapter OK means a callback was called;
it does not mean delivery, device acceptance or successful boot. A callback
error cannot be classified as never sent and must not trigger automatic retry.
Pre-submission refusal calls nothing and preserves output. Caller serialization,
provider/address qualification, non-overlap and lifetime duties remain explicit.
There is no real transport, device open, allocation, MMIO, wait loop or native
readiness promotion in this component.

The receive helper preserves all64 raw bits and classifies only bits48–53 as
CASE_2/CASE_9/OTHER. It is deliberately weaker than full-header validation and
cannot authenticate an acknowledgment or completion. The pinned public m1n1
files were independently read as text and their three hashes matched the released
record and clean checkout. They corroborate the outgoing header/address field,
separate endpoint transport and full-type0x42 event distinction, plus initdata
construction/UAT publication preceding submission. They were not imported or
executed. Shared lineage is not independent G17C hardware evidence. Gravity's
archive comparison remains M5's separate evidence, not re-read here.

## Findings, interpretation and unresolved prerequisites

M1 reviewed public behavioral metadata without opening Apple pseudocode/private
binaries or member-only messages. M5 reports two CPU and six GPU REA queries,
321 CPU words (157 new beyond the31L/Q/R union;164 overlap) and644 GPU words.
These private comparisons were not independently decoded or reproduced on M1.

The new CPU record resolves services12/17 to local handlers through the retained
generic boot image's dispatcher. This supersedes31R's unresolved static ownership
edge. The original resolver distinguishes table location from target anchor and
M5's private integration qualifies five selected entries, not all131 destinations.
The handlers configure range-protection state; they do not supply a secondary-
release operation. Historical descriptors, register-bank selection, effective
secondary protection and CPU1's first fetch remain unknown. Static ownership
cannot establish that these ranges caused the failure or that Linux must replay
the services. Four service12 register accessors remain unnamed; EL/ACC names do
not independently qualify live privilege or core ownership.

The direct GPU owner-initialization callee binds software callbacks and returns
success; it is not a device handshake. This appropriately narrows31R's defensive
ACCEPT/REJECT vocabulary without rewriting the frozen component. Identity address
conversion in a selected static class does not qualify the running class or any
CPU physical address. Endpoint selectors, provider roles and ADT GFX/GFX1 remain
separate. Firmware/shared-data ownership, publication, UAT geometry, actual
transport lifetime and bounded observable completion are unqualified.

All six GPU dossier gates remain manual_review_required; removed-block and
unresolved-indirect-jump warnings remain explicit. Earlier31Q/31R whole-function
refusals remain intact. Zero out-of-range P-code does not establish semantics or
native behavior. Carrier identity was not independently matched to the running
kernel. **Role/address domains UNQUALIFIED; firmware ABI and G17C UAT UNKNOWN.**

The upstream note separates an attributed firmware diagnosis from proof that
only Apple can fix every path. Cache-publication changes and other-chip SPTM
research remain comparators, not a demonstrated T6050 fix. M1 did not refetch
external sources, compile upstream code or verify current branch status. No
native SMP/GPU, responsiveness or energy improvement follows from this review.
Prior31O's closure/network qualifications remain preserved via31P's correction.

**REA, private firmware parsing/integration, full symbols, upstream builds,
Linux sanitizers, VM execution and live version/policy checks: NOT RUN on M1.**
No private input was downloaded or transferred for this pass.

## Input integrity and preservation

441-file manifest SHA-256:
`8bc15934985daeb816d00aaa4f5b5f2ad52bbe4f827494031c51eb6698e17158`.
All12 earlier frozen closures R420/Q402/P379/O348/N330/M306/L281/K254/J226/I202/
H186/host6 and every listed hash independently PASS unchanged. All13 retained
package hashes/sizes match the earlier receipt. Retained boot021 SHA-256:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Client clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, verified using Git
without import/execution. Installed boot021 and retained boot042 unchanged.

Before/after hashes match for357 evidence files directly under earlier attempt31
intake directories. No consumed receipt cleared, renamed, overwritten, forced
or reused; no31S native-use file created. Private output/bookkeeping remains
ignored under `build/native-intake/attempt31s-offline/`. The owned bounded
caffeine assertion has exited; sleep settings were unchanged.

**New discovery queries0 / device opens0 / target requests0 / native invocations0.**
Neither Mac restarted. No USB connection, image transfer, installation, Recovery,
volume/security/policy/default/firmware change. Original Full/lab Permissive/
Macintosh HD default remain last reported, not freshly checked.

Publish and wait. **Native31S HOLD / NOT RUN; no boot readiness grant.** M5 owns
effective CPU entry/range-state evidence and G17C shared-data, role/address and
completion qualification. A future physical test requires its own meaningful
discriminator, bounded implementation and independent review. No automatic
restart, retry, firmware replay or generation alias follows from a software pass.

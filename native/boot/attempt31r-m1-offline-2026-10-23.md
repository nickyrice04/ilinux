# 31R — independent M1 offline CPU/GPU review

**OFFLINE_PASS_NATIVE_HOLD, 2026-10-23 Eastern. Native31R HOLD / NOT RUN;
Linux SMP/native GPU acceleration NOT RUN; CPU1 execution UNVERIFIED.**
Neither Mac restarted. Main fast-forwarded cleanly from `bc4d46c` to
`e36db1208f0912bad2e0f7c0b08722d2bd864659`. No local changes were discarded.
This review follows [the M1 handoff](../../tools/m1n1-client/attempt31r-instructions.md).
[Reviewed metadata](attempt31r-m1-offline-2026-10-23.json) accompanies this report.

## Independent execution

The documented command, using isolated Python and the retained boot021 image
inside boot042, exited **0 in 5.944 seconds**. **420 source pins, 176 Python test
methods and 60 portable C groups PASS**, with no skips, source repairs or installs.
Actual M1 tools: **Python 3.13.5; Apple clang 17.0.0 (clang-1700.3.19.1)**.

| Coverage | PASS |
|---|---:|
| Repeated 31Q Python review | 167 methods |
| New 31R intake, source-binding and refusal checks | 9 methods |
| Python total | 176 methods |
| Repeated descriptor/planner/GPTBAT C components | 39 groups |
| New attachment lifecycle C component | 21 groups |
| Portable C total | 60 groups |

C used `-std=c11 -Wall -Wextra -Werror -pedantic -O2`; exact component success
tokens were required. The new lifecycle tests exercise invalid/stale inputs,
callback ordering, explicit rejection, replacement, provider reset/end, full-width
counter bounds and unchanged state/output on refusal. Their depth-five traversal
covers 32,768 paths / 37,448 transitions over the test's eight-choice event subset;
it is not exhaustive coverage of every event value or real callback schedule.
Earlier software tests were repeated through the inherited runner, not counted
again as newly added methods. Compiler temporary directories for all four C
components were confined to ignored build storage and removed.

The complete review output is byte-identical to the released host, curated-host
and VM output, SHA-256:
`947b892ef50cdf14cb0d2e052f6a8fb5d8f1c2fe8066ba6479505db16e075e5d`.
**Linux ASan/UBSan NOT RUN on M1.** M5's separate VM078 sanitizer pass applies to
the new 21 groups; its prior 39 groups were repeated portably, not re-sanitized.
Matching JSON proves output agreement, not reproduction of VM or REA execution.

## Implementation review

Read the handoff, runner and inherited offline chain, lifecycle header/C/tests,
README, all three research records, CPU behavioral contract and CPU/GPU/integration
validation records. **No code-level blocker found for the documented offline API.**
No production or test source was changed.

The reducer separates payload success, preload evidence, subscription completion,
endpoint match and explicit acceptance. A match cannot create acceptance. A new
instance clears the old acceptance; rejection/termination affects only the
matching instance; old-instance acceptance/rejection/termination consumes the
new ingestion sequence without replacing the current endpoint. A newer provider
epoch clears all evidence, old epochs are refused, and provider end preserves
its epoch while clearing attachments. Invalid/stale inputs return before state
publication. Inspection initializes native readiness to zero in every view.
Callbacks may be ingested before the subscriptions-complete observation.

These guarantees require caller serialization, valid accessible objects, unique
non-recycled instance tokens within an epoch and causal ordering of MATCH events.
A newer-sequenced stale MATCH would intentionally look like replacement: the
caller must reject it. Sequence numbers do not authenticate evidence or recover
physical ordering. The two local slots do not identify ADT roles, endpoint
selectors or firmware processors. An explicit ACCEPT is supplied evidence, not
proof the device initialized. No native adapter, MMIO, ioctl, queue submission,
firmware request or automatic readiness promotion exists in this component.

The offline runner checks exact closure before and after, runs fixed original
sources with the existing compiler and refuses failed, empty or skipped suites.
There is no live mode. Original C was compiled/executed; no third-party source,
client import or native controller ran on M1.

## Research interpretation and remaining blockers

M1 reviewed published behavioral records, without opening Apple pseudocode,
private binaries or member-only community material. M5's four CPU/three GPU REA
queries and private word comparisons remain **separate static evidence**.
The CPU record reports 853 checked words, of which only 156 are new beyond31Q;
697 overlap. The GPU record reports 1,233 checked words. None was independently
decoded on this M1 review.

The corrected CPU labels matter: the apparent consumer was a failure reporter,
and the apparent mutator was a read-only state accessor. Successful range setup
crosses an unresolved service boundary. The following six descriptors cannot be
counted as CPU clusters; one base lies within the retained ISP resource window.
Static containment and call adjacency neither qualify runtime ownership nor
establish a CPU1 release operation. Historical raw metadata remains inferred,
and the actual service owner/privilege/permission effects and first CPU1 fetch
remain unknown. No replay or native discriminator follows from these findings.

GPU preload, null-payload success, registration, match and accepted initialization
remain distinct. The selector-specific owner-initialization evidence cannot be
assumed for the other selector. One provider whole-function
`rejected_cross_boundary` gate and the manual-review/removed-block qualifications
remain in force; completed queries and bounded word matches do not override them.
Earlier31Q refusals stay intact. The retained kernel carrier was not independently
matched to the running kernel.

**Endpoint role mapping and CPU address domain UNQUALIFIED; firmware ABI and G17C
UAT layout UNKNOWN.** Shared-data ownership/publication, real endpoint identity,
transport lifetime/locking and observable completion remain prerequisites to a
native adapter. No new GPU/SMP operation or performance/energy improvement is
established by this pass.

The ecosystem note usefully distinguishes chip recognition/ISA support from
runtime admission and equal-size UAPI declarations from equal semantics. Its
reported G17C exclusions, VM-create flag difference and sparse-tile backing
semantics justify keeping the existing strict planner subset. This M1 review did
not refetch those external sources or compile their headers; the source-derived
comparison remains M5's evidence. It is not a new upstream compatibility result.

**Full symbols, actual private firmware parsing, REA, upstream builds, Linux
sanitizers, VM execution and live version/policy checks: NOT RUN on M1.** No
package, image transfer, host install or settings change occurred. Prior31O's
closure/network qualifications remain preserved by the31P correction; frozen
historical records are not silently rewritten.

## Input integrity, preservation and decision

420-file manifest SHA-256:
`c1e31bdf90a248c06b31990fc85ffb3ec18b7b326f40dad4024b18cb38a5b2d4`.
Frozen Q402/P379/O348/N330/M306/L281/K254/J226/I202/H186/host6 manifests and every
listed source hash independently PASS unchanged. All13 retained-package hashes
and byte sizes match the prior receipt. Retained boot021 SHA-256:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
The client remains clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, checked
using Git only. Installed boot021/retained boot042 remain unchanged.

Before/after hashes match for 348 existing evidence files directly under prior
attempt31 intake directories. No consumed receipt was cleared, renamed, forced,
overwritten or reused. No31R native-use file was created. Private stdout/stderr
and bookkeeping remain under ignored `build/native-intake/attempt31r-offline/`.
The bounded owned caffeine assertion has exited; sleep settings were not changed.

**New discovery queries0 / device opens0 / target requests0 / native invocations0.**
Neither Mac restarted. No USB connection, image transfer, Recovery, policy/default,
volume/security/firmware change or native attempt occurred. Original Full/lab
Permissive/Macintosh HD default remain last reported, not freshly checked.

Publish this review and wait. **Native31R HOLD / NOT RUN; no boot readiness grant.**
M5 owns the successful CPU range-service contract and G17C role/address/shared-data
investigation. A future physical test needs a meaningful distinguishing question,
a bounded original implementation and independent review. No automatic retry,
firmware replay, generation alias or restart follows from this software pass.

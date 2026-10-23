# 31T — independent M1 offline CPU/GPU review

**OFFLINE_PASS_NATIVE_HOLD, 2026-10-23 Eastern. Native31T HOLD / NOT RUN;
Linux SMP/native GPU acceleration NOT RUN; CPU1 execution UNVERIFIED.**
Neither Mac restarted. Main fast-forwarded cleanly from `822d53f` to
`1f12a4ae583e7ac18bc81189a4c4b81ba34b5444`. Earlier evidence was preserved.
This review follows [the M1 handoff](../../tools/m1n1-client/attempt31t-instructions.md).
[Reviewed metadata](attempt31t-m1-offline-2026-10-23.json) accompanies this report.

## Independent execution

The documented isolated-Python command using retained boot021 content inside
boot042 exited **0 in 7.372 seconds**. **458 pins /216 Python methods /88 portable
C groups PASS**, with no skips, source repairs or installs. Actual M1 tools:
**Python 3.13.5; Apple clang 17.0.0 (clang-1700.3.19.1)**.

| Coverage | PASS |
|---|---:|
| Repeated31S Python review | 207 methods |
| New intake/source/refusal checks | 9 methods |
| Python total | 216 methods |
| Repeated descriptor/planner/GPTBAT/lifecycle/bootstrap C | 74 groups |
| New mapping-lease C | 14 groups |
| Portable C total | 88 groups |

Original C compiled as C11 with `-Wall -Wextra -Werror -pedantic -O2`, requiring
exact success tokens. The lease tests cover accepted/borrowed/partially failed
resources, cleanup with/without an obligation, mixed unresolved results, opaque
statuses and zero tokens, one-shot behavior, callback reentrancy, maximum bounds
and a shared resource with distinct independent leases. The2,432-case matrix
varies batch size, first preparation refusal and16 repeating ownership patterns;
it is not exhaustive coverage of cleanup failures or concurrent schedules.
Separate tests cover multiple incomplete cleanups on success and failure.

The complete review output is byte-identical to the released host, curated-host
and VM output, SHA-256:
`ecf940846a26ea5969aca1f3c9c8dd098d6eff1d3b6500f8e7e8139db48557fe`.
Compiler temporary directories for all six C components stayed under ignored
build storage and were removed. **Linux ASan/UBSan NOT RUN on M1**; M5's VM080
sanitizer pass for the new14 groups is separate evidence. Its prior74 groups
were repeated portably, not re-sanitized. Matching output does not reproduce
private REA/evaluator execution or a VM run on M1.

## Independent code review

Read the handoff, runner, original C/header/tests, intake tests, README, all
three research notes and CPU/GPU/job validation metadata. **No actionable issue
found within the documented offline contract.** Production/test sources unchanged.

The helper validates nonempty batches up to16 entries and required callbacks
before mutation. It copies resource tokens and operations into the batch, enters
PREPARING before invoking callbacks, prepares in input order and stops at the
first refused result. Acceptance, cleanup obligation, lease token and opaque
status remain separate. Nonzero status does not override explicit acceptance;
a failed operation can retain an obligation, and an accepted borrowed operation
can have none. No proprietary status code is converted into ownership.

Failure cleanup visits every explicit obligation in reverse order, including
the failing entry when required. It records an attempted cleanup before calling
the callback and preserves both preparation and completion results. A failed
cleanup does not prevent independent sibling cleanup. Normal finish has the same
policy. Resources with no obligation receive no completion call. Lease zero is
representable; it is not used as an absent-obligation sentinel.

On preparation failure, the return is PREPARE_FAILED even when cleanup leaves
UNRESOLVED state. A caller must inspect the phase and retained entries before
dropping ownership; that return code alone does not mean cleanup succeeded.
Finish instead returns CLEANUP_PENDING for an unresolved result. All terminal
phases refuse prepare/finish reuse. PREPARING/CLEANING also refuse reentrant
calls; callbacks may inspect but must not mutate the batch. The helper supplies
no locking, authentication, reset, retry or external recovery API.

These guarantees require zero-initialized, untampered batch state, serialized
access, accessible non-overlapping inputs, truthful bounded callbacks that return
normally, and context/resource lifetime through discharge or external recovery.
Every cleanup obligation must remain independently releasable even if another
is unresolved. This excludes dependent backing-pin/mapping graphs; reverse order
alone does not make those safe. Preparation must not publish resources to any
consumer, because a later refusal triggers immediate cleanup. Before a later
finish, the caller must independently establish consumer quiescence. These are
caller preconditions, not conditions the helper measures or enforces on a GPU.

PREPARED means only that every callback accepted. It establishes no cache/UAT
publication, address ownership, firmware acknowledgment or native readiness.
The bound, phases and tokens are original bookkeeping, not a firmware protocol.
There is no actual allocator/map/unmap, DMA/cache operation, device open, MMIO,
transport or firmware submission. All executable callbacks in this review were
local fixtures. Earlier planner/bootstrap components remain separate and frozen.
The runner verifies source closure before/after and refuses failed/empty/skipped
suites without a live mode or native interface.

## Research interpretation and remaining blockers

M1 reviewed published behavioral metadata without opening Apple pseudocode,
private images or member-only material. M5's two initial CPU table-address
no-procedure refusals remain failures, separate from two corrected successful
function-entry queries. The CPU record reports82 checked words,81 new and1
overlapping prior ranges. It identifies a separate range-control preparation
already called in the retained firmware, with no effective-state readback.
That is not a missing-operation diagnosis, historical execution trace or
measurement of CPU1 protection. Live entry PC, visibility, privilege/bank and
first fetch remain unknown. No new qualified native observer or write follows.

The public-source comparison correctly distinguishes boot-CPU system-register
reads from per-core reset mirrors and physical secondaries from guest shadow
arrays. Hypervisor guest setup presupposes working host secondaries; it cannot
supply their first fetch. The XNU-compatible shim is incomplete and requires
monitor residency plus continuing memory-management support. The reviewed
sources demonstrate no exact-machine workaround and do not establish that
only Apple can fix every possible path. M1 did not refetch those sources or
independently verify their current branch state.

M5's six GPU queries report2,935 checked words and bounded mapping preparation,
completion, allocation and initialization edges. Lower failure can already have
rolled back preparation, so an observed opaque error or higher cleanup edge
cannot be translated into a universal Linux ownership rule. Mapping completion
is not firmware acknowledgment. A statically named GPU-VA getter clarifies the
address source but does not establish CPU-physical identity, runtime subclass,
firmware-address validity, ADT role binding or UAT geometry.

The allocation query's truncated high P-code remains unaccepted, including its
known omitted input. All six manual_review_required gates, removed-block and
unresolved-indirect-jump warnings, and older31Q/31R whole-function refusals remain
in force. Complete bounded instruction coverage does not override those limits.
The private sequential path evaluators stub external effects and initial state;
they are neither concurrency/memory-order validation nor native observations.
Carrier identity was not independently matched to the running kernel.

**Role/address domains UNQUALIFIED; firmware ABI/G17C UAT UNKNOWN.** Actual
mapping ownership, safe release, shared-data layout/publication, provider binding
and bounded observable completion remain native-adapter prerequisites. CPU1,
SMP, GPU rendering and performance/energy improvement remain unverified.
Prior31O's closure/network qualifications remain preserved via31P's correction.

**REA/private decoding and evaluators, actual private firmware parsing, full
symbols, upstream compilation, external refetch, Linux sanitizers, VM execution
and live version/policy checks: NOT RUN on M1.** No private input was downloaded
or transferred; no third-party code or m1n1 client was imported/executed.

## Integrity, preservation and decision

458-file manifest SHA-256:
`7a7e8f063dbbf0407912d2abbb5c3cf822c0f3db3654c7781f5dff05823066d7`.
All13 earlier frozen closures S441/R420/Q402/P379/O348/N330/M306/L281/K254/J226/
I202/H186/host6 and every listed source hash independently PASS unchanged.
All13 retained package hashes/sizes match the earlier receipt. Boot021 SHA-256:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Client remains clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, checked using
Git only. Installed boot021/retained boot042 unchanged.

Before/after hashes match for366 evidence files directly under earlier attempt31
intake directories. No consumed receipt cleared, renamed, overwritten, forced
or reused; no31T native-use file created. Private stdout/stderr/bookkeeping
remains ignored under `build/native-intake/attempt31t-offline/`. The owned
bounded caffeine assertion has exited; sleep settings were unchanged.

**New discovery queries0 / device opens0 / target requests0 / native invocations0.**
Neither Mac restarted. No USB connection, image transfer, installation, Recovery,
volume/security/policy/default/firmware change. Original Full/lab Permissive/
Macintosh HD default remain last reported, not freshly checked.

Publish and wait. **Native31T HOLD / NOT RUN; no boot readiness grant.** M5 owns
effective CPU1 state/handoff evidence and G17C shared-data/role/address/publication
qualification. A future physical test requires a meaningful distinguishing question,
a bounded implementation and independent review. No automatic restart, retry,
firmware replay or adoption of another chip's handoff follows from this pass.

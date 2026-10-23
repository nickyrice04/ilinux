# 31V — independent M1 offline CPU/GPU review

**OFFLINE_PASS_NATIVE_HOLD, 2026-10-23 Eastern. Native31V HOLD / NOT RUN;
Linux SMP/native GPU acceleration NOT RUN; CPU1 execution UNVERIFIED.**
Neither Mac restarted. Main fast-forwarded cleanly from `c510d74` to
`dca49e39b85d2b64f72671576911150aecd4140f`, preserving earlier work and evidence.
Review follows [the handoff](../../tools/m1n1-client/attempt31v-instructions.md).
[Reviewed metadata](attempt31v-m1-offline-2026-10-23.json) accompanies this report.

## Independent execution

The documented isolated-Python command using retained boot021 content in boot042
exited **0 in 8.795 seconds**. **492 pins /234 Python methods /103 portable C
groups PASS**, no skips, source repairs or installs. Actual M1 tools:
**Python 3.13.5; Apple clang 17.0.0 (clang-1700.3.19.1)**.

| Coverage | PASS |
|---|---:|
| Repeated31U Python review | 225 methods |
| New intake/source/refusal checks | 9 methods |
| Python total | 234 methods |
| Repeated prior portable C components | 95 groups |
| New mapping encoder/submission C | 8 groups |
| Portable C total | 103 groups |

C used `-std=c11 -Wall -Wextra -Werror -pedantic -O2`, requiring exact success
tokens. New tests cover literal wire bytes, length/address/shift limits,
all65,536 index pairs (256 full;65,280 non-full), callback failures after effects,
reentrancy, copied inputs and one-attempt reuse refusal. All callbacks are local
fixtures; this is neither GPU simulation nor concurrent DMA-ordering validation.
Compiler temporaries for all eight C components stayed in ignored build storage
and were removed.

Full review output matches released host, curated-host and VM bytes, SHA-256:
`b6598abd846455e4c151464b2e2ceabbaaacb83a717c3e2cda26b1778a8f4f64`.
**Linux ASan/UBSan NOT RUN on M1.** VM082's sanitizer pass on the new eight groups
is separate M5 evidence; its prior95 groups were repeated portably, not
re-sanitized. Output agreement does not reproduce REA/private evaluators or a VM.

## Independent implementation review

Read the handoff, runner/tests, mapping header/C/tests/README, all three research
notes and linked CPU/GPU/job validation metadata. **No actionable issue found
within the documented offline contract.** No production/test source changed.

The encoder builds a zeroed24-byte scratch record, preserving the full64-bit
caller-converted firmware VA. It explicitly emits little-endian fields rather
than serializing a C structure. Nonzero4KiB-aligned length must fit32-bit units;
address-plus-length wrap and GART shifts outside14–29 are refused. The ratio
uses firmware shift14 and fits a nonzero16-bit power of two. Reserved fields
remain zero; flags encode only1/5 with no inferred permission meaning. All
validation precedes output publication. These are deliberate strict arithmetic
policies, not qualification of runtime address domains or every native page size.
The earlier44-bit bootstrap mask must not be applied to this64-bit field.

Prepare validates callbacks, indices0–255, mapped extent at least6,144 bytes,
phase and encoding before recording submission state. It captures inputs and
operations without invoking callbacks. One reserved slot distinguishes full:
next producer equal to consumer becomes FULL, while equal current indices mean
empty. FULL invokes no callback and does not wait, resnapshot or call an assumed
near-full helper. Invalid arguments leave state unchanged under the accessible,
non-overlapping input and untampered-state preconditions.

Submit enters BUSY before calling the record writer once at producer times24.
Only explicit write acceptance proceeds to publication once. It retains raw
record, proposed producer, attempted flags and opaque statuses. Nonzero status
is not automatically failure; explicit callback acceptance controls progression.
Write refusal can leave partial slot effects and becomes WRITE_UNKNOWN;
publication refusal may have advanced the shared index and becomes
PUBLICATION_UNKNOWN. Neither is proof of no effects. Further submission and
prepare reuse are refused, including after SUBMITTED. A replacement object is
not permission to bypass external reconciliation. Reentrant submit is refused.

Caller duties remain essential: zero-initialized stable state, no input alias,
sole-producer serialization from prepare through submit, acquired valid indices,
coherent mapping/slot lifetime, consumer advancement only through published
records and truthful bounded synchronous callbacks. Callbacks cannot mutate
state or retain record pointers. The publication adapter must ensure real data
visibility and ordering before the shared producer store; a C11 fence is not a
native DMA contract. Near-full wakeup/progress, backpressure and completion are
external prerequisites. This core supplies no wait, doorbell, allocator, PTE/UAT
operation, MMIO, transport or readiness transition. SUBMITTED means callback
acceptance, not firmware receipt, mapping consumption or hardware completion.

The new intake correctly binds the prior31U report's exact integer source/test/
C counts and source-manifest digest, then derives prior totals. Mutation cases
refuse wrong counts, bool substitutions and wrong digest. This closes the
previously permissive prior-result check in the new runner only; frozen older
runners and evidence are unchanged. It does not authenticate arbitrary child
reports outside the pinned local execution chain or prove native behavior.

## Research interpretation and remaining prerequisites

M1 reviewed behavioral metadata without Apple images/pseudocode, private
evaluators or member-only material. M5's one CPU query and bounded checks report
189 words (93 new;96 overlapping). The shared pre-entry helper processes the
same1,024-byte command-line span from both callers. The BootArgs revision3
layout comparison identifies that span, not a historical live revision or monitor
activation. Common final forwarding carries entry/context/mode to a boot-CPU
handoff; it is not CPU1 reset evidence. The previously refused31K caller remains
refused as a whole. A superseded query removed before launch is neither executed
coverage nor a new refusal. Historical selection/effective CPU1 state remain
unknown; no new release prerequisite or read/write observer is qualified.

The upstream audit locates a concrete public-source boundary: Aura excludes the
x1n1-derived native Mach-O/SPTM boot-object work from its located public release.
A RAM-loadable Mach-O output, guest serialization API or runtime mediation path
cannot substitute for the accepted native host bootstrap. Applicable WFE changes
act after secondary arrival; special startup mechanisms guarded for other SoCs
do not qualify T6050. The attributed all-core guest remains a useful lead, not a
source-to-artifact-to-physical-entry chain established here. M1 did not refetch
external sources or independently reproduce that result. No raw-start fix or
Apple-only impossibility is established.

M5's six GPU queries report1,351 independently checked words. Two new whole-
function decompilations cross their checked bounds and remain explicitly
rejected (three outside P-code operations total). Bounded instruction/synthetic
facts are a separate evidence basis, not an override of those refusals. Other
removed-block warnings and earlier31Q/31R cross-boundary,31T allocation and31U
dispatcher truncation refusals remain intact. No P-code truncation is reported
for31V; that does not imply complete semantics or runtime equivalence.

The mapping notification is24 bytes, distinct from the72-byte receive ring and
Asahi's20-byte firmware-control message despite similar control offsets. Static
conversion/commit/TLBI call names, deferred construction, queue publication,
firmware consumption and hardware completion are separate facts. Carrier identity
was not independently matched to the running kernel. **Role/address domains
UNQUALIFIED; firmware ABI and G17C UAT UNKNOWN.** Actual mapping/conversion,
cache visibility, native progress and observable bounded completion remain needed.

**REA/private decoding/evaluators, actual private firmware parsing, full symbols,
upstream builds, external refetch, Linux sanitizers, VM execution and live
version/policy checks: NOT RUN on M1.** No private input downloaded/transferred.
Earlier31O closure/network qualifications remain preserved via31P's correction.
No native GPU/SMP, performance or energy improvement is measured by this pass.

## Integrity, preservation and decision

492-file source manifest SHA-256:
`7b2cd432821583a351effd58eb53eb11eafc621c91a31fdab4579669c91e53cd`.
All15 earlier frozen closures U475/T458/S441/R420/Q402/P379/O348/N330/M306/L281/
K254/J226/I202/H186/host6 and every listed hash independently PASS unchanged.
All13 retained package hashes/sizes match the prior receipt. Boot021 SHA-256:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Client clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, Git-checked without
import/execution. Installed boot021 and retained boot042 unchanged.

Before/after hashes match for384 evidence files directly under earlier attempt31
intake directories. No consumed receipt cleared, renamed, overwritten, forced or
reused; no31V native-use file created. Private logs/bookkeeping remain ignored
under `build/native-intake/attempt31v-offline/`. Owned bounded caffeine assertion
has exited; sleep settings unchanged.

**New discovery queries0 / device opens0 / target requests0 / native invocations0.**
Neither Mac restarted. No USB connection, transfer, installation, Recovery,
volume/security/policy/default/firmware change. Original Full/lab Permissive/
Macintosh HD default remain last reported, not freshly checked.

Publish and wait. **Native31V HOLD / NOT RUN; no boot readiness grant.** M5 owns
the actual accepted host-bootstrap/physical-entry provenance and version-bound
G17C mapping/progress/publication/completion contract. A physical test needs a
new meaningful discriminator and bounded independent review. No automatic retry,
restart, firmware replay or image-classification substitution follows.

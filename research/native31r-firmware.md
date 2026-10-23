# 31R: range-service ownership and a handoff adjacency correction

2026-10-23. **Bounded offline findings; native31R HOLD / NOT RUN.** M1's31Q
review passed402 pins,167 Python methods and39 portable C groups. CPU1 execution
remains unverified. This pass changes no installed image, controller, boot policy,
firmware, macOS file or consumed native receipt.

The new result is a narrower ownership boundary: the range wrappers enter a
supervisor-call service, while their apparent ordinary callees are failure
reporting and software-state accessors. The immediately following six-descriptor
finalizer is not evidence of six CPU clusters or a missing secondary release.
One of its descriptor bases lies inside the retained ISP resource window. These
corrections remove misleading paths from the CPU investigation; they do not
establish CPU1's first fetch or a startup fix.

## Successful range setup crosses a service boundary

31Q established the inferred raw path's48KiB fallback allocation and three16KiB
views, separately from entry-vector selection. Its historical applicability is
still inferred: the installed historical metadata was not captured. This pass
continues from the same generic J716c input and analysis mapping.

**Confirmed bounded static:** seven checked wrappers from `0x100c1ada92c`
through `0x100c1adaaac` cross two supervisor-call service classes. Three wrappers
use service number12 and four use17. Their local successful paths return before
the failure-reporting path. They do not directly perform non-stack memory stores
in these checked bodies. The service numbers describe the retained firmware's
interface; they are not a Linux ABI or instructions to invoke these services.

The ordinary call edge through `0x100c1b3f5a8` and queried wrapper
`0x100c1b3f5cc` belongs to failure reporting. The queried `0x100c1b40230` is a
read-only accessor of software state at analysis global `0x100c1f2cb60`.
Neither supplies the successful range-service owner. The original private query
labels were selected before this distinction was established; the validation
record preserves them alongside their corrected roles.

**Unknown:** the actual dispatcher, executing privilege context, ownership
transition and protection semantics behind these services. A supervisor call
alone does not establish which boot component owns the handler. It also does
not show that Linux must repeat the operation. No protected call, replay,
protection change or firmware alteration follows from this observation.

## The next handoff call is not a CPU topology count

The handoff calls range preparation at `0x100c1ae5ba4`, then the function at
`0x100c1aec428` through `0x100c1ae5ba8`. These precede the previously checked
entry-vector operation at `0x100c1ae5c60`. Order alone does not make the next
function a CPU release prerequisite.

**Confirmed static:** the following function uses a bounded table of six
40-byte descriptors at `0x100c1e35fc0`. Its address lookup at `0x100c1aec3d4`
checks the descriptor index and computed table bounds; its table helper is at
`0x100c1aec52c`. Eligibility also depends on other software predicates, including
`0x100c1af6d28`, whose full meaning is not established here. The finalizer has
conditional writes after descriptor selection. Their hardware meaning and the
native conditions are unqualified; this finding is not a register recipe.

**Confirmed cross-artifact containment:** descriptor index2 supplies analysis
base `0x380020000`, inside the existing sanitized ADT's `/arm-io/isp0` resource
window beginning `0x380000000`, size `0x3ff0000`. This is structural containment
between retained artifacts. It neither proves the finalizer ran nor assigns all
six descriptors to a particular peripheral class. It does establish that counting
these descriptors as CPU clusters has no evidentiary basis. The other five
resource roles remain unassigned in this checkpoint.

An early private batch label called this lookup a per-cluster finalizer. That
was a search hypothesis, now rejected as a supported interpretation. No public
CPU topology or native write was derived from it.

## Evidence and limits

The unchanged generic decoded input SHA-256 is
`b4822fc8902c3693ee590c544011603423a75291edd60afd31210d068a4ca120`;
the analysis ELF SHA-256 is
`f89169923c17be829c6b31c3c04c5695d06d42a42cea7390f61214202400dcee`.
The analysis base `0x100c1aa4000` is not a measured runtime address.

Independent Apple LLVM21/original/analysis-ELF comparison covers **853 instruction
words /3,412 bytes in14 disjoint blocks**, with zero mismatches. Of those,156 words
are new relative to31Q and697 overlap it. The four dossiers contain94 instruction
addresses and88 P-code operations; none reports P-code truncation, body escape or
removed-block warnings. These dossier counts overlap the independently checked
words and must not be summed. A separate bounded arithmetic check covers12
synthetic descriptor-lookup inputs; it does not execute a firmware branch.

The [validation record](../reverse-engineering/findings/cpu-startup31r/validation.json)
records four completed REA queries, their exact returned bodies and provider
limits, fresh LLVM/original/ELF comparisons, overlap with31Q, the table-data hash,
and the sanitized ADT hash. Two separate bounded VM batches preserve their own
loopback-only checks and query outcomes. All proprietary bytes, disassembly and
pseudocode remain under ignored local build storage. Successful query completion
and matching words do not establish complete decompiler semantics or execution.

The ordinary error-handler query and read-only accessor query are retained as
negative-applicability evidence. Their initial labels are not promoted into
behavioral facts. Whole-function pseudocode is not accepted as source for an
implementation. Supervisor-call dispatch, predicate meanings, the historical
branch and CPU1's effective first fetch remain unresolved.

## Focused next question

Identify the owner and bounded contract of the successful range services in the
retained generic boot chain, then determine whether that contract covers the
memory containing the independently selected CPU1 entry. The useful distinction
is an ownership or permission requirement that remains unsatisfied at raw handoff,
versus firmware bookkeeping already completed before entry. Establishing the
service's owner and its consumers must precede interpreting it as an omitted
Linux operation.

The [behavioral contract](../reverse-engineering/findings/cpu-startup31r/behavioral-contract.json)
records the separation of fallback ranges, service ownership, the unrelated
descriptor-count hypothesis and entry selection for future original work. It
contains no native operation. A new physical test still requires a concrete
remaining hypothesis and a distinguishing, independently reviewed observation.
This checkpoint supplies no such test and requests no restart.

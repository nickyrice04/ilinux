# 31U — independent M1 offline CPU/GPU review

**OFFLINE_PASS_NATIVE_HOLD, 2026-10-23 Eastern. Native31U HOLD / NOT RUN;
Linux SMP/native GPU acceleration NOT RUN; CPU1 execution UNVERIFIED.**
Neither Mac restarted. Main fast-forwarded cleanly from `99146f7` to
`24cba27be3eaf0b5e046bded6994db5b9d06fe60`, preserving prior work and evidence.
Review follows [the M1 handoff](../../tools/m1n1-client/attempt31u-instructions.md).
[Reviewed metadata](attempt31u-m1-offline-2026-10-23.json) accompanies this note.

## Independent execution

The documented isolated-Python command with retained boot021 content inside
boot042 exited **0 in 7.912 seconds**. **475 pins /225 Python methods /95 portable
C groups PASS**, with no skips, source repairs or installs. Actual M1 tools:
**Python 3.13.5; Apple clang 17.0.0 (clang-1700.3.19.1)**.

| Coverage | PASS |
|---|---:|
| Repeated31T Python review | 216 methods |
| New intake/source/refusal checks | 9 methods |
| Python total | 225 methods |
| Repeated descriptor/planner/GPTBAT/lifecycle/bootstrap/leases C | 88 groups |
| New ring consumer C | 7 groups |
| Portable C total | 95 groups |

C used `-std=c11 -Wall -Wextra -Werror -pedantic -O2` and exact success tokens.
The new ring suite covers all1,785 consumer/producer pairs for capacities1–17,
full raw-byte preservation, arbitrary-capacity wrapping, type/mask refusals,
copy/publication failures, opaque statuses, reentrant callbacks, wide offsets
and copy failure after a prior success. It does not model real concurrency,
cache visibility, DMA ordering or every firmware event type. All callbacks are
local fixtures. Compiler temporaries for all seven C components were confined
to ignored build storage and removed.

Full review output is byte-identical to released host, curated-host and VM output:
`3f5aba9fcc965b797bfde72887ad6894301f9831351414552ee2974d4cd2c155`.
**Linux ASan/UBSan NOT RUN on M1.** VM081's sanitizer result for the new seven
groups is separate M5 evidence; its prior88 groups were repeated portably, not
re-sanitized. Matching JSON does not reproduce private REA or VM execution.

## Independent implementation review

Read the handoff, runner/tests, ring header/C/tests/README, all three research
notes and CPU/GPU/integration validation metadata. **No actionable issue found
within the documented offline contract.** Production and test sources unchanged.

Begin validates nonzero32-bit capacity, both indices, callbacks and the entire
mapped extent before mutation. The multiplication is widened before computing
capacity times72. A captured producer remains fixed for the batch; equal indices
mean empty, including capacity1, rather than full. Each next call processes at
most one record; the caller decides how many calls to make. Representable large
capacities are arithmetic coverage, not a qualified native profile.

Copy uses a private initialized72-byte buffer, publishes no consumer update on
copy failure, and retains the complete successful copy. Type admission explicitly
decodes little-endian32 bits and rejects values at/above64 before shifting, so
oversized types cannot alias a lower mask bit. A zero allow-mask is valid policy
that refuses every record. Type refusal retains the raw copy without publishing.
Wraparound uses the explicit capacity, avoiding a power-of-two assumption and
32-bit overflow at maximum capacity under the untampered-state precondition.

Publication is attempted only after copying and validating the type. It sets
receipt flags and passes the proposed index once to the injected callback. On
callback acceptance, local consumer advances; opaque nonzero status does not
negate explicit acceptance. Refusal leaves local consumer unchanged and retains
raw data, proposed index/status and PUBLICATION_UNKNOWN. This is uncertainty
about external effects, not proof that no store happened. It is terminal: no
retry, reset or reuse is allowed. A new object must not bypass reconciliation.

BUSY refuses reentrant operations. Caller still owns serialization, stable
unmodified state, non-overlapping inputs, acquired indices, coherent complete
records, sole-consumer ownership, producer non-overwrite rules and lifetime.
Callbacks must be bounded, truthful and normally returning. The component cannot
check real mapping or publication order: the publication adapter must implement
platform-qualified record-read-before-index-store synchronization. A C11 fence
is not a qualified DMA substitute. Fields with record_valid/publication_attempted
false can retain earlier bytes/status and must not be read as a new receipt.

This is the checked72-byte variant, not Asahi's56-byte EventMsg ABI. There are no
event labels, acknowledgment decoder, native mapping/device adapter, MMIO,
firmware submission or readiness transition. Admission and index publication
are not firmware boot completion. Original policies are stricter than the
observed variable-shift behavior and do not claim binary equivalence.

## Research interpretation and remaining blockers

M1 reviewed published behavioral metadata, not private Apple images/pseudocode,
private evaluators or member-only content. M5's two CPU queries report254 checked
words (165 new,89 overlapping prior ranges). They distinguish fallback ranges
from the SPTM-named optional-object context before common handoff. Historical
accepted descriptor selection, actual monitor residency, effective CPU1 state
and first fetch remain unknown. A static record name and different entry source
cannot establish that the historical boot selected or completed that path.
The CPU layout query's removed-block output remains refused for whole-function
semantics; earlier producer omissions/truncation remain unresolved.

The upstream note preserves a new positive lead: attributed18-CPU Linux guest
operation under a resident-SPTM x1n1 host on a different board/firmware. This is
worth investigating as an alternative architecture. Its guest count is not
public physical-entry evidence, and the located material lacks the exact host
bootstrap/accepted payload needed to reproduce it here. No ready-to-use raw-
startup correction or Apple-only impossibility is established. M1 did not
refetch external sources or independently verify the reported runtime result.

M5's four GPU queries report1,750 independently checked words. The event-drain
listing is incomplete (1,402 of1,418 bounded words) and its high P-code truncates
with omitted operation/edges; no whole-dispatcher event/role/readiness claim is
accepted. All manual-review gates and earlier31Q/31R cross-boundary and31T
allocation-truncation refusals remain intact. A bounded index-store barrier does
not qualify snapshot acquisition, mapping/UAT/cache publication or completion.
Private sequential evaluators remain separate from this M1 software execution.

The Vinix72-byte comparison and Asahi captured-producer algorithm have different
firmware/record-width/type policies. Matching stride is not ABI compatibility;
no type constant or event meaning is imported. The retained carrier was not
independently matched to the running kernel. **Role/address domains UNQUALIFIED;
firmware ABI and G17C UAT UNKNOWN.** Actual versioned ring mapping, synchronization,
role binding and bounded request/event completion remain prerequisites.

**REA/private decoding/evaluators, actual private firmware parsing, full symbols,
upstream compilation, external refetch, Linux sanitizers, VM execution and live
version/policy checks: NOT RUN on M1.** No image/private input was downloaded or
transferred. Prior31O's closure/network qualifications remain preserved via31P.
No performance/energy, native GPU or SMP improvement is established here.

## Integrity and preservation

475-file manifest SHA-256:
`3cd55cf11ea37d2af3712508da53a2ad9051d8011fa99024741dd8e5e78adf25`.
All14 earlier frozen closures T458/S441/R420/Q402/P379/O348/N330/M306/L281/K254/
J226/I202/H186/host6 and every listed hash independently PASS unchanged.
All13 retained package hashes/sizes match the earlier receipt. Boot021 SHA-256:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Client clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, checked via Git only;
no client import/execution. Installed boot021 and retained boot042 unchanged.

Before/after hashes match for375 evidence files directly under earlier attempt31
intake directories. No consumed receipt cleared, renamed, overwritten, forced or
reused; no31U native-use file created. Private logs/bookkeeping remain ignored
under `build/native-intake/attempt31u-offline/`. Owned bounded caffeine assertion
has exited; sleep settings unchanged.

**New discovery queries0 / device opens0 / target requests0 / native invocations0.**
Neither Mac restarted. No USB connection, image transfer, installation, Recovery,
volume/security/policy/default/firmware change. Original Full/lab Permissive/
Macintosh HD default remain last reported, not freshly checked.

Publish and wait. **Native31U HOLD / NOT RUN; no boot readiness grant.** M5 owns
the alternate host-bootstrap provenance and local effective-entry evidence,
plus version-bound G17C ring mapping/acquisition/publication/completion. A new
physical experiment requires its own meaningful discriminator and reviewed,
bounded implementation. No automatic restart, retry or firmware replay follows.

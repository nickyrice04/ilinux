# 31AA — independent M1 research-supplement review

**OFFLINE_PASS_NATIVE_HOLD, 2026-10-25 Eastern. Native checks NOT RUN.**
Reviewed main `5ef577833ee6d544f7cf1769a0afc272f6650f14`, pulled by fast-forward
with existing evidence preserved. Read both31AA research notes, the CPU findings,
supplement validation and original planner/public contract. The original31AA
instructions describe an earlier unpublished-REA checkpoint; this supplement
explicitly supersedes that historical statement without changing frozen files.
[Reviewed metadata](attempt31aa-research-m1-offline-2026-10-25.json).

## Manifest and reused review

All **24 supplement pins PASS**, documented checksum command exit 0 in 0.020 s.
Manifest SHA-256:
`fc4e0ec2c1e003d546cbe8e6741e6b711a4163a23de1f095844909b3a99f7a68`.
The original planner manifest remains 14 entries,
`7260ea2e2966809622ed32437e35324eac25bacc9e6d2049e67834236a1e3252`.
The two manifests overlap; their counts are not distinct-file totals.

No completed exact-source M1 planner review was present. The
[planner review](attempt31aa-m1-offline-2026-10-25.md) was therefore completed once
in this handoff and is **reused here**, with no second execution. All 11 groups
passed optimized and with macOS ASan/UBSan, plus AArch64 compile/symbol inspection.
The exact12-file binding matches both published host and Linux VM:
`dc9177156a783fc08a74a54926f7c00f3e3788a68badca9f5d039f2534f2b87e`.
The pinned18-CPU fixture was checked against ADT source order and values separately.
Existing exact-source31Z review was reused; older executable suites were not repeated.
The planner report owns actual tools, timings, object hash and runtime dependencies.

## Research assessment and limits

**No actionable blocker found within the supplement's bounded research scope.**
The following are reviewed **M5 evidence**, not private-binary findings reproduced
on M1. The report distinguishes recorded behavior, public comparisons and design
inferences, and does not claim a deployed monitor bridge.

- Two REA queries completed; the helper's103-instruction body has bounded evidence,
  while the image helper's363-instruction whole-function pseudocode remains refused
  for cross-boundary/removed-block output. Whole-function pseudocode accepted: zero.
  The earlier prelaunch sandbox refusal involved no guest query and is retained
  separately, not counted as a third request or hidden as a successful run.
- Reported independent checks cover551 words/2204 bytes across seven ranges, zero
  mismatches;14 words are reverified31Z dependencies and queried bodies total466.
  Carrier byte equality and these checks do not repair the decompilation refusal,
  recover omitted context or prove runtime behavior of unexamined callees.
- The helper initializer is qualified as a local utility, with version-scoped
  fields ending at224 and no monitor activation. Actual incoming version and
  referenced objects' validity/lifetime remain unknown. A host may omit unused
  services; any service it consumes still requires qualified fields and objects.
- The independently checked no-chain edge supports investigating an original early
  image with genuinely no runtime chained relocation/PAC dependencies. Deleting
  the load command alone proves no such property. Image placement/metadata and the
  vector/synchronization/fixups-completion boundary remain separate requirements.
- Fixed bootstrap dispatch is distinct from optional XNU helper initialization and
  thread/preemption hooks. Encoding agreement does not qualify register clobbers,
  permitted guarded/interrupt state, an arbitrary wrapper or exception continuation.
  The void APIs do not furnish a portable numeric success result.

The earlier blanket requirement to decode the **entire848-byte record** is narrowed:
qualify the actual fields/services consumed by the original host, retain unused
fields opaque, and preserve all owned memory and referenced objects. This supersedes
that overbroad gate in earlier31Z review prose without rewriting historical reports.
It does not qualify an accepted host image, resident monitor or secondary execution.
Neither an implemented CPU workaround nor Apple-only necessity is established.

M5's SDK/public comparison reports ten successful fetches out of twelve attempts,
two404s, seven reused31Z bindings and one constant-only translation unit emitting
zero functions. These remain upstream evidence; no independent retrieval or SDK
compilation occurred on M1. Likewise REA, local Apple instruction decoding and
Linux VM/sanitizer checks were **NOT RUN on M1**. No Apple bytes, pseudocode, SDK
source, live monitor records or raw analysis output enter these reports.

## Remaining integration and preservation

CPU software research remains active. Next qualify actual early image placement
and references, entry level/guarded/interrupt state, readable argument lifetimes,
owned mapped stacks/vectors, live memory reservations, dispatch preservation and
own monitored exception-return paths. Registration still needs a resident monitor,
correct boot-first phase and actual supported CPU identities. Physical-secondary
entry/release observation is a later gate. A plan or parser match cannot supply it.
No native wrapper, controller, accepted image or meaningful physical test is ready.

All **21 preserved manifests/5770 listed-file checks**, the frozen31AA source,
retained13-file boot042 package, clean client `57a9339` and **510 prior intake files**
verify unchanged. The latter count is recursive and includes consumed receipts.
No receipt was cleared/reused. Detailed preservation metadata is in the JSON;
raw local logs stay ignored. No new native-use file, target query or device open.

**Neither Mac restarted. Native startup, live target-version checks, physical-
secondary observation, SMP, GPU and performance checks remain NOT RUN.** No monitor
call, installation, installed-object, policy/security, volume, firmware or default-
startup change, and no external outreach. Installed boot021 and client pin stay
unchanged; no routine policy recheck was performed or requested.

# 31Y — independent M1 format, CPU2-plan and read-only inspector review

**OFFLINE_PASS_NATIVE_HOLD, 2026-10-24 Eastern. Native31Y HOLD / NOT RUN.**
Pulled main cleanly from `9befeb3` through
`0f382bb74c2c0783a53cb8a41d1a900d9a6c82e8`. No prior work discarded.
[Reviewed metadata and normalized20-case results](attempt31y-m1-offline-2026-10-24.json).
The separate [31W](attempt31w-m1-offline-2026-10-24.md) and
[31X](attempt31x-m1-offline-2026-10-24.md) reports retain their own scope.

## Tests and tool identity

All18 current31Y manifest entries pass the documented shasum command, exit0:
`52f50dc70dc4605cf8cc0fcf320c26bb3d7997aa2566ab247542000f9844a3a9`.
Actual Python3.13.5; existing Apple clang17.0.0 (clang-1700.3.19.1) used only for
31W. No tools installed or tests repaired; no skipped tests.

| Independent M1 execution | Result |
|---|---|
|31Y format suite|14 methods PASS, exit0,0.078s|
|31Y CPU2 suite|9 methods PASS, exit0,0.132s|
|31Y public-input plan|OFFLINE_CPU2_BINDINGS_PASS, exit0,0.072s|
|31Y generation only|20 NOT_INSPECTED fixtures, hashes match reference, exit0|
|31Y explicit read-only local inspection|20 cases, completed_matrix=true, matches_reference=true, exit0,3.159s|
|Separate outstanding31W regression|509 pins/243 Python methods/111 portable C groups PASS, exit0,9.555s|

Across these labeled executable suites, **266 Python methods and111 portable C
groups passed**. The23 new methods are not counted as31X firmware validation.
The generated and inspected fixture sets use different fresh ignored directories;
every fixture hash and non-executable permission was checked. Generated-only
files remain NOT_INSPECTED; the second set owns the Apple-tool results.

The **actual M1 inspector environment is macOS26.0.1 /25A362**, with kmutil SHA-256:
`777d9def067162eb5bd107d6dc1e42d1b5e08530439a041ec450c6322081a458`.
The M5 reference environment is26.6.2/25G83 with another tool hash; those identities
are not interchangeable. Nevertheless the M1's **entire normalized20-case
signature matches**: stages, cases, fixture sizes/hashes, exits, classifications,
all derived properties and diagnostics. This was independently compared again
against the frozen reference, not merely its aggregate counts.

| Class | Cases | Actual process exit |
|---|---:|---:|
|Collection-loading errors|6|71|
|Property derivation errors|9|0|
|Properties derived|5|0|

Reference SHA-256:
`821945f643248e10c720904814bb8e9752d0233ca9bdd43cd9ff978e45738f48`.
The two boot-segment fixtures reproduce nonzero kcbz32768/kcbf32768; the three
ordinary successful fixtures have kcbz0. There was no timeout, signal, environment
refusal or retry on M1. Raw stdout/stderr, fixture files and local paths remain
ignored. Only original-fixture classifications/properties/hashes are published.

This establishes parser agreement for these20 cases across two local tool builds.
It does not establish configure-boot acceptance, iBoot/SPTM execution, a complete
validator specification, monitor memory requirements, historical image identity,
physical CPU entry or a working bootstrap. No fixture was executed or installed;
inspect used explicit synthetic and nonexistent workspace collection paths only.
No sudo, configure-boot, system collection or personalized object was involved.

## Independent code and contract review

Read generator/classifier/tests/reference, CPU2 planner/tests/README, all three31Y
research notes and linked validation limits. **No actionable blocker found within
the documented offline scope.** Original fixtures have bounded headers/segments,
synthetic empty metadata, original branch-to-self markers and no Apple program
bytes. Output must be a fresh directory beneath ignored build; fixture mode is0600.
Only an explicit inspect option invokes the fixed read-only inspector command.

The classifier requires a full nonduplicated14-property success block, correct
integer bounds and known output envelope. Exit-zero property errors remain errors.
Unknown output changes the full reference signature; unexpected warnings are not
silently discarded as success. A timeout/signal stops the matrix and is not a
format rejection. Diagnostic signatures strip path/fixture-ID banners; whole
stdout/stderr is retained privately. Classifying a rejection is not reproducing
all installer/analyzer semantics. M5's extra80 mutation checks remain its separate
review evidence; the14 portable methods and real20-case matrix ran here.

The CPU2 planner hashes five public inputs and derives the actual same-M0 row2
rather than reusing CPU1's records. It derives reset/spin/info strides, dedicated
stack and target values, excludes row2 from zero/fresh scans while covering row1
and rows3–31, and preserves a separate CPU0 invariant. Expected MPIDR0x40002 is
explicitly inferred. The original paired-store leaf would need rebuilding for
value4; no such leaf is produced or run by this plan. Normal/Device identity
field offsets remain distinct. The optional retained-source/image mode was
NOT RUN; ordinary public-input plan is bound to the published layout audit.
General retained-package integrity was checked separately below.

Plan output has target_cpu2, controller_present=false, deployment_ready=false,
hardware_operations0 and required_live_preflight=NOT SATISFIED. Fresh CPU2 guards,
owned RAM/stack/mappings, observations, classifications, source closure and durable
one-use controller are still required. A successful offline plan predicts neither
CPU2 execution nor Linux SMP. A second all-zero result would remain ambiguous.

## Research boundaries and remaining implementation work

M5's139-word retained-tool comparison and one REA query are separate evidence,
not reproduced on M1. Caller-selected property serialization does not prove the
indirect binding of inspect and configure-boot. Earlier refusals remain intact.
The public XNU comparison identifies reason/two-pointer arguments and memory,
fixups, exception and monitor-library lifecycle obligations from an already
running SPTM. Aura's ordinary raw argument consumer is not that adapter. The
complete matching T6050/25G83 argument/header/version remains unqualified.
A register shuffle, parser success or nonzero property cannot substitute for it.
Original offline adapter research can continue without the unpublished host;
no working software correction or Apple-only necessity has been established.

REA, private Apple decoding/instruction checks/evaluators, full symbols, external
source refetch/upstream builds, Linux sanitizers, VM execution and live target/
policy checks **NOT RUN on M1**. The read-only local inspector above did run and
is distinguished from those omissions. No external message was sent; the user's
no-outreach instruction supersedes the frozen31X draft. Native CPU/GPU and
performance/energy improvements remain NOT RUN / UNMEASURED.

## Preservation and disposition

All18 earlier frozen manifests and every listed source hash independently pass,
including31W509 and31X6; current31Y18 pins pass before/after. All13 retained boot042
package sizes/hashes match the earlier receipt. Its boot021 image SHA-256 remains
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Client clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, checked via Git without
import/execution. Installed objects and known working boot unchanged.

Before/after hashes match for393 evidence files directly under prior attempt31
intake directories. No consumed receipt cleared, renamed, overwritten, forced or
reused. No31W/X/Y native-use receipt created. Raw logs/new fixtures and preservation
bookkeeping remain under ignored build/native-intake/attempt31y-offline. Compiler
temporaries removed; owned bounded caffeine assertion ended; sleep settings intact.

**New discovery queries0/device opens0/target requests0/native invocations0.**
Neither Mac restarted. No USB, transfer, installation, Recovery, firmware, volume,
policy/security/default change. Original Full/lab Permissive/Macintosh HD default
remain last reported, not freshly checked. Publish and wait. **Native31W/X/Y HOLD /
NOT RUN; no boot readiness grant.** Next qualify the version-matched monitor-to-OS
entry/memory/fixups contract; CPU2 remains a separately controlled offline plan.

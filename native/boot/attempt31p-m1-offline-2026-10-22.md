# 31P — independent M1 offline CPU/GPU review

**OFFLINE_PASS_NATIVE_HOLD, 2026-10-22 Eastern. Native31P HOLD / NOT RUN;
native GPU acceleration and Linux SMP NOT RUN; CPU1 execution UNVERIFIED.**
No live test is released. Neither Mac restarted and no target operation occurred.
Main fast-forwarded cleanly from `1ac4f62` to
`311473c355a0cdf4c378d12d016dd08d6dab436b`; no local change discarded.
Reviewed [M1 metadata JSON](attempt31p-m1-offline-2026-10-22.json) accompanies this note.

## Independent execution

The documented `python3 -I tools/m1n1-client/attempt31p-offline.py --image ...`
command exited **0**, **379 pins /122 Python methods /12 C groups PASS**,
no skips or repairs. Elapsed4.064s. M1 used **Python3.13.5 and Apple clang17.0.0
(clang-1700.3.19.1)**, separately from M5's recorded Python3.9.6/clang21 environment.

| Coverage | Methods/groups PASS |
|---|---:|
| Previous31O image-only review | 63 Python methods |
| GPU descriptor/retained-ADT contract | 38 Python methods |
| Package-space helper, synthetic inputs | 7 Python methods |
| Toolchain-isolation helper, synthetic inputs | 6 Python methods |
| New intake/source safety | 8 Python methods |
| Python total | 122 methods |
| Original portable C codec | 12 groups |

C compiled as C11 with `-Wall -Wextra -Werror -pedantic -O2`; assertions remained
enabled. The exact success token `GPU31P_SEGMENTS_PASS` was required. Only original
pinned C was compiled/run. Temporary compiler output stayed below ignored build
and was removed; no codec temporary directory remains. **Linux ASan/UBSan NOT RUN
on M1**; the portable test does not reproduce M5's sanitizer validation.

M1's full review output is byte-identical to the released host, curated-host and
VM output: SHA-256
`ec98fa7d5968e7d905716f9f70893832b84b196fd985429b9856e20750308250`.
The ADT contract result also equals `kernel/experiments/gpu31p/adt-validation.json`.

## Retained GPU metadata result

**STRUCTURAL_PASS, J716C_T6050_DUAL_ASC**:644 indexed paths,9 contract nodes,
GFX and GFX1 roles,2 segments/64 descriptor bytes per role. Both parent/nub
descriptor sets agree. Each role's first-address fields need **41 bits**;
both high descriptor words are nonzero and preserved. The opaque last words
survive unchanged. The profile requires16KiB alignment, without asserting a GPU
page-table ABI. Three cross-role IOVA overlaps are reported rather than rejected
as a single shared address space. Mapper/AIC/resource checks pass.

Sanitized ADT SHA-256:
`6f143434d2f05310067559f8fa3836ae564dd9934ebc5912660f2a9f5a8a73af`.
Descriptor-pair hashes:
GFX `d7619805c5c69587fbe839da3923b2f200d60f63c78aac35aa78eb85de25fdd8`;
GFX1 `e39089b7f7c41db977595bf50089e0c7ce735c647cb8622dfa8663fcbff791ad`.
These identify retained sanitized metadata, not firmware images or live probes.

**descriptor_cpu_address_domain=UNQUALIFIED, UAT layout/firmware ABI UNKNOWN,
GPU enablement HOLD, native validation NOT_RUN.** Property presence is not a
page-table value or readiness measurement. Generated CPU reservations0/MMIO
writes0/hardware operations0. This does not establish either controller's
firmware role, GPU initialization, compute, rendering or performance.

## Independent code review and limits

Reviewed the offline runner, Python contract, C API/implementation and synthetic
tests, helper tests, release validation and four research records. No code-level
blocker was found for the documented offline scope. No production or test source
was modified on M1.

The codec preserves three64-bit address fields, a32-bit size and opaque32-bit
word. Counts, capacities, additions, alignment and within-role overlaps are
bounded; conservative end-exclusive overflow is refused. C decode validates a
bounded scratch array before copying output. Error paths preserve outputs under
the documented caller requirements: accessible capacities and non-aliasing
buffers/arrays. Neither C nor Python derives CPU physical addresses, reservations,
UAT entries, queues, firmware messages or hardware writes.

The retained-ADT profile validates exact identity/resources and role-local ranges,
without treating cross-role IOVA overlap or aggregate MMIO containment as a bug.
Contract-path/handle uniqueness, parent/nub agreement and full-width descriptor
round trips are checked. The bounded regular-file CLI rejects malformed JSON,
duplicate keys, nonfinite numbers, symlinks/special files and unsafe input shapes;
its outputs contain fixed labels, counts, booleans and hashes. No live option,
discovery, USB open or client import exists in this intake.

The helper suites exercised original pure functions with synthetic package,
signature-status and archive-member records. They did not verify real signatures,
extract/install packages, access a host keyring or execute downloaded build code.
The existing C compiler was used; no host tools were installed.

## Environment and earlier-closure corrections

Read and retain `research/native31p-environment.md` as the superseding correction.
The earlier31O M1 full-checkout pass checked its348 listed pins; it did **not**
establish completeness of its executable dependency closure. The old runner
invoked the unchanged `entry_contract.py` outside that list. 31P explicitly pins
that dependency in its379-file closure. The frozen31O files/results are unchanged;
prior full-checkout success is not relabeled as a passing minimal-tree test.

The earlier M5 VM31O `network:false` statement was inaccurate: its wrapper
inherited NAT. Job intent did not prove network isolation and no packet capture
establishes absence of traffic. This supersedes that historical environment claim.
M1 did not run a VM in either review. M5's final31P loopback-only/no-network checks
and curated-tree validation remain separate documented evidence, not newly measured
by M1. No VM or private firmware was accessed here.

## Separate M5 results not reproduced

**Upstream Mesa build/396 gtests, upstream kernel object, Linux sanitizer runs,
REA/private firmware parsing and full image symbols: NOT RUN on M1.** The kernel
object was separately skipped by M5 pending a qualified Rust/LLVM pairing.
The63-method inherited review uses no symbols or private iBootData; its original
report consistency and image-only contracts remain distinct from firmware semantics.

M1 reviewed M5's findings as supplied, without refetching external sources or
opening Apple pseudocode. Image/object preparation is not a demonstrated new CPU
release action; actual raw-image metadata/branch provenance remains unresolved.
CPU1/all-core entry, G17C ABI/address translation and native acceleration need
separate evidence. A public compiler build or M4/base-M5 result is not T6050/G17C
hardware qualification or a measurement of application responsiveness/energy.

## Preservation and decision

379-file manifest SHA-256:
`5d022acf0f8002ca2d73c2ddb98ab2dadc4c753847d2e4073c7e32a6ba0bf84c`.
Frozen O348/N330/M306/L281/K254/J226/I202/H186/host6 independently verified unchanged.
Retained boot021 image SHA-256:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
All13 retained-package file hashes/sizes match the prior verified receipt. Client
remains clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, checked using Git
only; no client module imported/executed.

Before/after digests of all prior attempt31 receipts/offline evidence match.
No consumed file cleared, renamed, forced or overwritten; no31P native-use file
created. Private outputs and bookkeeping remain ignored under
`build/native-intake/attempt31p-offline/`; Git receives reviewed metadata/original
notes only. Bounded owned caffeine assertion handled; no sleep setting changed.

**New discovery queries0/device opens0/target requests0/native invocations0.**
Neither Mac restarted. No install, transfer, Recovery, policy/live-version check,
VM/REA run, native runner or macOS/volume/security/default/firmware change.
Original Full/lab Permissive/Macintosh HD default remain last reported, not
freshly verified. Installed boot021, retained boot042 and client pin unchanged.

Publish the offline result, then wait. **This is not readiness to boot: native31P
HOLD / NOT RUN; native GPU acceleration/Linux SMP NOT RUN.** M5 owns the next CPU
metadata/prerequisite investigation and G17C address-domain/ABI/UAT/queue work.
A physical handoff needs a new distinguishing question and separately reviewed
operations. No automatic restart, firmware replay, generation alias or consumed-
runner reuse follows. Performance/energy parity remains unverified.

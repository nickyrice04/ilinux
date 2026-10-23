# 31Q — independent M1 offline CPU/GPU review

**OFFLINE_PASS_NATIVE_HOLD, 2026-10-23 Eastern. Native31Q HOLD / NOT RUN;
native GPU acceleration/Linux SMP NOT RUN; CPU1 execution UNVERIFIED.**
Neither Mac restarted and no hardware operation occurred. Main fast-forwarded
cleanly from `5058916` to `1cfe016980270c55ac390032b7fa418f68e3dc98`.
No local change discarded. Reviewed [M1 metadata](attempt31q-m1-offline-2026-10-23.json)
accompanies this original note; compiler diagnostics and private logs remain ignored.

## Independent execution

The documented isolated-Python31Q offline command exited **0** in **5.390s**:
**402 pins /167 Python methods /39 portable C groups PASS**, no skips or repairs.
M1 tools: **Python3.13.5, Apple clang17.0.0 (clang-1700.3.19.1)**. This differs
from M5's recorded development tools and is reported separately.

| Coverage | Methods/groups PASS |
|---|---:|
| Prior31P portable review, including31O | 122 Python methods |
| New planner/GPTBAT reference | 36 Python methods |
| New intake/source/refusal checks | 9 Python methods |
| Python total | 167 methods |
| Prior descriptor codec | 12 C groups |
| New VA planner | 20 C groups |
| New GPTBAT format codec | 7 C groups |
| Portable C total | 39 groups |

Original C compiled as C11 with `-Wall -Wextra -Werror -pedantic -O2`.
The exact component success tokens were required. Tests cover139,392 reduced
page-grid decisions,500 seeded high-VA translation checks,16,383 nonzero format
offset refusals and10,000 seeded format roundtrips. These are synthetic software
cases, not hardware coverage or timing measurements. Only original pinned C
was compiled/executed. Compiler temporary directories stayed in ignored build
and were removed for both new components and the repeated prior codec.

M1's complete review output is byte-identical to the released host, curated-host
and VM output: SHA-256
`a286ec699b1567dc4d8fc9ffaca2e2208d640f00236dd9b80a1006e66728e58c`.
**Linux ASan/UBSan NOT RUN on M1**: M5's new27-group sanitizer run is separate
evidence. The39 portable groups here do not reproduce sanitizer execution.

## Independent implementation review

Read the handoff, runner, C/Python planner and format APIs/implementations,
component tests, validation and all three research records. No code-level blocker
was found for these documented offline APIs. No production/test source was changed.

The planner validates explicit userspace GPU VA windows, a protected kernel
reservation, actual object extents and ordered bind/unbind/repeated-page operations.
It preserves64-bit values; checks addition/subtraction bounds, alignment, flags,
handles, containment and full-page object extent; and preserves duplicate-address
operation order. It neither rounds values nor invents a G17C profile. Its64-op/
64-object limits are local work bounds. Empty operation batches are allowed while
zero spans, invalid reservations and malformed objects are refused.

C validates into bounded scratch storage before publishing output. Failure leaves
output/count untouched under the documented accessible-capacity and non-aliasing
requirements. This is local validation transactionality, **not kernel ioctl
atomicity** or a promise that real mapping will succeed. Object lifetime, locks,
mapping state, synchronization, submission and partial-kernel-failure recovery
remain outside the API. C structs are internal representations, not wire structs.

The GPTBAT codec uses separate page-number/base types and checks lossless
32-meaningful-bit page numbers scaled in16KiB units to an aligned46-bit format.
Width and alignment violations refuse without modifying C output. Zero is a
representable value, not evidence of a valid table or readiness. The inverse
conversion is an original format check, not an observed register-write routine.
There is no automatic conversion from ASC descriptors, CPU physical addresses or
GPU userspace VAs, and no register address or hardware access in this codec.

The runner repeats prior portable checks, uses fixed original component sources
and the existing compiler, requires exact source closure before/after, refuses
missing tools/failed/skipped tests and has no live mode or device interface.
No third-party source/build code or m1n1 client was imported/executed on M1.

## Research boundaries retained

M1 reviewed the supplied behavioral records; it did not refetch external sources,
inspect Apple pseudocode, rerun REA or independently decode private binaries.
M5's CPU2,701-word/GPU489-word instruction findings remain separate static evidence.
The current raw producer's omission of the extra-object selector does not prove
historical installed metadata or the branch actually taken. Fallback memory-range
preparation remains distinct from effective CPU1 entry or a missing release step.

The GPU format claim is bounded to the retained member and independent instruction
checks. Three whole-function `rejected_cross_boundary` refusals remain in force;
completed REA queries do not become admitted whole-function pseudocode. The
retained kernel carrier's match to the running kernel was not independently
established. Provider null-payload success and the Release build-flavor label do
not establish firmware ownership, readiness or numeric ABI.

**Descriptor CPU address domain UNQUALIFIED, G17C UAT layout/firmware ABI UNKNOWN.**
Format width does not qualify CPU physical mapping, a G17C page-table profile,
shared firmware structures or queues. No ioctl, PTE, MMIO write, firmware load,
device-tree change or native implementation is generated. CPU1/all-core execution,
G17C rendering/compute and measured performance/energy parity remain unverified.

**Full symbols, actual private firmware parsing/REA, upstream Mesa/kernel builds
and Linux sanitizer execution: NOT RUN on M1.** Prior396 Mesa gtests and M5's
VM077 results remain prior/separate evidence. No VM, package installation,
firmware transfer or host tool installation was performed for this review.

## Inputs, preservation and decision

402-file source manifest SHA-256:
`7e2a22826e8311532b16b81603b2fbe79bc4556d7893c3142fad92cbc943f0c6`.
Frozen P379/O348/N330/M306/L281/K254/J226/I202/H186/host6 independently PASS unchanged.
Retained boot021 SHA-256:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
All13 retained-package file hashes/sizes match the prior verified receipt.
Client remains clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, checked using
Git only. Installed boot021 and retained boot042 remain unchanged.

Before/after digests of all earlier attempt31 receipts and offline evidence match.
No consumed file cleared, renamed, forced or overwritten. No31Q native-use file
created. Private outputs/bookkeeping remain ignored under
`build/native-intake/attempt31q-offline/`; only reviewed metadata/original notes
are published. Bounded owned caffeine assertion handled; no sleep setting changed.

**New discovery queries0/device opens0/target requests0/native invocations0.**
Neither Mac restarted. No transfer, installation, Recovery, live-version/policy
check, VM/REA run or macOS/volume/security/default/firmware change. Original Full/
lab Permissive/Macintosh HD default remain last reported, not freshly verified.

Publish and wait. **This pass is not boot readiness: native31Q HOLD / NOT RUN;
GPU acceleration and Linux SMP NOT RUN.** M5 owns the next bounded raw-handoff
prerequisite and G17C handoff/address-domain/UAT/queue investigation. A physical
test needs its own distinguishing question, operations, bounds and offline review.
No automatic restart, firmware replay, generation alias or consumed-runner retry.

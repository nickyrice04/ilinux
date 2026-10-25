# 31AA — independent M1 registration-planner review

**OFFLINE_PASS_NATIVE_HOLD, 2026-10-25 Eastern. Native checks NOT RUN.**
Pulled main cleanly with `git pull --ff-only` from `6106a6c` through
`5ef577833ee6d544f7cf1769a0afc272f6650f14`, including planner publication `d2df23b`
and its research supplement. No prior exact-source M1 31AA review/output was found,
so the focused planner checks ran once. Existing 31Z results were reused after
binding verification. [Reviewed metadata](attempt31aa-m1-offline-2026-10-25.json).

## Actual M1 execution

All **14 planner manifest entries PASS**, exit 0 in 0.038 s. Manifest SHA-256:
`7260ea2e2966809622ed32437e35324eac25bacc9e6d2049e67834236a1e3252`.
The documented isolated Python runner with `--sanitize --freestanding` completed
once, exit 0 in **1.467 s**, using fresh ignored output. Actual tools: Python 3.13.5,
Apple clang 17.0.0 (clang-1700.3.19.1), macOS 26.0.1 / 25A362.

| M1 check | Result |
| --- | --- |
| Optimized registration suite | 11 groups PASS |
| ASan + UBSan registration suite | Same 11 groups PASS |
| AArch64 freestanding compile and ELF symbol inspection | PASS |
| Fixture independently compared with pinned sanitized ADT | 18 records PASS |

There are **11 unique C groups**, not 22. Exact success markers and empty test
stderr match the published M5 host/final ARM64 VM receipt. All **12 source bindings**
match the supplement's host record and the VM's binding hash:
`dc9177156a783fc08a74a54926f7c00f3e3788a68badca9f5d039f2534f2b87e`.
Coverage includes 120 order permutations, 56 duplicate cases, all 64 oversized-
affinity positions, failure nonmutation, maximum capacity and frozen31Z composition.
No tests were skipped, repaired or retried. Older suites and the31Y inspector were
not rerun.

The fixture preserves all 18 source records in order, including 12 `M` and 6 `P`
tags as metadata. Its numeric IDs and affinities were independently compared with
the pinned sanitized ADT, separately from the runner. CPU2's ADT affinity is 2,
not diagnostic MPIDR 0x40002. Generated header SHA-256:
`870f0d1150a071a5a81e461bb7c2c829f47070531183d3385b810a6a6a251ca0`.
These are retained observations, not fresh runtime topology or scheduling evidence.

The cross object is independently confirmed ELF64 little-endian AArch64 relocatable,
SHA-256 `b8e559a397fe1c06a344ee1e9182bb0e927de27defb38ecf79d12231fabf3efd`.
Undefined symbols are `memcpy`, `memset`, `sptm31z_get_boot_words`, as also recorded
upstream. The compiler-dependent object hash need not equal M5's. It was neither
linked nor executed; a future host must supply its runtime and entry contract.

## Independent code review

Read both API/implementation, runner, tests, README, public contract and published
validation. **No actionable blocker found in the documented offline contract.**
The planner validates non-null objects and count before reading input rows; uses
frozen31Z's structural cold-role check; validates each full raw affinity before
narrowing; refuses duplicate source IDs and affinities; and requires both boot
identity fields to match row zero. It never sorts or moves the boot CPU. A local
zero-initialized plan is assigned only on success, preserving output on failure.
Owned records retain source IDs/classes and exact order; predicted ordinals remain
separate from source IDs. Count is bounded at 64, making the quadratic uniqueness
scan and ordinal conversion bounded. Valid disjoint objects and serialization
remain explicit caller duties.

A 32-bit width check cannot authenticate an ADT affinity: the deliberate in-range
wrong-MPIDR test correctly demonstrates that limit. The caller still binds the
complete actual supported CPU set and boot identity. The real registration service
is void; this component neither calls it nor invents a success result. There is
no mutable execution cursor, callback, retry loop or hardware-ready state.

The runner verifies seven frozen inputs/dependencies and binds all twelve files,
derives fixture affinities only from ADT `reg`, checks independent topology and
boot-first state, and preserves classes without sorting. It requires new output,
exact markers and unchanged final source hashes. Frozen31Z's hash-verified ELF
reader is imported without creating bytecode caches. Tests execute only original
project code with synthetic/previously public data.

Reused [31Z review](attempt31z-m1-offline-2026-10-24.md), JSON hash
`751aa0100c5c21bcc93892bad420e09de432cfcf824b54484eb591295f35d931`, still matches
all original component bindings. Its executable suites were not repeated.
The [separate research review](attempt31aa-research-m1-offline-2026-10-25.md)
qualifies the newer minimal-dependency scope without editing that frozen evidence.

## Preservation and scope

All 21 preserved manifests, including the existing31AA package, and **5770
listed-file hash checks PASS unchanged**; these are entries, not distinct files.
The separate research manifest's 24 entries also pass. All **510 prior intake
evidence files**, recursively hashed before/after, are unchanged, including consumed
receipts. Retained13-file boot042 package hashes/sizes match. Client remains clean
at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. No new native-use receipt exists.
The temporary compiler directory is empty; the owned bounded caffeinate exited.
Raw logs and generated artifacts remain ignored under `build/31aa-adapter-m1-review/`
and `build/native-intake/attempt31aa-offline/`.

REA, private Apple binary checks, SDK measurements/source retrieval and M5 VM/Linux
sanitizer execution were **NOT RUN on M1**. The macOS ASan/UBSan checks did run.
No native invocation, device open, target query, restart, installation, external
contact or boot/security/volume/default change. Installed boot021 remains unchanged.
Native startup, physical-secondary observation, SMP, GPU and performance checks
remain **NOT RUN**. Original Full/lab Permissive/Macintosh HD default stay last
reported, not newly checked. CPU software research continues; no native test is ready.

# 31AE: reproduce and repair the reported boot-property arithmetic error

2026-10-25 Eastern. **Confirmed for the reported arithmetic error; native
installer/firmware acceptance NOT RUN.**

## What M1 reported

The [31AD result](../native/boot/attempt31ad-recovery-2026-10-25-result.md)
captures the actual Recovery configure failure: subtracting file offset 49152
from 32768, configure 71, capture 0. Those are the released image's
`__DATA_SPTM` and `__TEXT_EXEC` offsets. No diagnostic entry occurred. The human
reported exact boot021 rollback, return to Macintosh HD and restoration of its
default. Final rollback numeric exits were not captured. The initial rollback
authentication error was resolved by entering the requested username first;
no pipe/TTY defect was established.

## Independent offline reproduction

On the M5, Apple's read-only inspector reproduces **the same operands and
arithmetic-error text on the exact released 31AD image**, SHA-256
`406be900521795608073fa9f050f4e5f00b595793c95b0a155e510893cc16309`.
Its process exit is **0**, but its output says boot properties could not be
derived. Therefore the Recovery report's inspector exit 0 never proved complete
property derivation. The previous ordering guard and review were incomplete.

On the corrected 31AE image the same inspector derives **all 14 properties**,
with no property error. Both inputs, stdout/stderr, argv, hashes and exact exits
are retained privately. The frozen original 31Y classifier checks the complete,
nonduplicated key set and rejects exit-0 property errors. This is a parser
comparison, not configure-boot or a firmware boot.

The desktop tool SHA-256 is
`2f435e8f872e75e7edcf0ec108f3360e18b1e4123451032062b7c28aa4106b43`;
the retained arm64e slice is
`13827d7242e4550f3d45994f9849ce3a84dbb14d3bb6de21601c4488287582fb`.
The exact Recovery executable hash remains unavailable. A separate sandboxed
read-only attempt failed before parsing because it could not create a Disk
Arbitration session; that environment failure is retained, not counted as an
image test. The subsequent host read-only comparison ran successfully.

## REA qualification and full finite range contract

REA 6.4.0 with Ghidra 12.1.4 ran in the existing diskless, network-disabled
Linux lab. New queries cover the distance-call adapter at `0x100025cc0` and
the SPTM segment-name accessor at `0x100058e6c`. Existing analyzer, tuple
producer and arithmetic-helper evidence was reused, with independent source-byte
and LLVM comparison: 1,127 selected instruction words match, zero mismatches.
The large analyzer's decompilation has removed blocks and
truncated value flow; no whole-function pseudocode claim is accepted. The
bounded assembly/byte trace, plus the actual old/new inspector experiment,
supports these behavioral facts. No extracted Apple bytes, assembly or
decompiler statements are published.

Let T, D, E, B, P and L denote the file offsets of `__TEXT`, `__DATA_SPTM`,
`__TEXT_EXEC`, `__TEXT_BOOT_EXEC`, `__PRELINK_INFO` and `__LINKEDIT`.
The qualified analyzer computes:

| Check | Condition | Required nonnegative distance |
| --- | --- | --- |
| Executable split | profile true, B present | B − E |
| Initial range | always | selected start − T |
| Link-edit range | always | L − P |
| SPTM data range | D present, either profile | E − D |
| Boot range | B present | P − B |

Selected start is P for profile false; for profile true it is D when present,
otherwise E. Missing B uses E's declared size for the split instead of B − E.
The top-level T offset must be zero. Inner headers use collection-absolute
offsets and retain T = 16384; they are not independently constrained to T = 0.
The original finite validator checks both headers' mapping geometry, starts,
extents, gaps, permissions, metadata and payload consistency. Its arithmetic
model is explicitly **not Apple's complete validator**. Permissions are not
part of the traced tuple; no general firmware permission policy is inferred.

Analyzer call sites are `0x100024a50`, `0x100024af8`, `0x100024b4c`,
`0x100024b8c`, and `0x100024be8`. The last three use the adapter at
`0x100025cc0`; the common distance wrapper is `0x10002413c` and the checked
subtraction primitive is `0x1000eecc8`. The actual failing E − D path is
independent of the page-protection profile. The former 31AD theory focused on
only B − E and missed this check.

Apple's [pinned XNU linker rules](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/makedefs/MakeInc.def#L996)
independently place DATA_SPTM before normal executable text and normal text
before boot text. This is corroborating build convention, not proof of custom
collection acceptance. `loader.h` defines Mach-O structures; it does not specify
these semantic subtraction rules. XNU's pre-collection LINKEDIT placement is not
used to overturn the project's measured collection P-before-L requirement.

## Original repair

31AE relinks the same seven frozen original source files. It moves owned data
before normal executable text and retains boot code, entry, vectors and body
positions. It does not rename writable bytes as code or move encoded code
without relinking.

| Region | Final file start | Bytes | Protection |
| --- | ---:| ---:| --- |
| Outer and inner headers | 0 | 32768 | R |
| Owned data | 32768 | 49152 | RW |
| Normal executable park | 81920 | 16384 | RX |
| Boot executable | 98304 | 65536 | RX |
| Prelink information | 163840 | 16384 | R |
| Link-edit reservation | 180224 | 16384 | R |

Complete image: 196608 bytes. Both headers satisfy D ≤ E ≤ B ≤ P ≤ L,
with nonoverlapping extents and a consistent affine file/virtual mapping.
The entry remains inner-base + `0x14000`; vectors remain +`0x14800`.
The record becomes +`0x4000`, stack bottom +`0x8000`, stack top +`0x10000`.
The record-field ABI and code sources are unchanged; these absolute addresses
are intentionally changed. GNU linking changes exactly three boot instruction
words at payload offsets `0x14010`, `0x14068`, `0x15004`, independently predicted
as the record/stack references. No additional boot-code differences occur.

The 31AD package and every prior receipt remain frozen. New source,
validator, regression tests and full-payload runtime harness live under 31AE.
The exact rejected 31AD artifact is a negative control, including the case where
the old executable-only guard accepts it and the new data-order guard refuses.
Both modeled profile values are tested; native profile selection is not assumed.

## What the next native test can establish

After independent M1 review and separate human approval, one lab-only Mach-O
installation can test the remaining installer contract. Only success permits one
30-second visible-entry observation, followed by exact boot021 rollback and
Macintosh HD/default restoration. Preserve original Full/lab Permissive.
No security change, new volume, raw candidate fallback or automatic retry.

The marker tests resident-entry/display visibility, not monitor readiness,
secondary CPU start, Linux, GPU or performance. A silent result is ambiguous.
The captured error and its offline repair are image-format evidence, not a
physical CPU or Apple-firmware prohibition. Neither an all-core solution nor an
Apple-only dependency is established yet.

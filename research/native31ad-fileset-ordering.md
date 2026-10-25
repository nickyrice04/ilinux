# 31AD — fileset split-protection ordering, offline root-cause hypothesis

**Status: Hypothesis.** This note records why 31AD reorders the candidate image.
It does **not** claim the 31AC `configure-boot` exit 71 ("fileset error") is
diagnosed. The actual Recovery error text and the actual installer analyzer
profile were never captured (`actual_recovery_profile: UNOBSERVED`), so the cause
remains **Unknown**; 31AD is the candidate that *tests* this hypothesis, not a
proven remedy.

## The public invariant

The published Mach-O fileset format in
[Apple's pinned `loader.h`](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/EXTERNAL_HEADERS/mach-o/loader.h)
places the normal executable text segment (`__TEXT_EXEC`) and the
boot-executable text segment (`__TEXT_BOOT_EXEC`) in a boot fileset. A
split-protection file-offset check computes the gap between the two by unsigned
subtraction and therefore requires

```
__TEXT_EXEC.fileoff <= __TEXT_BOOT_EXEC.fileoff
```

in both the outer and inner headers. When `__TEXT_EXEC` is placed *after*
`__TEXT_BOOT_EXEC`, the subtraction wraps (unsigned underflow) and the check is
expected to throw.

## The 31AC candidate's own geometry (Observed)

The project's own 31AC diagnostic Mach-O
(`sha256 261d4444…e54ab72`, the image rejected on 2026-10-25) places:

| Segment | File offset | File size |
|---|---:|---:|
| `__TEXT_BOOT_EXEC` | 65536 (0x10000) | 65536 (0x10000) |
| `__TEXT_EXEC` | 131072 (0x20000) | 16384 (0x4000) |

So `__TEXT_EXEC.fileoff` (131072) is **greater than** `__TEXT_BOOT_EXEC.fileoff`
(65536); the ordered difference is `-65536`, an unsigned underflow. These are the
offsets of **our own** published artifact, measured offline from its own bytes.

## What is and is not established

* **Likely:** the 31AC layout violates the public ordering invariant and would
  underflow the checked subtraction.
* **Hypothesis only:** that this is what produced exit 71. The offline analyzer
  derives the gating page-protection profile as *false* for the path it could
  follow, and the real Recovery profile was never observed. A different profile,
  a different check, or an unrelated fileset constraint could equally produce a
  "fileset error". No component-level cause is confirmed.
* **Confirmed:** wrapping the old payload in a nested fileset **without**
  reordering does not change this relative order and so does not address the
  invariant. The fix must reorder the payload itself.

No decompiled Apple code, pseudocode or extracted Apple bytes are reproduced
here or anywhere in the repository; the proprietary-binary analysis that raised
this hypothesis stays under the ignored `build/` tree. This note records
behaviour and our own artifact's geometry only.

## What 31AD does

31AD relinks the unchanged, hash-pinned 31AC payload (entry, translation
helpers, runtime, C bridge, 31AB observer — byte-identical sources) so that
normal executable text precedes boot-executable text, then wraps it in an outer
`MH_FILESET`. Both inner and outer headers satisfy
`__TEXT_EXEC.fileoff <= __TEXT_BOOT_EXEC.fileoff`. The code bytes are unchanged;
only link placement and the wrapper change. Total image length is 196608 bytes.
Geometry and the independent ordering guard are in
`kernel/experiments/bootimage31ad/README.md` and `validate_ordered.py`.

A successful install of the 31AD candidate would make the ordering hypothesis
**Likely**; it would still not prove native entry, display, SMP or performance.
A second rejection would leave the cause Unknown and must not be retried with
altered flags.

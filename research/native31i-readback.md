# 31I: correct the reset readback predicate, complete the combined campaign

2026-10-21. **Native31I NOT RUN.** No host/boot/security change or target operation.

## What31H actually measured

[M1's31H result](../native/boot/attempt31h-2026-10-21-result.md), commit16292e3,
is a preflight refusal, **not a CPU1 startup timeout**. Both guarded64-bit mirror
reads completed, fully equal, address field=image base, bit0 set, bit11 clear,
bits10:1/47:42 zero. Upper63:48 was nonzero. There were0 mutation intentions,
0 starts and no PS/core-state/entry measurements. Macintosh HD return was
confirmed at+37.692 seconds. Exact upper-bit values were not retained publicly
and must not be invented.

The31H check required upper bits to read zero. That requirement was an error
in our interpretation: a normalized write value does not determine all readback
bits. The new evidence below directly supports correcting that predicate.
It does not establish why CPU1 previously failed to enter.

## REA readback investigation and independent validation

Reused the retained REA6.4/Ghidra12.1.4 dossiers for the matching generic,
unpersonalized `iBoot.j716c.RELEASE`, `mBoot-18000.161.10`. No new REA VM query
was needed. Fresh bounded disassembly with the existing Apple LLVM tool was
compared with the decoded original bytes and our analysis ELF. All Apple bytes,
disassembly and decompiler output remain under ignored local build storage.

| Input | SHA-256 |
|---|---|
| Decoded firmware | `b4822fc8902c3693ee590c544011603423a75291edd60afd31210d068a4ca120` |
| Analysis ELF | `f89169923c17be829c6b31c3c04c5695d06d42a42cea7390f61214202400dcee` |

The analysis base0x100c1aa4000 is header-derived, not a live load measurement.
Runtime branch selection and current effective CPU1 entry remain unknown.

**Confirmed static:** function0x100c1c2e398 normalizes the requested address
with0x3fffffff800 and bit0. After the64-bit readback, it compares only bits41:11
and bit0, using mask **0x3fffffff801**. Upper63:42 and low10:1 are explicitly
excluded from this equality. A zero-upper readback is not required by that
verified predicate.

| Behavior | Function-relative offset / analysis address |
|---|---|
| Comparison-mask construction | +0x80/+0x84,0x100c1c2e418/41c |
|64-bit readback | +0xb8,0x100c1c2e450 |
| Mask applied to readback | +0xbc,0x100c1c2e454 |
| Comparison | +0xc4,0x100c1c2e45c |
| Equality advances iteration | +0xc8,0x100c1c2e460 |

The bounded following function0x100c1c2e498..0x100c1c2e4fc checks table iteration
and contains no peripheral read or upper-bit predicate. This does not prove
that no other firmware stage uses any upper bit.

A separate retained path at0x100c1aaa664 corroborates address-mask/bit0 checking:
its already-locked branch masks at+0x1ec and compares at+0x1f0, then returns on
match. The precise hardware context of that abstraction remains unresolved;
it supports format interpretation, not effective raw-boot routing.

**Validation:**233 instruction words/932 bytes freshly checked:208 words from
retained REA function bodies plus25 bounded follow-up words. Zero raw-to-ELF
or LLVM-word mismatches. The retained dossiers have zero cross-boundary pcode.
These structural checks supplement manual dataflow/control-flow review; they
are not native execution evidence.

## Independent public-source corroboration

Pinned m1n1 `57a9339ffd1876e78297b17d34dece8cff8fa1ba`
[`src/smp.c`](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/smp.c)
uses bits47:12 for its legacy address comparison and bit0 for lock handling;
it does not require upper63:48 zero. Its64-bit proxy read and unsigned Python
return decode are separate from RPC status; no sign-extension/status-packing
artifact was found by the source audit.

The public [boot guide](https://asahilinux.org/docs/sw/m1n1-dev-guide/) distinguishes
raw cold entry+0x800 from the vector at0. It supplies no reason to move the
recorder because unrelated readback fields are nonzero. The matching firmware
caller already reviewed for31H aligns the supplied entry to4KiB. No new hook,
reset/power write, firmware replay or protection change is justified.

## Original implementation decision

31I adds a pure report validator and a separately pinned controller. It calls
the frozen31G preflight through the existing31H observer, then applies the
corrected readback predicate. It never catches a31H refusal and continues,
changes shared globals, modifies a consumed manifest, or reruns the census.

Retain all these requirements: exactly2 guarded validated rows; integer-zero
exception acknowledgements; complete/full mirror equality; matching legacy
page and firmware image-base field; bit0 set; bit11 clear; bits10:1 and47:42
zero; exact live hardware/ADT/core routing. Retaining the latter zero checks is
conservative;31H actually observed them and no reason to broaden them exists.

Bits63:48 may be present only under the same full-mirror-equality requirement.
Their classification is retained as `present_uninterpreted`; their meaning is
**UNKNOWN**, not declared benign, reserved, a status code or a CPU address.
The new gate result describes address-readback compatibility only, never PC,
reset release or CPU1 instructions. This is a correction to a project check,
not a change to a hardware/security check.

All later31H behavior is inherited unchanged: up to8 PS and8 opaque core-state
reads, existing recorder, same two CPU1 starts, complete arrival/identity gates,
8 conditional callbacks and final park. Same bounds/first-error stop. The
32-bit core-state access remains exploratory and untested on this hardware;
31H did not reach it. Its original access-risk and interpretation limits apply.

## Make the physical session count

One session collects the previously unrun combined campaign:

| Result | Next engineering decision |
|---|---|
| Address/lock/mirror or fault refusal | Stop with partial evidence. Review the precise mismatch; no retry or guessed write. |
| Core-state access/translation refusal | Record the baseline prefix and stop. Do not change width/address or continue after fault. |
| PS and opaque state transition, no marker | Investigate effective dispatch/first-store visibility; neither field proves execution. |
| PS transition, unchanged opaque state, no marker | Investigate reset/entry contract and state-field meaning; do not call it proof of reset being held. |
| Partial recorder | Localize the first committed software stage, retaining identity/EL/cache uncertainty. |
| Complete arrival,8 requests/counter progress and park | Prepare a separate two-core Linux batch: coherence/atomics, timers/IPIs, clocks, memory and renderer/input latency. |

No more cores, longer timeout, speculative fallback, reinstall or image transfer.
No negative result automatically triggers another branch or boot. Physical
firmware/cache behavior cannot be proven in a VM, but the actual31H report is
now an offline regression so this particular needless refusal cannot recur.

The target remains12 Performance+6 Super cores with measured scheduling/DVFS/
idle policy, networking/storage and GPU support. This campaign has not delivered
native SMP or macOS-class performance; it fixes the diagnostic obstruction.

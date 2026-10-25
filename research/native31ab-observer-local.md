# 31AB: local aperture lookup and cold pointer preparation

The retained kernel provides a small physical-to-virtual range lookup, and the
retained monitor prepares its count/table pointers on the checked normal cold
handoff branch. These facts support an original bounded address resolver. They
do **not** yet establish that the table is populated and accessible before
`FIXUPS_COMPLETE` (service 15), or that a translated framebuffer address is writable
with suitable cache attributes. This is a narrower unresolved dependency than
decoding the complete 848-byte record or implementing every helper service.

This supplements the frozen [entry finding](native31ab-entry.md). The independent
[public observer contract](native31ab-observer.md) describes the video descriptor
and mapping obligations; the [route note](native31ab-route.md) separates software
implementation from native acceptance. No native execution, monitor invocation,
framebuffer write, permission change or hardware readback occurred here.

## Inputs and scope

The retained `kernel.release.t6050` is 17168528 bytes, SHA-256
`2bd94a6fcff6203861e46b39920c16e1b5563d9bb17405b8a42c59c2ef4486e0`.
Its 31Z comparison to the installed 25G83 kernel is inherited, not rerun. The
retained decoded monitor is 1376288 bytes, SHA-256
`da2ad8d4ecbf3e29fbaaa07e8c7d291ed20d296044494e00303c7a780d190666`.
Its earlier 25G83 association comes from the 31W record; it is not a fresh match to
the installed or historically executing firmware. Agreement between selected
fields does not establish complete ABI or runtime identity.

CPU-B used a sparse analysis carrier containing exactly 140 original code bytes
at their original virtual addresses and file offsets, with generated metadata.
Original data and most code were omitted, and the original entry was unmapped.
CPU-C used the unchanged retained monitor. It has no `LC_FUNCTION_STARTS`; entry
markers, the next marker, returned provider bounds and source bytes qualify the
selected 1688-byte body. Neither carrier is an original deployable boot image.

## Confirmed bounded behavior

The kernel's exported `ml_static_ptovirt` wrapper directly calls the 140-byte
lookup at `0xfffffe0007c784c0`. This independently establishes the translation
direction. The lookup consumes a physical address and a pointer to an 8-byte
output. Its helper state supplies a count pointer at +8 and table pointer at +16.
The pointed-to count is 32 bits. Each 24-byte record supplies:

| Offset | Width | Meaning |
| --- | --- | --- |
| +0 | 8 bytes | Physical base |
| +8 | 8 bytes | Virtual base |
| +16 | 4 bytes | Count of 16 KiB pages |

The physical interval includes its base and excludes its end. A successful
translation preserves the offset within the range. A zero translated result is
rejected. The output changes only on success: return 0 succeeds, 1 reports an
uninitialized helper, 2 rejects a null output pointer, and 4 reports no match or a
zero translation. There is no monitor call, mapping installation, cache operation
or TLB operation in this body. General arithmetic overflow rejection is not
qualified; an original reader must bound the count, complete access extent and
all address arithmetic rather than inherit trusted-table assumptions.

The monitor producer at `0xfffffff0270bf958` is directly called on the checked
normal cold preparation branch before the common exit. Its selected stores set
the helper's 32-bit version to 10, and its two 64-bit pointers to
`0xfffffff027105ac8` (count) and `0xfffffff027105ad0` (table). The helper begins at
outer record +416, so these are outer record +424 and +432. They are monitor DATA
virtual addresses; their normal-world accessibility is not established by the
stores. The selected helper version agrees with the 26.5 SDK comparator, but the
complete 848-byte outer layout remains unidentified. The previously checked
kernel helper initializer forwards these two fields.

## Remaining initialization and display boundary

The retained file contains a zero count, not a runtime snapshot. A separate
bounded initializer writes the count, and two direct caller edges are identified.
Their ordering relative to the normal cold exit or service 15 is **unknown**.
The private handoff records the exact initializer, caller ranges and next owner
question. A dispatch endpoint must not be inferred from neighboring table entries
or index arithmetic. The positive finding is pointer preparation before the
checked cold exit; it is not proof of a populated, readable pre-service 15 table,
nor proof that no such table is available. All-path dominance through other error
branches is also outside this finding.

The sanitized ADT audit covered 656 nodes and found no retained framebuffer/video
address or geometry values. A useful observer must take its descriptor from the
actual cold-entry argument and validate its applicable revision, dimensions and
complete extent. Existing range translation alone cannot certify permissions,
memory type or scanout visibility. Architectural translation checks can add evidence
about the active mapping; their precise regime and scope must remain explicit.
DockChannel service 45 is not an established substitute: neither its pre-service 15
availability here nor an external observer is qualified.

The finite next discriminator is whether the actual cold-entry count/table is
initialized and readable, followed by whether the complete selected framebuffer
extent has the required mapping and attributes. The exact static count-initializer
owner remains an alternative way to resolve the first question. No additional
REA query was requested in this supplement. These unknowns do not establish an
Apple-only restriction and do not justify an unchanged raw-start retry.

## Verification

CPU-B completed one query in 16.469 seconds: 35 instructions, 64 P-code operations.
CPU-C completed one query in 22.252 seconds: 422 instructions, 2471 P-code operations.
Both returned within the 100-second bounds, with setup/job exit 0, no provider
warnings, no P-code outside their returned bodies and no native-value-flow
truncation. Whole-function pseudocode was not used. Root owned both isolated VM
runs; only loopback networking and no physical USB were recorded.

Independent source/LLVM comparison covers 566 instruction-sized words
(2264 bytes) in eight ranges with zero mismatches: 457 queried-body words,
13 exported-wrapper words, one rejected-candidate width check, three cold-call
words reverified from CPU-A, 90 unqueried initializer-context words and two caller
words. These are unique within this supplement, not all new across 31AB. The
original two-target CPU-B proposal was superseded **before execution** when the
second candidate proved to write a one-byte classification. It contributed zero
guest queries and is not a provider failure. Frozen CPU-A and earlier refusals
remain unchanged.

The [validation record](../reverse-engineering/findings/cpu-startup31ab/validation-observer.json)
contains source/carrier hashes, per-range hashes, query bounds, execution receipts
and these limitations. Apple bytes, instruction text and pseudocode remain in
ignored private storage. Original implementation tests are reported separately;
they are not native CPU or display progress measurements.

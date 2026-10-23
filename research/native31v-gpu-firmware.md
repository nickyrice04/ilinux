# 31V: mapping notification is a separate publication contract

Date: 2026-10-23. **Offline research and original implementation; native G17C
HOLD / NOT RUN.** M1's 31U review, merged as `c510d74`, passed 475 pins, 225
Python methods and 95 portable C groups with no actionable issue. Native
mapping, coherence, progress and readiness remained unqualified. Earlier sources
and refusals remain frozen.

This pass follows map-commit calls to an outbound mapping-notification record
and ring. It establishes a useful 24-byte encoder and bounded producer contract,
without qualifying an end-to-end page-table/cache/TLBI protocol or native adapter.

## Mapping and notification are distinct

The checked secure map commit at `0xfffffe00089b5c74` and legacy commit at
`0xfffffe00089986a0` contain separate mapping and notification operations.
Static collection references resolve their validation, standard-firmware
classification and notification slots. The secure no-argument wrapper forwards
to the checked secure commit slot. These identities do not establish runtime
selection of either class.

The notification chain continues through `notifyFirmwareOfMapping` and its page
callback. In the inspected `AGXArmFirmwareASC` table, firmware slot 752 resolves
to `AGXArmFirmware::notifyNewMapping` at `0xfffffe000896b8e0`. Conversion and
firmware-page-shift slots resolve separately. The checked ASC page-shift
accessor returns 14. Address conversion remains a typed boundary even where the
checked implementation preserves the input value; CPU-physical identity does
not follow.

Secure `mapInThisGart`, at `0xfffffe00089b7188`, calls both IOUnifiedAddressTranslator
and AGXUnifiedAddressTranslator mapping APIs. The latter's `doMap`, at
`0xfffffe00089d94fc`, includes direct call edges to pending-unmap commitment,
locking and TLB invalidation. Actual mode selection, indirect mapping effects,
cache visibility and hardware completion remain unqualified. A named commit or
an absent inline cache instruction cannot settle those questions.

## Selected notification record

Independent bounded instruction checks establish this **24-byte little-endian
variant** on the selected ASC path:

| Offset | Width | Checked field |
|---:|---:|---|
| 0 | 8 bytes | Converted firmware virtual address |
| 8 | 4 bytes | Byte length in 4-KiB units |
| 12 | 4 bytes | Zero |
| 16 | 2 bytes | Gart-page-size / firmware-page-size ratio |
| 18 | 2 bytes | Observed values 1 or 5, selected by the Boolean input |
| 20 | 4 bytes | Zero |

With firmware shift 14 and Gart shifts 14–29, the ratio is a nonzero 16-bit
power of two from 1 to 32,768. This is the original encoder's arithmetic domain,
not qualification of every such native Gart configuration. Bit 2 has no assigned
permission, protection or cache meaning.

The private path narrows fields. Original software instead rejects zero length,
lengths not divisible by 4 KiB, counts above `UINT32_MAX`, address-plus-length
overflow and shifts outside its admitted range. The full caller-qualified
64-bit firmware address is retained. This is distinct from the 31S bootstrap
message's 44-bit field; that mask or an unconverted CPU address cannot be reused.

Selected notification paths append to a bounded deferred array; another state
calls immediate ring insertion. With neither a pending array nor the active
immediate path, the checked synthetic case produces no ring entry. These
software conditions are not a recovered readiness handshake.

## Ring publication and original implementation

`insertNewMappingEntry`, at `0xfffffe000896b780`, uses **256 slots of 24 bytes**,
requiring 6,144 data bytes. Shared control has a 32-bit consumer at offset 0 and
producer at offset 16. Both indices must be below 256. The next producer wraps
modulo 256; equality with the consumer means full.

Successful insertion copies all 24 bytes to the producer's slot. An
inner-shareable barrier follows the copy and precedes the producer-index store.
This establishes a concrete data-before-index order, not the device visibility
of an arbitrary Linux mapping or a C11 fence.

There is additional progress behavior. When the consumer is two slots ahead
of the current producer, leaving one free entry under the reserved-slot rule,
the checked path invokes an unresolved indirect helper before copying. The full
path waits and rereads state. The helper's object and effects remain unknown;
it must not be labeled a doorbell or flush from its slot number.

The original [interface](../kernel/experiments/gpu31v/mapping.h) and
[implementation](../kernel/experiments/gpu31v/mapping.c) encode the selected
record and perform one bounded submission attempt through injected callbacks:

- Preparation validates the record, indices and extent, retains the bytes, and
  refuses a full ring without waiting or invoking the unresolved helper.
- Submission writes the complete record to an unpublished slot, then calls the
  publication adapter. That adapter owns actual synchronization and the index
  store. Opaque status and explicit acceptance are separate.
- Write or publication refusal may already have effects. A terminal receipt
  retains the record/status, with no retry or reset. A new object cannot bypass
  external reconciliation.
- The caller preserves sole-producer ownership, acquired indices, coherent
  backing and mapping lifetime from preparation through submission. The consumer
  advances only through published records. Reentrant submission is refused.

The single-attempt full-ring policy is an original choice. Native progress,
including the near-full helper, remains an external prerequisite. Adapter
acceptance means neither wakeup nor firmware receipt, consumption, completion
or readiness. No native allocator, DMA mapping, page-table operation, MMIO or
firmware transport is supplied.

Review found no blocker after making progress policy and reconciliation explicit.
The parent reports eight original host C groups passing; its integration record
owns those executions and the source closure.

## Explicit decompiler refusals

Both notification dossiers are **rejected across a function boundary**:
`notifyNewMapping` has two retained high P-code operations outside its body and
`insertNewMappingEntry` has one. All three enter the unlock helper at
`0xfffffe000bc0f6cc`. Bad-instruction/control-flow warnings remain recorded; the
notifier also has a removed-block warning. Their whole pseudocode is not used.

The separate evidence is complete symbol-bounded carrier words, matching LLVM
instruction words, and an original sequential interpreter using synthetic data
and stubbed external effects. This checks the selected encoding/publication
behavior without executing external callees. It does not relax rejected gates
or prove all runtime paths, pointer authentication, concurrency or cache coherence.

Secure commit and secure inner mapping retain removed-block warnings. No query
truncates high P-code in this pass. Earlier 31Q/31R cross-boundary refusals, 31T
allocation truncation and 31U dispatcher truncation remain unchanged. No expanded
dispatcher export was needed.

## Public comparison and remaining prerequisite

Asahi's pinned
[firmware-control definition](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/fw/agx/channels.py#L445)
has a **20-byte** record and a 256-slot ring with the same 0/16 index offsets.
Matching control geometry does not make it compatible with this 24-byte record.
Its [UAT publication](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/hw/uat.py),
[object release](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/agx/object.py)
and [handoff phases](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/fw/agx/handoff.py)
are separate ordering/lifetime comparisons, not G17C qualification.

Vinix's pinned
[G17 initialization](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/kernel/gpu/agx/gpu/g17.v)
constructs mappings and roots behind closed normal-driver admission. Its complete
[flush transaction](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/kernel/gpu/agx/gpu/gpu.v#L1107)
explicitly requires G13. The G17 source context is 25F71/AGXG17X 351.2/RTKit
3255.120.11, distinct from retained 25G83. The
[upstream investigation](native31v-upstream.md) details these limits. Six relevant
public files were read and hash-checked as data, never executed.

The missing native adapter must bind the correct role's mapping/conversion to
this notification variant, qualify page-table/cache/TLBI visibility, acquire
coherent ring state, publish with device-safe ordering, and resolve progress
and completion. Mapping commitment, deferred construction, producer publication,
firmware consumption and hardware completion remain separate events.

## Evidence totals

Carrier SHA-256 remains
`26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`; AGXG17X
remains `e772f7d8a6197ff54fa3e06b5cc83f8d2019dfb53cdc345b59678ebc4f14339b`.
A match to the running kernel remains unverified. Independent raw-word/Apple
LLVM checks match **1,351 words across 13 ranges**, including 1,084 words in
six query targets, with zero mismatches. Fifteen selected collection references
have verified chain membership; this is static evidence only.

Six queries completed within 100-second limits in three root-owned, diskless,
no-network VM batches. Secure/legacy commit took 72.589/71.912 seconds; inner
map/notifier 72.413/72.423; insertion/UAT map 71.971/72.119. Each batch verified
loopback only; the parent confirmed setup/job exit zero and released its locks.

Four standard gates require manual review and two reject cross-boundary output.
Of 1,329 retained high P-code operations, three are outside independent bounds
and remain refused. All six assembly listings match complete independent ranges.
Exact bounds, hashes, warnings and public-source pins are in the
[validation metadata](../reverse-engineering/findings/gpu31v/validation.json).

The private interpreter checks **1,549 synthetic cases**: 512 exact encodings,
five narrowing cases refused by original policy, four deferred-array cases,
768 successful publications covering every producer slot, 256 bounded full-ring
stops and four invalid-index cases. Successful cases include 256 observations
of the unresolved near-full helper. These are not native execution of Apple
code or a hardware ordering test. Apple bytes, assembly and P-code remain solely
in ignored local storage. **Native G17C remains HOLD / NOT RUN.**

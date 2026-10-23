# 31W: mapping pressure note and qualified transport boundary

**Confirmed, bounded static evidence:** the previously unresolved near-full
mapping helper uses numeric provider role **0** and the endpoint associated with
selector **0x21**, carrying the exact word **0x0085000000000000** and an outer
Boolean **false**. This resolves a host-side call boundary. The word's firmware
meaning, mapping completion and GPU readiness remain **Unknown**. Native GPU
enablement remains **HOLD / NOT RUN**.

M1's 31V offline PASS review was incorporated in `9befeb3`. This pass preserves
the frozen [31V format and producer](native31v-gpu-firmware.md) and all earlier
refusals. It adds an original composition with that producer, rather than a
second queue implementation. The machine-readable record is
[validation.json](../reverse-engineering/findings/gpu31w/validation.json).

## Evidence and bounds

Root executed one isolated, diskless, no-network VM batch. Both 100-second-bounded
REA queries completed: provider initialization in 72.863 seconds and gated note
forwarding in 22.991 seconds. Root reported `SETUP_EXIT=0 JOB_EXIT=0`; the guest
network record contains loopback only. No native operation was performed.

The retained local 25G83 carrier SHA-256 is
`26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`.
The AGXG17X derivative is
`e772f7d8a6197ff54fa3e06b5cc83f8d2019dfb53cdc345b59678ebc4f14339b`;
the provider derivative is
`99d95ff5c337a3f6a46368893359c1e6cd861eeed0fa47f398cc8c7280770841`.
These are retained artifacts, not a verified identity for the currently running
kernel. Apple bytes, assembly and P-code stay in ignored private storage.

| Independently checked range | Start | End, exclusive | Words |
| --- | --- | --- | ---: |
| Provider initialization | `0xfffffe000896d0ac` | `0xfffffe000896d130` | 33 |
| Gated asynchronous note | `0xfffffe00088f93bc` | `0xfffffe00088f95d8` | 135 |
| Asynchronous-note wrapper | `0xfffffe00088f95d8` | `0xfffffe00088f96e4` | 67 |
| Mapping insertion, repeated 31V range | `0xfffffe000896b780` | `0xfffffe000896b8e0` | 88 |

All **323 instruction words** agree between carrier, derivative and Apple LLVM
21.0.0; 168 belong to the two fresh queries. Their REA listings cover the bounded
ranges. There are **144 high P-code operations**, none outside those ranges and
no reported truncation. Both standard gates require manual review. Gated
forwarding retains unresolved-indirect-jump and provider-removed-block warnings;
these counts do not establish whole-function equivalence. In particular, the
repeated insertion range does not overturn its 31V cross-boundary refusal.

Five static collection references and three matching callsite discriminators
qualify the selected edges. Original sequential interpretation checks
**522 synthetic cases**: two provider roles, 256 near-full positions, 256 ordinary
positions, three wrapper statuses, three direct-send statuses and two excluded
direct-send guards. External calls are stubs. This is not native execution of
Apple code and proves neither pointer authentication nor concurrent/device
behavior.

## Receiver and transport findings

**Confirmed selected paths:** initialization places providers for numeric roles
0 and 1 in separate slots, 56 bytes apart. The near-full call reads the role-0
slot. The checked provider tables resolve slot 2176 to pointer binding and slot
2216 to the asynchronous-note wrapper. Static membership and discriminator
agreement do not prove the class or lifetime of a live receiver.

The wrapper preserves the word and outer Boolean through gated dispatch. The
selected direct gated path requires a non-null stored endpoint and a zero
provider guard byte. It reaches endpoint `sendMessage`, forwarding the word
buffer with a null secondary buffer and a separate Boolean true. Neither Boolean
is assigned a priority, blocking or acknowledgement meaning. The endpoint slot
is associated with selector 0x21 by the earlier checked
[match/termination callbacks](native31r-gpu-firmware.md). Numeric provider role,
endpoint selector and ADT GFX/GFX1 identity remain separate namespaces.

Endpoint absence or a nonzero guard excludes this direct send. Those alternate
diagnostic/error/suppression paths are not qualified delivery paths, and their
status conventions remain unknown. An adapter must establish actual eligibility,
accepted endpoint ownership and lifetime; the private guard is not a public
readiness API. A zero status alone cannot establish delivery.

**Confirmed ordering:** in the 256-slot mapping ring, one available entry is
identified by `consumer == (producer + 2) % 256`. The selected path sends the note
before copying the new 24-byte record and publishing its producer index. The
checked insertion does not branch on the returned note status before proceeding.
Because the note precedes the new record, that return cannot acknowledge the
unpublished record. Firmware consumption, page-table visibility, completion and
readiness require separate evidence.

## Original composition and remaining prerequisite

The [31W component](../kernel/experiments/gpu31w/pressure.h) composes the frozen
31V producer. With a valid captured snapshot and one available entry, it requests
the exact qualified note first, then performs the existing record write and
adapter publication. A full ring calls nothing and does not wait. Ordinary
positions need no note.

Explicit adapter acceptance is separate from opaque status. Suppressed or
uncertain delivery stops before the record write, retains the receipt and
forbids automatic retry. This is an intentional original policy stricter than
the checked private insertion. Existing unknown-write/publication handling is
preserved. Reentrancy is refused; callers must maintain producer serialization,
mapping lifetime and an acquired snapshot throughout. Unknown effects require
external reconciliation, including before attempting a new submission object.

Review of the original `pressure.h` and `pressure.c` found no behavioral blocker
within that contract. Root owns its final tests and integration. No native
transport adapter is supplied. The caller still must qualify the provider
incarnation, endpoint acceptance, firmware version, transport eligibility,
address conversion, mapping and actual DMA visibility. Accepted callbacks do
not imply firmware acknowledgement or readiness.

The public comparator makes the semantic limit especially important:
[Vinix at ffb1fc5](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/kernel/gpu/agx/gpu/gpu.v#L27)
names 0x85 shifted by 48 as `halt`, and 0x84 as firmware control. Its complete
flush path is G13-only; its G17 initialization remains behind closed admission.
Its 25F71/AGX351.2/RTKit3255.120.11 context differs from this retained 25G83 input.
Neither that label nor a benign kick/flush interpretation is qualified here.
The exact public-file hash is in the validation record; the file was read and
hashed, never executed. See the [31V public comparison](native31v-upstream.md).

The next useful discriminator is a version-matched firmware-side interpretation
or independently observable completion condition for this note and mapping
queue. Another host wrapper alone cannot establish it. Earlier cross-boundary
and truncation refusals remain frozen; no native boot, mapping operation,
performance gain or firmware readiness is claimed.

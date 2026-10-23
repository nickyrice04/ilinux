# 31U: a bounded firmware-event consumer contract

Date: 2026-10-23. **Offline research and original implementation; native G17C
HOLD / NOT RUN.** This consumes M1's 31T review published in `99146f7`: 458 pins,
216 Python methods and 88 portable C groups passed with no actionable issue.
That review did not qualify native firmware mapping, publication or readiness.
The frozen 31T ownership helper and all earlier records remain unchanged.

The new result is a concrete event-ring consumption contract: capture bounded
indices, copy a complete 72-byte record, validate its type, then order the reads
before publishing the new consumer index. This supports an original component
that performs those operations through injected callbacks. It does not yet
supply the native mapping/coherency adapter or establish firmware readiness.

## Confirmed bounded ring behavior

`AGXFirmwareRingValidator::snapshotState`, at `0xfffffe00089571b0`, captures
32-bit consumer and producer indices from shared control storage. In this
retained implementation their control offsets are 0 and 32 bytes. Both indices
must be below the 32-bit capacity, and the data backing must be present. The
captured values form local state for subsequent consumption. No inline memory
barrier is observed in this bounded snapshot routine; this does not establish
that preceding callers or mapping attributes provide the required acquisition
and coherence guarantees.

`fetchNextEntry`, at `0xfffffe00089572bc`, consumes those captured indices. It
does not reread the shared producer. Equal cached indices, an invalid consumer
index or missing backing take failure paths before record copying. Thus a
producer advancing after the snapshot does not extend this drain batch. A new
snapshot is required to observe that progress. The adjacent outstanding-entry
check also operates on the cached indices.

**Record stride and copied size are both 72 bytes.** The checked fetch transfers
all eighteen 32-bit words of the selected record into the supplied output. The
first copied word selects a bit in a 64-bit allowed-type mask. Type admission
occurs after the full copy and before the consumer index advances or is
published. A disallowed selection follows a failure path without publishing
the consumer index. A successfully copied or admitted record is not by itself
an acknowledgment, a completion event, or permission to free other resources.

The private variable shift uses the architecture's low-six-bit shift-count
behavior. Consequently a type value of 64 or above can alias a lower mask bit.
The original component deliberately rejects every type at or above 64. This is
a stricter input policy, not a claim that the observed routine performs that
range check.

After copy and type admission, the checked routine advances the consumer modulo
the explicit capacity. Non-power-of-two capacities work in the bounded checks.
An inner-shareable barrier then precedes the shared consumer-index store. This
orders the observed record-read/reclamation path; it does not establish cache
maintenance, mapping publication, UAT commit/TLBI ordering, or the conditions
under which firmware first acquires the shared data. A CPU-language fence alone
cannot be substituted for a qualified DMA/device synchronization contract.

## Completion and role limits

The separate `AGXFirmware::drainFirmwareEventRing` query, at
`0xfffffe0008941df8`, contains role-dependent ring selection and calls the
checked fetch routine. It also calls the separate
`waitForDeviceControlCompletion`, at `0xfffffe00089434d4`. The latter has
time/deadline-related direct calls and unresolved indirect calls. Neither its
name nor the presence of a wait supplies a received-event acknowledgment ABI.

The event-drain dossier has **truncated high P-code**, with at least one omitted
operation and 204 known omitted edges, and retains a provider-removed-blocks
warning. Its REA listing covers 1,402 of the 1,418 independently checked words
between the symbol bounds. Whole-function event/completion/readiness
interpretation is refused. Only separately checked bounded edges are used.

Two static collection references in the `AGXArmFirmwareASC` table have verified
chained-pointer membership: the controller-event handler and the recovery
staleness handler. Their resolution does not establish the runtime class,
pointer authentication, event labels, or a GFX/GFX1-to-ADT binding. Small checked
software boot-flag accessors likewise do not measure hardware readiness. No
event number is assigned an acknowledgment or ready meaning in the original
consumer.

## Original component and practical adapter boundary

The original [ring interface](../kernel/experiments/gpu31u/ring.h) and
[implementation](../kernel/experiments/gpu31u/ring.c) consume at most one raw
record per call, toward a fixed producer snapshot. They require nonzero
capacity, bounded indices, a sufficiently large mapped extent, and explicit
copy/publication callbacks. Byte offsets use wide arithmetic. That arithmetic
policy does not qualify a native ring with every representable capacity; high
signed-index pointer paths in the retained implementation remain unvalidated.

- A copy callback must return a stable, complete 72-byte record on acceptance.
  The consumer retains all raw bytes and decodes only the initial little-endian
  32-bit type for mask admission. Copy failure stops without publication.
- A type outside the strict software range or supplied mask stops after the
  raw copy without publication. Empty rings and invalid inputs produce safe
  software results rather than reproducing private panic behavior.
- The publication callback must perform the platform's actual synchronization
  and consumer-index store. Acceptance records the callback result, not a
  firmware acknowledgment. A refused publication may already have effects, so
  its raw record, proposed index and opaque status are retained in a terminal
  unknown-effects state. There is no blind retry.
- The caller supplies serialization, sole-consumer ownership, stable backing
  and mapping lifetime, index-acquisition ordering, record coherence, and a
  producer that never overwrites unread records. Equal indices mean empty
  under this contract. Reentrant calls are refused while a callback runs.

This component is useful at the future Linux adapter boundary between a
qualified firmware event mapping and event-specific handling. It supplies the
bounded copy/admission/reclamation operation while retaining the raw record
for a separately qualified decoder. It has no event labels, native device
adapter, allocation, DMA mapping, MMIO, submission, or readiness transition.
Callback result types and failure states are original software choices, not
firmware structures or private status conventions.

Review found no behavioral blocker in the documented offline contract. The
parent's seven original C test groups include 1,785 capacity/index cases,
wrapping, type bounds, copy and ambiguous-publication failures, wide offsets
and reentrancy. Parent integration records own the executed test results and
full source closure; this research record does not independently claim those
runs.

## Versioned public corroboration

The pinned Vinix
[G17 implementation](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/kernel/gpu/agx/fw/g17.v#L3042)
uses 72-byte records and 256 slots, checks the type against a fixed mask with a
strict bound of 32, and copies a record before updating the consumer. It rereads
the producer for each dequeue. The corresponding
[G17C research record](https://github.com/vlang/vinix/blob/ffb1fc5b87660104de4c268804cf1fb2d8afe4bc/tools/agx-re/G17_T6050.md)
identifies macOS 26.5/25F71, AGXG17X 351.2 and RTKit 3255.120.11; its hardware
firmware boot gate remains closed pending further HAL300 work. Those observations
are from a different build than this retained 25G83 carrier. Matching record
size corroborates a useful implementation direction, not native compatibility.
Its constants and event labels are not adopted here.

The pinned Asahi
[receive-channel poller](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/agx/channels.py)
captures a producer position once, processes records to that position, and
publishes the consumer after draining. Its corresponding
[event definitions](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/proxyclient/m1n1/fw/agx/channels.py)
use 56-byte event records. This is an ordering comparator, not the 72-byte ABI.
Both projects' source files were read and hashed as data, never executed or
imported. Exact pins, paths, sizes and SHA-256 values are in the validation
metadata.

## Evidence and remaining discriminator

The retained carrier SHA-256 is
`26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`;
AGXG17X is
`e772f7d8a6197ff54fa3e06b5cc83f8d2019dfb53cdc345b59678ebc4f14339b`.
Their match to the currently running kernel remains unverified. Independent
carrier/derivative/Apple LLVM comparison matches **1,750 instruction words in
nine ranges**, including 1,702 words in the four query targets, with zero
mismatches.

All four queries completed within their individual 100-second bounds in two
parent-controlled diskless, no-network VM batches. Snapshot/fetch took
72.724/72.807 seconds; drain/wait took 72.474/71.729 seconds. Each batch's network
check found loopback only, and the parent reported setup/job exit zero. An
initial sandbox launch refusal occurred before guest execution and is retained
separately by the parent; it is not a completed REA query.

All standard dossier gates remain `manual_review_required`. All 3,333 retained
high P-code operations have addresses inside the independent bounds; this does
not remove the event-drain truncation. The earlier 31Q/31R cross-boundary
refusals and 31T allocation truncation also remain in force. Exact outcomes,
range hashes, gate warnings and public-source digests are in the
[validation metadata](../reverse-engineering/findings/gpu31u/validation.json).

An original bounded interpreter additionally checks 1,923 synthetic fetch
cases and five snapshot cases, including all 64 mask positions, disallowed
types, six architectural shift-alias cases, wrapping, missing backing, invalid
indices, stale producer state, complete raw copies and publication order.
External calls stop without executing. These are sequential instruction-behavior
checks using synthetic memory, not native execution of Apple code, concurrency
tests, pointer-authentication validation or cache-coherence proof. Apple bytes,
disassembly and P-code remain solely in ignored local storage.

The next prerequisite is a version-bound adapter contract connecting the actual
role's ring allocation and CPU mapping to firmware-visible addresses, qualified
index/data acquisition, and consumer publication under the selected UAT/cache
policy. Separately, complete bounded event-dispatch evidence must identify what
specific consumer event means and which request it completes. Until those are
established, mapped memory, an admitted record and a published consumer index
remain distinct from firmware boot readiness. **Native G17C remains HOLD.**

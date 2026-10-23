# 31T: shared-memory preparation has an ownership contract

Date: 2026-10-23. **Offline research and original implementation; native G17C
HOLD / NOT RUN.** This consumes M1's independent 31S review, published in
`822d53f`. Its 441 pins, 207 Python methods and 74 portable C groups passed.
That review found no blocker in the documented offline contracts and correctly
left shared-data ownership, publication and firmware completion unqualified.
The frozen 31S bootstrap code and earlier records remain unchanged.

## Preparation is separate from firmware completion

**Confirmed static behavior:** `AGXArmFirmware::prepareFirmwareData` at
`0xfffffe000896d998` prepares a collection of mappings after the base firmware
preparation succeeds. It checks individual results, has conditional resources,
and follows different cleanup paths when preparation fails. Its successful
path records a software flag while holding a lock. This is preparation of host
resources; it is not a firmware reply or evidence that firmware can read them.

The paired `completeFirmwareData` at `0xfffffe000896d8f4` calls mapping-completion
operations and the base completion routine. The exact three-instruction
`IOGPUMemoryMap::prepareMapping` and `completeMapping` wrappers forward to their
backing `IOGPUMemory` object's preparation and completion interfaces. The
page-table commit/release methods are distinct routines. The word “complete” in
these names therefore does not establish bootstrap acknowledgment, command
completion or readiness.

**Confirmed bounded failure distinction:** one optional-array failure path
passes the failing mapping to completion, whereas fixed-resource failure paths
differ. At the lower layer, a checked `IOGPUMemory::prepare_memory_slow` path
where wiring succeeds and mapping commit fails unwires the backing, balances
the preparation increment, and returns the error. A successful path retains
preparation and updates state. An error may already have been unwound internally.

These observations rule out treating an opaque error code as a universal cleanup
instruction. They do not establish that every failing operation retains a lease,
or that none does. Aliasing, preexisting references, actual callback results and
selected object classes remain unobserved. The optional-array path is not a
claim of a runtime defect. No private counter encoding or cleanup order is
proposed as a Linux ABI.

## Allocation and address provenance

`AGXFirmware::allocateSharedData` at `0xfffffe00089474f8` separates allocation,
mapping creation, initialization of backing storage and retrieval of a mapped
address. Allocation or zeroing alone is insufficient evidence of publication
to the firmware consumer. The query retains its decompiler removed-block warning;
claims use independently bounded instruction evidence.

The larger `AGXArmFirmware::allocFirmwareData` at `0xfffffe000897203c` contains
separate buffer-allocation and firmware-GPU-mapping edges; two checked mapping
results are stored in distinct object fields. `initFirmwareData` at
`0xfffffe00089709e8` then supplies a substantial initialization path with many
indirect calls. These observations preserve the distinction between backing
allocation, mapped addresses and record initialization. They do not recover a
complete shared-data wire layout or resolve the indirect publication/consumer
contract. The absence of an inline cache instruction would not exclude cache
maintenance in a callee.

The allocation dossier explicitly reports **truncated high P-code**, with one
known omitted input and no reported omitted operation or edge. Whole-high-P-code
conclusions are refused. Its bounded allocation edges above use the complete
independent instruction range. The initialization dossier retains removed-block
and unresolved-indirect-jump warnings. Neither result supplies an initialization
profile for native replay.

The address getter used by this allocation path and the 31S bootstrap producer
is now more specifically identified. Carrier chained-reference validation
resolves slot 344 in `IOGPUMemoryMap`, `AGXLegacyMemoryMap` and
`AGXSecureMemoryMap` to `IOGPUMemoryMap::getGPUVirtualAddress` at
`0xfffffe000a491a20`. Its three instructions return the stored address field.
The inspected `IOGPUSysMemory` entries also identify mapping creation and the
wire/unwire methods used by the selected lower preparation path.

This supplies a **statically named GPU-virtual-address source** before the
separately typed firmware-address conversion and 44-bit bootstrap encoding.
It does not establish CPU-physical identity, the runtime map subclass, an ADT
GFX/GFX1 binding, firmware address validity or G17C UAT geometry. The existing
31S codec must continue rejecting oversized firmware-address values; it must
not silently turn a CPU address into a GPU or firmware address.

## Original component

The original [lease interface](../kernel/experiments/gpu31t/leases.h) and
[implementation](../kernel/experiments/gpu31t/leases.c) turn the ownership gap
into an explicit adapter contract. They perform resource operations through
injected callbacks, rather than merely recording readiness observations.

- Each preparation reports acceptance, an independent cleanup obligation, an
  opaque lease token and an opaque status. Status alone determines none of the
  other fields. Accepted borrowed resources and partially failed owned resources
  are both representable.
- A bounded batch calls preparation in input order and stops at the first
  refusal. Cleanup visits every reported obligation once, including the failed
  entry if it owns one. Reverse order is an original design choice, not a claim
  about Apple's private cleanup sequence.
- Each cleanup separately reports whether it released the lease. Unreleased
  leases, tokens and statuses remain available in an UNRESOLVED result. There
  is no automatic retry or discard of unresolved ownership.
- A fully prepared batch can be finished once, after the caller independently
  establishes that the consumer has stopped using its resources. Reentrant API
  calls are refused while callbacks run; the caller provides serialization.

The callbacks must report ownership according to the actual mapping API. All
leases must be independently completable even when another lease remains
unreleased, because cleanup continues after a refusal. Dependent resource graphs
need a separate policy. Preparation callbacks must not expose resources to a
consumer: automatic cleanup on a later preparation failure would otherwise race
that consumer. Consumer publication, cache maintenance, page-table visibility,
bootstrap submission and quiescence remain explicit external responsibilities.

This can serve a future Linux adapter that prepares several firmware mappings
and must retain enough information to clean up partial failure. It does not
provide that native adapter, allocate or map real memory on its own, call a
device, or assert firmware readiness. The bound of 16 entries, tokens, result
enums and callback structures are original software choices, not firmware
limits or shared-memory layouts.

Review found no remaining code-level issue within this contract after clarifying
independent cleanup and the prohibition on consumer exposure during preparation.
The 14 original C groups cover owned and unowned failures, borrowed resources,
mixed unresolved cleanup, preserved opaque statuses/tokens, reentrancy, shared
resources with distinct leases and bounded failure combinations. Integration
execution and complete source closure are recorded by the parent 31T job; these
research findings do not independently claim those runs.

## Linux API comparison

The primary Linux
[DMA mapping guide](https://docs.kernel.org/core-api/dma-api-howto.html#cpu-and-dma-addresses)
distinguishes CPU virtual, CPU physical and DMA/bus addresses. Its
[error-handling examples](https://docs.kernel.org/core-api/dma-api-howto.html#handling-errors)
unwind previously successful mappings when a later mapping fails; the failed
call does not itself establish a valid mapping to unmap. Its
[streaming-mapping rules](https://docs.kernel.org/core-api/dma-api-howto.html#using-streaming-dma-mappings)
also keep unmapping separate from completion of DMA activity. These public
contracts support explicit ownership and consumer-lifetime duties, but do not
translate an Apple status value or qualify this machine's firmware path.

## Evidence boundary

The carrier remains SHA-256
`26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`.
AGXG17X retains SHA-256
`e772f7d8a6197ff54fa3e06b5cc83f8d2019dfb53cdc345b59678ebc4f14339b`.
An ordinary IOGPUFamily member was derived locally using the original bounded
fileset tool, preserving its mapped bytes against the same carrier; its digest
is `4bdf71a84df51736e6f5fd4b064ff232db4093f0d54a3c021a9d84c5bc217593`.
The selected member scope was expanded only in the private invocation; frozen
extraction sources and manifests remain unchanged. No third-party code ran on
macOS. The carrier's match to the currently running kernel remains unverified.

Exact query outcomes, independent symbol bounds, instruction-range hashes,
chained-reference checks and decompiler gates are in the
[validation metadata](../reverse-engineering/findings/gpu31t/validation.json).
Each query has a 100-second timeout and runs only in the existing diskless,
no-network Linux VM under the parent's control. Each batch verifies loopback
only. Apple bytes, disassembly and P-code remain solely in ignored local storage.

All six queries completed in three batches: preparation/completion in
72.254/71.973 seconds, shared allocation/lower preparation in 72.491/47.164
seconds, and allocation/initialization in 72.541/72.247 seconds. Independent
carrier/derivative/Apple LLVM comparison matches **2,935 instruction words in
14 disjoint symbol-bounded ranges**, including 2,601 words in the six query
targets, with zero mismatches. Six selected chained references have verified
chain membership; this is static reference evidence, not runtime pointer
authentication or selection of an object class.

All six standard dossier gates remain `manual_review_required`. All 5,341
retained high P-code operations have addresses inside the independent bounds,
and all six assembly listings cover those bounds. That does not remove the
allocation dossier's truncation or any decompiler warning. The new explicit
whole-high-P-code refusal and the earlier 31Q/31R cross-boundary refusals remain
in force; no software or VM pass overrides them.

An original bounded interpreter additionally checks 127 synthetic mapping paths
and three selected lower-preparation paths. All external effects are callback
stubs; these are sequential instruction-behavior checks, not native execution of
Apple code, concurrency validation or native hardware observations. The selected
lower paths fix their initial flags and callback results. They do not prove
every reachable state or establish a memory-ordering protocol.

The next discriminator remains a qualified G17C consumer/publication contract
and effective provider/address binding. A mapped address, prepared host lease,
software flag or injected callback result supplies none of those by itself.
Firmware ABI, actual cache visibility, runtime UAT layout and observable bounded
firmware completion remain unqualified. No restart, hardware request, boot-policy
change, firmware replay or native performance/energy claim follows from this pass.

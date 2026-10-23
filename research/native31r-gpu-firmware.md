# 31R: firmware attachment is a lifecycle, not payload success

Date: 2026-10-23. **Offline research; native GPU enablement HOLD / NOT RUN.**
This continues after M1's independent 31Q review, published in `bc4d46c`.
The 31Q mapping planner, GPTBAT format codec and earlier frozen evidence remain
unchanged. No Mac restart, device operation, firmware request or policy change
was performed for this investigation.

## Evidence boundary

The retained kernel collection SHA-256 is
`26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`.
The derivatives remain AGXG17X
`e772f7d8a6197ff54fa3e06b5cc83f8d2019dfb53cdc345b59678ebc4f14339b`
and AGXFirmwareKextG17XRTBuddy
`99d95ff5c337a3f6a46368893359c1e6cd861eeed0fa47f398cc8c7280770841`.
Their match to the currently running kernel is not independently established.
All addresses below identify static locations in that retained image.

REA runs in root's existing diskless Linux VM with explicit no-network
configuration. Each query is bounded to 100 seconds and each batch checks that
only loopback exists. Apple LLVM independently decodes symbol-bounded ranges;
the encoded words match both the derivative and original carrier. Direct external
callee names are checked against the carrier symbol table, avoiding misleading
nearest-symbol labels in an extracted member. Apple bytes, disassembly and
P-code remain in ignored local build storage. Only behavior and validation
metadata are published.

## Provider attachment and endpoint lifetime

**Confirmed static behavior:** provider `bootFirmware` at
`0xfffffe00088f9920` consults `RTBuddyService::iBootLoaded`. Its true path cannot
reach the `RTBuddyService::loadFirmware` call in this routine; the false path
can. This establishes a distinction between attaching to a reported preloaded
instance and a loading-capable path. It does not observe which path this Mac
takes, who owns the firmware memory, or whether that firmware is ready.

This strengthens, without changing, the 31Q result: the admitted provider's
null payload and length 8 are interface output, not an eight-byte image and
not a preload attestation. The consumer's no-copy success remains separate from
the boot provider's preload predicate. The Release label remains a build flavor,
not a numeric firmware ABI.

The boot provider reads a `role` property and forms two endpoint service names
with the suffixes `Endpoint1` and `Endpoint2`. It registers match and termination
notifications for each, then records that subscriptions were installed. That
flag does not establish that either callback fired. The checked routine does not
establish that callbacks can only arrive after the flag is written, so an
original event model must allow callbacks during subscription installation.

The separately bounded gated callbacks distinguish endpoint selectors `0x20`
and `0x21`. Matching selector `0x20` stores an endpoint and performs separate
`RTBuddyEndpoint::initForOwner` initialization; failure clears the attachment.
A match observation therefore cannot be promoted to accepted attachment without
separate evidence. This pass does not establish that selector `0x21` has the
same owner-initialization contract.

The termination callback clears the stored slot selected by `0x20` or `0x21`.
Independent synthetic evaluation of its bounded selector dispatch covers
0, 1, 31, 32, 33, 34, 255 and UINT32_MAX: the two admitted selectors clear separate
slots and those tested unsupported selectors write neither slot. This is
instruction-behavior validation using synthetic object memory, not execution
on the GPU or a callable driver adapter.

Three namespaces remain distinct: provider request roles 0/1, endpoint selectors
`0x20`/`0x21`, and ADT roles GFX/GFX1. The present evidence does not map them to
one another. Endpoint suffixes 1/2 do not supply that mapping. Earlier
cross-role descriptor overlaps remain meaningful, and merging both address
spaces remains unjustified.

## MMU and shared-data limits

The secure-monitor `setupMMUConfig` at `0xfffffe0008988f58` contains device
configuration activity: the bounded routine has 13 static register-read helper
callsites and 12 register-write helper callsites. This is not a proposed replay
sequence. The routine itself does not resolve an ownership-property binding,
qualify a CPU physical address, or establish G17C firmware page-table contents.
The 31Q GPTBAT encoding result supplies none of those missing facts.

`initFirmwareSharedData` at `0xfffffe000895fc04` initializes two distinct record
objects using both common and different inputs. Three corresponding fields are
populated through the same indirect helper from the same source-object
references. A further corresponding field uses a different source object for
each record, and their scalar state storage is separate. This supports retaining
both shared resources and per-record lifetime in an original model. It does not
identify either record with an ADT role or establish that helper results are
CPU physical addresses. The indirect helper's selected implementation, publication
and firmware consumption remain unresolved; this pass publishes no wire layout.

## Original implementation contract

The useful implementation is an offline lifecycle reducer that records evidence
and invalidates it when an instance ends. Its state distinguishes payload result,
observed preload, completed subscription registration, endpoint match, and
explicit endpoint acceptance. A new provider incarnation resets all of those
observations. Endpoint replacement clears its previous acceptance; explicit
initialization rejection and termination clear only the corresponding attachment.
Provider termination clears both.

Provider epochs, observation sequence numbers, local slots and opaque instance
tokens are **original bookkeeping**, not Apple protocol fields. Monotonic sequence
checks prevent stale record replay; instance tokens let delayed acceptance or
termination observations leave a newer attachment intact. Tokens must not be
reused within a provider epoch. A new match intentionally denotes replacement;
the caller supplies causal ordering for match events. Rejected input must leave
the state unchanged. Callback observations may precede the final subscription
flag. Neither a match nor payload success implicitly asserts acceptance.

This reducer is useful for deterministic trace ingestion and later transport
adapter tests, including replacement, termination, delayed callbacks and provider
restart. It emits no MMIO, firmware message, image loading, queue submission or
address translation. Its `native_ready` result remains false even when both local
slots have accepted attachments. A native adapter still needs qualified selector
binding, firmware ABI, address domain, ownership, shared-data publication and a
bounded observable completion. See the original
[lifecycle interface](../kernel/experiments/gpu31r/lifecycle.h).

## Current public implementations are comparison evidence

The hash-checked Aurora Mesa source at
[`bd4290a`](https://github.com/aurora-silicon/mesa/blob/bd4290aef2b0f68afb3dd508a527fdaf0729b196/src/asahi/lib/agx_chip.h)
admits G17G and G17S in its M5-family helper; that helper excludes G17C.
The pinned Aurora Linux driver remains a separately qualified source, not a
T6050/G17C binding inferred from a family name. No fresh public code was executed
on macOS in this investigation.

The pinned
[SPTM boot-handoff research](https://github.com/niklassheth/bootloader/blob/98412d670862a6d1cd29c5e8f33439839ae3c7e6/src/hv_sptm_boot.c)
reads distinct address-space-management, global-root and handoff properties.
Its accompanying
[UAT model](https://github.com/niklassheth/bootloader/blob/98412d670862a6d1cd29c5e8f33439839ae3c7e6/src/hv_sptm_uat.c)
is useful public comparison material for ownership and publication questions.
It is research/emulation evidence, not a qualified native initialization profile
for this machine. Property presence, integer fit and source-level support labels
must not automatically enable native hardware.

## Verification and next discriminator

The companion [validation record](../reverse-engineering/findings/gpu31r/validation.json)
lists bounded ranges, original-carrier hashes, query outcomes and retained gates.
Independent instruction checks cover 1,233 words in seven disjoint ranges:
1,020 words for the three requested targets and 213 words for the endpoint
callbacks and gated helpers. Derivative/carrier and LLVM word mismatches are zero.
All three REA queries completed, in 22.972, 73.311 and 71.596 seconds respectively;
none reached its 100-second deadline. Both batches verified loopback only. The
three provider property/endpoint-name anchors also match the carrier.

The provider dossier's whole-function gate is `rejected_cross_boundary`: 58 of
its 1,304 high P-code operations lie outside the symbol-bounded routine.
Unresolved-jump and removed-block warnings are retained. These operations are
excluded; the refusal is not overridden by query completion or by the independent
instruction checks. The provider findings above use only bounded, independently
checked behavior. A `manual_review_required` gate on another dossier is likewise
not a semantic or runtime acceptance result. The MMU and shared-data dossiers
receive that gate, with 293 and 224 P-code operations respectively, all inside
their independent ranges. No dossier reports truncated high P-code. All three
assembly listings cover their symbol-bounded ranges. The 31Q refusals remain
unchanged in their original records.

Next work should resolve actual runtime handoff metadata, establish a mapping
between the separate role namespaces, qualify shared-data publication and its
consumer, and identify an observable bounded endpoint/queue completion. The
matched callback's endpoint owner initialization and `enableEndpoints` are narrow
follow-up static targets. Native G17C initialization, rendering, performance and
energy remain unmeasured. No restart follows from this checkpoint.

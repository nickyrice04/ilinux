# 31S: a bounded GPU bootstrap word and injected transport contract

Date: 2026-10-23. **Offline implementation; native G17C HOLD / NOT RUN.**
This consumes M1's independent 31R review, published in `ff1ed8e`: 420 source
pins, 176 Python methods and 60 portable C groups passed, with no native
operations. That review correctly separates software evidence from firmware
initialization. The 31R lifecycle component and all earlier frozen records
remain unchanged.

## New result and its boundary

**Confirmed static format:** `AGXArmFirmware::notifyFirmwareStarted`, retained
address `0xfffffe0008957928`, forms a 64-bit bootstrap word with this layout:

| Bits | Meaning established by this pass |
|---|---|
| 63–48 | Fixed full header `0x0081` |
| 47–44 | Zero |
| 43–0 | Address field populated from the conversion result |

Equivalently, the fixed word portion is `0x0081000000000000`, with a 44-bit
address field. This is a message representation, not a GPU page-table format or
physical-address width. The retained operation inserts the low 44 bits; the
original implementation **rejects values at or above 2^44** instead of silently
discarding bits. Zero and unaligned values fit the representation, but fit does
not make an address valid for firmware use.

The checked call reaches the provider's `sendMessageToFirmware` interface through
a statically resolved vtable entry. Its wrapper preserves the supplied word for
the gated send path. That path uses the endpoint slot that 31R independently
associated with selector `0x20`. The selector belongs to the transport; it is
not embedded into the bootstrap word's address or header bits. This establishes
enough structure for an original strict codec and a transport adapter with an
injected callback. It does not establish a usable native endpoint on this Mac.

## Owner binding and enablement are separate operations

The exact `RTBuddyEndpoint::initForOwner` callee at `0xfffffe000ae82f8c` stores
the owner, callback and context, then unconditionally returns success. Its five
instructions contain no allocation, transport request or firmware handshake.
This narrows 31R's interpretation: the caller's failure branch exists, but this
retained direct callee supplies no negative return path or device acceptance
test. The original 31R ACCEPT/REJECT events remain defensive evidence vocabulary;
they are not an assertion that Apple firmware accepted initialization.

Provider `enableEndpoints` at `0xfffffe00088fa1b8` calls the enable entry on both
stored endpoint objects, followed by a separate callback through its accelerator
context. The retained `RTBuddyEndpoint` vtable entry resolves to
`IOSlaveEndpoint::enable`. No hardware readiness result is inferred from these
calls. The selected runtime subclass, transport internals and accelerator
callback contract remain unobserved here.

`AGXArmFirmware::bootFirmware` at `0xfffffe000896d518` remains a distinct provider
boot/wait path. Its successful static analysis does not make the later bootstrap
word a complete firmware initialization sequence. Shared-data construction,
address ownership, cache publication and observable completion remain separate
requirements.

## Address conversion and send-path qualifications

The retained `AGXArmFirmwareASC` vtable resolves its address-conversion entry to
`AGXArmFirmware::convertGPUVAToFWVA` at `0xfffffe000896bab0`. That particular
three-instruction method returns its address argument unchanged. The abstract
`AGXFirmware` table has a different entry. This is a class-specific static fact,
not evidence that CPU physical addresses, descriptor addresses and GPU virtual
addresses are interchangeable, or that this runtime follows that class path.

The provider's gated send at `0xfffffe00088f9718` passes the message buffer, a
null second buffer and a true Boolean argument to the statically resolved
`RTBuddyEndpoint::sendMessage` entry. The Boolean's operational meaning and
borrowed-buffer lifetime are not qualified by this pass. The original adapter
therefore uses a word passed by value and preserves the injected transport's
status as opaque data. It does not copy Apple's pointer or locking interface.

Endpoint selector `0x20`, provider request roles 0/1, and ADT names GFX/GFX1
remain separate namespaces. No mapping to a physical controller or either ADT
role is supplied. The same numeric endpoint can belong to a different provider
instance; a correct provider binding is still a caller/native-adapter duty.

## Receive classification is deliberately weaker than message validation

The bounded `AGXArmFirmware::receivedMessageFromAKF` routine at
`0xfffffe0008957c70` extracts **bits 48–53**, a six-bit discriminator, and
distinguishes numeric cases 2 and 9. The implemented classifier retains the
entire 64-bit word and labels only CASE_2, CASE_9 or OTHER. It does not label a
case as acknowledgment, boot completion, a valid queue event or readiness.

This distinction matters when comparing public implementations. The pinned
[m1n1 protocol definitions](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/proxyclient/m1n1/fw/agx/__init__.py#L12-L66)
use full 16-bit type `0x42` for a channel-poll notification. The pinned
[Gravity Linux receive handler](https://github.com/GravityLinux/linux/blob/4fc326f6c25ccceb7515e2635c22e01fde5d3bac/drivers/gpu/drm/asahi/gpu.rs#L361-L367)
requires endpoint `0x20` and the **entire word** `0x0042000000000000`.
Although the low six bits of `0x42` equal 2, neither public implementation
corroborates accepting every word with discriminator 2. No corresponding mailbox
case 9 was found in those checked sources. A channel-record type with the same
number belongs to another layer and cannot supply its meaning.

## Public corroboration and publication requirements

The m1n1 definitions independently state the same outgoing header, zero gap and
44-bit address field, and assign firmware to endpoint `0x20` and doorbells to
`0x21`. Its [ASC layer](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/proxyclient/m1n1/fw/asc/base.py#L14-L50)
keeps endpoint selection in a separate transport word. These are public
protocol comparisons, not new mappings between this machine's two ASC roles.

The pinned Gravity Linux
[firmware manager constants](https://github.com/GravityLinux/linux/blob/4fc326f6c25ccceb7515e2635c22e01fde5d3bac/drivers/gpu/drm/asahi/gpu.rs#L90-L108)
and [startup path](https://github.com/GravityLinux/linux/blob/4fc326f6c25ccceb7515e2635c22e01fde5d3bac/drivers/gpu/drm/asahi/gpu.rs#L1253-L1263)
also describe the outgoing format and endpoint. The
[m1n1 startup sequence](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/proxyclient/m1n1/agx/__init__.py#L357-L384)
constructs initialization data and flushes UAT before sending its address.
That explicit separation supports keeping publication outside the word codec.
It does not qualify G17C cache operations or justify copying an older startup
sequence into a native driver.

The m1n1 files were checked against commit
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`, excluding unrelated checkout changes.
Gravity Linux commit `4fc326f6c25ccceb7515e2635c22e01fde5d3bac` was read from the
retained archive after rechecking SHA-256
`045c64540fa4210394c899cad6320c5bf9090a66919938d986aeaad0033946e8`.
Exact file hashes and line ranges are in the validation record. The two projects
share implementation lineage; this is public-source corroboration, not two
independent hardware observations. No third-party source executed on macOS.
Neither source establishes G17C runtime compatibility or a matching firmware ABI.

## Original component and review

The original [bootstrap interface](../kernel/experiments/gpu31s/bootstrap.h) and
[implementation](../kernel/experiments/gpu31s/bootstrap.c) provide:

- A distinct firmware-address type, strict width validation and full-header
  encode/decode, with unchanged output on refusal.
- A raw-preserving six-bit receive classifier that asserts no message semantics.
- A submission adapter requiring an explicit selector-`0x20` binding and an
  injected callback. It validates first, invokes the callback once with the
  word by value, and preserves the callback's status without retry.

The caller owns address conversion, provider identity, attachment, serialization
and lifetime. Callback failure does not prove the device received nothing.
Adapter success means the callback was invoked, not that firmware booted.
No byte-wire ordering, implicit alignment, page-table publication, controller
selection, MMIO, wait loop or readiness promotion is implemented.

Review of the original C and its 14 test groups found no remaining actionable
issue in this scope. Tests include 10,000 valid-address roundtrips, malformed
headers and oversized-address refusals, all 65,536 combinations of the upper
16 receive bits, and exact-once/zero-on-refusal mock transport checks. Execution
results and the complete source closure belong to the 31S integration record;
the research findings do not independently claim a native test.

## Evidence and next discriminator

The retained carrier SHA-256 is
`26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`.
The AGXG17X, AGXFirmwareKextG17XRTBuddy and RTBuddy derivatives and all exact
ranges are pinned in the
[validation metadata](../reverse-engineering/findings/gpu31s/validation.json).
Their match to the currently running kernel remains unverified.

Six REA queries completed in three batches. Each query had a 100-second bound;
each batch verified loopback only in the existing diskless, no-network Linux VM.
Independent Apple LLVM/carrier checks cover **644 instruction words in 12
disjoint symbol-bounded ranges**, including 490 words in the six query targets.
There are zero derivative/carrier or LLVM word mismatches. Eight selected
collection references have verified chain membership; five callsite
discriminators match their static reference metadata. This is not runtime
pointer authentication or proof of the selected object classes.

All six standard dossier gates remain `manual_review_required`. All 425 high
P-code operations are inside the independently established function bounds;
none reports truncation. Removed-block and unresolved-indirect-jump warnings
remain explicit. Query completion does not override them. All six assembly
listings cover their symbol-bounded ranges. The earlier 31Q/31R whole-function
refusals remain intact in their frozen records. Apple bytes, disassembly and
P-code remain solely in ignored local build storage.

The next discriminator is the actual G17C provider/address binding and the
publication/consumer contract for the structure named by the bootstrap word.
Qualified cache publication and a bounded observable reply are still needed
before a native transport can use this codec. This pass supplies a concrete
message component, not an initialization profile. Native GPU acceleration,
Linux SMP, performance and energy improvements remain unmeasured. No restart,
hardware operation, boot-policy change or firmware replay occurred.

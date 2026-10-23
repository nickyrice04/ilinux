# 31Q: G17C firmware handoff and address-format evidence

Date: 2026-10-23. **Offline research; native GPU enablement HOLD / NOT RUN.**
This follows the independent M1 31P review on `311473c`, published in `5058916`.
That review reproduced the 379-source closure, 122 Python methods and 12 C test
groups. It did not qualify a GPU firmware address, native queue, or CPU startup.

## Inputs and scope

The authorized, retained kernel collection has SHA-256
`26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`.
The two analysis derivatives are `AGXG17X` (`e772f7d8a6197ff54fa3e06b5cc83f8d2019dfb53cdc345b59678ebc4f14339b`)
and `AGXFirmwareKextG17XRTBuddy`
(`99d95ff5c337a3f6a46368893359c1e6cd861eeed0fa47f398cc8c7280770841`).
These are static analysis inputs, not executable Linux payloads. Function
addresses in this note are retained-image analysis locations, not live pointers. Derivative
metadata repairs do not resolve all collection fixups or external virtual calls.
The retained carrier's identity is pinned; its match to the currently running
macOS kernel was not independently established in this work.

REA/Ghidra analysis runs only in the existing isolated Linux lab. Apple LLVM
independently decodes selected instruction ranges; their encoded words are
compared with both the derivative and the original carrier. Apple bytes,
assembly and pseudocode remain in ignored private build storage. This document
records externally useful behavior and limits, not Apple implementation code.
The machine's retained sanitized ADT is the unchanged 31P input, not a fresh
hardware observation.

## GPTBAT base representation

**Confirmed static format:** the matching AGXG17X `readGPTBATBaseAddress`
accessor at `0xfffffe000898969c` uses a 32-bit page-number result and 16 KiB units.
The represented base occupies at most 46 bits, with its low 14 bits zero. The
accessor's register selector is `0x00d0802c`; this is an analysis fact, not an
approved live address or a new MMIO operation. The selected read implementation,
actual register contents and runtime class selection remain unobserved here.

This yields a bounded original software component: a distinct page-number type
and a distinct GPTBAT-base type, checked lossless conversion, and boundary tests.
The format permits zero; zero alone proves neither a valid table nor readiness.
The inverse conversion is an original validation convenience, not an observed
Apple write routine. It must reject unaligned bases and values at or above
2^46 rather than truncate them. This component does not generate a GPU PTE or
publish a table to hardware.

**Address domains remain separate.** The 31P descriptor addresses need 41 bits,
but that numerical fit does not make them GPTBAT bases, CPU physical addresses,
or DRM GPU virtual addresses. No implicit conversion, mask, subtraction or
reservation is justified by this accessor. The original planner and this codec
must not accept each other's values merely because they fit an integer width.

## Firmware mapping dispatch does not establish physical identity

`AGXArmFirmwareMapper::mapToPhysicalAddress` at `0xfffffe0008978330` first obtains
its accelerator context and selects between IOUAT and the legacy translator.
The requested address is forwarded to the selected object's translation method.
The wrapper does not implement an identity mapping, and this pass does not
resolve the translation result for any retained descriptor.

The legacy `getFirmwareAddressSpaceHandle` at `0xfffffe00089d913c` caches one
firmware translator handle and does not use the supplied role to select among
handles. **This is a statement about that legacy function only.** It does not
prove that GFX and GFX1 universally share all address mappings, that the legacy
path runs on this machine, or that the IOUAT path behaves identically. The 31P
role-specific range validation and three reported cross-role overlaps remain
appropriate; merging both role namespaces would be premature.

## The provider is a handoff interface, not an embedded firmware image

The older `gpu-g17` note describes the firmware provider as containing two
functions. The retained symbol map actually exposes substantially more provider
methods, including the actual request and version accessors. The old note is
preserved; this is a correction to its analysis coverage.

`AGXG17X::requestFirmwareBinary` at `0xfffffe0008980800` forwards the request and
role to the provider. The actual `AGXFirmwareKextG17RTBuddy` provider at
`0xfffffe00088f8738` accepts two role values for its admitted configurations and
returns success with a null payload pointer and a length field of 8. Runtime
selection of an admitted configuration was not observed, and this pass does not
map numeric roles 0/1 to the GFX/GFX1 device-tree names. These are
interface results, **not eight bytes of embedded firmware**. Unsupported role or
configuration cases do not take the success path.

`AGXArmFirmware::loadFirmwareBinary` at `0xfffffe000896d768` treats a null payload
as success without copying or allocating a firmware image. This independent
consumer observation supports interpreting the provider result as a no-copy
handoff path. It does not by itself prove where firmware is loaded, its ownership,
its readiness, or a complete Linux initialization sequence.

The provider's `getVersion` at `0xfffffe00088f845c` selects a static **Release**
build-flavor label for its admitted role/configuration combinations. That label
is not a numeric firmware ABI. The older note's linkage of this method to an
actual iBoot-loaded version is not supported by these checked instructions.
The fatal iBoot-load check mentioned in that note is not a substitute for
tracing the runtime metadata consumer. **The matching firmware ABI remains
UNKNOWN**, and macOS release numbers must not populate a Linux ABI selector.

Engineering consequence: do not manufacture a firmware blob from these provider
outputs, copy the macOS provider into Linux, or implement a reload just because
an API is named `requestFirmwareBinary`. The next firmware task is to trace the
runtime payload/metadata handoff and separate role-specific shared structures,
then establish ownership and cache publication before any queue submission.

## Public Linux comparison

The pinned Gravity Linux source
[`4fc326f6c25ccceb7515e2635c22e01fde5d3bac`](https://github.com/GravityLinux/linux/tree/4fc326f6c25ccceb7515e2635c22e01fde5d3bac/drivers/gpu/drm/asahi)
was inspected from the retained archive after its recorded hash was checked.
No downloaded source executed on macOS. In `g16_vm.rs`, firmware bootstrap page
tables are attached separately from client roots; mappings have ownership and
publication lifetimes. That separation is relevant architecture to preserve in
original Linux work. It is not proof that G17C can reuse G16 tables unchanged.

The pinned `m4_pgtable.rs` describes 42-bit G16 input addresses versus 39-bit
G13/G14 input addresses. These are GPU virtual address widths, not the width of
the GPTBAT base encoding identified above. The M4 driver still binds T8132,
not T6050. Neither the page-number conversion nor the prior 396 Mesa tests
supplies a G17C device binding, compatible firmware structures, or native render.

## Validation and next discriminator

**Completed:** five fresh REA function queries, three earlier queries cancelled
at their 70-second bounds, and one initial environment refusal before any query
because the query share was not mounted. Successful retries use 100-second query
bounds. Every executed query batch verified that its guest exposed only loopback;
root's launcher used explicit `--no-net`. No target hardware or device discovery
occurred.

Independent checks cover **489 instruction words / 1,956 bytes in seven disjoint
symbol-bounded ranges**, with zero derivative/carrier or LLVM-word mismatches.
Four eight-byte static flavor-label anchors also match the original carrier.
Five completed REA requests correspond to 376 independently checked instruction
words; the other 113 words are the legacy-handle and delegating-wrapper routines,
checked through LLVM only. Query completion does not mean whole-function
pseudocode admission. The five dossiers contain 611 high P-code operations;
248 fall outside the independently established requested-function ranges and
are excluded from behavioral evidence.

The companion [validation metadata](../reverse-engineering/findings/gpu31q/validation.json)
records exact function ranges, word counts, hashes, REA outcomes and retained
refusals. REA outputs are hypotheses until independently checked, and static
findings are distinct from native behavior. In the GPTBAT dossier, REA
underreports the function body and assembly as the four-byte entry instruction,
although its high P-code reaches the complete routine and contains the mask/shift
operation. Independent symbol-bounded LLVM/carrier checks supply the full
instruction coverage; the truncated listing is not counted as complete coverage.
The unchanged standard `check_evidence.py` gate rejects whole-function pseudocode
for that dossier as `rejected_cross_boundary`. That refusal stands. The format
claim instead rests on independently checked instruction behavior, corroborated
by high P-code whose addresses fit the independently established symbol range.
A read-only review of REA's bridge confirms that reported body/listing coverage
comes from Ghidra's function AddressSet, separately from decompilation. The cause
of this specific one-instruction AddressSet is not established; no REA or Ghidra
source/database was patched to force acceptance.

The provider request and version dossiers also receive
`rejected_cross_boundary`: unresolved failure-call behavior lets the decompiler
continue into neighboring methods. Only their independently checked, bounded
success paths inform the findings above. The mapper and null-payload consumer
have consistent reported bounds and still require manual semantic review;
unresolved indirect calls are not treated as resolved by a successful exit code. Original code and synthetic tests
are recorded by the 31Q integration package; no native result is claimed here.

The next bounded static questions are specific:

| Target | Question | Original Linux work it could enable |
|---|---|---|
| Provider `bootFirmware`, `0xfffffe00088f9920` | How is an existing firmware instance attached and which per-role handoff object is required? | Separate attach-state validation from payload loading; bounded endpoint initialization |
| G17 secure-monitor `setupMMUConfig`, `0xfffffe0008988f58` | Which property selects address-space ownership and which table representation is consumed? | Correct boot-handoff validation and a domain-aware page-table interface |
| `initFirmwareSharedData`, `0xfffffe000895fc04` | Which shared structures are role-local and what publication/completion fields exist? | Original typed layouts and synthetic serialization tests, followed by a reviewed bounded queue test |

These are proposed analysis targets, not completed REA results or callable native
operations. Previous informal notes about their structure sizes need the same
independent instruction and data validation before becoming implementation inputs.

A useful next hardware test still needs a qualified firmware owner, a usable
address domain, matching shared-data/queue semantics and an observable bounded
completion. None is supplied by changing a GPU compatible string. Continue the
runtime handoff and page-table/queue investigation offline; **do not restart for
this checkpoint**. macOS, boot policy, volumes, installed lab image and prior
consumed attempt receipts remain unchanged. G17C acceleration and performance/
energy parity remain unmeasured.

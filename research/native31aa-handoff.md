# 31AA — bounded helper, fixup and dispatch qualification

Completed REA on2026-10-24; independently checked and published2026-10-25.

**A minimal original monitor bridge does not inherently require decoding the
entire848-byte record or initializing every XNU helper.** The checked helper
initializes local scalar state; fixed bootstrap dispatch has a separate transport.
The local image path also supports absence of chained-fixup work. These results
narrow the bridge's dependencies, without establishing accepted image placement,
all permitted entry states or a working exception-return continuation.

This is a supplement to the frozen [31Z local finding](native31z-handoff.md) and
[31AA public contract](native31aa-public-contract.md). The committed registration
planner and its tests are unchanged. No new VM query, native operation, restart,
installation, security change or external contact occurred after resuming this
publication work.

## Evidence and retained refusal

The retained standalone T6050 kernel remains17,168,528bytes, SHA256
`2bd94a6fcff6203861e46b39920c16e1b5563d9bb17405b8a42c59c2ef4486e0`.
31Z independently matched it to the installed25G83 kernel, whose build metadata
identifies XNU12377.161.14. That provenance is carried forward; this pass does not
refresh installed or historical lab boot-chain identity.

The new analysis-only carrier preserves original addresses and file offsets for
33,180 copied bytes in two ranges. Its SHA256 is
`68e10ccfd2a55e30a16e41785a1b3686ede7776be9d61584dedd9ee40aa534e1`.
Every copied byte matches the source. Generated metadata and analysis labels are
not original metadata; most code and all original data are omitted. The carrier
is not an executable or deployable host image.

| Fresh query | Actual result | Permitted use |
| --- | --- | --- |
| Helper initializer `0xfffffe0007c78324` | CLI0,16.885s;412bytes/103 instructions;186 P-code operations; no truncation, outside-body operations or reported warnings. | Exact body and independently checked field accesses. Whole-function pseudocode was not used. |
| Image helper `0xfffffe0007ca4488` | CLI0,16.854s;1,452bytes/363 instructions;541 P-code operations,42 outside its body, removed-block warning; no truncation. | **Whole-function pseudocode refused.** Only independently checked instruction facts and the specific no-chain edge below are used. |

The root-owned VM's setup and job both exited0; the guest exposed only loopback
and no physical USB. An earlier sandbox refusal occurred before guest queries
and is retained separately. It is not a third REA request. No query was retried.

Independent LLVM/source comparisons cover **551 instruction-sized words /
2,204bytes across seven bounded ranges, zero mismatches**. This includes14 words
already checked in31Z; they are reverified dependencies, not additional startup
progress. Six ranges match complete source function-start spans; the seventh is
the four-word direct fixups-completion boundary. The queried bodies account for
466 of those words. Equality of words does not repair the rejected decompilation
or qualify unexamined callees. Mappings, bounds and hashes are retained in the
[validation record](../reverse-engineering/findings/cpu-startup31aa/validation.json).

## Helper initialization is a local utility

**Confirmed, bounded local behavior:** the initializer receives the subobject
at monitor-record+416 previously established in31Z. It reads a32-bit version at
subobject+0 and forwards selected fields into local globals. Its exact body has
no call to another function and no monitor transition. A null argument returns2;
the checked non-null paths return0. This result is a local utility result, not
monitor acceptance or CPU-start evidence.

Later fields are consumed at version thresholds3 through10. The greatest accessed
field ends at byte224. Selected widths and positions agree with the measured
SDK26.5 helper: that comparator has a312-byte object, with reserved storage after
byte224. The incoming runtime version is not observed. The initializer does not
establish the mapping, validity or lifetime of the tables referenced by its
fields, and this comparison does not identify the unmatched outer848-byte layout.

**Implementation consequence:** an original host may omit unused helper services.
If it uses a service, it must qualify the consumed fields and referenced objects;
copying opaque bytes alone does not provide that qualification. This finding does
not supply a recipe to construct or replay monitor-owned state.

## An image may have no chained-fixup work

The independently checked local command scan recognizes the public
`LC_DYLD_CHAINED_FIXUPS` kind at `0xfffffe0007ca45fc` and captures its command
pointer at `0xfffffe0007ca45d0`. The absent state is initialized at
`0xfffffe0007ca4540`. Its zero test at `0xfffffe0007ca47c4` branches to
`0xfffffe0007ca4960`, skipping the chained-fixup walk. This narrow edge agrees
with Apple's public no-command case; it does not depend on the refused
whole-function pseudocode.

**Qualified design candidate:** build an original early image whose actual code
and data references require no runtime chained relocation or pointer signing,
then audit those properties. Merely deleting a load command cannot establish
them. The surrounding image/collection context and actual placement still need
qualification. The public wrapper also handles collection address metadata;
the absence of chain work does not erase those obligations.

In particular, empty fixup work does not remove the final vector-base,
synchronization and fixups-completion protocol. Nor does it turn31Y's successful
read-only property derivation into firmware acceptance. The public format and
image-context distinctions are detailed in the frozen
[31AA comparison](native31aa-public-contract.md).

## Fixed dispatch has different dependencies from XNU hooks

The local registration14 and exception-return registration18 stubs select fixed
dispatch identifiers. Their transfer words, and the direct cold-entry transfer15,
exactly match the pinned public GENTER encoding. LLVM renders these words unknown;
the architectural name comes from the independent public/header comparator, not
an invented disassembly interpretation.
[Public encoding](https://github.com/AsahiLinux/m1n1/blob/51b747dced07a58eacf5dabc31ed6f00bcfa20fd/src/gxf_asm.S#L7).

The40-byte registration and exception-registration stubs call the same small
before/after helpers at `0xfffffe00072f68e8` and `0xfffffe00072f6954`. Their local
bodies use thread/preemption context and interrupt state, with null-thread paths;
they do not directly read the helper-state globals initialized above. The public
XNU hooks identify this bookkeeping and the guarded-state entry check. Their
optional scheduler work is an XNU dependency, not a portable scheduler supplied
to an original host.
[Public hooks](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/locore.s#L2681),
[guarded-state register definition](https://github.com/AsahiLinux/m1n1/blob/51b747dced07a58eacf5dabc31ed6f00bcfa20fd/src/cpu_regs.h#L707).

The already checked cold path performs direct fixups completion before entering
the C consumer and before helper initialization. Together with the SDK's static
dispatch declaration, this excludes helper initialization as a universal
precondition of every fixed bootstrap call. It does **not** qualify calling an
XNU wrapper with arbitrary thread state, borrowing its exception continuation,
or inventing a transport success value. These bootstrap APIs are void.

## Concrete next integration boundary

The [original registration planner](../kernel/experiments/sptm31aa-adapter/README.md)
already prepares ordered arguments offline. This research adds no native wrapper,
controller or image, and makes no new synthetic-test claim.

The next bounded bridge must establish its actual entry exception level and
guarded state, preserved/clobbered registers, readable argument buffers, owned
stack and executable vector region, then the exception-return behavior for every
reachable monitor path. An original image can minimize these dependencies, but
must prove which ones it omits. A pointer registered as an exception continuation
does not itself implement that continuation. Physical secondary entry and release
remain a later, distinct qualification.

**Unknown:** no matching producer or complete848-byte layout was recovered; no
resident monitor or accepted original host image was observed. Those unknowns
must be scoped to fields and services actually used, not imposed as a blanket
whole-record decoding gate. No native boot is ready, and neither a working CPU
workaround nor Apple-only necessity is established.

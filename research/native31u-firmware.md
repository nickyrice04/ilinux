# 31U: raw entry versus the SPTM-named object path

2026-10-23. **Offline evidence; native31U HOLD / NOT RUN.** M1's31T review
passed458 pins,216 Python methods and88 C groups; no native readiness follows.
CPU1's effective entry and protection state remain unknown.

The retained firmware distinguishes raw entry preparation from an optional-object
path before common handoff. This pass identifies the exact SPTM-named record used
by a range accessor and connects that identity to the alternate entry context
bounded in31L. It does **not** find a missing reset-release operation, prove which
path the historical boot took, or establish that firmware makes Linux SMP
impossible. No workaround is qualified.

## The comparison and its first divergence

The following combines new bounded checks with the frozen
[31L entry trace](native31l-entry.md), [31P property/loading trace](native31p-firmware.md)
and [31Q raw serializer/fallback trace](native31q-firmware.md). It describes
conditional software behavior, not observed execution of either whole path.

| Stage | Raw-associated path | Optional-object path | Evidence boundary |
|---|---|---|---|
| Accepted image descriptor | The current raw serializer omits `kcbz`; recorded installation arguments were raw entry2048/base0. | In the primary caller, descriptor-present equal to1 and nonzero selector `+0x38` gate additional-object loading before common image preparation. | `kcbz` feeds `+0x38`; historical accepted properties and historical serializer hash were not captured. Current raw applicability is inferred. |
| Entry source | Producer A derives its entry from descriptor `+0xa0` and relocation/translation context. | Producer B derives the shared entry from a selected subobject. The subobject location identified in31L is the record beginning with `SPTM`. | B's runtime context and field values remain unobserved; naming a static record does not establish a resident monitor. |
| Range preparation | Three16KiB fallback views come from a separate48KiB allocation. | The fresh accessor directly addresses the SPTM-named record and checks object metadata before publishing its range outputs. | The shared consumer invokes object and fallback helpers. These inputs are not interchangeable; checked software setup does not reveal effective CPU1 permissions. |
| Reset entry consumption | The shared entry global is consumed by the established per-core vector programmer. | The same consumer can therefore receive an entry from the other context. | A different entry source is externally relevant, but neither producer proves CPU1's first fetch. |

The **first checked software divergence** is conditional additional-object loading
in the primary caller at `0x100c1aa5de0`, before common image preparation. The
**externally relevant downstream distinction** is the source of the shared entry
and range metadata. The range setup occurs before the checked vector operation.
The trace does not identify a separate omitted CPU1 release store on the raw
path. It also does not establish that the optional path would accept ordinary
m1n1 or satisfy its MMU, exception-level and monitor interface requirements.

## New bounded evidence

The decoded generic image contains an exact NUL-terminated `TXM` name at
`0x100c1eb3958` and `SPTM` at `0x100c1eb3a98`, separated by `0x140`. This is the
precise selected-subobject address already identified by31L, rather than a
nearby string used to assign a name by proximity. The new identity check does
not independently reconstruct every runtime write that initializes that context.

The new range accessor at `0x100c1ca6da4` obtains its record-table base through
`0x100c1ca7688` and directly addresses the SPTM record. Bounded field inventory
identifies record offsets `+0x10`, `+0x18`, `+0x20` and `+0x68`. The checked
zero-presence edge returns without writing its output fields. No direct system
register or supervisor/hypervisor/secure-service operation occurs in this
accessor. It is an object-range query, not a CPU-start operation. Its caller is
`0x100c1aec864` inside the already identified handoff range consumer.

A second fresh query covers layout helper `0x100c1ca7268`, called by both the
alternate preparation path and the range consumer at `0x100c1aec8c8`. REA reports
114 instructions but only2 high-P-code operations and **provider-removed blocks**.
Whole-function semantic inference from that output is refused. Independently
matching its instruction words does not repair that limitation. No claim about
its complete layout transformation or CPU1's state is derived from its pseudocode.

These facts narrow the missing-prerequisite hypothesis: raw and optional-object
handoffs have different software entry/range inputs. They do not show that the
raw input is defective, that a protection setting caused the failure, or that
replaying the other path would work. No descriptor mutation, monitor replay,
range-register mutation or protection bypass is proposed.

## Finite decision tree

1. **Is the historical accepted descriptor available as already retained,
   non-personal metadata?** It is not in the present evidence. The retained
   boot021 payload still matches its campaign hash, but payload bytes and raw
   installation arguments cannot recover the enclosing accepted properties.
   Do not access personalized policy objects. The minimum useful static record
   is the accepted selector's presence/value, entry-offset/load-base metadata,
   and their exact image/producer provenance. Without it, retain the raw-path
   inference and stop this branch; another unchanged marker boot or adjacent
   helper query would not resolve it.
2. **If that evidence establishes ordinary raw preparation:** an SPTM-resident
   host/guest design is a different bootstrap contract. Require a public,
   inspectable host bootstrap and qualified firmware/platform evidence before
   assessing such a design. Do not force the optional branch by changing image
   classification. The current raw failure remains an effective CPU1 entry-state
   problem, with no newly identified release operation.
3. **If it establishes optional-object selection:** selection alone is insufficient.
   Distinguish requested/loaded object readiness and the selected entry/range
   context at the preparation phase from actual monitor entry. A qualified record
   showing those completed would weaken the “missing object preparation” theory;
   a record showing failure would locate a concrete earlier prerequisite. The
   present artifacts contain neither result. This pass qualifies no new live
   collector for those fields.
4. **Only after preparation is resolved:** a physical experiment needs a
   core-and-phase-qualified discriminator of CPU1 fetch, entry context or effective
   permission. CPU0 reads, software masks, reset mirrors and guest shadow arrays
   cannot substitute. Until such evidence or a qualified alternative bootstrap
   arrives, nativeHOLD is the explicit terminal decision for this investigation.

The new public all18-CPU claim is documented separately in the
[31U upstream comparison](native31u-upstream.md): it concerns a Linux guest under
an SPTM-resident x1n1 host on a different machine/firmware combination. Its absent
public host bootstrap and private referenced logs do not resolve this historical
raw-path decision. The claim remains relevant to an alternative architectural
approach; it is neither a verified raw-path remedy nor evidence of impossibility.

## Validation

The unchanged generic J716c image is `mBoot-18000.161.10` for25G83. Decoded SHA-256
`b4822fc8902c3693ee590c544011603423a75291edd60afd31210d068a4ca120`; byte-preserving
analysis ELF SHA-256 `f89169923c17be829c6b31c3c04c5695d06d42a42cea7390f61214202400dcee`.
The header-derived analysis base is `0x100c1aa4000`, not a measured live address;
decoded bytes map at ELF offset4096. Existing generic-carrier provenance is
unchanged. Retained boot021 SHA-256 remains
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.

Two fresh REA/Ghidra12.1.4 queries completed in the root-controlled isolated lab,
67.167/67.189 seconds, query exits0 and VM setup/job exits0. The batch verified
loopback only, with no physical USB. Both dossiers are untruncated with zero
P-code operations outside their reported bodies; the layout removed-block warning
remains an explicit refusal. Earlier producer-A removed blocks and producer-B
truncation also remain unresolved.

Apple LLVM21 independently matches **254 instruction words /1,016 bytes in13
bounded blocks**, zero mismatches:165 words are new beyond the prior published
CPU range union and89 overlap it. Counts measure static coverage, not execution
or whole-function correctness. Exact body/data offsets, hashes, timings, provider
flags and bounded conclusions are in the
[validation record](../reverse-engineering/findings/cpu-startup31u/validation.json).
Proprietary bytes, disassembly and pseudocode remain ignored and private. No
native operations, personalized-object access, installed-image changes or restart
occurred. This pass produces no new CPU hardware adapter or startup fix.

# 31P CPU findings: image preparation is not a secondary-release step

Date: 2026-10-22. **Native 31P HOLD / NOT RUN.** This pass continues the
31O firmware-prerequisite investigation. It does not establish the missing
CPU1 startup step or justify another marker-only reboot. macOS, the installed
lab image and consumed native receipts remain unchanged.

## What the new trace establishes

The matching generic firmware's image-property callback places the `kcbz`
property into a 64-bit descriptor field at `+0x38`, and `kcep` into a 64-bit
field at `+0xa0`. On the bounded paths examined, the first influences entry
producer selection and additional-object loading; the second supplies an entry
offset. Both the buffer and file loaders register the property callback.
Property spelling is observed; a broader interpretation of these names is not
needed for the verified data flow.

In the primary caller, a descriptor-present byte equal to one and a nonzero
`+0x38` field gate an additional-object preparation call before common image
preparation. The checked object path loads a table of additional firmware
objects. It is not itself a newly discovered MMIO write that releases CPU1.
Another buffer-loading path can also populate its readiness state, so the
checked file loader is not the sole possible producer.

Before selecting the other entry producer, the bounded preparation path checks
equality of two 32-bit software masks representing requested and loaded objects.
It then marks software layout/context state. These are **object-preparation
conditions**, not CPU power, reset-release or first-fetch observations. Their
native values during the consumed raw boot are unknown. The following labels
refer to analysis addresses, never qualified live native reads:

| Evidence | Analysis location / field | Meaning supported by the trace |
|---|---|---|
| Property callback | `0x100c1ad0b04`; descriptor `+0x38`, `+0xa0` | Separate selector and entry-offset inputs |
| Primary caller | `0x100c1aa5de0` | Conditional additional-object preparation before common image preparation |
| Alternate caller | `0x100c1aa6528` | Another bounded caller, not a raw/macOS label by assumption |
| Object file loader | `0x100c1ca6390` | Loads and populates software object state |
| Requested / loaded masks | `0x100c1f2c8e0` / `0x100c1f2c8dc` | Equality is a loader-readiness predicate |
| Active context byte | `0x100c1f288d9` | Software state, not remote CPU execution evidence |

**Inference limit:** a filename, raw packaging, or an empty BootKC region does
not establish the callback's actual metadata values or the branch taken on
this machine. This trace narrows the comparison that must be made; it does
not authorize altering firmware objects, security state or software descriptors.

## Why instruction checks mattered

The tag-comparison helper communicates through ARM64 condition flags rather
than the ordinary C return-value convention. The decompiler's C-like output
does not preserve that data flow correctly. Tag dispatch conclusions therefore
come from independently checked instructions and conditional targets, not a
translation of the pseudocode into Linux code.

REA/Ghidra completed six queries: three decompilation responses and three
function dossiers. The dossiers contain 1,077 instruction words and 4,914 pcode
operations. Independent LLVM/original/analysis-ELF comparison covers 1,955 unique
instruction words, with zero mismatches. These counts overlap; they must not
be summed as independent coverage. Decompile-only responses have no dossier
body/pcode guarantees. All original bytes, disassembly and pseudocode remain
in ignored private research storage.

The first batch exceeded the VM job's 240-second outer deadline: three requests
completed, one was interrupted without a completion record and one never
started. Those are preserved as incomplete, not counted as successful queries.
A second bounded batch completed the three dossiers and exited successfully.
Both VMs explicitly disabled networking and verified that only loopback existed.

Matching input hashes, all bounded instruction ranges, individual query
outcomes and limitations are in the
[validation record](../reverse-engineering/findings/cpu-startup31p/validation.json).
The analysis base is not a measured runtime address. No firmware program was
replayed and no native memory, register or policy operation occurred.

## Next CPU work

Establish the actual metadata provenance for the custom raw image from existing
authorized artifacts, then relate it to this traced preparation contract.
Distinguish object preparation that precedes handoff from restoration that
occurs only on later power transitions. Do not infer a missing hardware action
from a skipped software-object branch alone.

A physical test still needs a new, qualified discriminator of a concrete
remaining hypothesis. The previously discussed post-power mirror comparison
or bounded state trace can be part of that test once its interpretation changes
the next decision. Neither alone establishes CPU1's effective PC. First verified
secondary execution remains ahead of coherent-memory/timer/IPI qualification,
other Performance/Super clusters, Linux SMP and efficiency measurements.

# 31K: trace the source entry, then test natural arrival

2026-10-21. **Static REA analysis completed; native 31K NOT RUN.** This
investigation does not resolve CPU1's effective entry path or deliver SMP.
Apple bytes, assembly, high-pcode and decompiler output remain in ignored local
build storage. This document records original behavioral findings only.

## Result and engineering decision

The firmware's reset-address programmer consumes an entry value from a global
populated during image preparation. It does not simply receive the current
boot-mode argument as an entry address. That value is aligned to 4KiB before
programming the per-core mirrors. Neither this source provenance nor mirror
readback proves which instruction CPU1 executes.

The useful next discriminator is a **RAM-only natural-arrival tripwire** at the
installed m1n1 cold-entry candidate, armed only after CPU0 has completed its
normal initialization. It must record and enter a local self-loop before cold-path work
can clear shared BSS. It must not redirect a reset vector. Retain the separate
vector recorder and a CPU0 positive control of the recording mechanism.
This is an experiment on a candidate path, not a firmware-derived startup fix.
The controller's independent prefix, identity, mapping and cleanup review
remains necessary; the static findings do not substitute for it.

## Artifact and method

Reused the matching generic, unpersonalized `iBoot.j716c.RELEASE` identified as
`mBoot-18000.161.10` by the [31H analysis](native31h-reset-entry.md). No new
personalized boot object, credential or host-system modification was involved.

| Artifact | SHA-256 |
|---|---|
| Generic IM4P wrapper | `b9501bee4fef7d2b82530d34a0a3182e21f9f0edf60cb5ad1dae0358dd4bcef1` |
| Decoded firmware, 4,266,536 bytes | `b4822fc8902c3693ee590c544011603423a75291edd60afd31210d068a4ca120` |
| Byte-preserving analysis ELF | `f89169923c17be829c6b31c3c04c5695d06d42a42cea7390f61214202400dcee` |
| Installed boot021 pin used by this campaign | `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664` |

The firmware analysis base is `0x100c1aa4000`, derived from its header; it is
**not a measured live load address**. Raw bytes begin at ELF file offset 4096.
The analysis wrapper does not model BSS, so global addresses and their static
references do not establish their runtime contents. Public m1n1 reference pin:
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`.

Six fresh REA 6.4.0 / Ghidra 12.1.4 queries ran in three bounded batches in the
existing diskless analysis VM: five function dossiers and one cross-reference
query. Each completed with exit 0. The previous lab job was restored and all
VM/quiet locks released afterward. Third-party analysis did not run on macOS.
Apple's existing LLVM 21.0.0 tool independently decoded the new bounded bodies.

## Entry provenance established statically

| Analysis address / extent | Observation | Confidence and limit |
|---|---|---|
| `0x100c1b3ef44`, 276 bytes | Direct caller of `0x100c1ae53b8`. The input is used as a mode and compared with 12 and 2 on different branches. It is also passed to the later handoff helper `0x100c1ae45d8`. | High for these bounded original-byte/LLVM uses only; whole-function high-pcode is rejected for crossing the reported boundary. Neither numeric mode is assigned a raw-boot/macOS meaning here. |
| `0x100c1ad4ef0`, 12 bytes | Supplies the address of global `0x100c1f2a1b0` to descriptor helper `0x100c1ad7af8`. | High for the local address/dataflow; global runtime contents unknown. |
| `0x100c1ad7af8`, 24 bytes | Constructs a descriptor whose value range spans one 8-byte element at the supplied address. | High; it constructs a view, rather than choosing an entry path. |
| `0x100c1ae5c60`–`0x100c1ae5c88`, within retained 31H caller | Obtains the descriptor, checks that its start precedes its limit, dereferences its first element, aligns the value to 4KiB and calls the per-core programmer `0x100c1c2e398`. | High for this bounded path. The mode argument is not the source of the programmed address. |
| `0x100c1ad2478`, inside `0x100c1ad12e0` | Static write reference to the entry global from an image-preparation function. | High for the decoded reference; provider removes blocks, so no whole-function reachability claim. |
| `0x100c1ad4528` / `0x100c1ad4540`, inside `0x100c1ad2594` | Static write and read references to the same global from a second image-preparation function called by the first. | High for these references; high-pcode truncates, so branch selection and complete producer semantics are unresolved. |

The additional function at `0x100c1c2feac` concerns peripheral finalization and
does not establish CPU1 reset dispatch. Its analysis did not justify changing
CPU-start, stop, power or reset-register writes.

The global's two producers are **not evidence of two CPU entry modes**. Their
call relationship is known statically, but which producer/path supplies the
current raw boot, whether any other computed writer exists, and which entry
CPU1 ultimately consumes remain unresolved. In particular, the 4KiB alignment
does not prove that CPU1 naturally visits m1n1 image offset `0x800`.

## Validation and interpretation limits

[Sanitized validation record](../reverse-engineering/findings/cpu-startup31k/entry-provenance-validation.json)
records source digests, function/body offsets and hashes, query outcomes,
provider bounds and warning classes. It contains no firmware bytes or code.

- Five fresh function bodies: **3,594 instructions / 14,376 bytes** checked
  against decoded source and analysis ELF, and independently against fresh
  Apple LLVM words. Zero byte/word mismatches. **Three high-pcode operations escape the reported
  dispatch-caller body**, at two addresses (`0x100c1b3f068` and
  `0x100c1b3f080`); its whole-function high-pcode/pseudocode is rejected.
  The other four dossiers have zero out-of-body operations. The caller claims
  above rely only on bounded original-byte/LLVM instruction review.
- The three-instruction descriptor getter was additionally decoded and checked:
  **3,597 total independently checked instruction words / 14,388 bytes**.
- Separately, producer A has `provider_removed_blocks`; producer B's high-pcode is truncated.
  Whole-function route inference from either is rejected. Untruncated pcode in
  producer A does not repair its removed blocks. Body coverage does not prove
  that a reported path is reachable.
- A cross-reference inventory cannot exclude computed writers or later stages.
  No incoming CPU1 EL, MMU/cache state, effective PC or reset-release condition
  was established. No firmware sequence is replayed by this investigation.

The previous [31I readback findings](native31i-readback.md) remain unchanged.
The observed locked mirror format is not a request to unlock or reprogram it.
The latest 31J record reached phase 0 in all samples, with identity fields not
committed; this must not be rewritten as every raw record word being zero.
The CPU1 power and opaque-state transitions are not instruction evidence.

## What one 31K session can distinguish

Use the implemented controller's exact gates; these are interpretation rules,
not authority to perform extra target operations.

| Committed observation | Meaning / next decision |
|---|---|
| CPU0 positive control fails, including unsuccessful normal scratch restoration | Recording/probe setup is not demonstrated. Stop before CPU1 startup; retain partial evidence. |
| CPU0 control succeeds; only the expected phase-1 cold marker commits | The first marker store was observed, but CPU identity is not committed. Do not attribute arrival to CPU1; stop with partial evidence. |
| CPU0 control succeeds; natural cold tripwire commits phase 2 with the expected fresh marker and CPU1 identity | CPU1 reached the candidate cold-entry interception point in this run. Investigate a secondary-specific handoff before allowing any cold-path initialization. This alone does not prove Linux SMP, coherence, timers or callbacks. |
| Vector recorder commits CPU1 progress | Localize progress with its original phase/identity gates. A cold marker is not required if the vector route is independently established. |
| Neither recorder commits CPU1 evidence, despite CPU0 control success | Positive control narrows some recording failures, but does not prove CPU1 reached neither path: CPU1 state, instruction/data visibility and earlier dispatch remain unknown. No speculative fallback or extra start. |
| Fault, timeout, uncommitted/ambiguous identity or conflicting records | Stop with the observed prefix. Do not promote a raw scratch value or state transition into CPU1 execution proof. |

Phase 3 adds a committed CurrentEL value; it does not prove that the terminal
self-loop was reached or that an architectural park occurred. Normal scratch
restoration is part of the successful CPU0 control only; a fault does not
authorize cleanup, retries or further target operations.

A positive control runs in CPU0's known context. It cannot establish CPU1's
incoming execution state or guarantee that CPU1 would see the same patch and
record mapping. A negative tripwire is therefore not proof of a different
firmware entry. No outcome authorizes a security/CTRR change, installed boot
mutation, register redirect or expansion to additional cores.

CPU1 execution and a validated secondary handoff remain prerequisites for
bringing up the machine's **12 Performance + 6 Super cores** and measuring
scheduler, rendering, memory and power behavior against macOS. Native 31K and
all macOS-performance-equivalence claims remain **NOT RUN / UNPROVEN** here.

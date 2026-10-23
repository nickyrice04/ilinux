# 31S: the range services resolve inside the retained mBoot image

2026-10-23. **Offline findings; native31S HOLD / NOT RUN.** M1's31R review
`ff1ed8e` passed420 pins,176 Python methods and60 portable C groups. CPU1 execution
remains unverified. The existing31R evidence remains frozen.

The successful range-service owner is now resolved: both services enter the
matching generic mBoot image's own exception dispatcher and local handlers.
Their checked bodies configure implementation-specific range registers and
perform translation maintenance. Public register definitions identify CTXR
bounds and most of the CTRR bounds. This closes31R's unresolved ownership edge.
It supplies no missing secondary-start operation and does not establish that
range protection caused the failed CPU1 entry.

## The dispatcher and the handler are in the same artifact

31L had already established the generic image's exception route and supervisor-
call dispatcher for final OS handoff. Applying that retained evidence to31R's
range services resolves the two previously unknown cases without assuming an
external SPTM owner.

**Confirmed bounded static:** the exception path reaches dispatcher entry
`0x100c1cb6c1c` through `0x100c1caf858`. The selector permits unsigned values
through130 inclusive. The table at `0x100c1cb9898` therefore has131 entries,
each a signed32-bit little-endian displacement. The displacement's base is the
separate code anchor `0x100c1cb6d10`. Using the table address as that anchor
would produce different, incorrect targets.

| Service | Decoded case | Handler call site | Local handler |
|---|---|---|---|
| 12 | `0x100c1cb7db8` | `0x100c1cb7dcc` | `0x100c1adac44` |
| 17 | `0x100c1cb7e38` | `0x100c1cb7e4c` | `0x100c1adaaec` |

The same decoding preserves31L's previously checked selectors5,6 and7. These
are static control-flow destinations in one byte-preserving analysis mapping.
They do not qualify live addresses, authorize invoking a service or establish
that the historical raw boot took the inferred preparation path.

## Range configuration and the unresolved CPU failure

**Confirmed bounded static:** each queried handler contains16 distinct system-
register accessor encodings, synchronization and translation-maintenance paths.
Neither checked body makes another supervisor/hypervisor/secure call or directly
stores to non-stack memory. This is a local range-configuration path, not an
unexamined forwarding call into another firmware image.

The retained public m1n1 definitions at commit
`57a9339ffd1876e78297b17d34dece8cff8fa1ba` identify all16 service17 accessors as
CTXR lower/upper bounds and12 of service12's16 accessors as CTRR lower/upper
bounds. Four service12 accessors remain unnamed by those retained definitions.
The names include ACC variants; their presence alone does not establish which
secondary, cluster or live register bank was affected. Sources were read as
local data and verified unchanged against that commit:
[m1n1 CPU register definitions](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/cpu_regs.h)
and [register metadata](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/proxyclient/m1n1/apple_regs.json).
This is a pinned comparison, not a current upstream-status claim.

31L's VHE finding still applies: an EL1-named accessor does not by itself prove
execution in an EL1-only regime. No live privilege state or protection state was
measured. The new trace identifies range-protection preparation before the
selected boot entry; it does not show that Linux omitted it, that a lock must be
changed, or that a particular restriction prevents CPU1's first fetch.

**Unknown:** the historical descriptor values, selected register bank, effective
range state when CPU1 starts and its first executed instruction. Those missing
values prevent a decisive overlap or causality test from these static artifacts.
A further adjacent function query cannot supply historical runtime values. No
range rewrite, lock change, firmware replay or physical retry follows.

## An original reusable resolver, checked on the retained input

The original [relative-table resolver](../kernel/experiments/firmware31s/dispatch.py)
accepts an exact source digest, explicit table offset/count, separate target
anchor, non-overlapping file/address mappings and allowed target ranges. It
rejects malformed or unbounded layouts, signed-target arithmetic overflow,
misaligned/out-of-range targets and source mismatch before returning metadata.
It never executes a target or infers permissions.

A private integration check used the entire retained decoded image, not an
unidentified slice. Five selected entries resolved inside five exact4-byte
allowed target windows. Independent unsigned decoding plus explicit two's-
complement conversion agreed for all five; old selectors5/6/7 were preserved.
The full131-entry table extent was bounded, but only those five destinations
were requested and qualified. The result is **STATIC_RESOLUTION_ONLY**.
The [resolver validation](../reverse-engineering/findings/cpu-startup31s/resolver-validation.json)
records the public implementation hash, input provenance, declared layout,
five targets and output digest without firmware bytes. Synthetic software tests
and this private-input integration are separate evidence.

## Provenance and bounded validation

The retained generic IM4P wrapper hashes to
`b9501bee4fef7d2b82530d34a0a3182e21f9f0edf60cb5ad1dae0358dd4bcef1`.
Its exact compressed payload is independently matched at wrapper offset42;
that payload hashes to
`826d767772cf6b1121e64d42b3a1022aca9a6eaa6d8e576f74b1cae2e558fc4f`.
Extraction/decompression provenance is inherited from retained31H/31N work;
decompression was not repeated in31S and no personalized object was read.

The resolver input is the4,266,536-byte decoded image, SHA-256
`b4822fc8902c3693ee590c544011603423a75291edd60afd31210d068a4ca120`.
The REA input is its byte-preserving analysis ELF, SHA-256
`f89169923c17be829c6b31c3c04c5695d06d42a42cea7390f61214202400dcee`, with the
entire decoded image at file offset4096. Analysis base `0x100c1aa4000` remains a
header-derived mapping, not a measured runtime base. The table's raw-file offset
and analysis-ELF offset differ by4096; both are recorded explicitly.

The [validation record](../reverse-engineering/findings/cpu-startup31s/validation.json)
contains two successful REA queries with90 instruction addresses and67 P-code
operations. No P-code truncation, body escape or removed-block warning was
reported; whole-function pseudocode remains unaccepted. Fresh focused Apple
LLVM decoding matches **321 instruction words /1,284 bytes in9 disjoint blocks**
against the decoded input and ELF, with zero mismatches.157 words are new beyond
the union of the checked31L/31Q/31R ranges;164 overlap it. The524-byte dispatch
table is data and is hashed separately, not counted as instructions.

The VM used explicit no-network configuration and verified loopback only.
Private Apple bytes, disassembly and pseudocode remain ignored. No hardware,
boot, macOS or policy operation was performed. The next CPU question requires
provenance for effective secondary range/entry state or another independently
qualified distinguishing observation; this checkpoint creates no boot request.

# 31L offline entry investigation

2026-10-22. **Native 31L HOLD / NOT RUN.** No new hardware write or read is
qualified by this investigation. This continues 31K; it does not replace the
installed boot entry, reset the project, or establish Linux SMP.

## Decision

31K's CPU0 recording control passed in 14.136 ms. Both CPU1 start stores were
acknowledged, CPU1 eventually reported power actual 15 and opaque byte 2, but
neither candidate recorder committed an identity. That leaves CPU1's effective
instruction path and memory visibility unresolved. The final in-flight
observation deadline did not complete a trailing state pair. See the
[31K result review](native31k-result-review.md) for the evidence and its limits.

The useful next work is an exact-image execution-context audit and a bounded
investigation of **what CPU1 executes before it can publish its first store**.
Another unchanged negative-marker boot would not distinguish a held core,
different instruction path, early exception, or invisible marker. No additional
PMGR reset-release write was found with sufficient provenance to test.

The new descriptor findings below close gaps in the static analysis. They do
**not** invalidate the already observed reset mirror or make a runtime selector
dump a prerequisite: even fully resolving that selector might only reproduce
the address already read back. The unresolved question is first fetch and
incoming execution context at that address.

## Evidence and method

Reused the same generic, unpersonalized `iBoot.j716c.RELEASE` from 31H/31K,
identified as `mBoot-18000.161.10`. No personalized object or secret was read.

| Artifact | SHA-256 |
|---|---|
| Decoded firmware | `b4822fc8902c3693ee590c544011603423a75291edd60afd31210d068a4ca120` |
| Byte-preserving analysis ELF | `f89169923c17be829c6b31c3c04c5695d06d42a42cea7390f61214202400dcee` |
| Installed boot021 campaign pin | `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664` |

Analysis base `0x100c1aa4000` comes from the image header and is not a measured
live address. Raw bytes are preserved at ELF offset 4096. The wrapper does not
establish BSS contents or runtime global values.

Two fresh REA 6.4.0 / Ghidra 12.1.4 function queries ran in the existing isolated
diskless VM. Both exited 0. Their analysis took 58.184 and 57.201 seconds. The
prior job was restored and all quiet/shared locks released. Retained producer
dossiers guided a separate, bounded original-byte/Apple LLVM review rather than
another large decompilation. **320 instructions / 1,280 bytes** matched the
decoded firmware, analysis wrapper and fresh LLVM output, with zero mismatches.
Both fresh dossiers have untruncated high-pcode and zero operations outside
their reported bodies; their context and terminal-flow limitations remain.

[Sanitized validation record](../reverse-engineering/findings/cpu-startup31l/entry-provenance-validation.json).
Apple bytes, disassembly and decompiler output remain in ignored local build
storage. This document records behavioral observations, not translated source.

## Bounded entry dataflow

| Analysis location | Observation established from bounded blocks | Limit |
|---|---|---|
| `0x100c1ad15a4` through `0x100c1ad15f0` | Producer A selects producer B when the input descriptor's 64-bit field at `+0x38` is nonzero; otherwise it proceeds along another preparation path. | This does not assign either branch a raw-boot/macOS name or prove its runtime selection. |
| `0x100c1ad1b68` through `0x100c1ad1bfc`, then `0x100c1ad5ef0` through `0x100c1ad5fec` | A passes a bounded output pointer for its local entry slot to the layout helper. In the mode-1 helper branch, that slot receives descriptor field `+0xa0` plus the selected relocation base supplied by A. | Descriptor contents and all preceding relocation choices are runtime data. This is local dataflow, not whole-function reachability. |
| `0x100c1ad2348`, `0x100c1ad7e00`, `0x100c1ad4858`, then `0x100c1ad2478` | A translates the local entry using a structure's base pair at offsets `+0x8` and `+0x10`, then writes the shared entry global `0x100c1f2a1b0`. The arithmetic is input minus the first base plus the second. | The base pair matches public BootArgs virtual/physical layout; the identification is corroboration, not proof of every runtime value. |
| `0x100c1ad44a4` through `0x100c1ad4540`, helper `0x100c1ad79f0` | B obtains a subobject at global context `0x100c1eb3958 + 0x140`; it combines its fields `+0x78`, `+0xa0`, and `+0x8` as first plus second minus third and writes the same entry global. | Field names and current runtime values are not established. No claim that this is the active raw-boot branch. |
| Wrapper `0x100c1aa4e5c`; call sites `0x100c1aa6210`, `0x100c1aa6808`, `0x100c1aa975c` | A's descriptor passes through a common wrapper reached from at least three statically direct callers. Two callers pass bounded stack descriptors; the third forwards another descriptor. | A direct-reference inventory cannot exclude indirect callers. These are follow-up anchors, not three proven hardware modes. |
| Retained consumer `0x100c1ae5c60` through `0x100c1ae5c88` | The consumer dereferences the shared entry global, aligns to 4 KiB, and invokes the per-core reset-address programmer. | This remains consistent with the observed base address. It does not prove CPU1 fetches that address or the cold entry at offset `0x800`. |

The public BootArgs layout is independently visible in
[`xnuboot.h` at the campaign's m1n1 pin](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/xnuboot.h).
The existing boot-entry procedure configures raw entry offset 2048; that
installation argument does not prove a secondary-core reset PC.

Producer A still has provider-removed blocks and B still has truncated
high-pcode. These defects are not repaired by checking selected blocks. Claims
above use only bounded instructions and explicit local argument relationships;
complete control-flow reconstruction remains out of scope for this pass.

## Fresh early-accessor queries

The 12-byte helper at `0x100c1aab970` selects an offset of `0x50000` and forwards
the caller's hardware context to an accessor. The 68-byte helper at
`0x100c1aa9ef4` performs a bounds-checked table lookup and forms an address from
the table value, caller offset and a die-derived contribution. This improves
provenance for retained early firmware setup but does not establish that the
context is CPU1's active reset interface. No register from this path is added
to the native allowlist.

The retained T6050 PMGR findings still support the die bitmap and per-cluster
core-mask stores already used. CPU1 is in the boot cluster, and its bit remains
2; topology for later clusters must retain six-core grouping. The bounded
AppleARMCPU start dispatcher and PMGR enable path do not reveal an additional
reset-release operation. That is a bounded negative finding, not proof that
earlier cluster preparation or a firmware prerequisite does not exist.

## Why the PC-sampler idea is not ready

The ADT contains per-core debug windows, but the inspected public m1n1 watchdog
only records the UTT-debug base; it does not establish a supported PC-read
contract. The retained Apple watchdog health function checks OS/processor
health through callbacks rather than exposing a proven direct hardware PC
sampler in that bounded routine.

Public XNU's
[`configure_coresight_registers`](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/osfmk/arm64/cpu.c)
skips ED/UTT mapping when CoreSight debug is disabled, and the setup path can
include lock-access writes. Thus an ADT window is insufficient authorization or
technical evidence for a passive PC observer. No unlock or debug-state write
is proposed. A future read would need T6050-specific width, offset, feature,
power/lock and read-side-effect evidence. This pass establishes none.

## Next research that can change an experiment

1. Use the exact installed m1n1 image and the 31K evidence to enumerate the
   earliest loads, branches, exception routing and first publication store for
   plausible incoming EL/MMU/cache states. Keep CPU0-visible RAM contents
   separate from CPU1 instruction visibility. The offline checker can reject
   unsupported assumptions; it cannot emulate undocumented firmware or prove
   a CPU1 state.
2. Trace the reset/secondary dispatch before those instructions, or identify a
   documented read-only observation distinguishing fetch from no fetch.
   Retained firmware anchors: the consumer above, entry dispatch at
   `0x100c1ae45d8`, and direct finalizer/caller at `0x100c1b3ef44`. Review only
   blocks needed to determine incoming context and physical-address visibility.
   Do not infer a hardware mode from numeric mode arguments alone.
3. Independently trace the platform prepare/unquiesce context around the
   established AppleARMCPU/PMGR enable dispatch. Seek a prerequisite with
   concrete register provenance and ordering, not another speculative store.
   The two final start stores may be correct while an earlier prerequisite is
   missing.
4. Release another native attempt only when it changes one supported hypothesis
   and gives distinguishable outcomes. Existing mirror readback already
   constrains the target; re-proving its producer alone is insufficient.

The public [T6050 m1n1 support report](https://github.com/AsahiLinux/m1n1/pull/610)
also reports powered secondary cores failing to execute m1n1. This corroborates
the category of failure; it does not diagnose this particular boot or justify
an unmeasured workaround. All heterogeneous-core scheduling and efficiency
claims still require actual secondary execution, Linux SMP, and native tests.

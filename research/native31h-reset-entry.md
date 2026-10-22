# 31H: reset format, firmware ownership and an independent core-state observation

2026-10-21. **Static analysis and offline software tests; native31H NOT RUN.**
This records original behavioral findings. Apple bytes, disassembly and
decompiler output remain in ignored local build storage. It is not an SMP fix
or a claim of CPU performance improvement.

## What the firmware analysis establishes

The generic, unpersonalized `iBoot.j716c.RELEASE.im4p` found read-only in the
installed reference environment identifies `mBoot-18000.161.10`. Two generic
copies matched. No personalized IMG4, identifiers or credentials were collected.
Decompression and REA6.4/Ghidra12.1.4 ran in the existing isolated analysis VM.

| Input | SHA-256 |
|---|---|
| Generic IM4P wrapper | `b9501bee4fef7d2b82530d34a0a3182e21f9f0edf60cb5ad1dae0358dd4bcef1` |
| Compressed payload | `826d767772cf6b1121e64d42b3a1022aca9a6eaa6d8e576f74b1cae2e558fc4f` |
| Decoded 4,266,536-byte firmware | `b4822fc8902c3693ee590c544011603423a75291edd60afd31210d068a4ca120` |
| Original analysis ELF wrapper | `f89169923c17be829c6b31c3c04c5695d06d42a42cea7390f61214202400dcee` |

The wrapper preserves raw bytes at file offset4096. Its analysis address base
`0x100c1aa4000` comes from a header field; it is **not a measured live load
address**. It does not model BSS or prove runtime values of global tables.
This is the matching board/version artifact, not a measurement of which
firmware branch executed during the lab boot.

**Confirmed static, with bounded instruction/dataflow review:**

| Function / bounded site | Behavior | Engineering consequence |
|---|---|---|
| `0x100c1ae8b40`, 484bytes; store+`0x19c` | Builds CPU implementation-window addresses from base`0x210050000`, die shift38, cluster shift24 and core stride1MiB; stores these addresses in a RAM table. | Confirms address construction. This is **not** itself a peripheral-register write. |
| `0x100c1c2e398`, 256bytes; mask+`0x74`, bit0+`0x78`, store+`0xb0`, readback+`0xb8` | Consumes that table; normalizes its input with mask`0x3fffffff800` and bit0, then uses64-bit write/readback. | The firmware field retains bits41:11. The old47:12-only report loses information. |
| `0x100c1ae53b8`, 2,808bytes; input alignment at`0x100c1ae5c84`, call at`...5c88` | The sole direct caller found first aligns the source entry to4KiB. | Retained bit11 does **not** show that this path programs the cold entry at image+`0x800`. Do not relocate the hook on that premise. |
| `0x100c1aaa664`, 576bytes; masks+`0x88` and+`0x1ec` | Another access path uses the same format and64-bit write/readback. Its hardware-context ownership is unresolved. | Corroborates the format, not the active raw-boot destination. |

Seven firmware function dossiers were checked against original bytes and
independently decoded with Apple's existing LLVM: **1,537 instruction words /
6,148 bytes, zero mismatches, zero cross-boundary high-pcode operations, zero
reported decompiler warnings**. Those checks do not prove semantic correctness;
the findings above also required manual control-flow and register-provenance
review. Entry/boot-metadata routines were analyzed but do not independently
establish secondary reset dispatch.

Two additional driver queries (AppleARMPlatform start and watchdog health)
matched653 instruction words, but their whole-function pseudocode crossed the
provider's function boundary and was rejected. No new hardware claim relies
on those pseudocode results.

## What remains unknown

The current raw boot's effective CPU1 destination, reset release, incoming
translation/cache state and first instruction remain **UNKNOWN**. A correctly
formatted register mirror is not a PC. CPU0 readback does not demonstrate
CPU1 visibility. The 31G power-domain transition is not execution evidence.

The exact installed boot021 has vector entry0 and cold entry`0x800`. Its cold
path initializes primary state and clears shared BSS; blindly redirecting a
secondary through it is inappropriate. 31H retains the reviewed vector hook.
No RVBAR, security-register, firmware or installed boot-object write is added.

The PMGR stop-clear hypothesis is not supported by the inspected paths: retained
`ApplePMGR::configMiscCores` assembly uses offset0 on disable, offset4 and
cluster offset8 on enable, agreeing with public m1n1. The mode2 branch at
`0xfffffe0009495b44` selects the disable path; relevant dispatch sites are
`0xfffffe0009495ebc`, `...95ba8`, `...95c4c`. No prerequisite stop-register
clear/read was established. A command address must not be treated as readable
sticky reset status merely because its writes are understood.

## Why the additional read is a bounded experiment

Pinned public m1n1 `57a9339ffd1876e78297b17d34dece8cff8fa1ba`:

- [`src/hv/hv.c`](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/hv/hv.c), lines42–88, accepts four-byte physical accesses at the ADT CPU implementation base+`0x100`; its read forwards the hardware access before masking the low byte for a guest that has not started that core.
- [`src/hv/hv_vm.c`](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/hv/hv_vm.c), lines928–969, implements the width-specific guarded physical read with barriers.
- [`src/smp.c`](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/smp.c), lines214–250, checks the low byte with a64-bit read after stopping a previously running CPU. It skips access for deep sleep because powering off the last core can remove access.

This supports the **location and32-bit access experiment**. It does not prove
never-started t6050 CPU1 accessibility, side-effect freedom or low-byte meaning.
A bounded firmware search found48 immediate-offset`0x100` loads, but none with
independently established CPU-window provenance. That negative search is not
proof that no firmware reader exists.

31H uses CPU0 as the executing reference and CPU1 in the same active cluster.
The inherited live census binds both complete `cpu-impl-reg` windows (extent
`0x9018`); translation checks precede access. Fixed addresses are
`0x210050100` and `0x210150100`. Two guarded baseline reads occur before any
CPU1 start intent. Six subsequent reads reuse the tested32-bit helper without
temporarily changing the shared exception guard. Maximum: eight reads in four
pairs, with a one-second pair deadline and the existing outer/human bounds.

Only the opaque low byte and comparisons are retained. Zero, nonzero, equality
with CPU0 or a transition **never authorize CPU1 callbacks or prove reset
release, instructions, coherence or a running Linux CPU**. The existing entry,
identity, timer and parked-state gates remain mandatory.

A guard handles synchronous faults; it cannot guarantee containment of an
asynchronous SError or bus hang. Any fault, lost acknowledgement or exceeded
deadline stops the campaign with partial evidence, no retries or further
target commands. The human returns to Macintosh HD under the existing90-second
bound. No idle/stop/deep-sleep operation is introduced.

## Decisions connected to evidence

1. Preserve both existing RVBAR reads with the verified firmware format and
   explicit unknown bits. Refuse before mutations if mirrors disagree, the
   field differs from image base, or unexplained bits are present.
2. Keep the two CPU1 start writes and vector recorder unchanged. Neither a
   cold-entry redirect nor a new power/stop write has supporting evidence.
3. Compare reset-format, PS, opaque CPU-state and recorder evidence in the same
   bounded session. See the outcome table in the31H plan; no additional reboot
   is needed merely to collect the second signal.
4. Continue heterogeneous-core work only after CPU1 entry is established.
   The machine remains12 Performance +6 Super cores across three clusters.
   Public idle workarounds are already present in boot021; their eventual
   power cost is a separate efficiency task, not a demonstrated startup fix.

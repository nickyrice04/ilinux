# 31N: firmware command programs and locally grouped CPU-start writes

Date: 2026-10-22. Scope: static analysis of this machine's matching generic
firmware and macOS driver members. No native target operation or macOS setting
changed. Raw Apple material, decompiler output and disassembly remain ignored.

## Decision

**Confirmed:** 31M qualified CPU0's observation and maintenance machinery but
obtained no committed CPU1 identity. Another equivalent zero-marker observation
would not resolve the missing first instruction. The matching firmware does
contain CPU implementation-register restore programs, but their existence does
**not** establish a missing reset-vector write that Linux should reproduce.

**Practical next experiment:** retain the same reviewed CPU1 start addresses,
masks and entry recorders, while issuing the two start writes within a single
bounded CPU0 operation. This removes host transport and intermediate observer
work from the interval between the writes. The macOS driver supplies behavioral
support for local grouping; it does not establish a required microsecond limit
or guarantee that this change will start CPU1. The controller and native
authorization are separate from these static findings.

## Inputs and independent checks

The generic firmware is **mBoot 18000.161.10, J716c**, matching the prior 31H–31M
analysis. Its decoded iBoot SHA-256 is
`b4822fc8902c3693ee590c544011603423a75291edd60afd31210d068a4ca120`.
The analysis-only ELF base is `0x100c1aa4000`; it is not a claim about the live
firmware address space.

The matching generic iBootData IM4P SHA-256 is
`8b86a8ec0a074fde75995a53ec3cd616311fcff3b5a771ab530ce2c6bce38b4d`.
It was decoded in the isolated VM. The resulting 459,150 bytes have SHA-256
`b43f7a31f6d980c6205f029dd80b2dc5ec0a2a52d7d3d801019736d9dcb5d11b`.
No personalized firmware material was used.

An original bounded parser independently checks the RCfg directory, section
bounds and non-overlap, fixed-size names, command lengths and sequence IDs. All
four command sections consume exactly: **16,542 + 843 + 5,411 + 59 = 22,855
records**, plus 417 names including the end marker. This is a decoder, not a
firmware interpreter: it does not evaluate conditions or execute transactions.

REA/Ghidra queries run only in the isolated VM. Original bytes are compared with
the analysis ELF and independent Apple LLVM instruction words. Noncontiguous
Ghidra function bodies are validated range by range; provider no-return flags,
tail-call signatures and analyst-added function boundaries are not accepted as
runtime proof. The first opcode-0x15 query failed because Ghidra had no function
defined at the table-referenced entry; that refusal is retained separately from
the successful seeded retry. **Five successful queries** cover parser, dispatch,
handler, read helper and queue: 256 instruction addresses and 416 pcode
operations all stay inside their reported bodies, without truncation. The
dispatch body has one explicitly checked discontiguous four-byte tail. The
analyst seed changes only temporary analysis metadata, leaving firmware bytes
unchanged. The machine-readable [validation record](../reverse-engineering/findings/cpu-startup31n/validation.json)
contains query outcomes, exact hashes, checked ranges, counts and limitations.
The independent word check covers **282 unique firmware instructions / 1,128
bytes** and **316 driver instructions / 1,264 bytes**, with zero mismatches.
The 256 query instructions overlap the 282-word firmware check and must not be
added to it.

The public lead was the pinned [M5 SMP audit](https://github.com/Sowyu/m5-azahi/blob/82c90a5fd0b841d3acec4f558f9424b2cefec8bf/docs/audit-2026-09-25/smp.md),
which analyzes a different J714s / 18000.161.9 build. Its addresses were not
assumed to transfer: the parser, dispatch table, handler, helper and matching
data were located independently in this machine's 18000.161.10 artifacts.

## Firmware findings

**Confirmed static:** the matching command parser at `0x100c1c81d18` bounds the
operand count to 32. The command header carries operand count, opcode, sequence
ID and flags. The dispatch path at `0x100c1c81dd8` uses a 32-byte descriptor
stride. The table at raw offset `0x40d3e0` contains 248 entries; its checked
factory at `0x100c1c843b4` supplies the same table and extent.

**Confirmed static:** opcode `0x15` is associated with entry
`0x100c1c85af4`. The bounded handler uses the existing-address read helper
`0x100c1c830c8` in its 64-bit mode, then passes the value read to the buffered
command queue at `0x100c1c82f1c`. It does not directly program a reset register
with either of the trailing data operands. The queue and later compilation are
separate from the immediate read. This establishes read-and-queue behavior,
not successful restoration on hardware.

The three `MGP_CE0_ACC0_POWER_UP`, `MGP_CE0_ACC1_POWER_UP` and
`MGP_CE0_ACC2_POWER_UP` sequences each include six such records at the CPU
implementation-register bases independently identified in the sanitized ADT.
Together these account for all 18 cores. The selected records begin at raw
iBootData offsets `0x5ee34`, `0x61204` and `0x635ac`. Their trailing `0` and
`0x100` operands are **not literal replacement reset vectors**. The surrounding
sequences also contain other register operations and conditions; the selected
records are not a complete startup protocol.

**Confirmed static:** `MPMGR_D2A_IBOOT2B` contains conditional opcode-0 queued
32-bit writes to `0x280688010` or `0x280688008`, each with value 1. Their raw
data offsets are `0x50e58` and `0x50e94`. These occur in different control-flow
branches with other power-management work. Concatenating the two branches, or
substituting their values into the CPU1 experiment, would misread the program.
Neither branch supplies the already reviewed CPU1 mask of 2.

**Unknown:** which of these firmware programs has run on the current lab boot,
whether CPU1 needs any additional retained state, and what its effective first
instruction address is. A static restore program cannot establish any of those
facts. No new MMIO read, register write or firmware replay is qualified here.

## Why a local pair of start writes is a distinct test

The prior [platform review](native31l-platform-prepare.md) establishes that
`ApplePMGR::enableCPUCores` disables local interrupts and holds software locks
while dispatching `configMiscCores`. This review additionally checks both
start-addressing branches and the underlying writer against the original
kernel-collection carrier.

| Checked path | Behavior relevant to the next experiment |
|---|---|
| Selector-2 `configMiscCores`, `0xfffffe0009495b74..5c60` | Die bitmap dispatch at `5ba8`, local topology and ordinal calculations, then cluster-mask dispatch at `5c4c`; no target-state observer call between those dispatches. |
| Legacy branch, `0xfffffe0009495d24..5dc4` | Die dispatch at `5d54`, local mask calculation, then cluster dispatch at `5db8`; again no intermediate observer. |
| T6050 writer, `0xfffffe0009884dc4` | The resolved virtual target delegates the start-register write to the base writer. Its extra power-state handling does not apply to misc-cores map 8. |
| Base writer, `0xfffffe0009498870` | The actual mapped write is 32 bits, at `0xfffffe0009498948`. |
| T6050 register classification, `0xfffffe0009884f50` | Map 8 is not classified as a power-state register, so the optional power-state wait paths do not supply an intervening start-register completion poll. |

The table contains function dispatch locations, not a copied implementation.
Four selected chained references bind the T6050 writer/classifier and base
writer to the pinned carrier. As in the prior analysis, the relationship between
the observed property version and the runtime selector field is not upgraded
to a traced assignment.

**Inference:** host RPCs, JSON journaling and target observation between two
start writes are avoidable differences from this local driver path. Removing
them gives a meaningful independent variable without inventing a new register.
The macOS stores are not literally adjacent instructions; local calls and mask
calculation remain. The static evidence does not prove a timing deadline,
processor-memory ordering equivalence or a performance improvement. Native
31N must report those limits and retain the original record/identity criteria.

## Other public leads and exclusions

The [Aurora T8142 reset-vector relay](https://github.com/aurora-silicon/m1n1/pull/12)
addresses a specific RAM-chainloaded Mach-O layout: locked RVBAR can identify
the resident header before the executable vectors. It branches from that
consumed header to the vectors. This project's boot021 is different: the exact
live vector image begins at its verified base, and the observed RVBAR address
field already matches that base. The relay therefore does not justify another
entry patch here.

The related public clean-to-PoC change also does not identify a missing fix in
31M. The existing CPU1 recorder bodies and hooks already use `DC CVAC`; the
CPU0 helper's different publication path is not the CPU1 instruction-fetch
range. Neither of these negative applicability findings proves that CPU1
fetched the published bytes.

## Remaining path to all core types

A committed CPU1 identity is still the first necessary result. After verified
entry and a bounded rendezvous, later gates are the remaining cores in the
active Performance cluster, the second Performance cluster, then the Super
cluster, with their distinct topology, power and frequency controls retained.
The hardware inventory remains **12 Performance and 6 Super cores**. An online
count alone cannot establish coherent memory, timers, cross-core interrupts,
correct scheduling, frequency behavior or macOS-level efficiency.

If locally grouped starts are also negative, do not make the next test another
equivalent recorder. The matching firmware programs are now a pinned research
input for tracing effective reset selection and retained state. Further work
must connect a specific preparation step to this cold secondary-core path,
with independent evidence and a bounded hypothesis, before expanding hardware
operations.

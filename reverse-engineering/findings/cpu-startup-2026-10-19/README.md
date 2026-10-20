# t6050 secondary CPU startup: recovered evidence and remaining gates

2026-10-19. Offline continuation of the interrupted CPU-start research.
No hardware access, new REA session, VM, launcher change, m1n1 change or boot
was performed. The current baseline is attempt 26: native Omarchy, one CPU,
working keyboard and USB control link. These findings do not change the
attempt-27 delivery plan or enable another CPU.

This document contains behavior specifications and evidence locations, not
Apple source, pseudocode or extracted bytes. The input is this machine's
macOS 26.6.2 / 25G83 artifacts. Artifact digests and the new bounded byte check
are in [validation.json](validation.json). Prior REA/Ghidra results and saved
assembly remain under ignored build directories.

**The useful new result is that the T6050 driver's misc-cores group really is
PMGR reg[0] + `0x88000`.** Its cluster-control group is reg[0] + `0x20000`.
The descriptor-based 18-bit start layout remains strongly supported. Neither
fact establishes where a secondary enters in the custom raw boot environment.

## Evidence recovered

The old CPU-power handoff is
`kernel/experiments/cpu-power-smp/README.md`; the earlier independent REA
cross-check is `reverse-engineering/findings/cpu-startup-2026-10-13/`.
The interrupted October 19 session left `sptm-text.asm` and the extracted
watchdog member, but no completed new SMP handoff or saved watchdog result
was found in its stated notes/evidence folders. Findings that were only
described in that session's narrative are not promoted to confirmed results.

Local inputs:

| Artifact/evidence | Location |
|---|---|
| PMGR and platform members, symbols, extraction mappings | `build/macos-drivers/members/` |
| Earlier REA running notes and PMGR batch | `build/macos-drivers/evidence/notes-pmgr.md`, `ApplePMGR-batch1.txt` |
| Exact kernel assembly | `build/macos-drivers/evidence/kernel-text.asm` |
| Exact SPTM assembly and input | `build/macos-drivers/evidence/sptm-text.asm`, `build/macos-drivers/firmware/sptm.t6050.bin` |
| Independently checked PMGR assembly and REA results | sibling research workspace, `build/rea-lab/evidence/pmgr-all.llvm.txt`, `pmgr-config-misc-cores*`, `drivers/pmgr-cluster-enable*` |
| Topology and address translation | `hardware/adt/adt-sanitized.json` |

The derived PMGR members retain unresolved external collection references.
The earlier whole-function pseudocode gate rejected `configMiscCores` and
`enableCluster`; their bounded assembly and resolved table metadata are the
usable evidence. A decompiler function name or its rendered control flow
does not establish runtime behavior.

## Register groups and start masks

**Confirmed static.** `AppleT6050PMGR::initRegGroups`, at
`0xfffffe000987f094`, supplies the following tuples to
`ApplePMGR::initRegGroup` (`0xfffffe000947d5d0`):

| Group | Register map | Base offset | Call site / function offset |
|---|---:|---:|---|
| Cluster control, 2 | 0 | `0x20000` | `0xfffffe000987f0b4` / `+0x20` |
| Misc cores, 8 | 0 | `0x88000` | `0xfffffe000987f0e4` / `+0x50` |

The 212-byte function was checked against its original carrier mapping;
the group arguments were recovered from bounded ARM64 constant/dataflow
analysis and checked against the shared helper's symbol and saved assembly.
Map 0 resolves to PMGR reg[0] in `initRegMaps` (`0xfffffe000987ea54`,
previous independent REA/assembly evidence). ADT reg[0] is **bus-relative**
`0x80600000`; the arm-io range translates it to `0x280600000`.
Consequently misc cores is `0x280688000`, and cluster control is
`0x280620000`. Omitting the range translation would be an address bug.

**Confirmed static contract; runtime sufficiency unknown.**
`ApplePMGR::configMiscCores` (`0xfffffe0009495968`, prior bounded assembly)
uses misc-cores offset `+0` for the stop bitmap, `+4` for the start bitmap,
and `+8 + 4 × cluster-index` for the corresponding cluster's core mask.
The ADT cluster descriptors describe widths/positions `(6,0)`, `(6,6)`,
`(6,12)`. Its six-core fields produce 18 unique bits. The pinned public
m1n1 `57a9339` uses a four-bit stride and produces only 14 distinct bits
for those 18 cores, with collisions at bits 4, 5, 8 and 9.

The existing original `m1n1/test_start_bits.py` was rerun: PASS, including
malformed-layout checks. That is an arithmetic/model result, not an SMP
boot. Its secondary `acc-cores` fixture is a previously recorded value,
not a fresh independent hardware observation.

This closes the old question about the group's base offset and supports
review of the existing descriptor patch. It does not explain failure of
every secondary: within cluster 0 the old and proposed bit positions are
identical. A reset-entry or early-state failure remains possible.

## Cluster power is a separate interface

**Confirmed static.** `ApplePMGR::enableCluster`
(`0xfffffe000949e47c`) selects a physical cluster register from group 2,
preserves its other fields and requests low-nibble state `0xf` for on or
`0` for off. The bounded sites are `+0x138..+0x1c4` for addressing/request
and `+0x1c8..+0x208` for the optional wait, whose mask is bit 4 and expected
value zero. This is distinct from the generic per-device PMGR PS format;
do not apply the latter's `[7:4]` actual-state interpretation here.

The T6050 `configCPUComplexPowerState` function
(`0xfffffe0009880a64`) maps its three CPU complexes to SoC-cluster IDs
1, 2 and 3. The resulting candidate register addresses are
`0x280620004`, `0x280620008`, `0x28062000c`.
`_waitForACCClusterPowerUpGated` (`0xfffffe000949df18`, notably
`+0xa8..+0xfc`) also waits on software completion state, so a single
MMIO nibble is not proof that the entire macOS startup protocol completed.
No cluster power write or completion interrupt was exercised here.

## Raw boot and macOS entry must remain separate

**Confirmed static.** The saved XNU `__bootcode` at
`0xfffffe0007ca0000` distinguishes arrival reasons, and
`+0x98..+0x140` selects per-CPU stacks and one of two established handlers
using MPIDR-derived identity and per-CPU data.
The SPTM image has its own early entry/configuration path at
`0xfffffff0270a0000..0xfffffff0270a02c4`, including exception-vector,
translation, stack and implementation-defined register setup.

**Unknown:** which component owns the effective reset target in the current
custom raw boot, the locked RVBAR values of its offline cores, their incoming
register/exception-level state, and whether they would first reach `_start`,
`_vectors_start`, or a firmware trampoline. The macOS XNU entry is an OS-side
entry contract; it is not a measurement of the hardware reset vector.
Absence of an obvious RVBAR write in selected driver/kernel paths does not
prove that no firmware stage sets it.

Therefore two statements in the October 15 CPU-power notes are too strong:
“secondary start is PMGR-only” describes the selected PMGR request path,
not all prior initialization; “the reset vector is the boot object's entry”
is an unverified raw-mode hypothesis. The existing late-entry m1n1 patch
must be reviewed as a diagnostic hypothesis, not installed on that premise.
No SPTM code, system-register initialization sequence or security state is
to be copied, patched, bypassed or replayed into Linux.

## Idle, IPI and timeouts

**Confirmed static, bounded:** XNU's routine at
`0xfffffe00072f8310` has a WFI/acknowledgement loop at
`+0x50..+0x64` and does not return through that loop. A separate helper at
`0xfffffe00072f8390` contains WFI and a conditional return.
This does **not** prove that every WFI unconditionally powers down every
core in every firmware mode. The old blanket wording should not be used
to design an idle driver. Keep `idle=nop arm64.nowfxt` until the native
context-preservation/resume contract is established.

The saved kernel also exposes fast-IPI behavior, matching public m1n1
register names:

| Kernel function | Address | Observed request behavior |
|---|---|---|
| `ml_cpu_signal` | `0xfffffe00075068c0` | Same-cluster local request at `+0x1c`, cross-cluster request at `+0x30`; target core in the low byte, cluster in bits 23:16 of the cross-cluster form |
| `ml_cpu_signal_deferred` | `0xfffffe00075068fc` | Deferred marker bit 29; request sites `+0x20`, `+0x38` |
| `ml_cpu_signal_retract` | `0xfffffe0007506940` | Retract marker bit 28; request sites `+0x20`, `+0x38` |

These are **existing active-CPU signaling contracts**, not CPU power-on
or reset-vector programming. They do not authorize probing those sysregs.
The corresponding public names are in m1n1 `src/cpu_regs.h`; this review
has not established that every form is usable by Linux in raw mode.

The pinned m1n1 startup loop waits up to 100 iterations of 1 ms for a
shared entry flag. That is a software bound, not a measured startup latency.
macOS `enableCluster` takes its wait limit from driver state
(`0xfffffe000949e650`, function `+0x1d4`); this recovery did not establish
the active value. `cluster-enable-timeout-ms` is a property name, not
proof of a particular deadline. The extracted Apple watchdog member has
not received a completed review in this continuation. Public m1n1 disables
the secondary watchdog for ADT versions 2/3; leave that existing behavior
alone. Do not extend a boot attempt on an assumed macOS timeout.

## Next evidence, before an SMP attempt

The immediate delivery, keyboard and frequency-scaling work remains
independent. The cheapest SMP next step is a separately reviewed, bounded
**read-only census**, not a combined all-core/idle/frequency experiment.
No census has run or been authorized by this document.

1. Reuse the verified installed m1n1 and current hardware identity gates.
   Record its exact image identity, boot CPU MPIDR, image entry/vector
   addresses and sanitized CPU topology from already available metadata.
2. Review an explicit allowlist for the boot CPU and one secondary in the
   same cluster. Candidate observations are their ADT-derived RVBAR mirrors
   and their already mapped PMGR power-state registers. First establish
   that each proposed read is supported and has no read side effect in the
   current state; an address found in a binary is not that assurance.
   The existing m1n1 RVBAR read path is useful evidence for review.
3. Limit the proposed census to one read per approved field, a short
   overall deadline, no retry after a fault, no secondary-start call and no
   write, power transition, IPI, SPTM call or reset-vector modification.
   Do not read every CPU or scan the CPU_START block indiscriminately.
   If an offline core's window is not safe to read, leave it Unknown.
4. Compare the reset target to the running image without assuming equality
   is necessary: a firmware trampoline is possible. Keep unknown entry
   behavior separate from the confirmed bitmap mismatch.
5. A later **write-capable** single-secondary experiment needs its own
   reviewed plan. It must distinguish power-on, first instruction, shared
   entry flag, stable parked state and Linux online status. Also review
   m1n1's post-entry parking: its default secondary loop can enter
   `deep_wfi()`, so “Started” alone does not establish safe residence.
   CPU idle, hotplug and suspend should not be bundled into that experiment.

Success criteria progress from one stable secondary to one per cluster and
then all 18 CPUs, with Linux topology/IPI/load checks and measured idle
power at each expansion. Static evidence, VM execution and increased CPU
count alone cannot establish macOS-level performance or efficiency.

The old plan's “Linux side once m1n1 starts the cores: only the DT is needed”
is also too strong. Correct MPIDRs, spin-table entries and DT enablement
provide a candidate handoff interface. Each new core still needs verified
entry/heartbeat, timer delivery, IRQ/FIQ handling, bidirectional IPIs,
cache/coherency behavior and scheduler/load execution. Those checks precede
the next cluster; all-core enumeration by itself is insufficient.

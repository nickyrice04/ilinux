# 31O firmware findings: conditional restore programs and reset-mirror stability

2026-10-22. This is bounded static research and decoder validation for the next CPU1
investigation. **Native 31O remains HOLD.** This is not an SMP implementation
or a native execution result. The consumed 31N session
completed its local startup pair, but no channel committed CPU1 identity.
macOS and the installed lab remain unchanged by this analysis.

## Decision

**Confirmed:** removing the host work between the existing startup writes did
not produce an observed CPU1 entry in 31N. This does not justify another
unchanged marker campaign. Matching firmware has conditional per-core reset
address capture within per-cluster power-up programs. Those programs are not a
flat set of missing startup writes, and no new register write or replay is
qualified by this pass.

**Candidate observation, not a restart instruction:** compare CPU0 and CPU1's
existing reset-address
mirrors before and after the completed startup pair. The current campaign reads
those mirrors only before startup. A change after startup would reveal a
previously unobserved reset-address transition and direct the next investigation.
An unchanged result would close this particular observation gap without proving
an effective reset PC or instruction execution. This observation must use the
same proven addresses and 64-bit width, preserve opaque fields, and stop on
faults or unexpected data. The controller's separate review determines the
actual native allowance and failure ordering.

**Hypothesis, not a finding:** a startup transition might select or restore a
value after the pre-start check. Firmware provides a reason to test temporal
stability, but CPU1 is in CPU0's already active Performance cluster. A per-core
start does not establish that a per-cluster restore program runs. No claim is
made that this is the cause of the failure or that another mirror read is a
measurement of first fetch.

The immediate implementation is an original bounded RCfg decoder with synthetic
malformed-input tests. It makes these structures reproducible for future analysis
without interpreting or replaying firmware commands. Offline structural checks
cannot emulate proprietary reset behavior or establish the missing startup step.

## Matching inputs and method

The generic J716c firmware is mBoot 18000.161.10. Its decoded iBoot SHA-256 is
`b4822fc8902c3693ee590c544011603423a75291edd60afd31210d068a4ca120`;
the analysis-only ELF SHA-256 is
`f89169923c17be829c6b31c3c04c5695d06d42a42cea7390f61214202400dcee`.
Its header-derived analysis base `0x100c1aa4000` is not a measured live address.
The matching generic decoded iBootData SHA-256 is
`b43f7a31f6d980c6205f029dd80b2dc5ec0a2a52d7d3d801019736d9dcb5d11b`.
The earlier [31N firmware review](native31n-firmware.md) preserves extraction,
parser, descriptor, read-and-queue and driver provenance.

This pass uses REA/Ghidra in the isolated VM, then independently checks bounded
instruction words against the decoded original, its analysis ELF and Apple
LLVM. It independently decodes command framing, section boundaries and the
local condition/restore/end adjacency. Proprietary bytes, decompiler output,
disassembly and operand lists remain in ignored local research storage. The
public [validation record](../reverse-engineering/findings/cpu-startup31o/validation.json)
contains hashes, ranges, counts and tool limitations only. Five REA queries
succeeded; the initial missing-procedure refusal for the condition handler is
retained alongside its successful retry using a descriptor-derived analysis
seed. Their 512 instruction addresses and 3,189 pcode operations have no body
escapes, truncation or provider-removed blocks. Independent LLVM/original/ELF
comparison covers 706 unique instruction words (2,824 bytes), with zero
mismatches; the 512 REA addresses overlap this count. The seed changes only
temporary analysis metadata, not firmware bytes. Whole-function pseudocode is
still not treated as verified source. No firmware command program is interpreted
or executed.

## Every selected reset capture is individually conditional

**Confirmed static:** the 18 selected opcode `0x15` records at CPU
implementation-window bases are each immediately preceded by opcode `0xbe`
and followed by a matching `0xc8` end delimiter. This holds for the six cores
in each of the three `MGP_CE0_ACC{0,1,2}_POWER_UP` sequences. The wrapper's
operand identifies the cluster in bits 15:8 and the core ordinal in bits 7:0.

The descriptor for opcode `0xbe` identifies `0x100c1c88320`. It passes the
sequence and packed ordinal to `0x100c1b33234`, then dispatches the nested
conditional block. The predicate bounds the cluster index below three and
compares the core ordinal against a per-die/per-cluster count obtained through
`0x100c1af5ed0`. That helper caches counts; its population path examines three
groups of six positions per die. These are firmware's own topology conditions,
not proof of current Linux core state, identity or availability.

Together with 31N's independently checked opcode `0x15` read-and-queue behavior,
this establishes guarded capture of existing per-core register values for later
use. It does not establish a new literal reset vector, a requirement to rewrite
the mirror from Linux, or that any of those programs ran during 31N. Preserve
the separate cluster/core topology when implementing later SMP support; do not
replace these conditions with a whole-chip start mask.

## The two firmware startup records are alternatives

**Confirmed static:** the condition at raw iBootData offset `0x50e20` uses
opcode `0xc0`. Its matching descriptor names `0x100c1c87f14`. The handler tests
a 64-bit mask against a bounded software descriptor's field at `+0x50`, with
an explicit polarity, then invokes the conditional-record driver at
`0x100c1c81bd8`. For this record the mask is bit 46 and the polarity is the
nonzero intersection case. The software descriptor's live value is unknown.
This is not a newly discovered MMIO readiness read.

The conditional driver recognizes `0xc7` as its alternate-branch delimiter
and `0xc8` as the block end, with nesting handled separately. Consequently the
record at `0x50e58` targeting the cluster-2 start address and the record at
`0x50e94` targeting the cluster-0 start address are alternatives. The else
record is at `0x50e68` and the end at `0x50ea4`. Both selected records carry
value one for their respective first-core paths; neither changes the existing
CPU1 mask of two. Their surrounding power-management operations cannot be
concatenated into a CPU1 startup recipe.

## Reset programming and descriptor preparation are different stages

**Confirmed bounded ordering:** the retained handoff preparer
`0x100c1ae53b8` programs the selected per-core reset addresses through its known
call at `0x100c1ae5c88`. Later on that local path, call `0x100c1ae5ce8` enters
`0x100c1c81e9c` with a distinct initialization tuple. The call at
`0x100c1ae5c40` is on another branch and is not an earlier step to concatenate
with that path. These locations connect reset programming to later command
context preparation; they do not establish the active native branch or all
selected programs.

The only direct caller found for descriptor initializer `0x100c1b31c0c` is
`0x100c1c8202c`, inside that context preparation. Its bounded body selects
mode-dependent sequence collections and descriptor ranges, installs the command
handler table, and retains a command context. It is initialization work, not
a direct request to start CPU1. The numerical modes remain unassigned to
raw-boot or macOS labels without additional runtime evidence.

**Inference:** it is not justified to assume that every stored restore value
predates reset programming. The firmware contains a preparation path after
that programming, and the selected programs and captured values remain runtime
data. This narrows the hypothesis rather than identifying a missing Linux
write. A change in the mirror after the native pair would be more useful than
speculation about which static program must have run.

## What a temporal mirror comparison can establish

| Result | Supported conclusion | What it cannot establish |
|---|---|---|
| CPU1's decoded address field changes after startup | The pre-start mirror was insufficient to describe the later register state; investigate reset restoration/selection using the captured old/new relation. | The changed value is not a sampled execution PC or proof that a particular firmware program ran. |
| Only opaque high or low fields change | The register has a startup-dependent difference requiring separate interpretation. | Unknown bits must not be renamed as security, EL or mode fields. |
| CPU0 changes too | The observation is broader than a CPU1-only transition; stop and review. | It does not justify repairing either mirror or touching CPU0 reset state. |
| Both full words remain unchanged | The same observed reset mirrors survived the sampled startup interval. | It does not prove first fetch, correct reset release, retained context, instruction visibility or coherent secondary execution. |
| Read/guard/liveness failure | The measurement is incomplete and the target session must end. | Failed or absent reads are not zero values and must not trigger retries. |

Architectural RVBAR sampled on CPU0 would describe CPU0's architectural state;
it does not remotely sample CPU1. Likewise, an ADT debug window is insufficient
to qualify an arbitrary CPU1 PC read. This review adds no debug unlock, debug
register access, firmware replay, reset programming, additional core start or
persistent change.

The goal remains both Performance clusters and the Super cluster working with
coherent memory, timers, interrupts, scheduler topology, frequency management
and measured energy/performance. CPU1's same-cluster first execution remains
the immediate gate. A positive identity would permit a separately reviewed
rendezvous experiment; another negative temporal comparison would require a
new discriminator, not another equivalent boot attempt.

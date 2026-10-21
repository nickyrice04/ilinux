# 31F startup target review

2026-10-21. Read-only source, sanitized ADT and retained REA-evidence review
after the consumed 31E result (`b8cf1d9`). No new target operation, new REA
session, firmware change or CPU start occurred in this review. Raw Apple
material remains in ignored build storage; this document records original
behavioral findings only.

**The two CPU1 start stores address the reviewed target correctly.** The known
cross-cluster bitmap bug does not affect CPU1. The next informative test is
earlier, identity-independent entry recording using the same CPU1 start
request; there is no evidence here for an additional power-register write.

## What 31E established

The [native result](../attempt31e-2026-10-21-result.md) records valid CPU0
EL2/VHE permissions, all 16 translation probes, body/hook/whole-text readback,
and acknowledgements for both startup stores. It retains 93 early-recorder
samples at phase zero and 94 reset/spin observations without a reset record.
This narrows the problem but does not prove that CPU1 executed no instruction.
CPU0 translation and readback do not establish CPU1 instruction visibility,
effective reset destination, incoming mappings or cache state.

## CPU1 selection and masks

The pinned public m1n1 source is `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
Its `src/smp.c` indexes `cpu_info` by ADT `cpu-id`; die, cluster and core
come from separate fields of ADT `reg`. The runtime census checks every one
of the 18 active records and all 14 unused records against the sanitized ADT.
These checks were inherited by 31E, not inferred from a Linux CPU number.

| Item | Reviewed CPU1 value | Evidence |
|---|---|---|
| Logical ADT CPU ID | 1 | Sanitized `/cpus/cpu1`; runtime census |
| ADT register / die / cluster / core | `0x1` / 0 / 0 / 1 | ADT plus exact runtime `cpu_info` checks |
| Core type | M, macOS Performance class | ADT; inventory's macOS performance-level observations |
| CPU implementation window | `0x210150000`, length `0x9018` | ADT low/high words and runtime record |
| CPU start base | `0x280688000` | Runtime global, translated ADT and bounded PMGR analysis |
| Die-wide start store | `0x280688004`, value 2 | Public source and original controller |
| Cluster-local start store | `0x280688008`, value 2 | Public source and original controller |
| Expected MPIDR low 24 bits | `0x40001` | **Inferred** from upstream M-core mapping, not yet observed on CPU1 |

The boot CPU's observed MPIDR low 24 bits are `0x40000`. ADT `reg = 0x1`
is not itself CPU1's MPIDR. Source commit
`5d84c4c34d3fbb8bbe6230cecd5e8df8428335a2` documents M-core and P-core
MPIDR examples and fixes M-core classification. It supports the expected
mapping but is not a measurement of this machine's waiting secondary.

Existing bounded REA analysis locates
`AppleT6050PMGR::initRegGroups` at `0xfffffe000987f094`, the misc-cores
group at map 0 + `0x88000`, and
`ApplePMGR::configMiscCores` at `0xfffffe0009495968`. The map's ADT
bus address `0x80600000` translates to physical `0x280600000`.
The static interface uses offsets +4 and +8 + 4 × cluster for the start
bitmap and cluster mask. See the [recovered evidence](../../../reverse-engineering/findings/cpu-startup-2026-10-19/README.md)
and its byte-validation record. The carrier SHA-256 is
`26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`;
static interfaces are confirmed, runtime sufficiency remains unknown.

For this particular target, both index calculations yield bit 1:

- Pinned m1n1: `4 × cluster + core = 4 × 0 + 1 = 1`.
- ADT descriptor layout: `cluster_start + core = 0 + 1 = 1`.

Both therefore request `1 << 1`, value 2. Changing the cluster stride alone
would repeat the same CPU1 request and cannot explain this timeout.

## A separate gate before additional clusters

ADT cluster descriptors are widths/positions `(6,0)`, `(6,6)`, `(6,12)`.
The existing original
[`0002` descriptor patch](../../../kernel/experiments/cpu-power-smp/m1n1/0002-smp-pack-t6050-start-bitmaps-from-ADT-clusters.patch)
and its arithmetic tests address the legacy four-position stride. Across
all 18 CPUs, the legacy calculation has 14 distinct bits and collisions
at bits 4, 5, 8 and 9; the descriptor calculation has 18 distinct bits.
Keep that correction as an explicit reviewed prerequisite for cross-cluster
expansion. It is not permission to start extra cores during 31F.

The topology is two six-core M clusters and one six-core P cluster. The M
class is macOS **Performance**, and the P class is macOS **Super**; M does
not mean efficiency. CPU1 remains in the already-active CPU0 M cluster.
After same-cluster entry and coherency work, cross-cluster startup, the P
cluster, per-cluster DVFS, interrupts, capacities and scheduler placement
need separate measured validation. Enabling CPU1 alone cannot demonstrate
macOS-equivalent heterogeneous scheduling or all-core performance.

## Why an earlier recorder has greater diagnostic value

The consumed 31E hook is at image offset `0x8fc`. Its recorder reads MPIDR
and silently bypasses publication unless the low 24 bits equal the expected
CPU1 value. Thus phase zero includes an unexpected identity as well as
failure to reach the hook, a fault on the first register read, or an
invisible record store. The first several reset-path instructions precede
that hook. A complete source/image review is needed for changing that path;
the parallel entry review owns that work.

For 31F, the original entry design should publish a stackless marker from
the earliest reviewed vector entry **before the first system-register read**,
then record MPIDR, CurrentEL and the selected SCTLR in separate phases.
It must preserve and classify an unexpected CPU's record, but that diagnosis
must never authorize callbacks or further startup. A complete expected-CPU1
record plus the existing arrival proof remain prerequisites for callbacks.

**The vector-zero slot is also the same-EL synchronous-exception slot when
SP0 is selected.** Public `src/start.S` and the exact-image entry audit confirm
that the proposal instruments a shared entry location, not an exclusively
reset-only callback. A first marker cannot establish CPU1 identity or reset
provenance; even a later MPIDR classification does not by itself identify the
reason for entry. Unexpected CPU0 or another identity must be preserved and
stop the controller. The replay must restore the original X9 assignment and
resume the original dispatch. Exception routing, recursion and hardware
visibility are not simulated by the ordinary instruction-prefix model.

| Observed outcome | Supported interpretation / next branch |
|---|---|
| No first marker | Earliest hook still unobserved; effective reset route, instruction visibility or first store remain unresolved |
| Marker only | Some entry/store execution observed; identity and register state remain unknown |
| MPIDR phase, unexpected identity | Preserve expected-topology classification; stop without treating it as CPU1 arrival |
| Expected identity, stops before SCTLR | Narrow the failing entry interval; do not infer cache bits from zeros |
| Complete early record, no normal arrival | Use recorded state to examine the remaining original reset path |
| Complete record and normal arrival | Run the already bounded conditional requests and final park check |

Do not append speculative PMGR, RVBAR, cluster-power or firmware operations
to compensate for a missing record. The same-cluster CPU1 request, earlier
entry evidence and one bounded session make the next restart more informative
without conflating independent hardware hypotheses. The sanitized outcome
must distinguish first-entry progress from CPU1 arrival, Linux SMP and any
performance result; the latter remain unverified until their own tests run.

# 31X independent CPU startup and observation audit

2026-10-24. **No new startup implementation defect or verified software fix was
found in the consumed 31A–N path. The negative observations still do not establish
that CPU1 executed no instruction, or that every compatible software route is
blocked.** The strongest missing evidence is the secondary's effective entry and
incoming context, followed by a version-qualified accepted alternative host.

This audit read the frozen controllers, original recorders, result JSON,
sanitized ADT and retained public boot021 sources. No target, VM, firmware,
installed image or settings operation occurred. No frozen file was edited.
The read-only audit checked all 18 topology records, all 18 separately retained
die-local ordinal/start-mask records, the consumed result inventory, and seven
boot021 source hashes. Original parsing ran locally; downloaded source did not.

## What was actually tried

There were **ten consumed attempts with both CPU1 stores acknowledged**: 31C,
31D, 31E, 31F, 31G, 31J, 31K, 31L, 31M and 31N. Every one targeted CPU1 in
CPU0's M/Performance cluster. 31A was a read-only census; 31B and 31H stopped
before startup; 31I failed during connection and has no new startup result.
None of these tests reached Linux SMP. See the
[31N native result](../native/boot/attempt31n-2026-10-22-result.md) and its
[controller record](../native/boot/attempt31n-controller-2026-10-22.json).

The experiments progressively covered distinct hypotheses:

| Evidence | What it narrows | What remains open |
| --- | --- | --- |
| 31D UART RAM isolation | Early diagnostic UART access was removed from the selected continuation. | Effective reset route and incoming CPU1 state. |
| 31E/F published recorders; 31F vector-first marker | CPU0 permissions, complete patched text and the chosen branch destinations were checked. | CPU1 fetch, permission and store visibility. |
| 31G/J power/state samples | The selected CPU1 domain changed actual state 0→15; later opaque state changed 0→2. | Instruction execution, reset release and PC; those fields are not execution acknowledgements. |
| 31K cold-entry tripwire and CPU0 control | Both candidate entry locations were instrumented; the recording mechanism worked on CPU0. | A different effective entry or an earlier CPU1 fault. |
| 31L/M Normal, Device and maintained observations | A Normal-memory alternative and CPU0 cache-observation limitations were tested. | CPU1's private/noncoherent context and accessibility of either destination. |
| 31N single local pair | Both known stores completed without host RPCs or journaling between them. | Any additional firmware/hardware prerequisite; elapsed hardware timing was not measured. |

## Checks that did not reveal a new bug

**Topology and addressing.** The
[sanitized ADT](../hardware/adt/adt-sanitized.json) and
[31G ordinal observation](../native/boot/attempt31g/topology-observation.json)
agree on three six-core clusters: M0, M1 and P. CPU1 is local core 1 in M0;
its physical-core bit is 1 and die-local cluster ordinal is 0. Its two known
32-bit startup values are therefore both 2 at the already consumed addresses.
The legacy four-bit cluster packing defect affects later clusters, not CPU1.
The initial ADT sanitizer omitted several property values; a property name's
presence is not a decoded value. The separate 31G collection supplies the
needed ordinals and `acc-cores` mapping. Neither source singles out CPU1 as
disabled or harvested. [Topology interpretation](cpu-topology31f.md).

**Entry, addresses and lifetime.** The
[boot021 layout](../kernel/experiments/smp31/boot021-ram-layout.json) and inherited
controllers bind the vector at image offset 0, cold entry at 0x800, CPU1's
dedicated stack and target slot. The full-width Normal-prefix address encoder,
relative branches and source publication order agree with those contracts.
Bodies precede hooks; CPU0 makes no post-start restoration of those hooks,
stack or target. The raw image's base is its vector base, so the separate
Mach-O-header-relay fix has no established applicable header here.
[31N image/publication audit](native31n-result-review.md).

**Cache observation.** CPU1-fetched patched spans already use clean-to-PoC
publication; changing their publication from PoU to PoC would repeat existing
behavior. The 31M observer owns and initially cleans disjoint 128-byte spans,
qualifies CPU0 cache geometry and forbids later CPU0 record stores. Its paired
cached/maintained reads stop on any partial record. No dirty-zero overwrite,
wrong field offset or stale-zero-only observer defect was found in that scope.
This still does not establish that CPU1 participates in the relevant coherency
domain. [31M observer](../kernel/experiments/smp31m-observer/observer.py).

**Identity and acknowledgement.** The earliest Normal marker precedes MPIDR
access. An unexpected nonzero identity or phase stops and is retained rather
than silently becoming a clean timeout. Consequently, a wrong expected Aff2
value alone cannot explain an all-zero observed prefix. Post-start reads use
guard-free helpers; they do not clear the shared exception counter through the
ordinary bulk-read interface. The 31N return token and clean diagnostics confirm
the CPU0 leaf's completion, not a remote CPU instruction or firmware response.
[Start-pair contract](../kernel/experiments/smp31n-startpair/plan.py).

**Idle policy is later.** Both original Normal prefixes have no WFI/WFE and
store phase 1 before their first system-register read. The cold tripwire ends
in a plain branch loop. Public m1n1 publishes secondary identity and its arrival
flag before its WFE/deep-WFI loop. Thus Linux idle policy or a post-arrival WFE
fix does not explain these missing earliest markers. Warm return from a known
secondary sleep state is a different transition from the unobserved initial
entry tested here. [Pinned m1n1 source](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/smp.c).

**A wake event was not wholly absent.** Inherited preparation calls
`smp_set_wfe_mode(true)`, whose hash-matched implementation issues unconditional
SEV after changing the mode. Its IPI loop targets only already-alive secondary
records; it does not establish a CPU1 IPI. That SEV precedes the start pair.
Neither the fixed 31N pair nor public m1n1's per-core startup adds a post-pair
event. Consequently, a powered-down target losing an earlier event and later
waiting in a firmware holding pen remains a hypothesis, not something the
pre-start SEV rules out.

A post-pair SEV would be a distinct stimulus, but there is no located CPU1
waiting PC, holding-pen release predicate or version-qualified firmware contract
requiring it. The prior bounded macOS start-caller work establishes the
`function-enable_core` → PMGR request route, while the separately identified
fast-IPI routines concern active-CPU signaling; it does not qualify an omitted
post-power event. This is not an exhaustive claim about every earlier firmware
caller. Reject a blind event/IPI poke as the next implementation now. Reconsider
only with evidence of that holding pen and a defined observable prediction;
success would support a wake dependency, whereas another absent marker would
still not prove no execution. [Bounded platform caller](native31l-platform-prepare.md),
[active-CPU IPI distinction](../reverse-engineering/findings/cpu-startup-2026-10-19/README.md).

## Ranked remaining candidates and falsification

These are evidence requirements, not a new native-test authorization or a
claim that the candidates are equally likely.

| Rank | Candidate | Why it survives | Safe next discriminator |
| --- | --- | --- | --- |
| 1 | Effective secondary entry, incoming translation/protection or an early fault differs from the assumed raw path. | The reset mirror is not a sampled PC. CPU0 AT/permissions, EL2/VHE and store controls do not describe CPU1. | First qualify a version-matched firmware/monitor observable or accepted-host trace that identifies the physical secondary, effective entry and early fault/context. Audit its side effects and provenance offline before proposing collection; arbitrary CoreSight/MMIO reads are not qualified by an ADT range alone. |
| 2 | An accepted alternative host prepares a missing state while retaining a continuing monitor contract. | The existing positive guest report concerns another host route; the relevant accepted host/context and physical-secondary chain are not yet available. | Obtain the actual public revision/object/context and physical MPIDR-linked execution evidence, then compare with the local board/build. A guest CPU count or a source scaffold alone cannot falsify the local raw-path failure. |
| 3 | CPU1-specific state, indexing or per-core preparation differs from another same-cluster core. | All ten starts targeted CPU1; this is a coverage gap. No current topology evidence identifies a CPU1-specific exception. | An independently qualified same-cluster CPU2 entry would localize the failure away from a universal M0 inability. A second negative would not distinguish common context failure from a broken observer. Audit all target-bound stack, identity, reset, power and record assumptions first; changing only the start bit is insufficient. |
| 4 | Another cluster/core type has a different valid startup prerequisite or route. | M1 and P/Super targets have not been tested; their cluster-power state and incoming preparation are unqualified. | Prefer a validated successful reference sequence or passive state trace for that cluster before designing a new test. Do not turn generic PS active state or another cluster's register offset into a reset-release contract. A blind negative adds several variables. |
| 5 | An early store or barrier prevents all subsequent recorder progress despite some instruction fetch. | In 31L–N, Normal runs before Device; a fault at the first store or blocked synchronization can suppress both. Earlier Device-first 31F/K narrows but does not eliminate the general incoming-context problem. | Resolve the destination's CPU1 accessibility or obtain an independently qualified early-fault/PC channel. Another equivalent RAM marker is not independent evidence. |

The channels must not be multiplied into a claim of four independent first-fetch
tests. They cover two candidate entry addresses and multiple observation methods,
but later Device recording depends on earlier Normal-prefix progress. Also, a
bounded three-second negative cannot exclude arbitrarily late arrival. The
markers are persistent and the ordinary public m1n1 arrival wait is shorter;
there is no new evidence that merely extending this deadline would resolve the
missing state.

## Which untested physical target would be informative?

| Target | ADT identity | New variables versus CPU1 | Assessment |
| --- | --- | --- | --- |
| CPU2 | M0, local core 2; expected affinity 0x40002 | Per-core identity/state, stack and observation binding | Least-confounded physical control if a separately reviewed target comparison is chosen; no present evidence promises success. |
| CPU6 | M1, local core 0; expected affinity 0x40100 | New cluster, six-bit die packing, cluster preparation and cross-cluster visibility | Less diagnostic than CPU2 for isolating a CPU1-specific failure. |
| CPU12 | P/Super, local core 0; expected affinity 0x10200 | New cluster plus core type and its startup context | Potentially distinguishes a type-specific route, but currently lacks a qualified preparation contract. |

The ADT provides topology, not successful secondary execution. The startup
plan gives CPU6/12 die masks 64/4096 and cluster-local masks 1; these facts do
not establish their cluster-power or reset prerequisites. Conversely, CPU1
shares CPU0's already active cluster, so an omitted *new-cluster* power-on alone
is a weak explanation for that particular failure. The prior bounded platform
review found no omitted per-core cluster-restoration call; earlier firmware
preparation remains unknown. [Prior review](native31n-result-review.md).

Linux eventually requires every entering CPU to have the specified exception
level, MMU/cache state and coherency participation; an enable-method description
does not create those states. These are later acceptance requirements, not proof
of the current raw-entry cause. [AArch64 boot contract](https://docs.kernel.org/arch/arm64/booting.html).

## Engineering disposition

No new diagnostic implementation follows from this audit alone: a useful PC,
fault or context collector still needs a qualified source. Keep the current
native HOLD while pursuing the ranked inputs. Reset redirection, guessed
cluster writes, blind extra-core attempts, Linux scheduler/capacity edits,
longer unchanged waits and relabeling a store reply as CPU1 acknowledgement do
not repair the missing evidence. A CPU2 comparison remains a conditional
coverage experiment, not a discovered workaround or an automatic next boot.

The audit preserves the useful distinction: the tested raw path repeatedly
fails to produce observable CPU1 identity, while a universal Apple-only
impossibility remains unproved. The separate public-source and firmware tracks
may supply a concrete new prerequisite; none is invented here.

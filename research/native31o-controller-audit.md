# 31O: independent audit of the consumed 31N entry experiment

2026-10-22. Read-only source, sanitized-result and exact-image review at report
commit `922aeb3`. No native operation, VM run, installed-image change, or frozen
controller edit was performed by this audit. Original behavioral conclusions
only. This document does not qualify another native attempt by itself.

## Result and what it changes

**Observed:** 31N completed its single fixed CPU0 startup pair, including the
expected return token and clean diagnostics. Both stores were acknowledged.
CPU1 changed from power actual 0 to 15 and opaque implementation-state byte 0
to 2. Normal vector/cold channels each completed 126 paired observations and
maintenance acknowledgments without committed identity. Device channels also
remained negative. The controller reached its ordinary arrival timeout;
the human returned to Macintosh HD within the stated bound.

The intermediate host transactions removed by 31N are therefore not a
sufficient explanation of the observed first-entry failure. Their removal is
still a better match to the local driver operation, but repeating that pair
with an equivalent record would not distinguish the remaining hypotheses.
Neither the power transition nor the completed pair proves CPU1 instruction
execution. The consumed [31N report](../native/boot/attempt31n-2026-10-22-result.md)
and final JSON remain authoritative.

## Exact-image and controller checks

| Question | Checked evidence and conclusion |
|---|---|
| Does the controller execute CPU1 code through CPU0's RX alias? | No. The RX alias is used for CPU0 helper calls. The CPU1 vector/cold hook branches are PC-relative; Normal prefixes materialize the owned record's identity address with four full-width immediate pieces. No omitted upper address half was found. |
| Are branch destinations wrong? | The hooks at image offsets 0 and `0x800` reach original prefixes at `0xc00` and `0xd00`. Their final branches reach the previous recorders at `0xa00` and `0xb00`. The independent exact-image audits pass. |
| Does an architectural system-register read precede every marker? | No. Each Normal prefix's first store precedes its MPIDR read. Earlier Device recorder prefixes likewise store before reading MPIDR or CurrentEL. A system-register trap alone cannot explain phase zero if that preceding store was executed and externally visible. |
| Is the first marker dependent on the reset stack? | No. The prefixes have no stack access or stack write. Dedicated-stack initialization is necessary for later m1n1 entry but cannot repair a failure before these first stores. |
| Are startup values/topology incorrect for CPU1? | The live census binds CPU0/CPU1 to the active M0 cluster and fixed implementation windows. Value 2 selects its local core 1. The corrected six-core global packing differs from legacy packing only for later clusters, not CPU1. |
| Does the generic helper inherit guarded memory reads after startup? | The post-start paths use fixed CPU0 helper calls. They do not issue the old memory-read request that changes the shared exception guard. The separate clean check reads the diagnostic word without resetting it. |
| Were CPU1 code bytes only cleaned to PoU? | No. Vector, cold and Normal-prefix publications use `dc_cvac`, followed by `ic_ivau`, before startup. CPU0-only helper setup is a different publication path. The prior exact dispatch audit already binds CVAC to the intended image implementation. |
| Do fresh text reads prove the CPU1 instruction stream? | No. They establish CPU0-visible text and publication completion. CPU1's effective fetch address, execution regime and participation in the same coherency domain remain unobserved. |

The independently rerun original entry-contract tool passes 56 address cases
and 112 explicitly assumed translation cases. The Normal-prefix image audit
also passes, checking 1,371 relocations and the reviewed padding/symbol ranges.
These checks use boot021 SHA-256
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`
and symbol SHA-256
`751a9643a2196eda44efba4789aa789465b2b75e9546be460946d2fa4c70ac11`.
They do not execute the prefixes or model an Apple firmware reset.

Commands, relative to the repository:

```sh
python3 -I kernel/experiments/smp31l-analysis/entry_contract.py \
  --image virtualization/jobs/069-smp31k/out/boot021.bin \
  --symbols virtualization/jobs/069-smp31k/out/m1n1-symbols.txt \
  --report native/boot/attempt31k-controller-2026-10-22.json
python3 -I kernel/experiments/smp31l-candidate/builder.py \
  --image virtualization/jobs/069-smp31k/out/boot021.bin \
  --symbols virtualization/jobs/069-smp31k/out/m1n1-symbols.txt
```

The first command deliberately supplies the older result accepted by its
frozen schema; it does not claim to ingest or revalidate 31N's result.

## Observation dependencies that must remain explicit

**Confirmed source behavior:** the Normal and Device markers are serial paths,
not independent fallback executions. A first-store failure in a Normal prefix
can prevent entry to its later Device recorder. Normal records reside in a
separately allocated helper span; Device records reside in the image's
SMP-shared span. CPU0's mapping tests establish neither span's accessibility in
CPU1's incoming translation regime. The maintained Normal negative cannot
repair or detect a fault before that first store.

This is a limitation, not a newly found bug: the prefix source and prior
release already document it. Reordering these same markers or moving a store
into the code page would introduce a different unknown permission contract
without independently observing the effective reset route. That alone is not
a reason for another reboot.

Likewise, architectural instruction maintenance should not be described as
necessarily CPU0-local. Arm documents `IC IVAU` broadcast within the issuer's
Inner Shareable domain, with additional execution synchronization still
required. That does not establish a powered-down T6050 core's state or domain
membership. A whole-cache operation is not justified simply by renaming the
already present `IC IVAU` as local-only. See [Arm's architecture correction](https://documentation-service.arm.com/static/60082ae0773bb020e3de6c10).

## Concrete missing observation: reset state across the power transition

**Confirmed source/result:** the complete CPU0/CPU1 reset-register observations
occur in preflight, before either start store. No corresponding post-start
reset-register sample exists in 31N. The unchanged preflight mirrors and their
address fields therefore do not establish persistence through CPU1's observed
power transition.

A narrowly bounded follow-up could compare the same previously qualified
64-bit implementation-register addresses before startup, after the completed
pair, and at the final sample. It would distinguish a stable preflight mirror
from a powered-bank or autonomous-firmware change. This is a different
observation from another RAM marker and can be bundled with a stronger
firmware-derived discriminator if one is found.

Such an implementation would need its own review: bind both addresses to the
live ADT; validate 64-bit access and translation before startup; use an existing
guard-free leaf after startup; enforce fixed phases, deadlines and read budget;
record partial completion on error; never retry. Keep raw values transient and
publish only address-field relation, equality, lock-bit and changed-field
classifications. Do not change RVBAR or expand to adjacent registers. A
matching result would still not prove PC, first fetch, an effective reset route
or execution, and cannot justify replaying firmware.

**Recommendation:** continue matching-firmware command/condition analysis as
the primary work. Do not release a marker-only repetition. If a proposed
startup prerequisite is independently established, add the reset-state
persistence observation to that bounded test rather than spending a reboot
only re-proving the existing preflight relation. There is no demonstrated
instruction-entry fix from this controller audit.

The all-core goal still requires verified CPU1 identity and rendezvous, then
coherency/timer/IPI checks, the remaining M0 cores, the other Performance
cluster and the Super cluster. Twelve Performance and six Super cores must
retain their distinct identities, capacities, power and frequency handling;
an online count alone is not macOS performance or efficiency parity.

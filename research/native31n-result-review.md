# 31N review: what the consumed 31M experiment rules out

2026-10-22. Independent offline review of M1's consumed 31M result, release
`24aa8eb`, execution `f874095`, report `0a2590b`. No target access, macOS change,
VM, third-party code execution or modification of a frozen attempt occurred in
this review. Original behavioral findings only; this is not a native release.

## Result and immediate decision

31M reached its natural arrival timeout after both CPU1 start stores were
acknowledged. Both paired Normal channels completed 128 samples, 768 reads and
128 maintenance requests without observing a prefix or committed identity.
The separate Device, Normal and maintenance controls passed. CPU1's generic
power actual state changed from 0 to 15; its opaque implementation-state byte
changed from 0 to 2. These are power/state observations, not execution evidence.
See [M1's report](../native/boot/attempt31m-2026-10-22-result.md).

**No instruction-entry fix is established by this audit.** Another unchanged
start with an equivalent RAM marker would not address the remaining first-fetch
uncertainty. In particular, two useful fixes found in another M5 project do not
automatically apply to the already tested image here: a Mach-O-header relay and
changing instruction publication from PoU to PoC. Their prerequisites must be
compared with this image and this native evidence before proposing another boot.

The maintained negative records constrain the CPU0 observation hypothesis but
still do not exclude CPU1 execution, an unobserved entry path, an earlier fault,
different translation or private CPU1 data. CPU0's successful controls do not
establish CPU1's execution context.

## Independent checks of the start and entry chain

| Checked item | Evidence and conclusion |
|---|---|
| Core identity | Live census requires CPU1 to be local core 1 in die-local cluster 0, alongside CPU0. The complete topology remains 12 Performance cores in M0/M1 and 6 Super cores in P. |
| Start addresses and ordering | The controller submits the existing aligned 32-bit value 2 first to `0x280688004`, then to `0x280688008`. This agrees with pinned m1n1's ordering and the separately reviewed T6050 PMGR mapping. |
| Start-mask correction for later clusters | The four-bit legacy stride is wrong for six-core clusters, but CPU1 is bit 1 in either calculation. That later-cluster bug does not explain the current CPU1 failure. |
| Incoming stack and target | Dedicated CPU1 stack/target variables are initialized and checked before either request. No dummy-stack replacement follows the timeout. |
| Vector and cold hooks | The original branch encoders, image audit and full live text comparisons cover the vector hook at offset 0 and cold hook at `0x800`. Normal prefixes are at `0xc00` and `0xd00`. No wrong branch displacement or truncated full-address materialization was found. |
| Hook lifetime | Bodies are published before hooks; all publication completes before either CPU1 request. The observer does not restore or overwrite these hooks while CPU1 may run. |
| Effective reset destination | The matching reset mirror and its masked relation to the image are observed. CPU1's actual PC, instruction fetch and incoming regime remain unknown. Do not turn the relation into proof of execution at offset 0. |

CPU1 does not require a new cluster merely to share CPU0's active M0 complex.
The existing macOS platform investigation found no omitted per-core call to
cluster restoration in the bounded `startCPU`/`enableCPUCores` path. This does
not prove that all earlier firmware preparation is present in raw boot.

## Why a resident Mach-O-header relay is not presently qualified here

The public [Aurora PR 12](https://github.com/aurora-silicon/m1n1/pull/12)
addresses a distinct layout: locked RVBAR points to a consumed resident Mach-O
header before the vectors. Its guarded relay is unnecessary when RVBAR already
equals the vectors, and its header case requires Mach-O magic at that location.
Its reported native result is evidence for its tested hardware and configuration,
not this machine's effective reset route.

The retained boot021 is built using `m1n1-raw.ld`, not the Mach-O linker layout:

- `_base` and `_vectors_start` are both offset 0; `_start` is offset `0x800`.
- Pinned `P_GET_BASE` returns `_base`. The census then compares the complete
  first 4 KiB at that returned address with the raw boot021 image, independently
  of the reset-register classification. Every relevant native preflight passed.
- Exact image SHA-256 remains
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
  An independent standard-library byte check confirms its first instruction is
  the expected vector instruction, and is not the Mach-O magic word.
- CPU0/CPU1 reset mirrors' tested address fields equal that same base, with
  bit 11 clear. This is not a recorded `header-before-vectors` layout.

Consequently, there is no demonstrated header at the currently observed reset
address to replace. Do not write a relay there on the strength of the PR alone,
scan arbitrary preceding memory or replace the installed boot object to imitate
an unrelated layout. If another firmware-selected entry exists, identify its
provenance and ownership independently.

## Instruction publication already reaches PoC

A separate audit checked the proposed cold-secondary PoU/PoC explanation against
the actual frozen source, rather than inferring it from helper setup code:

| CPU1-fetched span | Existing publication |
|---|---|
| Vector recorder and hook | `smp31g.py::publish_recorder`: `dc_cvac` on the write alias, then `ic_ivau` on the identity fetch alias |
| Cold recorder and hook | `smp31k.py::prepare_cold_entry`: the same PoC publication |
| Normal prefixes and replacement hooks | `smp31l.py::publish_normal_prefixes`: the same PoC publication for every part |
| CPU0-only helper routines | Some use `dc_cvau`; these addresses are not fetched by the CPU1 prefixes or inherited reset continuation. |

The pinned client serializes `dc_cvac` as opcode `0x308`. Independent decoding
of the exact boot021 dispatch table gives case `0x2d48c`, calling `0x27b00`;
the existing image audit binds its `DC CVAC` instruction at `0x27b20`.
For comparison, `0x309` reaches the separate CVAU routine at `0x27700`, and
`0x30a` the CIVAC routine at `0x277a0`. These are distinct dispatch paths,
not a mislabeled client method. The common proxy completion executes DSB SY
and ISB. The fixed published spans are aligned and fit the measured 64-byte
cache-line geometry.

Thus changing these CPU1 spans from CVAU to CVAC would make no change: they
already use CVAC. No such patch or extra native attempt is justified by this
lead. Publication to PoC still does not prove CPU1's first fetch or its complete
instruction/cache/translation context.

## What would make the next test useful

Prioritize a defined first-fetch or startup-prerequisite discriminator with
independent provenance. A useful next candidate must name the missing condition,
explain why the previous controls did not cover it, and predict at least one
distinct observable outcome. Qualifying a different actual entry route or a
documented startup prerequisite would satisfy that standard; another equivalent
negative-memory probe would not.

### Selected hypothesis: host observation between the startup stores

The follow-up source audit identified a distinct difference that is worth a
bounded test. In the consumed controller, the first store is followed by power
and state sampling, paired cached/maintained observations, freshness checks and
durable host journal writes before the second store. A replay of the unchanged
31M controller against project-owned synthetic interfaces counted **127 external
interface/proxy calls and 33 journal callbacks** between those two store calls.
It did not measure their duration on hardware, and the public native report does
not supply a reliable inter-store timing measurement.

The pinned public m1n1 start routine and the previously reviewed macOS PMGR
request path issue their corresponding stores on-target without that host
transport/journal gap. Their source does not prove a required maximum interval;
31M's observed power transition also does not prove that no timing-sensitive
startup dependency exists. This is a testable instrumentation difference, not
an established firmware defect.

The original [31N fixed-pair leaf](../kernel/experiments/smp31n-startpair/README.md)
retains exactly the two known addresses, 32-bit value 2, order and completion
barriers, but performs them in one CPU0 call with no host transactions between.
All preconditions remain before it; all observations move after it. It leaves
interrupt state unchanged and is not atomic. A failed or missing reply must
report zero, one or two stores possibly completed, with no retry or further
target access. Only a valid completion token and clean diagnostics allow both
stores to be acknowledged.

This changes the stimulus rather than adding another equivalent marker. A
committed CPU1 identity is the decisive positive observation; another negative
result narrows the timing variant without establishing first-fetch failure.
The original leaf independently assembles to the same 44 bytes with Apple LLVM;
the host leaf and prior-gap suites pass nine methods. Integration, isolated-VM
validation and a separate reviewed M1 handoff remain required before native use.

No new MMIO address, security-state operation, reset-vector write, whole-cache
operation, cluster-restoration replay or arbitrary CPU-debug read is qualified
by this review. New evidence can change that engineering decision; the absence
of a confirmed fix is not permission to reinterpret unknown registers.

Once same-cluster CPU1 executes reliably, retain the separate milestones:
bounded callback/park, bidirectional coherency/timer/IPI checks, then one core
in the other Performance cluster and one Super core with their correct topology
and power indices. All 18 cores online remains distinct from measured scheduler,
frequency, efficiency and application-performance parity with macOS.

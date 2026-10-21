# J716c CPU types, topology and Linux scheduling — 31F preparation

**2026-10-21. Observed hardware description; offline validation only.** This
audit changes no boot package, device tree, security setting, CPU state or
clock. It supplies original validators and a read-only Linux collector for
later authorized tests. It does not resolve or certify CPU1 entry.

## This machine has two core types

A fresh, bounded, read-only macOS `sysctl` query returned:

```text
hw.ncpu: 18
hw.physicalcpu: 18
hw.logicalcpu: 18
hw.nperflevels: 2
hw.perflevel0.name: Super
hw.perflevel0.physicalcpu: 6
hw.perflevel1.name: Performance
hw.perflevel1.physicalcpu: 12
hw.perflevel0.cpusperl2: 6
hw.perflevel1.cpusperl2: 6
```

This confirms **12 Performance and 6 Super cores**, without an additional
efficiency-core class or SMT threads. Treating this machine as an older
Performance/Efficiency design would be incorrect. The following combines
that observation with the existing sanitized ADT and expected MPIDR encoding
in the public m1n1 source and project generator:

| ADT CPU IDs | Cluster | ADT type | macOS class | Raw ADT `reg` | Expected Linux DT MPIDR affinity | Shared L2 |
|---|---:|---|---|---|---|---:|
| 0–5 | 0 | M | Performance | `0x000`–`0x005` | `0x40000`–`0x40005` | 8 MiB |
| 6–11 | 1 | M | Performance | `0x100`–`0x105` | `0x40100`–`0x40105` | 8 MiB |
| 12–17 | 2 | P | Super | `0x200`–`0x205` | `0x10200`–`0x10205` | 16 MiB |

**Evidence distinction:** ADT topology and macOS class counts are observed;
secondary-core MPIDRs in this table are expected identities, not newly measured
secondary execution. Aff2 is 4 for M and 1 for P; Aff1/Aff0 identify cluster/core.
The older inventory table's column called “MPIDR” contains raw ADT `reg` values
and omits Aff2. Do not copy that column into a Linux CPU `reg` or startup matcher.
Older ADT compatible strings `apple,sawtooth` and `apple,everest` are reused
labels, not independent confirmation of this chip's precise microarchitecture.

**CPU1 is another Performance/M core in CPU0's cluster**, not the first Super
core. Therefore the 31E pre-Linux CPU1 failure is not evidence of a Linux
scheduler confusing these core classes. The controller never reached Linux.
The [31E result](../native/boot/attempt31e-2026-10-21-result.md) establishes
verified CPU0 code publication but no CPU1 record; incoming CPU1 EL/cache state
and whether it executed any early instruction remain unknown.

## What the current Linux description gets right

The original audit passes both retained boot042 DTBs. They contain all 18
canonical Aff2-bearing CPU regs, exactly three six-core `cpu-map` clusters,
one L2/OPP/performance-domain group per cluster, the correct L2 sizes, and
`opp-shared`. Stage B has all three cluster cpufreq controllers disabled in
the template. Template presence/enabled status does not prove runtime CPUs:
m1n1 fixup and launcher allowances determine the final tree and bootargs.

The retained config includes SMP, `CONFIG_NR_CPUS=512`, `SCHED_MC`,
`SCHED_CLUSTER`, CPUFreq/schedutil, CPUIdle and the Energy Model. Existing
default bootargs still limit Linux to one core and disable cpufreq and idle;
special experiment allowances have their own gates. Compiled options do not
establish that scheduling, frequency invariance or idle works on this chip.

The reviewed Asahi `apple-soc-cpufreq` source obtains its CPU sharing mask
from `performance-domains`, shares the OPP table across that mask, and registers
an OPP-backed energy model. Keeping clusters 0 and 1 distinct is necessary
even though both contain the same M core type. Driver source review is not
evidence of these policies running successfully on the native target.

## Two defects to avoid as SMP expands

**Uncalibrated capacity and power values.** The current generator explicitly
labels M=768/P=1024 and dynamic-power coefficients M=550/P=1054 hypotheses.
The former came from an uncertain-clock throughput comparison; the latter
include leakage. The auditor reports both `UNCALIBRATED` and does not replace
them or claim macOS parity.

Linux's optional `capacity-dmips-mhz` describes relative throughput per clock;
CPUFreq maximum-frequency information contributes to the final scheduler
capacity. It must be present consistently across CPU nodes. A clock ratio
alone cannot measure relative work per cycle. See the primary
[CPU capacity binding](https://raw.githubusercontent.com/torvalds/linux/master/Documentation/devicetree/bindings/cpu/cpu-capacity.txt).
Before changing these values, measure CPU-affine compute workloads at verified
stable rates on both classes, with repetitions and thermal/power metadata.
Include integer, branch and floating-point workloads to expose sensitivity
to workload choice; no single scalar captures every instruction mix.

**Four-bit startup packing cannot address all these cores distinctly.** The
sanitized PMGR `clusters` property describes `(width, position)` pairs
`(6,0), (6,6), (6,12)`. The older `4*cluster+core` calculation collides:

| Legacy bit | ADT CPUs aliased |
|---:|---|
| 4 | 4 and 6 |
| 5 | 5 and 7 |
| 8 | 10 and 12 |
| 9 | 11 and 13 |

The existing original
[m1n1 bitmap patch](../kernel/experiments/cpu-power-smp/m1n1/0002-smp-pack-t6050-start-bitmaps-from-ADT-clusters.patch)
addresses this layout but falls back to four-bit packing if its descriptor
is missing/invalid. A future all-core controller must refuse that condition;
the new audit does. This is not a fix for 31E: CPU1 is bit 1 under both layouts.
The patch remains a separate integration/runtime task; this audit neither
applies it nor starts another core.

## Native acceptance sequence: more evidence per authorized boot

These are future gates for the owning controller, not additional commands
authorized by this document. A failed stage stops expansion; do not jump to
all cores because an expected identity table has 18 entries.

1. **CPU1 entry:** establish a trustworthy incoming identity/EL and visible
   progress, then bounded timer/counter work and a verified final parked state.
   Separate code visibility from execution evidence. This remains the active
   startup blocker after 31E.
2. **Same-cluster Linux pair:** after the entry path is validated and a Linux
   allowance is reviewed, prove two online cores, per-core timer interrupts,
   IPIs, release/acquire memory handoffs, and idle/wakeup behavior. Collect the
   new read-only sysfs snapshot in the same session. Exercise renderer threading
   with a fixed workload and compare latency distributions to one core.
3. **One core from each additional cluster:** first the other M cluster, then
   the P/Super cluster, using verified six-bit packing and distinct expected
   identities. Check independent reset/entry assumptions, cross-cluster cache
   coherency, timers/IPIs and shared frequency-domain membership. A successful
   same-cluster test does not certify cross-cluster behavior.
4. **All 18 cores:** preserve Linux logical-ID-to-DT/hardware identity mapping;
   validate 3×6 cache and frequency domains, no invented SMT, all timer/IPI
   destinations, and bounded concurrent compute/memory tests. Record actual
   completed work, not only `/sys/.../online`.
5. **Heterogeneous scheduling and efficiency:** calibrate per-class capacity,
   validate requested versus effective rate and frequency-invariant utilization,
   then measure interactive latency, aggregate throughput, idle power and
   energy per task. Compare with the same macOS workload, power source, mode,
   temperature and screen workload. Validate idle residency/wakeup before
   calling the platform efficient; maximum clocks on every core are not an
   efficiency target.

Linux combines CPU capacity with frequency-invariant task utilization; this
requires meaningful effective-rate information, from suitable counters or
verified CPUFreq transitions. Timer frequency is not CPU clock frequency.
See [capacity-aware scheduling](https://docs.kernel.org/scheduler/sched-capacity.html).
Energy-aware placement additionally needs a credible per-domain energy model
and the appropriate runtime conditions; enabling a config option alone is
insufficient. See [energy-aware scheduling](https://docs.kernel.org/scheduler/sched-energy.html).
CPU types are thus explicit inputs to Linux policy, not labels to ignore or
an instruction to reproduce proprietary macOS scheduler code.

## Code and validation

[Tool instructions](../kernel/experiments/cpu-topology31f/README.md) cover the
original static audit and bounded Linux collector. **32 offline tests PASS**,
including raw-reg/MPIDR confusion, unknown type, duplicate IDs/phandles,
cross-cluster map errors, four-bit collisions, malformed descriptors, partial
capacities, split OPP groups, invented SMT and fixture-only capture.
Both retained real DTBs passed structural checks. Captured runtime sysfs
behavior was tested with synthetic fixtures only; native capture/SMP,
frequency invariance, energy model validity and performance parity are
**NOT RUN / unverified**. No decompiler output or proprietary bytes were added.

Inputs: sanitized ADT SHA-256
`6f143434d2f05310067559f8fa3836ae564dd9934ebc5912660f2a9f5a8a73af`;
boot042 base DTB `5d6fe64812b05e8c5d42ce3b97e3ede4c675e7a9a59d8fcf85d6906ef8daac9e`;
Stage-B DTB `17c55af9eb39ea799e254335176e9748193237dce3735f59cd286a63ea0a0405`.
The CPU map/affinity source is the project's
[generator](../kernel/experiments/t6050-dt/gen_t6050_dt.py) and public m1n1
commit `5d84c4c34d3f` (the current clean client is `57a9339`). The current
[hardware inventory](../hardware/hardware-inventory.md) supplies the earlier
macOS observation and sanitized cache inventory; its obsolete boot-status
summary is not used as current readiness evidence.

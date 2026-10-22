# 31L result review and the next CPU1 observation

2026-10-22. M1 report `eb1ac1c`, execution `c7608c7`, release `11cc2af`.
31L is consumed. Its controller ended naturally at `cpu1_arrival_timeout`,
not an outer deadline. Both CPU0 controls passed, both CPU1 start stores were
acknowledged, and all four entry channels remained negative. CPU1's PS actual
state changed to15 and implementation byte to2. Those values do not prove
instruction execution. The human returned to Macintosh HD within90 seconds.

An independent audit found no wrong CPU1 mask, truncated pointer, entry branch,
or sampled-field offset. Exact-image checks and pre-start publication succeeded.
The only tested target remains CPU1 in CPU0's active Performance cluster. The
12 Performance/6 Super topology matters for later clusters; it does not explain
this same-cluster failure. Eight inherited planned callbacks in31L were misleading
metadata: none was authorized or executed. The new controller explicitly plans0.

## Observation defect worth testing

31L initializes, cleans and reads each Normal record on CPU0 before the starts.
Subsequent reads can hit CPU0's cached zero. Its CPU0 control verifies a store
made by that same core; it does not test visibility of a secondary's stores
before normal coherency is established. This is a concrete limitation of our
observer, not a demonstrated cause of CPU1's failure.

31M retains exactly the31L CPU1 prefixes and start sequence. It adds a paired
observation: first read normally; only if every sampled phase/identity field is
zero, issue bounded CPU0 cache clean-and-invalidate for that owned record, then
sample again. All positive or partial evidence stops. The operation is issued
by CPU0 but may propagate through the shareable cache hierarchy; it is not a
promise of CPU0-local effects. Clean-and-invalidate avoids deliberately throwing
away a dirty peer's data. No invalidate-only or whole-cache operation is used.

The experiment requires qualified CPU0 execution regime and cache geometry,
complete owned granules, no CPU0 stores to them after initialization, a separate
pre-start maintenance control, and the existing exact image/topology/mapping
checks. Any failed qualification stops before CPU1 starts. A failed maintenance
or read stops without cleanup or another target command. No maintenance is
performed on CPU1, Device records, code, MMIO, firmware or personal storage.

| Outcome | What it establishes | What it does not establish |
|---|---|---|
| Expected CPU1 identity before maintenance | CPU1 prefix execution and normal observation | Reset provenance, verified park or Linux SMP |
| Expected identity after maintenance | CPU1 prefix execution visible in the maintained sample | Cache causality: CPU1 could have written between samples |
| Partial or unexpected identity | A changed/inconsistent observation requiring review | CPU1 execution proof |
| Both observations zero | No visible prefix in this bounded experiment | No fetch, held reset, a firmware defect or absence of execution |
| Pre-start control/geometry refusal | This operation is unqualified in the measured context | A CPU1 startup failure |

Dirty private CPU1 cache data outside the observed coherency domain, an earlier
fault, a different entry route and no instruction fetch remain possible negative
explanations. This corrects one observation limitation; it is not advertised as
an all-core fix or a desktop performance improvement.

## Firmware and upstream constraints

The new [firmware pass](native31m-firmware.md) distinguishes peripheral reset
selection and cluster-scoped error capture from CPU1 reset status. Neither
justifies additional MMIO. The [upstream audit](native31m-upstream.md) found no
new T6050 start fix. Recent M4 hypervisor hooks suppress certain guest power
writes rather than supply a Linux startup recipe. No proprietary code is copied
or replayed, and the installed image and macOS are unchanged.

After a first verified secondary entry, the path remains stable CPU1 execution,
then one core in each other cluster, then all18 cores with timer/IPI/coherency and
scheduler tests. Frequency, throughput, energy and responsiveness need separate
native measurements against macOS; a higher online CPU count is insufficient.

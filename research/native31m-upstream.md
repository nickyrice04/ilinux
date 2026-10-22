# 31M: current upstream CPU-start evidence

2026-10-22. Read-only source review after consumed31L; no target operation,
checkout update, macOS change or new hardware allowance.

## Current source comparison

GitHub's API reports upstream main at
`7cde7d1a784d851ebfee5579fa363c38b14150c0` (committer timestamp
2026-10-19T11:30:47Z), 32 commits ahead of the project's pinned
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`. The comparison contains no changes
to `src/smp.c`, `src/start.S` or `src/chickens.c`. The current open pull-request
and issue listings contain no identified T6050 secondary-start fix. This is a
bounded review of the default branch and listed open work, not proof that no
unpublished fix exists.

The [source comparison](https://github.com/AsahiLinux/m1n1/compare/57a9339ffd1876e78297b17d34dece8cff8fa1ba...7cde7d1a784d851ebfee5579fa363c38b14150c0)
mostly adds or revises macOS hypervisor, SPTM/GXF emulation, nested virtualization
and related device handling. It does not supply a raw-boot CPU1 startup fix.
[PR610](https://github.com/AsahiLinux/m1n1/pull/610), which introduced T6050/T6051,
explicitly reports powered secondary cores that do not execute m1n1, tested
with macOS26.2b2 and27.0b2. That corroborates a platform-level problem; it does
not identify the cause of our31L result or prove the same firmware behavior.

The open [boot-CPU switch proposal](https://github.com/AsahiLinux/m1n1/pull/563)
addresses logical CPU numbering after secondaries can execute. The open
[GENTER tracing proposal](https://github.com/AsahiLinux/m1n1/pull/717) concerns
hypervisor guest calls. Neither is an established substitute for CPU1's missing
first-entry evidence.

## Newly documented CPU-power interception

[PR731](https://github.com/AsahiLinux/m1n1/pull/731), committed as
[`25b1d89ca50be848b136ce771ce7167244852a91`](https://github.com/AsahiLinux/m1n1/commit/25b1d89ca50be848b136ce771ce7167244852a91),
reports that certain CPU/cluster power-control writes produce SErrors on M4.
The new [`src/hv/hv_cpu_power.c`](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/src/hv/hv_cpu_power.c)
intercepts these accesses for an SPTM-emulated macOS guest:

| ADT-relative address | Interception scope |
|---|---|
| Each `cpu-impl-reg` base +`0x9000`, +`0x9008` | Two 64-bit per-core software shadows |
| Each distinct `cpm-impl-reg` base +`0x8000`, +`0x8008`, +`0x40f8` | Three 64-bit per-cluster shadows; comments associate these locations with immediate SErrors |
| Same CPM base +`0x4008 + 0x10*n`, n=0..11 | Twelve additional shadows; comments describe suspected delayed SErrors |

**Confirmed source behavior:** `hv_start` calls the initializer before guest
entry. The initializer does nothing unless `hv_sptm_mode` is `SPTM_EMULATION`.
It zeros the software shadow state, obtains base addresses from the ADT and
installs stage-2 hooks for 8-byte accesses. Hooked writes update the shadow;
hooked reads return that shadow. The initializer and hook do **not** read or
write the real power-control registers. Its final translation maintenance
publishes the hypervisor mappings, not a CPU reset-release operation.

**Interpretation limit:** these are M4 observations in the macOS hypervisor
context. They are not measured T6050 register semantics and do not prove that
the corresponding T6050 accesses would fault. Equally, the source does not
qualify these registers for direct read-only probing, establish safe write
values, or reveal a CPU-start prerequisite.

The CPM +`0x40f8` location is independently relevant to the prior
[T6050 ACC restoration analysis](native31l-platform-prepare.md). The upstream
report strengthens the reason to establish ownership and lifecycle before
considering any such restore on an active cluster. It is not permission to
replay the macOS restoration path.

## Focused follow-up and CPU-type scope

The per-core control pair is a useful new **static-analysis lead**. Existing
sanitized CPU-window provenance yields CPU0 `0x210059000`/`0x210059008` and
CPU1 `0x210159000`/`0x210159008`. REA can search firmware, PMGR and platform
callers to determine who uses this pair, at what lifecycle stage, and whether
any independently verified getter establishes a meaningful observation. These
addresses are not added to a native allowlist by this document.

CPU1 is an M-type Performance core in CPU0's already active M0 cluster. The
observed machine remains twelve Performance cores across two M clusters and
six Super cores in the P cluster. A first-core cluster-restoration operation
or changing six-core mask spacing does not follow as the fix for this same-
cluster target. Later first-core starts in the other M and P clusters still
need their own power, entry, cache, timer and identity validation.

All31L zero markers remain inconclusive about CPU1 execution. No newer
upstream change found here removes that uncertainty, and no new native power,
reset or security operation is justified by this source review.

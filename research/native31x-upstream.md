# 31X — tracing the positive T6050 SMP report to its missing host

Checked 2026-10-24. This is a renewed, bounded public-source CPU investigation,
following the [31W assessment](native31w-upstream.md). Sources were read as data;
no downloaded code, hardware operation, VM, installation or external message was
executed. The local target remains the ADT-identified J716c/T6050 with retained
25G83 evidence. Public reports for other boards and firmware are qualified below.

**The accepted resident-SPTM host is the strongest software-alternative lead.
The evidence is stronger than a bare guest CPU count, but the actual accepted
host bootstrap and independently inspectable physical-entry evidence are still
missing. No usable raw-start fix or Apple-only necessity was established.**

## The positive report deserves follow-up, with corrected attribution

The historical SiliconForest kernel contains a concrete report of J714s/M5 Pro
operation under a resident-SPTM hypervisor on firmware 26A428. The
[ANS qualification document at `5c978948`](https://github.com/chriskearney/siliconforest-linux/blob/5c978948f42c44c725d621bde31d70cd3439167c/Documentation/arch/arm64/t6050-sptm-ans.rst)
attributes successful boot, per-CPU sleep/SIMD checks, timer interrupts, storage
I/O and subsequent installed-root operation to that setup. It provides a guest
kernel hash and names locally retained logs. Those logs and the accepted native
host object are not supplied by that document.

There are two useful additions to the earlier assessment:

- The [idle change `6c03bd92`](https://github.com/chriskearney/siliconforest-linux/commit/6c03bd926fc5672dc91457053c13b3e83ad30048)
  explicitly attributes register-loss probes to all 17 hardware secondaries. It
  describes affinity, all 32 SIMD registers, sleep/wake and repeated timer checks
  with 18 CPUs online under SPTM HV. Its implementation preserves state around
  waits after entry; it does not supply the missing first-entry operation.
- The [adjacent CPU-frequency qualification](https://github.com/chriskearney/siliconforest-linux/blob/5c978948f42c44c725d621bde31d70cd3439167c/Documentation/arch/arm64/t6050-sptm-smc-dvfs.rst)
  reports work pinned to CPUs 0, 6 and 12, with low/high/low throughput changes
  matching the three clusters' requested frequency ratios. This is a more
  substantive execution claim than an enumerated online count. The document
  distinguishes requested-state readback from measured work-rate scaling.

**These are not independent reports by the SiliconForest repository owner.**
Fresh GitHub commit metadata identifies `DjDeveloperr` as both author and
committer of [the ANS report commit](https://api.github.com/repos/chriskearney/siliconforest-linux/commits/5c978948f42c44c725d621bde31d70cd3439167c)
and [the idle/probe commit](https://api.github.com/repos/chriskearney/siliconforest-linux/commits/6c03bd926fc5672dc91457053c13b3e83ad30048).
Their preservation in another repository does not create independent hardware
corroboration. Attribute them to DJ's historical resident-SPTM work.

Taken together, the specific tests and corresponding guest-side fixes make this
a serious, internally coherent lead. They do not establish reproducibility from
the available files. No located public receipt binds the accepted host hash,
physical secondary entry/affinity and guest tests in one run. Nor does this
J714s/26A428 report establish compatibility with J716c/25G83. This assessment
neither treats the report as a demonstrated local workaround nor dismisses it
merely because the host is unavailable.

## Following the referenced artifacts, including archived sources

The [storage-import record](https://github.com/chriskearney/siliconforest-linux/blob/5c978948f42c44c725d621bde31d70cd3439167c/Documentation/arch/arm64/t6050-sptm-storage-import.rst)
names `m1n1-aurora@j873` commit
`29e59aaaeb5de3f26456dcc3ecdcd7643a873b58` and U-Boot commit
`52474099334fdd459e49236a5392a10ccd6d158d` as references guiding the adaptation.
**The bootloader hash is not identified as the successful x1n1 host.** Attempts
to resolve that bootloader reference in current Aurora m1n1, the old Aurora and
Omacom repository names, SiliconForest, its `iconidentify` alias, and DJ's public
m1n1 returned 404 or 422. This closes a specific reference lead; it does not
prove that the actual host has been deleted or was never published elsewhere.

The fresh audit also covered more than default heads:

| Public surface checked | Result and limit |
|---|---|
| SiliconForest m1n1 branches and both tag pages | 16 branches and 181 tags were returned. The pinned [source manifest](https://github.com/chriskearney/siliconforest-m1n1/blob/aca1258c2d7daad7db7079d4f89bb8217659f7ac/SILICONFOREST-SOURCES.json) describes 175 source snapshots, including public DJ M5 and Aurora/Omacom J873 references. No named x1n1, resident-host or accepted Mach-O/SPTM snapshot was located in those entries. A tag listing is not inspection of every historical file. |
| Public M5 bootloader profile and its recent history | [`a5cd8816`](https://github.com/chriskearney/siliconforest-m1n1/tree/a5cd88166aa90237466fadc5ea294aa92f91c997) preserves the older public T6050 ATC/display research. The current [profile table](https://github.com/chriskearney/siliconforest-m1n1/blob/aca1258c2d7daad7db7079d4f89bb8217659f7ac/README.md) explicitly calls it unbuilt and unqualified. It is not the September resident-host qualification. |
| SiliconForest release metadata and release profile source | Six bootloader releases and ten kernel releases were listed. Asset names describe package releases; no separately identified accepted T6050 x1n1 host appeared. The [release profiles](https://github.com/chriskearney/siliconforest/blob/29af15ec578ab3b7a81dd4a8888898f07fd0946a/release/profiles.json) enumerate M1–M3 profiles, with no qualified T6050 profile. Packages were not downloaded or executed; their names alone do not prove their internal contents. |
| Aura branches, forks, PRs and releases | One main branch, three forks with their branches, six PRs and an empty release API list were checked. The forks' named work concerns J604, T8122 display/GPU, PMGR validation and T6041 storage. No accepted T6050 host source surfaced. This is a bounded public inventory, not a claim about private branches. |
| DJ's public m1n1 branches | 42 branches were returned, including the same public M5 RFC/display tips. No branch named for x1n1, resident SPTM or an accepted Mach-O host was located. |
| Targeted repository/commit/issue search | Searches for x1n1, T6050 SMP/SPTM and exact relevant projects led back to the guest drivers, attributed reports, emulator work and negative raw-start reports. Searches are limited by indexing; one broad `t6050 start` query was noisy and only its first 100 results were read. It is not an exhaustive negative search. |

Aurora's [current README at `78b5d9d1`](https://github.com/aurora-silicon/aura/blob/78b5d9d17f7897ad5085c8465f0a9807a51553bb/README.md)
continues to reserve x1n1 Mach-O boot-object support for separate review. Its
[release note](https://github.com/aurora-silicon/aura/blob/78b5d9d17f7897ad5085c8465f0a9807a51553bb/docs/releases/0.1.0.md)
continues to exclude internal Mach-O/SPTM/native-SSD development. Ordinary
`aura.macho` output is therefore not evidence of that accepted host profile.

## What the available host code does establish

Aura's public [guest-secondary startup](https://github.com/aurora-silicon/aura/blob/78b5d9d17f7897ad5085c8465f0a9807a51553bb/src/hv/hv.c#L370)
prepares the secondary MMU state, calls initialization on that secondary through
`smp_call4`, waits for acknowledgement, and then dispatches guest entry through
another `smp_call4`. Its [physical-core dispatch helper](https://github.com/aurora-silicon/aura/blob/78b5d9d17f7897ad5085c8465f0a9807a51553bb/src/smp.c#L842)
rejects a target without a live spin-table flag and waits for that flag to change.
The [liveness query](https://github.com/aurora-silicon/aura/blob/78b5d9d17f7897ad5085c8465f0a9807a51553bb/src/smp.c#L959)
reads that flag.

This is a useful dependency distinction: in the published implementation,
launching a guest secondary consumes an already-entered host secondary. It does
not solve first entry of a dead host CPU. If the successful x1n1 host uses this
same design, a binding between its physical spin-table/affinity records and the
guest run would be highly informative. The unpublished host must be checked
before treating that conditional architectural inference as proof.

The [new Aura merge](https://github.com/aurora-silicon/aura/compare/553b566f69275ff4e46ee6542a7236fb80a333a2...78b5d9d17f7897ad5085c8465f0a9807a51553bb)
does not change this boundary. It adds T6041/J616C FDT-scoped DAPF setup and an
NVMe split-window admission case. Those are relevant fixes for that M4 Max
handoff, not T6050 secondary-start prerequisites. The previously checked T6050
startup code and its [31V applicability limits](native31v-upstream.md) are not
superseded by that merge.

## Emulator registration is a different operation

The two specifically rechecked public leads remain pinned at
[`niklassheth/bootloader` `98412d67`](https://github.com/niklassheth/bootloader/tree/98412d670862a6d1cd29c5e8f33439839ae3c7e6)
and [`apple-silicon-re` `35b1c63e`](https://github.com/ADevWithAnIdea/apple-silicon-re/tree/35b1c63e5cbfb599d9814dddf68b0f53c236aa1f).
The documentation's [scope statement](https://github.com/ADevWithAnIdea/apple-silicon-re/blob/35b1c63e5cbfb599d9814dddf68b0f53c236aa1f/docs/sptm/README.md)
primarily concerns the XNU-facing emulator for T8140/26.6, with T8142/27 updates.
It is not a complete real-SPTM initialization or protection contract for T6050.

The [CPU-registration description](https://github.com/ADevWithAnIdea/apple-silicon-re/blob/35b1c63e5cbfb599d9814dddf68b0f53c236aa1f/docs/sptm/xnu_bootstrap.md#238-register_cpu-and-cpu_id-endpoints-14-19)
describes registration by a CPU that has already spun up. The actual public
[emulator helper](https://github.com/niklassheth/bootloader/blob/98412d670862a6d1cd29c5e8f33439839ae3c7e6/src/hv_sptm_core.c#L42)
finds or appends an in-memory physical-ID/logical-ID record. The
[XNU endpoint dispatcher](https://github.com/niklassheth/bootloader/blob/98412d670862a6d1cd29c5e8f33439839ae3c7e6/src/hv_sptm_xnu.c#L105)
calls it. That helper contains no physical release operation. Porting it would
not supply the accepted real-monitor host bootstrap or repair an unobserved
physical first fetch. This conclusion concerns that actual emulator code, not
every registration step that real SPTM might require.

Fresh exact-project commit searches found Asahi's initial T6050 support and
[SARTv4 addition](https://github.com/AsahiLinux/m1n1/commit/9bfdf8aeca30ba8dee1897ec73713da89e7623b9),
and Gravity's inherited [initial support](https://github.com/GravityLinux/bootloader/commit/b2d3f5eba7ced3f5f9e00044744d2c4b4f2efeba).
Neither supplies a new physical-start fix. The separately surfaced
[Sowyu CPU investigation](https://github.com/Sowyu/m5-azahi/pull/5) explicitly
limits its hardware result to one CPU and calls its proposed startup conditions
unqualified. These findings do not exclude an unindexed or unpublished fix.

## Ranked next step and the minimum useful public answer

1. **Highest value: qualify the reported accepted resident-SPTM host.** It has
   concrete T6050 execution claims and a plausible continuing host/monitor
   contract. Required input: the exact original host source revision or minimal
   redistributable bootstrap source, accepted boot-object format and build
   identity, board/firmware applicability, and initial monitor context/ownership
   description. Add a sanitized observation connecting one non-boot physical
   affinity's host entry to the guest test; an all-core claim should account for
   every claimed physical affinity. No proprietary firmware or personalized
   boot object is needed in a public answer.
2. **Next: a specific local raw-path discriminator.** A missing writable
   prerequisite or an effective-entry/early-fault observation could reopen
   original implementation. The existing no-marker result, a CPU0 register dump,
   another guest-registration helper or a different chip's fix does not supply
   that discriminator.
3. **Do not substitute repeated boot attempts or a firmware-only conclusion.**
   This search found no new stimulus that justifies an unchanged local reboot.
   Failure to locate the host is an evidence/access gap, not proof that only
   Apple can make SMP possible.

A precise public request would ask for the **accepted T6050 resident-SPTM host
revision and boot-object/context contract used for the reported J714s/26A428
run, plus sanitized physical-secondary entry provenance**, and ask whether the
path is applicable to J716c/25G83. An explanation of the specific unsupported
prerequisite would also be useful if the original implementation cannot be
released. This note sends no request and prepares no native procedure.

## Retention and limits

Scoped API metadata, selected pinned source files and URL/time/SHA-256 records
are retained under ignored `build/research31x/public/`. HTTP failures and initial
local network-resolution failures are recorded separately from successful reads.
Source trees were queried as metadata; no full kernel, release package, Apple
binary, personalized boot object or private conversation was acquired. The
source/helper review was static. The hardware claims above remain attributed
reports, not independently reproduced results.

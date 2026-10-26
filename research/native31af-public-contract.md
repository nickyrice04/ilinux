# 31AF: public segment ownership and an earlier entry observer

Checked 2026-10-25 after the [31AE result](../native/boot/attempt31ae-recovery-2026-10-25-result.md).
31AE passed actual Recovery installation; one human-observed boot showed only
the Apple logo. Entry, display visibility, monitor services and physical
secondary execution remain unconfirmed. This review reads public source and the
original observer only. It does not read Apple decompiler artifacts, run
third-party code, start a VM, change the host or prepare a native write.

## A concrete public-source mismatch

**Confirmed source fact:** at official XNU commit
`ac9718fb1af618d5ce8678d0dc6e8a58f252216f`, `osfmk/arm/data.s` puts bootstrap
IRQ/exception stacks in `__BOOTDATA,__data`, ordinary clock data in
`__DATA,__data`, and a separate monitor/table reservation in
`__DATA_SPTM,__const`. The latter reserves one 16 KiB page described as
CTRR-covered SPTM data, followed by a read-only page-table arena. Its macOS
conditional reserves another twenty 16 KiB pages: `0x54000` total. This is a
public build profile, not a proven minimum for a small custom image or this
firmware. [Bootstrap stacks](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm/data.s#L42),
[distinct monitor/table reservation](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm/data.s#L98).

The same public consumer places its copied iBoot arguments in `__DATA,__const`
and copies both argument records during initialization. Its allocator describes
the `ropagetable_begin` arena as read-only allocation.
[Argument storage](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/arm_init_sptm.c#L163),
[argument copies](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/arm_init_sptm.c#L770),
[table allocator](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/arm_init_sptm.c#L1700).

**Confirmed original-code fact:** 31AE labels the observer record and stack's
entire `0xc000` region `__DATA_SPTM`. The unchanged entry clears the record before
installing its vectors, creating its own stack, testing its EL2 profile or
attempting any screen output. Therefore its silent result includes a first
store fault in that specially named region. Passing the inspector and declaring
RW in Mach-O did not establish the actual monitor mapping permissions.
[Original entry](../kernel/experiments/visible31ac/entry.S),
[31AE serializer](../kernel/experiments/bootimage31ae/ordered.py).

**Hypothesis to test:** placing ordinary record/stack storage in the monitor/table
reservation can prevent progress before the current observer. The public source
establishes a role mismatch; it does not prove this caused the 31AE logo-only
result or establish the incoming native permissions.

## Entry and code-placement boundaries

The public entry documents full x0 as an entry reason. Nonpanic entry supplies
iBoot arguments in x1 and separate monitor arguments in x2; panic entry instead
supplies a string pointer and dump-support Boolean. Preserve incoming state
before interpreting a reason or a pointer. A prototype may explicitly support
cold entry only, but must not interpret panic x1 as `boot_args`.
[Entry contract](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/start_sptm.s#L34).

The source states that only `__TEXT_BOOT_EXEC` is initially executable. Its cold
path establishes stacks, preserves x1/x2, completes its image preparation, sets
VBAR, and reports fixups complete before entering ordinary C initialization.
The literal EL1 register names do not by themselves establish the actual EL in
a VHE host. An original observer must record CurrentEL before choosing an
EL-specific register bank. All instructions, vectors, direct callees and literals
needed before the fixups boundary must stay in the boot region. No native
monitor call is justified merely by this source comparison.
[Cold path and fixups boundary](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/start_sptm.s#L123).

The exact public linker order keeps DATA_SPTM before ordinary executable code,
boot code after ordinary code, and ordinary DATA/BOOTDATA later. Both executable
segments receive RX declarations. Thus correcting ownership does not justify
moving the early observer into ordinary TEXT_EXEC or breaking the already
qualified file-offset inequalities. [Linker order and protections](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/makedefs/MakeInc.def#L1081).

## Useful next original test

A materially different offline candidate should separate the monitor/table
reservation from owned writable record and stack storage, retain pre-fixups code
in BOOT_EXEC, and improve the first observable stage. These changes address a
specific failure that 31AE could not report. They are not an unchanged retry.

Recommended checks before a new native proposal:

1. Validate distinct, nonoverlapping DATA_SPTM, DATA and BOOTDATA roles in both
   collection headers. Bind record/stack symbols to ordinary writable regions;
   reject any overlap with monitor/table storage. Keep DATA_SPTM independently
   zero initialized and explain the selected reservation size.
2. Audit the first instruction path and all pre-fixups branches/callees/literals
   against BOOT_EXEC extents. Reject early branches to the normal-code park.
   Check both link bases, relocation records and decoded branch destinations.
3. Add an initial bounded screen breadcrumb as early as the legitimate mapping
   contract allows, with separate stages for entry, own-storage access,
   descriptor acceptance, framebuffer mapping and final painting. If an early
   stackless/register-only painter is used, audit that it makes no stack or
   record access before its first visible store. Do not cast the physical video
   base to a pointer or weaken the mapping checks merely to obtain a marker.
4. Test a synthetic read-only DATA_SPTM mapping and writable owned storage; the
   revised code must leave monitor bytes unchanged. The former record-write
   path should fail under that fixture, distinguishing the repair from a
   generic successful writable-RAM test. Do not call that model a measurement
   of native SPTM permissions.
5. Exercise cold/panic/unknown reasons and supported/unsupported EL profiles.
   Capture x0/x1/x2/CurrentEL before interpretation, avoid EL2-only reads from
   an EL1 path, and bound every destination and failure stop. Preserve private
   argument material; screen codes should contain only nonidentifying state.
6. Retain the 31AD rejected-format control and full property-key/error checks.
   Installation, distinctive native entry, monitor services and physical
   secondary execution remain separate results.

An unchanged Apple logo would still be ambiguous. A RAM record without a
qualified retrieval route is insufficient native observability. A distinctive
early marker proves execution only through its own publication point, while a
later change of marker identifies the storage/mapping boundary actually passed.
The existing [framebuffer review](native31ab-observer.md) retains the mapping and
cache-visibility constraints.

## Topology is later than observable boot entry

The pinned public XNU topology routine reads physical IDs from `/cpus` `reg`,
assigns logical IDs separately, groups physical clusters, and invokes
`sptm_register_cpu(cpu->phys_id)` while traversing selected device-tree entries.
The declarations' required boot-CPU-first order remains a separate validation
obligation. Neither registration nor a synthesized guest CPU count demonstrates
physical secondary entry. Preserve source physical IDs and actual MPIDR when
eventually testing a secondary; do not infer affinity from logical array index.
[Physical ID input](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/machine_routines.c#L1210),
[registration placement](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/machine_routines.c#L1302).

## Refreshed public implementations

The prior pins were read before refreshing their exact default branches. Fresh
GitHub API responses on this date retain Aura `ec4a6ab8b4252079e78196515577d73ef0a86135`,
SiliconForest m1n1 `aca1258c2d7daad7db7079d4f89bb8217659f7ac`, antiapplefox
`35695e2a91feaff53e9df7b62bd1ab030bc58be0`, and Asahi m1n1
`51b747dced07a58eacf5dabc31ed6f00bcfa20fd`. SiliconForest's actual default is
`siliconforest/next`; its different `main` tip is not a newer default host.
Sixteen SiliconForest branches were returned. Fifteen heads match the prior
bounded inventory; `fix/usb4-pcie-adapter-alias` changed from `d1d05d4e` to
`7bb73392`. This inventory does not inspect every file or prove universal
absence. The changed branch comparison contains one added USB4 alias-fallback
test file and one commit; it adds no resident-entry source.
[Bounded branch comparison](https://github.com/chriskearney/siliconforest-m1n1/compare/d1d05d4eaf952bf1d0a25fe0ab48985727367bab...7bb733929066441769ce289fab7e6055fae7b0eb).

- Aura still reserves x1n1 Mach-O support for separate review and excludes
  internal Mach-O/SPTM feature development from its release. Its entry preserves
  incoming x0 for its ordinary raw-argument consumer, and its public Mach-O
  linker still emits plain segments/thread entry without the documented resident
  handoff adapter. [Scope](https://github.com/aurora-silicon/aura/blob/ec4a6ab8b4252079e78196515577d73ef0a86135/README.md#L38),
  [release boundary](https://github.com/aurora-silicon/aura/blob/ec4a6ab8b4252079e78196515577d73ef0a86135/docs/releases/0.1.0.md#L70),
  [entry](https://github.com/aurora-silicon/aura/blob/ec4a6ab8b4252079e78196515577d73ef0a86135/src/start.S#L103),
  [linker](https://github.com/aurora-silicon/aura/blob/ec4a6ab8b4252079e78196515577d73ef0a86135/aura.ld#L22).
- The SiliconForest historical J714s/26A428 report remains a useful positive
  resident-host lead, including its eighteen-CPU claim. The located report and
  guest DART transport still do not identify a reproducible accepted host object
  or independently establish this J716c/25G83 physical-secondary context.
  [Pinned report](https://github.com/chriskearney/siliconforest-linux/blob/5c978948f42c44c725d621bde31d70cd3439167c/Documentation/arch/arm64/t6050-sptm-ans.rst#L20),
  [guest transport](https://github.com/chriskearney/siliconforest-linux/blob/5c978948f42c44c725d621bde31d70cd3439167c/drivers/iommu/apple-dart-x1n1.c).
- antiapplefox's original packager keeps ordinary DATA mapped as `__DATA` and
  creates a separate file-empty DATA_SPTM reservation. That separation
  corroborates the ownership distinction; its packager is not a
  hardware-qualified resident host. This review does not consume that
  repository's Apple decompiler artifacts or import its implementation.
  [Original serializer](https://github.com/antiapplefox/m5-linux/blob/35695e2a91feaff53e9df7b62bd1ab030bc58be0/scripts/pack-bootkc.py#L38).

The public source supplies a new, testable ownership correction and clearer
entry observations. Neither missing host source nor the 31AE silent screen
establishes an Apple-only barrier.

## Retained source provenance

Fresh exact-commit public files and API metadata are retained under ignored
`build/research31af/public-xnu/`. Six XNU files were checked against the complete,
nontruncated Git tree using Git blob SHA-1 framing: six matches, zero mismatches.
The DATA source has blob `ef165e35ead3f9fbdaad4cd5a62d3691510bfac0` and SHA-256
`adef0aef5db1fcb27ab9dba5ed044d72d9d03cbcc387db5aa42bae42755870b4`.
The independent original manifest records all six sizes/digests.

Some browser-cache views of the same pinned URLs returned stale line numbers
and shorter text. The citations above use the freshly fetched blob-matched
files. For example, MakeInc.def's actual segment-order rule starts at line 1081,
not the earlier cached line 996. Shell fetches initially failed sandbox DNS;
read-only network fetches then succeeded. A failed cache fetch is not evidence
that a public source does not exist.

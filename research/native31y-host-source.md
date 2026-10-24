# 31Y: public resident-SPTM host entry contract

Checked 2026-10-24. CPU-only, public-source inspection; no downloaded source was
executed, and no image was installed or booted. The earlier
[31X attribution and hardware-evidence assessment](native31x-upstream.md)
remains unchanged.

**Confirmed source-level gap:** public Aura's Mach-O wrapper does not supply the
SPTM-to-OS entry adapter described by Apple's public XNU source. This gives the
alternate-host investigation a concrete missing interface, but does not establish
a working T6050 bootstrap or an Apple-only dependency. Offline image parsing can
test serialization independently; it cannot demonstrate iBoot/SPTM acceptance or
physical secondary execution.

## Two different entry contracts

Apple XNU tag `xnu-12377.1.9`, commit
`f6217f891ac0bb64f3d375211650a4c1ff8ca1ea`, documents an OS entry reached **from an
already running SPTM**. Register x0 supplies the entry reason; on ordinary boot,
x1 supplies iBoot arguments and x2 supplies separate SPTM arguments. Panic has
different argument meanings. The entry handles cold, warm, secondary and
hibernation cases. This is neither the monitor's own initial context nor a raw
hardware reset contract.
[Official entry source](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/osfmk/arm64/sptm/start_sptm.s#L34).

The same source requires the initial entry in `__TEXT_BOOT_EXEC`, the segment
initially executable under this contract. Its cold path preserves both argument
pointers, performs image fixups and static-interface initialization, establishes
final exception vectors, then reports fixups completion to the monitor. The
comments explain that this boundary validates/locks the vector base and changes
the code region's type. These are legitimate cooperation requirements, not a
means of installing SPTM after a raw boot.
[Entry and fixups boundary](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/osfmk/arm64/sptm/start_sptm.s#L61).

XNU then copies both argument structures and takes its first available physical
address from the SPTM arguments: iBoot's allocation high-water mark does not
account for pages consumed by the monitor and other components. It initializes
the SPTM helper library with monitor-supplied state. A hypothetical adapter that
merely moves x1 into x0 would therefore leave an unresolved memory/lifecycle
contract.
[Argument consumption and allocation boundary](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/osfmk/arm64/sptm/arm_init_sptm.c#L678).

By comparison, public Aura commit
`78b5d9d17f7897ad5085c8465f0a9807a51553bb` saves incoming x0 and passes it to
`_start_c`, which copies it directly as ordinary boot arguments. The raw and
Mach-O outputs link the same object list. Its Mach-O linker script declares
`MH_FILESET`, but emits a thread command and five plain segment commands; it
contains neither `LC_FILESET_ENTRY` nor `__TEXT_BOOT_EXEC`. Thus this public
wrapper is not itself an implementation of the documented SPTM-to-OS adapter.
[Entry](https://github.com/aurora-silicon/aura/blob/78b5d9d17f7897ad5085c8465f0a9807a51553bb/src/start.S#L104),
[C consumer](https://github.com/aurora-silicon/aura/blob/78b5d9d17f7897ad5085c8465f0a9807a51553bb/src/startup.c#L180),
[build outputs](https://github.com/aurora-silicon/aura/blob/78b5d9d17f7897ad5085c8465f0a9807a51553bb/Makefile#L287),
[linker script](https://github.com/aurora-silicon/aura/blob/78b5d9d17f7897ad5085c8465f0a9807a51553bb/aura.ld#L22).

## What the public build definitions do and do not provide

Apple's format header defines `MH_FILESET`, `LC_FILESET_ENTRY`, and that command's
address, file-offset and entry-identifier fields. **Those definitions do not
establish which commands iBoot or the local inspector requires.** The public XNU
build orders the boot executable segment and marks it RX, but also links external
`sptm_xnu` and TrustedExecutionMonitor libraries and imports platform headers from
SDK/KDK locations. The retained entry source includes `sptm/sptm_xnu.h`; the
retained official source and directory checks do not provide the complete
`sptm_bootstrap_args_xnu_t` definition or a compatible standalone host bootstrap.
Do not reconstruct its layout from the few consumer fields above.
[Format definitions](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/EXTERNAL_HEADERS/mach-o/loader.h#L1204),
[segment construction](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/makedefs/MakeInc.def#L1026),
[external libraries and header paths](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/makedefs/MakeInc.def#L1119).

**Applicability remains unqualified.** This public tag's Mac build lists include
T6041/T8132 but not T6050. Neither its structure layout, dispatch constants nor
fixups contract has been bound to the local J716c/T6050 firmware build 25G83.
The entry source is a useful architectural comparator, not a native recipe.
[Published build scope](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/makedefs/MakeInc.def#L32).

## Bounded history check

The new check followed Aura's actual entry/linker history and inspected relevant
patches, rather than treating a filename or output extension as support:

| Public change | Relevant scope and limitation |
| --- | --- |
| [M1–M3 stage-two relocation](https://github.com/aurora-silicon/aura/pull/4/files) | Moves an ordinary raw-chainloaded image away from live coprocessor buffers; does not add the monitor entry adapter. |
| [J700/T8140 run-base relocation](https://github.com/aurora-silicon/aura/commit/6dc5738054d293dc5d94f6e7c22d8263d79da8ec) and [relocation padding](https://github.com/aurora-silicon/aura/commit/c4b79bd632ab9fe1e540ee1bb512765f44aedf90) | Preserve a raw image's run location beneath a firmware read-only span; the incoming argument contract remains unchanged. |
| [MPIDR stack selection](https://github.com/aurora-silicon/aura/commit/1b469fcb618f1bb125b8566c28ec8cd2fc0cba9c) | Handles a core already executing the reset entry, including re-entry after deep idle; not evidence of a new first-fetch path. |
| [T8152 twelve-core startup](https://github.com/aurora-silicon/aura/commit/7902ce4153443eb10d6a82c4b004c798ea04d313) | Real physical-start code, explicitly gated to J873g, EL2, PMGR2 and two six-core banks. Includes publication and post-store event signaling; those differences are not qualified for T6050's topology or firmware. |

The entry-history response contained 26 changes; the renamed linker history
contained three. Relevant source patches and current entry/build files were
retained. This finite inspection located no accepted resident-SPTM host adapter
in those changes. It does not prove that no public or private implementation
exists elsewhere.

## Next useful input

The missing implementation is now specific: the successful host's accepted-image
construction, SPTM-aware initial entry, applicable monitor-argument/header version,
and memory ownership/fixups lifecycle, paired with board/firmware provenance and
physical-secondary entry evidence. An applicable SDK header alone would help
qualify the interface but would not provide the host or prove CPU release.
Offline inspection of original fixtures can narrow format rules while that
dependency remains unresolved. No new native attempt or unchanged reboot is
justified by this source comparison.

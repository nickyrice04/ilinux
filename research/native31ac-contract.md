# 31AC: a bounded native entry-observer contract

The next useful physical test is an original host that captures the monitor's
cold entry, checks the supplied memory ranges, and attempts a small distinctive
screen marker. It can test the previously unknown pre-service 15 table state at
runtime. Reconstructing the whole monitor initializer is not a prerequisite.
This note qualifies the implementation contract; it does not report a native
run or authorize an installed-object change. The separate
[launch procedure](native31ac-launch.md) owns that boundary.

## The local evidence supports a VHE profile

The retained monitor's declared entry branches to its primary preparation path.
Two bounded preparation windows explicitly test `CurrentEL == 8` before setting
both `HCR_EL2.E2H` and `HCR_EL2.TGE`, preserving the other HCR bits. The immediate
cold-entry thunk, direct cold-preparation body and common OS-exit body contain no
explicit HCR write. Thus a non-VHE-only observer would exclude a positively
supported local entry hypothesis. Implement both ordinary EL2 (`E2H/TGE=00`) and
VHE host EL2 (`11`), while recording the actual incoming registers. Mixed values
remain outside the first implementation profile; do not change HCR to force a
profile match.

This is a bounded static result, not proof of the complete path through every
intervening callee or of hardware state restored by GEXIT. Other retained context
transitions can change TGE. The common exit's previously qualified saved-status
construction also preserves the current EL rather than forcing EL1. Actual
`CurrentEL`, HCR and guarded-state context still belong to the native observation.
The [31AB entry finding](native31ab-entry.md) retains the earlier limitations.

The checked source is the unchanged 1376288-byte retained monitor, SHA-256
`da2ad8d4ecbf3e29fbaaa07e8c7d291ed20d296044494e00303c7a780d190666`.
Its 25G83 association is inherited from 31W, not refreshed against executing
firmware. Independent source/LLVM comparison rechecks 195 instruction-sized words
(780 bytes) in six ranges with zero mismatches. The HCR write sites are
`0xfffffff0270af0b4` and `0xfffffff0270af4a4`. No fresh REA query was necessary;
these are additional bounded interpretation and verification of retained input,
not 195 newly decompiled instructions. Apple bytes and instruction text remain
private.

## Runtime profile and translation format

Use explicit `AT S1E2R` for reads and `AT S1E2W` for framebuffer writes in either
supported EL2 profile. The pinned Linux KVM selftest exercises these operations
in the EL2&0 host regime before clearing TGE and testing the separate S1E1
operations. There is no need to introduce alias-sensitive S1E1 operations into
this observer. This primary software comparison and the original emulator tests
are distinct from native Apple behavior.
[Linux AT selftest](https://github.com/torvalds/linux/blob/03db5f05d4c76d76b32a9d26001e2ec6252f74f8/tools/testing/selftests/kvm/arm64/at.c).

Before any captured-pointer dereference, use the captured EL to select explicit
register banks, require EL2, masked DAIF, `SCTLR_EL2.M=1`, little-endian data
access, and one supported HCR pair. Own the stack and fatal vectors before
fallible reads. All code needed before `FIXUPS_COMPLETE`, including C helpers,
vectors and constants used as executable code, must remain in the initially
executable boot region; a separate ordinary executable segment is not enough.
The public XNU cold path initially relies on `__TEXT_BOOT_EXEC`.
[Entry/fixups ordering](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/start_sptm.s).

D128 capability and active D128 translation are different conditions. Ordinary
EL2 (`E2H/TGE=00`) uses VMSAv8-64 stage 1; it needs no TCR2 read. Arm's stage-1
VMSAv9-128 selection covers EL1&0, EL2&0 and EL3, not the ordinary EL2 regime.
For the supported VHE host profile (`11`), apply the following checks:

- `ID_AA64MMFR3_EL1.D128[35:32]=0` excludes the stage1 D128 format.
- If it is 1, require the recognized `TCRX[3:0]=1` capability and successfully
  read `TCR2_EL2`; require its D128 bit 5 to be zero. Unsupported feature values,
  active D128 or a trapped access do not qualify this 64-bit result decoder.
- An absent TCR2 must not be read speculatively. Do not write TCR2 to disable an
  unsupported mode. The first nonreturning host can explicitly own PAR as
  translation-result scratch state; it need not promise preservation of an
  unknown incoming 128-bit PAR value. A reusable API claiming preservation needs
  a separately sufficient save/restore contract.

[Arm address-translation regimes](https://support.arm.com/documentation/ddi0487/mc/-Part-D-The-AArch64-System-Level-Architecture/-Chapter-D8-The-AArch64-Virtual-Memory-System-Architecture/-D8-1-Address-translation?lang=en),
[Arm M.a known issues, section 2.18, pages 38–40](https://documentation-service.arm.com/static/69aac74fe79f9a1d642aa91f?token=).
The latter corrects the EL2 translation-base register D128 condition to require
effective `E2H=1`; it does not make support alone an active-format test.

The pinned Linux definitions establish the feature and register fields.
`TCR_EL2.DS` is bit 32 in the non-VHE layout; under VHE the corresponding host
layout has DS at 59 and IPS at 34:32. Non-VHE PS is 18:16. Record these with the
correct profile; DS is an address/descriptor sizing control, not a PAR-width
switch. Hardware performs the page-table walk, so DS alone need not reject a
valid 64-bit-format result. The 64-bit PAR address field covers bits 51:12; combine
it with the input VA's low 12 bits only after checking the fault indicator. Do
not truncate the expected physical address before comparing it.
[Linux feature/register fields](https://github.com/torvalds/linux/blob/03db5f05d4c76d76b32a9d26001e2ec6252f74f8/arch/arm64/tools/sysreg),
[non-VHE TCR definitions](https://github.com/torvalds/linux/blob/03db5f05d4c76d76b32a9d26001e2ec6252f74f8/arch/arm64/include/asm/kvm_arm.h),
[Arm 64-bit PAR description, section A2.1.16](https://documentation-service.arm.com/static/649ae5b238511951cb799288).
The last document is the retired RME supplement's 64-bit-format description, not
a source for D128 behavior or evidence that this Mac implements RME.

Synchronize after AT before consuming PAR. Probe the beginning of every 4 KiB
chunk intersecting each requested interval, with checked addition, an exact
exclusive end and bounded loops. That sampling covers the smaller boundaries within
all supported 4/16/64 KiB granules without guessing the active page size. A
successful AT result is still not a promise that a subsequent load/store cannot
fault: changing mappings, tags, additional hardware protections and external
errors remain possible. Fatal recording must terminate rather than attempt an
unqualified exception return. AT can affect translation caches and hardware
access flags; it is not universally side-effect-free.

## Only the fields this observer uses

Full-width cold reason 0 is required before interpreting x1/x2. The local
[consumer/producer finding](native31ab-observer-local.md) supplies the following
bounded reads; these values are obtained from this entry, not from historical
addresses or sanitized ADT placeholders.

| Input | Read and validation |
| --- | --- |
| x1 | 88-byte video prefix; expected ARM64 revision/version 2; checked geometry, stride, depth and complete framebuffer arithmetic |
| x2+416 | 32-bit helper version 10; only the selected local profile is recognized |
| x2+424, x2+432 | Two 64-bit virtual pointers: range count and range table |
| Count pointer | 32-bit count, restricted to 1..64 |
| Table pointer | Exactly 24 times count bytes; at most 1536 bytes |

Check each entire source interval with read translations before copying it to
owned storage. Reject Device-memory input records rather than treating an
arbitrary readable mapping as harmless RAM. Apply the original decoder to the
snapshot: physical base, virtual base and 16 KiB page count have distinct roles;
overflow, overlap and incomplete requested coverage fail. A zero count or
unmapped table is a runtime result to record, not permission to initialize or
repair monitor-owned state. Rechecking the small count/pointer set after copying
can detect observed changes, but does not prove absence of concurrent mutation.
No monitor call or page-table modification is needed for these reads.

This tests the missing initialization timing directly. It does not require
calling the kernel's local helper initializer, copying all 848 bytes, or invoking
service 15 merely to obtain a candidate table. No static assertion that the table
is ready before service 15 is added here.

## Framebuffer operation and interpretation

Use the supplied video physical address after stripping only its documented low
metadata bits. Resolve the chosen small rectangle through the validated range
snapshot. Before any pixel write, every touched interval must pass a write AT,
translate to exactly the expected physical address, and have a supported memory
attribute. Validate the entire plan first so a later rejected row cannot leave
an accidental partial marker. The original bounded plan limits the rectangle to
32×16 pixels with four-byte pixels; it does not authorize unrelated framebuffer
or device writes.

Two explicit visibility paths can be tested. For Normal non-cacheable ATTR 0x44,
use aligned volatile 32-bit stores followed by `DSB SY`. For Normal write-back
ATTR 0xff, additionally clean each intersecting cache line by VA to PoC using
`DC CVAC`, then complete with `DSB SY`. Derive the maintenance stride from
`4 << CTR_EL0.DminLine`; check rounding/loop arithmetic and the line-covered
extent, rather than hard-code a line size. Cache maintenance is ordinary allowed
operation under the selected profile, not permission to invalidate arbitrary
memory or alter cache controls. The native path must still handle an Apple
protection trap. Other attributes remain outside this first observer profile.
[Arm DC CVAC](https://support.arm.com/documentation/111107/2026-09/AArch64-Instructions/DC-CVAC--Data-or-unified-Cache-line-Clean-by-VA-to-PoC),
[framebuffer mapping comparison](native31ab-observer.md).

PoC completion does not independently certify the display's actual scanout or
platform coherency. A distinct visible marker would establish that execution
reached the marker-store/display path. It would not prove completion of cache
cleaning or the observer's final stage: a later fault or park can leave pixels
visible. The native experiment has no external RAM-record reader, and the marker
establishes neither service 15 success nor secondary CPU entry. A blank result
still combines image rejection, unsupported entry, unavailable argument/table mappings, a fault
and invisible scanout. Preserve that uncertainty rather than declaring an
Apple-only restriction. This contract enables a finite original native candidate;
its image, launch/return procedure and actual execution result remain separate.

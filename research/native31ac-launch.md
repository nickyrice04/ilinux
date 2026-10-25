# 31AC: one observable resident-entry attempt and exact recovery

2026-10-25. **Tested original candidate and plan prepared; installation and native execution NOT RUN.**
The original visible-entry image is intended to test whether the Mach-O boot
route reaches our cold-entry adapter and a bounded screen marker. It does not
start a secondary CPU, call the monitor, boot Linux, or measure performance.
The human sequence is in [the 31AC instructions](../tools/m1n1-client/attempt31ac-instructions.md).
The stable Mach-O is 180,224 bytes, SHA-256
`261d44447442f32ba6c41bbf0f69179e8c9eb4c33507b60762f0ea8c2e54ab72`.
The parent-owned receipt records 26 complete-payload QEMU cases, host compilation
and read-only property derivation; those qualify the tested original code and
parser behavior, not native firmware acceptance. The public manifest at
`native/boot/attempt31ac/manifest.json` binds the distributed archive and source.

## The concrete change

The existing lab is a distinct installed volume group. Its recorded baseline is
Permissive Security with boot021 installed; original Macintosh HD remains Full
Security. These are historical observations that must be checked again in the
lab's paired Recovery before an operation. The exact rollback file is already
staged on lab Data. [Existing installation record](../kernel/native-enablement/boot-entry-setup.md)
and [boot021 manifest](../native/boot/boot021-package-manifest.json).

The proposed test replaces **only the lab's active custom boot object**, using
`kmutil configure-boot` with the original Mach-O image. The rollback reinstalls
the unchanged boot021 raw image with entry 2048 and lowest virtual address 0.
Boot021's source file is never overwritten. Raw chainloading from the current
proxy does not itself establish the resident-monitor route under investigation.
The command modes are documented by the [Asahi m1n1 guide](https://asahilinux.org/docs/sw/m1n1-user-guide/#installation).
Its older Mach-O example establishes command syntax, not support for this new
image or this M5 Max firmware.

This is not a zero-policy-change experiment. Apple describes the custom-object
manifest hash as a LocalPolicy field updated by `kmutil configure-boot` in 1TR;
the anti-replay mechanism can re-sign LocalPolicy files when its nonce changes.
Preserving the original OS's Full Security therefore does not promise that all
policy bytes remain identical. No new security reduction, OS replacement,
volume creation, resize or erase is proposed.
[Apple LocalPolicy documentation](https://support.apple.com/en-au/guide/security/secc745a0845/web).

Paired Recovery follows the selected default installation. The plan explicitly
includes temporarily selecting the lab as Startup Disk, entering its paired
1TR, and restoring Macintosh HD as default after rollback. One-time startup
selection and default selection are different actions.
[Apple paired-Recovery documentation](https://support.apple.com/en-au/guide/security/sec4cf9d63a6/web).

The old `recovery-preflight.sh` defines useful read-only functions, but its
`ilinux_preflight` expects the historical Full/Full pre-install state. The new
instructions use a separate Full/Permissive preflight; they do not rerun initial
provisioning or change the frozen helper.

## Acceptance is an observation, not an inspector result

Read-only `kmutil inspect --show-mach-boot-properties` qualifies parser/property
behavior. The retained installed `configure-boot --help` offers no dry-run
acceptance mode. Only the authorized Recovery invocation can establish whether
that operation accepts this exact image; even exit zero does not prove execution.
The independent M1 review, final artifact hash and original-image inspection
precede the separate human authorization.

| Observation | Supported conclusion | Next action |
|---|---|---|
| Recovery rejects the exact Mach-O | This image/operation was rejected; retain the sanitized error | Restore boot021 if target/policy checks remain valid; inspect the error offline |
| Configure operation succeeds, expected marker is visible | Original entry reached the marker-store/display path; final cache completion is not independently visible | End the single attempt and restore boot021 |
| Configure succeeds, screen is blank or unchanged | Native outcome unresolved; acceptance, entry, profile refusal, mapping and scanout are not distinguished | End after the fixed observation window, restore boot021; no unchanged retry |
| Startup picker or original OS cannot be reached, or rollback fails | Recovery is incomplete | Stop automated guidance; do not add security changes, erase or restore actions |

A failed configure operation is not assumed atomic. Do not infer that the old
object is still selected, and do not convert a rejected Mach-O to `--raw` as a
fallback. The latter would change the very boot path being tested.

## Finite hardware profile and visibility

The integrated adapter accepts explicitly checked EL2 profiles: non-VHE
`E2H=TGE=0`, or VHE host `E2H=TGE=1`. It uses **S1E2R/W** for the current EL2
translation regime. The pinned Linux KVM selftest exercises S1E2R/W in EL2&0,
then clears TGE before its separate S1E1 tests. This supports retaining explicit
EL2 operations rather than relying on an EL1 alias.
[Linux selftest, pinned source](https://github.com/torvalds/linux/blob/03db5f05d4c76d76b32a9d26001e2ec6252f74f8/tools/testing/selftests/kvm/arm64/at.c).
Runtime state, not the public model or an inferred retained path, chooses which
profile applies. Mixed E2H/TGE profiles and EL1 do not gain support by analogy.

The PAR decoding profile separately excludes active D128. A D128 capability bit
alone does not mean it is active.
The pinned Linux register descriptions give MMFR3 D128 at bits 35:32 and TCRX at
3:0, each with known values 0/1; TCR2_EL2 is `S3_4_C2_C0_3`, with D128 at bit 5.
An optional-register read must be feature-qualified. VHE and non-VHE TCR fields
have different positions; VTCR fields must not be substituted for TCR fields.
[Pinned Linux register descriptions](https://github.com/torvalds/linux/blob/03db5f05d4c76d76b32a9d26001e2ec6252f74f8/arch/arm64/tools/sysreg#L2334).
Ordinary non-VHE EL2 uses VMSAv8-64 and needs no TCR2 read to exclude D128.
For the supported VHE EL2&0 profile, check the applicable active-format control.
[Arm ARM M.c, D8.1](https://support.arm.com/documentation/ddi0487/mc/-Part-D-The-AArch64-System-Level-Architecture/-Chapter-D8-The-AArch64-Virtual-Memory-System-Architecture/-D8-1-Address-translation?lang=en)
lists which regimes select VMSAv9-128; this separates a feature's presence from
the translation regime actually in use.
DS changes translation-descriptor interpretation, not the PAR result to 128 bits.
The 64-bit PAR format can carry output address bits 51:12; when implemented by the
adapter, that mask avoids an unnecessary 48-bit-only refusal. Probing every 4 KiB
boundary also covers the larger supported translation granules without walking
their page tables in software.
[Arm PAR definition, section A2.1.16](https://documentation-service.arm.com/static/649ae5b238511951cb799288).
The new host owns its PAR state and parks; preserving its low 64 bits is not a
promise to restore an incoming 128-bit producer state before returning.

Before any external descriptor read, the adapter checks the covered translation
pages. Before any marker store, it checks the covered framebuffer rows for write
translation, expected physical address and an explicitly supported effective
Normal memory attribute. It rejects aliases of protected input/payload pages. The
payload protection covers its first `0x24000` bytes, not the packager's appended
metadata/link-edit region at `0x24000..0x2c000`. AT itself
changes PAR and can interact with hardware access-flag handling; “no translation
control rewrite” is more precise than “all AT effects are read-only.” The
architectural checks do not establish every Apple protection or guarantee a
later access or scanout. The actual display is the intended discriminator.
[Earlier architectural qualification](native31ab-translation-probe.md).

The bounded marker can support Normal non-cacheable `0x44` directly and Normal
write-back `0xff` with a clean-to-PoC step. XNU's public console creates an explicit
framebuffer mapping and conditionally uses its uncached-normal mode; that is a
platform comparator, not proof that the incoming aperture already has the same
attributes.
[Pinned XNU video-console mapping](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/console/video_console.c#L2838).
For the write-back case, the original implementation can clean each intersecting
line by VA using `DC CVAC`, then complete with `DSB SY`. Arm permits an unaligned
VA, but translation can fault. Ordinary architectural EL2 execution is supported;
that is not a claim about every additional Apple protection. No trap control or
mapping is changed to force the instruction to succeed.
[Arm DC CVAC reference](https://support.arm.com/documentation/111107/2026-09/AArch64-Instructions/DC-CVAC--Data-or-unified-Cache-line-Clean-by-VA-to-PoC).

`CTR_EL0.DminLine[19:16]` encodes log2(words), so the minimum line size in bytes is
`4 << DminLine`; the actual register supplies it, not an assumed M5 constant.
Arm's [CTR field description](https://documentation-service.arm.com/static/5e7e1405b471823cb9de57ae)
documents the encoding; its Cortex-A55 example value is not an M5 measurement.
The clean covers cache lines intersecting the marker, potentially including
adjacent bytes; it does not invalidate them or expand the pixel-store region.
Completion to the architectural PoC is distinct from observed display scanout.
The native pattern is the visibility test, and these operations do not configure
the display controller or establish GPU support.

## Exact recovery anchor and remaining decision

Rollback is the unchanged 3,932,160-byte boot021 file, SHA-256
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`, built from
m1n1 `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Re-check its existing staged copy
before both installation and rollback. A second matching package copy is useful
recovery redundancy, not permission to replace the staged file silently.

Successful rollback means the Recovery command and post-checks succeeded;
boot021 execution is a separate observation if the human chooses to verify it.
Final return to Macintosh HD and restoration of its default selection must be
recorded explicitly. No USB proxy request is needed for this diagnostic.

This attempt can produce new evidence about a legitimate software path. A blank
screen, parser rejection or a guarded refusal cannot prove that an Apple update
is the only possible solution. Conversely, a marker does not prove physical SMP.
Only after the entry/observer result is reviewed should monitor lifecycle or a
single secondary become the next experiment.

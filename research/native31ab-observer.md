# 31AB: making an original entry observable

Checked 2026-10-25. A small screen marker is a plausible observer that does not
require a complete USB stack. **Its remaining prerequisite is a qualified
writable framebuffer mapping and visibility contract.** The boot video
descriptor supplies geometry; it does not independently supply that mapping.
This review performs no framebuffer access, monitor call, boot configuration or
native execution. It supplements the [entry findings](native31ab-entry.md) and
[public contract](native31ab-public-contract.md).

## Exact descriptor, bounded compatibility

The pinned public ARM64 header is XNU12377.121.6 at
`ac9718fb1af618d5ce8678d0dc6e8a58f252216f`,
`pexpert/pexpert/arm64/boot.h`. An original constants-only translation unit
included that header, using empty shims for two includes whose types are unused
by these declarations. AArch64 LP64 compile-only output establishes:

| Property | Bytes/value |
| --- | --- |
| `sizeof(boot_args)` / alignment |1152 /8|
| `sizeof(Boot_Video)` / its offset |48 /40|
| Revision / Version offsets |0 /2, each uint16|
| Video base / display / row bytes |40 /48 /56, each uint64|
| Video width / height / depth |64 /72 /80, each uint64|
| `virtBase` / `physBase` / `memSize` |8 /16 /24|
| `topOfKernelData` |32|
| Device-tree pointer / length |96 /104|
| Command line / boot flags / actual memory size |108 /1136 /1144|

The header defines revision2 and version2; depth occupies the low eight bits of
the depth word, with separate rotation/scale fields. This is the ARM64 header,
not the older ARM32 declaration with the shorter command line. The measured
1152-byte extent agrees with the retained local cold consumer's copy size;
size agreement does not authenticate every field or the incoming runtime
version. No compiled object was executed.
[Pinned declaration](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/pexpert/pexpert/arm64/boot.h#L22),
[local cold consumer](native31z-handoff.md).

The public platform initialization transfers those video fields into its console
descriptor and separately interprets depth, rotation and scale. This supports
reading a bounded video descriptor from an authenticated cold-entry x1 record;
it does not justify interpreting x1 that way for an unknown reason or layout.
[Platform initialization](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/pexpert/arm/pe_init.c#L436).

## Why the existing painter is not a resident-monitor mapping

The existing project [breadcrumb implementation](../native/hv/0002-ilinux-hv-t6050-hv003-crumbs.patch)
already bounds dimensions, stride, supported depth, address arithmetic and
rectangle stores. It writes directly before its own MMU initialization; afterward
it creates an identity mapping with non-cacheable memory attributes only when
that instance owns the mapping lifecycle. Its own refusal when it has not
observed that transition is relevant here. The
[earlier Linux framebuffer](../kernel/experiments/early-framebuffer/README.md)
likewise depends on separately validated mappings. Neither establishes access
under the resident SPTM's page tables.

Public XNU's console explicitly treats the initial video address as physical,
strips its low metadata bits, and requests a mapping through
`ml_io_map_unmappable`. It selects memory attributes appropriate to the platform;
the source's no-cache-cleaning comment is conditional on that setup. Thus neither
casting the physical base to a pointer nor applying a guessed physical-to-virtual
offset is a qualified substitute. A barrier alone does not establish scanout
visibility. The same console supports30- and32-bit modes using four-byte stores.
[Console mapping and attributes](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/console/video_console.c#L2838).

The hash-bound26.5 SDK offers a narrower target than rebuilding a complete host:
`sptm_phystokv` is a library translation into the physical aperture, requires no
monitor call itself, and reports failure. It does **not** promise that the returned
alias has framebuffer-compatible write permissions or cache attributes. Its
client state describes aperture ranges through an opaque pointer; it does not
publish the range-element layout. Separate APIs explicitly manage PAPT
cache/shareability attributes. The range representation and helper used by
this retained runtime must be qualified before an original implementation can
use them. Unused library services and unrelated outer-record fields may remain
opaque. [SDK provenance and scope](native31z-public-contract.md),
[public XNU translation wrapper](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm64/sptm/arm_init_sptm.c#L1384).

The smallest remaining observer discriminator is therefore whether the
monitor-provided framebuffer pages have a legitimate writable alias with the
required visibility properties. If that is established, a small original marker
can validate the descriptor, bound every destination row and write only its
distinctive pattern. It should preserve the existing RAM record and avoid
modifying page tables or device controls merely to force a result. A newly
visible distinctive marker would establish execution through that point; its
absence would still conflate entry failure, descriptor rejection, mapping failure
and invisible scanout. It would not prove that Apple must change firmware.

## Other output and offline validation

The same SDK declares fixed service45, `sptm_serial_putc(uint8_t)`, for dockchannel
output during early panics. Its stated use excludes ordinary printf, and XNU
disables it after serial initialization. A callable declaration does not establish
an externally reachable listener on this Mac. No such dockchannel observer was
qualified in this pass, so it cannot replace the missing screen/readback proof.

Installed KernelManagement utility version487.100.11 was queried with help only.
`inspect` exposes derived Mach-O boot properties and collection displays.
`configure-boot` exposes no validation-only/dry-run option. `check` checks
installed collections or kernel load information, rather than accepting an
arbitrary original boot image. `create` describes local code-signing checks;
those do not establish iBoot/SPTM acceptance. No configure, create, install,
authentication-bypass option or collection check was executed. The existing
[format inspection](native31y-format-probe.md) remains parser/property evidence,
not a boot-acceptance test.

This narrows the next work to the real mapping/observer contract. It does not
reintroduce a complete848-byte decoder, all helper initialization or full USB
implementation as a blanket prerequisite.

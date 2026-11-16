# J716c community firmware and deployment contract for 31AY

Research snapshot: November 15–16, 2026. This is an offline adoption record,
not an installation recipe or restart authorization. Public code was read as
data; no third-party program, installer or recipe was executed on the host.
The initial host observation was the generic running version/build:
26.6.2 / 25G83. The root agent then ran the reviewed narrow firmware reader
twice; it queried only the two fixed generic version properties, without a
registry dump. System firmware was observed as mBoot-20457.1.29; the running
OS firmware stayed UNKNOWN because its CFData length exceeded the reader's
bound. No rejected bytes were returned. No policy, boot-object, per-unit
identifier, firmware payload, mount or setting was queried or changed.

The accepted M1 review is `ee4f70c`, covering the 31AX offline controller on
`a3bbd5e01eb8dc9df5f8ad3bc4af0d81ee66127e`. It found no actionable
source defect and retained the matched-stack, deployment and manual-rescue
gates. This work supplies that stack's initial manifest; it does not turn an
offline reset/rescue component into a native kit.

## What can be adopted now

**Confirmed from the publisher's source record:** Cameron Cooper's reference is
the exact Mac17,6 / J716c / T6050 / G17C board, with 18 CPUs, on
**27.2.1 / 26B131 / mBoot-20457.41.3**. It reports bounded native CPU work,
N1 networking, accelerated graphics and internal-panel operation. It is a RAM
Arch/systemd/Hyprland engineering root, not persistent Omarchy or measured
macOS performance/power parity. This is a concrete existing software route;
the old project failures do not establish that this board must await an Apple
fix. [Published board status](https://github.com/cameroncooper/linux/blob/5e11068a1c6d8fccb155bc6e0159cc16107e53ec/Documentation/arch/arm64/apple-j716c-bringup/README.rst),
[published complete pins](https://github.com/cameroncooper/linux/blob/5e11068a1c6d8fccb155bc6e0159cc16107e53ec/Documentation/arch/arm64/apple-j716c-bringup/pins.json).

The new `native/stack/j716c-community/manifest.json` preserves that entire pins
object, its publication commit and source blobs. It separately records local
build slots, missing deployment inputs and false readiness/authorization
flags. In particular, the publisher's tested Image hash identifies its
historical bytes; the publisher expressly has not demonstrated a byte-identical
publication rebuild. Our new build needs its own hashes and receipts.

Adopt the exact kernel integration `a59e709c737777495c84541c6afb6c862bb79227`,
full config, its DT and modules as one build; graphics Aura Stage2
`9da61857f9d9262bd64c023fbc1b18315b12d0af`; and the pinned Mesa/userland
artifacts. The reference toolchain is LLVM/lld 22.1.8, Rust 1.96.1 and bindgen
0.73.2. The new offline jobs are 096 (kernel) and 097 (graphics). Do not substitute
boot042's diagnostic configuration, a partial J714s port map, or newest-head
versions for this tested combination.

## Firmware consists of separate dependencies

| Dependency | Established reference | Current qualification |
| --- | --- | --- |
| Running Original macOS version/build | Local 26.6.2 / 25G83 observation | Confirmed generic version only |
| Existing Lab OS version/build | Previously retained 26.6.2 / 25G83 observation | No new Lab read |
| Global system firmware / SFR | Must be compatible with the target OS firmware | System mBoot-20457.1.29 observed; required transition unqualified |
| Lab's selected OS iBoot and preloaded firmware | Publisher's 27.2.1 / 26B131 / mBoot-20457.41.3 stack | Not reproduced on this installation |
| Lab paired Recovery and enrollment tools | Correctly paired with the selected Lab OS | New-version environment unqualified |
| Extracted runtime firmware | Must match the selected OS-paired firmware and hardware | Required private local provisioning, not distributed in this repository |

Asahi distinguishes global firmware, per-OS firmware in the APFS stub, and
vendor firmware supplied to Linux at boot. It warns that OS-paired firmware is
not an interchangeable ABI; the vendor firmware archive should match it.
Its boot-chain description places iBoot2 and auxiliary firmware in the selected
OS's own boot environment. Updating the running Original alone therefore does
not demonstrate that the Lab uses the matched OS firmware.
[Pinned platform quirks](https://github.com/AsahiLinux/docs/blob/ed6f9d6ac4ac49a09924224ac07e7341a71e1e45/docs/platform/quirks.md#firmware-is-loaded-and-provided-on-boot),
[pinned boot-chain description](https://github.com/AsahiLinux/docs/blob/ed6f9d6ac4ac49a09924224ac07e7341a71e1e45/docs/platform/dev-quickstart.md#boot-process).

The publisher's single mBoot field does not separately inventory its global
system iBoot. Exact Aura source gates the graphics handoff on the **OS** iBoot
string. Our observed **system** string is therefore not a direct Lab OS
measurement. It is below the separate J714s 27.2 selector's system minimum,
supporting further transition planning; neither that comparison nor the
UNKNOWN running-OS field justifies broadening reads or claiming an exact
J716c firmware-update procedure is qualified.

Each installation has its own paired Recovery; security downgrades must use that
pair. Apple also warns that a newer macOS can install changes affecting the use
of an older version. Consequently, preserving Original's files and Full Security
does not imply that a Lab update has no shared firmware effects.
[Apple paired Recovery](https://support.apple.com/guide/security/paired-recoveryos-restrictions-sec4cf9d63a6/web),
[Apple multiple-version guidance](https://support.apple.com/en-us/118282).

**Inference for a future owner decision:** an exact supported refresh of the
existing Lab installation may avoid new Linux partitions while supplying the
required per-OS firmware. Its feasibility, signing/installer availability,
space requirements, shared system-firmware effects and recovery path must be
qualified first. Neither an Original upgrade nor a Lab upgrade is authorized
or requested by this record. Do not run the J714s partitioning installer on
this Max.

The installer source corroborates that firmware admission considers system
iBoot, running macOS, SFR, chip and board minimums separately. The published
J714s recipe selects 27.2 / 26B123, despite sharing mBoot-20457.41.3; this is
not the exact J716c 27.2.1 / 26B131 input set. A matching mBoot string alone
does not collapse these distinct image contracts.
[Pinned pure firmware selector](https://github.com/omacom/omarchy-mac-installer/blob/c07e54c2134a8ec1415e7e2b917589ae1d3d7dc9/Engine/overlay/src/omarchy_firmware.py),
[J714s firmware selection patch](https://github.com/betizzel/omarchy-m5/blob/7df16b1b51469edcf7d2f2a593d9e7437a0af71d/installer/patches-j714s/0001-Engine-J714s-on-the-27.2-stub-with-a-board-Mach-O-St.patch).

## The graphics gates explain why version matching matters

**Confirmed source behavior:** exact Aura9da reads OS
`firmware-version` separately from `system-firmware-version`. Its J716c GPU
handoff checks board/model/compatibles, OS mBoot-20457.41.3, valid firmware/UAT
ranges, a normalized loaded G17C text digest and valid per-unit power tables.
The DCP path separately checks the same OS iBoot, a pinned loaded DCP image and
the required ADT/DART/resource relationships. Firmware mismatch is already
handled by refusal or retention of the boot framebuffer; these checks must
remain. A host's marketing version alone cannot establish GPU compatibility.
[OS/system distinction](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/src/firmware.c#L548),
[GPU identity gates](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/src/kboot_gpu_j716c.c#L468),
[DCP identity gates](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/src/kboot_display_handoff.c#L3167).

The literal DCP interface version published to Linux is 27.2, while the board
report's installed OS build is 27.2.1. These describe different layers, not a
reason to rewrite the source's interface version. Keep the publisher's full
firmware tuple and the loaded-image checks together.

## Stage1 can be built, but the historical deployment is not supplied

The exact graphics Stage2 tree already contains the Mach-O wrapper, CTXR
confinement code and public Stage1 build instructions. Its README's older Mach-O
wording and chip-status table are not reliable evidence that this tree lacks
those implementations. The public T6050 guide builds Stage2 with
`CHAINLOADING=1 ESP_STAGE2=1` and describes omitting Stage2/debug proxy flags
for Stage1; release packaging documents independent Stage1 and Stage2 builds.
These are usable source recipes for a newly reviewed candidate. They do not
identify the publisher's actual installed Stage1 binary or its private
configuration.
[Exact T6050 guide](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/docs/t6050-linux.md),
[release build contract](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/docs/RELEASING.md),
[build selection](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/Makefile#L84).

For the confined EL2 path, the installed Mach-O must have `kcbz=0` and real
file-backed padding that creates a usable executable window. Aura reserves a
16 MiB slot; the 128 MiB kernel/module code window begins at the next required
2 MiB alignment. The kernel needs 16 KiB pages and
`CONFIG_ARM64_CTXR_EXECMEM`; modules and runtime executable allocations must
stay inside the same window. Ordinary CPU data/RAM is not limited to 128 MiB.
A confined core executing outside the permitted region can fault even if the
kernel otherwise builds and the boot CPU works.
[Exact confinement contract](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/docs/macho-boot-object.md#running-the-os).

The wrapper at 9da emits an unpadded object; padding is a separate installer
responsibility. Public MIT installer code supplies sparse file-backed
padding/inspection checks, including the 16 MiB slot and 128 MiB window.
The later Betizzel package demonstrates independent Stage1/Stage2 builds,
configuration fill, padding and separate ESP update paths, but its board
patches are J714s-specific. Borrow the reviewed general mechanism, not its
board authorization. Our prior candidate was already padded and our diagnostic
kernel already had 16 KiB/CTXR support; do not describe padding or page size as
a newly discovered explanation of the old blank-logo failure.
[Exact wrapper](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/tools/macho_boot_object.py),
[public padding implementation](https://github.com/aurora-silicon/aurora-installer/blob/832788c858f7bc5db8ba67d1232844977ffa8489/macOS/Recovery/Sources/Account/AuraStage1.swift#L372),
[J714s packaging example](https://github.com/betizzel/omarchy-m5/blob/7df16b1b51469edcf7d2f2a593d9e7437a0af71d/installer/recipes/m1n1-aurora-j714s/PKGBUILD).

A direct bounded RAM kernel avoids introducing U-Boot/Limine into the first
validation. A later persistent path must use CTXR-aware U-Boot and keep kernel,
DT, modules and window placement matched. A compressed zboot kernel is
different from an `Image.gz` that Aura decompresses before placing the normal
Image; do not equate those loading paths.

## Guardian, root and rescue are separate deliverables

The publisher explicitly excludes the installed Stage1/enrollment recipe,
Apple firmware, per-unit ADT/DROM, private root, connection settings and
host-side physical-watchdog guardian. Targeted public repository searches
found no guardian source; this is a bounded search result, not proof none
exists. A package-update guard does not replace a watchdog guardian. Before
adoption, retain default-off WFI, disabled runtime RTC/external ATC2, checked
temperature telemetry, firmware-owned fans and the reference's bounded CPU
ceilings. The root must carry the matching modules, early firmware provisioning,
network access, collection tools and J716c-specific update guards.

A firmware/Lab refresh is a new state transition. Old 26.6.2 policy anchors and
consumed transactions cannot be replayed against the new Lab. A newly authorized
experiment must take its baseline after that approved transition and preserve
Original's intended Full Security from then onward. boot021 remains an exact
known-byte reference, but its successful operation on the new selected firmware
is not established by historical 26.6.2 boots. Byte restoration and physical
fallback bootability are separate claims. Keep a route back to Original and
paired Recovery independently available; qualify the new-version rescue path
before declaring a boot transaction ready.

The next efficient sequence is:

1. Finish and independently check the pinned source builds and stack validator.
2. Produce the new Stage1 candidate/configuration and guardian/root design
   offline, with exact source, configuration and artifact receipts.
3. Resolve the exact Lab/system firmware transition and manual rescue plan;
   obtain separate authorization for any actual OS/firmware/boot change.
4. Only then prepare one bounded native run that checks loader/window admission,
   concurrent work on all 18 physical cores, timers, telemetry, N1 control and
   GPU/DCP correctness. Retain independent stop and return paths.
5. Integrate persistent Omarchy after this matched RAM stack passes; benchmark
   CPU/memory, input-to-frame delay, GPU, storage and power against this Mac's
   macOS baseline. Build/VM success is not native performance evidence.

No restart, firmware update, installation, policy operation or new physical
test is ready or authorized by this research.

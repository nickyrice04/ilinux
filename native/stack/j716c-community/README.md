# Matched J716c community stack

This is the source/build boundary for adopting Cameron Cooper's published
Mac17,6 / J716c / T6050 / G17C integration. It is not a boot kit, installer or
firmware-update authorization. `manifest.json` preserves the complete published
pin object and records local reproduction separately. Never relabel the J714s
ready image as a Max image.

The reference is [publication 5e11068a](https://github.com/cameroncooper/linux/blob/5e11068a1c6d8fccb155bc6e0159cc16107e53ec/Documentation/arch/arm64/apple-j716c-bringup/pins.json).
Its bounded native results establish an existing software route for all 18
CPUs, N1 and graphics on this board. They do not establish our native results,
persistent Omarchy, maximum CPU clocks, suspend or macOS power/performance parity.

Our deployment can qualify its own Stage1 built from public source; it does not
need the publisher's private installed binary. The new kit/profile must bind
our new artifacts and post-transition baseline. The old candidate's hash,
private anchors and consumed transaction state cannot stand in for that kit.
The generic build has blank factory configuration and enters proxy mode;
it is not an ESP-configured Linux installation. The existing Lab's APFS Data
directory is not an NVMe/FAT ESP. Matching Aura RAM-chainload and direct-composite
paths are public source options that still need explicit ABI, transport, layout,
root-transfer and recovery qualification before a no-new-partition boot proposal.

| Piece | Reproduction source |
| --- | --- |
| Kernel, modules and DT | Job 096, exact `a59e709c`, complete published 16K config; one build |
| Aura graphics Stage2 | Job 097, exact `9da61857`; firmware gates preserved |
| Generic Aura Stage1 candidate | Separate variant from the same source; new build, not the publisher's installed identity |
| Mesa Gallium/Vulkan | Job 097, exact `10161a78`; source build separately identified from published package assets |
| Firmware | Published OS 27.2.1 / 26B131; OS mBoot 20457.41.3 plus loaded GPU/DCP identity checks |
| Desktop | Reference Arch/systemd/Hyprland 0.57.2; our Omarchy integration remains a separate task |

The source builds passed. Kernel job 096 produced a 16K Image and 1,749
same-release AArch64 modules. Graphics job 097 produced both Aura variants,
the LLVM22 translator, Vulkan/EGL/GLES/GBM and unified Gallium. The source-build
DESTDIR is not an Arch package or an Omarchy overlay ready for installation;
its Wayland-only, GLVND-disabled options differ from a full desktop package.

Unchanged Mesa passed 175/179 CPU/offline Asahi tests. Four tests demand BLIT
where the driver intentionally advertises DEFAULT/CPU transfers. A separate
[test-only correction](../../../kernel/experiments/j716c-mesa-blit-tests/README.md)
preserves that generation-specific policy and adds CPU format round trips;
its suite passes 179/179. Shipping driver and baseline artifacts remain
unchanged. Guest exit 1 retains the baseline failures; normal VM shutdown exit
0 is not substituted for that test result. None of these tests exercises a
physical G17C GPU.

Builds use a case-sensitive filesystem inside the existing ARM64 Linux VM.
Source, output and toolchains can live in bounded guest tmpfs; exported archives
and receipts live in ignored workspace build directories. Both workspace VM
locks must be held because the two runners share one guest disk. Do not extract
Linux's case-colliding files onto the host filesystem. No public-source build
script is executed on macOS.

Source/config/toolchain admission, compilation, packaging and native validation
are different checks. A rebuild's SHA need not equal the publisher's measured
Image: the publisher explicitly does not assert byte-identical reproduction.
Record differences such as a version-matched bindgen with different bytes.
Source DT data containing another machine's unit-specific DROM stays private
and nondeployable; a runtime tree must use independently provisioned local data.
Apple firmware, raw ADT, private keys, VM images and compiled outputs never enter
public Git.

The held kernel archive includes `aurora.ko` (Asahi), `appledrm.ko`,
`apple_centauri_t6050.ko`, `apple-soc-cpufreq.ko`, SMC telemetry and SPI-HID
modules. Apple NVMe and watchdog code are built in. These names matter when
assembling the new root; do not assume the GPU module is named `asahi.ko`.
Their static presence and matching vermagic do not establish hardware operation.

## Read-only validation

```sh
python3 -I native/stack/j716c-community/validate.py native/stack/j716c-community/manifest.json
python3 -I -m unittest discover -s native/stack/j716c-community -p 'test_*.py' -v
python3 -I -m unittest discover -s tools/firmware31ay -p 'test_*.py' -v
```

An optional `--artifacts-root .` from the repository root checks the recorded regular files by
size and SHA, without following artifact path symlinks. This verifies receipt
consistency, not that a compiler produced a safe program. Even a valid manifest
and all successful builds return `native_ready=false`, `restart_ready=false`
and every deployment gate unmet. Authorization never comes from these files.

## Initial package-update protection

`package_guard.py` and the two ALPM hook templates borrow the community's useful
pre-transaction protection idea, with an explicit J716c/T6050 check and an
initial frozen-stack policy. The [community implementation](https://github.com/betizzel/omarchy-m5/blob/7df16b1b51469edcf7d2f2a593d9e7437a0af71d/installer/recipes/omarchy-aurora-firmware/m5-boot-guard)
otherwise falls back to J714s. Our implementation does not infer a Max from an
unknown or unreadable device tree.

The first package profile refuses replacement/removal of the matched kernel,
loader, firmware, Mesa/Vulkan and Hyprland packages. A second file-trigger hook
catches a differently named package writing protected boot/module/renderer
paths. Ordinary software updates remain available. There is no environment
override, one-shot sentinel, repository-version guess or update action. A future
reviewed profile can introduce an atomic replacement transaction with exact
artifact admission; arbitrary version suffixes are insufficient evidence.

These are uninstalled templates, tested as pure decisions and CLI refusals.
The hooks still need genuine ALPM validation in a disposable Linux root before
integration. They do not protect arbitrary direct root writes or replace the
physical watchdog guardian, backup or rescue controller.

The [watchdog contract](watchdog-contract.md) identifies the remaining guardian
work from the exact loader/kernel sources. `lease.py` tests a finite renewal
decision protocol without any device or transport writer. The standard Linux
UAPI is suitable after ownership; T6050 pre-Linux arming and the published
config's indefinite pre-open feeding still require explicit integration and
physical expiry tests. Neither killing an M1 process nor a watchdog reset
automatically selects Macintosh HD.

## Firmware and deployment boundary

The narrow optional version reader in `tools/firmware31ay` reads only two generic
properties from the running OS. It cannot identify another installation's OS
iBoot, GPU firmware, paired Recovery or selected boot object. Its public shape
diagnostics never print rejected bytes.

See the [firmware findings](../../../research/attempt31ay-firmware-2026-11-15.md)
for the exact source checks and current observations. A supported transition
must qualify global system firmware **and** the existing Lab's OS-paired boot
firmware/Recovery/runtime firmware. Updating Original alone does not qualify
Lab. Refreshing Lab can still have global firmware effects. Exact installer
availability, signing, preservation and rescue need review before an owner
decision. No firmware or boot-setting change is authorized here.

The [installer availability check](../../../research/attempt31ay-installer-availability-2026-11-16.md)
finds Apple's generic J716cAP update advertisement and reachable exact restore
object. It does not verify an installer package or TSS signing. The inspected
community policy excludes this exact board/build and its startup-update executor
is unfinished. Qualify an Apple installer refresh of the existing Lab instead
of relabeling that automatic updater or running the Pro partitioning recipe.

Do not reuse old private policy anchors across a firmware/Recovery transition.
The AX reset/rescue controller is reviewed offline, not yet a deployed kit.
Boot021 remains a known byte reference; successful operation on a new firmware
baseline must be requalified. A concrete manual rescue, Stage1 enrollment, host
guardian and owner-approved single test must precede any new restart cue.

The first native acceptance target is one matched RAM boot proving CPU topology,
accelerated panel rendering, N1 connectivity and responsive keyboard/app actions,
with checked temperature and the reference's conservative clock/idle limits.
This machine's retained inventory distinguishes twelve Performance cores in two
six-core M clusters from six Super cores in a P cluster. Check all three clusters,
their cache/affinity topology and scheduler capacities; eighteen online CPUs
alone do not prove correct heterogeneous scheduling or maximum clock behavior.
Static DT capacity values are declarations, not measured performance.
Then compare the same CPU/RAM/graphics workloads and energy measurements against
macOS. SSD support and APFS interoperability require their own read/write plan;
do not mount Original writable or infer storage-speed parity from a driver build.

# Matching a working J716c boot stack and choosing firmware deliberately

Research date: November 15, 2026. Public sources were read as data. No foreign
recipe, installer, binary or hook was executed; no host update, download of
firmware, partition, volume, policy or boot-setting operation occurred. Sources
below report other owners' hardware results, not tests repeated on this Mac.

## Decision

Do not update Macintosh HD simply to fix attempt 31AR. Its actual error was an
unavailable shell comparator before controller dispatch; neither Aura nor Linux
was tested. Boot021 restoration remains outstanding in that result. A newer
macOS is not evidence that this dependency or our transaction has been repaired.

For the next accelerated Linux baseline, however, a deliberately matched
**27.2.1 / 26B131 J716c firmware and software stack** has substantially better
evidence than our current 26.6.2 lab. Reproducing it is a concrete software path,
not a reason to assume that all-core Linux must wait for a future Apple fix.
Any actual firmware or OS change remains separate work requiring an explicit
reviewed plan and authorization. The current work preserves Macintosh HD.

The root agent's fresh, whitelisted read-only version check on this date
observed **26.6.2 / 25G83 for both the running macOS and mounted lab System**.
Only version/build fields were returned; no firmware query or update ran.
These local observations are separate from the external 27.2.1 hardware report.

## How the other Omarchy project boots

The released J714s image is a native disk installation. Its chain is:

```
Apple boot firmware and the installation's 27.2 stub
  -> padded Mach-O Aura Stage 1, no __TEXT_BOOT_EXEC / kcbz zero
  -> Aura Stage 2 in the install's ESP: m1n1/boot-ctxr.bin
  -> patched U-Boot, with CTXR-aware EFI image placement
  -> Limine EFI loader and the install's unified kernel image
  -> Linux / Omarchy from its own disk partitions
```

The Stage 1 is configured for that install's ESP and uses a 128 MiB executable
window. The compatible kernel confines executable allocations to that window,
allowing the selected native EL2 path on the secondary cores. Ordinary Stage 2
updates do not re-enroll Stage 1. This is not virtualization, and it retains a
macOS boot choice. Our embedded diagnostic instead loads a RAM kernel/root and
does not require their persistent U-Boot/Limine installation. Sources:
[release 7](https://github.com/betizzel/omarchy-m5/releases/tag/omarchy-j714s-7),
[Aura package](https://github.com/betizzel/omarchy-m5/blob/9b74652a81652493a997d1fec9f9a927c94adc57/installer/recipes/m1n1-aurora-j714s/PKGBUILD),
[U-Boot package](https://github.com/betizzel/omarchy-m5/blob/9b74652a81652493a997d1fec9f9a927c94adc57/installer/recipes/uboot-aurora/PKGBUILD),
[Limine image contract](https://github.com/omacom/omarchy-mac-installer/blob/c07e54c2134a8ec1415e7e2b917589ae1d3d7dc9/image-builder/builder/apple_limine.py).

The loader and kernel must agree about placement. Aura's primary guide explains
that an incompatible U-Boot or compressed zboot path can place the kernel
outside the executable window and leave only the boot CPU. A 16 KiB page-size
choice alone is not the multicore solution. Its older chip-status table is not
the current T6050 support inventory; use the newer board reports alongside it.
[Aura's exact window contract](https://github.com/aurora-silicon/aura/blob/22b71758dfd048f6a874073db55fbe6bd1d17f44/docs/macho-boot-object.md).

## Use the exact Max board as the main reproduction reference

The J714s installer admits the **14-inch M5 Pro**, explicitly excluding the Max
and 16-inch models. Its advertised host requirement is macOS 27.2 or later, but
the image itself selects a specific 27.2 restore row. Do not run its partitioning
installer on this J716c or replace our board tree with its physical port, panel,
speaker or power maps. [Current pinned README](https://github.com/betizzel/omarchy-m5/blob/9b74652a81652493a997d1fec9f9a927c94adc57/README.md).

Cameron Cooper publishes a closer match: **Mac17,6 / J716c / T6050 / G17C**, on
27.2.1 build 26B131, mBoot 20457.41.3. The status describes all 18 CPUs online,
N1 networking and key-authenticated SSH, native GLES/Vulkan and a 32-frame
checkerboard readback with zero mismatches. It is a RAM Arch/systemd/Hyprland
engineering environment, not persistent Omarchy. CPU ceilings are around 2 GHz
with checked telemetry; suspend, deeper idle and several peripherals remain
unqualified. Online CPUs do not establish macOS performance parity.
[Frozen board status](https://github.com/cameroncooper/linux/blob/5e11068a1c6d8fccb155bc6e0159cc16107e53ec/Documentation/arch/arm64/apple-j716c-bringup/README.rst).

The owner's separate report describes a ten-minute mixed CPU/GPU correctness
run across all 18 cores at bounded frequencies. This is stronger than merely
listing online CPUs, but is still an attributed report rather than our physical
validation. [Owner's hardware update](https://github.com/omacom/linux-aurora/issues/293#issuecomment-6798385998).

| Input | Published exact reference |
| --- | --- |
| Kernel integration | `a59e709c737777495c84541c6afb6c862bb79227` |
| Paired opt-in graphics Aura Stage 2 | `9da61857f9d9262bd64c023fbc1b18315b12d0af` |
| Their upstream bases | Our existing `dc8f6f77934b` Linux / `bd9f3e8273dc` Aura lineage |
| Configuration | Full frozen config; SMP, 16 KiB pages and `CONFIG_ARM64_CTXR_EXECMEM=y` |
| Toolchain | LLVM/lld 22.1.8, Rust 1.96.1, bindgen 0.73.2 |
| Firmware | 27.2.1 / 26B131 / mBoot 20457.41.3 |

These references include source/config and tested-image hashes. They do not
supply the installed Stage 1, complete enrollment recipe, Apple firmware,
per-unit ADT, private root or host guardian. The Stage 2 commit specifically
qualifies graphics handoff; it is not a turnkey boot package. Rebuilding does
not automatically reproduce the tested binary bytes.
[Published pins](https://github.com/cameroncooper/linux/blob/5e11068a1c6d8fccb155bc6e0159cc16107e53ec/Documentation/arch/arm64/apple-j716c-bringup/pins.json).

There is also merged J716c GPU/panel work in the shared kernel. PR 1276 reports
G17C, internal-panel Hyprland, public Mesa and dock input/Ethernet. Its CLPC
connection raises the memory/fabric floors during GPU work; the reported GPU
memory-read result rises from 89 to 292 GB/s. That directly supports investigating
memory policy together with graphics instead of assuming the RAM is already
operating optimally. It does not prove CPU memory bandwidth or all-core
concurrent correctness. [Merged J716c implementation](https://github.com/aurora-silicon/linux/pull/1276).

## Current head is not the tested release

The repository head inspected was `9b74652a81652493a997d1fec9f9a927c94adc57`.
It changes the kernel recipe to `c0a2a7522b4eb123f3f1fcf1c9b842b773ae480f`
(v272-12), explicitly marked built but not booted. The released image 7 retains
the v272-11 kernel from the tested release 6 setup. Aura remains pinned to
`22b71758dfd048f6a874073db55fbe6bd1d17f44`; its U-Boot recipe pins
`70e990818a895454780797beedc6a7bdac9e2fd6`.
Use a matched hardware-tested baseline before adding the newest suspend series.
[Head's build-only status](https://github.com/betizzel/omarchy-m5/commit/9b74652a81652493a997d1fec9f9a927c94adc57).

## What an OS update would and would not establish

The installer checks system iBoot, running macOS and SFR minimums before offering
an OS firmware row. Its J714s patch explicitly requires a 27.2 system baseline
for the 27.2 stub. A later host can select that older supported stub, but an
arbitrary latest host version is not the firmware contract for every GPU/ISP
handoff. This is source-based selection policy, not a proven J716c update plan.
[Firmware filtering](https://github.com/omacom/omarchy-mac-installer/blob/c07e54c2134a8ec1415e7e2b917589ae1d3d7dc9/Engine/overlay/src/omarchy_firmware.py),
[device-specific 27.2 selection](https://github.com/betizzel/omarchy-m5/blob/9b74652a81652493a997d1fec9f9a927c94adc57/installer/patches-j714s/0001-Engine-J714s-on-the-27.2-stub-with-a-board-Mach-O-St.patch).

Updating Macintosh HD alone would not demonstrate that the existing Linux lab
has the required selected OS firmware or preloaded GPU bytes. Each installation
has its own paired Recovery. Conversely, a second OS volume is not a guarantee
that firmware effects are isolated: Apple warns that changes installed by a
newer macOS can affect using an older version. Keep the original installation's
Full policy; distinguish retaining its files from promising no shared firmware
change. [Apple paired Recovery](https://support.apple.com/guide/security/paired-recoveryos-restrictions-sec4cf9d63a6/web),
[Apple multiple-macOS guidance](https://support.apple.com/en-us/118282).

## Next practical work

1. Repair both Recovery boxes without `cmp`, test actual restricted-utility
   shell execution, and preserve the current kernel, helper, kit and old state.
   The refusal did not enroll a new transaction or consume a native window.
2. Reproduce and audit the exact J716c source/config/graphics pair offline.
   Map its runtime DT safety gates, Stage 1/window requirements, firmware rows,
   telemetry limits and Mesa into our existing build recipes. Keep authorship
   and original public patch provenance.
3. Before any OS/firmware action, choose the exact supported J716c build, check
   current system/selected-lab requirements, establish the restoration plan and
   current external backup, and obtain separate explicit authorization. Avoid
   beta selection or an in-place lab refresh based only on a version number.
4. Use one reviewed native run to collect loader/Linux entry, real concurrent
   per-core work, timers, bounded telemetry, memory checks and N1 control access.
   Follow with accelerated desktop/input tests on the matched graphics stack.
5. After stability, qualify a persistent Aura/ESP/U-Boot/Limine/Omarchy chain
   and update guards. Measure CPU/memory, input-to-frame latency, GPU bandwidth,
   storage, power and suspend against comparable macOS runs. None of the cited
   build or correctness reports establishes daily-use parity on this computer.

## Build delta against this project's diagnostic profile

A bounded source/receipt comparison found that our existing 31AH/31AJ build
already enables SMP, 16 KiB pages and CTXR executable-memory confinement. Merely
changing page size would not reproduce the published Max graphics environment.
The old `kernel/experiments/direct31ah/linux/check_config.py` intentionally
rejects Rust, graphics/PMP/SEP/AOP support and limits configured CPU capacity.
Keep that diagnostic validator frozen and introduce a separate graphics-profile
validator instead of weakening its safety assumptions.

The published full configuration has Rust and graphics/PMP modules, with
`NR_CPUS=512`. That is possible kernel capacity, not the number of workers to
launch on this eighteen-core machine; the existing collector's 64-worker bound
already covers its actual CPU set. The reference notably leaves
`CONFIG_DRM_ASAHI_M5` unset while carrying relevant source backports and other
graphics families. Enabling a symbol merely because its name says M5 would not
reproduce this tested build.

Configuration alone does not enforce runtime exclusions. The reference builds
RTC support but disables RTC and external ATC2 in its runtime device tree. Carry
those gates, the bounded frequency policy, valid SMC thermal telemetry and the
external stop/guardian procedure into any new systemd/Omarchy root.

Existing VM receipts show successful builds using GCC 16.1.1 with kernel Rust
disabled, and different Aura LLVM/Rust toolchain versions. They do not establish
that the reference's LLVM 22.1.8, Rust 1.96.1 and bindgen 0.73.2 or all source
dependencies are cached. The project's isolated toolchain machinery is a useful
foundation; preflight it before claiming an offline graphics build is ready.
No new compiler, VM, download or kernel build was run for this comparison.

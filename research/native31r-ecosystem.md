# 31R: related projects and the public CPU/GPU implementation boundary

Checked 2026-10-23. Public-source research only. No third-party code was executed,
no native operation was attempted, and no upstream message was sent. The search
included official project pages, GitHub revisions, source files and issue/PR
records. It is bounded evidence, not a census of unpublished work.

## Decision

There are substantial related projects to build on. **No newly verified T6050
secondary-start fix or admitted G17C Linux graphics path was found.** The most
useful new sources are Aurora's M5 Mesa proposal and the newer public Gravity
developer branches. They deserve targeted offline comparison before more
implementation is written. Their actual chip predicates and kernel contracts
matter more than an umbrella “M5” or “Apple9” label.

The project's 31Q state remains unchanged: CPU1 execution is unverified; G17C
firmware ownership, address domains and runtime ABI are unqualified; native
SMP/acceleration have not run. See [31Q CPU findings](native31q-firmware.md),
[31Q GPU findings](native31q-gpu-firmware.md) and
[the original GPU planner](native31q-gpu-planner.md).

## Who is pursuing related work

| Project | Verified current role and scope | Relevance to this M5 Max |
|---|---|---|
| **Asahi Linux / Fedora Asahi Remix** | Platform enablement, m1n1, kernel and Mesa work, with Fedora integration. The September 6 M3 release added substantial device support but explicitly excluded performant GPU acceleration. The current M5 feature table still marks its listed SoC blocks TBA. | Foundational code and platform documentation; the M5 table is not a claim that no experimental fork boots. Sources: [M3 announcement](https://asahilinux.org/2026/09/m2-episode-1/), [M5 table](https://asahilinux.org/docs/platform/feature-support/m5/), [Fedora](https://asahilinux.org/fedora/). |
| **Gravity Linux** | Independent hardware-enablement project aimed at M4 and newer, distributed as a Fedora remix. Its public release is an early alpha for the M4 Mac mini with GPU acceleration; power management and suspend remain limited. Its FAQ attributes an unresolved M5 Pro/Max secondary-core problem to platform misconfiguration. | Closest direct public hardware-development comparison. The M4 result is not M5 Max support, and the FAQ is the project's report, not an Apple erratum. Sources: [release/support page](https://gravitylinux.org/), [FAQ](https://gravitylinux.org/about/). |
| **Aurora Silicon** | Public kernel, bootloader, Mesa and distro integration work. The current M5 Mesa proposal includes AGX3C/HAL300 work; its rebased tree has host-only validation. The inspected integration kernel has an A18 Pro/T8140 G17 binding. | Valuable compiler, GPU-VM, firmware-channel and completion/recovery code. G17P/A18 Pro, G17G/base M5, G17S and this machine's G17C must remain separate. Sources: [project](https://github.com/aurora-silicon), [Mesa PR47](https://github.com/aurora-silicon/mesa/pull/47), [pinned kernel binding](https://github.com/aurora-silicon/linux/blob/6af6603bf854f01e934d1153d31ac02b821fa885/drivers/gpu/drm/asahi/driver.rs#L140-L198). |
| **Mesa Asahi / Honeykrisp** | Shared graphics components: shader compilation, OpenGL and Vulkan implementation. Honeykrisp originated as the native Apple Vulkan driver; it is not a separate Linux distribution. | Reuse the compiler, API and userspace infrastructure once the actual kernel/firmware contract is qualified. Shader generation alone cannot initialize this GPU. Sources: [Honeykrisp introduction](https://asahilinux.org/2024/06/vk13-on-the-m1-in-1-month/), [Mesa driver documentation](https://docs.mesa3d.org/drivers/asahi.html), the pinned code below. |
| **Ubuntu Asahi** | Community Ubuntu packaging/image integration using Asahi's platform work. Its README says it follows reference-distribution releases and aims at feature parity. | Packaging and installation examples; no separate T6050 startup or G17C solution established by those claims. Sources: [website](https://ubuntuasahi.org/), [README at ed2868b](https://github.com/UbuntuAsahi/ubuntu-asahi/blob/ed2868b96efe0eaa32fe87b706eba5071f679e1c/README.md). |
| **NixOS Apple Silicon** | Nix packages and modules intended to reproduce the Asahi reference configuration. The canonical repository is now under `nix-community`; the older `tpwrules` URL redirects. | Reproducible system assembly and firmware integration, rather than evidence of different hardware capability. Source: [README at b33a26a](https://github.com/nix-community/nixos-apple-silicon/blob/b33a26ae250666760abceb0634b5a22440244f6b/README.md), [release notes](https://github.com/nix-community/nixos-apple-silicon/blob/b33a26ae250666760abceb0634b5a22440244f6b/docs/release-notes.md). |
| **Asahi ALARM** | Arch Linux ARM integration built on Asahi; its installer offers several desktops, including Hyprland. Current PKGBUILDs remain active. | A particularly relevant packaging base for Omarchy. Choosing Arch/Hyprland does not supply missing hardware drivers. Sources: [website](https://asahi-alarm.org/), [PKGBUILDs at 39699ec](https://github.com/asahi-alarm/PKGBUILDs/tree/39699ec74ed71b1a2bf60a67b066d5c2775442e8). |
| **omarchy-mlx** | MLX Vulkan and ANE work on Linux, with tested M1/M1 Max/M2 Max targets and same-machine macOS comparisons. Its supported installer targets are M1-class Macs and M2 Max. | A direct example of Omarchy/Apple performance work, useful later for workload correctness and profiling. Its results are not M5 GPU support. Source: [project and hardware table](https://github.com/joshuaswarren/omarchy-mlx), [author's October 8 report](https://joshuawarren.com/blog/i-made-llamacpp-18x-faster-on-apple-gpus-under-linux/). |

Independent experiments add more specific evidence. The retained
[M5 Pro raw-path report](https://github.com/rolotrealanis98/m5pro-linux/blob/bb0c75e69d06247faf595641c5a12b0fadc415d2/docs/smp-t6050-raw-path.md),
[Sowyu CPU checkpoint](https://github.com/Sowyu/m5-azahi/blob/82c90a5fd0b841d3acec4f558f9424b2cefec8bf/research-archive/probe/CPU-CHECKPOINT.md)
and [qspqww J716c findings](https://github.com/qspqww/m1n1/blob/90f3be1d34a5af87e04fffead4f3cdb44d8fd046/findings.md)
remain useful negative T6050 startup observations. Their relevant revisions were
unchanged when checked. Conversely, the
[base-M5 GPU handoff](https://github.com/sh1ftmaker/m5-linux-research/blob/d220c02ab2bc3cedb9a956061bce5106a1e44049/research/handoff-final/gpu.md)
reports a retired bootstrap no-op on T8142, followed by a failing Mesa user job.
That is a research milestone, not a working M5 Max desktop. Earlier CPU details
and limits are preserved in [31N](native31n-upstream.md) and
[31O](native31o-upstream.md).

## Newest useful GPU lead: Aurora Mesa PR47

The open [proposal](https://github.com/aurora-silicon/mesa/pull/47) was checked at
head **`bd4290aef2b0f68afb3dd508a527fdaf0729b196`**, updated October 23. It describes
G17G/G17S compiler and Honeykrisp work, including command formats, resource
interfaces and synchronization. It explicitly says the rebased tree has no GPU
runs. Historical performance/CTS results quoted in commit messages are not a
qualification of this head or this machine.

The source gives a precise reason it cannot simply replace this project's Mesa:

| Pinned source | What is established |
|---|---|
| [`agx_chip.c`, identity/ISA classification](https://github.com/aurora-silicon/mesa/blob/bd4290aef2b0f68afb3dd508a527fdaf0729b196/src/asahi/lib/agx_chip.c#L63-L145) | G17C is recognized and assigned AGX3C encoding. Recognition/code generation is distinct from runnable device admission. |
| [`agx_chip.h`, M5 helper](https://github.com/aurora-silicon/mesa/blob/bd4290aef2b0f68afb3dd508a527fdaf0729b196/src/asahi/lib/agx_chip.h#L548-L553) | `agx_chip_g17_m5()` includes G17G and G17S, **not G17C**. |
| [`agx_chip.c`, bring-up predicate](https://github.com/aurora-silicon/mesa/blob/bd4290aef2b0f68afb3dd508a527fdaf0729b196/src/asahi/lib/agx_chip.c#L310-L323) | The experimental admission requires one die, USC3 and HAL300; it accepts T8142/G17G with one cluster or T6050/G17S. G17C is excluded. |
| [`agx_device.c`, opening](https://github.com/aurora-silicon/mesa/blob/bd4290aef2b0f68afb3dd508a527fdaf0729b196/src/asahi/lib/agx_device.c#L895-L920) | The M5 path requires the explicit bring-up option and describes general rendering as unqualified. This note is not a suggestion to enable the option. |
| [`agx_m5_va.h`](https://github.com/aurora-silicon/mesa/blob/bd4290aef2b0f68afb3dd508a527fdaf0729b196/src/asahi/lib/agx_m5_va.h) | A concrete userspace address-window layout to compare with the original planner, not proof of G17C physical-address translation or UAT geometry. |
| [Kernel `driver.rs`](https://github.com/aurora-silicon/linux/blob/6af6603bf854f01e934d1153d31ac02b821fa885/drivers/gpu/drm/asahi/driver.rs#L140-L198) | At inspected `integration/aurora` head `6af6603bf854f01e934d1153d31ac02b821fa885`, the G17 match is `apple,agx-t8140`; the table contains no T6050/T8142 GPU binding. |
| [Kernel `hw/t8140.rs`](https://github.com/aurora-silicon/linux/blob/6af6603bf854f01e934d1153d31ac02b821fa885/drivers/gpu/drm/asahi/hw/t8140.rs#L1-L49) | Its concrete configuration is A18 Pro, variant P, HAL200 and 42-bit UAT input/output. These constants are not a G17C profile. |

The fetched Mesa/kernel UAPI headers also differ: SHA-256 `72d4918b…43b88`
versus `697f494b…dd21`. This alone does not prove binary incompatibility, but it
prevents claiming the byte-identical pairing established for the older Gravity
foundation. PR47 lists required M5 extensions; they must be checked explicitly.
**A matching T6050/G17C firmware contract for the retained 25G83 environment was
not established.** A version label or widening a predicate would not supply it.

### Bounded ABI comparison for the existing planner

Static declaration comparison of the pinned
[Mesa header](https://github.com/aurora-silicon/mesa/blob/bd4290aef2b0f68afb3dd508a527fdaf0729b196/include/drm-uapi/asahi_drm.h)
and [kernel header](https://github.com/aurora-silicon/linux/blob/6af6603bf854f01e934d1153d31ac02b821fa885/include/uapi/drm/asahi_drm.h)
finds the following. Offsets/sizes below are derived from the explicit integer
declarations and documented natural/8-byte alignment, **not a compiled-layout or
ioctl execution result**. The comparison covers the planner's inputs and a
future adapter, not the whole DRM interface.

| Item | Both headers / actual difference | Consequence for original code |
|---|---|---|
| GPU VA window | `vm_start`, `vm_end`, `vm_kernel_min_size` remain unsigned64 at offsets552/560/568. | Keep all64 bits; no narrowing to the GPU's separately qualified hardware width. |
| Global parameter reply | Shared first600 bytes; Mesa declares600 bytes, kernel appends two unsigned64 memory limits at600/608, totaling616. `GET_PARAMS` remains24 bytes and carries a size bound. | Query into a zeroed, size-qualified reply; do not require whole-header identity or invent values for absent tail fields. |
| VM creation |24 bytes in both: unsigned64 reservation endpoints at0/8 and unsigned32 VM ID at16. Offset20 is Mesa's zero padding, but the kernel calls it `flags` and defines HAL200 acknowledgment bit0. | The reservation math is reusable. A future adapter must resolve this semantic difference; equal sizes do not establish interchangeable VM creation. |
| One bind operation | Identical32-byte declaration: unsigned32 flags/handle at0/4, unsigned64 object offset/range/GPU address at8/16/24. | The original planner preserves the same widths; its native input structure is still explicitly not a wire structure. |
| Bind ioctl envelope | Identical24-byte declaration: unsigned32 VM ID/count/stride/padding at0/4/8/12; unsigned64 user pointer at16. VM_BIND remains ID4. | A future adapter must zero padding, validate count/pointer lifetime and use the supplied stride for extension. There is no separate extension-chain pointer in this envelope. |
| Existing bind flags | Unbind/read/write/repeated-page remain1/2/4/8 in both. Offset/range/address retain page-alignment requirements. | The existing strict four-flag planning subset is unchanged. |
| New sparse-tile flag | Mesa adds16, requiring the sparse-tiles feature bit19 and repeated-page mode; the inspected kernel header has neither declaration. Its documented behavior uses kernel-owned tile pools rather than repeating the supplied object's page. | Keep rejecting this unknown flag. Simply accepting16 would silently change backing/lifetime semantics the planner does not model. |

The original [31Q planner](../kernel/experiments/gpu31q/planner.h) need not change
its four-flag arithmetic merely to follow PR47. Useful reuse is the stable bind
declaration and high-bit preservation; remaining adapter work includes capability
discovery, VM-create negotiation, padding/stride handling and actual object
lifetimes. The kernel header also explicitly says its HAL300 enum value is never
reported by that kernel, consistent with the inspected device match table.
The source-derived comparison is retained in ignored
`build/research31r/ecosystem/abi-comparison.json`; no third-party header was
compiled or executed to produce it.

## Newer Gravity developer branches

These are public development branches, distinct from Gravity's published
repository tips. Their contents were independently retrieved as public source.

| Source | Pin checked | Finding |
|---|---|---|
| [`niklassheth/bootloader`, `sptm-cleanup`](https://github.com/niklassheth/bootloader/tree/98412d670862a6d1cd29c5e8f33439839ae3c7e6) | `98412d670862a6d1cd29c5e8f33439839ae3c7e6`, October 16 | Public SPTM-emulation and UAT-handoff sources are available. `src/smp.c` is byte-identical to the previously checked Gravity file. |
| [`niklassheth/mesa-wip`, `wip/apple9-latest`](https://github.com/niklassheth/mesa-wip/tree/50cfaf889f3e9d96e6e2bb88e8d40d9cff28eacb) | `50cfaf889f3e9d96e6e2bb88e8d40d9cff28eacb`, October 20 | Much newer M4 native Vulkan work than the retained Gravity Mesa foundation. |
| [`niklassheth/linux`, `gravity-m4`](https://github.com/niklassheth/linux/tree/dea38a96aa86679d5e24da16b799030fe07ad2f6) | `dea38a96aa86679d5e24da16b799030fe07ad2f6` | Public branch metadata verified; three selected raw driver files returned HTTP429, so their current contents were not verified in this pass. |
| [`niklassheth/linux`, `integration/m4-7.3`](https://github.com/niklassheth/linux/tree/e05e77d0aecf125728b0a8e0b368c5d48d78f158) | `e05e77d0aecf125728b0a8e0b368c5d48d78f158` | Additional public integration branch located; no build/runtime qualification here. |

The new Mesa [Vulkan record](https://github.com/niklassheth/mesa-wip/blob/50cfaf889f3e9d96e6e2bb88e8d40d9cff28eacb/src/asahi/vulkan/README.apple9.md)
explicitly targets T8132/M4 Mac mini/G16G B1, reports experimental native Vulkan
and sets conformance version zero. Its
[`agx_device.c` switch](https://github.com/niklassheth/mesa-wip/blob/50cfaf889f3e9d96e6e2bb88e8d40d9cff28eacb/src/asahi/lib/agx_device.c#L791-L815)
maps generation16/G to G16G and generation17/P to G17P; it does not admit G17C.
The newer implementation is worth learning from without calling it an M5 Max
driver or discarding the reproducible [31P build](native31p-gpu-build.md).

The public SPTM branch supplies particularly useful protocol explanations:

- [`hv_sptm_boot.c`, properties](https://github.com/niklassheth/bootloader/blob/98412d670862a6d1cd29c5e8f33439839ae3c7e6/src/hv_sptm_boot.c#L391-L403)
  distinguishes address-space-management mode, VA width, segment/mapping limits
  and a TLB-maintenance choice; [later initialization](https://github.com/niklassheth/bootloader/blob/98412d670862a6d1cd29c5e8f33439839ae3c7e6/src/hv_sptm_boot.c#L645-L654)
  connects the GPU contexts, shared L2 region and handoff base.
- [`hv_sptm_uat.c`](https://github.com/niklassheth/bootloader/blob/98412d670862a6d1cd29c5e8f33439839ae3c7e6/src/hv_sptm_uat.c)
  separates global/per-context slots, checks firmware acceptance, publishes
  handoff state with cache/barrier operations, and tracks resumable mapping
  cursors. These are concrete comparisons for the 31Q ownership questions.

This is a guest-research/emulation implementation, not independently validated
G17C-native startup instructions. Its assumptions must be compared with this
machine's retained metadata and independently qualified behavior. No firmware
replacement, guest launch, table installation or MMIO follows from reading it.

## CPU startup: no demonstrated new release correction

Fresh reads confirm [Asahi m1n1 PR610](https://github.com/AsahiLinux/m1n1/pull/610)
was merged July 10 but explicitly reported powered secondaries without code
entry on tested M5 Pro firmware. It does not promise functional SMP. Its M/P
core names follow ADT/MPIDR, not the newer marketing names; iLinux should keep
its observed topology rather than infer identity from names.

The fresh Gravity and developer-branch `src/smp.c` files both hash to
`7ba57060e8118841b17b1624c8b02a4a8535a977bc6f8275d0066ab75c7f22ce`, matching
31O's snapshot. [Gravity's FAQ](https://gravitylinux.org/about/) still describes
the M5 Pro/Max limitation as of macOS27.0 beta5. Its claim is scoped to that
report; it cannot establish every later firmware's behavior or prove there is
no software workaround.

The [T6050 DVFS proposal](https://github.com/aurora-silicon/linux/pull/249)
remains open at `a289553f195ed51f2e44dcb9dfaab307d70ec13b`, with hardware
frequency and firmware thermal ownership explicitly unqualified. It is later
performance work, not a first-secondary startup fix. Continue the current
offline handoff/preparation investigation unless a new source supplies a
discriminating operation or observation.

## What distinguishes iLinux

The defensible distinction is the **specific T6050/J716c M5 Max target and an
end-to-end Omarchy/performance research program**: its attended native desktop
work, original bounded probes and codecs, reproducible packages, independent
second-machine reviews, and measurements against macOS on the same hardware.
Evidence is in the [project overview](../README.md),
[benchmark methodology](../benchmarks/methodology.md),
[performance scorecard](../reports/performance-parity.md),
[native attempt records](../native/boot/README.md) and
[original GPU building blocks](../kernel/experiments/gpu31q/README.md).

Those are useful contributions without claiming greater overall hardware
capability than upstream. Arch/Hyprland, Omarchy on Apple Silicon, reproducible
builds and macOS comparisons all have related work elsewhere. Current iLinux
offline checks do not establish all-core execution, hardware acceleration,
responsiveness gains or energy parity. Its value should be expressed through
the exact machine, evidence and working components, with credit to the shared
Asahi/Mesa foundation.

## Reproducible source intake and next use

Small public snapshots are retained as data under ignored
`build/research31r/ecosystem/`. The pinned source manifest contains repository,
commit, path, URL, byte count and SHA-256 for each successful fetch, and explicit
404/429 records for failed fetches. No whole kernel archive was downloaded.
No fetched scripts, modules or compiler tools ran on the host.

Useful unchanged release pins: Gravity bootloader `f02d4a52017915febb222539636b5b025a70407a`,
Linux `4fc326f6c25ccceb7515e2635c22e01fde5d3bac`, Mesa
`87ac51d411f0e58a9433567ec2666f457be89e1d`, website
`cfc74e6b3fcdb2f794fbf725464f27b506ad8d21`. Asahi m1n1 was checked at
`7cde7d1a784d851ebfee5579fa363c38b14150c0`; Asahi docs at
`0d1f8917fa88745d62a4c05d802c4a7298c8616b`.

The next useful offline work is a narrow comparison of the new source's chip
admission, UAPI fields, GPU address-window separation and SPTM handoff ownership
against the existing original code and retained G17C findings. Any reused code
needs its license/provenance preserved and actual G17C inputs validated.
No boolean gate should be widened merely because a family name matches.
Native31R remains HOLD until a separately justified implementation and review.

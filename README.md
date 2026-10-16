# iLinux: native Linux on the Apple M5 Max MacBook Pro

**Work in progress.** This repository is the working notebook of one engineering
project: run **Omarchy** (Arch Linux + Hyprland) natively on a MacBook Pro with
the **Apple M5 Max** (SoC `t6050`, board `J716c`), and bring it to the **same
performance as native macOS on the same machine**, measured rather than
claimed. Nothing here is finished, packaged for other people, or safe to copy
onto a Mac without reading the notes first.

The project is unaffiliated with Apple, Asahi Linux and Omarchy. It builds on
Asahi Linux's work (m1n1 and the Asahi kernel tree, both pinned by commit) and
on Omarchy's configuration, and sends nothing upstream. It was developed with
AI coding agents (Claude) under the rules in [`AGENTS.md`](AGENTS.md); every
claim in the documents is labelled Confirmed, Likely, Hypothesis or Unknown and
tied to a measurement, a log or a primary source.

## Where it stands (2026-10-16)

**The first native Omarchy desktop came up on 2026-10-16** (attempt 19).
Linux booted from RAM into an Arch userspace, and Hyprland started on the
laptop's own display with software rendering: wallpaper, waybar and a
terminal, with the desktop ready 7.8 seconds after the kernel started and
still running more than eight minutes later. The full record is
[`native/boot/stage-b-2026-10-16-attempt19-result.md`](native/boot/stage-b-2026-10-16-attempt19-result.md).

That desktop is a proof of life, not a usable system:

| Works today | Not yet |
|---|---|
| Boot from RAM through m1n1 from a second Mac; nothing is written to the internal drive | Keyboard, trackpad, any input (the desktop is view-only) |
| One CPU core, 16 KiB pages, 126 GiB of the 128 GB of RAM visible | The other 17 cores, cpufreq, cpuidle, thermal management |
| The firmware framebuffer (`simpledrm`) with Mesa llvmpipe | The display controller, GPU acceleration (the G17 GPU has no Linux driver), external displays |
| Hyprland, waybar, foot, systemd, Omarchy's configuration | Internal NVMe storage, Wi-Fi, Bluetooth, audio, camera, Touch ID |
| The power-domain release ladder and the device tree for this SoC | A USB link into Linux (two attempts so far: macOS has no driver for the first gadget, and the second gadget's control endpoint stalled) |
| | Power and battery behaviour, suspend, any performance claim |

Asahi Linux's M5 feature table still lists this SoC's GPU, cpufreq, cpuidle,
display and USB support as to be announced (checked 2026-10-13), so the device
tree, the power-management sequence and the boot path here are our own,
derived from the sanitized Apple Device Tree of this machine, the Asahi
sources for earlier SoCs, and experiments on the hardware.

A separate **VM track** runs Omarchy in a GPU-accelerated virtual machine on
macOS (`virtualization/`): Hyprland through VirGL on Metal, Vulkan through
Venus and MoltenVK, hardware H.264 decode, and LLM inference on the Mac's GPU
over RPC. Those numbers (for example 99% of macOS single-thread CPU throughput
and 94–98% of native Vulkan compute inside the VM) are documented in
[`reports/vm-vs-macos-parity.md`](reports/vm-vs-macos-parity.md). They are VM
results and say nothing about native hardware support.

## The goal, precisely

The target is **parity with native macOS on this exact machine**: the same
benchmarks (CPU, memory, storage, GPU, LLM inference, video), the same power
source and settings, measured on macOS and on native Linux, with energy per
task, idle power and sustained thermal behaviour reported together. The
reference point is 100%. The scorecard is
[`reports/performance-parity.md`](reports/performance-parity.md); the method
and the rules for what counts as evidence are in [`roadmap.md`](roadmap.md)
under Phase 4. Today only the macOS baselines and the VM track have numbers.
Native Linux has none yet, because it runs on one core with no frequency
scaling and no GPU. Those restrictions exist to test liveness, not speed.

The path from here is in `roadmap.md`, Phase 3: a USB link into Linux for
logs and SSH, then input (the keyboard and trackpad speak Apple's MTP protocol
over DockChannel), then all cores with idle and frequency control, then
storage, wireless and the GPU. Each step needs evidence on the hardware before
the next one is attempted.

## How a native boot works

Two Macs are involved. The M5 boots a custom [m1n1](https://github.com/AsahiLinux/m1n1)
from a lab volume that leaves the macOS installation untouched (Full Security
stays on the original volume). A second Mac connects over USB and drives m1n1's
proxy: a reviewed launcher ([`native/boot/launch.py`](native/boot/launch.py))
verifies the package against the manifest pinned in Git, checks the device tree
and the target, uploads the kernel, the initramfs and the device tree into RAM,
and hands off once. Every attempt is started by a person, filmed, and written
up in `native/boot/` with what was confirmed, what is likely and what is not
established. There is no installer and no persistent change to the machine.

Start with these files:

| File | What |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Rules (the macOS host is read-only; what is never committed), layout, conventions |
| [`roadmap.md`](roadmap.md) | Phases; Phase 3 is the path to a native Omarchy boot, Phase 4 performance |
| [`progress.md`](progress.md) | Chronological log of what was done, measured and found |
| [`coordination.md`](coordination.md) | Current handoff between the M5 and the second Mac |
| [`native/boot/README.md`](native/boot/README.md) | The current native package and the attempt reports |
| [`tools/m1n1-client/stage-b-instructions.md`](tools/m1n1-client/stage-b-instructions.md) | The checklist the second Mac follows for one boot |
| [`hardware/hardware-inventory.md`](hardware/hardware-inventory.md) | What this machine is, with observed and measured facts |
| [`reports/compatibility-matrix.md`](reports/compatibility-matrix.md) | Every SoC block, the matching Linux driver, and its status |
| [`kernel/patches/t6050/`](kernel/patches/t6050/) and [`kernel/experiments/`](kernel/experiments/) | The kernel patches and the experiments behind each boot package |
| [`omarchy-arm64/`](omarchy-arm64/) | The Arch RAM root that becomes the desktop, and the Omarchy ARM64 work |
| [`reverse-engineering/findings/catalog.md`](reverse-engineering/findings/catalog.md) | Research findings, each with its evidence and confidence |

## Reproducibility and what is not in Git

Every native package in the Releases is built in a VM job under
`virtualization/jobs/` from the Asahi kernel tree at commit
`77cb8f24c2381a8abb7272d7bbdec548d6426a8a` (Linux 7.1.9) plus the patches in
`kernel/`, with the kernel configuration shipped in the package and the m1n1
revision pinned in `tools/m1n1-client/`. Each release lists its file digests,
and the launcher refuses a package that does not match the manifest in Git.

Not in this repository, by rule: the RAM-root image (it carries its own SSH
host key and travels between the two Macs privately), videos and raw target
output, serial numbers, UUIDs, chip IDs, nonces and MAC addresses (the device
tree extractor in `hardware/scripts/` strips them), VM images, model weights,
and anything decompiled from Apple's software. Reverse-engineering notes
record findings and their evidence, not Apple's code. Asahi Linux's
clean-room policy still applies to anything meant for upstream, which this
project does not send.

The macOS baseline can be reproduced on any Mac with Xcode:

```bash
benchmarks/macos/run_baseline.sh all
```

It builds the portable benchmarks, runs them under `caffeinate -i`, and writes
JSONL plus an environment snapshot to `benchmarks/results/`. It is
non-destructive apart from one temporary 8 GiB file that it deletes.

## Licensing

The patches here are derivative works and carry the licence of what they
modify: the Linux kernel patches (`kernel/patches/`, `kernel/experiments/`,
`omarchy-arm64/kernel/`) and the QEMU patches (`virtualization/qemu/patches/qemu/`)
are GPL-2.0; the virglrenderer and Mesa patches are MIT; code that follows m1n1
says so in its header and keeps m1n1's licence, which each native package
includes as `m1n1-LICENSE`. The original tools, benchmarks, scripts and
documents are under the MIT licence in [`LICENSE`](LICENSE); [`NOTICE`](NOTICE)
lists the per-directory licences.

This is a personal research project. There is no support, no release
schedule and no promise that anything here will work on another machine.

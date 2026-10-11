# Omarchy on ARM64: Compatibility Status

Snapshot 2026-10-11. Full analysis, with sources and file:line references:
[`../research/omarchy/omarchy-arm64-analysis.md`](../research/omarchy/omarchy-arm64-analysis.md).
Package table: [`../research/omarchy/package-arm64-matrix.csv`](../research/omarchy/package-arm64-matrix.csv).

## Headline

**Upstream Omarchy 4 already supports aarch64** on its edge channel:

* platform detection (`x86` / `aarch64` / `aarch64-apple`);
* per-platform package lists and pacman templates;
* an aarch64 package repo (`pkgs.omarchy.org/edge/aarch64`);
* an HTTPS Arch Linux ARM mirror;
* an Apple boot chain (m1n1 → U-Boot → Limine);
* aarch64 ISO branches.

This project is therefore a **thin downstream layer**, not a fork: VM
integration, a few upstreamable fixes, and macOS-parity extras such as
`omarchy-qos`.

## Verified in our VM (real pacman, not simulation)

VM job `virtualization/jobs/004-omarchy` ran Arch Linux ARM in `vzrun`
against upstream commit `9480d1b` (`quattro`). The input was the 161-name
`omarchy-pkg-defaults aarch64` set plus `linux-aarch64 limine snapper
btrfs-progs efibootmgr omarchy omarchy-settings vulkan-swrast`.

| Repos | Result |
|---|---|
| Omarchy edge aarch64 templates (`[omarchy]` + ALARM core/extra/alarm/aur via `arm-mirror.omarchy.org`) | **842 packages, 0 unresolved** (181 core, 619 extra, 42 omarchy) |
| Arch Linux ARM alone | **33 names unresolved**; the resolvable subset closes over 794 packages |

The 33 names that only Omarchy's repo provides: aether asdcontrol cliamp
disktree-bin dotnet-runtime herdr hype hyprland-preview-share-picker
localsend mise-bin monologue obsidian omacalc omacut omarchy
omarchy-hyprland-titlebars omarchy-nvim omarchy-settings omasnap omawrite
owe owe-lockfeed pinta qemu-user-static-binfmt signed tobi-try
ttf-ia-writer ttf-jetbrains-mono-nerd-basic ttfx tzupdate ufw-docker
yaru-icon-theme yay.

Resolution ran in a throwaway pacman DB with signature checks off, because
nothing was installed and the `[omarchy]` DB is signed with a key the ALARM
keyring lacks. **An actual install needs Omarchy's keyring.**

## Known blockers for a UEFI VM install (from the analysis; not yet patched here)

1. aarch64 is edge-only, and no aarch64 ISO has been released.
2. `bin/omarchy-update-restart:26` prompts for a reboot after every update on
   ALARM kernels (#10048).
3. No Vulkan driver for VMs, so `nvidia-utils` gets pulled in (#14427).
   The fix is a `vulkan-swrast` fallback.
4. Repo shadowing of hyprtoolkit/hyprland-guiutils (#14758).
5. The forced `btrfs-overlayfs`/`encrypt` mkinitcpio hooks, and the
   pacman.conf overwrite that drops extra repos (#15030).
6. The Install menu offers x86-only apps (#8645).
7. `fwupdx64.efi` is hardcoded.
8. Virtualization.framework guests get 2D graphics only (llvmpipe).

## Our components

| Component | Status |
|---|---|
| `configuration/qos-tiers` (**omarchy-qos**): macOS-style QoS tiers | **VM functional test 5/5 pass**: slice placement, efficient-CPU fence, default unrestricted, utility tier; cpuset delegation works. uclamp skipped because the stock ALARM kernel lacks `CONFIG_UCLAMP_TASK_GROUP`. A bug found by the test (inactive slices have no cgroup) is fixed. |
| Patch queue P1–P13 | Planned (see analysis §7.3). Each fix should go upstream. Omarchy's repo ships an `AGENTS.md`, so check its contribution policy for AI-assisted patches first. |
| `omarchy-arm64-vm` integration package | Planned: virtio initramfs modules, `vulkan-swrast`, guest agents, menu gating, overlay-repo hook |

## Native Apple Silicon

Not possible on this M5 Max. The upcoming Omarchy Mac Installer targets M1–M3
only. Native testing of the `aarch64-apple` path needs an M1/M2 (or M3,
llvmpipe) Mac.

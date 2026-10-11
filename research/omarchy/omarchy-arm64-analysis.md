# Omarchy on ARM64 (aarch64): architecture, package availability, x86 assumptions, and a porting plan

Research date: 2026-10-11. Scope: what it takes to run Omarchy on aarch64. The first target is Arch Linux ARM in a UEFI VM with virtio-gpu, on an Apple Silicon Mac host (the user's M5 Max). The later target is Asahi-style Apple Silicon hardware.

Method: static analysis of a shallow clone of the upstream repo (`research/omarchy/upstream-omarchy/`), read-only GitHub API reads of related Omarchy repos, and web research. The live pacman sync databases of Arch Linux ARM, Omarchy's package repo (x86_64 and aarch64), Asahi ALARM and Arch Linux x86_64 were downloaded as metadata and indexed. An offline dependency-closure simulation approximating `pacman -Sp` was run over those databases. No upstream script was executed.

Companion file: `package-arm64-matrix.csv`, with 372 package names and one row each.

---

## 0. Executive summary

1. **Which repo is canonical:** `github.com/omacom/omarchy`. `github.com/basecamp/omarchy` answers HTTP 301 to it, and the API redirects to repository id 994093166. The default branch is `quattro` (Omarchy 4), identical to `master`. I analyzed commit `9480d1b6a98156314dbabe6bfef08f39f8b9cd07` (2026-10-11). The latest release is v4.0.4, commit `c668141e9c42b13c80c9ca4ea108e11708c5e8a5` (2026-09-15).

2. **Omarchy 4 already ships most of the aarch64 plumbing. This is no longer a from-scratch port.**
   - **Platform model and detection:** `bin/omarchy-hw-platform` prints `x86`, `aarch64` or `aarch64-apple`.
   - **Per-platform package sets:** `install/omarchy-aarch64.packages`, `install/omarchy-aarch64-apple.packages` and `install/omarchy-x86_64-only.packages`, composed by `bin/omarchy-pkg-defaults`.
   - **Per-platform pacman templates:** `default/pacman/aarch64/` and `default/pacman/aarch64-apple/`.
   - **An Omarchy package repo for aarch64:** `pkgs.omarchy.org/edge/aarch64`, 179 packages, the newest built 2026-10-11.
   - **An HTTPS mirror of Arch Linux ARM:** `arm-mirror.omarchy.org`.
   - **A lifecycle-dispatch layer for the Apple boot chain** (m1n1 → U-Boot → Limine), implemented by `omarchy-mac-boot` and `omarchy-mac`.
   - **Unmerged ISO branches with CI:** `omarchy-iso` branches `arm64-generic`, `n1x` and `dragon` build aarch64 ISOs. CI installs them unattended in QEMU/KVM and checks the booted result.
   - **Upstream intent:** the upstream triage bot says "Omarchy is going to support ARM very soon". It also says "a fully supported Omarchy M Installer for Apple Silicon Macs is coming very soon".
   - **Still edge-only:** aarch64 is published on the edge channel only. Stable and rc have no aarch64 runtime, and the user manual still says M-series Macs are "not directly supported".

3. **Package availability, verified against the live sync DBs on 2026-10-11.**
   - **Across all 372 package names** (base, optional installers and hardware leaves):

     | Category | Count |
     | --- | --- |
     | In Arch Linux ARM by name | 232 |
     | In ALARM via a provider | 5 |
     | Only in Omarchy's aarch64 repo | 89 |
     | Only in the Asahi ALARM repo | 2 |
     | x86 or vendor-hardware only, not needed on ARM | 30 |
     | Needs a replacement (no aarch64 build anywhere checked) | 14 |

   - **The aarch64 default set** that `omarchy-pkg-defaults aarch64` composes has 161 names. ALARM supplies 128, 2 more come via provides (`nvim`→`neovim`, `vi`→`ex-vi-compat`), and 31 come only from Omarchy's aarch64 repo. With Omarchy's own repo order, the simulated full dependency closure (base set plus ISO boot set) has **872 packages and 0 unresolved**. Against ALARM alone, **37 targets are unresolved**, including `omarchy` and `omarchy-settings` themselves.

4. **Main blockers for a generic aarch64 UEFI VM.** Each has a file and line in Section 5 and an upstream issue where one exists.
   1. aarch64 exists only on the edge channel, and no released aarch64 ISO exists yet (the ISO work is branch-only).
   2. `bin/omarchy-update-restart:26` assumes `/usr/lib/modules/*/vmlinuz` is package-owned. On ALARM kernels this produces a reboot prompt on every update (#10048).
   3. `install/hardware/vulkan.sh` has no virtio or software Vulkan driver. Any later package that needs `vulkan-driver` (zed, Steam) gets `nvidia-utils` (#14427).
   4. Repo order lets older Omarchy-built `hyprtoolkit`/`hyprland-guiutils` shadow newer ALARM builds, causing downgrade and reinstall loops (#14758, #12303).
   5. `etc/mkinitcpio.conf.d/00-omarchy-hooks.conf:34` forces `encrypt` and `btrfs-overlayfs` on every non-Apple platform. Separately, the pacman template copy wipes any extra repositories (#15030).
   6. Install menu entries for packages with no aarch64 build are not gated: Bitwarden, Ollama, Hermes, Lutris/Wine, Battle.net and GeForce NOW (#8645, #11591, #14592).
   7. `bin/omarchy-update-firmware:13-14` hardcodes `fwupdx64.efi`.
   8. Graphics: Apple's Virtualization.framework gives Linux guests 2D virtio-gpu only, so you get llvmpipe. QEMU or UTM with `virtio-gpu-gl-pci` plus VirGL gives GL/GLES but needs Hyprland and app workarounds.

5. **Apple Silicon hardware is not an option for the user's M5 Max.**
   - Asahi supports M1/M2. M3 support was added to the installer on 2026-09-06, but with no GPU driver (llvmpipe only).
   - M4 and M5 are not installable.
   - The upcoming Omarchy Mac Installer enables M1, M2 and M3 only; it refuses M3 Ultra and M4 or later.
   - So on the M5 Max, Omarchy runs in a VM. Native Asahi testing needs a separate M1/M2 (or M3) machine.

6. **Recommended approach.**
   - **Do not fork.** Build an "omarchy-arm64" variant as a thin downstream layer on upstream's own `aarch64` platform (edge channel), made of four parts:
     - (a) a small, hash-pinned patch queue of about 10 upstreamable fixes, each also filed as an upstream PR;
     - (b) a downstream integration package (VM guest agents, a virtio initramfs drop-in, a Vulkan fallback, menu gating, a `pre-refresh-pacman.d` hook that re-adds an overlay repo) that never edits upstream files;
     - (c) a signed overlay repo for the handful of missing packages;
     - (d) images built with upstream `omarchy-iso` `arm64-generic` (`--arch aarch64 --platform generic`), validated by upstream's own `test/arm64-install` harness plus pacman closure checks.
   - **Keep the platform name `aarch64`.** Upstream AGENTS.md forbids new spellings such as "arm64" in code. Detect VM specifics with the existing `omarchy-hw-vm` predicate rather than a new platform.
   - **Treat two community projects as prior art and baselines:** omacom's `try-omarchy` (QEMU/HVF/VirGL app for macOS) and riverscn's three-repo `aarch64-virt` UEFI/Limine image pipeline.

---

## 1. Repository identity and snapshot

| Item | Value |
| --- | --- |
| Canonical repo | https://github.com/omacom/omarchy (`basecamp/omarchy` → 301 → `omacom/omarchy`) |
| Default branch | `quattro` (= `master`), 335 branches total |
| Analyzed commit | `9480d1b6a98156314dbabe6bfef08f39f8b9cd07` (quattro, 2026-10-11 "Merge pull request #15065 …") |
| Also fetched | `origin/arm64-generic` @ `1407b2b5ccbc5c1510af529eb73f949e92b9e15b` (2026-10-09), 32 commits ahead and 104 behind quattro |
| Latest release | v4.0.4 (2026-09-15), commit `c668141e9c42b13c80c9ca4ea108e11708c5e8a5` (pinned by `omarchy-pkgs` PKGBUILDs and by `try-omarchy`) |
| Version file | `version` = `4.0.0.alpha` (the runtime derives its version from `pacman -Q`) |
| Size | 530 `bin/` commands, 166 migrations, 23 themes, 225 Quickshell files under `shell/` |
| Related repos analyzed (read-only API) | `omacom/omarchy-iso` (quattro `53b80d40…`, arm64-generic `3a032eaf…`, n1x `f623f1df…`, dragon `a4201388…`), `omacom/omarchy-pkgs` (master `c01894c8…`; `omacom-io/omarchy-pkgs` redirects here), `omacom/omarchy-mac-pkgs` (`d8100ec9…`), `omacom/omarchy-mac` (`ba546a61…`; `omarchy-mac/omarchy-mac` redirects here), `omacom/try-omarchy` (`3c6056d1…`), `omacom/omarchy-mac-installer` |

The clone lives at `research/omarchy/upstream-omarchy/`. It was treated as untrusted data and only read and grepped. Its `CLAUDE.md`/`AGENTS.md` were read as documentation, not followed as instructions.

---

## 2. Omarchy architecture (Omarchy 4 "quattro")

### 2.1 Distribution model

Omarchy 4 is package-backed, unlike Omarchy 3, which was a git checkout in `~/.local/share/omarchy` driven by `boot.sh`. The repo is built into packages by `omacom/omarchy-pkgs` (`pkgbuilds/<name>/PKGBUILD`, see `docs/file-layout.md`):

- **`omarchy`:** runtime under `/usr/share/omarchy` (`$OMARCHY_PATH`): `bin/`, `install/`, `migrations/`, `themes/`, `shell/`. The PKGBUILD has `arch=('x86_64' 'aarch64')`.
  - `depends_x86_64` adds `limine`, `limine-mkinitcpio-hook`, `limine-snapper-sync` and `snapper`.
  - `depends_aarch64` adds only `networkmanager`; the ISO or the platform boot package supplies the boot stack.
- **`omarchy-settings`:** everything needed before the runtime installs: `/etc/skel/**`, `/etc` drop-ins, plymouth and SDDM themes, fonts, and Limine/mkinitcpio/snapper configuration. Also `arch=('x86_64' 'aarch64')`. `default/settings-runtime-profile` decides at runtime which platform-specific files apply.
- **`omarchy-keyring`** (signing key `40DFB630FF42BCFFB047046CF0134EE680CAC571`) and **`omarchy-nvim`**.
- **Dev variants:** `omarchy-dev` and `omarchy-settings-dev`.
- **Channels:** `stable`, `rc`, `edge` and `dev`, switched by `omarchy-channel-set`. The package repo is `https://pkgs.omarchy.org/<channel>/<arch>`.
  - x86_64 also pins Arch itself through Omarchy mirrors (`stable-mirror`, `rc-mirror` or `mirror.omarchy.org/$repo/os/$arch`).
  - aarch64 uses `https://arm-mirror.omarchy.org/$arch/$repo`, a mirror of Arch Linux ARM's `core`, `extra`, `alarm` and `aur` repos.
- **Updates:** `omarchy update` (`docs/update-process.md`) runs in this order:
  1. lock;
  2. free-space check;
  3. sudo once;
  4. `paccache` prune;
  5. snapper snapshot;
  6. `pacman -Syu` via `omarchy-update-pacman` (a `systemd-run --scope` wrapper);
  7. per-user migrations;
  8. orphan cleanup;
  9. restarts;
  10. hooks;
  11. mise;
  12. AUR via yay, with no reusable sudo timestamp;
  13. the platform's `update-verify` boot check;
  14. the reboot prompt.

  A pacman ALPM hook (`00-omarchy-update-guard.hook`) aborts raw `pacman -Syu` unless `OMARCHY_ALLOW_DIRECT_PACMAN=1` is set.

### 2.2 Install entrypoints and phases

**Omarchy 4 (current).** The ISO owns installation (`agents/skills/install-scripts.md`). In `omacom/omarchy-iso`, an archiso image boots a TUI configurator (`configs/airootfs/root/configurator`). That configurator calls a Python orchestrator (`configs/airootfs/usr/share/omarchy-iso/orchestrator/`), which drives archinstall and then runs these phases (`main.py: build_phases`):

1. Preparing live environment
2. Preparing install target
3. Installing Arch + Omarchy (archinstall, pacstrap of `install/omarchy-base.packages`, early Limine pieces)
4. Configuring hibernation
5. Configuring system: in the target chroot it runs `omarchy-apply-system`, which does:
   - `install/config/all.sh`;
   - `omarchy-apply-hardware`, which sources `install/hardware/all.sh` and ends with `install/hardware/platform-setup.sh`, which calls lifecycle dispatch `setup-boot` and `setup-system`;
   - `install/login/all.sh`;
   - `install/post-install/all.sh`, which writes the platform pacman templates, keyrings, udev and localdb.
6. Staging provisioning: deferred owner provisioning with a staged LUKS key under `/var/lib/omarchy/provisioning`.
7. Finalizing Limine boot (UKI)
8. Finalizing user: `omarchy-provision-user` / `omarchy-finalize-user`, which run `install/user/all.sh`, ending with `install/user/platform-setup.sh` → `setup-user`.
9. Configuring login, SSH access, Tailscale and the DNS resolver
10. Validating boot setup
11. Creating the factory snapshot (`@factory`), used by `omarchy-system-factory-reset`.

**First boot:**

- `omarchy-provision-owner.service` runs the owner wizard and re-keys LUKS from the staged key to the owner's password (`install/provisioning/luks-rekey.sh`, with a crash-safe journal).
- `omarchy-provision-hardware.service` runs only for prebuilt images: it drains the deferred hardware queue and handles the per-machine pacman keyring.
- `omarchy-provision-first-run` runs once the session is up.

**Unattended installs:** a `CIDATA` volume with `user_configuration.json` (manual chapter 51, and `bin/omarchy-cidata-load` on the ISO).

**Omarchy 3 (legacy, tag v3.8.4).** `boot.sh` set the Omarchy mirror, then `git clone basecamp/omarchy ~/.local/share/omarchy` and `source install.sh`. `install.sh` sourced `helpers`, `preflight`, `packaging`, `config`, `login` and `post-install`. `install/preflight/guard.sh:24-27` aborted on `uname -m != x86_64`. The guard also required Limine and a btrfs root (lines 39-43). That guard no longer exists in Omarchy 4.

### 2.3 Package sources and composition

- **`install/omarchy-base.packages`:** the 162-name core set pacstrapped by the ISO and read by the ISO's offline mirror builder.
- **`install/omarchy-other.packages`:** 58 names installed outside the base list: boot and kernel packages, hardware drivers, and T2/Dell/Intel/NVIDIA/Asahi Vulkan. It ensures they exist in the ISO's offline mirror.
- **Composition:** `bin/omarchy-pkg-defaults [platform]` = base + `omarchy-aarch64.packages` (aarch64 only: `zram-generator`) + `omarchy-<platform>.packages`. On ARM it then drops `omarchy-x86_64-only.packages` (`gliff`, `superwhisper-bin`).
- **Installing:** `omarchy-pkg-add` is pacman-only, with `--noconfirm --needed`; `omarchy-pkg-aur-add` uses yay. In Omarchy 4 essentially every default package comes from Arch or Omarchy's repo. The x86 dependency closure of the base set resolves with 0 AUR builds (Section 4.3).
- **Omarchy's own repo** carries:
  - first-party apps (aether, omacut, omawrite, omasnap, owe, hype, signed, monologue, ttfx, herdr, cliamp, …);
  - repackaged vendor binaries (1password, google-chrome, VS Code, Cursor, Spotify, Dropbox, Slack, Obsidian, …);
  - Limine tooling from the AUR (`limine-mkinitcpio-hook`, `limine-snapper-sync`);
  - kernels (`linux-omarchy*` on x86, `linux-aurora` on Mac);
  - yay and mise-bin.
- **Optional software:** about 60 installers (`bin/omarchy-install-*`) and the Install menu (`default/omarchy/omarchy-menu.jsonc`, lines 240-331): browsers, editors, AI apps, services, gaming, dev environments (mise-based: ruby, node, go, python, …), fonts and terminals.

### 2.4 Migrations

`migrations/<unix-ts>.sh` (166 files) run per user through `omarchy-migrate` after the pacman transaction. They are idempotent, and completion is recorded per user in `~/.local/state/omarchy/migrations/<name>`. A login-time notifier (`omarchy-migrate-notify.service`) catches users who bypassed `omarchy update`.

### 2.5 Configuration layout, themes, `bin/`

- **Locations:**
  - `/usr/share/omarchy/{bin,default,install,migrations,themes,shell,…}` is read-only and package-owned.
  - `/etc/skel/.config/**` is the seed, copied by `useradd -m`.
  - `~/.config/omarchy/` holds user `extensions/omarchy-menu.jsonc`, hooks and theme overrides.
  - `~/.local/state/omarchy/` holds the current theme, toggles, migration markers and update markers.
- **Hooks:** `~/.config/omarchy/hooks/{pre-refresh-pacman,post-update,post-boot,theme-set,font-set,battery-low}.d/`, run by `bin/omarchy-hook`. They are a key rebase-friendly extension point.
- **Themes:** `themes/<name>/colors.toml` (23 themes) feed `default/themed/*.tpl` templates. Aether does theme generation.
- **Commands:** `bin/omarchy-*` (530), routed by `bin/omarchy` with `GROUP_DESCRIPTIONS`. Hardware predicates are `omarchy-hw-*`; the architecture predicates are `omarchy-hw-x86` and `omarchy-hw-aarch64`.

### 2.6 Hyprland and desktop

- **Hyprland 0.56 with a Lua config:**
  - `default/hypr/*.lua` holds Omarchy defaults: `bootstrap.lua`, `envs.lua`, `nvidia.lua`, `toggles/`, …
  - `config/hypr/*.lua` holds the user layer: `hyprland.lua`, `monitors.lua`, `input.lua`, `bindings.lua`, `looknfeel.lua`, `autostart.lua`.
  - The session is managed by uwsm. `xdg-desktop-portal-hyprland` and `-gtk` are used.
- **Quickshell desktop (`shell/`):** bar, menu, notifications, lock screen and OSD. It replaced waybar, mako, walker and hyprlock in v3.
- **SDDM** with an Omarchy theme. Plymouth `omarchy` theme.
- **VMs:** `install/user/hardware/vm-no-animations.sh:6-10` turns off animations and transparency when `omarchy-hw-vm` (`systemd-detect-virt --vm`) is true.

### 2.7 Boot, snapshots, encryption

- **Limine (UEFI) with UKIs:**
  - `limine-mkinitcpio-hook` builds `EFI/Linux/omarchy_<kernel>.efi`; `etc/limine-entry-tool.d/omarchy-uki.conf` sets `ENABLE_UKI=yes`.
  - The template is `default/limine/limine.conf` (branding and Tokyo Night colors), with `default/limine/default.conf` `@@CMDLINE@@` substituted by the ISO.
  - `etc/limine-entry-tool.d/omarchy-defaults.conf` sets cmdline defaults: `quiet splash … initramfs_async=0 systemd.tty.term.console=dumb`, plus `BOOT_ORDER="linux-t2, linux-omarchy, linux-omarchy-*, *, *fallback, Snapshots"`.
  - The ISO installs `limine_x64.efi` (x86) or `limine_aa64.efi` (aarch64 branch).
- **Snapper:** root config template at `default/snapper/root` (NUMBER_LIMIT 5). The timeline timer is disabled, and cleanup plus `limine-snapper-sync` are enabled (`install/config/snapper.sh:23-24`).
- **Booting snapshots:** `limine-snapper-sync` adds snapshot boot entries. They boot read-only with the `btrfs-overlayfs` initcpio hook, which `limine-mkinitcpio-hook` ships.
- **Btrfs:** subvolumes `@`, `@home` and others, plus `@factory`.
- **mkinitcpio baseline:** `etc/mkinitcpio.conf.d/00-omarchy-hooks.conf`.
  - Non-Apple: `HOOKS=(base udev plymouth keyboard autodetect microcode modconf kms keymap consolefont block encrypt filesystems fsck btrfs-overlayfs)` (busybox).
  - Apple: a systemd initramfs, with `omarchy-mac-boot` adding its hooks.
  - `omarchy_hooks.conf` drops `kms` for NVIDIA-only systems and bundles `vconsole.conf` for Latin layouts.
- **LUKS2:** full-disk encryption is the default on the ISO. The disk, the login user and root share one password, and there is no recovery key (`docs/lifecycle-dispatch.md`, "Key slots").
- **Secure Boot:** not required.
  - `bin/omarchy-usb-authorization-boot` signs Limine and the UKI with `sbctl` only when Secure Boot is enabled. The Limine EFI file name is derived from `limine_efi_arch` (lines 397-407), so that path is arch-neutral.
  - `omarchy-iso/plans/consumer-secure-boot.md` covers future work.
- **TPM:** not used by default. LUKS unlock is password-based, and TPM2/FIDO2 tokens are only tolerated (`install/provisioning/luks-rekey.sh:27`).
- **Hibernation:** `bin/omarchy-hibernation-setup` creates a swapfile plus a resume drop-in. It is Limine-only and skipped on Apple Silicon (lines 17-20, 29-32).
- **Direct boot:** `bin/omarchy-setup-direct-boot` creates an efibootmgr entry for the UKI. It is refused on Apple Silicon (lines 9-12).

### 2.8 Hardware-specific logic

`install/hardware/all.sh` runs `run_logged` leaves, each gated by PCI/DMI predicates:

- ASUS ROG, Framework 16, Dell XPS (haptics, sidecar amps, PTL speaker firmware) and Surface;
- network and regdom, F-keys, Synaptics, Bluetooth;
- **NVIDIA** (`nvidia.sh`: open-dkms vs 580xx; early KMS modprobe and mkinitcpio);
- **Vulkan** (`vulkan.sh`: an Intel/AMD/"Apple" lspci map);
- **Intel**: video acceleration, lpmd, thermald, IPU7 camera, FRED, Wi-Fi 7 EHT, SOF;
- Elgato, ASUS PTL display and touchpad, Framework QMK;
- **Apple Intel Macs** (`apple/`): SPI keyboard, NVMe suspend, T2 (`linux-t2`, `arch-mact2` repo, `t2fanrd`, Apple BCM firmware) and the brcmfmac supplicant quirk;
- Lenovo Yoga, BCM43xx `wl` driver, Surface keyboard, YT6801 Ethernet, Tuxedo backlight, speaker tuning;
- `pacman.sh` (the T2 repo);
- last, `platform-setup.sh` (lifecycle dispatch).

Apple Silicon has no inline branches. Its runtime and boot specifics live in `omarchy-mac` and `omarchy-mac-boot` (`omacom/omarchy-mac-pkgs`), behind `bin/omarchy-lifecycle-dispatch`, which is registered in code at lines 89-118. The dispatch operations are:

- `provision-prepare`, `provision-commit`, `provision-verify`;
- `reset-prepare`, `reset-verify`, `reset-commit`, `reset-rollback`;
- `update-verify`, `update-takeover`;
- `luks-slots`;
- `setup-boot`, `setup-system`, `setup-user`;
- `post-install`, `pre-remove`.

Platform data files live under `/usr/share/omarchy-platform/` (`displays.conf`, `audio.json`, `key-names`, `keyrings`).

### 2.9 Platform abstraction, which is what makes ARM viable

- **Detection** (`bin/omarchy-hw-platform`):
  - A device-tree root `compatible` with the vendor prefix `apple,` gives `aarch64-apple`.
  - `qcom,` or any other aarch64 machine gives `aarch64`. This includes ACPI-only UEFI VMs that have no `/proc/device-tree`, which fall through to `uname -m` (lines 156-202).
  - Image builds read `/var/lib/omarchy/image/target`.
- **Naming rule** (AGENTS.md "Platforms"): only `x86`, `aarch64` and `aarch64-<family>`. Never `arm64`, `generic` or `apple-silicon` (the old names are accepted only from legacy image manifests).
- **Pacman templates** (`install/helpers/pacman.sh:8-31`): `default/pacman/` for x86 and `default/pacman/<platform>/` for ARM. The default channel is `stable` on x86 and `edge` on aarch64. `omarchy-refresh-pacman` and `omarchy-channel-set` refuse channels that have no templates for the platform.

### 2.10 The ISO repo (`omacom/omarchy-iso`)

- **The quattro branch is x86_64-only:**
  - `configs/profiledef.sh:11-12` sets `bootmodes=('bios.syslinux' 'uefi.grub')` and `arch="x86_64"`.
  - `builder/build-iso.sh:126-127` downloads the Node `linux-x64` tarball; `:137-151` set `linux-t2`, `packages.x86_64` and the T2 live kernel.
  - `builder/archinstall.packages` lists `amd-ucode` and `intel-ucode`.
  - `configs/airootfs/root/configurator:415-416` (T2 detection), `:810` and `:1153` (`"efi_binary": "limine_x64.efi"`), and `:842-844` and `:1235-1237` (x86 Arch mirrors).
  - `orchestrator/phases_impl.py:395,413-421,763,1678` (`limine_x64.efi`/`BOOTX64.EFI` defaults) and `:1208` (`node-v*-linux-x64.tar.gz`).
  - `configs/efiboot/loader/entries/01-archiso-x86_64-linux.conf`.
- **`plans/aarch64-support.md`** is the upstream plan for a generic UEFI aarch64 ISO, with ALARM as the base. It lists every file above.
- **Branch `arm64-generic`** (52 commits ahead of quattro) implements that plan:
  - `bin/omarchy-iso-make --arch aarch64 --platform generic`;
  - `configs/pacman-online-aarch64.conf` with `[platform]`, then `[omarchy]` edge/aarch64, then ALARM via `arm-mirror.omarchy.org`;
  - `builder/aarch64-package-filter.sh`, which swaps kernels to the platform kernel, maps `nvim`→`neovim` and `vi`→`ex-vi-compat`, and drops x86 and vendor packages;
  - grub/archiso aarch64 patches;
  - CI (`.github/workflows/arm64-iso.yml`) that builds on a native ARM runner, boots the ISO under KVM (`test/arm64-live-boot`), and installs it unattended (`test/arm64-install`, using `efi_binary=limine_aa64.efi` and `KERNEL=linux-aarch64`).
- **Branch `dragon`** covers Snapdragon X (`configs/aarch64/platforms.json`, `builder/check-arm-packages.sh`).
- **Branch `n1x`** covers the NVIDIA N1X laptops (ASUS ProArt P14, Dell XPS 16) with `linux-omarchy-n1x`; see `N1X.md`.

---

## 3. ARM ecosystem status (October 2026)

### 3.1 Arch Linux ARM (ALARM)

- **Builds are actively produced.** The latest builds in `core`/`extra`/`aur` are dated 2026-10-11 (this snapshot). 97% of the 13,008 package names shared with Arch x86_64 are at identical versions.
- **Desktop stack versions match x86_64:** Hyprland 0.56.2-4, Mesa 26.2.4, Qt 6.12.0, systemd 262, Firefox 157.0.1, Limine 12.9.3, plymouth and snapper.
- **Laggards:**
  - glibc 2.43 (x86 has 2.44) and gcc 16.1 (x86 16.2);
  - chromium 153.0.8010.36 (x86 .52);
  - `yt-dlp` 2025.12.08, about 8 months stale (x86 2026.08.19);
  - `sushi` 50.0 (x86 51.1).
- **2,331 Arch core/extra names do not exist in ALARM.** Relevant to Omarchy: `obsidian`, `ghostty`, `zed`, `bitwarden` (desktop), `ollama`, `wine`, `dotnet-runtime`, `libretro-ppsspp` and `qemu-user-static-binfmt`.
- **Governance and community health is a concern.** An April 2026 arch-general thread describes ALARM as neglected: forum registration broken, PRs unreviewed, past chromium breakage. A March 2026 forum post says the community archive/rollback services were abandoned. ALARM still has no official status within Arch.
- **Security note:** ALARM's default mirror is plain HTTP and its repository databases are unsigned; packages are signed with key `68B3537F39A313B3E574D06777193F152BDBE6A6`. Omarchy's templates therefore use its own HTTPS mirror. For a privacy- and security-minded build, keep `SigLevel = Required DatabaseOptional` and use an HTTPS mirror.
- **Keyring:** `archlinuxarm-keyring` is old (20240419-2). Upstream's arm64-generic commit `8d3123163` adds explicit trust repair for the ALARM build key.

### 3.2 Official "Arch Linux Ports" and the Valve/Collabora port

- **Arch Linux Ports** (https://ports.archlinux.page, RFC 32) is a namespace for unofficial ports. Its own page says "No port has been approved yet".
- **The AArch64 port** lists community repos (`arch-linux-repo.drzee.net` for ARMv8.2+, `arch.bens.haus`), bootstrap tarballs, and systemd-boot ISOs (Codeberg `ironrobin/archiso-aarch64`). Targets are laptops (X13s, XPS 13 9345, Vivobook S15), SBCs, and Hetzner/AWS.
- **Some Omarchy users already run on Ports.** Upstream issue #15030 is from a Surface Pro 11 on Arch Linux Ports. Omarchy's ALARM template overwrites those repos.
- **Collabora and Valve "Holo Core":** a pure aarch64 Arch port, the base of the Steam Frame OS. A preview was published 2026-07-17 (sources on gitlab.steamos.cloud, binaries at holo-packages.steamos.cloud), and they intend to work with upstream Arch on an official port.
- **Neither replaces ALARM today.** ALARM remains the practical base, as upstream Omarchy's choice confirms.

### 3.3 Asahi Linux and Asahi ALARM

- **Asahi Linux:**
  - M1/M2 are supported.
  - M3, M3 Pro and M3 Max were merged into the Asahi installer on 2026-09-06 (blog "M2: Episode 1 (or, Asahi Linux on M3)"). There is no M3 GPU driver yet (llvmpipe only), no sleep, no MacBook HDMI, and no M3 Ultra.
  - M4 and M5 are early bring-up only (NVMe enabled) and not installable.
- **Asahi ALARM** (https://asahi-alarm.org, github.com/asahi-alarm) is a hobby-maintained Arch Linux ARM distribution for Apple Silicon. It installs with `curl https://asahi-alarm.org/installer-bootstrap.sh | sh` and offers a Calamares desktop choice that includes Hyprland.
- **Its repo** (`https://github.com/asahi-alarm/asahi-alarm/releases/download/aarch64`, 36 packages) carries:
  - kernel and boot: `linux-asahi 7.1.13.asahi3`, `m1n1 1.6.1`, `uboot-asahi 2026.07.asahi2`, `grub 2.16-3`;
  - audio: `asahi-audio`, `speakersafetyd`, `alsa-ucm-conf-asahi`;
  - x86 emulation: `FEX-Emu 2604`, `muvm 0.6.0`, `steam` (x86 via muvm/FEX);
  - other: `widevine`, `asahi-bless`, and `mesa-dummy`, because Asahi's GPU drivers now ship in upstream Mesa: ALARM `extra` carries `vulkan-asahi 26.2.4`.
- **Omarchy's Apple stack** builds on that: `omarchy-mac` depends on `asahi-audio`, `speakersafetyd`, `vulkan-asahi` and `asahi-alarm-keyring`. `omarchy-mac-boot` depends on `limine`, `limine-mkinitcpio-hook>=1.39.0-2`, `asahi-scripts`, `m1n1`, `uboot-asahi` and others. Omarchy's own Mac kernel is `linux-aurora 7.1.12.aurora2`, with `m1n1-aurora` (forks at `omacom/linux-aurora` and `omacom/m1n1`).
- **The Omarchy Mac Installer** (`omacom/omarchy-mac-installer`, extracted from `maralcbr/omarchy-mx-mac`, not yet released) enables all M1, M2 and M3 Macs (34 boards). It refuses the M3 Ultra (`apple,j575d`) and M4 or later (`apple,j614s`), and M3 runs on llvmpipe.

### 3.4 Upstream Omarchy's stated position on ARM

- **The manual:** `manual/44-mac-support.md` says M-series is "not directly supported at this time". `manual/49-omarchy-on.md` points to Asahi Alarm plus the community `omarchy-mac` guide, and to Parallels, UTM and VMware VM guides.
- **The code and docs:** AGENTS.md says "Omarchy runs on x86 and aarch64 (ARM)". `docs/update-process.md` says aarch64 is edge-only until "a release supports aarch64".
- **Triage bot (Sept–Oct 2026, on #10048, #12303, #14592 and others):**
  - first, Apple Silicon and ALARM reports were "out of scope … only installs made from the official Omarchy ISO";
  - then, "a fully supported Omarchy M Installer for Apple Silicon Macs is coming very soon";
  - then, "Reopening: Omarchy is going to support ARM very soon … a generic aarch64 problem".

### 3.5 Community ARM efforts

| Project | What it is |
| --- | --- |
| `omacom/try-omarchy` (2.5k★) | macOS app: pinned ALARM image + Omarchy 4.0.4 (`c668141e`), QEMU 11.1.1 + HVF (in-hypervisor GICv3), virtio-gpu-gl + VirGL on macOS OpenGL, direct kernel boot (no UEFI or Limine). It ships a hashed backport set (`guest/patches/omarchy/*.patch`), a patched Hyprland, held packages, and nested KVM on M3+ with macOS 26. It is the most complete VM integration and the closest analogue to the user's machine. |
| `riverscn/omarchy-aarch64-image` + `omarchy-aarch64` + `omarchy-pkgs-aarch64` | Generic AArch64 UEFI disk image for QEMU `virt` and UTM: Btrfs `@ @home @log @pkg`, Limine (`BOOTAA64.EFI`) + UKI + snapper + Plymouth + `@factory`, signed stable aarch64 repo, a single-commit runtime adaptation per release line. Unencrypted by design. |
| `ggalancs/omarchy-arm-utm` | Script-built UTM VM. Documents the v3 guard and that quattro has no arch guard. |
| `omacom/omarchy-mac` (was `omarchy-mac/omarchy-mac`) | One-command Omarchy 4 on Asahi Alarm (M1/M2), with in-place LUKS. |
| Others | `alexisraitano-myffu/omarchy-arm`, `kim-raaschou/omarchy-aarch64`, `thatcherstudio/omarchy-arm64` (plan), `maralcbr/omarchy-aarch64-*` package recipes, `macarchy/macarchy-core`, `hollomancer/uconsole-omarchy-arm64`. |

---

## 4. Package availability on aarch64

### 4.1 Data sources (all fetched 2026-10-11)

- **ALARM aarch64** `core`/`extra`/`alarm`/`aur` from both `mirror.archlinuxarm.org` and `arm-mirror.omarchy.org`. The two copies hold the same packages apart from one `extra` entry (13,392 vs 13,391 names).
- **Omarchy** `pkgs.omarchy.org/{edge,stable}/aarch64` (179 and 59 packages), `{stable,edge,rc}/x86_64`, and the unchannelled `pkgs.omarchy.org/aarch64` (`omarchy-keyring` only).
- **Asahi ALARM** `asahi-alarm.db`.
- **Arch x86_64** `core`/`extra`/`multilib` from `geo.mirror.pkgbuild.com`.

ALARM DBs use the older two-file layout (`desc` plus `depends`); `%PROVIDES%` lives in `depends`. Parsing both matters: with only `desc`, `nvim` and `vi` falsely look unresolvable.

### 4.2 Counts

All 372 package names Omarchy may install are covered: base, other/ISO, package depends, optional installers, hardware leaves, and the aarch64/Apple lists. The categories are the `alarm_aarch64_available` column of the CSV.

| Category | Meaning | Count |
| --- | --- | --- |
| `yes` | In ALARM by exact name | 232 |
| `yes-provides` | Satisfied via a provider in ALARM (`nvim`→neovim, `vi`→ex-vi-compat, `linux`→linux-aarch64, `libappindicator-gtk3`→libappindicator, `nvidia-dkms`→nvidia-open-dkms) | 5 |
| `no-omarchy-repo` | Not in ALARM, but published by Omarchy for aarch64 (edge) | 89 |
| `no-asahi-repo` | Only in Asahi ALARM (`asahi-bless`, `widevine`); Apple path only | 2 |
| `no-not-needed` | x86 or vendor-hardware specific: microcode, T2, Intel, NVIDIA 580xx, lib32/multilib, Dell/Tuxedo/ASUS drivers, x86 kernels, debug packages | 30 |
| `no` | Needs a replacement: `bitwarden`, `hermes-desktop`, `heroic-games-launcher-bin`, `libretro-ppsspp`, `libretro-uae-git`, `microsoft-edge-stable-bin`, `minecraft-launcher`, `ollama`, `spotify`, `superwhisper-bin`, `umu-launcher`, `wine-staging`, `wine-mono`, `wine-gecko` | 14 |

Confidence: 359 rows are `high` (DB-verified), and 13 are `medium` (functional caveats, such as box64-emulated Dropbox, Electron GPU in VMs, or gpu-screen-recorder on Apple).

By default set:

| Set | Size | yes | yes-provides | Omarchy aarch64 repo | asahi-alarm | no |
| --- | --- | --- | --- | --- | --- | --- |
| `omarchy-base.packages` (x86 default) | 162 | 127 | 2 | 32 | 0 | 1 (`superwhisper-bin`) |
| aarch64 default (`omarchy-pkg-defaults aarch64`) | 161 | 128 | 2 | 31 | 0 | 0 |
| aarch64-apple default | 168 | 129 | 2 | 35 | 2 | 0 |
| `omarchy-other.packages` | 58 | 30 | 1 | 3 | 0 | 24 not-needed |

The 31 aarch64-default packages that exist only in Omarchy's aarch64 repo:

- **Omarchy first-party apps:** aether, asdcontrol, cliamp, herdr, hype, monologue, omacalc, omacut, omawrite, omasnap, owe, owe-lockfeed, signed, ttfx, tobi-try, omarchy-nvim, omarchy-hyprland-titlebars, hyprland-preview-share-picker.
- **Third-party apps and tools:** disktree-bin, dotnet-runtime (via dotnet-runtime-bin), localsend, mise-bin, obsidian, pinta, qemu-user-static-binfmt, ttf-ia-writer, ttf-jetbrains-mono-nerd-basic, tzupdate, ufw-docker, yaru-icon-theme, yay.

### 4.3 Dependency-closure simulation (offline `pacman -Sp` approximation)

`scripts/closure.py` (in the scratchpad) uses libalpm's satisfier order: the first repo with a literal name that satisfies the version, otherwise the first satisfying provider, with versioned and soname dependencies honored. Conflicts and replaces are not modelled.

| Scenario | Targets | Closure | Unresolved |
| --- | --- | --- | --- |
| x86_64 control, Omarchy **edge** + Arch | base + ISO set (181) | 900 | **0** |
| x86_64 control, Omarchy **stable** + Arch | same | 890 | 6 (`disktree-bin gliff hype monologue omarchy-hyprland-titlebars signed`: the quattro base list is ahead of the stable channel) |
| **aarch64 generic**: `[omarchy edge/aarch64]` first, then ALARM (upstream template order) | aarch64 default + ISO set (`linux-aarch64`, `-headers`, `linux-aarch64-pkgbase-shim`, Limine stack, snapper, …) (180) | 872 (46 from Omarchy) | **0** |
| aarch64, ALARM first, Omarchy last (community order seen in #14758) | same | 866 (39 from Omarchy) | **0**, with a self-consistent newer Hyprland stack from ALARM |
| aarch64 **ALARM only** (no Omarchy repo) | same | 815 | **37 targets**: the 31 above plus `omarchy`, `omarchy-settings`, `omarchy-keyring`, `limine-mkinitcpio-hook`, `limine-snapper-sync`, `linux-aarch64-pkgbase-shim` |
| **aarch64-apple**: `[omarchy]`, `[asahi-alarm]`, then ALARM | Apple default + Mac boot set (187) | 929 (53 Omarchy, 10 asahi-alarm) | **0** |

Notable repo-priority effects in the generic order: `hyprland 0.56.2-5`, `aquamarine 0.15.1-1.1`, `hyprtoolkit 0.5.4-5.1`, `hyprland-guiutils 0.2.2-3` and `quickshell 0.3.2-3` all come from Omarchy, shadowing ALARM's `0.56.2-4`/`0.15.1-1`/`0.6.0-1`/`0.2.2-4`/`0.3.2-1`. Mixing these ABI-coupled packages across repos is what produces #14758 and #12303.

### 4.4 Problem packages and strategies

| Package(s) | Status on aarch64 | Strategy |
| --- | --- | --- |
| `nvim`, `vi` | Via provides in ALARM | Use explicit `neovim` and `ex-vi-compat` in aarch64 lists and offline mirrors, as the upstream ISO filter does |
| `linux`, `linux-omarchy*` | x86 kernels | `linux-aarch64` + `-headers` + Omarchy `linux-aarch64-pkgbase-shim` (VM/UEFI); `linux-aurora` or `linux-asahi` (Mac) |
| `intel-ucode`, `amd-ucode` | n/a | Drop. The mkinitcpio `microcode` hook is a harmless no-op on ARM |
| `gliff` | Upstream lists it as x86-only, but Omarchy edge/aarch64 now publishes 0.3.1-1 | Remove from `install/omarchy-x86_64-only.packages` |
| `obsidian`, `ghostty`, `zed`, `dotnet-runtime` | Missing in ALARM | Omarchy aarch64 repo |
| `yt-dlp` | ALARM copy stale | uv/pipx, the upstream `yt-dlp_linux_aarch64` binary, or an overlay `any` package |
| `qemu-user-static-binfmt` | ALARM lacks it; Omarchy ships a Debian-derived build | Drop on aarch64, or replace with ALARM `qemu-user` + binfmt; it may clash with FEX binfmt on Asahi |
| `bitwarden` | No ALARM build | Vendor `bitwarden_<ver>_arm64.tar.gz` (desktop-v2026.9.1 has an arm64 tarball and snap) packaged in the overlay, or `bitwarden-cli` (ALARM) + browser extension |
| `ollama` | No ALARM build | Package `ollama-linux-arm64.tar.zst` (v0.40.3) as `ollama-bin`; CPU in VMs |
| `hermes-desktop`, `libretro-uae-git` | Omarchy builds x86_64 only, but both build from source | Add `aarch64` to `arch=()` in omarchy-pkgs (upstreamable) |
| `libretro-ppsspp` | ALARM lacks the core | Standalone `ppsspp` (ALARM) or build the core |
| `spotify` | No arm64 Linux client | Omarchy web app (`open.spotify.com` + widevine), `spotify-player` or `ncspot` (ALARM). The menu is already x86-gated |
| `microsoft-edge-stable-bin` | No arm64 Linux build (Arm install guide, Jul 2026) | Chromium, Google Chrome (arm64 .deb exists since 2026, packaged by Omarchy) or Brave. Already x86-gated |
| `minecraft-launcher` | x86 only | `prismlauncher` + `jre-openjdk` (ALARM). Already x86-gated |
| `heroic-games-launcher-bin` | No Linux arm64 (only macOS and Windows arm64 builds) | Hide (already x86-gated) |
| `steam` | Omarchy aarch64 package = Valve's **native linuxarm64 client** | Use it. x86 games via FEX/Proton; on Apple, `omarchy-steam-fex` (muvm+FEX). No `lib32-*` on aarch64. Provide a `vulkan-driver` first |
| `wine-*`, `umu-launcher`, Lutris/Battle.net/GeForce NOW installers | No aarch64 Wine; the GFN installer runs an x86 `.bin` | Gate these installers to x86 until a FEX/muvm path exists (#14592) |
| `dropbox` | Omarchy aarch64 package runs the **x86_64 client under box64** | Works, but emulated. `rclone` or `nextcloud-client` (ALARM) are native |
| `superwhisper-bin` | x86 only | `voxtype-bin` (Omarchy aarch64, CPU-only; `bin/omarchy-install-dictation-voxtype:22`) |
| `gpu-screen-recorder` | ALARM 6.1.3 | Fails on Apple (separate display and GPU DRM devices): use `wf-recorder`. Verify in VMs |
| `1password`, Electron apps | Omarchy aarch64 (official arm64) | In VMs Electron may need `--disable-gpu` (try-omarchy wraps 1Password). See #9576 |

---

## 5. x86_64-specific assumptions in the code (file:line in the cloned repo)

Status meanings:

- **OK:** already arch-aware.
- **Bug:** affects aarch64 now.
- **VM:** affects the UEFI/virtio target.
- **Apple:** affects Asahi hardware.

### 5.1 Runtime repo (`omacom/omarchy` @ `9480d1b`)

| # | Location | Assumption | Effect on aarch64 | Status / fix |
| --- | --- | --- | --- | --- |
| A1 | `bin/omarchy-update-restart:23-38` (glob at :26) | The kernel image is `/usr/lib/modules/<ver>/vmlinuz` and owned by a package | ALARM `linux-aarch64` installs `/boot/Image`. Omarchy's `linux-aarch64-pkgbase-shim` writes an **unowned** `vmlinuz`, so `pacman -Qo` fails and "Linux kernel has been updated. Reboot?" appears on every update | **Bug** (#10048 open, #12440). Fix: also accept the package-owned `modules.builtin` or `pkgbase` in the running kernel's directory, and report "unknown" rather than "changed" (try-omarchy `update-restart-arm-kernel.patch`) |
| A2 | `bin/omarchy-update-firmware:13-14` | `fwupdx64.efi` → `/boot/EFI/arch/fwupdx64.efi` | On aarch64 the binary is `fwupdaa64.efi`, so the step is silently skipped. Apple Silicon has no UEFI capsule path | **Bug**. Pick the binary via `uname -m`; skip on `aarch64-apple` |
| A3 | `etc/mkinitcpio.conf.d/00-omarchy-hooks.conf:28-36` (generic HOOKS at :34) | Every non-Apple machine boots a busybox initramfs with `encrypt` and `btrfs-overlayfs` | Fails where `btrfs-overlayfs` is absent. That hook is shipped by `limine-mkinitcpio-hook` (`usr/lib/initcpio/{hooks,install}/btrfs-overlayfs`, verified in the Omarchy aarch64 files DB), so it fails on any machine without that package, e.g. UKI without Limine on Arch Linux Ports (#15030). Has no virtio modules for early KMS or Plymouth in VMs | **Bug/VM**. Add `btrfs-overlayfs` only if `/usr/lib/initcpio/install/btrfs-overlayfs` exists; add a VM drop-in `MODULES+=(virtio_gpu virtio_blk virtio_pci)` |
| A4 | `install/hardware/vulkan.sh:4-20` | GPU = Intel/AMD/"Apple" by **lspci** vendor | A virtio GPU gets no driver, so pacman `--noconfirm` later picks **`nvidia-utils`** as the `vulkan-driver` provider (zed, Steam) (#14427). The Apple GPU is not on PCI (omarchy-mac pulls `vulkan-asahi` instead); "Apple" also falsely matches T2 (#13727) | **Bug/VM**. Map virtio → `vulkan-virtio` (if the host exposes Venus) with fallback `vulkan-swrast`; never leave `vulkan-driver` unsatisfied |
| A5 | `install/hardware/nvidia.sh:3,5`; `bin/omarchy-install-gaming-gpu-lib32:14-28`; `bin/omarchy-install-gaming-steam:16` | `lib32-*` multilib packages exist | No multilib on aarch64 | **Bug**. Fixed on `arm64-generic` (commit `796a1869c`); cherry-pick |
| A6 | `default/omarchy/omarchy-menu.jsonc` | Only some entries are gated with `when: omarchy-hw-x86` (:199 Superwhisper, :260 Windows, :264 Edge, :270 Dropbox, :271 Spotify, :302 Minecraft, :308 Heroic) | **Not gated:** :277 Bitwarden, :294 Hermes, :296 Ollama, :303 GeForce NOW, :306 Battle.net, :307 Lutris, all of which fail with "target not found" or crash. **Over-gated:** :270 Dropbox (a box64 aarch64 package exists) | **Bug** (#8645, #11591, #9356). Better: a generic `omarchy-pkg-available <pkg>` guard (`pacman -Si`) |
| A7 | `install/omarchy-x86_64-only.packages:3`; `migrations/1791542175.sh:3-4` | `gliff` has no aarch64 build | It now does (Omarchy edge/aarch64 `gliff 0.3.1-1`) | Stale. Remove |
| A8 | `install/post-install/pacman.sh:20-25`; `bin/omarchy-refresh-pacman:45-49` | `/etc/pacman.conf` and the mirrorlist are copied whole from platform templates | Removes any non-template repo (overlay, Arch Linux Ports, device kernel repos) (#15030) | By design. Downstream uses the `pre-refresh-pacman.d` hook (`bin/omarchy-refresh-pacman:57-58`). Upstream could add an `Include = /etc/pacman.d/omarchy-extra.conf` |
| A9 | `default/pacman/aarch64/pacman-edge.conf:21-24` | `[omarchy]` precedes ALARM | Older Omarchy rebuilds of ABI-coupled Hyprland libraries shadow newer ALARM ones, so updates loop (#14758, #12303) | **Risk**. Keep the whole Hyprland stack from one repo, or have Omarchy publish matching builds promptly |
| A10 | `default/pacman/aarch64/*` | Only `pacman-edge.conf` and `mirrorlist-edge` exist | aarch64 can only follow edge; `stable`/`rc` refused (`install/helpers/pacman.sh:19-31`) | By design until a release supports aarch64 |
| A11 | `etc/limine-entry-tool.d/omarchy-defaults.conf:28` | `BOOT_ORDER` names x86 kernels | `linux-aarch64` matches `*`; harmless | OK |
| A12 | `bin/omarchy-refresh-limine:6-8`; `bin/omarchy-upgrade-to-quattro:515-519,680` | UKI names `omarchy_linux.efi` / `<machine-id>_linux.efi` | Cosmetic on aarch64 (the UKI follows the kernel pkgbase) | OK |
| A13 | `bin/omarchy-usb-authorization-boot:397-407` | Limine EFI file name | Derived from `limine_efi_arch`, so arch-neutral | OK. Secure Boot is n/a on Apple Silicon |
| A14 | `bin/omarchy-hw-x86:5`, `bin/omarchy-hw-aarch64:5` | `uname -m` | Intended architecture predicates | OK |
| A15 | `bin/omarchy-hw-platform:43-45,156-202` | Device-tree vendor (`apple,`/`qcom,`), else `uname -m` | ACPI VMs (no DT) → `aarch64`; QEMU `virt` with DT (`linux,dummy-virt`) → `aarch64` | OK |
| A16 | `install/user/mise-work.sh:16-18` | Node platform | Handles `aarch64` → `linux-arm64` | OK (was an ISO blocker until omarchy#14637) |
| A17 | `bin/omarchy-windows-vm:7-10`; menu :260 | x86 Windows guest under KVM | Refused on ARM | OK |
| A18 | `migrations/1789325478.sh:3-5` | `linux-omarchy` migration | Gated to x86_64 | OK |
| A19 | `bin/omarchy-upgrade-to-quattro:810-813, 842-853` | 3.x→4 upgrader: x86-only list handling, lspci-based Vulkan | Upgrade path only; v3 never supported aarch64 | Low |
| A20 | `install/hardware/fix-bcm43xx.sh:5-10` | `broadcom-wl-dkms` (x86 proprietary) | Gated on BCM4360/4331 PCI IDs; Apple Silicon (BCM4378/4387, brcmfmac) is not matched | OK |
| A21 | `install/hardware/apple/fix-brcmfmac-supplicant.sh:25-27` | Disable FW supplicant on Mac Broadcom | Explicitly skipped on `aarch64-apple` | OK |
| A22 | `install/hardware/pacman.sh:3-11`; `apple/fix-t2.sh:3` | T2 repo and kernel | Gated on the T2 PCI ID `106b:180[12]` | OK |
| A23 | `bin/omarchy-install-gaming-geforce-now:14-16` | Runs NVIDIA's x86 `GeForceNOWSetup.bin` directly | Runs under FEX binfmt and aborts on 16K pages (#14592) | **Bug**. Gate to x86 |
| A24 | `bin/omarchy-install-dictation-voxtype:12,22` | Vulkan backend | Handles aarch64 (no Vulkan backend) | OK |
| A25 | `bin/omarchy-hibernation-setup:17-20,29-32`; `bin/omarchy-setup-direct-boot:9-12` | Limine and efibootmgr | Apple excluded; fine on UEFI VMs | OK |
| A26 | `bin/omarchy-update-keyring:25-30` | Arch and ALARM keyrings | Refreshes `archlinuxarm-keyring` on aarch64. `arm64-generic` adds trust repair for key `68B3…E6A6` | OK (better on branch) |
| A27 | `install/config/enable-services.sh:5,13` | `linux-modules-cleanup` (kernel-modules-hook), `power-profiles-daemon` | Both exist on ALARM; ppd has little effect on Apple and VMs | OK |
| A28 | `install/omarchy-base.packages:96,152` (`nvim`, `vi`), `:28` (`dotnet-runtime`), `:122` (`qemu-user-static-binfmt`) | Names resolve as on x86 | Via provides (neovim, ex-vi-compat), Omarchy repo (dotnet-runtime-bin), Omarchy-only build (qemu) | OK with the Omarchy repo; use explicit names for offline mirrors |
| A29 | `bin/omarchy-lifecycle-dispatch:89-118` | Registration: only `aarch64-apple` has a platform package | Generic aarch64 = generic Limine/UKI path, like x86 | OK. A VM needs no dispatch entry |

### 5.2 ISO repo (`omacom/omarchy-iso` @ quattro `53b80d40`)

All of these are listed in `plans/aarch64-support.md` and solved on branch `arm64-generic`:

- `configs/profiledef.sh:11-12` (BIOS syslinux, `arch="x86_64"`, x86 BCJ filter);
- `builder/build-iso.sh:126-127` (Node `linux-x64`), `:137-151` (`linux-t2`, `packages.x86_64`);
- `builder/archinstall.packages` (`amd-ucode`, `intel-ucode`);
- `configs/airootfs/root/configurator:415-416`, `:810`, `:842-844`, `:1153`, `:1235-1237`;
- `orchestrator/phases_impl.py:395,413-421,763,1208,1678`;
- `configs/efiboot/loader/entries/01-archiso-x86_64-linux.conf`;
- `configs/grub/grub.cfg` (x86 shell and memtest fragments);
- `bin/omarchy-iso-boot`, `bin/omarchy-vm` (OVMF x64 paths);
- `bin/omarchy-iso-release:52`;
- `.github/workflows/nightly-build.yml` (x86 runner only).

### 5.3 Platform-level assumptions that are not code lines

- **Boot firmware.**
  - x86 ISOs assume UEFI or BIOS. aarch64 VMs use edk2 UEFI (`AAVMF`/`edk2-aarch64`) with ACPI (UTM, Virtualization.framework) or DT (QEMU `acpi=off`, as upstream CI does).
  - Apple Silicon boots m1n1 (stage 1 in iBoot, stage 2 on the ESP) → U-Boot (UEFI) → GRUB on stock Asahi ALARM, or → Limine with `omarchy-mac-boot`. There is no UEFI Secure Boot or TPM, and the install key lives on an ext4 boot partition (`docs/lifecycle-dispatch.md`).
- **Kernel layout.** ALARM kernels don't put `vmlinuz` under `/usr/lib/modules`, hence the shim and bug A1. Apple kernels use **16K pages**, which affects FEX, box64, some JITs and Chromium/Electron allocators (#14592).
- **Microcode, multilib, NVIDIA 580xx, Intel media/IPU/lpmd/thermald, T2, Broadcom `wl`:** none apply on ARM. All are gated or filtered (Section 4.2).
- **Wi-Fi firmware.** Generic ARM laptops need `linux-firmware` splits. Apple needs firmware extracted from macOS by `asahi-fwextract` (asahi-alarm). VMs need none.
- **TPM.** Unused by default. Available in VMs via `swtpm` if desired.

---

## 6. Hyprland on ARM64, Asahi and VMs

- **Packages:**
  - Hyprland 0.56.2 is built for aarch64 by ALARM (0.56.2-4) and by Omarchy (0.56.2-5, plus `hyprpm` and `omarchy-hyprland-titlebars`).
  - The whole stack (aquamarine, hyprutils, hyprlang, hyprgraphics, hyprtoolkit, hyprland-guiutils, xdg-desktop-portal-hyprland, hyprpicker, hyprsunset, uwsm, quickshell) is in ALARM at x86 versions.
  - **The ABI-coupling risk:** Hyprland and hyprtoolkit require aquamarine ABI 14, and GUI utils require hyprtoolkit ABI 6 (try-omarchy notes). Shadowing across repos breaks updates (#14758).
- **Asahi, M1/M2:**
  - The GPU driver is upstream Mesa (Gallium asahi + Honeykrisp Vulkan, `vulkan-asahi` 26.2.4 in ALARM). Hyprland runs, and Asahi ALARM offers it as a desktop choice; omarchy-mac ships Omarchy 4 on it.
  - **Separate display and render devices:** the DCP display controller and the AGX GPU are separate DRM devices. Tools that assume one device fail (`gpu-screen-recorder`, hence `wf-recorder` in the Apple list).
  - **Workarounds and quirks:** community configs (e.g. dusky-asahi) set `WLR_NO_HARDWARE_CURSORS=1`. The notch is handled by Omarchy's bar. 16K pages affect FEX-based Steam/GFN (muvm is used).
  - **Video decode:** hardware decode via `avd-fw` + `libva-v4l2_request-avd`.
- **Asahi, M3:** no GPU driver. Hyprland runs on llvmpipe, which is slow and costs battery. **M4/M5:** not available.
- **VMs:**
  - **Apple Virtualization.framework** (UTM "Apple" backend, Tart, …) gives Linux guests virtio-gpu 2D only, so Mesa falls back to llvmpipe through `kms_swrast`. Hyprland works but is CPU-bound. Omarchy turns off animations and transparency in VMs automatically. This is unverified for macOS 26, so medium confidence.
  - **QEMU/HVF** (UTM QEMU backend, try-omarchy) with `virtio-gpu-gl-pci` and VirGL on the host: the guest gets GL ≤4.3 / GLES 3.x, and Hyprland and browsers are accelerated.
    - Known issues: rounded-border coverage artifacts (try-omarchy rebuilds Hyprland with `rounded-border-coverage.patch`); the host cursor is composited by Cocoa (`cursor:invisible` in-guest); EDID-driven resize; CPU-only video decode; Electron EGL failures (`--disable-gpu`).
  - **Vulkan:** Venus (`vulkan-virtio`) needs host Venus support, which is generally not available on macOS QEMU. Use `vulkan-swrast` (lavapipe) as the `vulkan-driver` provider.
  - **CPU cost:** QEMU 11.1 with the in-hypervisor GICv3 cut idle CPU from about 65% to about 15% of a core.
  - **Nested virtualization:** available on M3+ with macOS 26, so the user's M5 Max can run upstream's KVM-based `arm64-install` tests inside a Linux VM.

---

## 7. Porting plan: "omarchy-arm64" as a thin downstream of upstream `aarch64`

### 7.1 Principles

1. **Consume upstream's aarch64 support.** Platform `aarch64`, the edge channel, and the `omarchy-iso` `arm64-generic` builder. Do not fork the runtime.
2. **Every code change is a small patch** with an upstream PR or issue link. The patch queue is applied by script with strict SHA-256 pins, like try-omarchy's `apply-omarchy-backports.py`.
3. **Prefer extension points over patches:**
   - `~/.config/omarchy/hooks/*.d` (shipped via `/etc/skel`);
   - menu extensions (`~/.config/omarchy/extensions/omarchy-menu.jsonc`, id override with `when`);
   - `/etc` drop-ins (`mkinitcpio.conf.d`, `environment.d`, `systemd`);
   - `/usr/share/omarchy-platform/` files (only if you own the platform package; for VMs prefer not);
   - the `omarchy-hw-vm` predicate.
4. **Respect upstream naming:** platform `aarch64`, not `arm64`. "omarchy-arm64" is only the project name.
5. **Overlay repo:** signed, `aarch64` only, holding only what neither ALARM nor Omarchy publishes.

### 7.2 Components

```text
omarchy-arm64/
├── patches/omarchy/NNNN-*.patch     # minimal runtime patches, SHA-pinned, each with upstream PR link
├── patches/omarchy-iso/…            # only if arm64-generic hasn't merged what you need
├── pkgbuilds/
│   ├── omarchy-arm64-vm/            # integration package (no upstream files touched)
│   ├── bitwarden-bin/  ollama-bin/  yt-dlp-latest/   # gap fillers (or upstream to omarchy-pkgs)
│   └── (rebuilds) hermes-desktop/ libretro-uae-git/  # = upstream PKGBUILD + arch=('x86_64' 'aarch64')
├── image/                           # omarchy-iso arm64-generic invocation + UTM/QEMU profiles
└── test/                            # closure checks, VM boot/install harness, graphics matrix
```

**`omarchy-arm64-vm` package contents:**

- `/etc/mkinitcpio.conf.d/90-omarchy-arm64-vm.conf`: `MODULES+=(virtio_pci virtio_blk virtio_gpu virtio_net virtio_input)`, plus a conditional that drops `btrfs-overlayfs` if its hook is missing (A3).
- `/usr/lib/systemd/system-preset/80-omarchy-arm64-vm.preset`: enable `qemu-guest-agent` and `spice-vdagentd`.
- **Dependencies:** `vulkan-swrast` (lavapipe; satisfies `vulkan-driver` so `nvidia-utils` is never chosen, A4), `qemu-guest-agent`, `spice-vdagent`.
- `/etc/skel/.config/omarchy/hooks/pre-refresh-pacman.d/10-omarchy-arm64-overlay`: re-appends the `[omarchy-arm64]` overlay repo after Omarchy rewrites `pacman.conf` (A8).
- `/etc/skel/.config/omarchy/extensions/omarchy-menu.jsonc`: overrides `when` for `install.service.bitwarden` (until the overlay ships it), `install.ai.hermes`, `install.ai.ollama`, `install.gaming.geforce-now`, `install.gaming.battlenet`, `install.gaming.lutris` → `omarchy-hw-x86` (A6).
- `/usr/lib/environment.d/90-omarchy-arm64-vm.conf`: Wayland hints for Electron/Chromium in VMs (as try-omarchy does). Optionally an Electron `--disable-gpu` wrapper for apps known to fail.

### 7.3 Minimal patch list, by file

Each patch should be filed upstream. The "upstream status" column says where it stands.

| Patch | File(s) | Change | Upstream status |
| --- | --- | --- | --- |
| P1 | `bin/omarchy-update-restart` (:23-38) | Recognize the running kernel via a package-owned `modules.builtin`/`pkgbase` in `/usr/lib/modules/$(uname -r)`, or via `pacman -Qqo /usr/lib/modules/$(uname -r)`. Treat "no recognized marker" as unknown, not changed | #10048 open. Model: try-omarchy `update-restart-arm-kernel.patch` |
| P2 | `bin/omarchy-update-firmware` (:13-14) | `case $(uname -m) in x86_64) efi=fwupdx64.efi;; aarch64) efi=fwupdaa64.efi;; esac`; skip on `omarchy-hw-aarch64-apple` | New |
| P3 | `install/hardware/vulkan.sh` (:4-20) | Add `virtio` → `vulkan-virtio` when the host exposes Venus, otherwise `vulkan-swrast`. Add `vulkan-swrast` when no vendor matched and `omarchy-hw-vm`. Use `lspci -nn` vendor IDs (`1af4:1050` virtio-gpu) instead of the "Apple" string | #14427, #13727 |
| P4 | `install/hardware/nvidia.sh` (:3,5), `bin/omarchy-install-gaming-gpu-lib32` (:14-28), `bin/omarchy-install-gaming-steam` (:16) | No `lib32-*` on aarch64; ensure a `vulkan-driver` exists before `steam` | On `arm64-generic` (`796a1869c`); cherry-pick |
| P5 | `default/omarchy/omarchy-menu.jsonc` (:277, :294, :296, :303, :306, :307; reconsider :270) | `when: "omarchy-hw-x86"`, or better a new `omarchy-pkg-available <pkg>` (pacman `-Si`) guard so entries appear when an aarch64 build is published | #8645, #11591 |
| P6 | `install/omarchy-x86_64-only.packages` (:3), `migrations/1791542175.sh` | Remove `gliff` (aarch64 build exists) | New |
| P7 | `etc/mkinitcpio.conf.d/00-omarchy-hooks.conf` (:33-35) | Append `btrfs-overlayfs` only if `/usr/lib/initcpio/install/btrfs-overlayfs` exists. Keep `encrypt` only for encrypted roots (or keep it and rely on the busybox no-op) | #15030 |
| P8 | `bin/omarchy-install-gaming-geforce-now` (:14-16) | Refuse on aarch64 with a clear message | #14592 |
| P9 | `install/hardware/all.sh` + new `install/hardware/vm.sh` | Optional upstreamable alternative to the integration package: when `omarchy-hw-vm`, enable guest agents and install `vulkan-swrast` (riverscn `install/hardware/virtual-machine.sh` is a model) | New |
| P10 | `default/pacman/aarch64/pacman-edge.conf` | Downstream only: add `[omarchy-arm64]` (SigLevel Required) after `[omarchy]`. Optionally move `[omarchy]` below ALARM to avoid shadowing, accepting that Omarchy-only patched builds then lose priority (both orders resolve fully; Section 4.3) | Downstream (A9 discussion upstream) |
| P11 | `omarchy-pkgs/pkgbuilds/{hermes-desktop,libretro-uae-git}/PKGBUILD` | `arch=('x86_64' 'aarch64')` | Upstream PRs |
| P12 | `omarchy-pkgs`: new `bitwarden` (arm64 tarball), `ollama-bin` (arm64), current `yt-dlp` | Fill the `no` gaps (Section 4.4) | Upstream PRs or overlay |
| P13 | `omarchy-iso`: use `arm64-generic` as is | `bin/omarchy-iso-make --arch aarch64 --platform generic --local-source <patched-omarchy> <omarchy-pkgs>`. Ensure `linux-aarch64-pkgbase-shim` and the virtio modules are in the target | Branch upstream |

The aarch64 ISO filter already handles the `nvim`, `vi`, kernel, microcode and T2 name issues. The packaged runtime builds from a local tree via `OMARCHY_SRC=/path/to/patched/checkout` (supported by the `omarchy` and `omarchy-settings` PKGBUILDs).

### 7.4 Keeping it rebasable

- **Track the upstream release line:**
  - Pin `_commit` to a release tag commit (now `c668141e`, v4.0.4) for "stable-arm64".
  - Track `quattro` HEAD nightly for "edge-arm64".
  - Upstream itself publishes aarch64 runtime packages only on edge, so match its `omarchy`/`omarchy-settings` versions.
- **Nightly CI rebase:**
  1. Fetch upstream.
  2. Apply `patches/omarchy/*.patch` with `git apply --3way`.
  3. Detect patches already merged upstream with `git apply -R --check` and drop them automatically.
  4. Fail on conflicts and open an issue.
  5. Keep `git range-diff` output as an artifact.
- **Keep integration-package files out of upstream paths.** Use only drop-ins, hooks and `/etc/skel` extensions, so upstream updates never conflict.
- **Pin the Hyprland stack as a set** (hyprland, aquamarine, hyprtoolkit, hyprland-guiutils) from one repo. If you carry a VirGL Hyprland patch, use `IgnorePkg` for exactly that set, as try-omarchy does. Remove the hold as soon as upstream is clean.
- **Use upstream's own tests as the contract:** `test/all` (CLI and shell suites with platform fixtures, e.g. `test/shell.d/lifecycle-dispatch-test.sh`, `platform-setup-test.sh`), plus omarchy-iso `test/arm64-install`.
- **When upstream merges aarch64 ISO support and ships aarch64 on stable,** the variant should shrink to the VM integration package plus the overlay.

### 7.5 Staged roadmap

**Stage 0. Evaluate, about 1 day, on the M5 Max.** Run `try-omarchy` (QEMU/HVF/VirGL) and riverscn's UTM image to see the target UX and the graphics limits. Record the idle CPU, browser GPU and Electron behaviour.

**Stage 1. Generic UEFI VM, first target.**

1. **Build host:** an aarch64 Linux VM on the Mac (UTM/QEMU with HVF; nested KVM is available on M3+ under macOS 26), or an ARM CI runner.
2. **Packages:** apply P1–P8 to a quattro checkout, then build `omarchy`/`omarchy-settings` with `omarchy-pkgs` `bin/build --arch aarch64`, using `OMARCHY_SRC` pointed at the checkout. Build `omarchy-arm64-vm` and the gap fillers into a signed overlay repo.
3. **ISO:** run omarchy-iso `arm64-generic` with `--arch aarch64 --platform generic --local-source …`.
4. **Install** into a QEMU `virt` machine with these settings:
   - firmware: edk2 `QEMU_EFI`/AAVMF;
   - `-accel hvf` on the Mac, `kvm` in CI;
   - devices: `virtio-gpu-gl-pci` (or `virtio-gpu-pci` for 2D), `virtio-blk`, `virtio-net`, `qemu-xhci`, USB keyboard and tablet;
   - an encrypted Btrfs root, with Limine `limine_aa64.efi` + UKI.
5. **Daily-driver UX:** run in UTM (QEMU backend, "GPU supported" display) or a try-omarchy-style launcher.

**Stage 2. CI.** Run upstream's `arm64-iso.yml` pattern: build, then `test/arm64-live-boot`, then `test/arm64-install` with cidata answers. Add the checks in Section 8.

**Stage 3. Asahi hardware, later.** This needs an M1/M2 (or M3, llvmpipe) Mac. The M5 Max cannot be used. Use the upcoming Omarchy Mac Installer, or Asahi ALARM + `omarchy-mac` (omacom). The variant adds nothing platform-specific there: `aarch64-apple` is handled upstream by `omarchy-mac` and `omarchy-mac-boot` via lifecycle dispatch. Only the overlay and menu gating carry over.

---

## 8. Validation plan

1. **Package resolution, static.**
   - On an aarch64 Arch host or container with the variant's `pacman.conf`:
     - `pacman -Sy`
     - `pacman -Sp --print-format '%r/%n %v' $(omarchy-pkg-defaults aarch64) linux-aarch64 linux-aarch64-headers linux-aarch64-pkgbase-shim limine limine-mkinitcpio-hook limine-snapper-sync snapper btrfs-progs efibootmgr omarchy omarchy-settings vulkan-swrast qemu-guest-agent spice-vdagent > plan.txt`
   - Assert exit 0.
   - Assert the Hyprland stack (`hyprland|aquamarine|hyprtoolkit|hyprland-guiutils`) comes from a single repo.
   - Assert no `nvidia-*`/`lib32-*` in the plan.
   - Compare the closure size with this report's baseline (872 with Omarchy-first ordering). Diffs flag repo drift.
   - Also run `pacman -Sp` for every Install-menu package visible under `when` on aarch64, and fail if any is "target not found" (catches A6 regressions).
2. **Upstream unit tests.** Run `./test/all` on the patched checkout on Linux, in your dev environment. Add fixture tests for P1 (ALARM kernel layout), P3 (virtio lspci), P5 (menu guards) and P7 (missing hook).
3. **Image build.** Run the omarchy-iso `arm64-generic` build and check, as its CI does:
   - the ISO contains `EFI/BOOT/BOOTAA64.EFI`, `arch/boot/aarch64/vmlinuz-linux-aarch64` and `airootfs.sfs`;
   - the offline mirror index is complete.
4. **VM boot and install** (QEMU `virt`, AAVMF, KVM or HVF), using upstream `test/arm64-install` plus these checks:
   - `systemctl is-system-running` is `running` or `degraded`, and no failed units;
   - Hyprland is running; `omarchy-hw-platform` = `aarch64`; `omarchy-hw-vm` true;
   - booted via Limine UKI (`/boot/EFI/Linux/omarchy_*.efi`); kernel owned by `linux-aarch64`;
   - Plymouth LUKS prompt shown, by OCR of the screenshot as the upstream harness does with tesseract;
   - `omarchy update -y` completes **without** a kernel-reboot prompt when nothing changed (P1), and `omarchy-update-available` is quiet afterwards (no #14758 loop);
   - `vulkaninfo --summary` shows lavapipe/virtio, and `pacman -Q nvidia-utils` fails;
   - snapper creates a snapshot; `limine-snapper-sync` adds entries; booting a snapshot works (`btrfs-overlayfs`); factory reset round-trip;
   - `omarchy-refresh-pacman` keeps the overlay repo (hook);
   - menu: every visible Install entry installs (scripted via `omarchy-pkg-add` dry runs).
5. **Graphics matrix.**
   - Configurations: `virtio-gpu-pci` (2D/llvmpipe), `virtio-gpu-gl-pci` (VirGL), UTM Apple-VZ backend (2D), UTM QEMU backend (VirGL/ANGLE).
   - Record: Hyprland start, frame times and idle CPU (try-omarchy `profile-process.py` method), rounded-border artifacts, Chromium/Chrome GPU status, Electron apps (1Password, VS Code, Obsidian), `wf-recorder`, `gpu-screen-recorder`.
6. **Update soak.** Daily edge updates for 2 weeks: snapshot, then `omarchy update`, then reboot. Track pacman conflicts, migration failures and repo-shadowing downgrades.
7. **Asahi, stage 3.**
   - Run the lifecycle-dispatch operations end to end (provision, `update-verify`, `luks-slots`, factory reset).
   - Check 16K-page apps (FEX/Steam/box64-Dropbox/Electron), speakers (speakersafetyd), suspend, DCP external displays, Wi-Fi (brcmfmac firmware from `asahi-fwextract`), and notch layout.

---

## 9. Risks and open questions

- **Upstream moving fast.** aarch64 lands daily on edge. The ISO branches may merge soon and supersede parts of this plan. Re-check `omarchy-iso` `arm64-generic` and the omarchy `arm64-generic`/`n1x` branches before starting.
- **ALARM governance.** Builds are current, but community reports describe neglect. Fallbacks: Arch Linux Ports (drzee.net repos) or Holo Core if ALARM stalls. Omarchy mirroring ALARM at `arm-mirror.omarchy.org` reduces the risk.
- **Repo shadowing and ABI coupling** of the Hyprland stack (#14758). Decide on a single-repo policy.
- **Proprietary apps run emulated** (Dropbox via box64) or are absent (Spotify, Edge, Heroic, Minecraft launcher, Wine stack). That is acceptable per upstream policy: "hide what can't exist; fix upstream otherwise".
- **VM graphics ceiling on macOS.** No Vulkan Venus, GL ≤4.3 via VirGL, no hardware video decode, and Apple VZ is 2D only.
- **Supply chain.** ALARM DBs are unsigned and the default mirror is HTTP. The ISO builder config uses `SigLevel = Optional TrustAll` for `[omarchy]`/`[platform]` (`configs/pacman-online-aarch64.conf`), while installed systems use Required. Keep your overlay `Required`.
- **The user's M5 Max cannot run Asahi** (M4/M5 unsupported, and the Omarchy Mac Installer refuses M4+). Plan for VM-only on that machine.

---

## 10. Sources

**Upstream code, commits and issues**
- Omarchy repo (canonical): https://github.com/omacom/omarchy. Analyzed `quattro` @ `9480d1b6a98156314dbabe6bfef08f39f8b9cd07` (2026-10-11); `arm64-generic` @ `1407b2b5ccbc5c1510af529eb73f949e92b9e15b`; release v4.0.4 = `c668141e9c42b13c80c9ca4ea108e11708c5e8a5`; legacy v3.8.4 (`boot.sh`, `install.sh`, `install/preflight/guard.sh`).
- `basecamp/omarchy` redirect: `curl -sI https://github.com/basecamp/omarchy` → `301 location: https://github.com/omacom/omarchy`.
- Branch comparisons: https://github.com/omacom/omarchy/compare/quattro...arm64-generic, https://github.com/omacom/omarchy/commit/796a1869c, https://github.com/omacom/omarchy/commit/8d3123163.
- Upstream issues: https://github.com/omacom/omarchy/issues/10048, /12440, /12303, /14758, /15030, /14427, /14592, /12874, /8645, /11591, /9356, /9576, /13727, /12625, /8530.
- Omarchy ISO: https://github.com/omacom/omarchy-iso (quattro `53b80d406cdcb56cd757562e0f31d2c13cb57f47`). Plan: https://github.com/omacom/omarchy-iso/blob/quattro/plans/aarch64-support.md. Branches `arm64-generic` (`3a032eafba9ad7d22b755c66d087cfcc2abadda9`), `n1x`, `dragon`; `test/arm64-install`, `.github/workflows/arm64-iso.yml`, `builder/aarch64-package-filter.sh`, `configs/pacman-online-aarch64.conf`, `N1X.md`.
- Omarchy packages: https://github.com/omacom/omarchy-pkgs (master `c01894c8b85c4ef82c6b899d87a966122980f5f6`). PKGBUILDs `omarchy`, `omarchy-settings`, `omarchy-mac`, `omarchy-mac-boot`, `steam`, `dropbox`, `google-chrome`, `obsidian`, `hermes-desktop`, `linux-aarch64-pkgbase-shim`.
- Omarchy Mac: https://github.com/omacom/omarchy-mac, https://github.com/omacom/omarchy-mac-pkgs (`d8100ec9…`), https://github.com/omacom/omarchy-mac-installer.
- Try Omarchy: https://github.com/omacom/try-omarchy (`3c6056d1…`). `guest/spec.json`, `guest/README.md`, `guest/patches/omarchy/*.patch`, `guest/pacman.aarch64.conf`, `docs/architecture.md`, `docs/performance.md`.
- Community: https://github.com/riverscn/omarchy-aarch64-image, https://github.com/riverscn/omarchy-aarch64 (branch `v4-0-2` vs v4.0.2), https://github.com/ggalancs/omarchy-arm-utm, https://github.com/alexisraitano-myffu/omarchy-arm, https://github.com/kim-raaschou/omarchy-aarch64, https://github.com/thatcherstudio/omarchy-arm64.

**Package databases (fetched 2026-10-11)**
- ALARM: http://mirror.archlinuxarm.org/aarch64/{core,extra,alarm,aur}/*.db; https://arm-mirror.omarchy.org/aarch64/{core,extra,alarm,aur}/*.db.
- Omarchy: https://pkgs.omarchy.org/{edge,stable}/aarch64/omarchy.db, https://pkgs.omarchy.org/{stable,rc,edge}/x86_64/omarchy.db, https://pkgs.omarchy.org/aarch64/omarchy.db.
- Asahi ALARM: https://github.com/asahi-alarm/asahi-alarm/releases/download/aarch64/asahi-alarm.db.
- Arch x86_64: https://geo.mirror.pkgbuild.com/{core,extra,multilib}/os/x86_64/*.db.
- Vendor release assets via GitHub API: https://github.com/ollama/ollama/releases (v0.40.3, `ollama-linux-arm64.tar.zst`), https://github.com/bitwarden/clients/releases (desktop-v2026.9.1, `bitwarden_2026.9.1_arm64.tar.gz`), https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases (v2.22.3, no Linux arm64).

**Ecosystem status**
- Arch Linux Ports: https://ports.archlinux.page, https://ports.archlinux.page/aarch64/.
- Collabora/Valve Holo Core: https://collabora.com/news-and-blog/news-and-events/building-an-arch-linux-aarch64-port-for-holo-core.html.
- ALARM status discussions: https://archlinuxarm.org/forum/viewtopic.php?p=74021, https://lists.archlinux.org/archives/list/arch-general@lists.archlinux.org/message/5CKJKBWU2XMUQWY4EO3X43JU6EFRPTV5/, https://archlinuxarm.org/forum/viewtopic.php?p=73989.
- Asahi: https://asahilinux.org/blog/ (2026-09-06 "M2: Episode 1 (or, Asahi Linux on M3)"), https://linuxiac.com/asahi-linux-nears-official-support-for-apple-m3-macs/, https://www.igeeksblog.com/asahi-linux-m3-support/, https://www.pcgameshardware.de/Linux-Software-26761/News/Asahi-Linux-Apple-M3-Support-offiziell-1553190/.
- Asahi ALARM: https://asahi-alarm.org/.
- Chrome ARM64 Linux: https://linuxiac.com/google-chrome-is-finally-coming-to-arm64-linux/, https://www.techrepublic.com/article/news-google-chrome-arm64-linux-support-2026/.
- Steam on ARM64: https://www.gamingonlinux.com/2026/09/factorio-gets-a-full-arm64-linux-port-to-play-anywhere-especially-nice-for-the-steam-frame/, https://xenospectrum.com/en/steam-linux-arm-support-boundary/.
- Spotify aarch64 (absent): https://community.spotify.com/t5/Desktop-Linux/spotify-desktop-for-aarch64-linux/m-p/5495487.
- Edge on Arm Linux (absent): https://learn.arm.com/install-guides/browsers/edge/.
- VM graphics: https://www.qemu.org/docs/master/system/devices/virtio/virtio-gpu.html, https://eclecticlight.co/2022/07/06/virtualisation-on-apple-silicon-macs-2-how-does-it-work/, https://apps.apple.com/us/app/utm-virtual-machines/id1538878817.
- Hyprland VM notes: https://wiki.hypr.land/Getting-Started/Installation/ ("Running In a VM").

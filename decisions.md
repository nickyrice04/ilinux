# Decisions Log

Format: date, decision, context, alternatives, consequences. Newest last.

## D-001 · 2026-10-11 · Workspace location

**Decision:** The workspace lives at
`~/Documents/iLinux/apple-silicon-linux-research/`, inside the folder the
user opened for this project, rather than at `~/apple-silicon-linux-research/`.

**Context:** The mission suggested `~/apple-silicon-linux-research/` "such
as". The session's project folder is `~/Documents/iLinux`. iCloud Drive has
a `Documents` folder, but `~/Documents/iLinux` is not present in it and has a
different inode, so the workspace is not iCloud-synced (checked 2026-10-11).

**Consequences:** Large artifacts (VM disks, models) can stay in the
workspace. If iCloud "Desktop & Documents" sync is ever enabled, move
`virtualization/images/` and `benchmarks/ai/models/` out of `~/Documents`.

## D-002 · 2026-10-11 · Sanitized device-tree capture only

**Decision:** Never store raw `ioreg` dumps. Use `hardware/scripts/adt_extract.py`
(property names for every node, values only for whitelisted
hardware-description keys).

**Context:** The raw IODeviceTree plane contains serial numbers, UUIDs,
die IDs, boot nonces, entropy and MAC addresses. A first pass leaked `die-id`
through the whitelist; it was removed and added to the denylist.

## D-003 · 2026-10-11 · Portable, libc-independent benchmarks

**Decision:** Write our own small C benchmarks (`benchmarks/src/*.c`) whose
hot loops make no libc calls, plus a Metal benchmark for macOS. The same C
sources build on Linux.

**Context:** macOS-vs-Linux parity must compare hardware and kernel, not
libc `memcpy` or `qsort` implementations. Off-the-shelf suites (Geekbench,
fio, sysbench) are not installed, and installing them needs approval.

**Consequences:** Results aren't comparable with published Geekbench
numbers. They are comparable across OSes on this machine.

## D-004 · 2026-10-11 · Synthetic-weight GGUF models for LLM benchmarking

**Decision:** Generate models with real architecture shapes and random
weights (`tools/synth_gguf.py`) instead of downloading weights.

**Context:** llama.cpp throughput depends on shapes and quant types, not
weight values. No GGUF models were present locally, and downloads need
approval. A bit-identical file can be benchmarked on macOS and Linux.

**Limitations:** Output text is meaningless. Speculative or
quality-dependent features such as MTP and early exit cannot be measured. MLX
comparisons need real MLX models (some exist in the user's HF cache) plus an
approved MLX install.

## D-005 · 2026-10-11 · No background benchmark contention

**Decision:** While the baseline suite runs, agents do only light work
(documentation, web research) so measurements aren't perturbed.

## D-006 · 2026-10-11 · REA not installed until approved

**Decision:** Analyze REA statically and propose a project-scoped
integration, but run `npx rea-agents setup` only after explicit user approval.

**Context:** Setup may modify Claude Code configuration and install
host-level dependencies such as a JDK/Ghidra, both of which require
approval under the mission rules. Details are in
`research/rea/rea-analysis.md`.

## D-007 · 2026-10-11 · No upstream Asahi contributions from this (AI-driven) project

**Decision:** Treat everything produced in this workspace as **local research
and tooling**. Do not submit any of it to Asahi Linux projects (m1n1, linux,
docs, issues): the device-tree draft, findings, or analyses.

**Context:** Asahi's generative-AI policy (asahilinux.org/llm-policy,
2026-09-08) "broadly forbid[s]" generative AI for material contributions.
m1n1 PR templates require certifying no generative-AI use. Interpreting
hypervisor traces with an LLM earns a final warning. Separately, the
copyright policy restricts code written alongside binary disassembly to
trusted contributors and forbids disassembling Metal and the shader compiler.

**Consequences:**
* Upstream value flows only through **human** contributors working
  independently, or through projects whose policies allow AI assistance.
  Omarchy's repo ships an `AGENTS.md`; check its contribution policy before
  any PR.
* Hardware *data* the user personally collects with Asahi's own tools, such as
  ADT dumps, is the user's decision to share. This project won't send
  anything externally.
* REA use stays at the interface/metadata level and never touches Metal or
  the shader compiler.

## D-008 · 2026-10-11 · Disposable Linux VM: vzrun + Arch Linux ARM, built via Docker

**Decision:** Boot an Arch Linux ARM rootfs with the workspace-built `vzrun`
(Virtualization.framework, ad-hoc signed). Use direct kernel boot (the ALARM
7.1.6 kernel has virtio-blk/pci/console and ext4 built in, so no initramfs is
needed) on a 32 GB sparse ext4 image. Docker Desktop, already installed, is
used only as a Linux userland to GPG-verify the tarball against the pinned
ALARM key `68B3537F39A313B3E574D06777193F152BDBE6A6` and to run
`mkfs.ext4 -d`. Jobs run non-interactively through a virtiofs-shared
`job/run.sh`, and the guest powers off when done.

**Alternatives:** UTM, Lima, try-omarchy and QEMU (all host installs; not
approved). Apple `container` (not installed). krunkit for GPU (host install;
later, with approval).

**Consequences:** 2D graphics only (no GPU acceleration). CPU, memory and
storage measurements are valid as *VM* numbers. SME2 is exposed to the guest.
MIDR is masked (part 0x000).

## D-009 · 2026-10-11 · Same compiler target flags on both OSes for parity runs

**Decision:** Parity comparisons use `-O3 -mcpu=apple-m4` on both macOS
(Apple clang 21) and Linux (ALARM clang). `-mcpu=native` resolves
differently: Apple clang knows the host, while Linux clang sees the masked
MIDR. `-march=armv9*` must never be used, because it implies SVE, which this
CPU lacks.

## D-010 · 2026-10-11 · ADT extractor: full PMGR/DVFS tables plus a content-based leak check

**Decision:** Whitelist the PMGR `devices`, `ps-groups`, `voltage-states*`,
`acc-clusters` and `perf-*` tables, the CPU `function-enable_core` and
`function-cpu_idle` values, and the SART, NVMe and DART layout properties.
Emit binary tables as full hex. Before anything is written, compare in
memory the values of every denylisted property against every
representation in the output (strings, u32/u64 words, hex blobs). Output
is refused on any match. The only exception is a denylisted value that
equals the public model string (e.g. `/product/unique-model`). The denylist
was only extended.

**Context:** Decoding PMGR power domains and DVFS states needs complete
binary tables. Name-based filtering alone can't prove that a large hex blob
doesn't contain an identifier.

**Consequences:** `adt_extract.py --check-only` re-verifies any capture.
The 2026-10-11 capture reports "54 denylisted values compared, 0 problems".

## D-011 · 2026-10-11 · Clean-room boundary for t6050 SMP research

**Decision:** Use only m1n1, Linux and this machine's ADT as sources for
t6050 enablement. m1n1 PR #631 (closed, unmerged) describes Apple kext
internals, which implies binary analysis. Do not use it as a source.

**Consequences:** The SMP root cause must come from register-level probing
or hypervisor tracing on this machine. Both need user authorization.


## D-012 · 2026-10-12 · GPU-accelerated VM engine: QEMU + VirGL built in the workspace

**Decision (user-approved):** Build QEMU 11.1.1 (HVF, in-hypervisor GICv3) with
virglrenderer 1.3.0 and native macOS OpenGL from source into
`virtualization/qemu/runtime/`, following omacom/try-omarchy's MIT recipe and
patches. libepoxy comes from upstream (GNOME-published hash). A small patch
compiles EGL dispatch in for Apple and makes a missing `libEGL` mean "no EGL
context": epoxy probes EGL on every GL lookup, and aborted without it.
Khronos EGL headers are pinned by commit. There's no ANGLE and no
third-party prebuilt bottle, and audio uses CoreAudio.

**Why:** Virtualization.framework can't give Linux guests 3D. Accelerated
Hyprland is required for a smooth Omarchy experience and for battery
efficiency, since llvmpipe burns CPU.

## D-013 · 2026-10-12 · VM root on btrfs with Omarchy's subvolume layout

**Decision:** Migrate the VM disk to btrfs (`@`, `@home`, `@log`, `@pkg`,
zstd:1). Omarchy's system phase requires snapper/btrfs, so patching snapshots
out would diverge from the Omarchy experience. Compression shrank the 10 GB
system to 7.9 GiB.

## D-014 · 2026-10-12 · Guest kernel: full Arch ARM module set, essentials built in

**Decision:** Kernel v2 uses Arch Linux ARM's full stock config, extracted
from the stock Image via IKCONFIG, plus 16K pages, uclamp, test_power and 9p.
virtio net, fs, 9p, console and blk are built in.

**Why (lessons from v1):** `localmodconfig` trimmed modules ufw needs, and a
half-applied firewall cut all networking. Separately, Arch's
`linux-modules-cleanup.service` deletes `/usr/lib/modules` trees that no
package owns, which removed the custom kernel's modules. That service is
masked in the VM. Next step: package the kernel so pacman owns it.

## D-015 · 2026-10-12 · VM DNS through Quad9 with opportunistic DNS-over-TLS

**Decision:** NetworkManager `dns=none`. systemd-resolved uses
`DNS=9.9.9.9#dns.quad9.net …`, `DNSOverTLS=opportunistic`, `Domains=~.`.

**Why:** The NAT DNS proxy (192.168.64.1) never answered resolved's queries.
Before Omarchy switched networking to NetworkManager, lookups had silently
used resolved's Quad9 fallback.

## D-016 · 2026-10-12 · VM logs the owner straight into Omarchy (SDDM autologin)

**Decision:** `/etc/sddm.conf.d/20-ilinux-vm-autologin.conf` autologins user
`omarchy` into `omarchy.desktop`. hypridle and the shell lock still lock the
session on idle. Delete the file to get the SDDM password prompt back.

**Why:** Omarchy keeps autologin permanently on encrypted installs, because
the LUKS prompt is the auth boundary. In the VM, the boundary is the macOS
login session that launches QEMU. Anyone in that session can read the disk
image directly, so an SDDM password protects nothing and costs a second
login.

## D-017 · 2026-10-12 · Pin the Omarchy shell's QtQuick import to 6.11 (Qt 6.12 compat)

**Decision:** Install `compat/qt612-color-shadowing`, an idempotent script
plus a pacman hook. It rewrites the shell's unversioned `import QtQuick` as
`import QtQuick 6.11`.

**Why:** QtQuick 6.12's new `Color` type shadows the shell's `qs.Commons`
singleton `Color`, which leaves a black, empty bar and unthemed popups
(Confirmed, minimal reproduction). The pin hides only 6.12-only types. The
fix is self-disabling once upstream renames the singleton, and it applies on
native installs too.

## D-018 · 2026-10-12 · Desktop launcher: windowed by default, full screen and full grab opt-in

**Decision:** `run-omarchy-gpu.sh` opens a resizable Retina window by
default. `--fullscreen` (immersive Space) and `--full-grab` (system key
chords go to Hyprland) are opt-in. A workspace QEMU patch keeps the initial
window size and gives the guest the window's backing pixels at launch, so
Hyprland gets a crisp 2× mode from first boot.

**Why:** Full screen takes over the display, so it is the user's choice
(recommended for daily use). Full grab needs a one-time Accessibility grant
for the ad-hoc-signed QEMU, and each rebuild needs the grant again.


## D-019 · 2026-10-12 · Heterogeneous vCPUs that mirror Super/M scheduling

**Decision:** Add `-machine virt,bg-vcpus=N[,bg-capacity=C]` (workspace QEMU
patch). The last N vCPUs run their host threads at macOS background QoS and
are described to Linux as `capacity-dmips-mhz` C (default 220) vs 1024. The
launcher's `--hetero` gives 18 vCPUs in 3 clusters (6 background).

`omarchy-qos` keeps `background.slice` on the low-capacity CPUs. With
`RESERVE_EFFICIENT_CPUS=auto` (min/max capacity below 40%), it also keeps
system, session, app and utility slices off them.

**Why:**

* macOS only moves work to M cores under background QoS. That costs about
  4.7× speed and buys about 2.4× work per joule (F-028).
* Mapped this way, guest background work is 1.84–2.25× more energy-efficient
  than foreground, while foreground stays at 99% of native (F-029).
* Without the reservation, new tasks could start on a slow vCPU.

## D-020 · 2026-10-12 · App Nap policy for the VM: `auto`

**Decision:** Add a workspace Cocoa option, `app-nap=on|off|auto`. The
launcher defaults to `auto`: macOS may nap a hidden, idle VM, but QEMU holds
a user-initiated activity while non-background vCPUs are busy (more than 25%
of a core over 1 s, released after 10 idle seconds).

**Why:**

* A hidden QEMU window put every vCPU at background priority, about 4×
  slower, for work the user left running (F-027).
* `auto` keeps the idle cost at +0.09 W vs +0.14 W for `off` (F-032).
* Background-tier guest work does not wake the process.

## D-021 · 2026-10-12 · Event-driven VirGL fences on macOS

**Decision:**

* virglrenderer emulates eventfd with a pipe on macOS.
* QEMU enables threaded sync with async fence callbacks on the CGL path
  (previously EGL-only) and watches the poll fd.
* The 1 ms fence-poll timer becomes a 10 ms backstop in that mode.

**Why:** Polling added about 1.5 ms to every guest GL sync. The change took
blended fill from 17% to 74% of native, readback from 23% to 61%, and ALU
from 92% to 99.7% (F-030). It also removes about 1000 main-loop wakeups/s
during animation.

## D-022 · 2026-10-12 · Clipboard sharing through QEMU's vdagent, not a custom bridge

**Decision:** Build QEMU with `spice-protocol` headers to get the
`qemu-vdagent` chardev (`clipboard=on`, `mouse=off`). In the guest, a
stdlib-only Python agent speaks the vdagent clipboard protocol and uses
wl-clipboard. A udev `uaccess` rule limits the port to the desktop user.

**Why:**

* QEMU's Cocoa UI already owns the Mac pasteboard and transfers on demand:
  nothing is read until a paste happens. That is better for privacy and
  power than a polling bridge.
* The stock `spice-vdagent` is X11-only, which is why the guest needs its
  own agent.
* Tested both directions: Mac → Linux via `pbcopy`/`wl-paste`, and Linux →
  Mac via `wl-copy`/`pbpaste`. The Mac pasteboard was empty beforehand and
  was cleared afterwards.

## D-023 · 2026-10-12 · VM disk: writeback on a dedicated iothread by default

**Decision:** virtio-blk runs on its own iothread with 4 queues and
`cache=writeback`. `DISK_CACHE=none` (now F_NOCACHE) is available for
streaming or memory-sensitive use.

**Why:** These were the measured trade-offs (F-033):

* The iothread doubles random-I/O scaling, and keeps disk work off the
  main loop that also runs VirGL.
* Writeback gives native QD1 latency once data is warm.
* F_NOCACHE gives 4 GB/s writes and 100% cold sequential reads, but costs
  3× QD1 random-read latency.

## D-024 · 2026-10-12 · Adaptive display refresh, and an app bundle for the VM

**Decision:**

* Workspace patch 0006: one draw request per frame, a 100 ms tick after a
  second without frames, and a redraw when the window is unhidden.
* `virtualization/app/build-omarchy-app.sh` builds `Omarchy.app` in the
  workspace. It contains its own signed copy of QEMU and launches with
  options from `virtualization/run/omarchy-app.conf` (default
  `--hetero --fullscreen`).

**Why:**

* Idle QEMU CPU drops 45% (F-034).
* A bundle gives the VM a Dock identity, and macOS attributes privacy
  prompts (microphone, Accessibility) to "Omarchy" instead of the terminal
  or agent that started QEMU.
* Nothing is installed outside the workspace.

## D-025 · 2026-10-12 · Microphone via an AudioQueue input voice in QEMU's CoreAudio backend

**Decision:** Workspace patch 0007 adds capture to QEMU's CoreAudio backend.
It uses an AudioQueue on the default input device, set to the format QEMU
requests, and starts it only while the guest records. Frames are dropped,
never overwritten, if the guest falls behind.

**Why:**

* The backend had no input voice, so Linux apps had no microphone.
* AudioQueue converts formats itself, so the Mac's input device is never
  reconfigured. QEMU's playback path does change the output device's
  sample rate.
* The macOS microphone indicator and permission prompt stay meaningful.

## D-026 · 2026-10-12 · VM kernel packaged for pacman; boot-integration packages removed from the VM

**Decision:**

* The VM kernel is now the package `linux-ilinux-vm`
  (`omarchy-arm64/kernel/linux-ilinux-vm`: kernel.org 7.1.6 tarball, hash
  from the signed `sha256sums.asc`, plus the job-010 config). It owns
  `/usr/lib/modules/7.1.6-vzrun2`, so `linux-modules-cleanup.service` is
  unmasked again.
* The host boots the package's own Image (`images/alarm/Image-7.1.6-vzrun2-pkg`,
  exported by job 019).
* Removed from the VM: `limine`, `limine-mkinitcpio-hook`,
  `limine-snapper-sync`, `efibootmgr`, and the unused stock `linux-aarch64`.
  snapper stays.

**Why:**

* Direct kernel boot needs neither a bootloader nor an initramfs.
* Limine's pacman hook fires on systemd, firmware and module updates. On a
  non-Apple device tree it runs `limine-install`, which fails with no ESP,
  so every Omarchy update ended in an error.
* No package depends on these. try-omarchy's VM image ships without limine
  too.

## D-027 · 2026-10-12 · Guest Vulkan through Venus on MoltenVK, in-process, on by default

**Decision:**

* The VM's Vulkan driver is Mesa Venus. On the host it runs as
  virglrenderer's Venus renderer, in a render-server thread inside QEMU, on
  the Khronos loader and MoltenVK 1.4.2 (all pinned and built in the
  workspace, D-020 approval).
* Swapchain images reach the compositor through an IOSurface mirror (virgl
  patch 0007). Sub-page blobs are mapped in whole 16 KiB host pages (QEMU
  patch 0010).
* The launcher enables `venus=on,blob=on,hostmem=4G` by default.
  `--no-venus` opts out.

**Why:**

* Venus works with stock guest Mesa and no host install.
  KosmicKrisp/krunkit would need host packages.
* Compute runs at 94–98% of native MoltenVK (F-035). vkcube presents
  correctly at the 120 Hz output rate with D-028.
* Desktop GL is unchanged with Venus/blob on (glbench 0.99–1.17×).
* The 4 GiB BAR reserves address space only; pages are committed per blob.

**Trade-offs:**

* Each Vulkan frame costs about 0.12 ms of main-thread time and two GPU
  copies, a 140 µs blit at 1272×679 FP16. True zero-copy needs
  IOSurface-backed Venus memory and rectangle sampling in vrend.
* The Metal→GL ordering relies on observed driver behaviour (F-037).

## D-028 · 2026-10-12 · `MESA_VK_WSI_DEBUG=nowlts` in the VM session

**Decision:** The VM integration ships
`/etc/environment.d/60-ilinux-vm-vulkan.conf`, which turns off Mesa's
Wayland commit-timing timestamps for Vulkan FIFO. Native installs must not
carry it.

**Why:**

* Without a real vblank behind the VM's presentation feedback, about one
  FIFO commit in four waited an extra refresh: 92.9 vs 119.5 fps on the
  120 Hz output (F-038).
* GL already paced correctly.

**Revisit:** when QEMU provides paced virtual vblank and presentation
timestamps, re-measure with the timestamps on.

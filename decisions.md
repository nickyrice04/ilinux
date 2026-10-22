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

## D-029 · 2026-10-12 · Guest video decode through VA-API on VideoToolbox, inside virglrenderer

**Decision:**

* The VM's hardware video path is virglrenderer's video interface (the
  protocol Mesa's virgl VA-API driver already speaks), implemented on
  VideoToolbox (virgl patch 0008).
* Decoded pictures stay IOSurface-backed and reach the guest's video
  surfaces by GPU copies. They are fenced, so the picture returns to
  VideoToolbox's pool only after the GPU has read it.
* QEMU exposes it as `virtio-gpu-gl,video=on` (patch 0011). The launcher
  turns it on by default; `--no-video` opts out.
* H.264 first. VP9, HEVC, AV1 and encode (VTCompressionSession behind VA-API
  encode) come next on the same path.

**Why:**

* It needs no guest kernel or package changes. The stock Arch ARM Mesa
  ships the virgl VA driver, so FFmpeg, mpv, GStreamer `va` and Chromium
  can use it as they are.
* Whole-SoC power for 4K60 playback is 7.0 W against 17.3 W with guest
  software decode, both with mpv's default scaling. With the fast profile
  the VM now ships, it is 3.9 W against macOS's 2.9 W. The VM window was
  off screen in those runs, so host presentation is still unmeasured
  (F-046, F-048, F-049).
* Output is bit-exact against FFmpeg's software decoder (F-043, F-044).
* The alternatives:
  * virtio-video: an abandoned spec;
  * virtio-media: needs a new guest driver and a new QEMU device;
  * software decode: the status quo, at twice the power.

**Trade-offs:**

* The virgl video protocol carries Mesa-internal enums, which changed in
  Mesa 26. Guest Mesa upgrades can break the mapping (F-042).
* Decode stays synchronous on QEMU's main thread: about 1–3 ms per frame
  holding the global lock. The guest has no decode fence, so an
  asynchronous host decode needs completion tracking in vrend first (F-045).
* CPU readback of decoded surfaces needs a guest Mesa fix (F-045).
* None of this carries over to native Linux. The native path is the M5
  media engine (AVD) through a V4L2 stateless driver, which doesn't exist
  for M4/M5 yet (gap matrix: P1).

## D-030 · 2026-10-12 · Draw guest frames on flush; IOSurface presenter opt-in

**Decision:**

* QEMU's Cocoa GL display asks Core Animation for a draw as soon as the
  guest flushes a frame, instead of at the next GUI refresh tick (QEMU 0013).
* The IOSurface presenter (`COCOA_GL_PRESENT=iosurface`) ships but is off by
  default.
* Display benchmarks run with the VM window on screen: `COCOA_FLOAT=1`
  for measurement sessions only, and `playback_power.py` refuses hidden
  windows (F-049).

**Why:**

* Drawing on flush cut flush-to-draw from p50 6.4–8.1 ms and p95 11–13 ms
  to p50 0.14–0.23 ms and p95 about 2 ms.
* It draws every frame at 60 and 120 fps; before, 70–80% of 120 fps guest
  output was drawn.
* No power change was measured (F-051).
* The IOSurface presenter's lower p95 (0.25 ms) came with about +0.8 W in
  4K60 playback.

**Revisit:**

* If a Metal-side presenter (compressed, framebuffer-only drawables)
  removes the IOSurface presenter's video cost, it can become the default
  and also take the BQL off AppKit's main thread.


## D-031 · 2026-10-12 · Separate Linux VA driver, NV12 decode and lossless downloads

**Decision:** Build Mesa 26.2.4 plus two original patches as
`mesa-virgl-video-ilinux`, installed only in the existing VM, selected per
process by `ilinux-video`. Keep ordinary Mesa/GL/Vulkan packages intact.

**Evidence:** F-052/F-053. Cross-format VA downloads, rather than all CPU
readbacks, failed. Plane rearrangement avoids the failing shader conversion
and preserves samples exactly. NV12 decode removes the host's planar
conversion and reduces measured QEMU CPU cost by 41.3% for paced 4K60.
The experimental decode dirty-flag patch had no demonstrated benefit and
is not shipped. No whole-SoC power gain is claimed.

**RE scope:** The current user explicitly authorizes targeted local binary
analysis beyond earlier metadata-only research. REA establishes artifact
identity and interfaces; LLVM supplies bounded supplemental ARM64 inspection
while Ghidra/Hopper/IDA are unavailable. No proprietary code is copied, no
artifacts are uploaded, and native security/boot changes remain unauthorized.

**Limits:** Even progressive 8-bit 4:2:0 downloads only; other shader paths,
other codecs, asynchronous decode, native AVD and hardware validation remain.
See `reports/video-download-and-nv12-2026-10-12.md` for reproduction and rollback.

## D-040 · 2026-10-13 · Isolated REA native analysis with evidence gates

**Decision:** Run pinned REA/Ghidra in B's diskless ARM64 Linux lab, never
in the live Omarchy VM or through host-level installs. Copy only permitted
software payloads, retain full raw results locally in ignored files, and
publish provenance/behavioral conclusions rather than proprietary code.

**Evidence:** F-070–F-072. The provider smoke test and four native dossiers
work. Independent LLVM/original-byte checks cover 554 instructions. Three
decompilations contain out-of-body high-pcode despite `member` labels;
`check_evidence.py` therefore rejects their whole-function pseudocode.

**Engineering consequence:** Advance the existing SMP H2 with an original
read-only ADT audit and portable C mask-layout experiment. Linux builds and
tests validate arithmetic/error handling only. Hardware register semantics,
RVBAR, collection fixups and runtime dispatch remain unresolved; no native
MMIO change follows from this evidence alone. A owns the virtual wakeup path.

**Next gate:** Corroborate the selected PMGR dispatch and descriptor mapping,
then obtain explicitly authorized native observations before integrating a
startup-sequence change. Agent C configures the native desktop only after
the existing native gates. Full handoff:
`reverse-engineering/findings/rea-native-2026-10-13/handoff.md`.

## D-032 · 2026-10-13 · Fixed virgl VA-API driver is the VM session default

**Decision (agent A, goal 4):** The VM session makes
`mesa-virgl-video-ilinux` the default VA-API driver through
`omarchy-arm64/configuration/vm-integration/etc/environment.d/70-ilinux-vm-video.conf`:

```
LIBVA_DRIVERS_PATH=/usr/lib/ilinux-va:/usr/lib/dri
LIBVA_DRIVER_NAME=virtio_gpu
VIRGL_VIDEO_DECODE_NV12=1
```

So plain `mpv`/FFmpeg launched from the Omarchy desktop hardware-decode
H.264 with the lossless-download fix and NV12 decode, without the
`ilinux-video` wrapper. The wrapper (D-031) stays for explicit use.

**Why:**

* The driver is a strict superset of stock Mesa's virgl VA driver: it fixes
  cross-format 8-bit 4:2:0 CPU downloads (F-045) and, with
  `VIRGL_VIDEO_DECODE_NV12=1`, skips VideoToolbox's per-frame planar
  conversion (~41% less QEMU CPU for paced 4K60 decode, F-052/F-053).
* `LIBVA_DRIVERS_PATH` lists the fixed driver first and stock Mesa second, so
  removing the package degrades to stock video rather than breaking it.
* Only the VA video driver changes; OpenGL (virgl) and Vulkan (Venus) keep
  stock Mesa, confirmed after the switch.

**Opt out:** `VIRGL_VIDEO_DECODE_NV12=0` keeps the download fix without the
NV12 narrowing; remove the file to return to stock video entirely.

**Scope:** VM only. The handoff kit (coordination.md, goal 7) lists this
among the `vm-integration` files that must not be applied on native Asahi
hardware, where the path is the M5 AVD through V4L2.

## D-041 · 2026-10-13 · Driver contracts, local input patch and explicit hardware gates

**Decision:** Expand B's authorized REA work across driver families using
bounded, provenance-checked functions. Keep N1 ACIPC distinct from RTKit;
use ordinary host interfaces only. Independently verify instruction words
and reject out-of-body/truncated decompilations before deriving conclusions.

**Evidence:** F-073–F-075: 17 functions and 1,107 independently checked
instruction words; reusable selected ISP layouts; Linux-tested original
DockChannel input hardening and offline N1 queue helpers. Synthetic parser
checking overhead is +0.97% median, not a native performance claim.

**Implementation:** The input patch is for A's disposable native kernel
build, pending full-object and hardware validation. N1 helpers model bounded
software queues; they do not establish descriptor semantics, DMA barriers,
firmware ownership or operational Wi-Fi/Bluetooth. All raw proprietary
results stay ignored and local. No Apple code is copied into Linux.

**Next gate:** Build the full HID object, then validate physical input after
the existing native boot gates. Continue selected N1 descriptor/completion
and ISP startup questions. Agent C configures native Omarchy only after the
boot gate, with this hardware matrix and without VM-only bridge settings.
See `reverse-engineering/findings/driver-interfaces-2026-10-13/handoff.md`.

## D-042 · 2026-10-13 · Native critical path and bounded startup diagnostics

**Decision:** Per the user's new priority, A owns native full builds and the
first-boot/configuration handoff; B concentrates REA on startup, GPU/display
and idle/DVFS. Preserve the working VM as development infrastructure.

**Evidence:** F-076 resolves twelve static PMGR dispatch entries and links
the `clusters` property to descriptor-based startup packing. REA idle hooks
show status polling, not a complete safe Linux idle/resume protocol.

**Implementation:** F-077 is a public-source-only m1n1 guard experiment:
decline secondary activation after the existing locked-RVBAR check finds a
mismatch. It introduces no new hardware register access. The baseline
regression reproduces; eight Linux cases pass with GCC and Clang ASan/UBSan,
and the complete source compiles to ARM64 `smp.o`. Treat it as optional
diagnostic policy, never as a verified SMP-enablement patch.

**Next gate:** Retest unmodified pinned m1n1 on the actual unit after the
user approves native prerequisites. Keep entry-vector, mask, early-state
and exception hypotheses separate. No guessed CPU_START encoding or idle
policy change follows from static decompilation alone. Full handoff:
`reverse-engineering/findings/cpu-startup-2026-10-13/handoff.md`.

## D-043 · 2026-10-13 · Offline boot package with explicit native stop point

**Decision:** At the user's request, export/publish job-020 payloads with a
fresh unmodified m1n1 build and an original one-core diagnostic launcher.
Keep binaries in a private prerelease asset and checksums/source recipes in
Git. Offline verification is the default. No boot settings or physical boot.

**Evidence:** upstream linux.py starts secondaries unconditionally; setup.py
resets the panic counter; native handoff shuts down m1n1 USB. Its phram log
is not a Linux crash recorder. The new launcher avoids those controller setup
paths, verifies the packaged target build, and reads back the effective DT
before a separately approved handoff. NVMe/cpufreq stay disabled in Stage B.

**Validation/limits:** job-021 build/schema checks, 17 offline tests and one
real serializer test pass. The exact kernel/initramfs reaches PID 1 and 60
seconds of heartbeats in a diskless ARM64 VM. Native J716c DT/USB/framebuffer,
SMP and power remain untested. A real OS entry requires Apple boot assets and
paired recovery; an empty APFS volume is insufficient. See `native/boot/`.

## 2026-10-13 · Second-machine package intake and staged execution

**User direction:** receive/checksum the M5 native package with the client
pinned to the agreed target m1n1 revision. Await the corrected single-core
launcher and boot-entry procedure; do not run upstream `tools/linux.py`.
The first live action is the bounded USB handshake, then recording the
results of approved diagnostic boots.

**Implementation:** local-only package/receipt/result directories, manifest
verification against the sender's separate digest, a clean-client pin check
and an observation template. Checksum verification does not authorize a boot
or establish the target's actual running version. No live test has occurred.

## D-044 · 2026-10-13 · Dedicated M5 entry via a matching macOS scaffold

**Decision:** Prepare the exact procedure for a second full macOS installation
named `iLinux Boot Lab` in the existing APFS container, followed by a lab-only
m1n1 boot object. No execution is authorized by this preparation request.

**Evidence:** Read-only checks show approximately 1.017 TB free and Apple still
offers the host's exact 26.6.2 / 25G83 installer. Apple documents volume-based
multiple installations and per-OS recovery pairing. Local tool help and pinned
Asahi stage-two source substantiate the policy/boot-object command sequence.

**Limits:** The installer can touch shared boot metadata and service firmware;
the matching build does not guarantee no firmware effects. No supported Asahi
M5 installer or native J716c boot has been validated here. Actual installer
metadata, future volume identities, paired 1TR and owner authentication must
be checked at the appropriate stage. There is no need for a Linux root/ESP or
container shrink for the proposed RAM test.

**Validation/next:** Five shell blocks parse; a mocked preflight passes the
valid case and rejects eleven failures. No host disk/policy calls were made
by those tests. See `kernel/native-enablement/boot-entry-setup.md`; wait for
M1 receipt and explicit installation/boot approval before any host changes.

## D-045 · 2026-10-13 · Download authorization does not authorize installation

**User direction:** download the matching macOS installer while M1 finishes
verification; stop before creating volumes or changing boot settings.

**Result:** downloaded 26.6.2 through Apple's softwareupdate. Embedded asset
metadata confirms 25G83; disk-image checksum passes. Application signature/
Gatekeeper assessment reports a custom-resource-envelope error, which must be
resolved before launch. No installer launch or assessment bypass was attempted.

**Coordination:** M1 should publish its actual offline receipt/test results,
keeping all live USB/native boot checks **NOT RUN**. A working native desktop
is not established by this download or the controller's offline test success.
The dedicated entry and first native diagnostic remain separate later steps.

## D-046 · 2026-10-13 · Authenticate the original package without bypassing app checks

**User direction:** resolve installer verification without disabling security
checks; stop before volume creation or boot changes.

**Finding:** the app's custom resource rules explain the generic whole-app
verification rejection. The installed SharedSupport.dmg also contains the
original Apple XAR package, as described by its signed postinstall script.
That package passes `pkgutil` trust verification and Gatekeeper's install
assessment. Its table matches Apple's catalog and stored signed checksum;
all five signed entries and installed app contents match. Three executable
signatures pass strict Apple-anchor checks. No replacement download was needed.

**Decision:** record authenticity/integrity as verified using that independent
chain, while retaining the whole-app rejection as an unchanged observation.
Do not re-sign, suppress errors, strip quarantine or add security exceptions.
The original read-only verifier passes on the actual package; eleven synthetic
integrity/parser regressions pass. This is not proof of successful installer
launch, OS installation or native Linux boot. Stop if a later authorized
normal launch is blocked. See `native/boot/macos-installer-download.md`.

**Coordination:** M1 report `dfdf8cf` is reviewed and integrated. Offline ready;
all live checks **NOT RUN**. Dedicated-entry provisioning remains a separate
user-authorized step, not implied by either machine's verification results.

## D-047 · 2026-10-13 · Provision the lab macOS entry, stop before boot security

**User direction:** set up iLinux Boot Lab, preserve original macOS, stop before
changing boot security, and provide restart timing and an M1-agent handoff.

**Action:** selected the current original installation's internal APFS container
after read-only checks; created exactly one uniquely named lab volume with no
partition resize/quota/reserve. Existing volumes retain names/roles/encryption.
Original security mode is Full, with SIP/authenticated-root and FileVault enabled.
Installer content verification was repeated successfully; the normal GUI launched,
the user authorized the license, and the lab was explicitly selected as destination.

**Boundary:** an empty volume is not a bootable entry. During the handoff the
installer advanced to installation progress, still targeting the lab. Completion,
new local-account setup and return-to-original verification are unverified.
Apple's installer manages the required restarts; save remaining work and let
it finish. No boot-security changes, custom boot object, live USB/native tests,
firmware recovery or automatic erase/removal are authorized. The M1 assists with
the bounded provisioning handoff, retaining NOT RUN for all live tests.

**Limits:** the backup destination is disconnected; its completion is the user's
report, not a fresh content check. A normal macOS installation writes shared
boot metadata and may service recovery/firmware, as already disclosed in D-044.
The original System/Data volumes are not installation destinations. See the
current execution handoff in `kernel/native-enablement/boot-entry-setup.md`.

## D-048 · 2026-10-13 · Separate macOS boot success from native evidence

**User direction:** review the M1 restart report and determine next steps for
booting Linux and collecting data. This does not lift the previous security hold.

**Evidence:** M1 report `f34970e` records user-observed lab setup/boot and return
to Macintosh HD. B independently verifies both builds, lab/original volume-group
separation and original FileVault/SIP/authenticated-root. Post-return boot-policy
modes remain pending an authenticated read; automated Terminal access was blocked.
Packaged m1n1 still hashes correctly but is not staged on the lab Data volume.

**Next experiment:** lab-only custom boot setup after explicit authorization;
Stage A m1n1/P_NOP, then separately approved Stage B one-core RAM Linux. Record
provenance, controller checkpoint/exit, M5 screen/PID 1/CPU/memory/interrupts,
60-second liveness and macOS return. No native success follows from a controller
handoff alone. The proposed screen-observation limit is 120 seconds after
handoff; the existing 180-second controller deadline is a different bound.
Blank output is an observation-path problem to investigate before another
blind attempt, not evidence of a particular driver failure. No native performance
or desktop-compatibility claim follows from this first diagnostic.

## D-049 · 2026-10-13 · Stage an ordinary lab file without installing a boot object

**User direction:** provide the read-only policy-check command, then stage m1n1;
preserve original macOS and supply restart timing and an M1-agent handoff.

**Action/evidence:** rechecked the mounted lab System/Data roles and group,
separation from original, original FileVault and destination parents. Created
only the lab Data `Users/Shared/iLinuxBoot` directory and `m1n1.bin` with exclusive
file creation. Reread bytes match the boot021 source and tracked manifest:
3,932,160 bytes, SHA-256
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
No existing file was overwritten; no boot policy or startup setting changed.

**Boundary/next:** staging is reversible file preparation, not custom boot
installation. It needs no restart or policy reduction. Current per-OS policy
modes remain pending the user's manual read-only helper output. Review that
result and obtain explicit authorization before lab-only Permissive Security,
kernel CTRR/custom-boot work and the paired-Recovery restart. M1 prepares
records offline; all live/native checks remain NOT RUN. Original macOS remains
the protected reference environment.

**Follow-up, 2026-10-13:** the user supplied the read-only helper JSON: original
Full / exit 0; lab Full / exit 0; `read_only: true`. B reviewed it and resolved
the pending policy read, without independently rerunning the privileged query.
This result does not lift the user's stop before boot-security changes. The
prepared lab-only Recovery/custom-boot procedure still needs authorization;
pairing/target checks must pass in Recovery before any write. No live test ran.

**Authorization expansion, 2026-10-13:** the user then explicitly authorized
lab-only Recovery setup, Permissive Security, disabling kernel CTRR and m1n1
installation, preserving Macintosh HD at Full Security. This supersedes the
previous hold for that scope; do not ask for the same approval again. Pairing,
target, payload and original Full checks remain execution prerequisites.
The read-only helper and guarded one-at-a-time commands are prepared/tested;
helper staged on lab Data, no boot-policy/install command run from the desktop.
M1 guides the human through Recovery and returns to original macOS afterward.
Stage A/P_NOP and Stage B/Linux remain separately gated. No native success is
inferred from authorization, preparation or a future kmutil success alone.

## 2026-10-13 · Record completed lab installation and incidental m1n1 startup separately

The authorized human/M1 Recovery session reports preflight exit 0, lab-only
Permissive/kernel CTRR change, kmutil exit 0/Installed yes and final original
Full/lab Permissive. User confirms return to Macintosh HD and default restored.
Recovery's missing shasum was handled by a temporary, narrowly scoped shell
function using the available sha256; the verified helper file stayed unchanged.

During return the user accidentally booted m1n1; their photo shows
`Running proxy...`, followed by user-reported power-off and original macOS
return. Record that incidental screen observation separately from controlled
tests. Live USB/P_NOP, exact live version checking, Stage B/Linux and native
Omarchy remain NOT RUN. This event grants no further authorization and does
not complete Stage A. No raw photos or device identifiers are saved.

**M5 review/next, 2026-10-13:** B reviewed M1 commit `c6f2c6f`, verified original
build/FileVault/SIP/authenticated-root and staged payload hash, and received
the user's fresh read-only original Full/lab Permissive result (both exit 0).
Treat provisioning and return verification as complete; do not repeat Recovery
or reinstall m1n1. Next proposed experiment is controlled Stage A boot/P_NOP,
then review before the one-core RAM Linux diagnostic. Incidental proxy screen
output establishes bootloader execution, not USB transport, Linux execution,
GPU acceleration or performance parity. No live test was authorized or run
by this request to review progress and recommend next steps.

**Stage A approval, 2026-10-13:** the user subsequently explicitly authorized
one m1n1 boot, one USB handshake and return to Macintosh HD, retaining Full
Security. This lifts the Stage A hold for one session; no repeat approval is
needed. Keep the original as default, use the existing lab entry through the
picker, send only the bounded P_NOP and return after success or failure.
No retries, policy/boot-object writes or Linux launch. Record actual evidence;
authorization/preparation does not change NOT RUN to PASS. M1 guides the human
while the M5 desktop agent is offline and publishes a sanitized result.

## 2026-10-13 · Identify Stage A USB by descriptor ancestry, not callout suffix

The first controlled m1n1 boot reached proxy, but the checker stopped before
opening either discovered callout because its P_01 suffix assumption failed.
User confirms Macintosh HD return and requests an offline fix. No P_NOP ran.

Pinned source uses a real serial when present and P-0 only as fallback. Require
m1n1 VID/PID 1209:316d and primary CDC data interface 1 through the cached
macOS USB registry ancestry. Reject ambiguity or missing metadata; never guess
from filename/order, loosen to every modem, or probe both interfaces. Keep
callout paths and raw registry data only in memory. Preserve the single P_NOP,
10-second deadline, no retry, client pin and boot021 package. Twenty offline
tests pass; real metadata selection remains pending the next user-started
Stage A session. Linux and live version verification stay NOT RUN.

## 2026-10-13 · Accept Stage A proxy response separately from Linux readiness

After the naming fix, the user started a new Stage A attempt. The corrected
checker found one primary interface and received one P_NOP reply (exit 0,
0.158 seconds, UTC 2026-10-14 01:13:02), then closed the port. No retry or
memory/register/boot request occurred. User confirms Macintosh HD return.
Record the USB result as PASS and the desktop return as user-observed; fresh
post-attempt build/default/protection checks remain pending M5 review.
Keep exact live target-version verification and Linux/Stage B NOT RUN.
P_NOP confirms proxy response, not the running build or Linux compatibility.
Boot021/client pin stay unchanged; this report authorizes no further boot.

## 2026-10-13 · Carry observed USB identity into the native Linux launcher

Stage A's real failure/success established that the filename suffix is not
reliable but descriptor ancestry works for this M1/M5 pair. The Stage B
launcher still used the rejected suffix rule. Share the selector rather than
maintaining a second implementation or weakening it to arbitrary modem paths.
The live launcher rechecks the sole primary just before opening; `auto` avoids
serial-bearing command arguments. It closes transport on initialization failure
and reports non-sensitive progress checkpoints. No boot artifact rebuild needed.

Stage A return protection checks are complete: independent original build,
FileVault/SIP/authenticated-root and user-supplied original Full/lab Permissive
JSON. The next physical experiment is one separately approved Linux RAM boot.
Keep `idle=nop`, disabled cpufreq and single-core limits for initial diagnosis;
these workarounds cannot substantiate macOS-class performance/efficiency. Once
kernel liveness is observed, use that result to target REA and driver changes,
then validate SMP/idle/DVFS and GPU/display independently on this exact machine.

## 2026-10-13 · Authorize one bounded Stage B attempt after controller readiness

User explicitly approves one Linux RAM boot after M1 confirms readiness,
then return to Macintosh HD. Preserve original Full Security; no volume or
security changes. Earlier Stage B permission holds are superseded for this
scope, but approval is not a readiness or execution result. M1 verifies the
changed controller, confirms ready before human shutdown, runs the existing
launcher once and records screen milestones/return. No retries or scope
expansion; no new installation is needed. Keep NOT RUN until observed.

## 2026-10-13 · M1 controller readiness passed for the authorized Stage B attempt

Read authorization `b06c56e`; completed package verification, 31 launcher,
20 USB and 7 intake cases (all exit 0), plus 13 receipt-file/manifest checks.
Keep boot021 and pinned clean client unchanged. Publish readiness before the
human boots the lab; then run the documented launcher exactly once and collect
controller/screen/return evidence. No new live action occurred in preparation.
Keep Linux/live version checks NOT RUN until actual observations supersede them.

## 2026-10-13 · Stop Stage B at KeyError; correct the ADT API use offline

One authorized attempt stopped before upload/handoff after target checks passed.
User confirms Macintosh HD return and explicitly requests no retries. Preserve
Linux NOT RUN, but update live packaged-marker verification to observed PASS.
Do not infer heap exhaustion from normal heap-limit output or relabel the failed
controller preflight as a Linux boot failure. No new policy/volume work.

Real pinned-parser/synthetic-data regressions prove the launcher's root lookup
was wrong; read root compatibility directly and keep wrong/missing-board rejection.
Original fake dictionary hid the mismatch. Fix only local launcher/tests; keep
upstream pin and boot021 intact. 31 launcher + 4 ADT cases and offline package
verification pass. Precise live throw site is uncertain without raw traceback;
fix is not hardware-tested. M5 reviews result and read-only return checks next.

## 2026-10-13 · Review the launcher API fix and proceed with one corrected attempt

M1's first Stage B stopped before upload/handoff; a confirmed pinned-ADT API
mismatch explains its checkpoint/type, with exact live throw site still uncertain.
Review accepts the narrow root-property fix and actual-parser regression; no
kernel rebuild or reinstall follows from a controller API error. User now asks
to prepare the next boot and M1 handoff. Carry that direction into one corrected
Stage B attempt with existing scope, fresh evidence record, bounded stop and
original macOS return. Preserve original Full Security and make no volume or
security changes. Do not request already-given permission again or require
another readiness-message loop for unchanged code M1 already tested.

## 2026-10-13 · Stop corrected Stage B at the prepared-DT framebuffer gate

Attempt 2 passed root compatibility and initial framebuffer checks, uploaded
payloads, then rejected the prepared DT for lack of an enabled simple-framebuffer.
Keep this observation gate; no Linux handoff occurred and Linux stays NOT RUN.
Retain the exact fixed rejection and safe traceback metadata, separating this
result from attempt 1's KeyError. The single corrected attempt is consumed.
Guide original-desktop return and record confirmation only when received;
no retries, security changes or new live diagnostics. Investigate the specific
framebuffer preflight failure offline after return, without claiming a Linux
kernel/display failure or changing boot021/client pin in this reporting task.

## 2026-10-13 · Accept user-confirmed attempt-2 return; retain screen evidence limits

User confirms the usual Macintosh HD desktop. Photo ends at m1n1 `FDT prepared`
(address omitted), consistent with controller rejection after DT preparation.
Record the display/reserved-memory/GPU warnings as observations, without inferring
a freeze or Linux failure. Linux remains NOT RUN; the controller never handed off.
Fresh default/build/security checks remain for M5. No reconnect or retry, and no
image, target addresses or raw diagnostic data are copied into the repository.

## 2026-10-13 · Fix the DT contract before rebuilding or broadening native scope

Attempt 2 reached m1n1 DT preparation; its packaged DT omitted the framebuffer
placeholder required by `dt_set_fb()`. Reproduce this using the exact pinned
public C function in an isolated VM, then insert only that placeholder. Keep
all other payload bytes unchanged and publish a new boot022 artifact rather
than overwrite boot021. Retain/strengthen the observation gate; do not paper
over the rejection or modify unrelated display/GPU nodes without evidence.

Use public source for this known interface; REA is reserved for missing behavior
that source cannot explain. Package/validate before reboot. The user's next-boot
direction carries into one reviewed corrected RAM attempt once M1 intake and
return-policy checks pass, with a new evidence record and no automatic retry.
M1 can confirm readiness directly to the human; no redundant inter-agent
approval loop is required. Prior default/security/boot-object settings are
unchanged; no new installation or host policy work is involved.

For reaching Omarchy sooner, prioritize native liveness and an interactive
Linux access/rootfs path before unrelated peripheral research. A first desktop
may precede accelerated graphics; it cannot establish macOS-class efficiency.

## 2026-10-13 · Accept supplied return-policy check; wait only for new-package intake

The user's requested read-only helper result reports original Full/lab
Permissive, both exit 0. Record the policy prerequisite as complete, identifying
this as reviewed user-supplied output rather than an independent query. M1
boot022 intake is the remaining preparation step; after it passes, the human
can start the already reviewed single attempt. Do not repeat the policy check
or add another approval round trip for unchanged scope. No code or payload
changes require tests to be rerun for this documentation update.

## 2026-10-13 · Accept M1 boot022 intake; wait for human lab selection

M1 independently verifies the Git-tracked archive before extraction, the new
13-file receipt, source hashes/pin and 31+5+4 offline tests. Actual payload
comparison confirms only the Stage-B DT differs; retain installed m1n1 and its
boot021 marker. Existing M5-reviewed policy JSON satisfies the prerequisite.
Confirm ready directly to the human and wait for Running proxy; one documented
attempt 3 only, then screen milestones and Macintosh HD return. No USB opened
at readiness; Linux/current live checks remain NOT RUN. Preserve both earlier
attempts and all receipts; no retry, reinstall or boot-setting changes.

## 2026-10-13 · Preserve passing boot022 gates; diagnose m1n1 exception offline

Attempt 3 passed all controller preflight checks and requested handoff. Target
photo establishes m1n1 SError/EL2 and unhandled-exception reboot output; the
controller USB timeout alone would not establish success or failure. Kernel,
PID 1, online CPU count and 60-second liveness remain NOT OBSERVED. User confirms
Macintosh HD return. Record safe code offset/log text only, omit raw register/
address data, and distinguish nearby PCIe warnings from a proven cause. M5
reviews the exact pinned handoff path/build symbols offline and checks return
protections; no retry, reinstall or boot-setting changes are authorized.

## 2026-10-13 · Honor DAPF instance metadata; use a bounded RAM workaround first

The matching shipped binary, public source, REA and instruction cross-check
place the handoff exception in DAPF initialization. The AOP register index used
by m1n1 is GAPF according to this Mac's sanitized instance table. Correct the
layout handling before attempting another boot; do not infer that PCIe warnings
caused the exception or broadly bypass hardware initialization.

Keep a tested source fix for future builds. For the next experiment, leave the
installed boot object unchanged: verify the exact live table/code and current
ADT layout, then remove only the absent AOP DAPF entry from its RAM work-list.
One 96-byte data write, readback checked, is the entire correction; no firmware
filter register or protection control is written by it. Preserve all other
entries and existing launch gates. Unknown layouts/readback failures stop.

The user requested fixing the error; this prepares a proposed next experiment,
not an automatic retry under consumed attempt-3 authorization. M1 verifies
offline and waits for the human to start that single experiment. No repeated
policy query is needed: fresh original Full/lab Permissive JSON already passed.
Actual native correction and Linux execution remain unverified.

## 2026-10-13 · Accept attempt-4 offline checks; preserve the explicit-start boundary

M1 independently passes the 53 required launcher/DAPF/parser cases and verifies
unchanged boot022, its retained receipt, exact reviewed source hashes and clean
client pin. Record readiness before the human restarts; do not open USB until
the human explicitly starts the single experiment and reports Running proxy.
Capture both DAPF checkpoints plus handoff/screen/return evidence. Prior policy
PASS remains current; no reinstall, settings change or automatic retry. Native
RAM correction remains untested and Linux execution remains unobserved.

## 2026-10-13 · Separate accepted handoff/DAPF correction from observed Linux

Attempt 4 passed live DAPF provenance/layout, the bounded RAM correction and
readback, final DT gates and kboot request/reply. Controller exit 0 is not a
kernel/PID 1/liveness result. Human saw logo and unreadably fast text; record
milestones NOT OBSERVED and do not invent a panic or claim native success.
Stop was instructed at the 120-second screen limit; the user confirms macOS
return. M5 should improve
early-boot observation offline before proposing another physical session.
No reconnect/retry, reinstall, boot-setting change or new live diagnostics.

## 2026-10-13 · Instrument the silent handoff before another native attempt

Attempt 4 proves the DAPF RAM correction and kboot reply, not Linux execution.
Exact-binary REA plus public source confirms that m1n1 clears its console before
its final jump. Select bounded original kernel instrumentation rather than
speculative register/driver changes: three pre-MMU rectangles, a flat-DT early
framebuffer console and initcall tracing. Use the already validated scanout
range through a verified 16-byte RAM descriptor; no physical address is baked
in or exported. Only Image changes in boot024; boot022 DT/initramfs and the
installed boot021 m1n1 stay unchanged. This diagnostic overhead is not a
performance result. Generic VM and synthetic renderer success do not validate
native framebuffer access. Require local screen recording before one
human-started attempt 5, with the existing stop/return bounds; M1 offline
readiness and human start suffice without another inter-agent approval loop.
Fresh post-return policy JSON already passed; no duplicate check requested.

## 2026-10-13 · Accept boot024 M1 intake; require recorded screen evidence

M1 independently verifies the Git-tracked archive before extraction, all 13
receipt files, reviewed controller digests, clean client pin and 65 offline
cases. Only Image differs from boot022; installed boot021 m1n1 remains correct.
The human has started the lab and confirms Running proxy and phone recording.
Publish readiness before one invocation; no additional M5 approval round trip
or duplicate policy query is required. Attempt 5/live checks remain NOT RUN at
readiness. Capture both DAPF checkpoints, the new descriptor checkpoint and
observed screen milestones without exposing target memory/identifiers. Respect
the existing stop/return limits; no reinstall, boot changes or automatic retry.

## 2026-10-13 · Treat attempt-5 Linux panic as observed kernel evidence

Boot024 produced readable native early kernel text. Record Linux execution as
OBSERVED, distinguish controller/DAPF/descriptor PASS from the undefined-
instruction failure at aic_init_cpu+0x9c, and leave PID 1/diagnostic CPU count/
60-second userspace liveness NOT OBSERVED. The still does not establish the
rectangle count or exact faulting instruction cause; retain symbolic offsets
and safe text only. User confirms Macintosh HD return. M5 owns read-only return
checks and exact-build offline AIC diagnosis next. Preserve the successful
observation path, existing guards and installed boot object; no retry, settings
changes or new live session under this consumed attempt.

## 2026-10-14 · Restrict t6050 AIC guest/uncore features for the next RAM boot

Attempt-5's exact linked PC identifies a faulting legacy guest-timer enable
write. REA supports the register-update path but its init-function pseudocode
omits static-key/WARN paths; source and linked instructions remain authoritative.
Do not infer register absence, alter security controls, or patch only one PC.
Use architectural guest-timer source masking, reject unsupported guest IRQ/KVM
mappings, and separate unvalidated uncore access from fast IPI support in an
exact t6050 profile. Preserve previous AIC profiles, tested boot guards and
installed bootloader. Boot025 changes only Image. Physical IRQ/timer delivery
remains unvalidated despite 38 actual-driver scenarios, full link, 65 controller
cases and generic VM liveness. Publish one human-started attempt-6 checklist;
M1 offline readiness plus human start suffice, no redundant approval loop.
Original Full/lab Permissive fresh user JSON already passed after attempt 5.

## 2026-10-14 · Accept boot025 intake for one recorded attempt 6

M1 independently verifies the Git-tracked archive before extraction, 13 files,
reviewed controller hashes, unchanged clean client pin and all 65 offline cases.
Only Image differs from boot024. Human has started this attempt and confirms
proxy/video readiness; publish readiness, then invoke the same reviewed launcher
once. Existing post-attempt-5 policy PASS suffices. Capture AIC profile/final
initialization and timer progress separately from PID 1/liveness. No retry,
reinstall or settings changes; return to Macintosh HD at the documented stop.

## 2026-10-14 · Record late kernel progress separately from diagnostic userspace

Attempt 6 passes the same controller gates and produces late native Linux
initcalls with advancing timestamps. Record the last visible clk_debug_init
call and the human-confirmed unchanged screen; do not assert it proves the
precise hang or hardware cause. Earlier AIC/timer log lines are absent from the
supplied still; later progress is evidence beyond attempt 5, not complete IRQ
validation. Keep diagnostic PID 1/CPU/liveness NOT OBSERVED; initcall @ 1 does
not establish execution of /init. User confirms Macintosh HD return. M5 owns
read-only return checks and exact-build offline analysis next. No retry,
reinstall or boot-setting changes under this consumed attempt.

## 2026-10-14 · Isolate optional clock debug registration with one fixed skip

Attempt-6 late native progress moves the evidence beyond the AIC panic, but the
last clk_debug_init line is not an exact hang PC. Exact source and bounded REA
show debugfs setup, separate from normal clock operation. Select the existing
Linux initcall blacklist for only clk_debug_init; do not change clocks, remove
locks, disable all debugfs or rebuild identical payloads. Keep the argument
fixed and validated in the prepared DT, with omission/expansion regressions.
The unchanged boot025 Image passes the explicit skip and 60-second userspace
VM check. This is a temporary diagnostic workaround, not a native fix claim.
If another initializer stalls, investigate shared dependencies/visibility rather
than automatically expanding the blacklist. Publish one attempt-7 procedure;
M1 readiness and human start suffice. Fresh post-attempt-6 policies already PASS.

## 2026-10-14 · Accept attempt-7 offline readiness without extending the skip

M1 rechecks unchanged boot025 and passes all 69 controller cases, exact source
hashes and clean client pin. The only added argument is the reviewed fixed
clk_debug_init blacklist. Preserve earlier receipts/results; publish readiness
before one human-started recorded invocation. Human reports proxy/video ready;
post-attempt-6 policy PASS already suffices. Capture skip and subsequent progress;
no speculative additional skip/retry/settings change. Return within the bound.

## 2026-10-14 · Record later initialization without inventing the skip message

Attempt 7 passes exact prepared arguments and controller gates; fresh photo
shows initialization past the former clock-debug boundary to deferred_probe_initcall.
Record that progress, while leaving the unreadable blacklist checkpoint and
diagnostic userspace/liveness NOT OBSERVED. Exclude the accidentally repeated
attempt-6 photo. The last initializer is an observation boundary, not a proven
hang cause. At the time limit, instruct original-macOS return; confirmation is
pending. Preserve the one-skip limit: M5 analyzes shared dependencies offline,
with read-only post-return checks, not another speculative skip or retry.

## 2026-10-14 · Close attempt-7 return confirmation

The human confirms successful return to the usual Macintosh HD desktop and
reports no later screen message. Update the pending-return record to confirmed;
keep diagnostic PID 1/CPU/liveness NOT OBSERVED and fresh protection/default
checks NOT CHECKED. M5 can proceed with read-only return checks and offline
analysis. No new live session or settings changes are authorized.

## 2026-10-14 · Instrument deferred probing and verify the hardware description

Attempt 7 moves beyond the clock boundary but does not prove a deferred driver
or timer fault. Exact-build REA and source locate a debugfs call and two worker
flushes. Keep normal work and the existing single skip; add bounded phase,
counter/tick and independent timer-softirq observations in boot027. Do not
substitute another guessed register write or blacklist. The helper is opt-in,
single-CPU, finite in its logging and stops explicitly if its counter/tick
preconditions fail. Hardware description checks reject mismatched t6050 AIC,
timer routes and CPU topology; they do not claim physical delivery works.

Preserve boot025 and installed boot021 m1n1; only the new RAM Image changes.
Correct the verifier's historical provisioning hint to use the current stage.
Full build, sanitizer/controller/intake checks and exact-image generic VM pass
are prerequisites, not native compatibility evidence. M1 offline readiness and
human start authorize one filmed attempt 8 under the unchanged scope; no extra
M5 round trip, Recovery, volume/security/default change or automatic retry.
Post-attempt-7 policy JSON is already PASS. Use the new observations for a
root-cause fix, or advance to Linux control/input if userspace becomes stable.

## 2026-10-14 · Accept boot027 readiness with bounded diagnostic evidence

M1 independently passes archive-before-extraction, 13-file intake, reviewed
controller digests, all 90 cases and the unchanged clean client pin. Preserve
installed boot021 and earlier packages/results. Human reports proxy and phone
video ready; post-attempt-7 protection prerequisite is already PASS. Publish
readiness before one attempt 8. Capture new hardware/timer/deferred-work
checkpoints without inferring a root cause from a last line. No additional
blacklist, retry, reconnect or settings changes. Native/live NOT RUN at readiness.

## 2026-10-14 · Separate passing tick evidence from the next scheduling boundary

Attempt 8 directly observes counter PASS/25 ticks, J716c/t6050 EL2 and one CPU.
Final visible phase 1/timer status narrows the next investigation to before
phase 2, without proving preemption, watchdog or console failure. Preserve the
successful hardware/DAPF/descriptor checks. Diagnostic userspace/liveness is
unobserved, not a successful boot. Human confirms Macintosh HD return. The video
was recorded but not reviewed; report this limit explicitly. M5 performs
read-only return checks and offline analysis. No retry or wider blacklist.

## 2026-10-14 · Close the scheduling observation gap before another native attempt

Attempt 8 establishes native timer ticks but not a precise blocking PC. Exact
REA/LLVM/source show idle=nop is implemented and the diagnostic can reschedule
before its watchdog is armed. Do not redo the idle backport, add a blacklist,
change timer routing or claim a root-cause repair. Pre-arm the finite watchdog;
record scheduler boundaries without printk/locks using the existing framebuffer
mapping, plus one bounded watchdog stack. Keep source/byte provenance and
sanitizer/full-link/VM/controller/intake validation separate from native proof.

Boot028 replaces only the RAM Image. Preserve installed boot021 and the working
entry/controller/hardware checks. Post-attempt-8 original Full/lab Permissive
JSON already passed. M1 offline readiness plus human start suffice for one
filmed attempt 9; require literal strip/text evidence and a reviewed recording
or an explicit availability limitation. Return at the existing deadline. No
reinstall, security/volume/default change, repeated Stage A or automatic retry.
Stable native userspace is the next gate toward a Linux control channel and
Omarchy configuration, not a claim of desktop or efficiency parity.

## 2026-10-14 · Accept attempt-9 readiness and capture the scheduler strip

M1 independently verifies boot028 archive before extraction, all 13 files,
90 controller cases, reviewed source hashes and unchanged clean client pin.
Preserve prior packages and installed boot021. Human reports proxy and video
including bottom-left strip; protection prerequisite is already PASS. Publish
readiness before one attempt 9. Capture literal hex strip sequence, timer and
scheduler evidence, and review recording or report availability limits. Return
within the bound; no retry, expanded skip, reinstall or settings change.

## 2026-10-14 · Record phase-12 progress and unavailable strip without inferred lanes

Attempt 9 passes controller gates and reviewed video observes timer PASS/25
ticks, phases 1/10/11/12 and reschedule pending=1 strip=0. Do not invent P/S/W/H
values or a scheduler stack from an unavailable strip. Phase 13/userspace and
liveness remain unobserved. The source locates the next boundary around
preempt_enable; the evidence does not prove that call or a particular lock
is faulty. Human confirms Macintosh HD return. M5 owns read-only return
checks and offline scheduling/visibility/strip analysis; no retry or new skip.

## 2026-10-14 · Repair diagnostic lifecycle before interpreting a native scheduler stall

Attempt 9 has reviewed phase-12/pending=1/strip=0 evidence, not a blocking PC.
The actual old mapper reproduces a console-retirement skip. Make the diagnostic
mapping independent of console registration using only the validated DT range,
report preparation/mapping state, enlarge bounded glyphs and instrument actual
context-switch source boundaries. Keep all normal operations and gates. REA's
partial __switch_to output is explicitly incomplete; use full source/LLVM and
linked bytes to account for CPU-alternative paths. No guessed feature/register
changes or new driver blacklist. Map success requires native screen confirmation.

Boot029 changes only the RAM Image. Preserve installed boot021 and current lab
entry. Post-attempt-9 policies already PASS; do not ask for the same check again.
Full link/sanitizers/90-case controller/intake/VM tests pass; M1 independently
verifies private release and publishes readiness before one human-started filmed
attempt 10. No settings/volume changes, repeated Stage A, automatic retry or
extra M5 approval loop. Record literal strip/state/video evidence, return within
the bound, then select the next repair from observations. Native userspace and
Linux control/input remain prerequisites for the Omarchy configuration agent.

## 2026-10-14 · Accept boot029 readiness with independent display-state evidence

M1 verifies archive-before-extraction, 13-file intake, 90 controller cases,
reviewed hashes and unchanged clean pin. Human reports proxy and recording
including bottom-left edge; post-attempt-9 protection prerequisite already PASS.
Publish readiness before one attempt 10. Capture actual display-state and
literal enlarged strip values, review recording, and separate mapping from
visibility and diagnostic progress from boot success. Preserve installed setup
and earlier results; no retry, wider skip, reinstall or settings changes.

## 2026-10-14 · Use observed worker/probe boundaries without inventing an exact fault

Attempt 10 passes controller gates and reviewed video exposes P:05 S:09 W:04.
Three native strip lanes now visibly render. Decode these as first deferred-work
flush, scheduler exit and boundary before bus_probe_device; do not equate them
with an exact blocked driver/PC. Earlier phase-13 passage is a source-path
inference, not directly observed phase text. H is unobserved, not zero; blurred
small timer/display fields remain unconfirmed, with no values inherited from
prior attempts. Userspace/liveness remain unobserved. Human confirms Macintosh
HD return. M5 performs read-only return checks and offline probe/visibility
analysis next. Preserve the installed setup and all gates; no retry or new skip.

## 2026-10-14 · Identify the deferred device and operation before changing drivers

Attempt 10 exposes P:05 S:09 W:04, but no readable retry identity or heartbeat.
Use exact bus/platform REA plus source/linked bytes to separate framework work
from driver callbacks. Boot030 adds bounded operation markers and static public
DT indexes, with task gating and separate root/nested identity. Preserve all
original callbacks, locks, errors, work flushes and hardware checks; add no skip.
A compact four-row panel repaints saved lanes and marks heartbeat before printk.
It remains diagnostic overhead and non-atomic display evidence, not a fault PC.

Full build, actual helper/renderer/identity/platform/parser sanitizer tests,
90 controller cases/intake and exact-image generic VM liveness pass. Original
macOS policy remains Full and lab Permissive by fresh user JSON. Installed
boot021 and current entry remain. M1 offline readiness plus human start suffice
for one filmed attempt 11; no additional M5 approval loop or setup restart.
Record all readable lanes and video times through the stop criterion, decode
IDs offline, then return. Native userspace remains the gate before Linux-side
control/input and Omarchy configuration; no performance-parity claim.

## 2026-10-14 · Accept boot030 readiness and capture public device/probe boundaries

M1 independently verifies archive before extraction, 13-file intake, 90 cases,
reviewed controller/decoder hashes and clean pin. Human confirms proxy/video
including all four panel rows; post-attempt-10 policy prerequisite already PASS.
Publish readiness before one filmed attempt 11. Record literal lanes before
using the offline public-table decoder; preserve unreadable fields as unobserved.
Review early and final video within the existing stop bound. Preserve installed
boot021/gates/single skip; no retry, settings changes or inferred driver fault.

## 2026-10-14 · Preserve decoded probe identity and distinguish watchdog task context

Attempt 11 video/photo identifies final D=C=0059 / B=63 at the second pin-controller
platform callback boundary, while the first D=C=0057 instance returned 0. Follow
this device/operation evidence offline rather than guessing a driver skip.
Photo directly confirms phase 13, 25 timer ticks and two watchdog reports. The
first dump interrupted kdevtmpfs; later scheduler summary names kworker/u4:1.
Do not assign the first stack to the final callback or claim an exact fault.
Keep obscured lower frames unconfirmed and kernel heartbeats separate from
unobserved diagnostic userspace/liveness. Return was instructed at the bound;
confirmation remains pending. No retry/settings changes; fresh M5 return checks
and targeted offline analysis next. Preserve media locally and publish safe text.

## 2026-10-14 · Repair identified GPIO handoff gaps without treating a boundary as a fault PC

Attempt 11 identifies the main pinctrl platform callback, not an exact failing
instruction. Use exact Linux source/compiled REA plus independent Apple byte
observations to bound the hypothesis. Reject Apple's cross-boundary init
pseudocode; retain verified in-body instructions only as corroboration of the
public Linux register layout. Implement original t6050 cache geometry and
init_hw sequencing, using Linux IRQ-off semantics and checking readback rather
than overriding a locked pad. No blanket driver skip, new hardware routing or
proprietary code. Include stages that distinguish cache initialization from
registration and IRQ handoff if native still stalls. Tests cannot establish
that the synthetic pending source existed on this unit.

Post-attempt-11 protection/return PASS. Preserve boot021/current entry and all
prior evidence. Boot031 is a RAM Image update only. M1 offline readiness and
human start authorize one filmed attempt 12 under the unchanged stop/return
bounds; no extra approval round trip or repeated setup. Record GPIO errors
separately from userspace success. Native PID 1/liveness gates Linux control,
input and the configuration-agent Omarchy work; efficient SMP/GPU remain later.

## 2026-10-14 · Accept boot031 intake and bound attempt 12 to one filmed RAM launch

M1 independently verifies the archive before safe extraction, all 13 files,
90 offline cases, source/controller hashes and clean client pin. Human confirms
proxy running and recording; M5's return/protection prerequisite already PASS.
Publish readiness, then the reviewed launcher once. Record GPIO counts/errors
and public boundary values as observed, without treating an earlier boundary as
a proven fault. Stop at the existing bound and return. Installed boot021, gates
and fixed arguments remain; no retries, new blacklist or settings changes.

## 2026-10-14 · Narrow attempt 12 follow-up to the observed GPIO cache boundary

Boot031's first pin controller reports IRQ handoff 61/7/1 and successful return.
The final main-controller marker advances from prior B63 to B73 bounded cache
initialization. Investigate that exact operation offline; the marker is not a
blocked PC, proof of an IRQ storm, or evidence of an arbitrary driver to skip.
Preserve watchdog task context: the first dump is PID12/kworker/u4:0/device1,
while later device2 scheduling names PID38/kworker/u4:1. Do not assign the first
stack to the final main-controller cache operation.

Video/photo are reviewed, with literal final lanes and actual GPIO counts/return
recorded; the 40.163333s clip cannot establish full 120s coverage. Native userspace
and 60s liveness remain unobserved. Human confirms Macintosh HD return; M5's
fresh read-only policy/default review is pending. No retry/settings changes.

## 2026-10-14 · Respect firmware-excluded pins instead of scanning every declared register

Attempt 12 and independent REA/source evidence justify a narrow GPIO exclusion
repair. Translate the observed non-identifying pin list into the standard Linux
gpio-reserved-ranges property, not proprietary code. Validate geometry/list on
the live ADT before uploads and preserve exact packaged/effective DT checks.
Use explicit permitted defaults and a sparse cache; a readable predicate alone
is insufficient justification for retaining a contiguous raw-default scan.
Preserve GPIO numbers and reject forbidden GPIO/pinmux/IRQ operations. Refuse an
initially pending reserved IRQ before enabling parents; do not override pads.
Add a pin-index panel to make another stopped read actionable. Retain rejected
pseudocode limits; physical cause and successful repair remain unproven.

Full build/tests and generic liveness pass. Only Image and one Stage-B DT
property change. Post-attempt-12 return/policies PASS; no host settings changed.
M1's offline readiness plus human start suffice for one filmed attempt 13, then
return under the same bound. Preserve current boot021 entry and all previous
results. Native userspace comes before Linux control/agent configuration,
Omarchy, and separate GPU/SMP/efficiency validation.

## 2026-10-14 · Accept boot032 readiness and retain the indexed GPIO evidence

M1 independently verifies archive before extraction, 13-file intake, 102 cases,
reviewed hashes, clean pin and the exact one-property DT change. Human confirms
proxy and recording; post-attempt-12 protection prerequisite already PASS.
Publish readiness then invoke the documented launcher once, preserving the new
live GPIO gate. Capture literal I together with D/C/B and actual counts/errors;
no inferred pin fault from a boundary. Keep recording through the stop criterion,
then Macintosh HD. No extra approval loop, retry or settings/volume changes.

## 2026-10-14 · Separate attempt 13 heartbeat from GPIO and userspace progress

Boot032's controller GPIO contract passes, but native samples have W00 and
D/C0000/B00/I000 while P05 and H00 through H06 appear. Do not treat I000 as a
pin 0 failure, carry over prior GPIO success, or infer userspace from watchdog
updates. P05 narrows a source boundary, not an exact blocking PC; inspect
worker/scheduler/console progress offline. Preserve unreadable S/timer/phase
fields and absence of readable stack or GPIO counts. The 40.13s clip is partial
coverage; the still photo adds no duration. Return instructed; confirmation
pending, fresh policy/default not checked. Attempt consumed, no retry/settings
changes. Native userspace remains the gate for Linux control and Omarchy.

## 2026-10-14 · Remove scheduler rendering before adding more hardware changes

Attempt 13 shows changing kernel heartbeats but no attributed GPIO operation or
userspace. Exact source reveals full-panel repainting at scheduler checkpoints,
including locked/IRQ-disabled paths. Keep phase/PID/counters in RAM and sample
S from the existing watchdog. Verify actual hook state and linked instructions;
do not claim the unmeasured native stall is fixed. Preserve boot032 GPIO repair
and all hardware gates; only Image changes. Exact source answers this question,
so no additional proprietary decompilation or broad REA sweep is justified.

Post-return user policies and M5 read-only checks supersede pending return status.
No fresh policy exits supplied; default/installed object/authenticated-root not
rechecked. M1 readiness plus human start suffice for one filmed attempt 14.
Time the stop independently of media upload; no retry or settings changes.
Native userspace, control/input/RAM root and configuration agent precede Omarchy
and separate acceleration/SMP/power-efficiency validation. Claude follows
`native/boot/claude-workflow.md` with the same boundaries and evidence standards.

## 2026-10-14 · Accept boot033 readiness; record boot034 observation proposals

M1 independently verifies the archive before extraction, 13-file intake, 102
cases, reviewed controller hashes, clean pin and an Image-only payload delta.
The human reports the M5 proxy running; recording starts before the single
launch. M1 also records, at the user's request, proposals for M5: enable the
kernel's own stall detectors with panic output drawn without the workqueue,
and load the GPIO driver after PID 1. These are proposals; M5 owns boot034.
The m1n1 hypervisor needs m1n1 changes on t6050 and is deferred (study in
`research/m1n1/`). No retry, settings or volume changes.

## 2026-10-14 · Record attempt-14 native PID 1 and the silent reset; no retry

Attempt 14 proves native diagnostic userspace and the boot032 GPIO repair on
hardware, but the SoC resets about 5.6 s after PID 1 with no message. Record
the observed times, panel decode and GPIO counts literally. Treat the reset
trigger as unknown, with ranked hypotheses (PMGR sync_state power-off, ANS
mailbox/SART, idle path). The next native test should change one variable and
print genpd state and per-second heartbeats. Attempt consumed; no retry or
settings changes before M5 review and fresh instructions.

## 2026-10-14 · Attack the reset trigger natively before more hypervisor work

The hv002 session never got past the m1n1→m1n1 chainload, and the chainload is
not on the critical path for the reset question. Exact source answers the first
open attempt-14 hypothesis: genpd sync_state ignores `pd_ignore_unused` and
releases every unclaimed boot-on domain (152 of 188 here), which matches the one
5 ms late-init step and the 5.6 s delay. Test that single variable on the proven
native path (Image only), with a bounded one-domain-per-500 ms ladder after a
long stable window so a reset still names its domain. Do not claim the cause
until the native run; keep the hypervisor work as a parallel track.

## 2026-10-14 · Repair and instrument the chainload before more hypervisor work (hv003)

hv002's hypervisor change set has still never executed: its session stopped at
the m1n1→m1n1 chainload with a frozen restored logo and no USB device. Do not
guess at HV code. Change what differs from the field-proven Asahi stage-1→2
path and make the next failure describe itself: a padded-literal copy stub
(the stub's 64-bit entry literal sat at 4 mod 8 and runs with the MMU off),
SEPFW-only relocation with a 16-byte in-place ADT patch applied last and
reverted on failure, a `top_of_kernel_data` that never drops below the live
heap, a read-only layout gate, and a breadcrumb strip painted by the host, the
stub and 16 early m1n1 steps because the M5 has no reachable UART. Run it as a
ladder of separate human-started rungs (`--layout-only`, `--chainload-only`,
`--control stock`, then the full run) with a power cycle between them, and
stop at the first rung that fails. Keep the hv002 change set byte-identical.
Label the misaligned-literal explanation Likely, not confirmed; claim no
chainload or hypervisor progress until a rung passes on hardware. Close the
launcher's terminal echo of non-protocol target output (it carried the device
serial) in the same change.

## 2026-10-15 · Record attempt 15 as informative but confounded; recommend one clean rerun

Boot034 changed one variable and the attempt-14 reset at ~8.8 s did not recur, so
genpd's bulk sync_state power-off was the trigger of that reset. A second silent
reset at ~27.7 s during the release ladder cannot be attributed: the M1 host
kernel-panicked at the handoff and hard-reset in the same seconds, and the
controller record is incomplete. Report the three candidates (ladder step 6,
step 17, host USB reset) with their weaknesses and claim no culprit domain. A
host failure is not an experimental outcome, so one rerun of the unchanged
package on a freshly restarted M1 is the cheapest way to separate them; the
human and M5 decide. Film steadily and low so domain names stay readable.
Retract the earlier device-tree-order estimate of when display domains release.

## 2026-10-15 · Drop the SMC-owned power domains from the Stage-B DT (boot035)

Attempt 15 confirmed that Linux powering PMGR domains off can reset this SoC,
and both resets so far followed the release of an SMC-owned I2C master by the
same ≈ 5.6 s. Asahi never exposes `smc_*` domains, and nothing on t6050
consumes them. Remove the seven nodes from the Stage-B DT and change nothing
else, so attempt 16 tests one variable: if the ladder completes and Linux stays
up for 180 s, the remaining 145 unclaimed domains are safe to power off and the
project has its first stable, power-managed native baseline. Keep the boot034
kernel (sync_state fix, trace and ladder) for attribution. Do not claim the SMC
mechanism until attempt 16 or the PMGR probe shows it. Leave the
framebuffer-domain claim and the M1 launcher's tty mitigation for later
handoffs, because each would add a second variable or change a reviewed
controller digest.

## 2026-10-15 · Adopt the SMC-less Stage-B DT as the native baseline; leave attribution open

Attempt 16 (boot035) shows Linux releasing 74 boot-on unclaimed domains one at a time
and staying alive past 108 s with PID 1, one CPU and the 60 s milestone. Treat the DT
without the seven SMC-owned `smc_i2cm` nodes as the baseline and carry the removal into
the t6050 DT draft. The step-17 explanation for attempt 15 is refuted. Whether the SMC
domains or the M1's post-panic reset caused attempt 15's second reset is not separated,
because this run changed both; do not claim a proven mechanism. A boot034 rerun without
an M1 panic or a single-domain proxy probe would separate them, at low practical value.
The next gates are a Linux control channel and RAM root, then SMP, idle and DVFS, each
with its own evidence. No parity or efficiency claim.

## 2026-10-15 · USB control channel: a CDC-EEM gadget on the PHY state m1n1 leaves (boot036)

Build the control channel without a Linux Type-C PHY driver. The parts:

* three plain `snps,dwc3` device-mode cores at high speed;
* DMA through DART instance 1 with stream 1, exactly what m1n1's own gadget
  uses on this Mac;
* every ATC 0–2 power domain disabled, so Linux neither arms AUTO_ENABLE on
  them nor releases them;
* the gadget stack built into the Image (the Stage-B initramfs carries no
  modules).

The function is CDC-EEM, not NCM or ECM. EEM uses bulk endpoints only, the
ports flag `ncm-interrupt-ep-disabled`, omarchy-m5 saw NCM stall on its
interrupt endpoint, and macOS 26.6.2 has an EEM driver. Addresses are IPv6
link-local only with fixed locally administered MACs, so nothing on the M1 is
configured or routed. Root logs in by key only; host keys are made in RAM.

Alternatives kept as fallbacks, one variable at a time: both DART instances
(Asahi's layout; the USB-DT side session's candidate) and NCM.

Consequences:

* the link is USB 2.0 only, and nothing can bring the PHY back after a
  suspend (the quirks keep it from suspending);
* boot036 runs only after attempt 16 gives a stable baseline;
* the SSH key is the user's decision (`blockers.md`).

## 2026-10-15 · boot036 authorizes the M1's own key; kernel builds are reproducible

The M1 generated its own ed25519 key and committed only the public half
(`a6717b0`), so the private half never leaves the controller. The shipped
initramfs authorizes exactly that key, and the packager checks it. The VM
self-test cannot use that key, so its overlay authorizes a separate test key;
the overlay is never shipped.

Kernel jobs pin `KBUILD_BUILD_TIMESTAMP`, `KBUILD_BUILD_USER` and
`KBUILD_BUILD_HOST`, so a rebuild gives the same Image. Without that, every
rebuild changed the Image digest, and the RAM root (whose modules and checks
pin one kernel) could not follow boot036's kernel.

## 2026-10-16 · Do not patch the E1 probe on the M1; stop and hand the fix to M5

The E1 probe stopped on its first live step with a NameError raised before the serial
port was opened, so no request reached the M5. The approval covers the reviewed probe and
the procedure says stop on any STOP line, so the M1 neither edits M5-owned code nor
retries. M5 fixes this and the same pattern in the PMGR probe and adds an offline test
that builds the live API object. A rerun needs M5's patch, the M1's fresh offline
verification and the human's go. Offline unit tests with fake transports did not cover
this path, so each new live tool needs a test that executes its wiring with the real
imports.

## 2026-10-16 · Keep the boot036 USB baseline; change only the gadget function

Attempt 17 shows Linux device-mode USB working on the M5's dwc3 cores and the host enumerating the
gadget, so keep the three controllers, DART mapping, ATC-domain exclusion and key-only SSH. macOS 26.0.1
cannot bind CDC-EEM on this M1 (the kext is not in the kernel collection), so only the function type
changes: ECM, NCM or ACM serial, each of which macOS binds today. The M1's earlier kext check was
insufficient; intake must confirm loaded or available state with kmutil, not only the stub plist. Resolve
the interrupt-endpoint question before choosing ECM or NCM. No parity, input or performance claim.

## 2026-10-16 · Control channel: CDC-ACM log port + CDC-ECM, after attempt 17

Attempt 17 showed the hardware side of boot036's USB link works and that the
M1's macOS cannot bind CDC-EEM. Change only the gadget's functions: a CDC-ACM
serial port that the M5 writes its kernel log to and never reads, so the M1
gets `dmesg` with no network at all, plus CDC-ECM for the network and key-only
SSH. Both macOS drivers are loaded on the M1. Both functions use an
interrupt-IN notification endpoint, which the ADT flags for Apple's NCM and
which m1n1 never transmits on; attempt 18 therefore tests that endpoint, and
the serial port's silence or output answers it even if ECM fails. Keep Image,
config, DT, m1n1 and launcher byte-identical to boot036 so the attempt changes
one variable. The RAM root is asked to default to ECM for the same reason.

## 2026-10-16 · Probes: alias function-local imports before a class body uses them

The E1 probe stopped before any device contact because a class body assigned
`M1N1Proxy = staticmethod(M1N1Proxy)` with `M1N1Proxy` imported in the
enclosing function; a class body resolves such a name in class, global and
builtin scope only. Alias the import first, and test the live wiring by
building the API through `connect_and_run` with stub m1n1 modules, so a
regression fails offline rather than in the lab.

## 2026-10-16 · M1: read the ACM log port with a reader that never writes

The gadget's serial port keeps the default line discipline with ECHO on, so a
host terminal that echoes would write every received log line back to the M5 and
get it echoed again. The M1 therefore reads the port with a small tool instead of
plain `cat`: `O_RDONLY`, no writes, terminal flags read first and local echo
cleared only if it is on. A pty test shows the difference (plain `cat` with echo on
wrote 130 bytes back; the tool wrote 0). macOS's default on an unrelated serial
port was raw with echo off, so the guard may be unneeded; it costs nothing. The
driver report uses the registry (`ioreg`), which opens no port. Nothing the
checklist touches changes.

## 2026-10-16 · Boot the Omarchy desktop on boot035 before the USB link works

Attempt 18 showed the USB link's problem lies in the gadget's control endpoint
after configuration, and Linux itself kept running. The RAM root reaches the M5
through the m1n1 proxy before Linux starts, so the desktop does not need the
link. Boot it on the boot035 package, attempt 16's proven kernel and DT with no
USB controllers, so the only new variable is userspace. The video is the only
evidence this time. The control channel continues as its own candidate
(boot039, bulk-only), and the RAM root moves to the newer kernel once the link
works.

## 2026-10-16 · Make the repository public

The first native desktop is the milestone the user wanted on record before
opening the project. The audit found nothing that the host-protection rules
forbid (no identifiers, keys, media, images or decompiled code in any pushed
revision), so the same remote is made public rather than a fresh copy, keeping
the history and the Releases that the attempt reports cite. From now on every
push is public at once: documents are written for outside readers, the
RAM-root image and the second Mac's private key never enter Git, and the
project's framing is fixed in the README: unaffiliated with Apple, Asahi Linux
and Omarchy; AI-assisted; a work in progress whose goal is parity with native
macOS on this machine, with no performance claim until it is measured.

## 2026-10-16 · Decompile freely, publish only original work

The user's position: decompiling this Mac's macOS drivers with REA is a major
accelerator and should continue, while the published code needs to contain no
decompiled code, only what works. This is the clean-room split the project was
already following: REA output stays in the ignored `build/` tree; findings in
Git are specifications (addresses, sequences, formats, timings, each with its
evidence and confidence); Linux drivers are original code written from them,
ideally by a session that does not open the decompiler. The split matters more
now that the repository and its Releases are public: a compiled kernel image is
distribution, and a driver derived from Apple's code could neither meet the
kernel's GPL nor ever be shared. A driver written from a specification can be
published later. Recorded in `AGENTS.md` (Conventions) so every session
follows it. Not legal advice; Apple's licence terms, which restrict reverse
engineering except where the law permits, are a contract question separate from
copyright.

## 2026-10-18 · Change the launcher for the installer-built Omarchy root

The reviewed launcher had not changed since attempt 18, and every handoff pins its digest. The
root Omarchy's own installer builds is 2.34 GB, which the proxy client's default 1 GiB heap
refuses before a byte is written and which needs about 7.5 minutes of upload against a 300 s
deadline. Shrinking the root to fit would drop Chromium, LibreOffice and the agent tools and make
it Omarchy-style again, so the launcher changes instead, in the smallest way: a third profile with
a 3 GiB heap, a 900 s deadline, its own confirmation and its own pin, while the two existing
profiles are shown by test to behave exactly as the committed launcher did. The user approved the
change on 2026-10-17 and the handoff on 2026-10-18. The risk the heap adds is where 2.39 GB lands
in the M5's RAM relative to live carveouts, which only the native run can answer; the checklist
reads m1n1's heap and memory lines from the video and treats a reset during the upload as that
evidence. A two-stage delivery over the USB link remains the plan once that link works.

## 2026-10-18 · Passwordless sudo for the desktop user in the lab Omarchy image

Agents running inside Omarchy on the M5 need root for package installs, loading modules and
driver work, and the RAM-root image's desktop user has no password, because there is no keyboard to
type one. The user approved passwordless sudo for `omarchy` in this lab image on 2026-10-18,
confirming it directly in the session that builds the image. It uses Omarchy's own permanent grant,
`/etc/sudoers.d/99-omarchy-permanent-nopasswd-1000`, as `omarchy-sudo-passwordless permanent`
writes it, so Omarchy's bar shows its indicator and its own `--disable` revokes it for the rest of a
boot. The image lives only in RAM, is offline except through the M1's relay, and accepts only the
M1's key over SSH. Nothing grants root to any other account. Recorded as deviation 24 of job 045.

## 2026-10-19 · Attempt 26 is keyboard-only; read-only storage waits for a reviewed launcher change

The launcher refuses any Stage-B device tree whose NVMe node, or any of its three cpufreq
controllers, is not `status = "disabled"` (`check_stage_b` in `native/boot/fdt.py`). The check runs
on the package's tree, on the tree m1n1 prepares and in `make-package.py`, and it is what keeps
Linux's storage driver from binding to the internal SSD in a launcher-driven boot. Attempt 26 was
first scoped as keyboard plus read-only storage, which a tree with storage disabled cannot deliver.

The user decided on 2026-10-19 that attempt 26 is keyboard-only and that storage follows as attempt
27 behind a separate launcher change that the user reviews before it is applied. The recommendation
the user accepted: a keyboard problem then cannot be mistaken for a storage-controller problem, the
NVMe controller has never run natively, and loosening a safety guard is not bundled into another
attempt. Until the user approves that change, every shipped Stage-B tree keeps the NVMe node and
the cpufreq controllers disabled, and the committed launcher stays byte-identical so every
handoff's digest pins hold. Storage is prepared in full offline (modules, a write refusal in
nvme-core, a virtual-disk test, a read-only load script) and kept out of the attempt-26 package.

## 2026-10-19 · Attempt 27 is the two-stage boot with attempt 26's fixes; read-only storage moves to attempt 28; the CPU track starts offline

Attempt 26 switched the M5's keyboard on and ran for 63 minutes with no fault, and it measured
where the slowness is: one core, at the speed state the firmware left it in, draws the 3456×2160
screen in software at about 0.47 s per update, which is also why the terminal repeated letters (the
key release waited behind a frame longer than the 250 ms repeat delay). The keyboard path itself is
clean. The user accepted on 2026-10-19 the order below, chosen so that every later attempt costs as
little as possible and the real limit, the CPU, is worked on at once:

* **Attempt 27 = the two-stage boot** (VM job 049: a 60 MB stage one through m1n1, the Omarchy root
  over the USB link at the link's speed instead of m1n1's, about 2 minutes of transfer instead of 8)
  **with the attempt-26 fixes in the Omarchy root** (repeat delay 1000 ms, the leaked menu pollers,
  the keyboard switched on at boot by the proven steps, the idle sshd noise). No new hardware step:
  the keyboard path ran in attempt 26 and the delivery change is in software; the gadget's second
  bind on the same controller after the switch is the one thing the VM could not exercise.
* **Attempt 28 = read-only storage**, behind the launcher change the user reviews (design in
  `build/launcher-ro-storage/REVIEW.md`), unchanged in substance from the 2026-10-19 decision above,
  one attempt later. The first native use of the SSD controller stays its own attempt.
* **The CPU track starts now, offline, in parallel:** frequency scaling for the boot core (the
  device-tree nodes exist and are disabled; the launcher's guard refuses them enabled, as it refuses
  NVMe, so it needs its own reviewed allowance), and the facts on how macOS starts the other 17 cores
  (m1n1 cannot start them on this chip; cause unknown), from this Mac's own binaries under the
  decompile-freely rule. Neither touches the launcher or runs on hardware until reviewed.
* **Deferred:** the trackpad, the M5's own network, the desktop's drawing cost beyond cheap runtime
  tests, and the five early boot lines (harmless until the GPU).

The agent over SSH works today and does not need the desktop; it shares the slow core, so heavy
work on the M5 waits for the CPU track. The desktop stays slow until that track lands.

### Continuation review, 2026-10-19: evidence limits and completion

The resumed work retains the attempt ordering above. Job045's new root passed
its exact-kernel VM desktop/link checks; job051's experimental CPU module passed
compilation, sanitizer and narrow DT/schema checks; SMP behavior findings are
written. Work is uncommitted, as requested in the main-agent handoff. Results,
pins and unresolved issues are in `native/boot/subagent-review-2026-10-19.md`.
The next integration step is a new stage-one/root pairing and repeated job049
tests before the attempt-27 handoff; old tests name the preceding root.

Several earlier statements need qualification. The CPU's actual clock is
unmeasured; requested state is not clock telemetry. Frequency scaling and SMP
are worthwhile but cannot be assumed to remove serialized rendering costs or
replace GPU/display support. Automatic keyboard loading changes timing from
the successful manual path and must be checked natively. Early power-domain
and timer errors have unresolved effects, not an established harmless status.
Transfer-time estimates are not full-size native two-stage measurements.
No proprietary binaries or raw REA output are added to public artifacts.


### Attempt-27 integration, 2026-10-19: exact pair, bounded first native switch

The new root and rebuilt stage one passed job049's full failure/switch test and
an independent normal-path boot. Both manifest records move together; the M1
checks their agreement with the stage-one embedded pin before any launch.
Existing launcher/boot042/boot021 pins are unchanged. Native tests remain NOT RUN.

For the first native two-stage boot, the checklist permits one image send and
records a failed switch or missing second USB link without automatic retries
or driver repair. The deliberate bad transfers remain VM-only checks. This
keeps the first native transition attributable and bounded; it does not remove
the receiver's tested recovery behavior. Automatic keyboard loading is also
observed explicitly because its timing differs from attempt 26's manual path.

Publish only reviewed source, sanitized findings and image hashes after the
user's commit review. Private images are transferred directly to the M1; no new
GitHub release is required. Inherited kernel-config/compositing experiments
(jobs047/048) are outside the publication scope. Exact evidence and scope:
`native/boot/attempt27-two-stage-validation.md`.


### 2026-10-20 · Publication approved; M1 intake precedes the restart for attempt 27

The user approved committing the reviewed handoff, pushing it to the existing
public repository, and keeping offline CPU/SMP work in a separate commit.
Images remain private. This closes the commit-review gate recorded above.

The M1 first pulls and verifies the handoff, boot042 and both privately
transferred images. After offline readiness, use the established fresh-M1-
restart/cable-reseat procedure before the next human-started attempt. Keep the
M5 in macOS while intake is pending. Native attempt 27/live checks remain
NOT RUN; no policy, volume, firmware or bootloader change is authorized here.

### 2026-10-20 · M1 accepts the verified pair while retaining test failures and coverage limits

Both privately transferred files equal the public pair pins, including the
embedded root/kernel/count/size metadata; boot042 and the launcher remain
unchanged. Record offline readiness without a live launch. Preserve initial
test failures: the stale source-label spacing assertion is corrected, and the
known USB test close race is made deterministic by waiting for device EOF
before closing SSH stdin. Neither changes production transport or launcher.
Two absent legacy fixtures remain skipped; macOS sshd cases are handshake-only.
The system LibreSSL TLS handshake fails without the proxy too; the unchanged
proxy suite passes under the existing bundled OpenSSL runtime. No host install
or TLS-verification relaxation. Native readiness still requires the fresh M1
restart/cable/unlocked procedure, fresh read-only M5 protection/default check
and human start. Keep CPU/SMP/storage work separate from the two-stage delivery.


### 2026-10-20 · Omit repeated routine boot-policy checks

The user explicitly declines another routine security-policy check, citing the
many prior original Full/lab Permissive results. The user also confirms that
the M1 has restarted. This supersedes the repeated policy-check prerequisites
in earlier handoffs for this attempt; the M1 agent must not block or ask again
for them. No fresh result is claimed, and no boot policy/default/volume change
is made. M1's independent image/package verification remains complete and the
normal launcher identity/DT/integrity checks remain intact.

The human may now select the existing iLinux Boot Lab entry and wait at
`Running proxy...`; the M1 follows the one-attempt checklist. Native attempt
27 and live outcomes are still NOT RUN until the actual launch and observations.


### 2026-10-20 · Consume attempt 27 without bundling a desktop-performance experiment

The one authorized native two-stage boot and one image send succeeded, with
USB returning after the RAM-root switch and automatic keyboard/rerun passing.
The human reports clean `omarchy` text but application opening remains very
slow. Keep delivery/image results separate from desktop performance: no CPU
frequency, SMP, storage, GPU, render-setting or agent-login experiment was added.
Menu cleanup remains unconfirmed without its after snapshot. Preserve stage-one
sshd noise, failed units and teardown warnings for M5 review.

The human returned to Macintosh HD; fresh routine policy verification was
omitted as already directed, with no new protection/default claim. Controller
key-parser/dependency error and roughly one-minute desktop-window overrun are
reported explicitly; future collection needs checked prerequisites and an
independent deadline. One launch/send consumed, no retry authorized by success.
Evidence: `native/boot/stage-b-2026-10-20-attempt27-result.md`.

### 2026-10-20 · Prioritize a usable CPU, independent Wi-Fi and persistent storage

The user's post-attempt-27 direction makes these the acceptance targets before
moving their main development/REA workflow into native Omarchy. Retain
macOS-class measured performance and efficiency as the goal; an agent login,
clean typing or a core count alone does not satisfy it. Include graphics latency
because the software renderer directly affects responsiveness and CPU energy.

Prepare the bounded CPU-frequency baseline/experiment first, using the existing
offline-tested candidate. This proposed attempt-28 scope supersedes the old
storage-attempt-28 ordering; it does not authorize live DVFS or change a launcher.
Keep SMP entry diagnostics, N1 transport work and read-only storage preparation
separate, and select later attempts by evidence/readiness. Do not copy the
macOS SPTM sequence or assume a mask-only change enables secondary cores.

Distinguish persistent Linux storage from reading encrypted macOS volumes.
Stage selected authorized research inputs privately; public Git receives only
permitted findings and original implementation. Preserve the existing entry,
original macOS and waiver of repeated routine policy checks. Current plan:
`native/boot/post-attempt27-plan-2026-10-20.md`. No new boot package, hardware
test, partition/write target or native installation is approved by this review.


### 2026-10-20 · Attempt 28 observes CPU state before selecting a frequency increase

The user authorized the CPU experiment, offline tests and M1 handoff push.
Package the first no-write stage of the post-attempt-27 plan: actual boot-core
identity, requested command/OPP mapping, short independent CPU/memory work and
available thermal observations. Current mapping and monitoring are not yet
native-validated, so no defensible live frequency cap is selected in this run.
Do not let historical assumptions about a low clock determine the answer.

Use a separate `cpu-observe` profile with exact DT/Image/stage-one pins,
prepared-tree controller/OPP validation and fixed userspace governor selected
before registration. Preserve the working one-core/two-stage/keyboard/USB path,
idle restrictions and disabled NVMe. The explicit-load module has immutable
writes=false/cap=0. No DVFS/voltage write, module reload, secondary startup,
storage probe or desktop-setting experiment is added. Unknown policy state is
an informative diagnostic outcome; a command value is not an actual clock.

The next handoff also fixes attempt27's collection mistakes: verify stage two's
unique journal key before observation SSH, enforce one monotonic deadline with
remote and local process bounds, and require a human-visible return timer.
Keep native/live NOT RUN until the human starts after M1 offline intake.
No repeat boot-policy check, original macOS/settings change, raw-data upload
or proprietary code publication. Exact scope: `tools/m1n1-client/attempt28-instructions.md`.


### 2026-10-20 · M1 accepts attempt-28 offline readiness without claiming a native clock

The published pair, embedded CPU asset manifest, boot042 package, source pins
and requested independent M1 tests pass; retain two absent old-profile fixtures
as skips. Current CPU-profile exact-payload/fake-handoff tests executed. Keep
M5's earlier VM harness failure and fresh normal-path pass distinct from these
M1 results and from native module initialization. No source repair or live
request was made during intake. Evidence:
`native/boot/attempt28-m1-offline-2026-10-20.md`.

Stop at offline readiness: attempts/sends zero, live checks NOT RUN, no real
observation window armed. The one human-started observation keeps immutable
writes=false/cap=0, checked root key before collection and the fixed switch-time
deadline/human return timer. Unknown OPP or absent telemetry permits no added
experiment. Waived routine policy rechecks remain waived; no restart or boot/
security/volume change is implied by readiness publication.


### 2026-10-20 · Keep memory in the post-attempt-28 diagnosis; no automatic frequency increase

Attempt 28 initializes the no-write CPU policy and observes command p-state 6
mapped to 2.652 GHz, agreeing with a short 2.650/2.651 GHz dependent-ADD estimate
under its stated assumption. The user still finds application response unusable,
with accurate typing, and explicitly asks the M5 agent to consider memory.
Preserve the new cache/working-set chase data as native evidence; do not compare
its roughly 332–337 ns larger-working-set result directly with the older
attempt-20 protocol or attribute GUI latency without a matched baseline.

No thermal/energy/power telemetry is available. Policy initialization does not
select or authorize a frequency cap/transition. Memory/cache/translation and
software rendering remain separate investigation targets alongside CPU state;
M5 reviews the data offline before choosing the next scope. One boot/send/load,
no retry, no frequency/voltage/settings/storage/SMP action. Human return was
within +560/600 s; no deadline extension. Exact evidence:
`native/boot/stage-b-2026-10-20-attempt28-result.md`.


### 2026-10-20 · Attempt29 tests memory locality/translation before choosing a hardware clock change

The user requests continued REA and execution of the next-attempt plan after
M1's successful attempt28 observation, including memory as a slowness factor.
Keep the functioning two-stage boot and add one small verified RAM-only bundle.
Inspect architectural cache/table-walk attributes and a locked loader stack PTE;
compare global/page-local access and per-allocation base/huge advice while
recording backing, faults, context switches and CPU-placement boundaries.

REA's DCS path is separate from CPU DVFS, but rejected whole-function pseudocode
and unresolved mapping cannot justify a memory-controller register poke. The
macOS QoS controls also show why a single default-OS number is not a matched
comparison. No frequency, voltage, memory-controller, global VM or rendering
change is selected; no thermal headroom or performance gain is claimed.

Use a distinct memory-observe confirmation and fixed600s return window, one
explicit read-only architectural module load and no CPU28 module load. M1
intake/human start precedes execution. Preserve original macOS, boot/security/
volume settings and the waived routine-policy checks. Public Git contains only
original code, sanitized evidence and behavioral REA findings; private inputs,
images and the VM-only identity-bypass control remain excluded.


### 2026-10-20 · Accept M1 attempt29 offline intake while preserving native unknowns

The supplied small bundle equals the published hash; all four regular members
and embedded asset hashes verify, with collector source byte-identical to Git.
Retained attempt28 pair, boot042, all30 source pins and helper/key checks pass;
106 requested M1 methods pass, two absent legacy fixtures remain skipped.
No code/test repair, extraction/execution of the archive or live connection
was needed. M5's separate VM/macOS/REA claims and retained failures are not
relabeled as independently repeated M1 or native results.

Stop at readiness: launches/root sends/bundle sends zero, no real window armed.
The later human-started run permits architectural observation and local
allocation advice only; CPU28 remains unloaded, no clock/controller/global VM
or settings change. A hint is not huge backing and a page-local result is not
pure TLB attribution. Preserve fixed600s return and waived routine policy checks.
Evidence: `native/boot/attempt29-m1-offline-2026-10-20.md`.


### 2026-10-20 · Consume attempt29; normal sampled attributes and huge backing do not identify desktop causality

**Attempt29 consumed: one native memory-observation boot/root send/bundle load PASS.**
Execution `41e34a6`; final `MEMORY_OBSERVED`, no frequency or global VM writes,
CPU28 module unloaded, one CPU. Sampled MMU/cache/stack attributes normal;
32/128 MiB huge-advice allocations report full huge backing. Global-random
base/huge medians 335.221/331.144 ns and 350.004/339.354 ns; page-local about 90–95 ns.
All 48 samples retained with backing/fault/switch/placement counters; no matched
macOS or desktop-causality claim. CPU estimate 2.651/2.649 GHz, no thermal/energy
telemetry. Human: accurate typing, massive application delay remains; zero menu
pollers before/after. No kernel fault or M1 panic observed. Macintosh HD return
confirmed at +321.424/600 s; owned processes ended. No retry, settings, policy,
volume, frequency/controller/global-VM, SMP, Wi-Fi or storage operation. Routine
policy checks waived; last reported Full/Permissive/default retained. Evidence:
`native/boot/stage-b-2026-10-20-attempt29-result.md`; full sanitized 48-sample data:
`native/boot/attempt29/native-observation.json`.

The human authorized the one filmed run after readiness. Reused pair/boot042
and explicit architectural bundle completed without loading CPU28. The page-
local layout changes cache and translation locality together; AnonHugePages
is measured backing, not proof of a hardware-TLB mechanism. Preserve all 48 rows
and clock/QoS/compiler/thermal limits. No global THP or clock change is selected.
M5 reviews offline before proposing any controlled follow-up, SMP/core or
renderer work. Keep the existing installed entry, original macOS and waived
routine policy checks. No automatic retry or additional setup.


### 2026-10-20 · Attempt30 attributes GUI stalls before changing CPU or rendering policy

The user requests investigation, REA and execution of an attempt30 plan after
accurate but severely delayed typing/application use. Preserve the working
native image pair. Attempt29's sampled cacheability and huge backing did not
identify a memory-controller fault; one M core/software rendering remain.

Three CPU-policy REA entries distinguish work-interval feedback, performance
requests and scheduler preferences. Two rejected decompilations are excluded
from implementation evidence beyond independently verified bounded call facts.
Original Linux instrumentation measures compositor CPU time, frame callbacks,
main-thread software CPU samples and IPC response during controls and human use.
It does not copy Apple policy, write hardware registers or claim equivalence.

A preliminary VM color-management A/B showed no useful gain, so that proposed
setting change is dropped. Exact-root VM callbacks differ sharply between tiny
and full damage, supporting native causal observation without relabeling VM
results as hardware performance. All samples/outliers and limits are retained.

Choose a distinct desktop-latency profile, one RAM-only 163,840-byte bundle and
fixed 600s return window. No CPU28/memory29 module, renderer, idle, DVFS, extra
core, storage, Wi-Fi, security or volume change. M1 verifies offline then the
human starts the existing Boot Lab entry. Routine policy checks remain waived.
Stop after this observation; follow the README outcome table for the next
change. No native speedup or power/thermal/parity claim is established today.


### 2026-10-20 · Accept attempt30 M1 intake without promising a desktop fix

M1 pulled **`cfebfb7`**, verified the 163,840-byte desktop30 bundle
(`26a36600…1f07`), all four regular members, asset manifest and byte-identical
collector source without extraction/execution. Retained attempt28 images freshly
rehashed with embedded pins PASS; boot042 thirteen files and all 37 source pins
PASS. Desktop-latency eight-line offline launcher and root sender dry-run PASS;
clean client `57a9339`, eleven helper pins, SSH config/operator key and fresh
no-forwarding config checks PASS. **127 methods PASS / 2 absent legacy-fixture
SKIPS**, no source/test repairs. Native/live/latency NOT RUN; launches/root/
bundle sends 0 and no real window armed. Human confirms M1 restart and proxy,
cable/power/unlocked/lid/recording/timer. One new authorized run follows this
published readiness; no earlier collector replay or module/settings operation.
Evidence: `native/boot/attempt30-m1-offline-2026-10-20.md`.

Preserve sampler-unavailable errors and partial phases. Callback is not photon
latency, process CPU covers all compositor threads, and the software sampler
covers only its main thread. No automatic retry or renderer/clock policy change.


### 2026-10-20 · Consume attempt30; profile the expensive draw path before selecting a policy change

**Attempt30 consumed: one native desktop-latency boot/root send/userspace
bundle delivery PASS**, final `LATENCY_OBSERVED`; no frequency/renderer changes
or CPU/memory module load. Execution `6e49687`. Two 20-callback controls:
small medians 256.940/256.346 ms, full 513.491/516.029 ms; compositor process near 97%
CPU, IPC medians 407.639/407.789 ms. Software main-thread samples mostly anonymous
executable, not yet attributed to LLVM/Mesa; lost 0, unmapped retained. All 40
callbacks including warm-ups and 414 IPC samples preserved. Human reports
prompt cue, accurate typing, delay remains; individual action times unlogged.
Clock estimate 2.651/2.650 GHz; no thermal/energy data. No kernel fault/M1 panic
observed. Macintosh HD return confirmed +223.531/600 s; owned processes ended.
No retry, settings, policy/default/volume, hardware, SMP, storage or Wi-Fi change;
routine checks waived. Restart is human-reported; measured M1 reader uptime
20,933 s does not independently establish freshness. Evidence and timing limits:
`native/boot/stage-b-2026-10-20-attempt30-result.md`; full sanitized samples:
`native/boot/attempt30/native-observation.json`.

Both tiny and full controls are slow natively, unlike calling the VM tiny case
a native fast path. Keep all warm-ups/outliers and long-tail human IPC. Main-
thread anonymous mappings are not proven rasterizer code; precise action and
presentation timing remain open. No blind renderer/clock change, extra core,
retry or additional setup. Preserve Macintosh HD, installed entry and waiver
of routine policy checks. M5 reviews offline before a separately scoped run.


### 2026-10-21 · Attempt31: remove verified redundant drawing before changing CPU policy

Attempt30's controlled workloads saturate the compositor on one CPU, while
clock estimates remain near 2.65 GHz. Select an original, narrow framebuffer-copy
optimization with byte-equality and fallback evidence. Keep color settings,
input, login, kernel, CPU topology and clock behavior unchanged. Reuse validated
REA behavioral facts; public Hyprland source answers this immediate question.
The measured VM gain supports a native experiment, not a parity claim.

Ship a newly pinned pair derived from attempt28. The compositor is default off;
a single bounded off/on/on/off crossover and 45s human phase enable it temporarily.
Both the main collector and independent ExecStopPost reset the original draw
path, with M1 checking both receipts. Package metadata remains that of the base
root; executable hashes identify the custom build. Reject the earlier idea of
restarting an obsolete custom desktop service absent from the retained root.
No native installation or persistent setting change occurs.

Keep full-pair transport validation separate from3456x2160 headless copy tests,
callbacks separate from visible presentation, and process CPU separate from
energy. Correct the earlier inference about Aquamarine warnings; do not discard
failed harness runs or cherry-pick startup-contaminated timings. M1 verifies
both new images and publishes readiness before human start. No routine policy
check or additional boot/security/volume action. SMP, thermal/frequency, GPU,
Wi-Fi and storage remain on the detailed plan after this bounded experiment.


### 2026-10-21 · Hold copy-only 31; account for the full menu/input delay

Do not restart, launch attempt31, send its root or run its collector. The user
rejects the copy-only proposal as insufficient for the reported3–5s menu/input
delay. Code/images and offline results remain useful but are not the next boot.
Read `native/boot/attempt31/hold-and-replan.md`: trace input-to-visible-action
latency and establish CPU/memory/software-rendering baselines first. No new
native experiment is ready. Existing macOS/boot settings and waived routine
policy checks remain unchanged. This notice supersedes earlier readiness text.

The attempt26 keyboard timestamp evidence points downstream without excluding
firmware latency. Memory attributes and a CPU clock estimate do not prove full
bandwidth or CPU functionality. Trace the original path and compare identical
CPU/memory/software-rendering work before selecting another native change.
Preserve the optional copy optimization without presenting its VM25% result as
a fix for seconds of user-visible latency. No revised native trial is scheduled.

### 2026-10-21 · Follow measured rendering occupancy; retain native hold

The revised diagnostic implements event-loop timing, buffer-commit correlation,
original CPU/RAM/pixel references and separate observer/drain controls. VM
terminal delay is dominated by render-loop occupancy; draining identifies
scene work as larger than the final pass. Threaded-renderer VM sensitivity
shows a much larger improvement than a final-copy-only change. Prioritize
native SMP with measured renderer threading and G17 interface validation.
Native CPU/memory measurements and physical input/presentation timing still
need a separately reviewed boot. Keep attempt31 held; do not relabel VM
results as native fixes or lower visual quality as a parity claim. See
`native/boot/attempt31/diagnosis/README.md`.

### 2026-10-21 · Establish raw reset entry before native SMP deployment

2026-10-21. User authorized native SMP and renderer-threading development.
Original guarded single-secondary startup candidate fully linked in the VM;
14 actual-function cases PASS both normally and under ASan/UBSan.11 census
and8 renderer tests PASS; real pinned ADT parser checks PASS. Linux two-CPU
shared-payload/futex smoke PASS for2,000 rounds. All are offline/VM evidence.
Fresh REA verified53 PMGR instruction words; cross-boundary pseudocode rejected.

New renderer policy uses online CPUs intersected with process affinity, cap4.
At identical3456x2160 pixels, two-CPU VM control terminal first-buffer delays
685–754ms became37–41ms with one configured worker; full callbacks221→216ms.
Six CPUs/four workers gave59ms full callbacks. Neither physical presentation,
native CPU functionality nor energy/parity is established. Code/evidence:
`kernel/experiments/smp31/README.md`, `validation.json`, and
`native/boot/attempt31/smp-vm-results.json`.

**Next authorized live step is census31A only.** M1 reads
`tools/m1n1-client/attempt31-smp-instructions.md`, verifies offline, publishes
readiness, then waits for human restart to the existing Running proxy entry.
Two guarded RVBAR reads, no CPU start, Linux launch, chainload, hardware write,
new image transfer or security/volume/default change; then return to Macintosh
HD. Reset-target/entry remains unknown. Even matching mirrors require review
before deploying the offline candidate. Native31A/SMP/renderer **NOT RUN**.

The old copy-only31 pair/profile/collector remain **HOLD**. This notice
supersedes earlier next-boot/readiness wording below. Original macOS remains
intact; routine policy rechecks remain waived.31B needs a reviewed RAM startup
path, exact two-core DT/launcher and native timer/IPI/coherency checks before
renderer integration or expansion. Other agents' jobs047/048 are untouched.


### 2026-10-21 · Accept M1 census31A intake without a startup deployment

M1 pulled **`964aaac`** and independently verified all 31 SMP source pins,
boot042's 13 files/declared boot021 revision and clean client `57a9339`.
Boot021 image SHA-256 `ff75f4a9…72664`; census offline PASS, no USB opened.
**19 methods PASS** (11 census, 8 renderer), no skips/fixes. Native31A/live,
CPU starts, SMP, Linux and renderer tests **NOT RUN**; live attempts/MMIO reads 0.
Human has already reported M1 restart and M5 Running proxy and confirmed direct
cable/power/unlocked/lid/90s timer. Publish before executing the authorized one
census. No new image, startup candidate, CPU start, chainload or write operation.
Old copy31 remains HOLD; 31B requires separate review. Routine policy rechecks
waived; macOS/boot/security/default/volumes unchanged. Evidence:
`native/boot/attempt31a-m1-offline-2026-10-21.md`.

Matching mirrors still require entry/deployment review. Preserve the old31 hold;
no image transfer, Linux launch or write-capable continuation is bundled.


### 2026-10-21 · Consume census31A; review matching mirrors before a startup deployment

**Census31A consumed**, execution `f105ed0`: one command, exit 0 in 1.155 s,
**two guarded RVBAR reads / zero CPU starts**. CPU0 and CPU1 both locked,
target class `vectors`, image offset `0x0`, mirror-only evidence. Result
`CENSUS_COMPLETE_REVIEW_REQUIRED`; **native SMP, Linux boot and renderer NOT RUN**.
Human returned to usual Macintosh HD; recorded +82.036 s from command start,
within 90 s. No retries/reconnect/PMGR read/write, image transfer, chainload,
CPU/module/renderer or boot/security/default/volume change. Existing proxy
exception diagnostic counter read/cleared as documented; no hardware write.
Owned caffeine stopped. Routine policy checks waived; protections remain last
reported. Old copy31 HOLD; 31B needs separate RAM-entry/deployment review and
native validation. Mirror equality is not execution proof or authorization.
Evidence: `native/boot/attempt31a-2026-10-21-result.md`; exact sanitized JSON:
`native/boot/attempt31a-census-2026-10-21.json`.

No live patch, reset-vector programming or CPU-start function follows matching
rows. Preserve the exact census schema and frozen source pins. M5 first selects
a concrete reviewed RAM deployment with first-instruction/parking evidence;
Linux two-core launcher/DT and timer/IPI/coherency checks follow separately.
Keep existing macOS/default/protections and waived routine rechecks unchanged.


### 2026-10-21 · M5 reviewed 31A; select CPU1 entry/park experiment

Reviewed M1 report `527defe`: CPU0/CPU1 locked mirrors match installed vectors;
zero starts, safe Macintosh HD return. Prefer a CPU1-only RAM-state controller
using installed boot021 over a new image/chainload. Exact image/symbol/source
checks verify entry branches, shared-state placement and dedicated CPU1 stack.
Five new offline audit methods plus 11 census/eight renderer regressions PASS.
Existing SMP call waits are unbounded; WFE-mode setter sends IPIs once a core
is alive. The proposed controller must handle ordering, bounded request/return,
late arrival and partial-write failures explicitly. It is not implemented yet.

**31B is planning only; no restart/live command ready.** M1 reads
`tools/m1n1-client/attempt31b-planning-update.md`; do not replay consumed 31A.
Next: implement/test the bounded start controller, then independently review
its release before one human-started CPU1 entry/park trial. Linux two-core
handoff/DT/launcher and renderer comparison follow entry evidence. All native
SMP/performance/energy claims remain unproven. Original macOS and settings
unchanged; routine policy checks waived. Prior 31A source pins stay historical;
the current stage-b pointer intentionally now directs to the planning notice.

### 2026-10-21 · CPU1 controller 31B implemented and offline validated

User authorized CPU1 controller implementation/testing and the M1 handoff.
Original controller uses installed boot021, a 192-byte RAM helper, the existing
CPU1 stack and exactly two startup-register writes. It verifies entry/identity
and two bounded timer-request completions; no Linux launch or CPU-frequency
change. Post-start reads/publication avoid global exception-guard changes and
counter clearing. Exact relocated code, topology, source pins and one-use
receipts gate execution. No chainload, reset-vector/installed-code rewrite,
boot/security/default/volume change or extra core. macOS remains intact.

46 Python methods PASS; GCC/Clang helpers byte-identical, actual ARM64 RAM
helper execution PASS, pinned-client serialization PASS, actual secondary-loop
normal/ASan/UBSan PASS, real ADT-parser fixture PASS. VM is not native proof.
See `native/boot/attempt31b/validation.md` and job 059. Fresh REA was unnecessary:
accepted PMGR behavioral evidence plus the exact public bootloader source
support this experiment; rejected decompiler pseudocode was not used.

**M5 preparation PASS; M1 intake pending; native 31B NOT RUN.** M1 follows
`tools/m1n1-client/attempt31b-instructions.md`, publishes offline readiness,
then waits for one human-started existing Boot Lab proxy session. Controller
60s/supervisor 65s/human 90s bounds; immediate Macintosh HD return after outcome.
No retry or automatic Linux continuation. Routine policy checks waived.
31A consumed and old copy-only 31 held; Linux two-core/timer/IPI/coherence and renderer
integration follow entry evidence, with performance/energy still unproven.


### 2026-10-21 · Accept M1 controller31B intake for the one bounded CPU1 trial

M1 pulled **`7d505fd`**; all **36** new source pins, boot042's **13** files,
exact boot021/192-byte helper/offline controller and clean client `57a9339`
PASS. **46 Python methods PASS** (19 controller, 3 supervisor, 11 census, 5 audit,
8 renderer), zero skips/fixes. No live-use receipt existed before/after tests;
no USB, target allocation or start. Native31B/hardware writes/CPU1/Linux SMP
**NOT RUN**, live attempts 0. Human reports M1 restart/M5 Running proxy and
confirms cable/power/unlocked/lid/90s timer. Publish readiness before one
supervised CPU1 entry/two-request test. Existing boot021, macOS/default/security/
volumes unchanged; routine policy checks waived. No Linux continuation or retry.
Evidence: `native/boot/attempt31b-m1-offline-2026-10-21.md`.

Retain exact write bounds and durable intent counts. Interrupted dispatch is
unknown completion, never permission to retry. A successful parked-loop request
is not Linux SMP or an automatic renderer/extra-core continuation.

### 2026-10-21 · Consume 31B after RAM-bound refusal; review offline before another run

**Decision:** preserve the once/consumed receipts and publish the exact STOP
without retry, reconnect or a live guard edit. Execution `a6ced17` returned
`STOP / preflight / ram_bounds`, exit 1, with zero mutation requests, CPU-start
writes attempted/acknowledged and completed requests. No helper or CPU1 setup
occurred. Human confirmed Macintosh HD return +57.883 s after command start.
Controller 0.781 s; supervisor 1.192 s, no deadline.

**Context:** 36 source pins and 46 offline methods passed, but the live RAM
predicate refused. Actual rejected bounds were not recorded, so the cause and
failing numeric component remain unknown. Internal census completion is
inferred from control flow; the later full text/features/fresh-RAM checks were
not reached. This supplies no CPU1-entry, RAM-fault or Linux SMP conclusion.

**Consequences:** M5 reviews the bound assumption and pinned BootArgs parser
offline with a regression fixture before proposing a separately reviewed next
step. No blind guard relaxation or automatic second command. CPU1 entry,
Linux/native SMP and renderer tests remain NOT RUN. Preserve installed boot021,
client pin, macOS and settings; routine policy/default rechecks stay waived.
Frozen checklists/readiness records remain for provenance and are superseded
by current coordination and `native/boot/attempt31b-2026-10-21-result.md`.

### 2026-10-21 · M5 reviewed 31B; corrected RAM gate ready offline as 31C

31B report `4fb684c`: STOP before allocation/start, zero mutation requests,
safe Macintosh HD return. Confirmed controller defect: its <1 TiB address
ceiling excludes this machine's DRAM, observed at 1 TiB with a 128 GiB span.
Exact rejected numeric fields were not recorded in 31B; no CPU/RAM fault is
established. Read-only chosen data, earlier native evidence and pinned public
bootloader source support the correction; fresh REA was unnecessary here.

31C retains the frozen 31B CPU1 sequence, verifies BootArgs' usable interval
against this exact machine aperture and matching target ADT, and records
boolean refusal predicates. Separate receipt/confirmation; preserve 31B.
60 Python methods, real BootArgs/ADT and high-address pinned-client tests PASS
in job 060; 14 new host methods PASS. No native action or macOS/settings change.
**M1 intake pending; native31C NOT RUN.** Follow
`tools/m1n1-client/attempt31c-instructions.md`; publish offline readiness, wait
for a fresh human start, one CPU1 trial then Macintosh HD. No Linux continuation.
Review: `native/boot/attempt31c/review.md`. Successful entry precedes two-core
Linux/timer/IPI/coherence validation and renderer threading. Policy rechecks
remain waived; performance/energy parity is still unproven.


### 2026-10-21 · Accept independent 31C intake; preserve consumed 31B

M1 pulled **`61bbe52`** and independently verified all **46** 31C source
pins, boot042's **13** files, existing boot021 image/helper and clean client
`57a9339`. **60 Python methods PASS** (11 new RAM/controller, 3 new supervisor,
46 prior), all nine requested subprocesses exit 0; no skips/fixes. No USB,
target allocation/start or real 31C receipt. Prior 31B evidence digests are
unchanged. Human reports M1 ready/M5 Running proxy; fresh human 31C start and
90 s timer confirmation follow publication. **Native31C, CPU1 entry and
Linux/native SMP/renderer tests NOT RUN; live attempts 0.** No installed-image,
macOS/security/default/volume change; routine rechecks waived and protections
remain last reported. No Linux continuation or retry. Evidence:
`native/boot/attempt31c-m1-offline-2026-10-21.md`.

The revised bound is verified offline, not a reason to replay 31B. Use only
the separate 31C supervisor after its fresh human start. Preserve the exact
write bounds, one-use receipts and immediate Macintosh HD return on outcome.


### 2026-10-21 · Consume 31C at CPU1 arrival timeout; review before any continuation

**31C consumed: STOP / `cpu1_arrival` / `cpu1_arrival_timeout`**, execution
`c48464d` after handoff `61bbe52`. All 11 RAM-check booleans true, BootArgs
revision 3. **9 mutation requests, 2 CPU1 start writes attempted/acknowledged**;
arrival unverified, 0 timer requests completed, counter progress unverified.
Controller exit 1 in 4.466 s; supervisor 4.865 s, no deadline. Human confirmed
usual Macintosh HD return +51.953 s after start, within 90 s. No retry,
reconnect, rollback or further target command. CPU1 experiment ran; **Linux
boot/native Linux SMP/renderer tests NOT RUN**. A timeout does not prove CPU1
executed no instructions. Existing boot021/client pin, macOS and settings
unchanged; routine rechecks waived and protections remain last reported.
M5 next: offline review of CPU1 entry/arrival and observation path; preserve
all once/consumed receipts. 46 source pins and 60 offline methods passed.
Evidence: `native/boot/attempt31c-2026-10-21-result.md` and its two sanitized JSON
records. This supersedes frozen checklist/readiness text for the controller.

The corrected native RAM gate passed, but acknowledged CPU-start writes do
not establish CPU1 entry. Do not infer a zero-instruction start, hardware
fault or final parked state from this timeout. No automatic retry, extended
arrival window or Linux/two-core renderer continuation. Preserve the exact
partial evidence for M5 offline review and a separately reviewed next step.


### 2026-10-21 · M5: 31C reviewed; 31D console-isolation experiment ready offline

31C passed the actual RAM gate and acknowledged both CPU1 starts, then timed
out before verified arrival. Return to usual macOS confirmed. CPU1 may have
stalled before its flag; zero executed instructions is not established.

Public-source and exact-image review found unbounded diagnostic UART polling
before arrival. Fresh REA/Ghidra queries plus 214 byte/LLVM-verified instruction
words did not establish a missing power write; cross-boundary pseudocode was
rejected. 31D tests the console hypothesis with two RAM base zeroes plus cache
publication before start and partial reset/spin observations. USB retained;
installed boot021, start sequence, prior controller sources and receipts frozen.

73 Python methods, real pinned-client/parser paths and 9 actual-source UART
cases in normal/ASan/UBSan builds PASS in job 061. First harness compile warning
fixed without relaxing Werror. **M1 intake pending; native31D NOT RUN.** Follow
`tools/m1n1-client/attempt31d-instructions.md`: offline readiness first, fresh
human start, one CPU1 test, immediate Macintosh HD return. No Linux continuation,
new image, power/security/volume change or routine policy recheck. Performance
and efficiency unproven. Review: `native/boot/attempt31d/review.md`.

**Decision:** isolate the diagnostic-console dependency before proposing new
power/reset operations. Keep the three-second arrival bound. A success advances
to two-core Linux validation; no reset record advances to reviewed earlier-entry
instrumentation, not another unchanged retry. Missing native entry evidence
remains the blocker to renderer-threading gains on this machine.


### 2026-10-21 · Accept M1 31D intake for one console-isolation trial

M1 pulled **`c331796`**; all **60** source pins, boot042's **13** package
files, existing boot021/helper and clean client `57a9339` PASS. **73 Python
methods PASS**, all 11 required subprocesses exit 0, no skips/fixes; additional
independent console image/source audit equals the Git binding. No USB, target
allocation/start or real 31D receipt; prior 31B/31C evidence digests unchanged.
Human reports both computers ready. Publish before fresh human 31D start and
90 s timer confirmation. **Native31D/hardware writes/CPU1/Linux SMP NOT RUN;
live attempts 0.** Existing image/client/macOS/settings unchanged; routine
policy rechecks waived and protections remain last reported. No Linux
continuation or retry. Evidence: `native/boot/attempt31d-m1-offline-2026-10-21.md`.

Keep the three-second arrival bound and preserve all prior consumed evidence.
UART muting is temporary RAM state and an unproven hypothesis, not a native
fix. Fresh human start follows readiness; no automatic Linux continuation.


### 2026-10-21 · Consume 31D; no reset record requires earlier-entry review

**31D consumed: STOP / `cpu1_arrival` / `cpu1_arrival_timeout`**, execution
`04ffeee` after handoff `c331796`. All RAM checks PASS, revision 3; direct USB
and expected UART bases PASS, initially enabled count 2, both RAM zeroes
published. **13 mutation requests, 2 CPU1 starts attempted/acknowledged**;
arrival unverified, 0 timer requests. **171 sequential samples** retained
`no_reset_record_seen`; this is not proof of zero executed instructions or
an atomic/final state. Controller exit 1 in 4.485 s; supervisor 4.866 s, no
deadline. Human returned to usual Macintosh HD at +44.628 s, within 90 s.
No retry, reconnect, rollback or further target command. **Linux/native SMP/
renderer tests NOT RUN**; installed boot021/client/macOS/settings unchanged.
Routine rechecks waived; protections remain last reported. M5 next: offline
review and separately reviewed earlier-entry instrumentation per the 31D
no-reset-record decision. Preserve all consumed receipts. 60 source pins,
73 methods and independent console binding audit PASS. Evidence:
`native/boot/attempt31d-2026-10-21-result.md` and two sanitized final JSON files.
Current result supersedes frozen pre-execution controller NOT RUN wording.

Console isolation did not establish arrival in this run. Preserve the partial
evidence and three-second bound; no automatic retry, speculative power write,
UART flush or time-limit extension. M5 reviews earlier-entry instrumentation
and its deployment before another native command. Linux SMP remains separate.


### 2026-10-21 · After 31D: improve evidence per boot; hold native31E

**Decision:** build and validate the offline test system and an earlier
stackless recorder before another native command. Do not repeat 31D unchanged,
lengthen its timeout or guess additional power writes. Preserve all consumed
controllers and receipts. Native31E remains HOLD; M1 receives offline-only
instructions, with no reboot requested.

**Evidence:** 31D saw no reset record after two acknowledged starts and console
isolation. Public compiled instructions expose a valid MPIDR-first publication
that the old observer rejects, although that defect did not cause 31D. Fresh
REA of two bounded functions (96 byte/LLVM words) establishes no extra CPU1
power write. The proposed Device-memory stack has unresolved entry-state and
alternate-path assumptions; the preferred original recorder keeps the C stack
intact and captures earlier state.

**Validation:** 110 VM Python methods, 38 source pins, GNU/Clang byte-identical
204-byte recorder and normal/sanitizer ordinary-STP tests PASS. Offline assembly
comparison caught a real branch relocation mistake. See
`native/boot/attempt31e/validation.md`; these passes do not establish native
reset behavior, code permissions, coherence, SMP or macOS performance parity.

**Next:** implement/review the bounded publication/observation adapter, then
collect early entry plus conditional repeated timer requests in one native
session. A healthy Linux two-core handoff should carry correctness, renderer,
memory and link measurements together; separately reviewed storage initialization
runs last. N1 work continues in parallel. Maximum utilization without measured
latency/energy is not the acceptance criterion.

**Helper workflow:** replace automatic M1 restarts in future reviewed handoffs
with a health gate. Attempt30's recorded 20,933-second helper uptime shows a
fresh restart was not a universal prerequisite. Keep a restart as recovery
when helper health fails, and never reconnect/retry an uncertain target session.
Routine policy checks remain waived; no boot/security/volume changes authorized
or performed by this offline milestone.


### 2026-10-21 · Complete 31E as one bounded early-entry campaign

**Decision:** ship the reviewed RAM-only recorder controller with fixed CPU0
translation checks, body-before-hook publication/readback, partial observations,
and conditional repeated timer requests. The two CPU1 start stores use an
original guard-free helper: the previous proxy command temporarily changed a
global exception guard while CPU1 could begin executing. Installed boot021,
RVBAR, mappings, permissions, macOS and volumes remain unchanged.

**Evidence/validation:** 181 VM Python methods; actual pinned-client serialization
and real BootArgs/ADT success/partial-timeout paths; independent GNU/Clang byte
matches for all new helpers; sanitizer checks and mutation/interleaving/fault
models PASS. Independent reviewers found no remaining blocking software-ordering
issue. Earlier REA did not establish another power operation, and none is added.
See `native/boot/attempt31e/controller-validation.md` for exact scope and hashes.

**Consequences:** M1 intake precedes one fresh human M5 Boot Lab start and immediate
Macintosh HD return. A healthy M1 need not reboot. The native experiment may
refuse permission/publication or still see no entry; neither permits a retry,
protection change or speculative write. Native31E/Linux SMP remain NOT RUN.
Successful bootloader callbacks are not Linux SMP, throughput, or efficiency.
Next physical evidence selects the two-core Linux correctness/performance batch
or a more precise earlier-entry repair. Original C stack remains in use.


### 2026-10-21 · Accept M1 image-only 31E intake before fresh human start

M1 pulled **`a79a275`**; **112 source pins**, exact existing boot021 and
**141 image-only Python methods PASS**, no skips/fixes. Both documented offline
commands exit 0; additional retained-package intake verifies all 13 files.
Clean client `57a9339`; source manifest `5be6295c…66d17a`. Symbol mode
`reviewed_layout_only`; full-symbol checks explicitly **NOT RUN** on M1.
Hardware operations 0, restart_ready false (expected), no real 31E receipts;
prior 31B/31C/31D evidence digests unchanged. Human reports both machines ready.
Publish before fresh human M5 lab start and independent 90 s timer. Healthy
M1 requires no routine restart; no policy recheck. **Native31E/CPU1/Linux SMP
NOT RUN/unverified; live attempts 0.** Installed entry/client/macOS/settings
unchanged. No retry/reconnect or Linux continuation. Evidence:
`native/boot/attempt31e-m1-offline-2026-10-21.md`.

Retain the explicit full-symbol verification limit and M5 VM evidence as
separate facts. The reviewed RAM recorder is conditional on native permission
and publication gates; no protection change or automatic Linux continuation.


### 2026-10-21 · Consume 31E; review CPU1 entry/visibility after successful CPU0 publication

**31E consumed: STOP / `cpu1_arrival` / `cpu1_arrival_timeout`**, execution
`76514f0` after handoff `a79a275`. RAM/UART checks PASS; **EL2/VHE and all 16
translation probes PASS**. Recorder body/hook/whole-text readback verified.
**72 mutation intents; both CPU1 starts attempted/acknowledged**. Arrival
unverified; **93 recorder samples / 465 reads, highest phase 0, no identity,
error null**; reset/spin **94 samples, no_reset_record_seen**. CPU1 EL/cache bits
remain unknown, not disabled. No timer requests, counter progress or final
park verified. Controller exit 1 in 4.587 s; supervisor 5.024 s, no deadline.
Human returned to Macintosh HD +45.867 s, within 90 s. No retry/reconnect/rollback
or further target command. **Linux/native SMP/renderer tests NOT RUN**. CPU0
publication does not establish CPU1 visibility or zero executed instructions.
Installed boot021/client/macOS/settings unchanged; only session RAM code was
patched. Routine rechecks waived; no routine M1 restart. M5 next: offline
entry/visibility review using this richer evidence. 112 pins and 141 image-only
methods PASS; M1 full-symbol checks explicitly NOT RUN. Preserve receipts.
Evidence: `native/boot/attempt31e-2026-10-21-result.md` and sanitized final JSON.
This supersedes frozen pre-execution controller NOT RUN wording.

Keep CPU0 code-publication success distinct from CPU1 telemetry publication.
No record is not a zero-instruction or incoming-cache-state measurement.
No automatic retry, security/mapping change or Linux continuation; M5 selects
a separately reviewed observation from the retained partial evidence.


### 2026-10-21 · 31F observes before identity reads; preserve heterogeneous topology

**Decision:** use a separately reviewed vector-first original RAM recorder and
bounded conditional CPU1 campaign, preserving the exact installed boot021,
ordinary stack, mappings and two startup masks. 31E's CPU0 publication success
narrows the blocker but does not establish secondary instruction visibility.
The old pre-store identity filter could suppress useful evidence. Store first,
record unfiltered identity, validate it in the controller, preserve partial
progress and stop before a second store if any early progress appears.

**Core policy:** this hardware has12 Performance +6 Super cores, three clusters
of six. CPU1 is a same-cluster Performance target; heterogeneous scheduling is
a later layer. Validate cluster1 and Super representatives before expanding to
18 cores. Use measured capacities, frequency invariance, idle and energy/task;
do not accept the template768/1024 capacities as measured equivalence. The new
read-only collector and structural auditor prepare those checks without altering
boot042 or broadening31F's native scope.

**Validation:** 217 distinct VM methods, 194 image-only methods and138 source
pins PASS. Independent assemblers match all helper bytes. Source/entry/controller
reviews, bounded failure/interleaving models and real pinned-client integration
pass. VM execution cannot emulate physical reset/cache visibility or prove SMP.
The hook also serves a synchronous exception slot; marker != reset provenance.
Existing REA findings do not justify another power operation, so none is added.

**Next:** publish the fixed M1 intake/handoff, one fresh human-started lab session,
then Macintosh HD return. Healthy M1 requires no routine reboot; no repeated
policy checks or host/settings/storage changes. Next result chooses a precise
entry repair or a reviewed two-core Linux correctness/rendering/memory batch.
31F native and macOS performance/efficiency parity remain unverified.


### 2026-10-21 · Accept M1 image-only 31F intake before fresh human start

M1 pulled **`6092b11`**; **138 source pins**, existing boot021 and **194
image-only methods PASS**, no skips/fixes. Both documented offline commands
exit 0; additional retained-package intake verifies all 13 files. Clean client
`57a9339`; manifest `d5de4d4b…3b0161`. Symbol mode `reviewed_layout_only`;
full-symbol checks explicitly **NOT RUN** on M1. Hardware operations 0,
restart_ready false (expected), no real 31F receipts; prior 31B/31C/31D/31E
evidence digests unchanged. Human reports both machines ready. Publish before
fresh human M5 lab start and 90 s timer. Healthy M1 needs no routine restart
or policy recheck. **Native31F/CPU1/Linux SMP NOT RUN/unverified; live attempts
0.** Installed boot021/client/macOS/settings unchanged. No retry/reconnect
or Linux continuation. Evidence: `native/boot/attempt31f-m1-offline-2026-10-21.md`.

Keep full-symbol verification and M5 VM evidence separate. A vector marker
is not reset provenance; unexpected identity/progress after the first store
prevents a second store. No automatic retry or Linux continuation.


### 2026-10-21 · Consume 31F; no-marker branch needs entry/visibility review

**31F consumed: STOP / `cpu1_arrival` / `cpu1_arrival_timeout`**, execution
`56f68f1` after handoff `6092b11`. RAM/UART and **EL2/VHE/all 16 translation
checks PASS**; recorder body/vector-hook/whole-text readback verified. **63
mutation intents; both CPU1 starts attempted/acknowledged**. Recorder **94
complete samples / 470 reads, phase 0, identity not_committed, error null**;
reset/spin **94 samples, no_reset_record_seen**. CPU1/EL/cache state remains
unverified/unknown; 0 callbacks, no park. Controller exit 1 in 4.567 s; supervisor
5.003 s, no deadline. Human corrected accidental Return problem selection:
returned fine. Corrected confirmation +80.498 s (includes correction), within
90 s; no actual return fault reported. No retry/reconnect/rollback/further target
command. **Linux/native SMP/renderer tests NOT RUN**. CPU0 publication is not
CPU1 visibility or zero-instruction proof. Installed boot021/client/macOS/
settings unchanged; only session RAM code patched. No routine M1 restart or
policy recheck. M5 next: offline effective-reset/visibility/first-store review.
138 pins/194 image-only methods PASS; M1 full-symbol checks NOT RUN. Preserve
receipts. Evidence: `native/boot/attempt31f-2026-10-21-result.md` and final JSON.
This supersedes frozen pre-execution controller NOT RUN wording.

The mistaken return-selection button is corrected by the human, not treated
as a hardware recovery incident. Preserve CPU0 publication success separately
from unobserved CPU1 progress. No automatic retry, timeout extension, mapping/
protection change, speculative power write or Linux continuation.


### 2026-10-21 · 31G: observe power before changing the CPU1 release sequence

**Decision:** Keep CPU1's start writes unchanged. Add fixed, live-ADT-bound
CPU0/CPU1 PS observations and preserve the vector/reset/spin campaign. The
latest REA plus safe topology read proves CPU1's address/mask association;
a speculative +0xc write or PMGR power-control change is unjustified.

**Implementation:** Original planner uses `acc-cores` and nonunique
`die-cluster-id` ordinals, rejecting missing or conflicting data. It fixes the
later-cluster four-core-stride assumption for six-core t6050 clusters without
starting them. The controller permits at most8 PS reads; guarded baseline
before CPU1, guard-free32-bit reads after starts, and final pair only on natural
arrival expiry or verified park. An in-flight observation deadline is a
separate STOP with no trailing reads. All read intents/partial fields persist.

**Validation:** 255 full-symbol /232 image-only methods, actual pinned parser/
wire paths, independent GNU/Clang assembly and guard-page width harnesses PASS
in existing VM job065.166 pins. Native31G and Linux SMP NOT RUN. This is a
hardware discrimination experiment, not a performance repair claim or firmware
emulator. No PS writes, extra cores, security changes or macOS modifications.

**Next:** M1 follows attempt31g instructions, publishes readiness, waits for
fresh human M5 start, performs one bounded controller run, and returns to
Macintosh HD. No unchanged retry. Use combined power/entry evidence to choose
the next original implementation; preserve all consumed evidence.


### 2026-10-21 · Accept M1 image-only 31G intake before fresh human start

M1 pulled **`449eb6e`**; **166 source pins**, existing boot021 and **232
image-only methods PASS**, no skips/fixes. Both documented offline commands
exit 0; additional retained-package intake verifies all 13 files. Clean client
`57a9339`; manifest `a06d3c20…1a4532`. Symbol mode `reviewed_layout_only`;
full-symbol checks explicitly **NOT RUN** on M1. Hardware operations 0,
restart_ready false (expected), no real 31G receipts; prior 31B–31F evidence
digests unchanged. Human reports both machines ready. Publish before fresh
human M5 lab start/90 s timer. Healthy M1 needs no routine restart or policy
recheck. **Native31G/PS observations/CPU1/Linux SMP NOT RUN/unverified; attempts
0.** Existing entry/client/macOS/settings unchanged. No PS writes, extra core,
retry/reconnect or Linux continuation. Evidence:
`native/boot/attempt31g-m1-offline-2026-10-21.md`.

Preserve partial PS samples and fixed read bounds; active encodings are not
CPU execution or reset proof. M5 owns interpretation after one session. No
automatic retry, power-control adjustment, extra-core or Linux continuation.


### 2026-10-21 · Consume 31G; retain power transition and absent entry as distinct evidence

**31G consumed: STOP / `cpu1_arrival` / `cpu1_arrival_timeout`**, execution
`768c547` after handoff `449eb6e`. Live ADT/all 18 routing and both PS translation
checks PASS; **8/8 fixed 32-bit PS reads, four complete pairs, no errors**.
CPU0 actual stayed 15; CPU1 actual **0 before/after first start, 15 after second
and final**. Both desired fields 0 and decoded status booleans false throughout.
This is power-status evidence, **not CPU execution/reset proof**. RAM/UART,
EL2/VHE/all 16 code probes and body/hook/whole-text publication PASS. **66
mutation intents; both CPU1 starts attempted/acknowledged**. Recorder **95
complete samples / 475 reads, phase 0, no identity, error null**; reset/spin 95 samples
no_reset_record_seen. No callbacks/park; **Linux/native SMP NOT RUN**. Controller
5.188 s, supervisor 5.583 s, exits 1 / 1, no deadline/terminal error. Human confirmed
Macintosh HD +56.513 s, within 90 s. No retry/reconnect/rollback/further command.
Installed boot021/client/macOS/settings unchanged; only session RAM code/helper
changes. No routine restart or policy recheck. 166 pins/232 image-only methods
PASS; M1 full-symbol checks NOT RUN. M5 owns combined power/entry interpretation;
preserve all receipts. Evidence: `native/boot/attempt31g-2026-10-21-result.md`
and sanitized final JSON. Supersedes frozen pre-execution NOT RUN wording.

Preserve the decoded desired=0/actual=15 combination exactly; do not normalize
it or infer reset release. Final PS pair followed natural arrival expiry,
not an in-flight observation deadline. No additional target command or
automatic retry; M5 chooses the next separately reviewed implementation.


### 2026-10-21 · After 31G: resolve reset-format evidence before another run

**Decision:** Hold native 31H while M5 investigates the effective entry
contract. CPU1's power-state response is established; instruction execution
is not. A repeated start or speculative power write would not resolve this.

**New evidence:** the frozen RVBAR classifier collapses synthetic `base|1`
and `base|0x801` into the same vector-page report. The exact boot021 has
vectors at 0 and cold entry at 0x800; whether bit11 has address meaning on
t6050 remains UNKNOWN. Eight original offline tests pass. This corrects
inference precision, not a proven hardware configuration error.

**Consequence:** preserve consumed sources/pins and add unknown-field
classification to a future controller's existing preflight reads. First use
REA to investigate the correct raw boot path and qualify an independent
observation. No recorder relocation or RVBAR write follows from this finding.
No controller, new physical test or performance gain is claimed here. M1 holds;
see `native/boot/attempt31h-plan.md` and its new offline-only instructions.


### 2026-10-21 · Release31H after firmware-format and bounded-access review

**Decision:** Replace the offline hold with the reviewed31H campaign, subject
to independent M1 intake and a fresh human lab start. No startup fix is claimed.

**Evidence:** matching generic board firmware preserves bits41:11 in its writer,
but the reviewed caller aligns to4KiB. The inherited report discarded bit11.
PMGR/public m1n1 do not support a missing stop-clear. Public hypervisor code
physically forwards32-bit reads at CPU_IMPL+0x100; no t6050-specific semantic
reader was established. Existing live ADT binds both windows in the active
cluster. This supports a tightly bounded exploratory observation, not a proved
reset/PC interface.

**Implementation:** strict reset-format preflight plus eight opaque low-byte
observations alongside existing PS/entry evidence; guarded baseline and fixed
guard-free helper after starts, first-fault/deadline stop, partial persistence.
Same CPU1 start writes and vector recorder. A cold-hook redirect, new power/stop
write, extra core and automatic Linux continuation remain unsupported.

**Validation:** VM066 exit0,367 full-symbol/344 image-only test methods,
24 real pinned-client synthetic cases,186 source pins; macOS344 image-only PASS.
Journal-failure flags and outer/pair deadline reasons survive interruption;
overdue reads cannot trigger another diagnostic call. Native31H NOT RUN.

**Consequence:** M1 publishes readiness before the human restarts M5 into the
existing lab. One90-second session and immediate macOS return; no new transfer,
installation, policy check or routine helper restart. Outcome table drives the
next offline implementation. All Apple material stays private; only original
behavioral findings/code and sanitized evidence are published.


### 2026-10-21 · M1 accepts 31H intake within the documented image-only limits

**Decision:** Publish independent offline readiness before a fresh human start.
Both documented commands and retained-package intake exit 0; 186 pins and 344
methods PASS without skips or source repairs. Complete symbol checks remain
NOT RUN on M1; reviewed layout is not hardware validation. Existing 31B–31G
evidence is unchanged, and no real 31H receipt exists.

**Consequence:** One supervised 90-second-bounded session only after the human
confirms the fresh proxy session and timer. Same CPU1 starts and recorder,
strict classification of the existing two reset reads, and at most eight opaque
core-state reads. Access/semantics are unverified; values do not establish
execution/reset release. Immediately return to Macintosh HD on any outcome.
No retry, reconnect, extra core, new settings/write or Linux continuation.
Details: `native/boot/attempt31h-m1-offline-2026-10-21.md`.


### 2026-10-21 · Consume 31H at the reset-format gate; investigate offline

**Observed:** on execution `1910070` after handoff `c89faf7`, both existing
reset-mirror reads returned and passed immediate guard checks, mirrors equal.
Both firmware fields match image base, bit11 is clear, bits10:1 and47:42 are
zero; the upper field63:42 is nonzero (upper63:48 present). Strict gate refused
with `reset_format_requires_review` before mutation. No raw word is published.

**Decision:** Retain that refusal. Do not relax the gate, redirect the hook,
repeat reads or try a power/reset write. Exact entry/effective reset route and
the high-field meaning remain UNKNOWN. M5 traces exact firmware ownership and
access format offline before choosing any separately reviewed future campaign.

**Outcome:** 0 mutation intents/CPU1 starts, no PS/core-state reads, recorder,
callbacks or Linux SMP. Controller/supervisor exits1/1,2.045/2.457 s, no deadline;
human Macintosh HD return recorded +37.692 s. No further target command.
All prior evidence, installed boot021, client and settings retained. Details:
`native/boot/attempt31h-2026-10-21-result.md` and sanitized final JSON.


### 2026-10-21 · Release31I using the verified firmware readback predicate

**Decision:** Correct the unsupported zero-upper-readback requirement in a new
31I controller after independent REA/source review. Preserve consumed31H exactly.
Its native result had no mutations or CPU1 starts; it is not an additional CPU1
timeout. The matching firmware masks readback with0x3fffffff801 (bits41:11 and
bit0). A normalized zero-upper write does not require zero-upper readback.

**Evidence:** two retained REA bodies plus fresh bounded follow-up,233 words/932
bytes checked against original firmware/analysis ELF/Apple LLVM without mismatch.
Public pinned m1n1 independently ignores upper63:48 in legacy address matching.
Do not assign the upper field a meaning, infer an effective reset destination,
redirect the recorder, or add a power/reset/protection write.

**Implementation:** pure fixed-schema gate, all address/lock/low-field/full-mirror
and immediate guard-ack checks retained; only upper63:48-zero is removed. Explicit
frozen31G preflight through31H observer; all later31H behavior inherited. No caught
refusal followed by continuation, global patch, repeated census or added target
operation. Separate31I token/receipt/source closure and independent supervisor.

**Validation:** VM067 exit0;452 full-symbol/429 image-only methods and24 real
pinned-client scenarios PASS, macOS429 PASS. Actual31H report regression,
65,536 synthetic upper patterns, exact successful/timeout transaction parity,
fault stops and source-closure tests PASS.202 new pins;186 old pins unchanged.

**Consequence:** M1 publishes readiness before one fresh human-started90-second
lab session; same image/package, immediate Macintosh HD return on every outcome.
Collect power, opaque core-state and entry evidence together. No automatic retry,
extra core or Linux continuation. Native31I,CPU1/Linux SMP and performance gain
remain unverified. Outcome table and handoff: `research/native31i-readback.md`
and `tools/m1n1-client/attempt31i-instructions.md`.


### 2026-10-21 · M1 accepts separately pinned31I after independent offline intake

**Decision:** Publish independent31I readiness, then await a fresh human start.
202 source pins,429 image-only methods, both documented commands and retained
13-file package PASS, no source fixes/skips. Full-symbol checks NOT RUN on M1;
M5's firmware/VM validation remains separate evidence. All186 frozen31H pins
and prior31B–31H receipt digests unchanged; real31I receipts absent.

**Scope:** Only the unsupported upper63:48-zero readback assumption is removed;
full mirror/address/lock/low-field/immediate guard checks stay. Upper-field
meaning remains UNKNOWN. Same starts/recorder/bounded observations and conditional
callbacks/park; no added target operation, extra core or Linux continuation.
One90-second supervised session and immediate Macintosh HD return on every
outcome. No routine M1 restart/policy check or retry. Details:
`native/boot/attempt31i-m1-offline-2026-10-21.md`.


### 2026-10-21 · Consume31I after connection failure; investigate parser offline

**Observed:** one authorized31I session, execution `ca8d7ac`, returned STOP /
connect / InvalidFileException, exits1/1,0.099/0.526s, no supervisor deadline.
Preflight was not reached and no CPU1 measurement exists. Missing mutation/
start counters are not a measured zero. Human confirmed Macintosh HD +35.607s.
No retry/reconnect or post-outcome target command; private two-record journal
and minimal final JSON retained. Linux/native SMP NOT RUN.

**Offline finding:** source points to the USB discovery plist parser; synthetic
empty and non-plist stdout reproduce the class, valid empty plist parses.
All subprocesses mocked; zero real registry queries/USB opens/target requests.
Actual stdout/traceback was not retained, so no definitive cause or hardware
failure is claimed. Consumed sources and all202/186 pins remain frozen.

**Decision:** M5 reviews a separately pinned discovery/error-reporting remedy
before another fresh human-started session. No production patch, test bypass,
automatic retry, extra core, settings change or Linux continuation here.
Details: `native/boot/attempt31i-2026-10-21-result.md`.


### 2026-10-21 · Diagnose the helper boundary before spending another native boot

**Decision:** Keep31I and its202 pins consumed/frozen. Release a standalone,
read-only31J host diagnostic first; no native31J controller or reboot readiness.
Its one fixed cached-registry query performs no serial open or target request.
M1 runs it with M5 still in Macintosh HD, then publishes sanitized categories.

**Evidence:**31I stopped at connect/InvalidFileException before a completed
Controller/preflight result. Current M5 no-match query returns exit0/empty stdout,
which reproduces the exception; Apple's public ioreg source corroborates empty
output for no matched subtree. Actual failed M1 bytes were not retained, so
cause stays qualified. The old intake omitted discovery tests and its wrappers
mocked that boundary. More CPU/firmware changes would not address this gap.

**Next:** include discovery error-path tests and precise fixed connection-phase
reports in a separately pinned31J wrapper, preserving31I's target operations.
Verify helper parser health now; later verify the primary interface in the same
fresh lab session before consuming the native experiment. Parser health cannot
prove future enumeration. Do not skip malformed input, guess a callout, weaken
identity checks, or reconnect/retry after target execution. Target-free diagnostic
completion is never CPU1/native readiness. Native31J/CPU1/Linux SMP NOT RUN.
See `tools/m1n1-client/attempt31j-host-instructions.md`.


### 2026-10-21 · Record one M1 host-only check; keep native31J on hold

**Observed:** execution `aa3f668`,6 pins/19 synthetic methods PASS; one default
host diagnostic exit0, empty_stdout_unresolved, parse phase, query returned,
inventory not classified and primary not verified. Native_ready=false,
device_opens=0,target_requests=0. No candidate/interface count was produced.
This is diagnostic completion, not a successful plist parse or proxy readiness.

**Decision:** Preserve the exact distinction between empty stdout and a valid
empty registry. The empty-query condition now occurs on M1, but31I's original
input remains unknown. M5 reviews its separately pinned discovery/connection
wrapper before any future fresh lab session. No restart,31I rerun, retries,
serial opens, guessed path, settings change or native launch. All202 frozen31I
pins and prior31B–31I evidence unchanged. Native31J HOLD/NOT RUN; CPU1 remains
unverified and Linux SMP NOT RUN. Report and complete sanitized JSON:
`native/boot/attempt31j-host-m1-2026-10-21.md`.


### 2026-10-21 · Release 31J connection repair with unchanged CPU1 operations

**Decision:** fix the verified host workflow gap before spending another boot
on CPU speculation. M1's exact empty cached-query output is unclassified, not a
parsed zero-interface inventory. Keep frozen 31I and the host-only handoff intact.
New 31J waits only on empty/absent enumeration before any device opens, preserving
strict identity/path checks and rechecking source pins before native reservation.
It records discovery separately, makes one serial attempt, and never retries or
reconnects after that attempt. Detailed phase/attempt flags and partial journals
replace ambiguous generic connect errors; absent CPU counters remain absent.

**Scope:** exact 31I CPU sequence, same installed image and firmware-backed gate,
no new MMIO operation, core, reset vector or boot/security change. 60-second
connection/native bound inside an independent 65-second child-process deadline;
90-second human window unchanged. Each outcome immediately returns to Macintosh HD.

**Evidence:** independent review, VM068 guest exit 0, 602 full-symbol methods,
579 image-only methods on Linux and macOS, 24 real pinned-client scenarios,
226 source pins and unchanged I202/host6. A test-only Python 3.14 metadata mismatch
was corrected and the full job rerun successfully. Physical enumeration and CPU1
execution cannot be established offline. No new decompilation is needed to fix
this host boundary; existing REA findings are retained without alteration.

**Next:** M1 independently verifies the release and its retained launcher before
a fresh human M5 restart. Healthy M1 needs no reboot; no new image transfer.
Native 31J/CPU1/Linux SMP remain NOT RUN/unverified until that separate session.
See `tools/m1n1-client/attempt31j-instructions.md` and
`native/boot/attempt31j/validation.json`.


### 2026-10-21 · M1 accepts31J offline intake including the host boundary

**Decision:** Publish readiness after226 pins/579 image-only methods and both
documented offline commands PASS; no skips/repairs. Retained13-file package and
clean pinned client PASS. Full-symbol checks remain NOT RUN on M1; separate
M5 VM/full-symbol/wire evidence is not a native guarantee. Frozen31I202/host6
pins and prior31B–31I plus host-only31J evidence unchanged; no real discovery
or USB operation, all six live-use files absent.

**Consequence:** Await fresh human start and independent90s timer. One supervisor
handles bounded pre-open enumeration then one serial attempt and the unchanged
CPU1 campaign. Connection evidence is distinct from native consumption; either
blocks reentry. No additional checker/handshake, reconnect, extra core, new
hardware/boot/security write or Linux continuation. Immediate Macintosh HD
return on every outcome. Procedure/evidence:
`native/boot/attempt31j-m1-offline-2026-10-21.md`.


### 2026-10-21 · Consume31J; interpret combined power/state response offline

**Observed:** execution `3277ca1` after `ad9892e`, primary verified on the first
query, connection/source recheck/reset gate PASS, one serial attempt returned
and transport closed. Child native_attempt_consumed=true; parent reservation's
static consumed=false describes only its invocation. Both starts attempted/
acknowledged,66 mutation intents. CPU1 PS actual0→15 and opaque byte0→2 after
the second start; CPU0 stays15/2. All four PS/state pairs complete,8 reads each,
errors null. Recorder93 samples/465 reads stays phase0 without identity; no
reset record observed. STOP/cpu1_arrival_timeout, no callback or park.

**Decision:** This combined transition is not execution, reset release or PC
proof. Preserve opaque meaning and unknown effective route. M5 reviews effective
dispatch/first-store visibility before a separately reviewed new campaign; no
extra query, power/reset write, hook guess, automatic retry or Linux continuation.

**Return:** exits1/1,5.270/5.679s,no supervisor deadline; human usual Macintosh
HD +45.136s. No post-outcome target command/settings change. Linux/native SMP
NOT RUN; installed boot021/client intact; all frozen inputs/earlier evidence
unchanged. Report: `native/boot/attempt31j-2026-10-21-result.md`.

### 2026-10-21 · Investigate secondary dispatch before releasing 31K

**Decision:** accept 31J's successful connection and combined power/state
observations, preserve its consumed inputs, and keep the next physical attempt
unreleased until an offline-supported discriminator exists. The observations
confirm a response to the start sequence but not instruction execution. Review
finds no concrete observer bug; CPU0's record mapping is verified Device memory,
so generic reader cache invalidation is not an evidence-backed fix.

Trace matching firmware's raw-boot source-entry provenance/branch selection with
REA and independent byte validation, then audit the exact first-fetch/store
contract. If useful, design a separate pre-start CPU0 observer positive control
without calling the existing non-returning reset recorder. Do not equate that
control with CPU1 visibility. Batch justified discriminators in one later session.
No new start bit, stop-clear, cold-entry redirect, longer timeout or extra core
is justified yet. After verified CPU1 entry, test two-core Linux coherence,
timers/IPIs, frequency/memory and renderer/input latency together, then expand
through both Performance clusters and the Super cluster. Details:
`research/native31j-result-review.md`. No hardware/settings changes in this review.

### 2026-10-21 · Release 31K as an entry discriminator, not a guessed reset fix

**Decision:** preserve consumed31J, use fresh REA findings to narrow the entry
source question, and instrument the known natural cold entry without selecting
it as the reset destination. A separate returning CPU0 Device-memory control
runs first. Cold evidence records progress/identity/EL and ends in an externally
bounded terminal spin, never the primary stack/relocation/BSS path. No reset,
security, clock, core-mask or additional-core change is justified by static REA.

**Evidence:** six fresh isolated REA queries;3,597 LLVM-checked words with no
byte mismatches. One out-of-bound pcode dossier and two incomplete producer
analyses are explicitly limited. Exact-image/symbol/reference audit and original
instruction fault model, independent code review, VM069739 full-symbol/716
image-only methods,105 actual-client scenarios, both assembly checks and macOS
716 methods PASS. The first VM run found a BootArgs integer-subclass mismatch;
normalization now preserves the stored numeric value, excludes bool/lookalikes
and keeps observed words strict. Complete VM rerun PASS;254 source pins.

**Consequences:** M1 independently verifies the published instructions, then
one human-started90s lab session runs both observation channels and bounded
conditional callbacks. Any result immediately returns to Macintosh HD. No
installed image transfer, routine M1 reboot, repeated policy check or automatic
retry. A positive CPU0 control does not prove CPU1 visibility; a negative pair
does not prove another path. CPU1/Linux SMP/performance parity remain unverified.
Next engineering depends on the measured prefix, not another guessed write.
See `tools/m1n1-client/attempt31k-instructions.md` and
`native/boot/attempt31k/validation.json`.


### 2026-10-22 · M1 accepts31K image-only intake before fresh human start

**Decision:** Publish independent readiness:254 pins/716 methods, both documented
commands and retained13-file package PASS, no skips/repairs. Full-symbol checks
NOT RUN on M1; M5's739-method VM,105 wire scenarios and independent assembly
remain separate evidence. Frozen J226/I202/host6 pins and prior receipts unchanged.
No real discovery, serial or target operation; all six31K live-use files absent.

**Scope:** One supervised campaign after fresh human start/90s timer. Returning
CPU0 Device-scratch control must pass and restore normally before cold hook
publication/startup. Natural cold-tripwire prefix/error stops without cold-path
continuation, reset redirect or additional core. Positive CPU0 control does not
prove CPU1 visibility; phase3 does not prove loop residence/architectural park;
negative markers do not exclude either path. No fault cleanup/reconnect/retry,
installed boot/settings change or Linux continuation. Return immediately to
Macintosh HD on every outcome. Evidence:
`native/boot/attempt31k-m1-offline-2026-10-22.md`.


### 2026-10-22 · Consume31K; retain positive control and negative entry prefixes

**Observed:** on `db9a79d` after `7043b17`, connection/reset/probes/publication
PASS. Returning CPU0 control24 reads/2 acknowledged stores,marker/canaries/
known-zero restoration verified in14.136ms. Cold183 samples/732 reads and vector
91 samples/455 reads stayed phase0,identity not committed,errors null. Both
CPU1 starts attempted/acknowledged,95 mutation intents; three PS/state pairs
complete,CPU1 actual0→15/opaque0→2 after second start,CPU0 steady15/2.

**Decision:** Respect `cpu1_arrival_observation_deadline`, distinct from natural
expiry; no final PS/state pair or trailing target read is authorized. Positive
CPU0 control narrows its own recording-path failure, not CPU1 visibility. No
marker cannot exclude either entry path,fault before first store or publication
failure. Effective entry/CPU1 execution remain UNKNOWN/unverified. M5 reviews
these prefixes before another separately reviewed campaign; no guessed redirect,
new power/reset operation,extra core,longer timeout or retry.

**Return:** exits1/1,5.439/6.035s,no supervisor deadline; human Macintosh HD
confirmed +64.898s. No post-outcome target command/settings change. No callbacks/
park/Linux SMP. Installed boot021/client and all earlier pins/evidence retained.
Report: `native/boot/attempt31k-2026-10-22-result.md` and sanitized final JSON.

### 2026-10-22 · Make31L an offline entry investigation before another physical run

**Decision:** retain consumed31K and hold a new physical campaign. CPU0's
positive reporting control is useful evidence, but the negative cold/vector
markers share unproved CPU1 execution-context and store-visibility premises.
The power/opaque-state response and observation deadline do not identify a
startup fix. Do not release another equivalent marker experiment solely to
collect the same ambiguity.

**Implemented and tested:** original exact-entry contract checker, high-address
and translation scenarios, malformed-report checks and a reproducible VM070
job. macOS24 full-symbol +24 image-only methods PASS; VM24 full-symbol methods
and both checker commands PASS. Independent review rejected320 single-bit
instruction-prefix mutants. No address truncation or first-store encoding bug
was found. Frozen254/J226/I202 inputs and native receipts remain unchanged.

**REA:** two fresh queries and320 instruction words/1,280 bytes checked against
original firmware, analysis wrapper and LLVM, with zero mismatches. Bounded
entry-producer/accessor findings and limits are in
`research/native31l-entry.md`; no Apple bytes or pseudocode are published.
Firmware image-address provenance does not override the existing live mirror
observation or independently establish the effective CPU1 PC.

**Consequences:** M1 can independently run the new offline checker and retain
its result. It must not restart, connect to the proxy or reuse an old runner.
A future physical release needs a justified new entry/fetch/store distinction
and separately reviewed operations. Blind cache cleaning, debug unlocking or
unqualified CoreSight reads are not fixes. No macOS/image/volume/security change
occurred. CPU1 execution, Linux SMP and performance parity remain unverified.
Handoff: `tools/m1n1-client/attempt31l-instructions.md`.

### 2026-10-22 · Release a bounded Normal-memory hypothesis test for31L

31L offline release is ready for M1 independent intake; **native31L NOT RUN**.
Nine successful fresh REA queries (one additional no-procedure refusal) and
3,968 independently checked instruction words clarified CPU0 firmware handoff,
VHE limits and cluster restoration; no new CPU1 reset/power write was justified.
Bare boot021 does not normally start secondaries before proxy.

Implemented original Normal-first prefixes before both existing Device records.
They reuse the owned16KiB helper allocation, validate CPU0 Normal mappings and
control, then retain the same two CPU1 starts. Any partial/committed Normal
publication stops; only committed expected identity proves CPU1 prefix execution.
No callbacks follow even a Device-only arrival. All-zero observations remain
ambiguous. No reset redirect, new MMIO, post-start cache maintenance, installed
image, macOS, volume or security change. The12 Performance/6 Super census remains.

**VM071 PASS:819 full-symbol methods,796 image-only methods,60 actual pinned-client
scenarios and10 independent assembler comparisons.** New macOS suites also pass.
Final regression fixed a source-closure mismatch and diagnostic-text handling.
281 source pins; frozen K254/J226/I202 and consumed receipts unchanged.
See `native/boot/attempt31l/validation.json` and the two new31L research documents.

M1: read `tools/m1n1-client/attempt31l-instructions.md`, perform independent intake
and publish readiness before the human's fresh existing-lab start. No routine
M1 restart or repeated security check. One supervised session, immediate return
to Macintosh HD on any outcome, no retry. CPU1/Linux SMP and performance parity
remain unverified; this is an entry diagnostic, not a desktop-speed fix.

**Decision rationale:** Unknown CPU1 context does not forbid a bounded test with
a useful positive outcome. The new record changes CPU0 observation attributes
and storage ownership, not merely the address of another Device marker. It can
reveal execution that the existing channels could not establish. A first Normal
fault can hide subsequent Device evidence, so another negative must not be
advertised as ruling out entry. Firmware cleanup and shared-cluster restoration
are not replayed because their CPU1 necessity/ownership was not established.
Separate research findings are in `research/native31l-first-fetch.md` and
`research/native31l-platform-prepare.md`; proprietary artifacts remain ignored.

### 2026-10-22 · Complete31L locally as an offline verification only

**Observed:** `e1cdf7a`,Python3.13.5,24 image/report test methods PASS with0
skips; both documented commands exit0,OFFLINE_ENTRY_CONTRACT_PASS in reviewed
layout mode. Full symbols NOT RUN on M1. 56 address/112 supplied translation
cases,42 nonidentity/MMU-off mismatches and8 compatible injected hypotheses;
canonical output agrees with released contract except explicit symbol fields.

**Decision:** Retain native31L HOLD/NOT RUN and UNKNOWN effective CPU1 entry;
no restart,proxy connection,hardware query or reuse of a consumed runner.
Frozen inputs and all consumed evidence remain identical. Results/status notes
saved locally; no commit/push requested in this handoff. This software check
does not qualify another physical operation or identify the startup cause.
Evidence: `native/boot/attempt31l-m1-offline-2026-10-22.md`.


### 2026-10-22 · Accept separate31L Normal-memory release after M1 intake

**Preservation:** save a recoverable local snapshot/Git stash of the earlier
uncommitted24-test offline review,fast-forward to `11cc2af`,and carry its status
sections/report forward. The old report is byte-identical; consumed native
receipts and earlier source closures were not changed. The prior no-push/native-
hold wording describes the earlier `e1cdf7a` analysis-only handoff,not this release.

**Decision:** Publish281-pin/796-method image-only intake PASS,both documented
commands and retained13-file package exit0,no skips/repairs. Full symbols NOT
RUN on M1; M5's VM819 methods/60 wire cases/10 assembly comparisons remain
separate evidence. No real discovery or target operation and no31L use receipt.

**Scope:** fresh human-started90s session only after publication. Same CPU1
starts; new owned Normal records/prefixes require CPU0 mapping/control and
pre-start freshness/publication. Every Normal positive/partial/error stops;
only committed expected identity proves this prefix executed. No post-positive
Device comparison,callbacks,extra core,MMIO/reset/settings change,post-start
cache maintenance or Linux continuation. Both-negative remains ambiguous.
Immediate Macintosh HD return on any outcome,no reconnect/retry. Evidence:
`native/boot/attempt31l-m1-intake-2026-10-22.md`.


### 2026-10-22 · Consume31L once; retain negative-channel uncertainty

**Observed:** one authorized31L session consumed on execution/readiness
`c7608c7`, release `11cc2af`: **STOP / cpu1_arrival / cpu1_arrival_timeout**.
Both CPU0 controls PASS (24 reads/2 acknowledged stores each, marker/canaries/
restoration verified); mapping, freshness, reset and publication gates PASS.
Normal vector/cold each **169 samples/507 reads, phase0, no record, identity
not_committed, error null**; total1014 Normal reads. Device vector84 samples/
420 reads and cold169 samples/676 reads also phase0/no committed identity.
**144 mutation intents; CPU1 starts2/2 acknowledged; requests_completed0.**
Four complete PS/state pairs,8 reads each, include final: CPU1 actual0,0,15,15
and opaque byte0,0,2,2; CPU0 remains15/2. Controller5.796s/supervisor6.432s,
exits1/1, no outer deadline or journal/finalization error. Human returned to
usual Macintosh HD at+38.799s, within90s; no retry or post-outcome target command.

**CPU1 prefix execution/entry and effective reset route remain unverified.**
Neither Normal nor Device marker committed identity. Positive CPU0 controls
are not CPU1 visibility proof; negative channels cannot exclude execution or
identify a cache/Device cause. No callbacks, verified park, Linux boot/SMP,
extra-core start or new reset/MMIO/settings operation. Original Full/lab
Permissive/Macintosh HD default remain last reported, not freshly checked.
Existing boot021/boot042/client57a9339,281 pins,frozen K254/J226/I202/host6,
all prior receipts and earlier31L offline evidence remain intact. M5 owns next
interpretation; no automatic retry. Evidence:
`native/boot/attempt31l-2026-10-22-result.md` and its sanitized final JSON.

**Decision:** Publish only reviewed sanitized final JSON and original notes.
Do not infer a CPU1 reset/fetch failure or replay a firmware sequence from these
negative observations. Preserve the consumed invocation and all prior receipts;
M5 reviews the evidence before any separate next proposal.

### 2026-10-22 · Qualify a paired observation before further startup changes

31L is consumed. Both CPU0 controls and the two CPU1 start acknowledgements
passed, but neither Normal nor Device records committed CPU1 identity. Power
state changes are not execution evidence. The audit found no wrong start mask,
entry branch or sampled-field offset.

31M addresses a concrete observation limitation: CPU0 can keep reading a cached
zero after a secondary store. It retains the exact CPU1 prefixes and two starts,
then pairs cached reads with bounded clean-and-invalidate and another read of
the same owned record. Cache maintenance is issued by CPU0 and may propagate
through shareable caches. CPU0 regime, geometry, live dispatch bindings, complete
owned granules and a separate maintenance control must pass before starts.
Any partial/positive/error stops; only a committed expected identity proves CPU1
prefix execution. A maintained positive does not establish cache causality, and
all-zero still cannot exclude execution. No callbacks are authorized.

Three fresh REA/Ghidra queries and 378 independently checked instruction words
separated peripheral reset handling and cluster error capture from application
CPU1 startup. They qualify no new MMIO operation. Original behavioral findings
are public; proprietary bytes and decompiler output remain ignored.

**Offline PASS:** VM072 completed 893 full-symbol methods, 870 image-only methods,
46 actual pinned-client synthetic scenarios and one independent GNU assembly
comparison of the original CTR leaf. New host suites also pass. Source closure:
306 files, `b89a052048cb6af45cf5065a96983df0c6c3012c5d2ec705212310679ac3da97`.
Frozen H/I/J/host/K/L closures and all consumed receipts are unchanged. See
`native/boot/attempt31m/validation.json` for corrections, setup history and limits.

**M1 next:** follow `tools/m1n1-client/attempt31m-instructions.md`, run independent
offline intake and publish readiness before a fresh human-started lab session.
Reuse installed boot021 and retained boot042; no new image transfer or M1 reboot.
One supervised session, immediate Macintosh HD return on any outcome, no retry.
Native31M, CPU1 execution and Linux SMP remain unverified. macOS, volumes,
installed boot images and security/default settings are unchanged this turn;
no repeated policy check is requested.

The target topology remains 12 Performance and 6 Super cores. This attempt tests
CPU1 in CPU0's active Performance cluster. Stable secondary execution, another
cluster, all-core timer/IPI/coherency tests, and measured scheduling/frequency/
energy performance remain subsequent gates; online core count alone is not parity.

**Decision rationale:** A positive CPU0 self-test cannot establish visibility of
CPU1's stores before coherency is known. Paired cached/maintained observation
adds a distinct discriminator without guessing a firmware register or changing
CPU1's prefix. A negative result remains ambiguous and must not trigger an
automatic variant/retry. The next review should revisit reset-entry ownership,
private-cache visibility and the upstream power-emulation findings rather than
add another equivalent marker. No firmware sequence or proprietary code is copied.


### 2026-10-22 · Accept independent31M intake before fresh human start

M1 independently verified release **`24aa8eb`**: **306 pins / 870 image-only
methods PASS**, no skips/repairs; both documented commands and retained13-file
package verification exit0. Mode reviewed_layout_only, Python3.13.5; **M1 full
symbols NOT RUN** (not supplied). Clean client57a9339 and boot021 unchanged.
Manifest `b89a0520…ac3da97`; frozen L281/K254/J226/I202/H186/host6 and all prior
receipts/offline evidence unchanged. **0 discovery/USB/target operations;
six31M live-use files absent; native31M/Linux SMP NOT RUN, invocations0.**

Reviewed cache geometry/ownership, live feature/dispatch binding, separate CPU0
maintenance control and paired stop semantics. Maintenance is CPU0-issued but
may affect shareable caches beyond CPU0. Only an all-zero cached triad permits
fixed owned-record CIVAC and a maintained triad; partial/positive/error stops.
Committed expected identity proves prefix execution, not cache causality or
reset provenance. All-negative remains inconclusive. Same CPU1 prefixes/two
starts; no callbacks, extra core, new MMIO/reset write or Linux continuation.
No code-level blocker found for the bounded diagnostic; native qualification
remains unknown. Publish readiness then await fresh human start/90s timer.
No routine M1 restart/policy check or settings change. Evidence:
`native/boot/attempt31m-m1-offline-2026-10-22.md`.

**Decision:** Preserve every consumed receipt and keep native31M unrun until
the post-publication human start. The existing90s return bound and immediate
Macintosh HD return on any result apply; no automatic retry follows.


### 2026-10-22 · Consume31M once; preserve paired-negative uncertainty

**Observed:** one authorized31M native session consumed on readiness/execution
`f874095`, release `24aa8eb`: **STOP / cpu1_arrival / cpu1_arrival_timeout**.
CPU0 EL2/VHE cache layout qualified: DMinLine64/CWG64,128-byte owned spans.
Device/Normal/maintenance controls PASS, including maintenance48 reads,2 stores
and2 maintenance acknowledgments with marker/canaries/restoration verified.
Both paired channels: **128 samples/768 reads/128 maintenance acknowledgments,
phase0, no record/committed identity, error null**. All258 maintenance requests
acknowledged (2 control+256 paired); no CPU0 post-start record store. Device
vector64 samples/320 reads and cold129/516 also phase0/not_committed, errors null.
**413 mutation intents; CPU1 starts2/2 acknowledged; callbacks planned/completed0.**
Four PS/state pairs complete,8 reads each, including final: CPU1 actual0,0,15,15
and opaque byte0,0,2,2; CPU0 unchanged15/2. Controller5.835s/supervisor6.581s,
exits1/1, no outer deadline or journal/finalization error. Usual Macintosh HD
return confirmed+39.504s, within90s; no retry/post-outcome target operation.

CPU1 execution/effective entry remain unverified. Cached/maintained negatives
cannot exclude execution or identify cache causality; CPU0 controls do not prove
CPU1 visibility. **Linux boot/native SMP NOT RUN**; no extra core, new MMIO/reset
operation or settings change. boot021/boot042/client57a9339,306 pins,frozen
L281/K254/J226/I202/H186/host6 and all prior receipts/evidence intact. Original
Full/lab Permissive/Macintosh HD default remain last reported, not rechecked.
M5 interprets before any separate next proposal; no automatic follow-up. Evidence:
`native/boot/attempt31m-2026-10-22-result.md` and sanitized final JSON.

**Decision:** Retain every consumed receipt and publish only original notes and
reviewed sanitized final JSON. Neither successful CPU0 controls nor the bounded
paired-negative result qualify another native operation or a firmware replay.
M5 reviews the evidence before any new proposal.

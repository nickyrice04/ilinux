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

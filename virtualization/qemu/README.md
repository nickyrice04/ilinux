# GPU-accelerated Omarchy desktop: QEMU + VirGL (workspace build)

Omarchy runs here with a hardware-accelerated desktop. Hyprland renders through
virtio-gpu (VirGL) into macOS OpenGL 4.1 on the M5 Max GPU. QEMU, the VirGL
renderer, libepoxy and libslirp are all built from pinned sources into
`runtime/`. Nothing is installed on macOS (D-012).

```text
guest: Hyprland / Qt / GTK ─ Mesa virgl (GL 4.1 core, GLES 3.0)
          │  virtio-gpu commands
host:  QEMU 11.1.1 (HVF) ─ virglrenderer 1.3.0 ─ libepoxy ─ CGL ─ OpenGL 4.1 (Metal) ─ M5 Max
```

## Build

```bash
virtualization/qemu/build-qemu-virgl.sh            # full stack, ~10 min
ONLY=qemu virtualization/qemu/build-qemu-virgl.sh  # QEMU only, after patch edits
```

* Every archive is SHA-256 pinned. Build tools (meson, ninja, pkg-config)
  come from `tools/venv`. glib, pixman and friends link against Homebrew
  packages that are already installed.
* `downloads/`, `src/`, `runtime/` and `*.log` are gitignored.

**Patch layers, in order:**

1. try-omarchy's QEMU, VirGL and libslirp series (MIT,
   `third_party/try-omarchy`).
2. startergo's macOS VirGL patch set.
3. Local fixes:
   * libepoxy compiles EGL in but treats a missing `libEGL` as "no EGL
     context" instead of calling `abort()`;
   * a VirGL EGL-image guard;
   * the Cocoa GL include.
4. Workspace patches, applied in order:
   * `patches/qemu/0001-cocoa-window-size-and-name.patch`: keeps the Retina
     window size stable (it used to shrink to 487×365 pt), sends the window
     size to the guest at launch, and names the app from `-name`.
   * `patches/qemu/0002-hvf-heterogeneous-vcpus.patch`:
     `-machine virt,bg-vcpus=N[,bg-capacity=C]` gives the last N vCPUs host
     background QoS (M cores) and guest `capacity-dmips-mhz` C (D-019, F-029).
   * `patches/qemu/0003-cocoa-app-nap.patch`: `app-nap=on|off|auto`
     (D-020, F-027).
   * `patches/qemu/0004-virgl-macos-async-fences.patch` and
     `patches/virglrenderer/0001-macos-thread-sync.patch`: event-driven
     VirGL fences on macOS, replacing the 1 ms polling (D-021, F-030).
   * `patches/qemu/0005-file-posix-macos-f-nocache.patch`: `cache.direct`
     uses `F_NOCACHE` instead of O_DSYNC on macOS (F-033).
   * `patches/qemu/0006-cocoa-adaptive-refresh.patch`: the display timer
     drops to 100 ms after a second without frames, instead of waking QEMU
     at 120 Hz forever.
   * `patches/qemu/0007-coreaudio-capture.patch`: microphone input. The
     CoreAudio backend had none, so this adds an AudioQueue on the default
     input device.
   * **Guest Vulkan (Venus on MoltenVK, D-027, F-035–F-038):**
     * `patches/qemu/0008-virgl-venus-in-process-macos.patch`: Venus is
       served by an in-process render-server thread.
     * `patches/qemu/0009-virgl-no-map-fixed-on-macos.patch`: blobs are RAM
       subregions; HVF ignores `MAP_FIXED` remaps.
     * `patches/qemu/0010-hvf-map-venus-blobs-in-host-pages.patch`:
       sub-page blobs are mapped in whole 16 KiB host pages.
     * `patches/virglrenderer/0002`–`0006`: the loader path, proxy init for
       Venus, stream sockets with partial reads, and the
       `VK_EXT_external_memory_metal` table entry.
     * `patches/virglrenderer/0007-vrend-cgl-iosurface-mirror-for-venus-images.patch`:
       compositors import Venus swapchain images through an IOSurface
       mirror. `VIRGL_IOSURFACE_MIRROR_STATS=1` logs its cost.
   * **Hardware video decode (VideoToolbox behind the guest's VA-API, D-029,
     F-042–F-046):**
     * `patches/virglrenderer/0008-vrend-videotoolbox-video-backend.patch`:
       virglrenderer's video interface on VideoToolbox. H.264 (Constrained
       Baseline, Main, High) decodes on the Mac's media engine, and the
       decoded IOSurface's planes are copied into the guest's video surfaces
       on the GPU. Diagnostics: `VIRGL_VIDEO_DEBUG=1` (per-frame timing),
       `VIRGL_VIDEO_MD5=<file>` (per-frame MD5 of the decoded picture),
       `VIRGL_VIDEO_SYNC=finish` (wait for the copies every frame).
     * `patches/virglrenderer/0009-vrend-shader-tex-temporary-writemask.patch`:
       fixes a shader-translation bug in the macOS patch set that broke
       Mesa's video compositor shaders.
     * `patches/qemu/0011-virtio-gpu-gl-video-property.patch`: the
       `video=on|off` device property.
   * `patches/qemu/0012-cocoa-display-path-measurement-switches.patch`:
     `COCOA_GL_NOPRESENT=1` consumes guest frames without drawing them, and
     `COCOA_GL_LATENCY=1` logs flush-to-draw latency. Both need the window on
     screen, because macOS doesn't draw hidden windows (F-049).
   * `patches/qemu/0013-cocoa-draw-on-flush-iosurface-presenter.patch`
     (D-030, F-051):
     * A guest frame is drawn as soon as the guest flushes it, not at the
       next GUI tick. Flush-to-draw went from p50 7 ms to 0.14 ms, and every
       frame is drawn at 120 fps.
     * `COCOA_GL_PRESENT=iosurface` is an opt-in presenter that copies on
       QEMU's thread into IOSurfaces. p50 is 0.12 ms, but 4K60 video costs
       +0.8 W.
     * Measurement aids:
       * `COCOA_FLOAT=1` keeps the VM window on screen on every Space;
       * `COCOA_GL_PRESENT_CHECK=1` counts torn frames;
       * `COCOA_GL_PRESENT_DUMP=<file.ppm>` writes one presented frame.
   * `patches/virglrenderer/0010-vrend-macos-fence-wait-without-spinning.patch`:
     Apple's `glClientWaitSync` busy-polls for its whole timeout, so the
     fence thread now polls and sleeps instead of spinning while it waits:
     about 0.3–0.4 W less in 4K60 playback, same glmark2 throughput (F-047).
5. Vulkan stage: Khronos Vulkan-Headers and Vulkan-Loader (SDK 1.4.363.0,
   built) and the MoltenVK 1.4.2 release ICD (copied), all SHA-256 pinned.
6. `spice-protocol` headers (SHA-256 published by spice-space.org) enable
   QEMU's `qemu-vdagent` for clipboard sharing.

## Omarchy.app (double-click launcher)

```bash
virtualization/app/build-omarchy-app.sh    # rerun after rebuilding QEMU
```

This builds `virtualization/app/Omarchy.app`, which stays in the workspace
(drag it to the Dock if you like).

* **What it is:** a small Mach-O stub, a launch script, and a signed copy of
  QEMU (libraries and data stay in `runtime/`).
* **Identity:** macOS shows "Omarchy" in the Dock and window list, and
  attributes the microphone and Accessibility prompts to it.
* **Default launch:** `--hetero --fullscreen --console-socket`. Put
  `OPTIONS=(...)` in `virtualization/run/omarchy-app.conf` to change it,
  e.g. `OPTIONS=(--hetero --console-socket)` for a window, or add
  `--full-grab`.
* **First launch:** the app is ad-hoc signed and built locally, so Gatekeeper
  does not know it. Right-click → Open once.

## Run

```bash
virtualization/qemu/run-omarchy-gpu.sh [--fullscreen] [--full-grab] [--hetero] [--no-venus] [--no-video] [--console-socket]
```

| Option | Effect |
|---|---|
| (default) | Resizable window. The guest resolution follows the window's backing pixels, and Hyprland uses scale 2. A 1296×729 pt window gives a 2592×1458 guest at 120 Hz |
| `--fullscreen` | Omarchy gets its own macOS Space with the menu bar and Dock hidden. The guest runs at the panel's native safe area, 3456×2160 at scale 2 (1728×1080 logical). Switch Spaces with a 4-finger swipe |
| `--full-grab` | While the window is focused, Cmd-Space, Cmd-Tab and other system chords go to Hyprland (Cmd = Super). macOS asks once to allow Accessibility for the QEMU binary. Each rebuild changes the ad-hoc signature and needs the grant again |
| `--hetero` | 18 vCPUs as 3 clusters of 6, mirroring the M5 Max. The last cluster runs at host background QoS (M cores) and appears to Linux at capacity 220/1024. `omarchy-qos` puts `background.slice` there and keeps everything else off it |
| `--no-venus` | Turns off guest Vulkan. By default `virtio-gpu-gl` runs with `venus=on,blob=on,hostmem=4G` (`VENUS_HOSTMEM` env), so Vulkan apps run on the M5 Max GPU through Venus and MoltenVK, at 94–98% of native compute. Desktop GL is unaffected either way |
| `--no-video` | Turns off hardware video decode. By default `virtio-gpu-gl` runs with `video=on`: the guest's VA-API driver (Mesa virgl, `vainfo` shows `VAProfileH264High`) decodes H.264 on the Mac's media engine through VideoToolbox. Apps use it the usual way: `mpv --hwdec=vaapi`, `ffmpeg -hwaccel vaapi`, GStreamer `va` |
| `--no-clipboard` | Turns off clipboard sharing. By default text is shared both ways through `qemu-vdagent` and the guest `ilinux-clipboard-agent`, fetched only when someone pastes |
| `DISK_CACHE=writeback\|none`, `DISK_IOTHREAD=1\|0` (env) | Disk path. The default is `writeback` on a dedicated iothread with 4 queues: warm small I/O at native latency. `none` bypasses the host page cache (`F_NOCACHE`): 4 GB/s writes, cold reads at 100%, no double caching (F-033) |
| `APP_NAP=on\|off\|auto` (env) | macOS App Nap policy. Default `auto`: a hidden, idle VM naps, but a hidden VM doing foreground work runs at full speed |
| `--console-socket` | Root shell on `virtualization/run/console.sock`; drive it with `tools/vmconsole.py` and `tools/vmpush.py` |
| `--job DIR` | 9p share with tag `job`, for scripted runs |
| `--headless` | No display |

The launcher also provides:

* `tools/bin/ilinux-host-agent`, built on demand and exiting with QEMU. It
  feeds the battery, the clock after the Mac sleeps, and the time zone into
  the guest (`org.ilinux.host`).
* An HMP monitor on `virtualization/run/monitor.sock`.
* `-pidfile` and a single-instance guard. A second launch would otherwise
  unlink the running VM's sockets.
* `free-page-reporting` on the balloon.
* `discard=unmap` on the disk.

**Test VM account:** user `omarchy` (password is in job 009's provisioning
script). SDDM logs this user in automatically (D-016), and hyprlock still
locks the session on idle.

## Verified (2026-10-12)

**Guest renderer:**

* `virgl (Apple M5 Max)`, OpenGL 4.1 Core / Compatibility, OpenGL ES 3.0,
  Mesa 26.2.4.
* The host side reports `OpenGL 4.1 (Metal)`, renderer `Apple M5 Max`, MSAA
  up to 8×.

**Desktop:**

* The Omarchy 4.0.4 shell (Quickshell on Qt 6.12) and Hyprland 0.56.2 run
  at 2592×1458 at 120 Hz, scale 2.
* The bar, notifications and lock screen are themed. This needed the Qt 6.12
  compatibility fix in `omarchy-arm64/configuration/compat/` (D-017).

**Performance** (`reports/vm-vs-macos-parity.md`):

* GPU shader ALU runs at 99.7% of macOS OpenGL. Blended fill is 74%, draw
  calls 50%, texture upload 28% and readback 61%.
* CPU foreground single-thread is 99% of native.
* The background tier is 1.84–2.25× more energy-efficient than foreground.
* An idle desktop costs +0.09 W of SoC power (`app-nap=auto`).

**Integration:**

* The host bridge shows the Mac battery in the bar, keeps the guest clock
  right after host sleep (tested: a 30 s lag was stepped within one 60 s
  cycle), and follows the Mac time zone.
* Omarchy's idle policy works: screensaver at 150 s, lock at 300 s, then
  DPMS off. With DPMS off the guest stops rendering.

**Hardware video decode** (`benchmarks/vm/playback_power.py`, F-046):

* `vainfo` lists `VAProfileH264High : VAEntrypointVLD` (plus Main and
  Constrained Baseline).
* A 1080p60 High-profile clip with B-frames decodes bit-exact against
  FFmpeg's software decoder: 600/600 frames, 0 errors.
* mpv `--hwdec=vaapi --vo=gpu --gpu-api=opengl` uses zero-copy EGL dmabuf
  interop and plays 4K60 and 1080p60 in real time, fullscreen at 120 Hz,
  with 0–2 dropped frames per 1,500.
* Whole-SoC playback power, the same clips looped for 25 s (ABBA order, AC
  power). The native reference is AVFoundation in a window of the same size,
  with the VM off:

  | Clip | VM, hardware decode | VM, software decode | macOS native |
  |---|---|---|---|
  | 4K60 H.264, 60 Mbps | 7.0 W (mpv defaults), 3.9 W (`profile=fast`) | 17.3 W | 2.9 W |
  | 1080p60 H.264, 20 Mbps | 4.3 W (mpv defaults) | 6.7 W | 2.4 W |

  Idle is about 1.9 W either way.
* Decode alone (FFmpeg paced, nothing displayed) is 3.0 W at 4K60. Most of
  the rest was mpv's default scaling, so the VM now ships `profile=fast`
  (F-048).
* The VM window was off screen in these runs, so QEMU's draw and
  WindowServer's compositing are not included. The native window was on
  screen (F-049).
* With the VM window on screen, 4K60 playback with the VM defaults measured
  3.6–4.1 W across five sessions, against 2.9 W native. Presenting
  (QEMU's draw plus WindowServer) is about +0.3 W of that.

## Known gaps

* **Microphone:** capture works through patch 0007. The first recording
  shows the macOS microphone prompt. Launched from `Omarchy.app`, the prompt
  names Omarchy; from a terminal, it names that terminal app. The mic is
  open only while a guest app records.
* **Screenshots:** QEMU `screendump` can't read GL scanouts. Use `grim`
  inside the guest instead.
* **Vulkan presentation copies:** each presented frame costs two GPU copies
  (Metal blit into an IOSurface, GL blit into the compositor's texture) and
  about 0.12 ms of QEMU main-thread time. Zero-copy is future work (D-027).
* **Vulkan FIFO pacing** depends on `MESA_VK_WSI_DEBUG=nowlts` in the guest
  session (D-028) until QEMU provides paced vblank timestamps.
* **Debugging in the guest:** gdb can't attach (SME without SVE, F-039). Use
  `eu-stack` and `strace`.
* **Video decode scope:** H.264 only so far. HEVC, VP9 and AV1 decode and all
  encode are not offered yet.
* **Video readback:** same-format downloads work; the observed failure is
  cross-format GPU conversion, correcting the broader F-045 hypothesis.
  The installed optional [Mesa package](../../omarchy-arm64/packages/mesa-virgl-video/README.md)
  fixes tested even progressive NV12/I420/YV12 downloads. Odd crops, scaling,
  interlacing and other formats remain unvalidated (F-052).
* **Planar surfaces:** the same package's `ilinux-video` wrapper selects
  NV12 H.264 decode and avoids the host planar conversion. Paced 4K60 decode
  used 41.3% less QEMU CPU time across two ABBA blocks (F-053). Applications
  must opt in; no display-power improvement is established by that test.

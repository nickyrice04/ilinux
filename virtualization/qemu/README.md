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
5. `spice-protocol` headers (SHA-256 published by spice-space.org) enable
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
virtualization/qemu/run-omarchy-gpu.sh [--fullscreen] [--full-grab] [--hetero] [--console-socket]
```

| Option | Effect |
|---|---|
| (default) | Resizable window. The guest resolution follows the window's backing pixels, and Hyprland uses scale 2. A 1296×729 pt window gives a 2592×1458 guest at 120 Hz |
| `--fullscreen` | Omarchy gets its own macOS Space with the menu bar and Dock hidden. The guest runs at the panel's native safe area, 3456×2160 at scale 2 (1728×1080 logical). Switch Spaces with a 4-finger swipe |
| `--full-grab` | While the window is focused, Cmd-Space, Cmd-Tab and other system chords go to Hyprland (Cmd = Super). macOS asks once to allow Accessibility for the QEMU binary. Each rebuild changes the ad-hoc signature and needs the grant again |
| `--hetero` | 18 vCPUs as 3 clusters of 6, mirroring the M5 Max. The last cluster runs at host background QoS (M cores) and appears to Linux at capacity 220/1024. `omarchy-qos` puts `background.slice` there and keeps everything else off it |
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

## Known gaps

* **Microphone:** `hda-micro` has no capture with the CoreAudio backend
  (`Can not open 'adc'`).
* **Screenshots:** QEMU `screendump` can't read GL scanouts. Use `grim`
  inside the guest instead.
* **No Vulkan in the guest:** Venus is not built. This needs MoltenVK and is
  a candidate next step.

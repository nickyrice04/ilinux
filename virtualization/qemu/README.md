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
4. `patches/qemu-cocoa-window-size-and-name.patch`:
   * keeps the Retina window size stable (it used to shrink to 487×365 pt);
   * sends the window size to the guest at launch;
   * names the app from `-name`.

## Run

```bash
tools/bin/mac-battery-feed --unix virtualization/run/battery.sock &   # Mac battery -> guest
virtualization/qemu/run-omarchy-gpu.sh [--fullscreen] [--full-grab] [--console-socket]
```

| Option | Effect |
|---|---|
| (default) | Resizable window. The guest resolution follows the window's backing pixels, and Hyprland uses scale 2. A 1296×729 pt window gives a 2592×1458 guest at 120 Hz |
| `--fullscreen` | Omarchy gets its own macOS Space with the menu bar and Dock hidden. The guest runs at the panel's native safe area, 3456×2160 at scale 2 (1728×1080 logical). Switch Spaces with a 4-finger swipe |
| `--full-grab` | While the window is focused, Cmd-Space, Cmd-Tab and other system chords go to Hyprland (Cmd = Super). macOS asks once to allow Accessibility for the QEMU binary. Each rebuild changes the ad-hoc signature and needs the grant again |
| `--console-socket` | Root shell on `virtualization/run/console.sock`; drive it with `tools/vmconsole.py` and `tools/vmpush.py` |
| `--job DIR` | 9p share with tag `job`, for scripted runs |
| `--headless` | No display |

The launcher also provides:

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

**Integration:**

* The battery bridge shows the Mac battery in the bar.
* Omarchy's idle policy works: screensaver at 150 s, lock at 300 s, then
  DPMS off. With DPMS off the guest stops rendering.

## Known gaps

* **Microphone:** `hda-micro` has no capture with the CoreAudio backend
  (`Can not open 'adc'`).
* **Screenshots:** QEMU `screendump` can't read GL scanouts. Use `grim`
  inside the guest instead.
* **No Vulkan in the guest:** Venus is not built. This needs MoltenVK and is
  a candidate next step.

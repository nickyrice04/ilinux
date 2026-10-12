# Virtualization: disposable Linux test environments

Everything here stays inside the workspace. Nothing is installed on macOS.

## Components

| Path | What |
|---|---|
| `vzrun/main.swift`, `vzrun/build.sh` | Minimal Virtualization.framework VM runner. Ad-hoc signed with `com.apple.security.virtualization`; output in `bin/vzrun` (gitignored). Supports direct kernel boot or EFI, raw disks, ISO, virtiofs shares, NAT, nested virtualization (M3+) and a GUI window |
| `guest/customize.sh` | Turns an extracted Arch Linux ARM rootfs into a test guest: fstab, HTTPS mirror, **job runner**, hvc0 autologin, sshd masked |
| `scripts/build-alarm-image.sh` | Builds `images/alarm/root.img` (sparse ext4). Steps: GPG-verifies the ALARM tarball against the pinned key `68B3537F39A313B3E574D06777193F152BDBE6A6`, extracts it, customizes it and runs `mkfs.ext4 -d`. Docker Desktop is used only as a Linux userland for these steps |
| `jobs/NNN-*/run.sh` | Scripted test jobs. The guest mounts the job dir (virtiofs tag `job`), runs `run.sh` as root, writes `out/run.log`, and powers off |
| `images/` | Downloads, kernel `Image`, and disk images (gitignored) |

## Run a job

```bash
I=virtualization/images/alarm
virtualization/bin/vzrun --cpus 18 --mem 32 --kernel $I/Image --cmdline "$(cat $I/cmdline)" \
  --disk $I/root.img --share virtualization/jobs/001-sysinfo:job < /dev/null
```

Add more read-only shares with `--share <dir>:<tag>:ro` (e.g. `models`,
`omarchy`). The ALARM 7.1.6 kernel has virtio-blk/pci/console and ext4 built
in, so no initramfs is needed.

## What the VM can and cannot tell us (measured 2026-10-11)

* **CPU:** near-native. Integer, sort and SGEMM run at 91–100% of macOS, and
  SME runs at 96–101%. **SME2 is exposed to the guest** (SVL 512 bits).
* **MIDR is masked** as `0x610f0000` (Apple, part 0x000), so real core IDs
  can't be read from a VM.
* **Wakeups are expensive.** A pipe ping-pong round trip takes 21–52 µs in
  the guest vs 3.7 µs on macOS, because cross-vCPU wakeups go through the
  hypervisor.
* **Syscalls:** `getppid` costs ~113 ns in the guest vs 85 ns on macOS.
* **Memory:** 4K guest pages and two-stage translation raise large-buffer
  latency (≈128 vs 108 ns at 256 MiB). STREAM medians are close to native.
  "Best" values are unreliable because of vCPU preemption.
* **No GPU acceleration in Virtualization.framework:** it exposes virtio-gpu 2D only. See "GPU in the VM" below for the QEMU engine.
* **Storage modes (job 005, F-018).** Extra `--disk` images honour
  `--disk-sync full|fsync|none`, `--disk-cache automatic|cached|uncached`
  and `--nvme`.
  * Durable best is virtio + `fsync`: ≈ 5.6 GB/s read single-threaded, 8.6
    GB/s with 4 threads (native 11–13).
  * `cached`/`none` serves from the host page cache. Fastest, but not
    crash-safe, so use it for scratch disks only.
  * Sparse images pay a one-time allocation cost on first write.

## GPU in the VM (2026-10-12)

| Path | Status | Measured |
|---|---|---|
| **Desktop:** QEMU/HVF + VirGL to macOS OpenGL 4.1 (`qemu/`, workspace build, D-012) | **Working.** The Omarchy 4 desktop (Hyprland and the Quickshell bar) is accelerated at Retina resolution | Guest `virgl (Apple M5 Max)`, GL 4.1 core, GLES 3.0 |
| **Compute:** guest llama.cpp → ggml RPC → vsock → host `ggml-rpc-server` (Metal), job 017 | **Working** | Q4_0 8B: prefill 89%, generation 81% of native Metal |
| Venus (Vulkan) → MoltenVK → Metal | Not built yet. Needs MoltenVK in the workspace | Published M2 Max data: ≈ 50–57% for llama.cpp |
| llama.cpp GGML-VirtGPU (API remoting) | Not tried | Could use the M5 matrix units; no published numbers |

Virtualization.framework (`vzrun`) remains the engine for headless jobs
(CPU, memory and storage benchmarks, builds). The QEMU engine is used for
the desktop.

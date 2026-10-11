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
* **No GPU acceleration.** The framework exposes virtio-gpu 2D only.
* **Storage modes (job 005, F-018).** Extra `--disk` images honour
  `--disk-sync full|fsync|none`, `--disk-cache automatic|cached|uncached`
  and `--nvme`.
  * Durable best is virtio + `fsync`: ≈ 5.6 GB/s read single-threaded, 8.6
    GB/s with 4 threads (native 11–13).
  * `cached`/`none` serves from the host page cache. Fastest, but not
    crash-safe, so use it for scratch disks only.
  * Sparse images pay a one-time allocation cost on first write.

## GPU-in-VM options (not installed; each needs a host install, so new approval)

| Option | Path | Expected |
|---|---|---|
| krunkit / libkrun (podman machine or Lima `vmType: krunkit`) | virtio-gpu Venus → virglrenderer → MoltenVK → Metal | ≈ 50–57% of native Metal for llama.cpp (published M2 Max data) |
| llama.cpp GGML-VirtGPU (API remoting) | guest ggml forwards graphs to host `ggml-metal` | Could use the M5 GPU matrix units. Untested on macOS 26; no published numbers |
| QEMU/HVF + VirGL (UTM, try-omarchy) | OpenGL ≤ 4.3 / GLES 3 for the desktop | Accelerated Hyprland desktop; not compute |

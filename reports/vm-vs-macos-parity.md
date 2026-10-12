### Linux VM vs macOS, identical code and target flags (-O3 -mcpu=apple-m4), medians

| bench | test | threads / size | unit | reference | candidate | parity |
|---|---|---|---|---|---|---|
| cpu | fma | 1 | GFLOP/s | 125.3 | 140.9 | 112.5% |
| cpu | fma | 6 | GFLOP/s | 690.5 | 740.6 | 107.3% |
| cpu | fma | 12 | GFLOP/s | 1182 | 1253 | 106.0% |
| cpu | fma | 18 | GFLOP/s | 1621 | 1667 | 102.9% |
| cpu | freq | 1 | GHz(est) | 4.512 | 4.461 | 98.9% |
| cpu | freq | 6 | GHz(est) | 24.95 | 24.74 | 99.2% |
| cpu | freq | 12 | GHz(est) | 51.05 | 49.96 | 97.9% |
| cpu | freq | 18 | GHz(est) | 73.73 | 73.08 | 99.1% |
| cpu | intmix | 1 | Gop/s | 21.02 | 20.78 | 98.9% |
| cpu | intmix | 6 | Gop/s | 115.9 | 114 | 98.3% |
| cpu | intmix | 12 | Gop/s | 190.7 | 187.4 | 98.3% |
| cpu | intmix | 18 | Gop/s | 251.4 | 248.4 | 98.8% |
| cpu | pipe_pingpong_roundtrip | 1 | us | 3.838 | 52.01 | 7.4% |
| cpu | sgemm | 1 | GFLOP/s | 60.29 | 60.19 | 99.8% |
| cpu | sgemm | 6 | GFLOP/s | 315.3 | 318.3 | 100.9% |
| cpu | sgemm | 12 | GFLOP/s | 497.5 | 487.9 | 98.1% |
| cpu | sgemm | 18 | GFLOP/s | 598.5 | 585.8 | 97.9% |
| cpu | sme_bf16 | 1 | GFLOP/s | 2174 | 2137 | 98.3% |
| cpu | sme_f32 | 1 | GFLOP/s | 2173 | 2138 | 98.4% |
| cpu | sme_f32 | 2 | GFLOP/s | 2591 | 2583 | 99.7% |
| cpu | sme_f32 | 3 | GFLOP/s | 3029 | 2946 | 97.3% |
| cpu | sme_f32 | 6 | GFLOP/s | 3159 | 3154 | 99.8% |
| cpu | sme_f32 | 12 | GFLOP/s | 3213 | 3200 | 99.6% |
| cpu | sme_f32 | 18 | GFLOP/s | 3233 | 3183 | 98.5% |
| cpu | sme_i8 | 1 | Gop/s | 4347 | 4277 | 98.4% |
| cpu | sme_i8 | 2 | Gop/s | 5108 | 5037 | 98.6% |
| cpu | sme_i8 | 3 | Gop/s | 5781 | 5792 | 100.2% |
| cpu | sme_i8 | 6 | Gop/s | 6296 | 6311 | 100.2% |
| cpu | sme_i8 | 12 | Gop/s | 6398 | 6373 | 99.6% |
| cpu | sme_i8 | 18 | Gop/s | 6463 | 6356 | 98.3% |
| cpu | sort | 1 | Melem/s | 23.45 | 23.39 | 99.8% |
| cpu | sort | 6 | Melem/s | 129.9 | 130 | 100.1% |
| cpu | sort | 12 | Melem/s | 263.6 | 262.2 | 99.4% |
| cpu | sort | 18 | Melem/s | 380.7 | 375.8 | 98.7% |
| cpu | syscall_getppid | 1 | ns | 86.83 | 113.3 | 76.7% |
| mem | anon_first_touch | 4096 | GB/s | 30.15 | 10.47 | 34.7% |
| mem | latency_random_chase | 16 | ns | 0.7 | 0.67 | 104.5% |
| mem | latency_random_chase | 32 | ns | 0.7 | 0.67 | 104.5% |
| mem | latency_random_chase | 64 | ns | 0.7 | 0.67 | 104.5% |
| mem | latency_random_chase | 96 | ns | 0.7 | 0.66 | 106.1% |
| mem | latency_random_chase | 128 | ns | 0.7 | 0.67 | 104.5% |
| mem | latency_random_chase | 192 | ns | 2.54 | 2.37 | 107.2% |
| mem | latency_random_chase | 256 | ns | 2.76 | 2.62 | 105.3% |
| mem | latency_random_chase | 512 | ns | 2.8 | 2.67 | 104.9% |
| mem | latency_random_chase | 1024 | ns | 4.31 | 4.33 | 99.5% |
| mem | latency_random_chase | 2048 | ns | 7.61 | 8.26 | 92.1% |
| mem | latency_random_chase | 4096 | ns | 8.17 | 8.67 | 94.2% |
| mem | latency_random_chase | 8192 | ns | 9.31 | 9.91 | 93.9% |
| mem | latency_random_chase | 12288 | ns | 13.75 | 19.61 | 70.1% |
| mem | latency_random_chase | 16384 | ns | 18.84 | 27.74 | 67.9% |
| mem | latency_random_chase | 24576 | ns | 32.48 | 45.19 | 71.9% |
| mem | latency_random_chase | 32768 | ns | 56.6 | 71.48 | 79.2% |
| mem | latency_random_chase | 49152 | ns | 91.48 | 110.5 | 82.8% |
| mem | latency_random_chase | 65536 | ns | 101.6 | 116.9 | 86.9% |
| mem | latency_random_chase | 98304 | ns | 105.4 | 120.1 | 87.7% |
| mem | latency_random_chase | 131072 | ns | 106.5 | 121.8 | 87.4% |
| mem | latency_random_chase | 262144 | ns | 108.4 | 128.4 | 84.5% |
| mem | latency_random_chase | 524288 | ns | 109.7 | 134.4 | 81.6% |
| mem | latency_random_chase | 1048576 | ns | 110.8 | 142.2 | 77.9% |
| mem | latency_random_chase | 2097152 | ns | 111.9 | 154.5 | 72.5% |
| mem | latency_random_chase_dit | 16 | ns | 0.66 | 0.67 | 98.5% |
| mem | latency_random_chase_dit | 32 | ns | 0.66 | 0.67 | 98.5% |
| mem | latency_random_chase_dit | 64 | ns | 0.66 | 0.67 | 98.5% |
| mem | latency_random_chase_dit | 96 | ns | 0.66 | 0.67 | 98.5% |
| mem | latency_random_chase_dit | 128 | ns | 0.67 | 0.67 | 100.0% |
| mem | latency_random_chase_dit | 192 | ns | 2.42 | 2.37 | 102.1% |
| mem | latency_random_chase_dit | 256 | ns | 2.62 | 2.62 | 100.0% |
| mem | latency_random_chase_dit | 512 | ns | 2.7 | 2.67 | 101.1% |
| mem | latency_random_chase_dit | 1024 | ns | 5.6 | 5.06 | 110.7% |
| mem | latency_random_chase_dit | 2048 | ns | 7.26 | 8.27 | 87.8% |
| mem | latency_random_chase_dit | 4096 | ns | 7.77 | 8.84 | 87.9% |
| mem | latency_random_chase_dit | 8192 | ns | 8.79 | 11.2 | 78.5% |
| mem | latency_random_chase_dit | 12288 | ns | 14.87 | 17.61 | 84.4% |
| mem | latency_random_chase_dit | 16384 | ns | 19.18 | 25.09 | 76.4% |
| mem | latency_random_chase_dit | 24576 | ns | 33.34 | 44.17 | 75.5% |
| mem | latency_random_chase_dit | 32768 | ns | 58.36 | 81.61 | 71.5% |
| mem | latency_random_chase_dit | 49152 | ns | 91.4 | 109.8 | 83.2% |
| mem | latency_random_chase_dit | 65536 | ns | 104 | 116.7 | 89.1% |
| mem | latency_random_chase_dit | 98304 | ns | 105 | 120 | 87.5% |
| mem | latency_random_chase_dit | 131072 | ns | 106.3 | 121.9 | 87.2% |
| mem | latency_random_chase_dit | 262144 | ns | 108.2 | 128.8 | 84.0% |
| mem | stream_add | 1 | GB/s | 121.7 | 119.5 | 98.1% |
| mem | stream_add | 2 | GB/s | 227.8 | 205.9 | 90.4% |
| mem | stream_add | 4 | GB/s | 323.1 | 308.7 | 95.5% |
| mem | stream_add | 6 | GB/s | 345.6 | 336.7 | 97.5% |
| mem | stream_add | 12 | GB/s | 343.7 | 317.2 | 92.3% |
| mem | stream_add | 18 | GB/s | 344.5 | 340.2 | 98.8% |
| mem | stream_copy | 1 | GB/s | 136.8 | 110.5 | 80.8% |
| mem | stream_copy | 2 | GB/s | 247.4 | 188.3 | 76.1% |
| mem | stream_copy | 4 | GB/s | 347.7 | 322 | 92.6% |
| mem | stream_copy | 6 | GB/s | 377.1 | 349.8 | 92.7% |
| mem | stream_copy | 12 | GB/s | 355.7 | 343.9 | 96.7% |
| mem | stream_copy | 18 | GB/s | 369.1 | 367.1 | 99.5% |
| mem | stream_scale | 1 | GB/s | 121.2 | 113.4 | 93.6% |
| mem | stream_scale | 2 | GB/s | 232.4 | 196.1 | 84.4% |
| mem | stream_scale | 4 | GB/s | 348.1 | 323.6 | 93.0% |
| mem | stream_scale | 6 | GB/s | 372.6 | 352.4 | 94.6% |
| mem | stream_scale | 12 | GB/s | 361.5 | 344.5 | 95.3% |
| mem | stream_scale | 18 | GB/s | 366.9 | 365.9 | 99.7% |
| mem | stream_triad | 1 | GB/s | 121.6 | 120.8 | 99.3% |
| mem | stream_triad | 2 | GB/s | 228.7 | 201.4 | 88.1% |
| mem | stream_triad | 4 | GB/s | 323.1 | 310.3 | 96.0% |
| mem | stream_triad | 6 | GB/s | 345.1 | 337.3 | 97.7% |
| mem | stream_triad | 12 | GB/s | 344.9 | 316.9 | 91.9% |
| mem | stream_triad | 18 | GB/s | 343.6 | 341.3 | 99.3% |
| storage | randread | 1 | IOPS | 1.668e+04 | 9570 | 57.4% |
| storage | randread | 8 | IOPS | 1.356e+05 | 4.868e+04 | 35.9% |
| storage | randread | 32 | IOPS | 2.668e+05 | 7.874e+04 | 29.5% |
| storage | randwrite | 1 | IOPS | 1.236e+04 | 7444 | 60.2% |
| storage | randwrite | 8 | IOPS | 4.895e+04 | 5.805e+04 | 118.6% |
| storage | seqread | 1 | MB/s | 1.108e+04 | 1450 | 13.1% |
| storage | seqread | 4 | MB/s | 1.32e+04 | 3470 | 26.3% |
| storage | seqwrite | 1 | MB/s | 1.118e+04 | 335.3 | 3.0% |

---

## QEMU desktop VM (HVF + VirGL), 2026-10-12

This is the engine behind the GPU-accelerated Omarchy desktop
(`virtualization/qemu/`). The CPU results above came from the
Virtualization.framework VM. Raw data is in
`benchmarks/results/vm-qemu-2026-10-12/`.

### GPU: `glbench`, identical GL 4.1 core code (macOS CGL vs guest Mesa virgl), 2592×1458, medians of 3

| Test | macOS GL (Metal) | VM, 1 ms fence poll (before) | VM, async fences (now) | Parity now |
|---|---|---|---|---|
| Fragment ALU (FMA) | 12.35 TFLOPS | 11.35 | 12.31 | **99.7%** |
| Blended fill (16 layers per sync) | 200.7 Gpix/s | 33.8 | 149.4 | 74% |
| Draw calls (with uniform update) | 2.42 M/s | 1.107 | 1.217 | 50% |
| Texture upload (2048² RGBA8) | 48.0 GB/s | 12.0 | 13.4 | 28% |
| Readback (`glReadPixels`) | 11.57 GB/s | 2.63 | 7.06 | 61% |

* For reference, the Metal compute peak (session 1) is 14.75 TFLOPS FP32.
  GL fragment shading reaches 84% of it, natively and in the VM alike.

### GPU: Vulkan (Venus on MoltenVK, default since D-027)

`vkcompute` uses identical SPIR-V on both sides: native MoltenVK 1.4.2 vs
guest Mesa Venus. FMA throughput runs over a 4M-element buffer.

| Test | macOS (MoltenVK) | VM (Venus) | Parity |
|---|---|---|---|
| FP32 FMA throughput (median) | 11.24 TFLOPS | 10.6–11.0 | **94–98%** |
| Correctness vs CPU `fmaf` | exact | exact | identical |
| Submit + wait round trip (p50) | 204 µs | 381–390 µs | 1.9× slower |

Presentation in the VM uses vkcube at 1272×679 RGBA16F in Hyprland on the
2592×1458@120 output:

| Mode | VM result | Note |
|---|---|---|
| FIFO (vsync) | **119.5 fps** | 92.9 before D-028; no frames before QEMU 0010 |
| Mailbox | ~3,000 fps | client-side Venus path is not the limit |
| Per-frame host cost | 0.12 ms main thread + two GPU copies | IOSurface mirror (virgl 0007) |

* GL with Venus/blob on vs off (glbench): alu 0.99×, fill 1.01×, draws 0.99×,
  upload 1.17×, readback 1.06×.
* Raw data: `benchmarks/results/vm-qemu-2026-10-12/vulkan/` and
  `gpu/glbench-vm-virgl-venus-blob.jsonl`.

### CPU: heterogeneous vCPUs (`--hetero`), guest `cpubench intmix` (clang `-mcpu=apple-m4`) under host `powermon`

| Placement | Threads | Guest Gop/s | Host CPU W | Gop/s per W |
|---|---|---|---|---|
| Native macOS, default QoS | 1 | 20.97 | 7.21 | 2.91 |
| VM, foreground vCPU | 1 | 20.79 (99%) | 6.49 | 3.20 |
| VM, `omarchy-qos run background` | 1 | 4.51 | 0.77 | 5.89 (1.84× foreground) |
| VM, foreground vCPUs | 6 | 111.3 | 15.79 | 7.05 |
| VM, `omarchy-qos run background` | 6 | 21.8 | 1.37 | 15.9 (2.25× foreground) |

### Idle power (SoC sum, IOReport): back-to-back A/B, 3 × 30 s

| State | SoC W | vs host only |
|---|---|---|
| Host only (VM off) | 1.713 | — |
| VM idle desktop, `app-nap=auto` | 1.799 | +0.09 W |
| VM idle desktop, `app-nap=off` | 1.855 | +0.14 W |

### Storage: `storbench`, guest btrfs nocow file on virtio-blk vs macOS APFS (`F_NOCACHE`), 4 GiB file

| Test | macOS native | VM writeback, main loop (old) | VM writeback + iothread, 4 queues (default) | VM `DISK_CACHE=none` (F_NOCACHE patch) + iothread |
|---|---|---|---|---|
| Sequential write + flush (8 MiB blocks) | 11.2 GB/s | 2.75 | 2.05 | **4.04** |
| Sequential read, 4 threads (cold for `none`) | 13.2 GB/s | 45.1 (host RAM) | — | **13.2 (100%)** |
| 4K random read, 1 thread | 16.7K IOPS (p50 60 µs) | 14.1K | **16.9K (p50 59 µs)** | 5.7K (p50 176 µs) |
| 4K random read, 8 threads | 135.6K | 42.4K | **73.2K** | 40.9K |
| 4K random read, 32 threads | 266.8K | 54.7K | **112.8K** | 80.9K |
| 4K random write, 8 threads | — | 25.3K | **47.8K** | 24.0K |
| 4K write + fsync, 1 thread | 9.3K (p50 98 µs) | 2.1K | **2.3K (p50 439 µs)** | 1.5K |
| 4K write + fsync, 4 threads, same file | 27.9K | 0.81K | 0.83K | 0.78K |

* Writeback reads hit the host page cache once the data is warm, which is
  why the random-read latency matches native.
* `none` measures the real SSD path and avoids caching data twice (guest and
  host).
* APFS `fsync` vs `fdatasync` for in-place 4K writes: 22 vs 23 µs. So the
  host flush is cheap. The guest's btrfs fsync is a chain of dependent I/Os,
  each paying a virtio round trip of about 50 µs.

### Video playback: hardware decode (VideoToolbox behind guest VA-API, D-029)

The same two H.264 clips (synthetic content, High profile with B-frames)
play on both sides:

* 4K60: 3840×2160, level 5.2, 59.7 Mbps;
* 1080p60: level 4.2, 19.7 Mbps.

Each case is looped for a 6 s warm-up plus a 25 s measured window.

* **macOS:** AVFoundation (`benchmarks/bin/avplay`) in a 1296×729 pt window,
  the size of the VM window, with the VM shut down.
* **VM:** mpv fullscreen in Hyprland (2592×1458 at 120 Hz),
  `--vo=gpu --gpu-api=opengl`, with `--hwdec=vaapi` or `--hwdec=no`.

Power is the SoC sum from IOReport on AC. Scripts:
`benchmarks/macos/playback_power.py` and `benchmarks/vm/playback_power.py`.
Data: `benchmarks/results/macos-video-2026-10-12/` and
`benchmarks/results/vm-video-2026-10-12/fencepoll/`.

**Caveat: these are not like for like yet (F-049).** The native player's
window was on screen. The VM window was not, so macOS never drew it, and the
VM rows leave out QEMU's draw and WindowServer's compositing. Everything
inside the guest is included. The VM runs must be repeated with the window
on screen.

| Case | macOS native (median of 4, window on screen) | VM hardware decode, mpv defaults (mean of 2) | VM software decode (mean of 2) |
|---|---|---|---|
| Idle | 1.93 W | 1.86–2.98 W | — |
| 4K60 playback | **2.91 W** | 7.04 W | 17.34 W |
| 1080p60 playback | **2.36 W** | 4.33 W | 6.72 W |
| 4K60 decode only, nothing displayed | — | 3.00 W | 11.48 W |
| Dropped frames per 1,500 | 0 | 0–2 | 0–4 |

**Where the VM's 4K60 power goes** (session `mpv-render`, hardware decode,
same stream; this session's idle read 2.76 W):

| mpv configuration | SoC W | GPU W | DRAM + memory controller W | Dropped / 1,500 |
|---|---|---|---|---|
| Decode only (FFmpeg `-re`, nothing shown) | 3.03 | 0.23 | 1.32 | — |
| `vo=gpu`, `profile=fast` (**VM default now**) | **3.88** | 0.32 | 1.55 | 1 |
| `gpu-next`, `profile=fast` | 3.85 | 0.31 | 1.54 | 14 |
| `gpu-next`, mpv defaults | 5.92 | 0.85 | 2.57 | 7 |
| `vo=gpu`, mpv defaults | 7.28 | 0.80 | 3.40 | 0 |

* **Decode isn't the gap.** Hardware decode with frames kept on the GPU costs
  about +1.1 W over idle, close to native's whole playback increment (+1.0 W).
* **mpv's default scaling is the big cost (F-048).** It downscales in linear
  light at source resolution, with a wide filter and dithering. The fast
  profile saves 3.4 W at 4K60.
* **A fullscreen 60 fps client that only clears costs the whole guest chain
  about +0.8 W** (Hyprland plus virtio-gpu), measured with `vfill`.
* **Open:** the host side of presentation (QEMU's draw plus WindowServer)
  waits for runs with the VM window on screen.

**Guest software decode:** at 4K60 it costs 9.5 W of CPU power. Hardware
decode cuts whole-SoC playback power by 59% at 4K60 and 36% at 1080p60
(both with mpv's default scaling).

# Progress Log

Newest first. Each milestone lists: discovered, implemented, tested,
measured, still unsupported, and next.

---

## 2026-10-12 · Storage, clipboard, host agent, idle refresh

### Implemented

* **Host agent** (`tools/ilinux-host-agent`, launcher-managed) and guest
  `ilinux-host-bridge`: Mac battery, a clock step right after host sleep
  (tested: a 30 s lag was fixed within one cycle), and time zone. No polling
  in the guest.
* **Storage:**
  * virtio-blk runs on a dedicated iothread with 4 queues, doubling
    random-I/O scaling;
  * QEMU patch 0005 makes `cache.direct` use F_NOCACHE on macOS (it was
    O_DSYNC);
  * `storbench syncwrite` added (F-033, D-023).
* **Clipboard sharing with macOS:** QEMU built with spice-protocol
  (`qemu-vdagent`), plus a stdlib-only guest vdagent clipboard agent for
  Wayland (wl-clipboard) and a udev `uaccess` rule. Tested both directions
  (D-022).
* **QEMU patch 0006, adaptive display refresh:** a hidden window caused a
  redraw-request storm (1 guest frame vs 1832 requests in 20 s).
* **Housekeeping:** deleted the obsolete ext4 `root.img` (13 GB).

### Measured

* **Storage vs native:** warm 4K QD1 reads at 101%; 32 threads at 42% (was
  20%); cold sequential reads with F_NOCACHE at 100%; write+fsync at 22%
  (btrfs dependent-I/O chain).
* **Microphone:** QEMU's CoreAudio backend has no capture
  (`max_voices_in = 0`). A capture voice needs writing, ideally with an app
  bundle so macOS attributes the microphone prompt to it.

---

## 2026-10-12 · Efficiency pass: CPU heterogeneity, App Nap, GPU fences, power

### Discovered

* **App Nap (F-027):** a hidden QEMU window naps the whole VM, putting every
  vCPU at PRI 4 on M cores, about 4× slower.
* **macOS QoS on M5 Max (F-028):** only `background` QoS reaches the M cores.
  `utility` behaves like `default`.
* **VirGL fences (F-030):** on macOS they were polled every 1 ms, costing
  about 1.5 ms per guest GL sync. QEMU enabled the sync thread only for EGL,
  and virglrenderer needs eventfd.
* **Idle power (F-032):** an idle Omarchy VM costs only +0.09 W SoC. The
  earlier +0.38 W reading included post-login churn and a lingering test
  user manager.

### Implemented

* **Workspace QEMU and virglrenderer patches:**
  * `bg-vcpus` heterogeneous vCPUs: host QoS plus guest
    `capacity-dmips-mhz` (D-019);
  * `app-nap=on|off|auto` (D-020);
  * event-driven VirGL fences with a pipe-backed eventfd (D-021).
* **Launcher:** `--hetero`, `APP_NAP` (default `auto`), and the guest time
  zone follows the Mac (`ilinux.tz=`).
* **`omarchy-qos`:** `RESERVE_EFFICIENT_CPUS=auto` keeps system and
  foreground slices off much-slower efficient CPUs, plus a system unit
  `omarchy-qos-system.service`.
* **Tools:**
  * `benchmarks/src/glbench.c`: the same GL 4.1 code on CGL and EGL;
  * `benchmarks/vm/{vm_power_states,hetero_placement}.sh`;
  * `tools/power_{summary,table}.py`;
  * `vmconsole.py`: robust completion marker.

### Measured (`reports/vm-vs-macos-parity.md`)

* **GPU vs macOS GL:**

  | Test | Parity |
  |---|---|
  | ALU | 99.7% |
  | Blended fill | 74% (was 17%) |
  | Readback | 61% (was 23%) |
  | Draw calls | 50% |
  | Texture upload | 28% |

* **CPU:** foreground single-thread is 99% of native. The background tier
  gives 1.84× (1 thread) and 2.25× (6 threads) more work per joule than
  foreground.
* **Idle:** +0.09 W (`app-nap=auto`) and +0.14 W (`off`) over host-only
  1.713 W.

### Next

* Texture-upload and draw-call gaps: blob or zero-copy resources, and Venus
  (Vulkan) via MoltenVK or KosmicKrisp.
* Battery-mode measurements (on battery and in Low Power Mode).
* Package the kernel for pacman.

---

## 2026-10-12 · Session 2: Omarchy 4 desktop in a GPU-accelerated VM

### Implemented

* **Guest system:**
  * Omarchy 4.0.4 (aarch64 edge) on btrfs (`@`, `@home`, `@log`, `@pkg`,
    zstd) with snapper (D-013).
  * Kernel v2: 7.1.6 with 16K pages and uclamp, the full ALARM module set,
    essentials built in (D-014).
  * Network: Quad9 with DoT (D-015).
* **GPU compute from Linux:** guest llama.cpp → ggml RPC → vsock (vzrun
  `--vsock-forward`) → host Metal `ggml-rpc-server`.
* **GPU desktop:** QEMU 11.1.1 (HVF) + VirGL 1.3.0 + upstream libepoxy, all
  built from pinned sources in the workspace (D-012). The launcher is
  `virtualization/qemu/run-omarchy-gpu.sh`.
* **Fixes we wrote:**
  * libepoxy: a missing `libEGL` no longer aborts. Every GL lookup probed
    EGL first.
  * QEMU Cocoa patch: stable Retina window size, window size sent to the
    guest at launch, app name from `-name`.
  * Omarchy shell under Qt 6.12: the `QtQuick/Color` type shadowed the
    shell's `Color` singleton, leaving a black, empty bar. Fixed with a
    self-disabling pin plus a pacman hook (D-017).
* **Mac integration:**
  * the battery bridge feeds IOKit data over virtio-serial into
    `test_power`, so UPower and the bar show the Mac battery;
  * SDDM autologin (D-016);
  * opt-in full-screen Space and full keyboard grab (D-018).

### Tested / measured

* **ggml RPC:** Q4_0 8B prefill 2737 t/s (**89%** of native Metal),
  generation 85.1 t/s (**81%**). Socat `nodelay` was essential: with delayed
  ACK, generation was 23%.
* **Guest renderer:** `virgl (Apple M5 Max)`, OpenGL 4.1 core, GLES 3.0
  (Mesa 26.2.4).
* **Desktop:** Hyprland 0.56.2 at 2592×1458 at 120 Hz, scale 2. The bar,
  notifications and lock screen are themed (screenshots taken in the guest
  with `grim`).
* **Idle desktop cost:** QEMU used ≈ 3.4% of one host core with the desktop
  idle. Omarchy's idle chain works: screensaver at 150 s, lock at 300 s, then
  DPMS off, after which the guest stops rendering.
* **Native series (job 018):** `git am` on asahi 77cb8f24 is clean. `sart.o`
  and nvme `apple.o` build with 0 errors and 0 warnings, and
  `t6050-j716c.dtb` builds.

### Still unsupported / next

* No Vulkan in the guest (Venus/MoltenVK not built). No microphone capture
  with the CoreAudio backend.
* GPU benchmark (guest VirGL vs native GL) and host power: idle desktop vs
  macOS idle.
* Package the custom kernel for pacman. Guest timezone should follow the
  Mac's.

---

## 2026-10-11 · Native-enablement research pass (m1n1, Asahi Linux, PMGR/DVFS, drafts)

### Discovered

* **m1n1 (`57a9339`) on t6050:** single core plus NVMe read. SMP is still
  broken: cores power on but never run m1n1 code (PR #610). The cause is
  Unknown; ranked hypotheses are in `kernel/native-enablement/plan.md` §1.2.
* **M5 MPIDR:** M cores are 0x4XXYY and P cores 0x1XXYY (F-019). The old
  draft DT would have had every CPU node pruned by m1n1. Fixed.
* **Our ADT, decoded:**
  * the PMGR table: 661 records, 6 blocks, a second die at +0x21_0000_0000
    (F-021, F-024);
  * CPU DVFS: M 15 states up to 4.380 GHz, P 20 states up to 4.608 GHz
    (F-022);
  * SART `sart-version = 4`, the NVMe M4+ layout, and per-CPU
    `function-enable_core` (F-020, F-023).
* **AsahiLinux/linux:** `asahi` already has the NVMe firmware-ABI series.
  No branch has SARTv4 or the M4+ NVMe register split.
* **Idle:** m1n1 forces `idle=nop arm64.nowfxt` on M4+ (F-026).

### Implemented

* **`adt_extract.py`:** wider whitelist, full binary tables, and a
  content-based leak check (`--check-only`). Re-extracted: 0 problems.
* **The DT generator:** now covers PMGR power domains (188), MPIDR-correct
  CPUs, OPP and energy-model data, cpufreq, disabled DART/SART/NVMe drafts.
  `validate.sh` fixed and strict: **0 dtc warnings**.
* **Local patch series `kernel/patches/t6050/0001–0007`:** SARTv4, the NVMe
  M4+ split, bindings, and the DT. Untested; compile test pending. Not for
  upstream.
* **`kernel/native-enablement/plan.md`:** a dependency-ordered plan for items
  (a)–(j).

### Next

1. Compile-test the series and run `dtbs_check` in the VM, once it is free.
2. A native m1n1 read-only diagnostics session. This needs user
   authorization and a deployment plan.
3. Draft the SPMI gen-4 driver and a dockchannel-uart console driver.

---

## 2026-10-11 · Session 1: foundations, baselines, VM track, energy

### Discovered

* **Exact hardware:** MacBook Pro Mac17,6 (J716c), **Apple M5 Max = t6050**
  (`chip-id` 0x6050, SoC generation tag "H17", CPU family SOTRA).
  * 6 P ("Super", 16 MiB L2) + 12 M ("Performance", 2 × 8 MiB L2) cores;
    the ADT cluster type is `M`.
  * 40-core G17X GPU, H16-generation ANE (exclave-mediated), 128 GiB,
    2 TB ANS3 SSD.
* **ISA:** SME/SME2/SME2p1 (SVL 512) without non-streaming SVE. MTE present.
* **Linux status for t6050:**
  * No DT and no kernel bring-up. m1n1 has initial T6050 support with no SMP.
    GPU (G17), ANE, ANS3 NVMe, the N1 Wi-Fi chip, DCP and others have no
    Linux drivers.
  * **Asahi forbids generative-AI contributions** (2026-09-08), so this
    project's outputs stay local (D-007).
* **macOS QoS:** background work runs on M cores at ≈ 25% of P-core
  throughput, at **≈ 4× better energy per FLOP**.
* **SME:** one engine per cluster. The P-cluster engine gives 2.17 TFLOP/s
  FP32 (rail `PCPM` ≈ 9.8 W); the chip saturates at 3.23 TFLOP/s.
* **GPU:** FP16 GEMM ≈ 64 TFLOP/s (matrix units) vs 17.6 scalar. Core ML's
  planner prefers the GPU over the ANE on M5 Max.
* **ANE:** 14.0 TFLOP/s FP16 on a 1×1-conv stack at ≈ 3.6 W. Proven by the
  ANE energy counter and MLComputePlan.
* **Microarchitecture:** M5 P-core FMA throughput drops ≈ 11% when all FMLAs
  read the same two source registers (F-016). This explained a fake "112%
  VM parity".
* **Omarchy 4 already supports aarch64 upstream** (edge). Real `pacman` in
  our VM resolves the full default set: 842 packages, 0 unresolved.
* **VM facts:** SME2 is passed through. MIDR is masked. Wakeups cost 21–52 µs
  vs 3.8 µs native. Virtio storage reaches 3–30% of native.

### Implemented

* Benchmarks:
  * `cpubench` (freq, fma, **fma_asm**, intmix, sort, sgemm, SME f32/bf16/i8,
    pingpong, syscall);
  * `membench` (STREAM, latency incl. DIT/DMP-off, faults);
  * `storbench`;
  * Metal `gpubench`;
  * **`powermon`** (no-root IOReport energy and DVFS sampler).
* Model generators: `tools/synth_gguf.py` and `tools/synth_mlx.py`
  (synthetic models with identical shapes for llama.cpp and MLX).
* Analysis helpers: `tools/compare_results.py` (parity tables);
  `hardware/scripts/{adt_extract,ioreg_driver_map,kext_personalities}.py`.
* **VM track:**
  * `virtualization/vzrun` (Virtualization.framework runner: direct kernel or
    EFI boot, virtiofs, NAT, nested, NVMe and disk-mode options);
  * GPG-verified Arch Linux ARM image build;
  * the scripted job runner.
* **omarchy-qos** (QoS tiers via systemd slices, cpuset, uclamp), VM-tested
  and with one bug fixed.
* **Draft t6050 DT** (CPUs, AIC3, timer, WDT, 3 × pinctrl, 9 × I2C, UART),
  compile-checked with a workspace-built `dtc` 1.8.1. Local only.
* REA 6.4.0, project-local (`tools/rea`, `.mcp.json` and deny-list settings in
  `~/Documents/iLinux`). MLX, mlx-lm and coremltools in `tools/venv`.

### Tested and measured (highlights; see `reports/performance-parity.md`)

| What | Result |
|---|---|
| macOS CPU, 1 P core / 18 cores (asm FMA) | 140.8 GFLOP/s / 1.89 TFLOP/s |
| macOS SME f32, 1 thread / chip | 2.17 / 3.23 TFLOP/s |
| macOS STREAM, 18 threads (median) | ≈ 369 GB/s copy |
| macOS GPU FP16 GEMM / copy bandwidth | 64 TFLOP/s / 537 GB/s |
| macOS SSD seq read / write | 11.0 (13.3 at 4 threads) / 11.2 GB/s |
| llama.cpp Metal 8B Q4_0 | pp512 3090 t/s, tg128 105 t/s, ≈ 0.56 J/token |
| MLX 8B 4-bit / Gemma-3-12B bf16 | tg 100.8 / 21.7 t/s |
| ANE (Core ML conv stack) | 14.0 TFLOP/s at ≈ 3.6 W |
| **Linux VM vs macOS** (identical code and flags) | CPU compute 97–101%, SME 97–100%, STREAM 93–100%, DRAM latency 72–84%, syscalls 77%, wakeups 7%, storage 3–57% |
| omarchy-qos in VM | 5/5 pass; uclamp skipped (no `CONFIG_UCLAMP_TASK_GROUP` in the ALARM kernel) |

### Still unsupported or blocked

* Native Linux on t6050 (B-001), GPU (B-002), ANE (B-003), NVMe (B-004),
  Wi-Fi (B-012).
* GPU acceleration inside VMs needs host installs such as krunkit (new
  approval).
* No Linux-side energy counters yet.
* Strict BLAS-free llama.cpp prefill comparison on macOS needs `cmake`
  (not installed).

### Next

1. ✅ (2026-10-11) VM llama.cpp CPU comparison (F-017) and VZ storage-mode
   matrix (F-018). Follow-up: `fsync` default plus pre-allocation in `vzrun`.
2. Build a guest kernel config with `CONFIG_UCLAMP_TASK_GROUP` (and possibly
   16K pages) to test omarchy-qos clamps and the VM memory overheads.
3. Omarchy VM install: keyring, `omarchy-arm64-vm` integration package,
   Hyprland on llvmpipe smoke test.
4. Propose GPU-in-VM experiments (krunkit/Venus; llama.cpp API remoting) to
   the user for approval.
5. Decode the PMGR `devices`/`ps-regs` tables to extend the DT draft with
   power domains (local research).

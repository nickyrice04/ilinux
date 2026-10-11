# Blockers

Status legend: 🔴 hard blocker (no path today) · 🟠 blocked pending research or
upstream work · 🟡 pending user approval or action · 🟢 resolved.

## Hardware enablement

### B-001 🔴 No Linux support for t6050 (M5 Max)

* No DT exists for t604x/t605x/t8142 in mainline or any Asahi branch.
  Mainline stops at M3. Asahi has a minimal t8132 (base M4) DT from 2026-07.
* m1n1 has **initial** T6050/T6051 support (PR #610, 2026-06-29), but
  **secondary CPUs never start**. No public fix was found as of 2026-10.
* Asahi's M5 support page (2026-10-03) shows no active work on any block.
  The installer accepts M1–M3 only.
* Consequence: native Linux can't boot on this machine.

### B-002 🔴 GPU (AGX G17X) unsupported

* The Asahi DRM driver and Mesa support G13/G14 (M1/M2) only. M3 (G15) is
  still being reverse-engineered after an ISA and firmware-interface break.
* The M5 GPU adds matrix "Neural Accelerators". macOS FP16 GEMM reaches
  ≈ 64 TFLOP/s, against ≈ 17.6 TFLOP/s for scalar FP16 FMA.

### B-003 🔴 Neural Engine

* The ADT marks it `ane,t8132exclave`, and macOS drives it via
  `ANEExclaveProxy` and exclave services.
* The only Linux ANE driver (eiln/ane) is M1-only, out of tree, and
  untouched since 2024-03.
* Feasibility under a non-secure kernel is unknown.

### B-004 🟠 NVMe controller generation

* macOS binds `AppleANS3CGv2Controller`, and SART is CoastGuard (m1n1 calls
  it **SARTv4**).
* m1n1 can read NVMe on T6050. Linux `nvme-apple` and `apple-sart` support
  only older revisions. The macOS-15+ ANS firmware ABI change needs the
  `b4/nvme-fwabi` series.

### B-012 🔴 Wi-Fi / Bluetooth

* Apple's own **N1** wireless chip has no Linux driver (Asahi report).

## Testing infrastructure

### B-005 🟢 Isolated Linux environment (resolved 2026-10-11)

* User approved the workspace VM. `vzrun` boots a GPG-verified Arch Linux
  ARM image (`virtualization/images/alarm/`, 32 GB sparse, built via Docker
  Desktop) and runs scripted jobs via virtiofs.
* Remaining limit: Virtualization.framework gives Linux 2D graphics only.
  GPU-in-VM, e.g. krunkit/Venus, would need a host install and new approval.

### B-006 🟢 REA installation (resolved 2026-10-11, project-local)

* `rea-agents@6.4.0` is installed in `tools/rea` (`--ignore-scripts`; 144
  packages, registry signatures verified).
* `~/Documents/iLinux/.mcp.json` plus a deny-list `.claude/settings.json`
  are in place. MCP tools load in the next session launched from
  `~/Documents/iLinux`; the CLI works now.
* No decompiler engine (Ghidra/JDK not approved), so only metadata-level
  tools are available.

### B-007 🟢 AI framework baselines (resolved 2026-10-11)

* Project venv `tools/venv`: mlx 0.32.3, mlx-lm 0.32.0, coremltools 9.0.

### B-008 🟢 Power and energy measurement (resolved 2026-10-11, macOS side)

* `powermon` (`benchmarks/src/powermon.c`) reads IOReport "Energy Model"
  and DVFS residency channels **without root**: CPU per core and cluster,
  GPU, ANE, DRAM, memory fabric, display, ISP, AVE, PCIe. `powermetrics`
  isn't needed.
* Remaining: a Linux-side equivalent (PMGR/SMC energy counters) for native
  parity of performance-per-watt.

### B-009 🟡 Energy mode during baseline

* On AC (plugged in), macOS still reports the AC Energy Mode as "Low Power
  Mode: Yes" (`pmset powermode 2`). That is a separate setting from the power
  source.
* Single-core peak was unaffected. Multi-core and GPU sustained limits may be
  lower than in High Power mode. The user chose to keep current settings.

### B-011 🟠 uclamp missing in the stock Arch Linux ARM kernel

* `linux-aarch64` 7.1.6 has no `CONFIG_UCLAMP_TASK`/`UCLAMP_TASK_GROUP`, so
  `omarchy-qos` can test slices, weights and cpusets in the VM but not
  utilization clamps.
* Fix path: a custom kernel config in the VM, a future Asahi or native
  kernel with uclamp enabled, or both.

## Knowledge gaps

### B-010 🟠 MIDR values for SOTRA cores unknown

* macOS user space can't read `MIDR_EL1`.
* **Tested 2026-10-11:** the Virtualization.framework guest sees a masked
  MIDR, `0x610f0000` (implementer Apple, part 0x000), on all 18 vCPUs. A VM
  can't reveal it.
* m1n1 confirmed MIDRs for base M5 (T8142, PR #629). T6050 values are only
  obtainable natively.

## Policy constraints

### B-013 🟠 Upstream contribution to Asahi is not possible from this project

* Asahi's generative-AI policy (2026-09-08) forbids AI-generated material
  contributions. See decision D-007.
* This project's code, DT drafts and findings stay local. Upstream
  progress depends on human contributors working independently.

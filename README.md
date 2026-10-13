# Apple Silicon Linux Performance Parity: Research Workspace

Long-running engineering project. The goal is the highest achievable
**Linux (Omarchy) performance on this MacBook Pro (Apple M5 Max, SoC t6050)**,
measured against macOS on the same machine.

> **Current reality (2026-10-12):** native Linux has not been booted or
> validated on this unit. Initial m1n1 support exists, and the seven local
> t6050 patches passed driver-object and device-tree compilation. Boot/SMP,
> G17 graphics/display and idle/DVFS remain the largest native gaps.
> Omarchy already runs in an accelerated VM with heterogeneous vCPUs,
> Vulkan compute and hardware H.264 decode. These results are a separate
> VM track, not proof of native hardware support.

## Start here

| File | What |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Rules (macOS host is read-only), layout, conventions |
| [`progress.md`](progress.md) | What has been done, measured and found; next steps |
| [`roadmap.md`](roadmap.md) | Phased plan |
| [`blockers.md`](blockers.md) | Hard blockers and pending approvals |
| [`decisions.md`](decisions.md) | Decision log |
| [`hardware/hardware-inventory.md`](hardware/hardware-inventory.md) | Exact hardware facts (observed, measured, spec) |
| [`reports/compatibility-matrix.md`](reports/compatibility-matrix.md) | Every SoC block → Linux driver → status |
| [`reports/performance-parity.md`](reports/performance-parity.md) | Scorecard: macOS baselines, AI and energy, Linux-VM track |
| [`reports/vm-vs-macos-parity.md`](reports/vm-vs-macos-parity.md) | Full VM-vs-macOS table (identical code and flags) |
| [`reports/bottleneck-priorities-2026-10-12.md`](reports/bottleneck-priorities-2026-10-12.md) | Current audit of all eight hardware areas and ranked blockers |
| [`reports/video-download-and-nv12-2026-10-12.md`](reports/video-download-and-nv12-2026-10-12.md) | Packaged Linux video improvements, REA evidence and measured CPU savings |
| [`reverse-engineering/findings/catalog.md`](reverse-engineering/findings/catalog.md) | Research findings database |

## Reproduce the macOS baseline

```bash
benchmarks/macos/run_baseline.sh all
```

This builds the portable benchmarks with Xcode's clang and swiftc, runs
CPU/SME, memory, storage, Metal GPU and llama.cpp (synthetic-weight model)
tests under `caffeinate -i`, and writes JSONL plus environment snapshots to
`benchmarks/results/macos-<timestamp>/`. The run is non-destructive. It
writes one temporary 8 GiB file and deletes it afterwards.

## Tools built here

* `benchmarks/src/{cpubench,membench,storbench}.c`: portable C benchmarks
  that build unchanged on Linux, for apples-to-apples parity.
* `benchmarks/src/gpubench.swift`: Metal compute, bandwidth, GEMM and latency.
* `tools/synth_gguf.py`: synthetic-weight GGUF generator (Llama-3 shapes;
  Q4_K_M/Q4_0/Q8_0/F16) for model-free LLM throughput benchmarking.
* `hardware/scripts/adt_extract.py`: sanitized Apple Device Tree extractor
  (whitelisted values only, no identifiers).
* `hardware/scripts/ioreg_driver_map.py`: device-tree node → macOS driver
  class map.
* `virtualization/vzrun/`: minimal Virtualization.framework Linux VM runner
  (ad-hoc signed, workspace-only).
* `omarchy-arm64/configuration/qos-tiers/`: `omarchy-qos`, macOS-style QoS
  tiers for Linux (uclamp, cpuset, systemd slices).

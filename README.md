# Apple Silicon Linux Performance Parity: Research Workspace

Long-running engineering project. The goal is the highest achievable
**Linux (Omarchy) performance on this MacBook Pro (Apple M5 Max, SoC t6050)**,
measured against macOS on the same machine.

> **Current reality (2026-10-11):** the t6050 SoC has no Asahi or upstream
> Linux support (no m1n1, no device tree, no drivers for its new blocks), so
> native Linux can't boot on this machine yet. Native parity is 0% by
> definition today. This workspace builds the evidence, tooling and
> components needed to get there, and measures what is achievable meanwhile
> (Linux VMs).

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

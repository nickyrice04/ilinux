# omarchy-qos: macOS-style QoS tiers for Linux on heterogeneous Apple CPUs

**Status:** implemented, syntax-checked on macOS. The functional test in a
Linux VM is pending (see `tests/test-qos.sh`). Performance effects can be
validated only on native heterogeneous hardware. **Not validated yet.**

## Problem

On the reference machine (M5 Max: 6 "Super"/P cores + 12 "Performance"/M
cores), macOS ties scheduling *class* to *both* core type and performance
level. Our measurements (`reverse-engineering/findings/catalog.md`, F-002):

| QoS (single thread) | Cores used | FMA | Integer | SGEMM | SME |
|---|---|---|---|---|---|
| user-interactive / default / utility | P cluster (cpu12–17) | 125 GFLOP/s | 21 Gop/s | 60 GFLOP/s | 2170 GFLOP/s |
| background | M cluster (cpu6–10) | 33 (26%) | 5.1 (24%) | 14 (23%) | 204 (9%) |

Background work is kept off the P cluster and held at a low performance
point. Interactive work gets the fastest cores. Stock Linux desktops, Omarchy
included, launch everything with equal weight and no utilization clamps. EAS
alone can't tell an indexer from a compositor.

## Design

The building blocks are standard Linux and systemd mechanisms, nothing
Apple-specific:

* **systemd user slices** from the desktop integration conventions in
  `systemd.special(7)`, which uwsm/Hyprland already use: `session.slice`,
  `app.slice`, `background.slice`. We add `utility.slice`.
* **cgroup v2 `cpu.uclamp.min/max`.** `schedutil` then picks lower or
  higher frequencies, and EAS prefers efficient CPUs for clamped tasks. The
  kernel computes effective clamp = clamp(task request, group min, group max).
* **cgroup v2 cpuset** (`AllowedCPUs=`) as a hard fence for background work.
  The efficient CPU set comes from `cpu_capacity` at runtime, so nothing is
  hardcoded per SoC.
* **CPUWeight** for contention priority.

| Tier | Slice | Default policy |
|---|---|---|
| interactive | `session.slice` | uclamp.min 20%, CPUWeight 400 |
| default | `app.slice` | unchanged |
| utility | `utility.slice` | uclamp.max 70%, CPUWeight 50 |
| background | `background.slice` | uclamp.max 30%, CPUWeight 20, efficient CPUs only |

The values are starting points derived from the macOS ratios and are tunable
in `/etc/omarchy-qos.conf`.

## Files

* `bin/omarchy-qos`: `apply`, `run <tier> -- cmd`, `status`.
* `systemd/user/omarchy-qos.service`: applies the tiers at session start.
* `systemd/user/utility.slice`
* `systemd/system/user@.service.d/omarchy-qos-delegate.conf`: delegates
  `cpuset` (plus defaults) to the user manager.
* `install.sh <root>`: installs into a Linux root (VM or chroot only).
* `tests/test-qos.sh`: functional test (placement, CPU fence, uclamp
  readback).

## Kernel requirements

`CONFIG_UCLAMP_TASK=y`, `CONFIG_UCLAMP_TASK_GROUP=y`, `CONFIG_CPUSETS=y`,
`CONFIG_ENERGY_MODEL=y`, and the cpufreq governor `schedutil`. EAS also needs
asymmetric `cpu_capacity` values plus an energy model, which on Apple SoCs
come from DT OPP tables (`opp-microwatt`) and `capacity-dmips-mhz`.
`omarchy-qos status` reports what is missing.

## Validation plan

1. **VM (mechanics):** `tests/test-qos.sh` with
   `OMARCHY_QOS_EFFICIENT_CPUS=0` to simulate a heterogeneous set. Expected:
   slices correct, CPU fence applied, uclamp values read back.
2. **Native (effects, future):** repeat `benchmarks/bin/cpubench` under
   `omarchy-qos run background` vs `default` on Linux. Compare per-tier
   throughput ratios and, once power measurement exists, energy per task
   against the macOS QoS table above. Parity criterion: background tier
   throughput within ±10% of macOS's background ratio, and interactive
   latency (`pingpong`) not worse than `default`.

## Known limitations

* uclamp caps utilization requests, not frequency directly. On a busy system
  the realized frequency also depends on co-runners in the same cluster.
* There's no equivalent of XNU's per-thread QoS propagation through IPC
  (vouchers). Tiers are per process tree or cgroup only.
* `AllowedCPUs` on the user manager needs the `cpuset` delegation drop-in
  (system-level change inside the Linux install, never on macOS).

# Direct31AH RAM diagnostic

These original MIT-licensed helpers qualify the new public direct Mach-O
Aura/Linux route without changing the installed boot object. The related build
is `virtualization/jobs/095-direct31ah-kernel/`; the route and firmware evidence
are in `research/m5-boot-route-2026-11-12.md`.

`check_config.py` checks the resolved kernel policy, including 16 KiB pages,
CTXR executable confinement, all-core capacity and exclusion of SEP and storage
drivers from built-in code. `fdt_read.py` bounds binary FDT parsing;
`check_dtb.py` verifies the exact J716c static topology, CPU release protocol,
MPIDRs and M/P capacity distinction. Static CPU nodes and zero release-address
placeholders are not proof that Aura has started the cores. Aura must fill RAM,
release addresses, framebuffer and executable reservations at runtime.

`make_diag_dt.py` removes the public source's publisher-specific DROM and its
placeholder, and disables SEP, ISP and USB4 nodes. It preserves the CPU tree and
the USB2 control path. Firmware and personal board data are not included.

`make_initramfs.py` accepts a static AArch64 ELF and creates a deterministic
gzip/newc archive containing only `/init` and empty RAM mount points.
`check_artifacts.py` requires the completed checks and genuine generic Linux
collector selftest, and records output sizes/hashes. It always reports native
qualification and boot readiness as false.

## What the native diagnostic would collect

`diag_init.c` is a static, RAM-only PID 1. It requires the exact null-separated
J716c/T6050 compatible tuple, or a separate explicit generic VM-control flag.
It never opens block devices, mounts a storage filesystem, uses `/dev/mem`,
loads modules, hotplugs CPUs, changes frequency, changes firmware or restarts.

After mounting proc/sys/devtmpfs and a bounded RAM `/run`, it:

1. Emits a PID-1 marker and, on the native board only, binds a transmit-only USB
   bulk log gadget. It accepts no USB input commands. Only this collector's
   whitelisted JSON records are forwarded; arbitrary kernel/driver logs are
   excluded to avoid collecting unit identifiers or network addresses.
2. Records Linux's online CPU list, network interface names, any existing NVMe
   block-device names, and the executable-window **size**, never its address.
   Storage inventory does not open or mount a device; none is expected without
   the excluded NVMe module.
   Per-core observations also include the DT MPIDR, architectural MIDR and kernel
   capacity when exposed, so execution can be linked to the distinct core types
   without collecting per-unit identifiers.
3. Reads available CPU frequency policy membership, governor and frequency
   values. Reported `scaling_cur_freq` is not assumed to be a measured clock.
   No governor or speed state is written.
4. Starts one pinned checksum worker per allowed CPU for about 250 ms, verifies
   its actual CPU and arithmetic result, requires overlapping compute intervals,
   and records a 1 ms timer sleep. Native success requires eighteen workers.
   This is a short execution/affinity/timer smoke test, not a scheduler fairness,
   IPI-latency or CPU-performance-parity benchmark. A 2 s readiness timeout and
   shared 3 s monotonic join deadline handle ordinary thread failures. Unjoined
   records remain allocated and unread, avoiding stale pointers/data races.
   Userspace cannot recover or bound a wedged kernel; the external stop still
   applies.
5. Fills and reads 64 MiB of allocated RAM, checks its sum, records elapsed read
   time, then emits sixty 1 s heartbeats and a collection-complete marker. This
   smoke test is not a complete memory-bandwidth or memory-clock qualification.
   Every five seconds a compact camera summary repeats worker pass/count,
   expected count, timer completeness, memory checksum and compute overlap.
6. Remains running; the human-controlled stop/return procedure is external.

USB transmission is best effort/nonblocking and may lose records if the reader
is absent or the controller fails. The independent M1 webcam recording can show
screen progress even if USB never returns. USB logging is not proof of the
earlier firmware handoff and the collector cannot observe a failure before PID 1.
The pinned public kernel is explicitly T6050 host-only; the operator's local
device-mode patch is missing. Thus the gadget path is **not native-qualified**
and `NO_UDC` is an expected possible result, not evidence against CPU startup.

## Offline tests

Run the original Python-only synthetic checks on any supported host:

```bash
python3 -I kernel/experiments/direct31ah/linux/test_offline.py
```

They exercise the failure boundaries: SEP/storage policy, page-size conflicts,
CPU count/type/order, wrong board, disabled cores, missing release slots, FDT
overlap/truncation/overflow/duplicate nodes, DROM removal, dynamic/wrong-architecture
ELF rejection, and the initramfs entry whitelist. They do not execute downloaded
code or claim a native result.

The actual static C build and `diag-init --selftest` run only in the isolated
Linux VM. The latter uses at most two allowed guest CPUs, pure arithmetic and
affinity/timer checks, and performs no mount or USB configuration. Its output is
labelled `GENERIC_LINUX_CONTROL` with `physical_m5_claim:false`.
The separate `--selftest-timeout` deliberately stalls the workers, uses a short
50 ms join deadline and requires the timeout to be observed. The final receipt
labels this expected failure `GENERIC_LINUX_TIMEOUT_CONTROL`; it configures no
mounts, USB or native hardware. The artifact check requires both controls.

Native Omarchy, physical SMP, N1 connection/throughput, GPU, storage speed and
suspend remain untested by these offline controls. Their measurements must be
recorded separately after a reviewed, authorized hardware boot.

# t6050 heterogeneous CPU topology audit

Original, read-only tooling for this J716c's **12 Performance + 6 Super** cores.
It checks the expected hardware description and prepares useful Linux evidence;
it does not start cores, change capacity values, or authorize a restart.

From the repository root:

```sh
python3 -I kernel/experiments/cpu-topology31f/test_topology.py -v
python3 -I kernel/experiments/cpu-topology31f/audit.py \
  --dtb build/native-boot042/verified/t6050-j716c.dtb \
  --dtb build/native-boot042/verified/t6050-j716c-stage-b.dtb
```

The audit can run without `--dtb` when a machine has only the public sanitized
ADT. DTB checks reuse the project's original `native/boot/fdt.py` decoder.
Dependencies are Python's standard library and that original module with its
existing original `gpio_guard` import. No vendor client is loaded or executed.
Input sizes, node count, and sysfs reads are bounded. Exit 0 means structural
checks passed; `UNCALIBRATED` capacities and `native_smp_verified:false` remain
explicit. An absent PMGR cluster descriptor fails; there is no four-bit fallback.

`audit.py` checks CPU count/type, raw ADT register versus MPIDR affinity,
three six-core clusters, unique CPU/phandle/map references, shared L2/OPP and
frequency domains, consistent optional capacities, and the six-bit PMGR
packing. The report includes the four collision pairs from the older four-bit
packing, but has no target connection or writer.

Once a separately authorized Linux boot already exists, a Linux agent may run:

```sh
python3 -I kernel/experiments/cpu-topology31f/capture_linux.py
```

This reads only selected CPU sysfs fields: online/present/possible CPUs, Linux
topology, cache sharing, CPU capacity, MIDR/MPIDR if exposed, DT CPU identity,
and cpufreq policy membership/current/requested limits. No root privilege is
requested. Missing/denied fields are reported as unavailable. The collector
does not mount debugfs or inspect memory, devices, serial numbers or host names.
The caller can redirect stdout into that boot's ignored evidence directory.

`--sysfs-root PATH` reads a small synthetic sysfs fixture, labels it `fixture:true`,
and is suitable for offline tests. Fixture capture is not native evidence.
Real capture requires Linux. DT identities are named `expected_identity_from_dt`:
they are not hardware MPIDR reads. Linux logical numbering is not assumed to
equal the ADT CPU ID. Unknown identity never defaults to an efficiency core.
Even 18 online CPUs do not establish coherency, invariant counters, scheduling
quality, efficiency, or parity; those fields deliberately remain unverified.

The 32 tests cover both valid structure and regressions that could target the
wrong core or misdescribe its scheduling domain. See
[the topology findings](../../../research/cpu-topology31f.md) for the measured
host inventory, existing limitations, and staged native acceptance criteria.

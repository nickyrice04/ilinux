# Attempt 28: CPU command-state observation on boot042

2026-10-20. Baseline `a6ad886`. Preparation/publication authorized by the user.
**Native attempt 28, module initialization on t6050, speed changes and live
checks: NOT RUN.** No host/boot/security/volume/firmware setting was changed.

## Engineering decision and REA provenance

Attempt 27 proved native two-stage delivery and automatic keyboard startup;
it did not measure the boot core's clock. Before selecting a frequency cap,
observe the actual boot MPIDR, command state, OPP initialization and available
thermal telemetry. This attempt loads the existing experimental driver with
writes disabled and cap zero. It cannot improve a requested clock and is not
a claim that the single core was necessarily at its lowest frequency.

The implementation uses the independently checked REA/assembly/ADT findings
already catalogued in [CPU power](../../../kernel/experiments/cpu-power-smp/README.md)
and [cpufreq](../../../kernel/experiments/cpufreq-t6050/README.md).
No new Apple decompilation was needed or claimed in this preparation. The
reviewed interface is the boot cluster's command register at controller base
plus `0x20`; t6050 STATUS layout remains unknown and is never read. The OPP
state offset is a static-evidence hypothesis to corroborate on hardware. An
unrecognized state produces a diagnostic and refuses policy initialization.
No Apple code/pseudocode/binary is included in Git or the new CPU payload.

The Linux core was checked in the exact boot042 build tree: it accepts
`cpufreq.default_governor=userspace` using
`module_param_string(default_governor, ...)`, and that governor is built in.
This sets the intended governor at registration, before a later userspace
command could race the default schedutil governor. The driver's no-write guard
also returns `-EPERM` before MMIO if any transition is nevertheless requested.

## Pinned scope

The exact new image pair and module/tool digests are in this directory's JSON
records. The old attempt-27 global manifests remain unchanged. Image boot042
SHA-256 remains `0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c`.
Installed boot021 m1n1, client `57a9339`, keyboard/USB/idle settings and disabled
NVMe remain the baseline. No kernel rebuild or native disk write is required.

`cpu-observe` first verifies the unchanged boot042 package, then derives an
exact DT in memory: input `17c55af9…a0405`, candidate
`aa9731d1ba8246a9441a85dcbf59bf65cfe82c7a8d33439e9d2cdc40cb0ee725`.
Only three controller status/compatible pairs and 50 OPP-level fields differ.
It rejects operator overlays, different Image/DT/stage one, changed prepared
controller/OPP/CPU associations, extra cores and enabled storage. All existing
prepared-tree hardware guards remain. Old launch profiles still disable DVFS
and reject the candidate; their actual request behavior is regression-tested.

Job052 reuses the exact attempt-27 root and adds one directory containing six
hashed CPU assets plus its manifest, and one build-info line. The module lives
outside module autoload indices. Stage one's runtime-content change is only
the new stage-two pin. Both images are repacked with zstd 1.5.7, `-T4 -19
--long=27`; VM-only keys/probes are added by the separate test overlay, never
the shipping pair. No package upgrade or proprietary research payload.

Build checks: four original keyboard module files, enabled keyboard service,
locked root/omarchy passwords, no SSH host keys or pacman keyring. The inherited
base's prior privacy/content checks remain evidence for that exact base, not
an assertion that filename scans alone prove absence of secrets.

## Measurement and stopping rules

The one-shot collector verifies board and Linux CPU0's actual DT node, a known
18-core-topology MPIDR, one online core, required command line and six asset
hashes. It pins its work to CPU0. It records a before snapshot and bounded CPU
and memory samples, loads once with `ilinux_enable_writes=0 ilinux_max_pstate=0`,
and checks immutable parameters and userspace policy0. Unknown state/no policy
retains the first baseline and ends without retry. A successful policy permits
the same short measurements again; these compare registration overhead, not
a deliberate frequency increase. No unload, sysfs frequency write or SMP start.

* Existing dependent-ADD estimator: three 0.2-second-target samples. Its GHz
  estimate assumes one cycle per dependent ADD; corroborate with work rate.
* Existing FMA assembly and integer-mix kernels: same three short targets.
* Existing STREAM: 128 MiB, one thread, three samples; inherits CPU0 affinity.
* New bounded random pointer chase: deterministic single-cycle permutations,
  128-byte links; 16 KiB, 4 MiB, 32 MiB, 128 MiB; three timed samples per size,
  at least one full cycle and at least 262,144 loads. Full-cycle warmup checked.
  This differs from the old attempt-20 chase and is not directly interchangeable.
* One-second gaps, per-child bounds, 180-second overall alarm and systemd/M1
  deadlines. This is short characterization, not thermal soak or efficiency.
* Thermal data is whatever Linux exposes; absence is null. Energy/power is
  unavailable, never zero. Requested OPP is explicitly not measured frequency.
* Desktop snapshots before/after a short human menu sequence complete the
  missing poller check. Human/video latency observations are not instrumented
  frame-time distributions. No renderer/configuration change in this attempt.

The M1 verifies stage two's distinct journal key before observation SSH. A
single monotonic window starts at root switch and cannot be rearmed. Helpers
refuse work without time remaining; CPU and desktop work are bounded remotely
as well as on the M1. The human-visible timer and return by ten minutes are
still necessary: these helpers stop collectors, not the physical computer.
Raw journals/results/video remain private under `build/`.

## Offline validation

Build and exact-pair VM results, including the initial harness failure, follow. A source or
unit-test PASS is never a native-clock, real USB-controller or thermal result.

### Completed build and software checks

Job052 guest start/end: `2026-10-20T20:41:50Z` / `20:51:12Z`, exit 0.
Compiler GCC 16.1.1 (20260430), binutils 2.46.0, Python 3.14.8, zstd 1.5.7.
Build VM: Linux 7.1.6-vzrun2, aarch64, 12 vCPUs / 24 GiB. Target vermagic:
`7.1.9-g863199d8b4a3-dirty SMP preempt mod_unload aarch64`.
The boot042 Image and config compare byte-for-byte before/after the build.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Stage one | 60,671,683 | `65ea381524f266c78da0f98d42451f46fd48c94455d0734f1f6022c1d8f08c39` |
| Omarchy root | 2,469,319,544 | `59a7383e4b6cd47712e5dc05998ab34a58d511edc0b7ee016b267a15d4fb2b78` |
| CPU module | 84,824 | `67faac4a459a6af68923f8974f95b696226941126fb0a0d713377cc0071c0d17` |

The root contains 215,521 paths; its recorded 16-KiB tmpfs usage is
11,012,784,128 bytes, a conservative budget including the build's parent/empty
stage-one directory, not a runtime working-set measurement. The module's hash
differs from job051's build because this is a separate build artifact; use the
new asset record. The exact candidate DT hash still equals job051's compiled,
narrow-schema-validated DT, so that limited schema result is reused.

* External module `W=1` compile: PASS, no warning/error lines. Driver actual
  extracted get/target callbacks: 16 ASan/UBSan cases PASS; six deliberately
  broken variants rejected. Initialization invariants also checked in source;
  this is not native initialization coverage.
* Portable benchmark build/smoke tests and 12 collector tests: PASS in the VM.
  New pointer chase has 12 sanitizer output rows, no ASan/UBSan finding. VM
  throughput is deliberately not presented as native or matched macOS data.
* Controller VM final run: 296 tests PASS, no skips, using pinned m1n1 and pinned
  construct 2.10.70 / pyserial 3.5 in a VM-only venv. An additional 12 native
  collector and 11 M1 key/deadline tests PASS. Sources mounted read-only;
  all target/proxy operations are fakes. No target is connected to this VM.
* CPU-profile host suite: 19 tests PASS, including the two exact-payload/fake
  handoff cases also included in the final controller VM run. Earlier-profile suite:
  45 PASS. Pair-intake suite: 8 PASS. Sender suite: 18 PASS. Legacy DT/allowance/
  measurement suites: 5 + 5 + 2 PASS, inherited ADT ResourceWarning retained.
* Real exact-pair verification, embedded pin, CPU-profile offline launcher
  and sender dry run: PASS. No USB/session opened. The launcher estimates
  105,351,258 upload bytes, 21.1 s at 5 MB/s / 26.3 s at 4 MB/s, deadline 300 s;
  these are size/rate estimates, not native attempt-28 measurements.
* Source syntax, source/payload hashes and unchanged baseline image checks
  pass. Remaining real-controller and prepared-DT behavior requires M1/native
  observation; transport-injected tests cannot prove it.

Preparation failures: the first governor-source assertion
used the wrong macro name (`module_param` instead of `module_param_string`);
two packaging checks overmatched the temporary root pathname rather than the
new asset directory. Corrected before producing the final pair. The initial
macro-check log was overwritten during correction; later packaging-failure
logs are retained in ignored output directories. Older test
expectations for three profiles/error wording were updated for the explicitly
added fourth profile. A macOS temporary-path fixture was resolved before its
key-refusal test could exercise the intended condition. Host m1n1-dependent
suite initially lacked its Python dependencies; the full suite above ran in
the existing VM instead of installing into macOS. None was a native test.


### First full-pair VM run: transfer and boot passed; test harness verdict failed

QEMU 11.1.1 / HVF, one vCPU, 32 GiB, job041 test Image
`a1ecd7f899097dc70870678281e3b99b69120412e5bad7bad01e55b43b1a6bbc`,
PMU disabled, dummy_hcd and a synthetic 3456×2234 framebuffer. The exact new
image pair is augmented only by VM test keys/probes; no target Apple controller
is present. This cannot prove native module initialization, clock transitions,
USB reconnect, MTP keyboard, GPU, SMP, thermals or macOS parity.

The wrong image, short transfer and full corrupt image were correctly refused.
Corrupt transfer: 2,469,319,544 bytes in 311.7 s at 7.9 MB/s. The good transfer
then verified its exact pin, received in 311.6 s, unpacked 215,521 paths in
9.6 s and switched. Desktop ready at kernel +677.06 s, second SSH verified at
+703.56 s, inherited repeat-delay/weather/keyboard-skip/one-CPU checks passed.
The refusal panels and desktop screenshot were inspected.

The final **overall harness verdict was FAIL**, +703.63 s: the CPU identity
function rejected QEMU's four-byte CPU `reg`, while the VM probe caught only
OSError/ValueError. Python reported `struct.error` before module load. The
native pinned DT uses eight-byte CPU registers; no firmware/driver/package
change is needed. The VM probe now accepts this specific four-byte-layout
refusal, and checks that the module remains absent. On such malformed/non-native
CPU layouts the current native CLI emits a traceback rather than a JSON stop;
it still exits before any module load. Do not suppress an error on real hardware.

The original failed verdict and private evidence are preserved under job052
`out/vm-full-refusal-20261020/`. A fresh normal-path run tests the corrected
probe without repeating the unchanged, already successful negative transfers.
The final controller run (21:05:45–21:05:52 UTC) also verified and executed the
**exact shipping optimized pointer-chase binary**: 12 positive-duration VM
samples; disassembly retains the dependent `ldr x23, [x23]` loop between the
clock reads. These are functional checks, not native latency measurements.


### Fresh normal-path VM run: PASS

Same shipping images and test kernel, corrected VM probe, no intentional bad
transfers in this run. Receive 311.7 s at 7.9 MB/s; unpack 9.7 s; stage-two
systemd +331.07 s, gadget +333.08 s, desktop ready +340.37 s, second SSH verified
+366.87 s. CPU asset hashes verified; virtual CPU layout refused before module
load; inherited image-fix checks PASS. Final verdict PASS at +366.95 s, used
memory 15,273 MiB. Only the expected `omarchy-provision-hardware.service` and
`ufw.service` system failures remain; the earlier user document-portal issue
is not resolved by these checks. Fresh desktop screenshot inspected.

**M5 offline preparation complete.** The earlier failed overall verdict remains
recorded; it is not relabeled a full-run PASS. The exact-pair normal boot and
the previously successful negative-transfer results together cover this
handoff's software path. Native/live results remain NOT RUN. M1 must verify
the published sources and both privately transferred images, report readiness,
then await the human start. The two images are staged in ignored
`build/attempt28-transfer/`; no image or raw log is published.

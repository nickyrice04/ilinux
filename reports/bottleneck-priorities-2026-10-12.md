# Bottleneck audit: t6050 native Linux and the working Omarchy VM

Snapshot: 2026-10-12. Target: the inventoried Mac17,6 / J716c, Apple M5
Max, ADT chip-id 0x6050, 18 CPU cores and 40 GPU cores. This audit continues
the existing work; it does not replace the patch series or benchmark suite.

**The main native barriers are boot/SMP, G17 graphics, and CPU power-state
management. The best immediately testable implementation is the existing
VM's video-download conversion and decode-format path.** These are different rankings: severity
for the native objective versus engineering value under today's test access.

Evidence labels: **Confirmed** means source or recorded test evidence;
**Measured** means an existing benchmark result; **Likely** is an inference;
**Unknown** requires additional evidence. No new physical-hardware experiment
was performed for this audit. The main implementation pass records its own
REA evidence and new video tests separately.

## What was already accomplished

The project already has an accelerated Omarchy desktop, heterogeneous vCPU
placement, a packaged 16 KiB Linux kernel with uclamp, VirGL graphics,
Venus/MoltenVK compute, ggml RPC to Metal, a VideoToolbox-backed H.264 decoder,
and seven native t6050 patches. Existing measurements include ~99% CPU
single-thread throughput, 99.7% of native GL ALU throughput, and 94–98% of
native MoltenVK compute. These are particular VM benchmarks, not native
Linux hardware support or a whole-system parity score.

Native patch validation is farther along than several documents say.
Job 018 applied patches 0001–0007 to Asahi commit
`77cb8f24c2381a8abb7272d7bbdec548d6426a8a`, built `sart.o`, NVMe `apple.o`,
and all DTBs, with recorded exit status 0 and no warning/error matches in
the saved build logs. The resulting `t6050-j716c.dtb` is 61,326 bytes.
This is object/DT compilation, not a complete kernel build, schema validation,
or a native boot. Evidence: [job script](../virtualization/jobs/018-asahi-compile-test/run.sh)
and its local `out/{run,compile,dtbs}.log` files.

## Three largest native barriers

| Rank | Specific blocker | Why it matters | What can be done now | What needs physical validation |
|---|---|---|---|---|
| 1 | **No demonstrated native Linux boot on this unit; secondary CPU startup unresolved for t6050.** | All native drivers and measurements depend on obtaining a running kernel; one core would leave most CPU capacity unavailable. | Preserve the existing DT and SART/NVMe series; perform schema checks and a full kernel build; prepare a bounded register-observation plan and boot artifact manifest. | Explicitly authorized m1n1/native session: first a one-core initramfs, then secondary entry and interrupt/IPI tests, followed by read-only NVMe checks. |
| 2 | **No t6050 G17 native GPU implementation and no validated t6050 DCP path.** | A firmware framebuffer cannot deliver the accelerated, efficient Omarchy desktop or GPU compute objective. | Reuse Mesa/Asahi architecture, write small workload/correctness probes and capture parsers, separate submission, memory, ISA, and display questions. Improve the working VM's transfer/fence path now. | G17 firmware protocol, command submission, mapping and coherency evidence; first native GPU job and GPU reset; display modesetting/page flips; then rendering/conformance and power tests. |
| 3 | **Native idle/resume and DVFS remain unvalidated; m1n1 disables ordinary WFI/WFIT on M4+.** | A booting kernel that spins while idle cannot meet laptop battery or thermal goals. A guessed energy model cannot establish efficient heterogeneous scheduling. | Keep the safe boot arguments; finish EAS/QoS policy and replay tests; reuse sanitized OPP data and existing macOS cluster/power measurements. | Verify idle entry/exit and saved state, establish cpufreq register semantics, collect actual per-cluster capacity/energy and thermal feedback, then validate suspend and repeated wakeups. |

### 1. Boot and SMP: exact uncertainty, not a guessed fix

**Confirmed:** m1n1's [initial t6050 PR](https://github.com/AsahiLinux/m1n1/pull/610)
reported powered-on secondaries that never entered its code on the tested M5
Pro. That report was created June 29 and merged July 10, 2026; it was not a
test of this exact Mac and firmware. Current
[smp.c](https://raw.githubusercontent.com/AsahiLinux/m1n1/main/src/smp.c)
still selects the T6031 CPU-start offset for t6050 and uses the same
two-register start sequence. The checked workspace snapshot is
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`.

**Unknown:** whether current m1n1 already fixes the observed failure through
later shared-state/entry changes. Absence of a specifically named fix is
not proof that the current build still fails. The repository's claim
"secondary CPUs never start" should be read as an unresolved prior report,
not a fresh local measurement.

The [existing enablement plan](../kernel/native-enablement/plan.md) gives
three useful discriminators: locked RVBAR versus the entry point; the
CPU_START protocol's four-bit cluster stride versus six cores per cluster;
and secondary early-entry/shared-state behavior. The apparent bit aliasing
is a **Hypothesis**, not sufficient evidence to change a register layout.
Do not change locked-register settings or guess MMIO writes to test it.
Ordinary macOS userspace and a Linux VM cannot observe these boot-time
register semantics.

The local DT already corrects the M/P MPIDR encodings and supplies PMGR
domains. The Linux work remaining is integration and hardware validation,
not regenerating the tree. A single-core framebuffer/initramfs test can
precede SMP and disk access; SMP is not inherently a prerequisite to seeing
the first Linux boot log.

**Public-source qualification:** the [August Asahi report](https://asahilinux.org/2026/08/progress-report-7-2/)
describes development successes for M4/M5 NVMe and PCIe. The
[M5 feature table](https://asahilinux.org/docs/platform/feature-support/m5/)
still lists no installer and TBA for these SoCs. These describe different
levels of readiness. They do not establish a bootable, validated t6050
Omarchy installation, and they do not justify claiming that no Linux has
ever booted on any M5.

### 2. GPU and display: firmware and hardware questions remain

The active-driver inventory identifies `AGXAcceleratorG17X`; the existing
Asahi/Mesa support recorded in this workspace is G13/G14. Asahi's
[M3 report](https://asahilinux.org/2026/02/progress-report-6-19/)
describes substantial GPU ISA changes beginning at G15. Adding a compatible
string is therefore not a credible G17 enablement patch.

Required evidence is specific: queue initialization and message formats,
firmware version negotiation, GPU virtual-memory layout, cache visibility,
completion/fault handling, and the instructions used by minimal workloads.
macOS compute results show performance potential; they do not reveal those
interfaces. DCP modesetting and scanout are separate from successful GPU
compute. A native display pipeline must validate both.

REA can organize authorized artifact identities, symbols, references and
targeted disassembly when a question depends on a binary. For ordinary
Mesa and m1n1 source, source analysis is stronger and cheaper. Retain the
project boundary against disassembling Metal or Apple's shader compiler;
use original workload probes and public hardware-interface observations.
No security bypass is required or proposed. Mesa's documented
[drm-shim](https://docs.mesa3d.org/drivers/asahi.html#drm-shim-linux-only)
can exercise compiler/UABI code off-device, but cannot prove GPU execution.

The working VM already supplies valuable graphics. Its remaining measured
costs include GL texture upload at 28% of native GL, draw calls at 50%, and
Vulkan submit/wait near 1.9 times the native MoltenVK latency. F-050's
intermittent ~10 fps boot is a reliability fault and should be investigated
before treating smooth-frame benchmarks as universally representative.
These figures and the current fixes are in
[VM parity](vm-vs-macos-parity.md) and
[F-050/F-051](../reverse-engineering/findings/catalog.md).

### 3. Idle, frequency and thermals: mechanisms before policy

Current [m1n1 kboot.c](https://raw.githubusercontent.com/AsahiLinux/m1n1/main/src/kboot.c)
appends `idle=nop arm64.nowfxt` when Apple system registers are locked,
explicitly because M4+ WFI/WFIT can lose architectural state. Current
[cpufreq.c](https://raw.githubusercontent.com/AsahiLinux/m1n1/main/src/cpufreq.c)
has no t6050 cluster case. These are bounded source facts; the native idle
power penalty on this unit is **Unknown** because it has not booted Linux.

The ADT provides frequencies and voltages, and the project has generated
OPPs and an experimental energy model. Register format, legal transitions,
core/SRAM voltage sequencing, residency, and wakeup correctness still need
validation. Linux-native cpufreq, EAS, uclamp and thermal policy are feasible
once those mechanisms are established. macOS driver names such as CLPC and
SOCTuner indicate promising research targets but do not prove the details
of their control algorithms. Targeted analysis should answer one question
at a time, for example which publicly observable demand signal predicts a
cluster transition, corroborated by repeated QoS/IOReport experiments.

The VM's measured +0.09 W idle increment and QoS placement are useful
engineering progress; macOS still supplies its physical idle, frequency
and thermal mechanisms. No guest policy can validate a native replacement.

## All eight requested subsystems

Each row distinguishes present implementation, missing information, useful
analysis, original Linux work and the next meaningful test. The
[existing macOS block map](../reverse-engineering/macos-hardware-services.md)
and [native plan](../kernel/native-enablement/plan.md) contain the detailed
ADT/driver associations. Public support status was rechecked against the
Asahi pages above on October 12.

| Subsystem | Works here / existing foundation | Remaining limitation and required evidence | Targeted analysis and feasible implementation | Test that would establish progress |
|---|---|---|---|---|
| CPU and scheduling | VM integer/compute near native; SME exposed; QoS tiers and heterogeneous vCPUs implemented. Asahi supplies arm64 boot, spin-table, cpufreq/EAS foundations. | Native boot/SMP unresolved; actual MIDRs and capacity/energy model not validated. VM MIDRs are masked. | Public m1n1/XNU source plus own QoS benchmarks; scoped PMGR interface research. Finish native integration and measured EAS policy; do not infer physical core pinning from guest CPU numbers. | Build now; later all 18 CPUs enumerate, per-CPU interrupt and workload tests, 1/6/12/18-thread throughput and energy with identical compiler targets. |
| GPU graphics/compute | VirGL and Venus work through macOS; ggml RPC reaches Metal. Asahi/Mesa G13/G14 code and test tooling are foundations. | G17 submission/ISA/firmware plus native DCP unimplemented; VM transfers/round trips and F-050 still cost performance/reliability. | Original microbenchmarks, public interfaces, targeted permitted binary analysis; Linux-side resource/fence and VM WSI fixes now. | Guest GL/Vulkan correctness, upload/readback, 60/120 Hz tests across repeated boots. Native first-job/reset then conformance and compute tests later. |
| Unified memory | CPU memory and 16 KiB VM kernel work; Venus blobs and IOSurface mirrors share selected resources. Linux DART/dma-buf/MM interfaces exist. | UMA is physical shared DRAM, not automatic API-level coherence. VM images may still copy; native DART SID/remap/cache rules unvalidated. Older VZ 4 KiB page-fault/latency numbers do not describe the current QEMU configuration. | Read Mesa resource transfer/fence code and accessible IOSurface interfaces; measure mappings/copies. Validate plane maps and completion before CPU access; the new format matrix disproves the broad dirty-state hypothesis. Native DART integration remains separate. | Reused-surface checksum tests, repeated map/unmap and cancellation, copy-bandwidth and latency; native DMA/IOMMU fault and cache-coherence tests later. |
| Video decode/encode | H.264 guest VA-API on VideoToolbox: recorded 600/600-frame exact GPU path; visible 4K60 playback 3.60–4.14 W versus native 2.91 W. Asahi AVD V4L2 stateless work is a native base. | Cross-format shader downloads fail outside the new lossless path; no general guest decode fence; synchronous main-thread decode. HEVC/VP9/AV1 and encode absent from current bridge; t6050 AVD unvalidated. | REA artifact/interface inspection plus public source and pixel tests. A separate Linux Mesa package now fixes even progressive downloads and opts into NV12 decode; see the implementation report. Fence/completion work precedes async decode; codec support next. | CPU `hwdownload`/`vaGetImage` frame hashes against software, B-frame/reused-surface tests, zero-copy regression, bounded A/B throughput and on-screen power. Native V4L2 tests later. |
| Neural Engine/ML | CPU SME and Metal RPC usable; macOS Core ML ANE reference measured. External `eiln/ane` provides an older experimental driver, not t6050 support. | ADT `ane,t8132exclave` and ANEExclaveProxy show mediation, not proof that independent Linux ownership is impossible. MMIO ownership, firmware loading and queue ABI unknown. | Metadata/capability observation and public Core ML behavior; avoid protected services or secrets. A restricted guest Core ML inference bridge is feasible independently of a native ANE driver. | Synthetic inference with output tolerances, explicit compute-unit selection and ANE energy residency. Native claims require actual ANE execution without macOS; GPU success does not qualify. |
| NVMe/storage | SARTv4 and M4+ register-split patches already compile. m1n1/public work supplies known register layouts and ANS ABI fixes. VM iothread/queues implemented. | Native ANS startup/power lifetime and offsets untested. Current VM 4 KiB fsync ~439 µs versus 98 µs native; warm cached reads must not be called SSD throughput. | Public source is sufficient for present patch; no proprietary decompilation needed. Validate patches; reduce guest dependent-I/O costs or test a separate ext4 workload volume within existing VM allocation. | Schema/full-kernel build now; bounded same-file fsync and cold I/O A/B tests. Later native identification/read-only hashes first; no host disk writes. |
| Power/thermals | macOS IOReport reference, VM App Nap policy, battery mirror and QoS tiers work. Linux cpufreq/EAS/thermal/SMC interfaces exist. | WFI state loss, t6050 DVFS/SMC keys and thermal envelope unvalidated; no native Linux energy-counter baseline. | Correlate bounded macOS QoS and frequency/energy observations; original Linux policy can use established interfaces. Validate native mechanisms before tuning. | Repeat idle/load/cooldown on AC and battery with recorded energy mode; native idle wakeups/suspend and thermal response later. |
| Peripherals | Guest keyboard/trackpad, networking, playback and clipboard work via host bridges; CoreAudio capture code exists but no live microphone recording was tested. Asahi has older MTP/RTKit/SPMI/audio/ISP foundations. | N1 Wi-Fi/BT has no implemented project Linux driver; new USB PHY/SPMI, audio DMA, H16 camera and mic paths unvalidated. Touch ID has no implemented Linux authentication path; SEP-mediated enrollment/matching interfaces remain unavailable. Do not infer support from an external fingerprint reader. | Metadata identifies actual providers; targeted non-security interface analysis can narrow new transports. Guest camera/UVC bridge or generic USB support offers nearer-term functionality; each is separate from native support. | Synthetic capture first, user-initiated real mic/camera test only when intended; USB enumeration/hotplug and later native keyboard/trackpad, audio, camera and network tests. External libfprint/FIDO2 devices are alternatives, not Touch ID support. |

## Why video is the current implementation choice

F-045 supplied a reproducible wrong-result report: GPU playback works,
but some CPU downloads fail. The new matrix narrows this to cross-format
conversion; same-format downloads work. It points to a small,
original Linux userspace driver change with full source, an installed
binary, an existing test stream, and a working end-to-end hardware path.
This offers a shorter evidence-to-code-to-test loop than speculative G17 or
native PMGR work. It also restores useful software paths (`hwdownload`,
copy-back playback, image extraction) rather than only improving a score.

The second change, opting into the host's native NV12 output, removes an
observed conversion; it is validated separately. The
[implementation record](video-download-and-nv12-2026-10-12.md) reports both
changes, pixel correctness and CPU cost. A power saving remains unproven.
Do not make host decode asynchronous as part of either fix: an END_FRAME
ordering assumption is not an asynchronous completion contract.

The implementation record includes artifact hashes, REA capability limits,
source and patches, compiler options, frame hashes, CPU/power observations,
clip parameters and guest/host versions. Source and experimental evidence
rejected the initial dirty-state fix. Reproducible output tests establish
the narrower implemented behavior.

The next practical VM work is F-050's recurring frame-rate collapse and
video codec/encode coverage. Native work can continue concurrently through
schema/full builds and a concrete first-boot diagnostic plan. Applying or
testing boot artifacts still requires the user's explicit native-boot
authorization; no host changes were made for this audit.

## Continuity corrections for the main pass

These documentation inconsistencies were discovered and corrected during
this pass. They are not new hardware results.

* `kernel/patches/t6050/README.md` and B-004 said compile pending;
  job 018 proves driver/DT compile completion. Schema/native tests remain.
* B-011 described stock Arch's missing uclamp; the current packaged VM kernel
  has both `CONFIG_UCLAMP_TASK=y` and `CONFIG_UCLAMP_TASK_GROUP=y`.
* The roadmap's "G13–G15 supported" is too broad. Its GPU VM approval and
  several video/Vulkan TODOs are also older than completed work.
* The block-map table still says CPU video decode in the VM, superseded by
  D-029; several older presentation/power explanations were corrected by
  F-048–F-051. Use the visible-window results for playback parity.
* Some source-date prose conflicts with actual commit metadata. Pin commits
  for reproducibility; `job018/out/base.txt` records the tested base exactly.

No claim in this audit relies on a VM proving native Apple device support.

Implementation outcome: [video download and NV12 experiment](video-download-and-nv12-2026-10-12.md).

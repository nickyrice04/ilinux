# Why desktop actions wait: offline diagnosis, 2026-10-21

**Attempt31 stays HOLD. No replacement native boot is ready.** This work
preserves the working native kernel, keyboard, USB transport, images and macOS.
The next fix must address action latency, not only a relative callback score.

## Established mechanism, with its boundary

The original Hyprland event loop spends long intervals executing software
rendering. During these intervals it cannot service application commits or
input. In the final one-vCPU VM reproduction with the installed Omarchy shell,
three terminal launches reached their first buffer commits after
**811.6,971.6,975.8ms**. Rendering occupied **785.1,945.7,952.6ms** of those
intervals. Only 23–27 ms lay outside rendering. These are received-buffer times,
not first visible pixels or a measurement of physical keyboard firmware.

Direct menu commands returned in36–112ms in that run. All three actual menu
layers were independently observed. Command return does not mean the menu
was already visible. Full-size callback median was250.2ms; quartering pixels
gave56.8ms. This scaling is diagnostic evidence of pixel-work cost, not a
proposal to lower native display resolution.

This mechanism agrees with prior native evidence: attempt26's independent
reader saw kernel-event delivery within5.2ms while key actions generated
seconds of CPU work; attempt30 spent about97% of one CPU in the compositor
under load. **The full native3–5s interval remains unmeasured.** Do not convert
the VM timings into a native latency claim or clear the keyboard/memory paths
without that measurement.

Normal tracing showed time concentrated around final rendering. A separate
drain experiment established that much of it was **deferred scene work**:
scene completion median173.7ms, final-pass completion52.5ms. The call that
submits the final pass itself took0.056ms once scene work was drained. Thus
removing final-pass work alone leaves most rendering time intact. This is an
attribution diagnostic, not an optimization. Nested timings overlap.

The larger improvement was in a **VM-only threading sensitivity test**. Four
configured llvmpipe workers, with the compositor allowed on six guest CPUs,
reduced terminal first-buffer times to42.1–42.4ms and full callbacks to59.5ms.
Menu/terminal clients remained pinned to one guest CPU, with their renderer
threading unchanged. This supports prioritizing native SMP plus measured
renderer threading. It does not establish that native secondary cores work,
predict the exact native gain, or measure power use.

A separate option check found blur **already disabled**. Four repeated controls
with that original value gave full callbacks216.9–218.5ms. Active blur is not
the explanation in this tested image; no visual-quality setting was changed
for the accepted threading result.

The separate fixed-scene observer control gave full-callback medians of
269.4–280.7ms without logging and279.0–280.7ms with logging, three runs each.
Ranges overlap; the cost is not distinguishable from this small sample's
variation. It does not bound overhead on the native M core. Raw sanitized
summaries are in [vm-results.json](vm-results.json).

## CPU and memory references

One thread; AC power; same original sources and fixed workloads. macOS
26.6.2/25G83 uses Apple clang21; the development VM uses GCC16.1.1; both use
O3/ARMv8.4-a. Inline-assembly FMA/dependent-ADD work is fixed; C-generated
integer, memory and pixel instructions can differ. Raw sample summaries,
source hashes, flags, page sizes and placement observations are in
[macOS reference](macos-reference.json) and
[Linux VM reference](linux-vm-reference.json).

| Work | Native Linux, existing evidence | macOS default | macOS background | Linux VM |
|---|---:|---:|---:|---:|
| Dependent-ADD clock estimate |~2.65GHz |4.589GHz |1.341GHz |4.548GHz |
| Fixed NEON FMA |NOT RUN |144.529GFLOP/s |31.100GFLOP/s |139.913GFLOP/s |
| STREAM copy,128MiB/array |NOT RUN |140.62GB/s |44.34GB/s |125.62GB/s |
| STREAM triad,128MiB/array |NOT RUN |130.94GB/s |39.19GB/s |129.41GB/s |
| CPU-only3456×2160 pixel copy |NOT RUN |0.396ms |1.218ms |0.573ms |
| CPU-only premultiplied alpha-over |NOT RUN |3.266ms |15.094ms |3.645ms |

The pixel tests never use a GPU or graphics API; both systems produced the
same checked outputs. They isolate simple arithmetic and ordinary RAM access,
not the full Mesa shader/compositor workload. Fast copies do not prove that
framebuffer mappings or native DRAM-controller policy are correct.

The native boot uses one M core; 17 of 18 cores are offline. macOS QoS changes
placement/frequency and is not affinity. The VM's physical core and memory
controller remain managed by macOS. These contexts do **not** establish native
Linux throughput, bandwidth or energy parity. Existing pointer-chase results
also vary greatly with macOS placement; see the memory29 findings. Native
STREAM/FMA/pixels, alone and under desktop contention, are the missing checks.

## Implementation and validation

Original source and reproduction steps:
[`kernel/experiments/latency31`](../../../../kernel/experiments/latency31/README.md),
[`job056`](../../../../virtualization/jobs/056-desktop-timeline/run.sh).
The trace-enabled original compositor compiled in the VM with no copy31 code;
normal tracing adds no GL finish. A separate flag enables the drain diagnostic.
The final executable is14,202,864bytes, SHA256
`b22fedff2f75a7a955bb881aa5c314d6e7028570f98204d981eb0012bf920c6e`.
It is private build output and is not installed in any native image.

Twelve evidence-integrity tests pass. The CPU pixel implementation passes an
independent small-image oracle and four invalid-input controls. macOS and
Linux VM full-size pixel checksums match. The final VM trace checks reject
missing stages, empty/saturated data, absent menu layers and incomplete frame
controls. Physical input, native runtime and physical presentation are NOT RUN.

Rejected runs are preserved privately: initial build exhausted the VM disk
(resolved by building in guest RAM, removing only this job's failed tree);
the first workload had no Omarchy shell (rejected, explicitly launched the
installed shell); the initial global logger was consumed by a preliminary
launcher query (rejected, changed to lazy initialization). Do not count those
runs as successful timing evidence. The headless VM also lacks some native
system-service/controller behavior. Cleanup falls back to recursive guest
unmounting if background session processes retain the RAM-root mount.

## Engineering priority from this evidence

1. **Use the timeline as the gate for revising attempt31.** Measure native
   input arrival, first buffer, rendering and submission alongside matched
   compute/memory work. Select an improvement that reduces absolute action
   latency and preserves keyboard accuracy and output correctness. Publish
   another boot only with pinned artifacts, bounded collection/return and
   reviewed native overhead; keep the existing candidate held meanwhile.
2. **Native SMP is a high-value implementation track.** The current single
   core must execute compositor, rasterizer and every application. After core
   startup is proven, measure renderer threading and application contention.
   More cores alone do not make a long serial event loop responsive, and a
   frequency-request observation is not proof of complete CPU behavior.
3. **Move G17 GPU enablement onto the critical path now.** The rendering
   workload belongs on the GPU for the final performance/efficiency goal.
   The current Asahi driver has no t6050/G17 hardware or firmware handler.
   Target verified memory/firmware ownership, command completion and one checked
   render, then compositor integration. REA findings and remaining dispatch
   questions are in [gpu-findings.md](gpu-findings.md). No schedule estimate or
   claim that a new device ID completes this work is supported.

The optional copy31 optimization remains available for later controlled
comparison. Its earlier25% sparse-workload result is not the acceptance
criterion for a workstation. The target is measured prompt key echo,
cold/warm menu/application readiness, multiple responsive apps, and eventually
power/thermal behavior against this machine's macOS reference.

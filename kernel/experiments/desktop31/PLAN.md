# After attempt30: reduce measured desktop stalls

2026-10-21. M1 result `45952cc` is the starting point. Attempt30 is consumed.
This work preserves boot042, one CPU, the keyboard and USB control path, and
builds a new matched pair from the working attempt28 images. No macOS, boot-policy, volume, installed
m1n1, frequency, storage or network-device change is part of this experiment.

## Evidence and ordering

**Measured native:** two controlled workloads used about 97% of the compositor
process's available CPU time. Small-damage callback medians were 256.940 and
256.346 ms; full-damage medians were 513.491 and 516.029 ms. IPC medians during
those workloads were about 408 ms. Most main-thread samples landed in anonymous
executable mappings; those samples are not automatically attributed to Mesa.
The dependent-ADD estimate remained near 2.65 GHz. Accurate typing did not
establish prompt event handling. The human confirmed persistent application
delay; per-action timings and power/thermal measurements were not collected.

The immediate priorities are:

1. **Drawing work on the single available CPU.** Find and eliminate redundant
   pixel processing while preserving output. Test a direct framebuffer copy
   for the final identity pass, retain normal rendering for transforms, color
   conversion, screen effects and unsupported formats, and measure both paths
   in one Linux session. A faster isolated copy does not establish a faster
   desktop or explain all application-start latency.
2. **Secondary-core startup, then scheduler capacity and power management.**
   Reuse the October19 CPU-start findings. The six-bit cluster descriptor fixes
   mask collisions but does not explain same-cluster startup failure. Establish
   reset-entry ownership and incoming state, then test one secondary with
   bounded liveness/exception reporting before scaling to all 18 cores. Keep
   idle/context preservation, thermal telemetry, supported OPPs and frequency
   transitions as separate validation steps. A maximum-clock setting is not
   an efficiency policy.
3. **Native GPU acceleration.** Software drawing at panel resolution remains
   a structural constraint even if the copy optimization succeeds. Identify
   the exact GPU/firmware interface and the applicable Asahi/Mesa gaps; require
   command submission, memory coherency, synchronization and reset tests before
   desktop use. CPU improvements alone cannot promise macOS graphics parity.

Networking and storage remain workstation acceptance requirements: a browser
over built-in Wi-Fi, bounded storage measurements on a dedicated test target,
and an explicit read-only file-sharing plan. macOS APFS access, especially
encrypted data, is a separate filesystem/key-availability question from NVMe
speed. Do not mount the original macOS data volume writable or treat the USB
SSH transport as completed Wi-Fi support.

## Implement and validate

1. Audit the exact pinned Hyprland final-render path and framebuffer coordinate
   conventions; record hypotheses separately from observations. The pinned
   public source is preferable to decompiling this open-source implementation.
2. Build an original GLES3 comparison covering full/partial/edge/empty damage,
   vertical orientation and RGBA/RGB destinations. Compare every output byte,
   including pixels outside damage. Use balanced timing order, warm-ups and
   single-vCPU software rendering; preserve all samples.
3. Compile an opt-in Hyprland experiment against upstream
   `efb50993780079460b0cbed1363e2166a2de1d9f`. Default off. Bound it to the
   unrotated 3456x2160 llvmpipe path with no color conversion or final effect.
   Verify the first eligible copy for each framebuffer pair against the
   original draw; mismatch/error falls back for the rest of that session.
4. Exercise the rebuilt executable with the exact retained Omarchy userspace.
   Check ABI startup, configuration toggles, active-path evidence, pixel
   equality, crossover timings and fallback cases. Treat headless validation
   as offscreen rendering, not physical presentation.
5. Only after those checks, package a bounded RAM-only native A/B collector
   with explicit identity/hash guards, cleanup and M1 instructions. Restore the
   original draw path through the default-off runtime option. Build a new pinned
   pair from the existing root with only the compositor and experiment assets changed; never replay the consumed attempt30 collector as a new run.
6. Publish precise pins and offline outcomes. M1 verifies intake and reports
   readiness before the human restarts. Native results, actual presentation,
   visual correctness, responsiveness and efficiency remain NOT RUN until
   observed on the M5. If offline tests do not justify a native candidate,
   publish the blocker rather than request another speculative reboot.

## REA evidence and its limits

The existing attempt30 REA/Ghidra CPU-policy investigation checked 443 ARM64
instruction words against the original carrier and LLVM. Two whole-function
decompilations were rejected for boundary errors. Its usable behavioral facts
separate work-interval feedback, scheduler preference and performance requests;
they do not supply safe clocks, thermal limits, a secondary reset contract or
a solution to expensive software drawing. See
`native/boot/attempt30/rea-findings.md` and
`reverse-engineering/findings/cpu-startup-2026-10-19/README.md`.

No new Apple decompilation is needed to implement this open-source render-path
change. Reuse validated behavioral findings, not rejected pseudocode. New REA
work on the CPU track should answer the unresolved entry/state question with
bounded independent checks. Apple artifacts and decompiler output remain
private under ignored build paths; published code is original Linux code.

## Measurement correction

Review found repeated Aquamarine auxiliary-renderer errors in job054's VM log;
the pinned source shows that these can follow a successful display commit.
The earlier callback/CPU observations prove client, sampler and rendering work
ran, but do **not** establish successful VM display presentation. Neither its
timings nor its preliminary color-management comparison is evidence of native
causality. See `native/boot/attempt30/vm-evidence-addendum.md`.

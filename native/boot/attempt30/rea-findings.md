# CPU policy evidence for attempt30

2026-10-20. Local static analysis of this personally owned Mac's existing
AppleT6050CLPC member, macOS 26.6.2 / 25G83. REA6.4.0 with Ghidra12.1.4 in
the existing isolated ARM64 lab; no target binary executes. Carrier/member
hashes and exact entries: `rea-plan.json`. Raw Apple bytes, disassembly,
pseudocode, logs and project files stay under ignored private build paths.

## Question and results

Does macOS merely hold a fast CPU state, or are presentation work, scheduling
preferences and performance changes distinct interfaces?

| Function | Entry | Bounded observation | Confidence/limit |
|---|---|---|---|
| SchedulerInterface::workIntervalNotify | `0xfffffe00097c9908` | 524-byte body references current operating state, a thread-group variant, presentation-group registration and event submission. | Original bytes/131 LLVM instruction words match. P-code stays inside body; manual interpretation required. Ghidra marks a call at +0x8c terminal despite a non-noreturn target: do not assume complete reconstructed control flow. |
| SchedulerInterface::raiseClusterPerformanceIfNeeded | `0xfffffe00097cef80` | Direct call references include current unconstrained state, cluster-performance raise, pending-change bookkeeping, step-up timer cancellation and scheduler performance notification. | 1,180 bytes/295 instruction words match. Whole-function pseudocode REJECTED: 17 out-of-body p-code operations and truncation warning. Only bounded call/reference facts used. |
| PreferenceManager::sendPreferenceToScheduler | `0xfffffe00097c7d5c` | Separate named scheduler-preference entry exists; its indirect dispatch is unresolved. | 68 bytes/17 instruction words match. Pseudocode REJECTED: four out-of-body operations. Does not establish preference enum values, targets or placement policy. |

**Confirmed static:** 443 instruction words independently match the retained
carrier and LLVM decoding, with no unknown instruction words. **Inferred:**
interactive performance is a feedback/integration problem involving work,
placement and performance requests, not simply one maximum-clock setting.
No active macOS thresholds, power limits, timing guarantees or native Linux
register writes are inferred from these functions. Two rejected decompilations
are not converted into usable implementation source by renaming variables.

## Original Linux engineering decisions

1. Measure presentation-related work and event-loop delay alongside CPU usage.
   That led to `frameprobe.c`, `samplecpu.c` and the bounded original collector,
   not an imported Apple algorithm. Native observation is still required.
2. Keep CPU frequency and placement separate. Linux already provides
   [schedutil](https://docs.kernel.org/scheduler/schedutil.html) and
   [utilization clamping](https://docs.kernel.org/scheduler/sched-util-clamp.html)
   for scheduler-driven frequency requests and task performance hints. These
   require working drivers and calibrated capacity/frequency information;
   they cannot activate the currently offline CPUs or fix a blocking draw.
3. Preserve the existing single-core boot and unknowns. No thermal headroom,
   safe clock cap, secondary reset-vector contract or Linux-visible firmware
   policy is established by this analysis. Follow the CPU track in the
   experiment README, including the existing SMP findings.
4. Reject unsupported visual compromises. Pinned open-source Hyprland commit
   `efb50993780079460b0cbed1363e2166a2de1d9f` has a conditional color-management
   path in `src/render/OpenGL.cpp`, but the preliminary VM A/B showed no useful
   full-frame gain. Native attempt30 does not disable it.

Validation metadata is `rea-validation.json`. The original kernel source URL
initially queried for `osfmk/kern/sched_perfcontrol.c` returned 404 and was not
used as evidence. No proprietary artifact was sent to an external service.

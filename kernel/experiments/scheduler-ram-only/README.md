# Boot033: remove rendering from scheduler instrumentation

2026-10-14, following M1 attempt 13 (`9a045cf`). Native boot033/attempt 14
**NOT RUN**. Preserve boot032's GPIO exclusions and all working boot setup.

**Observed:** attempt 13 passed live GPIO ADT and effective-DT gates. The final
photo shows P05/W00/H06/D0000/I000/B00/C0000, with S unreadable; sampled video
shows S06 once. No attributed retry, GPIO result or PID 1 was observed. I000
does not identify a pin read. H06 is the bounded kernel watchdog, not userspace
liveness. The 40.13-second clip does not cover the whole observation window.

**Confirmed source defect:** every active scheduler checkpoint invokes the
eight-lane framebuffer renderer. These hooks run inside scheduling and context
switching, including regions with interrupts disabled and scheduler locks held.
For an illustrative 8x16 font at scale 4, each complete 37-character repaint
stores 75,776 pixels / 303,104 framebuffer bytes. This is a work-count calculation,
not measured native latency. Many checkpoints execute per context switch.

**Hypothesis:** diagnostic overhead contributes to the changed worker/console
progress. The report does not prove scheduler deadlock or that the GPIO repair
worked. Do not discard the GPIO repair or skip another initializer.

`apply.py` changes one digest-pinned boot032 header: scheduler hooks retain
phase/PID/selection counters in RAM, with no framebuffer call. The existing
five-second, six-sample watchdog displays S before H and before logging.
**S is now a sampled last scheduler checkpoint, not an immediately painted
boundary.** It may remain zero until the first watchdog or stale afterwards;
that alone is not a stall. P/W/H/D/I/B/C retain their meanings. Other panel
marks still repaint it, but do not refresh S's sampled value.

The actual old/new hook regression makes 10,000 old calls versus 30,000 new
checkpoints, confirming 10,000 versus zero renderer calls and preserved state.
ASan/UBSan pass. The linked new function is 56 bytes / 14 instructions with no
calls; all instruction words match the packaged Image. Exact source and linked
instructions answer this question directly, so no additional proprietary
decompilation was necessary. Prior REA findings and their uncertainty remain
applicable to the unchanged GPIO implementation. No safety filter was bypassed.

Only Image changes among payloads. DT/config/initramfs/m1n1, reserved pins,
single CPU, fixed arguments, hardware guards, DAPF/framebuffer corrections and
the existing clock-debug skip remain. No boot/security/volume changes.
Full Image/ELF roundtrip, controller tests/intake and generic VM checks are
recorded in `validation.json`; none establishes native compatibility.

M1 follows the current Stage-B checklist: offline readiness, one human-started
filmed attempt, stop at the milestone/error/120-second bound and return to
Macintosh HD. Capture native PID 1 if reached; otherwise record actual device,
pin, errors and sampled scheduler evidence. Native control/input and a usable
RAM root for the Linux configuration agent come after stable diagnostic userspace.

# After census 31A: CPU1 entry and parking before Linux SMP

**Superseded for execution:** the implemented controller and offline evidence
are now in [attempt31b-instructions.md](attempt31b-instructions.md). Keep this
document as the design record; its not-ready wording describes that earlier
milestone. Native31B remains NOT RUN until the M1 publishes a result.

2026-10-21. **Planning handoff only. Do not restart or run a target command.**
31A is consumed; the previous copy-only 31 remains held. This update does not
release a 31B executable or authorize another live session. Existing macOS,
boot021, Boot Lab, security policies, default disk and volumes stay unchanged.
Routine policy rechecks remain waived.

## Result reviewed

M5 fast-forwarded through M1 report commit `527defe`. The
[native result](../../native/boot/attempt31a-2026-10-21-result.md) and
[sanitized JSON](../../native/boot/attempt31a-census-2026-10-21.json) agree:
CPU0 and CPU1 locked RVBAR mirrors both name the installed vector entry at
image offset 0. Exit 0 in 1.155 s, exactly two hardware reads, zero starts, followed
by the human-confirmed Macintosh HD return. No native Linux or renderer trial
ran in that census. Matching mirrors remove the observed-address mismatch
concern; they do not show a core executing the entry.

## Decision: use the installed entry, test one secondary

Prefer a **CPU1-only RAM-state controller** over replacing or chainloading
m1n1. Offline inspection of the exact installed boot021 image verifies that
its vector branch reaches `cpu_reset`, whose non-EL3 path calls `_cpu_reset_c`.
Pinned public source then provides the existing stack selection, CPU setup
and SMP park loop. The linked image has a dedicated 64 KiB CPU1 stack and an
uncached SMP shared-state area. We can prepare that existing RAM state without
changing its reset vector or executable text. This is a design decision,
**not a tested deployment**.

Source: public m1n1 revision `57a9339ffd1876e78297b17d34dece8cff8fa1ba`,
`src/start.S`, `startup.c`, `smp.c`, `memory.c`, `proxy.c`, `utils.c` and
`smp_asm.h`. Original offline verifier:
[audit_boot021.py](../../kernel/experiments/smp31/audit_boot021.py);
machine-readable [layout evidence](../../kernel/experiments/smp31/boot021-ram-layout.json).
The two branch checks establish static destinations, not the reset execution
state. Five verifier test methods PASS; eleven census and eight renderer
regressions PASS. No VM/native CPU start was performed by this review.

Existing byte-validated REA findings establish the PMGR start group. Fresh
decompilation is not the missing evidence here: the installed open-source
entry is available, while whether CPU1 executes it requires a native test.
Do not reuse rejected PMGR pseudocode, replay SPTM initialization, or patch
the cold `_start` path based on an older hypothesis.

## Controller to implement before 31B can be released

1. Reuse 31A's exact board/topology/image/client checks as fresh preconditions
   within the start experiment, not as a second standalone census. Validate
   all code ranges the proposed controller actually relies on, all 32 spin
   records, CPU0 identity, fresh CPU1 reset-stack record and locked mirror
   matches. Validate the entry's EL/feature assumptions through a bounded
   read-only helper. Refuse a stale or partially prepared session.
2. Reserve the attempt durably on the M1 before the first mutation. Select
   WFE parking **while all secondary flags are zero**. Prepare only the
   reviewed CPU1 RAM fields: `target_cpu` and the persistent dedicated reset
   stack. Read back and order the stores before issuing either start write.
   Do not synthesize CPU1's MPIDR/arrival flag/reset-stack-table result; those
   must be written by the secondary itself. Keep the dedicated stack even on
   timeout because entry can arrive late.
3. Issue exactly the existing same-cluster CPU1 start sequence:
   32-bit value 2 to `0x280688004`, then 32-bit value 2 to `0x280688008`.
   Check the guarded exception result after each; a first-write fault stops
   before the second. No read/modify/write of unrelated bits, bulk start,
   RVBAR write, cluster-power or frequency change. These are **hardware
   writes**, confined to the intended CPU1 startup experiment.
4. Bound the arrival observation. Require CPU1's own MPIDR `0x40001`, arrival
   flag, correct stack-table entry, and no unexpected other-core activity.
   An arrival flag proves the C entry progressed; it alone does not prove the
   park loop is responsive. A timeout does not prove which earlier stage
   failed. Preserve that uncertainty in the result.
5. Prove a bounded request/return through the parked loop, using a tiny
   reviewed RAM helper for ordering/event signaling if necessary and the
   existing read-only timer function for the secondary callback. Check
   request acknowledgment, completion and progressing counter values, with
   explicit deadlines and no retry of a pending request. Do not publish raw
   counter values, addresses or console output. This is not Linux timer IRQ,
   IPI or long-term coherence validation.
6. Stop on success or failure, preserve evidence, and return by human power
   off to Macintosh HD. No generic secondary stop or deep-idle call. Use an
   independent human timer as well as controller deadlines: a stalled target
   need not honor a host deadline. No Linux launch or automatic continuation
   to more cores in 31B.

Two important source-review traps shape this design:

* `smp_call` and `smp_call_sync` have unbounded target-side waits. The name
  of the former does not make it an asynchronous, bounded request. Do not
  directly use them as the proposed heartbeat implementation.
* `smp_set_wfe_mode(true)` sends IPIs to already-alive secondaries before SEV.
  Use it only before CPU1 starts; do not use it afterward as an event-only
  wakeup. Any new helper needs its own compilation, instruction audit,
  placement/cache checks and refusal tests before release.

The earlier full-image `m1n1-OFFLINE.bin` stays offline. Its guarded-start
tests are useful design evidence, not tests of this new controller. The RAM
controller must earn its own tests, including partial failure after each
write, late arrival, wrong identity, stalled callback, stale session and
unexpected-core cases. M1 independently reviews its exact pins and published
readiness only after that implementation is complete.

## Fast path to the desktop after entry works

Next prepare the exact **two-core** Linux spin-table handoff, DT and launcher
together. The current launcher deliberately rejects started secondaries and
caps Linux at one core; changing boot arguments alone is insufficient. Verify
per-core timer progress, affinity, scheduler wakeups and the existing bounded
coherency test before starting the compositor. Keep frequency unchanged and
`idle=nop arm64.nowfxt` until idle is separately validated.

Then use one compositor worker on two available CPUs, keeping client workers
separate. Compare identical pixels/visual settings and collect terminal
first-buffer, full-frame, physical interaction, CPU/memory and thermal/power
evidence. The prior VM terminal 685–754 ms versus 37–41 ms result makes this a
high-value experiment, not a prediction for the M5. Two cores barely changed
the VM full-frame time; additional validated cores and eventually GPU support
remain necessary for throughput and efficiency.

Expand within the boot cluster before another cluster, apply the validated
six-bit start-mask layout when crossing clusters, and retain measured gates.
Native SMP plus busy idle is not macOS-level energy efficiency. Wi-Fi,
storage, G17 rendering and power management remain distinct subsequent work.

## M1 now

Pull the update, read this decision and the reviewed result, retain the
verified boot042 package and existing images, and wait in macOS. Do not rerun
31A, transfer the offline image, open the proxy, run the older 31 profile, or
restart for 31B. The next executable handoff will explicitly replace this
planning-only notice. No new user permission request is needed merely to
continue the already-authorized offline engineering.

The old 31A source manifest records the frozen `964aaac` handoff, including
the former `stage-b-instructions.md`. The current pointer intentionally
changes; do not regenerate or use that historical manifest as a 31B manifest.

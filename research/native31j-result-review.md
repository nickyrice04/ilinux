# 31J review: resolve secondary entry before another physical attempt

2026-10-21 Eastern. Reviewed M1 report commit `f4156af`, execution `3277ca1`.
This is an offline assessment. **31J is consumed; no 31K controller or restart
readiness is released.** macOS, installed boot021 and all consumed inputs stay intact.

## What the run establishes

The [M1 report](../native/boot/attempt31j-2026-10-21-result.md) and its
[controller JSON](../native/boot/attempt31j-controller-2026-10-21.json) agree:

- Primary discovery succeeded on the first query in 20.81 ms. Serial, UART,
  proxy, source recheck and controller construction passed. No connection,
  journal, finalization or supervisor-deadline error was reported.
- The corrected reset-readback predicate passed. Both CPU1 start commands
  were attempted and acknowledged. The exact CPU1 mapping remains supported.
- CPU1 PS actual values were 0,0,15,15; opaque state bytes were 0,0,2,2 across
  before/first/second/final samples. CPU0 stayed 15/2. Both fields therefore
  responded after the second command, with all eight reads of each kind complete.
- The recorder completed 93 samples/465 reads with highest observed phase 0.
  No committed CPU1 identity, arrival, callback or park was observed. This does
  **not** say every uncommitted raw record field was zero.
- The controller stopped at its natural arrival timeout in 5.270 seconds;
  normal Macintosh HD was human-confirmed at +45.136 seconds. Linux SMP was not run.

These observations remove the connection failure and the old readback refusal
as blockers in this run. They do not establish CPU1 instruction execution,
effective reset destination, reset release or performance. The opaque byte's
meaning remains unknown; matching CPU0 does not grant permission to run callbacks.

## Independent visibility review

The recorder buffer is at image-relative 0x90a40, inside the pinned SMP shared
range 0x90000–0xa0000. The live record-first/last read/write translation checks
passed. Their validator requires the exact physical address and attribute 0,
Device-nGnRnE, rather than ordinary cached RAM. Pinned m1n1 `memory.c` also maps
the shared aliases with that attribute. CPU0's reader is the fixed aligned
LDR helper. A generic CPU0 stale-data-cache explanation is consequently weak;
adding cache invalidation is not supported by this result.

Those are CPU0 facts. CPU1's incoming translation/cache state remains unknown.
Its marker requires the vector hook to be fetched, the recorder branch/address
calculation to execute, and its first store to complete through CPU1's address
view. CPU0 publication/readback cannot prove those conditions. Existing offline
fault tests already demonstrate that a fault before the first store can leave
phase 0. Their synthetic memory model does not emulate hardware coherence or
firmware dispatch. No concrete observer implementation bug was found in this review.

Sources: `native/boot/smp31g.py` (publication/sampling),
`kernel/experiments/smp31e-entry/permissions.py` (record attributes),
`kernel/experiments/smp31f-entry/recorder.S`, `telemetry.py`,
`recorder_check.py` and `test_recorder_check.py` (phase and fault semantics).
Public m1n1 source is pinned at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.

## Next work, in order

1. **Trace the effective secondary-entry contract with focused REA.** Follow
   source-entry provenance and branch selection around matching-board firmware
   function 0x100c1ae53b8 and its call to 0x100c1c2e398. Connect the selected path
   to the custom raw-boot handoff. Retained analysis proves input alignment and
   address-field formatting, but not which branch ran or CPU1's first fetch.
   Keep raw decompiler output local; validate useful claims against original
   bytes, bounded control flow and independent public-source evidence.
2. **Validate a discriminator for fetch versus first-store failure.** Audit
   the exact boot021 image and all proposed marker paths under explicit entry,
   translation and fault assumptions. Consider a separate pre-start positive
   control for the observer, using a distinct scratch record and preserving
   CPU1's fresh record. Such a control could validate the measurement path on
   CPU0; it would not prove CPU1 visibility. Do not directly call the current
   reset-vector recorder as a returning function or treat vector entry as
   reset provenance: that slot also serves a synchronous exception vector.
3. **Release 31K only when it can distinguish concrete outcomes in one boot.**
   It must report a meaningful new entry/publication result beyond the same
   PS/state transitions. Retain strict identity, a bounded single session,
   first-error stop and immediate macOS return. Review new operations, compile
   any helper, run actual-image/fault/wire tests and publish M1 instructions
   before declaring restart readiness. The exact change is not determined yet.
4. **After verified CPU1 execution, move to a two-core Linux batch.** Check
   atomics/coherence, timers/IPIs, bounded load, frequency/memory throughput and
   renderer/input latency together. Then expand through the second Performance
   cluster and the Super cluster using validated topology, measured scheduler
   capacity and idle behavior. Startup alone will not establish macOS parity.

The old October15 late-entry patch contains assumptions later withdrawn; it
must not be installed unchanged. Neither this report nor retained firmware
evidence justifies redirecting a secondary to cold entry +0x800, a new stop-clear,
another start bit, a longer timeout or additional cores. CPU1 is in the boot
cluster; the known later-cluster mapping issue does not explain its failure.

## Review record

Two independent read-only reviews covered reset dispatch and recorder visibility.
The final JSON was checked for consistency with the report; all 226 frozen 31J,
202 31I and six host-diagnostic source pins remain unchanged. No new REA query,
VM run, hardware command, image, live controller or boot/security change was
performed for this assessment. Fresh REA is the next investigation, not evidence
already obtained. M1 should preserve the consumed run and await a new handoff.

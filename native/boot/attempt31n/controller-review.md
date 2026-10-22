# 31N controller review

31M's successful CPU0 controls and two start acknowledgements did not establish
CPU1 execution. 31N tests a concrete difference in our startup sequence: the
original offline target model counts 127 interface calls and 33 journal callbacks
between the two stores. Those counts are not measurements of the native delay.
The pinned m1n1 source and bounded macOS PMGR paths group the stores locally.
Neither source establishes a required inter-store deadline.

## Scope and implementation

The same 32-bit value 2 goes to the same addresses, in the same order:
0x280688004 then 0x280688008. CPU1 remains the sole secondary, in CPU0's active
Performance cluster. The exact boot021 image, CPU1 vector/cold prefixes, Normal
and Device records, cache controls, source/reset/topology checks and pinned client
remain unchanged. No new MMIO address, firmware command, reset vector, interrupt
mask, security setting or installed image is introduced.

An original 44-byte CPU0 leaf at helper+0x240 performs both stores and returns a
fixed token. It uses caller-saved registers, no stack, arguments, memory reads or
system-register writes. DSB SY barriers precede, separate and follow the stores.
It contains no host transaction or observation between stores. This is not an
atomic pair: interrupts remain unchanged and no elapsed-time bound is claimed.
The leaf occupies a separate 64-byte line in the existing owned 16KiB allocation.
First/last instruction RX-read and identity-write translations must qualify;
the owned line is explicitly initialized, then code/padding read back, cleaned to
PoC, instruction-published and read back again. Allocation does not imply zeroed RAM.

All freshness checks, baseline observations and durable intents precede dispatch.
The tradeoff is explicit: unlike 31M, the controller cannot stop between the two
stores if CPU1 publishes a marker after the first. Both stores form the reviewed
local sequence; the first post-pair positive, partial record or error stops.
The old argument-taking single-store helper is never called by this controller.

## Completion and evidence

Before the single call, a durable pair intent and mutation intent are recorded.
Once dispatch starts, a missing/bad reply could mean zero, one or both stores
completed. It leaves acknowledged stores at zero, preserves that uncertainty and
issues no further target request or retry. The return token is checked inside the
dispatch operation, before the inherited diagnostic query. Only a matching token
and clean diagnostics confirm two stores. Diagnostic failure also retains uncertain
completion. A subsequent journal failure preserves confirmed completion and stops.
The inherited attempted-store counter then denotes two potential stores, not
independently observed execution. Completion never proves CPU1 instruction fetch.

Power and opaque-state reports contain only three actual phases: before_start,
after_second_start and final. A bounded adapter reuses frozen decoders, records
the omitted after_first_start phase, permits at most six reads per tracker and
freezes on errors/reentry. It does not fabricate a sample or fill missing data
with zero. Final sampling occurs only on the ordinary arrival timeout.

All inherited paired-observation stop semantics remain. A committed expected
CPU1 identity is prefix-execution evidence; zero records are inconclusive.
No callbacks, another core, Linux continuation, reconnection, cleanup or retry
is authorized. The 60-second child, 65-second supervisor, 3-second arrival,
2-second serial and 90-second human return bounds remain. In-flight requests can
reach their serial timeout; the arrival budget is not a per-instruction deadline.
Every outcome requires return to Macintosh HD.

## Review and validation limits

Independent review caught and corrected the uninitialized-allocation assumption.
The real-client VM test additionally caught parsed integer subclasses being
rejected as addresses; the corrected contract accepts integer subclasses while
rejecting booleans and non-integers without coercion or truncation.
Pure tests cover pair uncertainty, intent/journal failures, publication, tracker
phases, observer failures and positives. GNU assembly independently checks all
44 bytes. The real pinned client is exercised against a synthetic target only in
the existing isolated Linux VM, with a separate literal protocol allowlist.
Results and counts are in validation.json. These tests do not emulate Apple's
firmware, interconnect, caches or reset timing. Native 31N, CPU1 execution, Linux
SMP and macOS-equivalent scheduling/efficiency remain unverified.

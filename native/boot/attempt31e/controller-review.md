# 31E independent controller review

2026-10-21. Review of the original 31E controller and its frozen 31B/31C/31D
bases, against the clean public m1n1 client/source revision
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`. No target connection, native execution,
boot-setting change, proprietary pseudocode, or Apple artifact is involved in
this review. The full assembled-byte and pinned-image checks belong to the
separate validation record.

## Findings resolved before native use

1. **Telemetry API mismatch.** An intermediate controller called a nonexistent
   `Tracker.observe()`. The controller now calls `Tracker.sample(read64, base)`
   directly, retains its report, and refuses a sticky sampler error. Partial
   read counts and recognized phases therefore survive a transport failure.
2. **Global exception-guard window at CPU1 start.** The inherited `P_WRITE32`
   dispatch temporarily selects the global skip guard. A secondary fault could
   occur while that guard is active. 31E now issues the same two aligned
   32-bit startup writes through an original 16-byte helper that does not
   change the guard. This removes a diagnostic confound; it is not evidence
   that the guard caused any earlier attempt's failure.
3. **Arrival without successful instrumentation.** The controller now requires
   a completed, consistent early recorder after verifying CPU1 arrival and
   before dispatching any timer request. Arrival without that record remains
   separately visible in the failure result and is not promoted to complete
   experiment success.

## Startup helper

`kernel/experiments/smp31e-entry/start_helper.S` defines the original helper at
allocation offset 352. Manual instruction-field review confirms its four
words are a 32-bit store of `w1` at `x0`, a full-system data synchronization
barrier, a fixed return value `0x31e`, and return through the unchanged link
register. It changes no stack, link register, callee-saved register, NZCV,
exception guard, or event state. The caller supplies only the two fixed CPU1
startup addresses and the value 2. GNU/Clang assembly comparison remains a
separate required build check.

The helper's return means the store instruction and barrier completed, not
that CPU1 entered or that the hardware accepted a high-level startup protocol.
A fault or missing acknowledgment remains an unknown outcome. The controller
persists intent before dispatch and never repeats or rolls back that write.
Because this helper deliberately does not enable exception recovery, a target
fault may stop the proxy; the independent supervisor and human return timer
remain necessary.

## Sequential reads and request completion

The pinned `smp_secondary_entry` publishes reset identity, then spin identity,
then an initial flag, with intervening barriers. The controller reads the flag
before the identity words it validates, accepts both partial reset-publication
orders, and requires complete identity before arrival. These are sequential
observations, not an atomic snapshot or a program-counter trace.

The parked loop increments its flag **before** executing a requested callback.
Therefore a new flag alone cannot establish completion. The loop publishes the
return value and then clears its target, with a barrier between those stores.
31E retains the correct two-part completion predicate: the next flag and a
cleared target. Its row reader reads the target before the return value.

An independent small enumeration checked all **20** interleavings preserving
the producer's flag/result/target order and the consumer's flag/target/result
read order. None accepted completion with the old result. This is an ordering
model, not a physical coherency test. Each actual read uses the fixed helper
through the pinned proxy, whose dispatch epilogue includes DSB/ISB.

The recorder uses phase/data/phase sampling. A changing phase cannot establish
a complete record. Stable completion requires CPU1 identity and a supported
EL. The tracker rejects phase/identity regressions and changed exported state.
The controller requires completion before its eight timer requests, checks
strictly increasing timer values, and validates the final parked state.
Request round-trip durations include host transport and bookkeeping; they
must not be reported as core-start or scheduler latency.

## Publication and exception evidence

The controller verifies the exact existing image and fresh SMP state before
changing RAM. It queries the existing CPU0 translation regime and fixed
identity/write-alias spans. Successful address translation is insufficient on
its own: actual guarded writes, immediate exception checks, alias/identity
readback, and whole-text comparison must also succeed. It changes no mapping,
security policy, installed boot object, or reset-vector register.

The full recorder body is written and published before the single-word entry
branch. Every code write is before the first startup intent. The written alias
is cleaned to PoC and the identity instruction alias invalidated, with the
pinned proxy's dispatch barriers between requests. Any failed publication
stops before CPU1 start. Adjacent immutable text is included in the comparison.
The separate publication review describes remaining hardware assumptions.

After startup intent, fixed helper reads replace bulk `REQ_MEMREAD`, which
would otherwise clear the shared exception count and change the global guard.
The new startup writes also avoid the global guard. Exception count/guard
checks retain nonzero evidence rather than clearing it. The only following
writes are the bounded original helper's timer-request publication to CPU1's
known RAM slot. There is no allocation, code publication, permission query,
other-core start, Linux launch, reconnect, rollback, or retry after startup.

## Validation scope

The reviewer independently ran the current controller suite: **12 methods
PASS**, including all 80 modeled mutations under fault and transport-failure injection,
permission/publication refusals, partial entry, missing recorder, request
failure, and receipt preservation. Additional tests and final VM/compiler
results are recorded in `validation.md`; its final counts supersede this
intermediate review run.

This review found no remaining blocking software-ordering defect in the
reviewed controller. It does not establish physical code-write permission,
CPU1 reset state, cache visibility, successful entry, Linux SMP, performance,
or energy efficiency. Those remain native observations, collected once under
the published handoff after all offline intake and independent checks pass.

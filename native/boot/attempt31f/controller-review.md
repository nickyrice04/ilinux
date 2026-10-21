# 31F independent controller and supervisor review

2026-10-21. Reviewed the new controller against the separate telemetry
contract and the frozen 31B/31C/31D dependencies. No unresolved blocking
software issue found in the reviewed snapshot. This is an offline review,
not proof that the hardware follows the model or that native startup works.
No hardware, macOS settings or installed boot objects were accessed or changed.

| Reviewed file | SHA-256 |
|---|---|
| `native/boot/smp31f.py` | `ecea640ad36934ab211cbe82ae036286902d16d45b470c2dfe2bd9d499e161b0` |
| `tools/m1n1-client/attempt31f-supervisor.py` | `2c479d0f8eca2211a6ea722284ef96eadd3e1e188f2a6d744fef8f4dc29962c0` |
| `kernel/experiments/smp31f-entry/telemetry.py` | `237ac854b1c1752c76d9e0e9c81374681ecd2e910db6fe5cf9759cadb03d466a` |

## Controller checks

- The pinned image, exact runtime census, direct USB, existing mappings and
  helper gates precede code publication. The recorder body is published before
  its one-word hook. Readback covers both address views and the full immutable
  text with only the reviewed deltas applied.
- After the first acknowledged start store, the controller samples the
  recorder before considering the second store. Any observed entry phase,
  wrong identity, read error or changed spin state stops that sequence. The
  reviewed normal path has only the original two CPU1 stores; no additional
  core, cluster power, RVBAR, security or firmware operation exists.
- Once a start intent is recorded, RAM observations use fixed guard-free
  helpers. The diagnostic count/guard read neither clears those fields nor
  creates a new exception-guard window. A nonzero count or guard is retained
  as sanitized evidence and stops processing.
- `sample_recorder()` stores the complete sanitized tracker summary and
  checks `error` before returning. This is essential because `complete` can
  remain true as historical evidence after a later failure. No such latched
  failure can authorize another callback or the final success result.
- Normal arrival requires the established reset/spin identity and stack
  checks plus a complete stable phase-4 expected-CPU1 record. Partial phases,
  missing records and unexpected identities do not satisfy that condition.
  Eight conditional timer requests and the final park checks remain bounded;
  this is not a Linux handoff or performance measurement.

The unfiltered vector entry can also be a synchronous-exception path. A
phase-1 marker therefore proves observed entry/store progress only. CPU1
arrival and reset provenance cannot be inferred from that marker. See
[startup-review.md](startup-review.md) and the exact-image entry review.

## Review adjustments

The entry reviewer identified that a stable unsupported-EL phase originally
remained open until the arrival timeout. The telemetry now records
`unsupported_recorder_el` and closes immediately. Its regression test proves
that a subsequent caller-directed sample performs no more reads.

The controller now observes early publication between the two start stores.
This covers a marker or an unexpected CPU record that appears before the
ordinary reset/spin flag. Such evidence is retained without issuing the
second start store.

## Independent validation

Host executions used the project's original standard-library models only:

| Suite/check | Result |
|---|---|
| `python3 -I kernel/experiments/smp31f-entry/test_telemetry.py` | 29 methods PASS |
| Supported ordered store/read interleavings | 2,376 PASS |
| Unsupported-EL ordered store/read interleavings | 462 PASS, never completion |
| `python3 -I native/boot/test_smp31f.py` | 19 methods PASS |
| `python3 -I tools/m1n1-client/test_attempt31f_supervisor.py` | 15 methods PASS |
| Separate reviewer boundary fixtures | Four PASS, described below |

The separate fixtures injected (1) only a phase-1 marker after the first
start, (2) a known Super-class identity after the first start, (3) an identity
change after an earlier complete record and the first timer callback, and
(4) a nonzero exception guard during a recorder read. The first two and
fourth cases issued only one startup store and no callback. The third case
retained historical completion but stopped after one callback, with an error
and no park/success result. The guard case retained the nonzero-guard flag
and made no further recorder read. These were synthetic fixtures, not claims
about observed target behavior.

The supervisor has an independent 65-second child deadline, bounded process
termination, exclusive durable receipts and no device interface or retry
path. It rechecks source pins before spawning the fixed command, starts an
owned process group and records deadline/termination uncertainty distinctly
from success. The 15 supervisor tests include actual original dummy children
that exit, stall or ignore SIGTERM; no target controller was started by these
tests. The independent human 90-second return bound remains necessary.

VM assembly, pinned-client integration and full source-closure checks are
separate validation responsibilities. This review does not replace those
gates or M1 intake, and does not demonstrate secondary-core instruction
visibility, physical reset routing, native SMP or performance parity.

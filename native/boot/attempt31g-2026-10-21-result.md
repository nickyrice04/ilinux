# Attempt 31G — CPU1 PS state changes; entry remains unobserved

**Observed, 2026-10-21 Eastern:** one authorized supervised 31G run returned
**STOP / `cpu1_arrival` / `cpu1_arrival_timeout`**, controller/supervisor exits
**1 / 1**, no supervisor deadline. All **8 fixed 32-bit PS reads completed**,
with no read or terminal-observation error. CPU1's decoded **actual** field
was **0 before/after the first start store**, then **15 after the second store
and in the final sample**. CPU0's actual field stayed **15**. Desired fields
stayed **0** for both CPUs throughout.

Both startup stores were attempted and acknowledged. CPU0 permission and
recorder publication checks passed, but **95 complete recorder samples / 475
reads stayed at phase 0**, identity not committed; **95 reset/spin samples**
retained **`no_reset_record_seen`**. CPU1 arrival, callback progress and final
park remain unverified. No CPU1 timer callback or Linux boot ran.

Controller elapsed **5.188 s**, supervisor **5.583 s**. Human confirmed usual
Macintosh HD return at **+56.513 s**, within the independent 90 s bound.
**31G is consumed; no retry, reconnect, rollback or further target command.**

This is a decoded power-domain state transition at the bounded sample phases,
**not proof of CPU1 instructions, reset release or effective reset destination**.
No raw PS word is published. Linux/native Linux SMP, renderer performance,
timer callbacks, final park and energy tests remain **NOT RUN/unverified**.

Exact schema-reviewed final outputs:
[controller](attempt31g-controller-2026-10-21.json),
[supervisor](attempt31g-supervisor-2026-10-21.json).
Raw receipts, stderr, ADT, target memory/addresses and identifiers remain
private under ignored build. M5 owns the next evidence interpretation.

## Provenance and completed offline gate

M5 handoff **`449eb6ea7959d4dc28e4c923fd6954580d4987cc`**;
published readiness/execution **`768c54756631637e3f01aff8c0a9e3cc4ce56194`**.
[Independent M1 intake](attempt31g-m1-offline-2026-10-21.md): **166 pins** and
**232 Python methods PASS**, no skips/fixes; both documented commands exit 0,
zero hardware operations before start. Symbol mode **`reviewed_layout_only`**;
full-symbol checks **NOT RUN on M1**. M5's separate 255-method VM/full-symbol,
real-parser/client, independent assembly and width harness remain offline
evidence, not physical reset emulation or independently rerun M1 checks.

Source-manifest SHA-256:
`a06d3c201818a046b7964147a171d1d6c50e5b4d78a47dbdcd40584b321a4532`.
Existing 3,932,160-byte boot021 image:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Clean client remains **`57a9339ffd1876e78297b17d34dece8cff8fa1ba`**.
Additional retained-package verification passed all **13 files**. The retained
168-byte recorder and permission/start helpers remained unchanged; the new
16-byte read helper matches the reviewed digest
`c2316a02024b7ce2dfed2d4640c5c57abdce4bab81c9c4380a2d8cb3bbcb4dcd`.

All five real 31G live-use files were absent before/after offline intake.
No old evidence was deleted, edited or reset. Prior 31B/31C/31D/31E/31F live
evidence digests remain unchanged. No image transfer, install, VM or routine
M1 restart was needed. Source/guards were not changed to pass native checks.

## Live binding and power observations

After readiness publication, the human explicitly confirmed starting 31G,
a fresh M5 lab proxy session, powered Macs, direct cable, healthy awake/
unlocked/open-lid M1 and independent 90 s timer. These preparation facts are
human-reported. Timer cue immediately preceded the one fixed supervisor with
`--confirm START-CPU1-J716C-31G`. Command start:
**2026-10-22 00:29:34.544 UTC / 2026-10-21 8:29:34 PM Eastern**.

Live ADT binding passed for the two CPU0/CPU1 PS domains, fixed width **32 bits**,
with **CPU1 startup mapping unchanged** and all **18 topology routes validated**.
Both additional PS translation probes passed. These are mapping/table checks,
not an execution or peripheral-access guarantee. The subsequent eight actual
PS reads all completed successfully.

| Sequential sample phase | CPU0 desired | CPU0 actual | CPU1 desired | CPU1 actual |
|---|---:|---:|---:|---:|
| before_start | 0 | 15 | 0 | 0 |
| after_first_start | 0 | 15 | 0 | 0 |
| after_second_start | 0 | 15 | 0 | 15 |
| final (natural arrival expiry) | 0 | 15 | 0 | 15 |

For **both CPUs in all four samples**, decoded `parent_missing`,
`device_disabled` and `auto_enabled` were **false**. Read attempts/completions:
**8 / 8**; sample completeness **4 / 4**; tracker error **null**;
`terminal_observation_error` **null**. No reserved/unknown bits or raw MMIO
words were retained in the public result. Pairs are sequential CPU0-then-CPU1
reads, not simultaneous samples, and individual read timestamps were not
recorded. No wake-latency or performance measurement follows from this table.

The code uses the source-supported legacy PS field layout. Actual **15** is
the legacy active encoding; it does not establish t6050 reset release or CPU
execution. Desired **0** is preserved as observed rather than normalized to
15 or interpreted as a control request. The saved report explicitly keeps
`entry_execution`, `reset_release` and `effective_reset_destination` as
**NOT_ESTABLISHED**. No PS control write was made.

## Recorder/start evidence and boundaries

| Evidence | Recorded value |
|---|---|
| Result / phase / reason | STOP / cpu1_arrival / cpu1_arrival_timeout |
| RAM predicates / BootArgs revision | 11 true / 3 |
| Direct USB / expected UART bases / initially enabled count | true / true / 2 |
| UART RAM zeroes published | true |
| CPU0 regime / code probes / PS probes | EL2/VHE / 16 PASS / 2 PASS |
| Recorder body / vector hook / whole text | verified / verified / verified |
| Explicit mutation intents | 66 |
| CPU1 startup stores attempted / acknowledged | 2 / 2 |
| CPU1 arrival verified | false |
| Recorder samples / reads, all completed | 95 / 475 |
| Highest phase / identity status / record complete | 0 / not_committed / false |
| Recorder error / closed | null / false |
| Reset/spin classification / sample count | no_reset_record_seen / 95 |
| Timer requests planned / completed | 8 / 0 |
| Round-trip samples / counter progress / final park | empty / false / false |
| Linux boot / native Linux SMP | NOT RUN / NOT RUN |

**Inferred from exact flow and recorded gates:** inherited fresh-state/helper/
CPU1/UART setup, recorder permission/publication and new read-helper checks
completed before startup. The 66 mutation intents equal the retained 63-intent
fully published/two-start path plus three read-helper upload/cache intents.
AT queries and PS reads are distinct from this mutation counter. Acknowledged
start stores are not proof of higher-level CPU startup success.

The baseline used guarded 32-bit reads before any CPU1 start intent. Later
power reads used the fixed guard-free 32-bit helper, preserving diagnostic
exception evidence. The first-start PS pair preceded the recorder/reset
sample that permitted the second store. Recorder/reset counts include one
between-start observation and 94 arrival-window observations. No progress or
error was observed before the second store; no callback phase was reached.

The primary reason is **natural `cpu1_arrival_timeout`**, which authorizes
the documented final PS pair inside the controller. It was not the distinct
in-flight `cpu1_arrival_observation_deadline`; no terminal read error occurred.
After the final STOP result, no additional target command ran. The receipt
reported no nonzero exception-count/guard flag; this does not exclude an
unobservable early fault or establish an absence of every exception.

Permission booleans include expected identity-code write **denials**. Existing
writable-alias/code readback passed without remapping or changing protection
policy. `no_recorder_publication_seen` refers to **CPU1 telemetry**, not the
successful CPU0 code publication. Incoming EL/cache flags and observed CPU
identity remain **unknown/null**, not disabled or inferred from the PS value.
The vector also serves an exception slot; neither missing marker nor any
future marker is independently a reset-provenance or current-PC trace.

Topology metadata preserves the reviewed **12 Performance (ADT M) +6 Super
(ADT P)** mapping and CPU1's same-cluster target. The later-cluster legacy
mask mismatch list contains CPUs6–17; it is structural validation, not a
later-core hardware operation. Linux capacity calibration/all-core operation
remain uncalibrated/NOT RUN. No extra core or changed CPU1 mask was tested.

The private consumed receipt has **109 records**. Only schema-reviewed final
JSON is published. Total durations include USB, Python, host and journaling
overhead. Empty callback timings provide no CPU latency/performance estimate.

## Return and M5 handoff

Immediately on the supervisor result, the human was instructed to power off
and select Macintosh HD. Controller/supervisor completed and transport closed;
no target cleanup, rollback, code restore, reconnect or retry followed. Human
return confirmed **2026-10-22 00:30:31.056 UTC / 2026-10-21 8:30:31 PM Eastern**,
**+56.513 s** from command start, including confirmation/UI overhead. No return
problem reported. Only the owned bounded caffeine assertion was stopped afterward.

Session loaded-RAM code/helper changes remained until power-off. Installed
boot021/client/macOS, firmware, mappings/protection policy and boot/security/
default/volume settings stayed unchanged. Routine policy/default rechecks
remained waived; original Full/lab Permissive/Macintosh HD default remain
last reported, not freshly verified.

**M5 next: interpret the observed PS actual transition together with absent
entry telemetry/reset progress and select a separately reviewed next change.**
The entry/effective-reset/visibility uncertainty remains; do not infer CPU
execution from active status or add speculative power/protection operations.
Preserve all consumed receipts. No unchanged retry, timeout extension, extra
core or Linux continuation. Current coordination and this result supersede
frozen pre-execution controller NOT RUN wording.

# Attempt 31D — UART RAM isolation completes; no CPU1 reset record observed

**Observed, 2026-10-21:** one authorized supervised 31D run returned
**STOP / `cpu1_arrival` / `cpu1_arrival_timeout`**, controller exit **1**.
Both diagnostic UARTs were enabled at intake; their two RAM bases were zeroed,
cache-published and read back successfully. Direct USB stayed selected. Both
CPU1 start writes were attempted and acknowledged. **171 sequential samples**
retained the classification **`no_reset_record_seen`**; arrival was unverified.
No timer request or Linux boot ran. Controller elapsed **4.485 s**, supervisor
**4.866 s**, supervisor deadline **false**. Human confirmed usual Macintosh HD
return at **+44.628 s** from command start, within the independent 90 s bound.

**31D is consumed.** No retry, reconnect, UART flush, longer arrival window,
power-register operation, extra core, target rollback or Linux continuation.
CPU1 entry remains **unverified**. No reset record is not proof of no executed
instructions; the last sampled RAM stage is neither an atomic snapshot nor a
CPU program counter. **Linux/native Linux SMP, timer-request completions,
renderer performance and energy tests NOT RUN.**

Exact schema-reviewed final outputs:
[controller](attempt31d-controller-2026-10-21.json),
[supervisor](attempt31d-supervisor-2026-10-21.json).
The raw receipt, stderr, target memory and identifiers remain private under
ignored build. No recording or other raw artifact is published.

## Provenance and offline gate

M5 handoff **`c3317967eb7fc0dbd3428905d807d34eac551b74`**;
published M1 readiness/execution **`04ffeeec4da8261caad4eb0b6b26f6ccc6ad25ea`**.
The [independent readiness](attempt31d-m1-offline-2026-10-21.md) verified
**60 source pins**, boot042's **13 retained package files**, existing boot021
image/helper and clean client pin. **73 Python methods PASS**, all 11 requested
processes exit 0, zero skips/failures/fixes. The additional original offline
console image/source audit passed and exactly matched the Git JSON binding.

Source-manifest SHA-256:
`e41c9a29748007b08e06e077e45d63deb494eb0b3ec75e0142dc4aeb9f4e3ba5`.
Controller:
`1a37cd8e4e86dfd962240674a1714a4be0c2ac387efeead7efe459d5281ccc1c`.
Supervisor:
`ed2d4b2d0d794959fd75b6ed8e98285988917b916629038968177b2365b1e715`.
Existing 3,932,160-byte boot021 image:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Clean client remains `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
All shared controller sources, the helper and installed image stayed unchanged.
M5's VM/client/parser/UART-harness and REA evidence remain separate static or
offline evidence, not native entry proof. Rejected pseudocode was not used.

All five 31D live-use files were absent before/after offline checks. The actual
run created a separate receipt namespace; no old receipt was deleted or reset.
Prior 31B/31C live evidence digests remain unchanged. No new image, download,
host install or VM was needed. A bounded caffeine assertion covered this run.

## Live evidence

After readiness publication, the human explicitly confirmed starting 31D,
a fresh M1 restart, direct cable reseat, both Macs powered, M1 unlocked/lid
open, M5 Running proxy and the 90 s timer ready. Preparation facts are
human-reported. The timer cue immediately preceded the one documented
supervisor with `--confirm START-CPU1-J716C-31D`.
Local command start: **21:09:17.484 UTC / 5:09:17 PM Eastern**.

| Field | Recorded value |
|---|---|
| Result / phase / reason | STOP / cpu1_arrival / cpu1_arrival_timeout |
| RAM predicates / BootArgs revision | 11 true / 3 |
| Direct USB / expected-or-zero UART bases | true / true |
| Initially enabled diagnostic UARTs | 2 |
| UART RAM zeroes published | true |
| Explicit mutation requests | 13 |
| CPU1 start writes attempted / acknowledged | 2 / 2 |
| Entry observation / sequential sample count | no_reset_record_seen / 171 |
| CPU1 arrival verified | false |
| Timer requests completed / counter progress verified | 0 / false |
| Linux boot / native Linux SMP | NOT RUN / NOT RUN |
| Controller elapsed | 4.485 s |
| Supervisor exit / deadline / elapsed | 1 / false / 4.866 s |

**Inferred from exact control flow and saved phase/predicates:** inherited
RAM/image/text/features/fresh-state checks passed, then helper allocation,
upload/readback/cache maintenance and CPU1 RAM setup completed. Four new
mutation intents zeroed and cache-published the UART RAM bases before start;
the two existing start writes followed. Thirteen intents comprise seven
inherited setup mutations, four console-isolation mutations and two starts.
The controller's three-second arrival window expired; no timer-request phase
was reached. Final parked state and CPU1 arrival identity are not established.

`no_reset_record_seen` classifies the sampled existing reset-table record;
the observer uses the unchanged guard-free helper and sequential RAM reads.
It retains the last successfully sampled stage, not a post-timeout snapshot.
Muting UART outputs also removes fallback early-fault diagnostics for this
session. Acknowledged writes and CPU0 USB responsiveness do not establish
CPU1's reset state, first instruction or cache visibility. No cause is proven.

The private consumed receipt has **25 records**; only reviewed final schemas
are published. Controller/supervisor durations include proxy/software overhead
and are not core-start latency benchmarks. The console change did not produce
verified arrival in this run; this does not diagnose all early entry failures.

## Return and next M5 review

Immediately on the supervisor result, the human was instructed to power off
and select Macintosh HD. No further target command or cleanup occurred. The
controller closed its transport; only the owned caffeine assertion was stopped
after human return confirmation. Return was recorded **21:10:02.113 UTC /
5:10:02 PM Eastern**, **+44.628 s** from command start, including UI/confirmation
overhead. This is not an OS boot-time measurement.

Existing boot021/client pin, macOS, firmware, boot/security/default/volume
settings are unchanged. Routine policy/default rechecks remained waived;
original Full/lab Permissive/Macintosh HD default remain last reported, not
freshly verified. No Linux, renderer, frequency or new hardware-power test.

**M5 next: review the no-reset-record evidence and prepare separately reviewed
earlier-entry instrumentation, as the 31D decision specifies.** Preserve all
once/consumed receipts. Do not replay an unchanged test, extend the timeout,
add speculative power/RVBAR operations or continue to Linux. CPU1 entry evidence
still precedes two-core Linux timer/IPI/coherence and renderer integration.
Frozen source-pinned checklists/readiness text remain for provenance; current
coordination and this result supersede their pre-execution controller NOT RUN.

# Attempt 31N — local startup pair completes; no CPU1 identity observed

**Observed, 2026-10-22 Eastern:** one authorized native31N session consumed.
Final **STOP / cpu1_arrival / cpu1_arrival_timeout**, exits **1/1**, no supervisor
deadline. The single local pair returned the expected token and clean diagnostics,
confirming completion of the two stores. No cached, maintained or Device channel
committed CPU1 identity. **CPU1 execution remains unverified; Linux boot/native
Linux SMP NOT RUN.** There was no retry or callback.

Human confirmed the usual Macintosh HD desktop at **+41.286s**, within the90s
window. Controller **6.013s**, supervisor **6.685s**. These durations include
transport, observation and journaling; no hardware inter-store timing was measured.
Reviewed sanitized [controller](attempt31n-controller-2026-10-22.json) and
[supervisor](attempt31n-supervisor-2026-10-22.json) final JSON accompany this note.
Raw journals, stderr and local bookkeeping remain ignored/private.

## Inputs and independent intake

Release `adc9542566e595354216b474532ea9ddbf5fa6f3`;
published readiness/execution `a4b7840cdb46989847f8dda908729d855c258022`.
[M1 intake](attempt31n-m1-offline-2026-10-22.md): **330 pins / 932 image-only
methods PASS**, no skips/repairs; both documented commands and retained13-file
package check exit0. Python3.13.5, reviewed_layout_only; **M1 full-symbol checks
NOT RUN**, exact symbols not supplied. M5's955 full-symbol VM methods,51 actual-
client synthetic scenarios, GNU assembly comparison and REA work remain separate
offline evidence and were not rerun on M1.

| Input | SHA-256 |
|---|---|
| 330-file source manifest | `00dea9b06831a0e3d57fff4d2f92103ea469c887779ae5bce661bf0e0523e70a` |
| Retained3,932,160-byte boot021 image | `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664` |
| Original44-byte start-pair leaf | `8c591d55d1d92a6b466a33a9cc5af69f869504df066728862119c5f39037bf19` |
| Retained13-file package manifest | `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd` |

Client remains clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
Frozen M306/L281/K254/J226/I202/H186/host6 and all prior receipts/offline evidence
remain unchanged. No source repair, image transfer, install or old-receipt reset.

After readiness publication the human confirmed **“Start 31N; all confirmed”**:
fresh Running proxy, powered Macs, direct known-good cable, healthy awake/
unlocked/open-lid M1 and independent90s timer. These conditions are human-reported.
Timer cue immediately preceded the one supervisor invocation; wrapper start
**2026-10-22 20:13:20.084 UTC /4:13:20 PM Eastern**. One owned bounded120s
caffeine assertion was requested; no sleep setting changed. No preliminary
handshake, old checker or reconnect was performed.

## Connection and consumption

| Evidence | Recorded value |
|---|---|
| Cached registry queries attempted/returned | 1/1 |
| Classification/output/stderr | primary_verified/xml_plist/absent |
| Modem interfaces/primary candidates | 2/1 |
| Query start offset/elapsed | 0.000180s/0.020329s |
| Total discovery elapsed | 0.020915s |
| Discovery ready/native_ready | true/false |
| Source recheck | passed |
| Import, serial, UART, proxy, construction attempted/returned | all true/true |
| Native reservation attempted/child consumed | true/true |
| Last connection phase | controller_run |
| Transport close attempted/closed | true/true |
| Connection/native journal failure | false/false |

Cached-phase device_opens0/target_requests0 are not totals after serial open and
the native campaign. The pure reset validator's hardware_operations0 is local
validation scope. Parent invocation reservation alone is not native consumption;
the exclusive native journal and child consumed flag establish this session.

Connection journal **19 complete JSON rows**, native journal **1,633 complete
JSON rows**; their final rows equal the controller final JSON. Stderr contains
only the expected client-pin verification line. No finalization/interruption error
field was emitted. Supervisor reason controller_exited, deadline=false. All six
exclusive live-use files remain intact and block reuse.

## Pair publication and actual completion

All four pair permission predicates passed: first/last RX-read and identity-write
translations. The owned64-byte span was explicitly initialized; exact44-byte
leaf and20-byte padding verified, cleaned to PoC, instruction-published and read
back. All publication flags true, bytes44. Allocation ownership was not treated
as proof of zero-filled RAM. The code occupies its separate helper line; no
installed boot image or reset destination was changed.

| Pair evidence | Recorded value |
|---|---|
| Result | START_PAIR_COMPLETION_CONFIRMED |
| Durable intent/dispatch attempted | true/true |
| Reply received/return token matched | true/true |
| Diagnostics verified | true |
| Stores acknowledged/possible completed stores | 2/[2] |
| Individually observed store attempts | NOT OBSERVED |
| Inherited attempted-counter meaning | pair_contains_two_potential_stores |
| Atomic/timing measured/retry authorized | false/false/false |
| Completion proves CPU1 execution | false |

This was one no-argument CPU0 call, issuing the same two aligned32-bit writes of2
at the same existing addresses/order. DSB SY precedes, separates and follows the
stores. No host observer, journal or RPC occurs between them; interrupts remain
unchanged. There was deliberately no between-store abort opportunity. No maximum
hardware interval is established. The return token was checked before the normal
diagnostic query; both succeeded, so completion is confirmed rather than uncertain.
Two attempted stores in the inherited counter describe the pair, not two separate
host calls or independently traced instruction execution. This does not prove
CPU1 fetched an instruction.

## Inherited gates and CPU0 controls

RAM/BootArgs predicates passed, revision3. Direct USB/expected UART checks pass,
two initially enabled diagnostics and RAM zero publication recorded. CPU0 EL2/
regime and inherited code/Device/control/cold/power/state probes passed, along
with all20 Normal and13 cache permission predicates. Expected permission checks
include write denials; no mapping was changed. Live feature GOT/dispatch bindings,
CTR leaf, full clean vector/cold/control granules, inherited body/hook/whole-text
and Normal-prefix/full-text checks passed. Freshness/stack/target checks preceded
the single pair. Normal/cold entry armed; cache_records_frozen=true,
cpu0_post_start_record_stores=0.

CPU0 cache qualification: **DMinLine64/CWG64**, issuing CPU0/EL2,
VHE_host_stage2_disabled,64-byte records in128-byte owned spans. CIVAC is CPU0-
issued and may affect shareable caches beyond CPU0. CPU1 cache state UNKNOWN;
qualification itself does not establish native success.

| Control | Reads attempted/completed | Stores attempted/acknowledged | Maintenance attempted/acknowledged | Result |
|---|---:|---:|---:|---|
| Device | 24/24 | 2/2 | not part of this control | CPU0_OBSERVER_CONTROL_PASS |
| Normal | 24/24 | 2/2 | not part of this control | CPU0_NORMAL_CONTROL_PASS |
| Separate maintenance | 48/48 | 2/2 | 2/2 | CPU0_CACHE_CONTROL_PASS |

All markers observed, canaries preserved and original scratch restored on the
successful pre-start paths. Device journal_failed=false, Normal/cache error=null.
Device control elapsed0.012586s; other controls emit no elapsed field. Successful
controls establish CPU0 behavior, not CPU1 visibility; no fault cleanup followed.

Topology validated18 cores:12 Performance (ADT M),6 Super (ADT P); CPU1 alone in
CPU0's active Performance cluster, startup mapping unchanged. Reset observation:
2 reads/returns/immediate guards/validated rows, equal mirrors, error=null,
RESET_ADDRESS_READBACK_PASS. Both address fields classify as image_base, bit0
lock classifier true, bit11 false, low10:1 and47:42 zero, upper63:48 present/
uninterpreted. Exact entry/effective reset route UNKNOWN; no reset redirect.

## Three actual power/state phases

| Actual phase | CPU0 PS desired/actual | CPU1 PS desired/actual | CPU0 opaque byte | CPU1 opaque byte |
|---|---|---|---:|---:|
| before_start | 0/15 | 0/0 | 2 | 0 |
| after_second_start | 0/15 | 0/15 | 2 | 2 |
| final | 0/15 | 0/15 | 2 | 2 |

**after_first_start was not sampled.** Both trackers explicitly report that
omission with reason consecutive_start_pair; no row or zero value substitutes for
it. Three complete pairs, **6/6 reads each**, maximum_reads6,
phase_adapter_failed=false. PS/state errors null, state journal_failed=false,
terminal_observation_error=null. PS parent_missing/device_disabled/auto_enabled
all false. CPU0 later change flags false/false; CPU1 true/true, equality false/
true/true. Sequential PS/state samples are not simultaneous observations.

Power actual15/opaque byte2 do not establish t6050 running/reset/PC semantics.
Entry/reset/running NOT_ESTABLISHED, PC NOT_OBSERVED, register meanings UNKNOWN.
The final pair was acquired by the natural-timeout path before the outcome;
there was no extra target sampling after the supervisor result.

## Cached, maintained and Device entry channels

| Channel | Samples attempted/completed | Reads attempted/completed | Maintenance intents/attempted/acknowledged | Highest phase/identity |
|---|---:|---:|---:|---|
| Paired Normal vector | 126/126 | 756/756 | 126/126/126 | 0/not_committed |
| Paired Normal cold | 126/126 | 756/756 | 126/126/126 | 0/not_committed |
| Device vector | 64/64 | 320/320 | not applicable | 0/not_committed |
| Device cold | 128/128 | 512/512 | not applicable | 0/not_committed |

Each final cached and maintained snapshot has3 reads, complete=true, phase0,
any_record_seen=false and identity not_committed. Both paired aggregates have
error=null, journal_failed=false, observation_channel=null, any_record_seen=false,
CPU1 execution UNVERIFIED, visibility cause UNKNOWN and
negative_excludes_execution=false. **254 total maintenance intents/attempts/
acknowledgments = 2 control +252 paired**. No missing maintained sample or
maintenance fault is reported.

The inherited normal_observation contains only pre-start freshness observations:
2 samples/6 reads per channel. Total normal_reads **1,524 = 12 pre-start +1,512
paired**. Post-start data is in paired_observation; its final snapshots are not
all historical snapshots. Cumulative counters/highest phases and private journals
retain progress. The separate inherited arrival_samples counter is **63**;
Device recorder samples_completed is **64**. These distinct counters are
preserved exactly, not conflated or adjusted.

Device vector state no_recorder_publication_seen, identity flags false, record
incomplete, closed=false, EL/MMU/cache/identity fields null. Cold state
no_cold_publication_seen, any_record_seen/stop_required/complete/record_complete/
park_verified false, exception level/identity fields null, errors null. Inherited
entry classification no_reset_record_seen. These are phase/identity observations,
not a claim that every raw record word was sampled or neither path executed.

No committed expected identity or prefix execution was observed. Negative records
still cannot exclude an earlier fault, alternative route, private CPU1 data or
execution outside the observation contract. A maintained positive would not alone
prove cache causality either; CPU1 could arrive between snapshots. CPU0 controls,
confirmed pair completion and power transitions do not remove this uncertainty.

## Stop, return and handoff

**412 mutation intentions**, including RAM publication, controls, cache operations
and the one pair; not412 power writes. Pair contains two potential stores and
acknowledges both on confirmed completion. Callbacks planned/completed **0/0**,
empty round-trip list, counter_progress=false, park=false. Natural
cpu1_arrival_timeout ended the run, distinct from qualification/control refusal,
uncertain pair, transport failure, in-flight observation deadline or outer wall
deadline. Existing60s/65s/2s/3s/local-control bounds remained; operation-bracketed
budgets are not hard per-RPC interrupts. No window extension or retry.

Immediately on the outcome, before detailed inspection, the human was told to
power off and choose Macintosh HD. Usual desktop return confirmed
**2026-10-22 20:14:01.371 UTC /4:14:01 PM Eastern**, **+41.286s**, within90s.
This is the recorded confirmation interval, not exact shutdown/boot duration.
No return problem reported. Both owned bounded caffeine processes were absent
at return bookkeeping; no process was signaled then.

No M1 restart, image transfer, reinstall, new MMIO/reset address, firmware replay,
extra core, post-outcome target command, cleanup RPC, reconnect, retry or Linux
launch. Installed boot021, retained boot042, pinned client and macOS/volume/
security/default settings unchanged. Routine policy checks remain waived:
original Full/lab Permissive/Macintosh HD default remain last reported, not
freshly verified. Preserve all consumed receipts and prior evidence. Frozen
pre-execution NOT RUN wording is historical for this consumed31N session.

M5 owns the next interpretation. This result closes this bounded local-pair
variant without establishing CPU1 first-fetch failure or qualifying another boot.
**CPU1 execution/effective entry unverified; Linux boot/native SMP NOT RUN.
No all-core, speed, efficiency or macOS-parity claim follows.**

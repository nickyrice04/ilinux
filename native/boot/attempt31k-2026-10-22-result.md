# Attempt31K — CPU0 control passes; neither entry channel commits identity

**Observed,2026-10-22 Eastern:** one authorized31K native attempt returned
**STOP / cpu1_arrival / cpu1_arrival_observation_deadline**, exits **1/1**, no
supervisor deadline. **Native attempt consumed=true;95 mutation intentions;
both CPU1 starts attempted/acknowledged.** Connection/reset/probes/publication
passed. The returning CPU0 recording control passed and restored its own scratch.

Cold channel: **183 complete samples/732 reads,phase0,no committed identity**.
Vector channel: **91 complete samples/455 reads,phase0,no committed identity**.
Errors null. Three paired PS/core-state observations completed (**6 reads each**):
CPU1 actual0→15 and opaque byte0→2 after the second start; CPU0 unchanged15/2.
**No final pair** was taken after the in-flight observation deadline.

Controller **5.439s**, supervisor **6.035s**. Human confirmed usual Macintosh
HD at **+64.898s**, within90s. No retry/reconnect/further target command.
CPU1 arrival/callback progress/park remain unverified; **Linux boot/native Linux
SMP NOT RUN**. Positive CPU0 control is not CPU1 fetch/store visibility proof.
Negative entry markers do not establish that CPU1 reached neither path.

Exact reviewed sanitized final outputs:
[controller](attempt31k-controller-2026-10-22.json),
[supervisor](attempt31k-supervisor-2026-10-22.json).
Private journals/stderr,registry data,full register words,USB paths and identifiers
remain under ignored build. No raw artifacts are published.

## Provenance and offline gates

Handoff `7043b1732e58686f8550e942d35a6c4d8d2fe3ba`;
published readiness/execution `db9a79d5a8a294b84cf0df6f79a0f74c640bd032`.
[Independent M1 readiness](attempt31k-m1-offline-2026-10-22.md): **254 pins/716
image-only methods PASS**,no skips/repairs,both documented commands and retained
13-file package check exit0. Symbol mode reviewed_layout_only; **full-symbol
checks NOT RUN on M1**. Separate M5 VM/full-symbol,105 wire scenarios,assembly
comparisons and REA work were not rerun on M1 and remain offline evidence.

31K manifest SHA-256:
`cfb3a24b9f4447b6267938063ed09ee809218a90a8e7e2e235eca62d69c1668c`.
Existing3,932,160-byte boot021 image:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Clean client stays `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
All254 pins,frozen J226/I202/host6 inputs and prior31B–31J plus separate host-only
31J evidence remain unchanged. No source fix,image transfer,install or old receipt
reset. The candidate instrumentation changed only the live session's owned RAM.

After readiness publication,human authorized **“Start 31K; all confirmed”**:
fresh Running proxy,direct known-good cable seated,powered Macs,healthy awake/
unlocked/open-lid M1 and independent90s timer. Preparation is human-reported.
Timer cue immediately preceded the single supervisor. Wrapper start
**2026-10-22 04:11:21.284 UTC /2026-10-22 12:11:21 AM Eastern**.
No preliminary checker/handshake. A separate owned120s caffeine assertion was
started for the live command; no sleep setting changed.

## Connection and native consumption

| Evidence | Recorded value |
|---|---|
| Cached query attempts / returns | 1 /1 |
| Category / parsed output / stderr | primary_verified /xml_plist /absent |
| Inventory / primary verified | true /true |
| Modem interfaces / primary candidates | 2 /1 |
| Query start offset / elapsed | 0.000172s /0.021676s |
| Total discovery elapsed | 0.022178s |
| Discovery ready / native_ready | true /false |
| Source/pin recheck | passed |
| Import,serial,UART,proxy,construction attempted / returned | all true /true |
| Native reservation attempted / child consumed | true /true |
| Last connection phase | controller_run |
| Transport close attempted / closed | true /true |
| Connection/native journal failure flags | false /false |

Discovery's device_opens0/target_requests0 are **cached-phase-only** counts,
not totals after the successful serial open and target campaign. Pure reset
validation hardware_operations0 likewise describes local validation only.
Parent invocation reservation consumed=false is its static local scope; child
native_attempt_consumed=true and exclusive consumed journal establish native
consumption. No enumeration repeat or reconnect; one serial attempt returned.
No finalization/outer-deadline/interruption error field was emitted.

Private connection journal **19 complete rows**,native journal **199 complete
rows**. Stderr contains only the expected pinned-client verification line.
No raw rows are published; both receipts block reentry.

## CPU0 positive control

| Evidence | Recorded value |
|---|---|
| Result / phase | CPU0_OBSERVER_CONTROL_PASS /complete |
| Scope | cpu0_shared_device_ram_observer |
| Read intents / attempted / completed | 24 /24 /24 |
| Store intents / attempted / acknowledged | 2 /2 /2 |
| Marker observed / canaries preserved / original restored | true /true /true |
| Journal failure / elapsed | false /0.014136s |
| CPU1 execution / record visibility | NOT_TESTED /NOT_TESTED |
| Control translation probes | all5 PASS |

The returning leaf wrote the fixed marker in its separate64-byte Device scratch,
all eight words were checked,then the known zero marker was restored and all
words rechecked. Seven canaries were preserved. Restoration is the successful
normal control sequence, not cleanup after a fault. No additional restoration
or target operation followed the final STOP.

**Confirmed:** the CPU0 control path performed its expected store/read/restore
sequence in this session. It does not establish CPU1's incoming translations,
instruction fetch,record visibility or execution. Its scratch is separate from
the cold and vector records. Timing includes USB/Python/journaling,not CPU speed.

## Publication and readback checks

RAM all11 predicates true,BootArgs revision3. Direct USB/expected UART bases
true,initially2 enabled diagnostics,RAM zeroes published. Live ADT binds the
fixed32-bit PS locations and all18 topology routes; CPU1 startup mapping unchanged.
CPU0 EL2/regime verified;16 vector-code probes,2 PS,2 opaque-state,5 control
and16 cold probes PASS. Identity-code write booleans denote expected write
**denials**,not changed permissions or a new mapping.

Both vector and cold **body/hook/whole-text readback PASS**. Cold body publication
preceded its hook and required CPU0 control PASS; `cold_entry_armed:true`.
Live cold/vector freshness checks passed. Exact full-text comparison permitted
only the reviewed RAM instrumentation deltas. Installed boot021 did not change.

Reset observation complete:2 existing reads/returns/immediate guard checks/
validated rows,mirrors equal,error null. Both address fields=image_base,bit0 lock
classifier=true,bit11=false,low11:1 zero,bits47:42 zero,upper63:48 present.
Firmware-backed RESET_ADDRESS_READBACK_PASS; upper field present_uninterpreted,
semantics/exact entry/effective route UNKNOWN. No reset destination was redirected.

## Cold and vector observations

| Evidence | Cold channel | Vector channel |
|---|---|---|
| Samples attempted / completed | 183 /183 | 91 /91 |
| Reads attempted / completed | 732 /732 | 455 /455 |
| Highest phase seen | 0 | 0 |
| State | no_cold_publication_seen | no_recorder_publication_seen |
| Identity status | not_committed | not_committed |
| Complete record | false | false |
| Error | null | null |

Cold any_record_seen/stop_required/record_complete/park_verified all false;
exception level and identity fields null. Cold read counter732 agrees with the
tracker. Vector identity_seen/recorded/sample_complete false,closed=false,
EL/MMU/cache/identity fields null. Reset/spin classification no_reset_record_seen,
91 recorded samples. No independently verified CPU1 arrival or callback.

These are **phase/identity observations**, not a claim that every raw record word
was zero. The CPU0 publication checks and telemetry's no_publication_seen states
are distinct. No candidate natural-cold marker committed; no terminal loop or
architectural park is demonstrated. A phase3 marker would only prove CurrentEL
publication,but phase3 was not observed here. The cold record may also capture
unexpected identities; none was committed in this run.

## Power,state and exact stop boundary

| Sequential phase | CPU0 PS desired/actual | CPU1 PS desired/actual | CPU0 opaque byte | CPU1 opaque byte |
|---|---|---|---:|---:|
| before_start | 0/15 | 0/0 | 2 | 0 |
| after_first_start | 0/15 | 0/0 | 2 | 0 |
| after_second_start | 0/15 | 0/15 | 2 | 2 |

Three complete pairs,**6/6 reads** in each observation. All PS parent_missing/
device_disabled/auto_enabled false; PS/state errors null,state journal_failed=false.
Baseline change flags null; CPU0 later false/false,CPU1 false/true; equality
false/false/true. No final row exists. Sequential PS then opaque-state pairs
are not simultaneous samples. Opaque byte2 and legacy PS actual15 do not prove
t6050 reset release,running state or PC. Entry/reset/running NOT_ESTABLISHED,
PC NOT_OBSERVED,t6050 semantics UNKNOWN.

**95 mutation intents**,starts attempted/acknowledged2/2. Eight timer requests
planned,0 completed,round-trip list empty,counter progress=false,park=false.
The exact reason is **cpu1_arrival_observation_deadline**,checked inside the
inherited arrival observation loop. It is distinct from natural
cpu1_arrival_timeout and from the60s controller/65s supervisor wall deadlines.
Per the inherited gate,no trailing final PS/state pair was taken. Terminal
observation error=null does not mean a final pair passed; it was not attempted.
No extra target read was issued after the supervisor outcome. All acquisition
prefixes were preserved without extending the arrival window or retrying.

## Return and next interpretation

Human was instructed to power off and choose Macintosh HD immediately on the
supervisor outcome,before detailed inspection. Usual desktop return confirmed;
recorded **2026-10-22 04:12:26.181 UTC /2026-10-22 12:12:26 AM Eastern**,
**+64.898s** from wrapper start,within90s. This is the recorded confirmation
interval,not exact power-off or macOS boot time. No return problem reported.
Both owned bounded caffeine processes were no longer present during return
bookkeeping; no process was signaled then.

M5 next interprets the measured prefix under the published outcome table:
positive CPU0 control narrows CPU0 recording failures but does not prove either
CPU1 path absent. Earlier dispatch,first instruction/store,CPU1 publication and
incoming execution state remain unresolved. No guessed redirect,additional
power/reset/stop write,longer timeout,extra core or automatic next boot follows.

No post-outcome target command,retry,reconnect,cable troubleshooting,rollback/
cleanup RPC,Linux launch or settings change. Installed boot021,retained boot042,
client,macOS/volumes/firmware unchanged. Routine policy checks stay waived:
original Full/lab Permissive/Macintosh HD default remain last reported,not
freshly verified. **Linux/native SMP NOT RUN; CPU1 effective entry UNKNOWN**.
Frozen pre-execution NOT RUN wording is historical; this result supersedes it
only for the consumed31K session. Preserve all source pins and receipts.

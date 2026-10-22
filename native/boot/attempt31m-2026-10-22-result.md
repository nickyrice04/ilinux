# Attempt 31M — cache qualification passes; paired CPU1 records remain negative

**Observed, 2026-10-22 Eastern:** one authorized native31M session consumed.
Final **STOP / cpu1_arrival / cpu1_arrival_timeout**, controller/supervisor exits
**1/1**. CPU0 cache geometry qualified; Device, Normal and maintenance controls
all passed. Both retained CPU1 start stores were attempted and acknowledged.
Neither cached nor maintained Normal observation committed an identity.
**CPU1 execution remains unverified; Linux boot/native Linux SMP NOT RUN.**

Human confirmed the usual Macintosh HD desktop at **+39.504s** from wrapper
start, within90s. Controller **5.835s**, supervisor **6.581s**, no outer deadline.
No retry, reconnect, extra core, callback or post-outcome target operation.

Reviewed sanitized final JSON:
[controller](attempt31m-controller-2026-10-22.json),
[supervisor](attempt31m-supervisor-2026-10-22.json).
Raw journals, stderr and local execution bookkeeping remain ignored/private.

## Inputs, readiness and authorization

Handoff `24aa8eba5fe39b9587dd3a27d55d56159e9d8077`;
published readiness/execution `f874095919d1d7e2671b3cdea6dd08e0fbc9b0b5`.
[Independent M1 intake](attempt31m-m1-offline-2026-10-22.md): **306 pins and
870 image-only methods PASS**, no skips/repairs, both documented commands and
retained13-file package verification exit0. Python3.13.5, reviewed_layout_only;
**full-symbol checks NOT RUN on M1**, exact symbols not supplied. M5's VM072
893 full-symbol methods,46 synthetic actual-client scenarios, CTR-leaf assembly
comparison and REA work remain separate offline evidence, not rerun on M1.

Source manifest SHA-256:
`b89a052048cb6af45cf5065a96983df0c6c3012c5d2ec705212310679ac3da97`.
Retained boot021 image:3,932,160 bytes,
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Clean client `57a9339ffd1876e78297b17d34dece8cff8fa1ba`; retained package
manifest `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
Frozen L281/K254/J226/I202/H186/host6 and prior receipts/offline evidence remain
unchanged. No source fix, image transfer, install or consumed-receipt reset.

After readiness publication, human confirmed **“Start 31M; all confirmed”**:
fresh Running proxy, direct known-good cable, powered Macs, healthy awake/
unlocked/open-lid M1 and independent90-second timer. These conditions are
human-reported. Timer cue immediately preceded the one supervisor invocation;
wrapper start **2026-10-22 19:33:29.668 UTC /3:33:29 PM Eastern**. One owned
bounded120s caffeine assertion was requested for the command; no sleep setting
changed. No preliminary handshake/checker or reconnect was run.

## Connection and actual consumption

| Evidence | Recorded value |
|---|---|
| Cached registry queries attempted/returned | 1/1 |
| Classification/output/stderr | primary_verified/xml_plist/absent |
| Modem interfaces/primary candidates | 2/1 |
| Query start offset/elapsed | 0.000214s/0.021081s |
| Total discovery elapsed | 0.021603s |
| Discovery ready/native_ready | true/false |
| Source recheck | passed |
| Import, serial, UART, proxy, construction attempted/returned | all true/true |
| Native reservation attempted/child consumed | true/true |
| Last connection phase | controller_run |
| Transport close attempted/closed | true/true |
| Connection/native journal failure | false/false |

Cached discovery's device_opens0/target_requests0 are phase-only counts, not
totals after the successful serial open/native campaign. Pure reset validation's
hardware_operations0 likewise describes local validation. Parent invocation
reservation is not native consumption; the exclusive native journal and child
native_attempt_consumed=true establish this consumed session.

Connection journal **19 complete JSON rows**, native journal **1,655 complete
JSON rows**; each final row equals the final controller JSON. Stderr contains
only the expected pinned-client verification line. No finalization/interruption
error field was emitted. Supervisor reason `controller_exited`, deadline=false.
All six exclusive live-use files remain intact and block reuse.

## CPU0 qualification, controls and publication

| Cache qualification | Recorded value |
|---|---|
| Result | CPU0_MAINTENANCE_LAYOUT_QUALIFIED |
| DMinLine/CWG | 64 bytes/64 bytes |
| Issuing CPU/EL/regime | CPU0/EL2/VHE_host_stage2_disabled |
| Record/owned span | 64 bytes/128 bytes |
| Maintenance | DC_CIVAC_to_PoC |
| Effects limited to CPU0 | false |
| CPU1 cache state/native success established by qualification | UNKNOWN/false |

| Control | Reads attempted/completed | Stores attempted/acknowledged | Maintenance attempted/acknowledged | Result |
|---|---:|---:|---:|---|
| Device | 24/24 | 2/2 | not part of this control | CPU0_OBSERVER_CONTROL_PASS |
| Normal | 24/24 | 2/2 | not part of this control | CPU0_NORMAL_CONTROL_PASS |
| Separate maintenance | 48/48 | 2/2 | 2/2 | CPU0_CACHE_CONTROL_PASS |

All three controls observed their marker, preserved canaries and restored their
own scratch on the successful pre-start path. Device journal_failed=false,
Normal/maintenance error=null. Device control elapsed0.014119s; the other two
controls emit no elapsed field. These controls establish CPU0 behavior only,
not CPU1 execution or visibility. Restoration is the successful control path,
not cleanup after a fault.

RAM/BootArgs predicates passed, revision3. Direct USB/expected diagnostic UART
checks passed, two initially enabled diagnostics and RAM zero publication recorded.
CPU0 EL2/regime and inherited code/Device/control/cold/power/state probes passed.
All20 Normal and13 new cache permission predicates passed. Boolean permission
checks include expected write denials, not remaps or newly allowed writes.

Live feature GOT binding, CTR leaf readback/publication and full128-byte clean
vector/cold/control granules passed. The dispatch-table check also passed before
the controller advanced. Both inherited body/hook/whole-text checks and all
Normal prefix/full-text checks passed. Known-zero freshness preceded starts.
Normal/cold entry armed; cache_records_frozen=true,
**cpu0_post_start_record_stores=0**. New post-start maintenance was restricted
to the two owned Normal record addresses. No Device/code/MMIO/arbitrary-address,
whole-cache or invalidate-only maintenance was introduced.

Census validated18 cores:12 Performance (ADT M),6 Super (ADT P). CPU1 alone in
CPU0's active Performance cluster was targeted; start mapping unchanged.
Reset observation:2 reads/returns/immediate guards/validated rows, equal mirrors,
error=null; RESET_ADDRESS_READBACK_PASS. Both address-field classifiers match
image_base, bit0 lock classifier true, bit11 false, low10:1 and47:42 zero,
upper63:48 present/uninterpreted. Exact entry and effective reset route UNKNOWN;
no reset redirect occurred.

## Paired cached/maintained observations

| Channel | Paired samples attempted/completed | Reads attempted/completed | Maintenance intents/attempted/acknowledged | Highest phase/identity |
|---|---:|---:|---:|---|
| Normal vector | 128/128 | 768/768 | 128/128/128 | 0/not_committed |
| Normal cold | 128/128 | 768/768 | 128/128/128 | 0/not_committed |

Each final cached and maintained snapshot has3 completed reads, complete=true,
phase0, any_record_seen=false and identity_status=not_committed. Both aggregate
trackers also have highest_phase_seen0, any_record_seen=false, error=null,
journal_failed=false and observation_channel=null. CPU1 execution UNVERIFIED,
visibility_cause UNKNOWN, negative_excludes_execution=false and
effects_limited_to_cpu0=false remain explicit.

**258 total maintenance intents/attempts/acknowledgments** comprise2 pre-start
control requests plus256 post-start record requests. Every acknowledged request
returned through the reviewed completion/exception-check path. No maintenance
fault or missing maintained sample is reported. These are CPU0-issued operations
that can affect the shareability domain, not a guarantee of CPU0-local effects.

The inherited `normal_observation` holds only the pre-start cached freshness
sample:1 sample/3 reads per channel. It is not the post-start paired result.
Total normal_reads **1,542 = 6 pre-start +1,536 paired reads**. The post-start
cached/maintained details are in `paired_observation`. Its final snapshots are
not a dump of all samples; cumulative counters/highest-phase state and private
journals retain acquisition progress.

No CPU1 prefix identity was observed. Negative cached/maintained records still
cannot exclude execution, an earlier exception, a different entry route or
private dirty CPU1 data outside the observed domain. No positive occurred, and
even a maintained positive alone would not establish cache causality because
CPU1 could write between snapshots. **No cache cause or startup fix is established.**

## Inherited channels, power and stop boundary

Device vector: **64 samples/320 reads**; Device cold: **129 samples/516 reads**,
all attempted reads/samples complete. Highest phases0, identity not_committed,
errors null, records incomplete. Vector state no_recorder_publication_seen,
identity flags false, closed=false, EL/MMU/cache/identity fields null. Cold state
no_cold_publication_seen, any_record_seen/stop_required/complete/record_complete/
park_verified false, exception level/identity fields null. Entry classification
no_reset_record_seen. These are phase/identity observations, not proof that
every raw record word was zero or neither entry path executed.

| Sequential phase | CPU0 PS desired/actual | CPU1 PS desired/actual | CPU0 opaque byte | CPU1 opaque byte |
|---|---|---|---:|---:|
| before_start | 0/15 | 0/0 | 2 | 0 |
| after_first_start | 0/15 | 0/0 | 2 | 0 |
| after_second_start | 0/15 | 0/15 | 2 | 2 |
| final | 0/15 | 0/15 | 2 | 2 |

Four complete pairs,8/8 reads each for power and opaque state, errors null.
All PS parent_missing/device_disabled/auto_enabled flags false; state
journal_failed=false, terminal_observation_error=null. CPU0 change flags false
after baseline, CPU1 false/true/true, pair equality false/false/true/true.
These sequential pairs are not simultaneous measurements. Power/opaque changes
do not prove running/reset/PC semantics: entry/reset/running NOT_ESTABLISHED,
PC NOT_OBSERVED, t6050 register semantics UNKNOWN.

**413 mutation request intentions**, including RAM publication/controls/cache
operations and the two retained starts; this is not413 power writes. CPU1 start
stores attempted/acknowledged **2/2**. Callbacks planned/completed **0/0**, empty
round-trip list, counter_progress=false, park=false. No callbacks were authorized.

Natural **cpu1_arrival_timeout** ended the run. This is distinct from an
in-flight observation deadline, control/qualification refusal, transport failure
or outer60s/65s wall deadline. The final PS/state pair was acquired by the reviewed
natural-timeout path before returning the outcome; no additional target read
followed the supervisor result. Arrival/control budgets bracket batches and
operations, not hard per-RPC interrupts; the independent bounds were retained.

## Return and next interpretation

Immediately on the supervisor result, before detailed inspection, the human
was told to power off and select Macintosh HD. Usual desktop return confirmed
**2026-10-22 19:34:09.172 UTC /3:34:09 PM Eastern**, **+39.504s**, within90s.
This is the recorded confirmation interval, not exact shutdown/boot duration.
No return problem reported. Both owned bounded caffeine processes were absent
at return bookkeeping; no process was signaled then.

No M1 restart, image transfer, reinstall, new MMIO/reset operation, extra core,
post-outcome target command, cleanup RPC, reconnect, retry or Linux launch.
Installed boot021, retained boot042, pinned client, macOS/volumes/firmware and
security/default settings remain unchanged by this session. Routine policy
checks stay waived: original Full/lab Permissive/Macintosh HD default remain
last reported, not freshly verified. All consumed receipts and prior evidence
remain intact. Frozen pre-execution NOT RUN statements are historical for31M.

M5 owns the next interpretation before any separate proposal. CPU0 qualification
and maintained negative records do not establish CPU1's reset/first-fetch route.
**CPU1 execution/effective entry remain unverified; Linux boot/native Linux SMP
NOT RUN. No CPU speed, efficiency or macOS parity claim follows.**

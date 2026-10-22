# Attempt 31L — both CPU0 controls pass; no visible CPU1 entry

**Observed, 2026-10-22 Eastern:** one authorized native 31L session consumed.
Final result **STOP / cpu1_arrival / cpu1_arrival_timeout**, controller and
supervisor exits **1 / 1**, with no supervisor deadline. Both CPU0 controls,
mapping/reset gates and pre-start publication checks passed. Both CPU1 start
stores were attempted and acknowledged. Neither Normal nor Device channel
committed an identity. **CPU1 execution remains unverified; Linux boot and
native Linux SMP NOT RUN.** No callbacks or retry followed.

Human confirmed return to the usual Macintosh HD desktop at **+38.799 s**
from the command wrapper start, within the independent 90-second window.
Controller duration **5.796 s**; supervisor **6.432 s**. These durations include
transport/software work and are not CPU performance measurements.

Reviewed sanitized final outputs:
[controller](attempt31l-controller-2026-10-22.json) and
[supervisor](attempt31l-supervisor-2026-10-22.json).
Raw journals, stderr and local execution bookkeeping remain ignored/private.

## Provenance and independent offline verification

Release/handoff: `11cc2afc973838a6426f7882db6b2924893e85ae`.
Published readiness and execution: `c7608c7725dcd622d67d6c86109d55299f8967e9`.
[M1 intake](attempt31l-m1-intake-2026-10-22.md): **281 pins and 796 image-only
methods PASS**, no skips or source repairs. Both documented offline commands
and the retained 13-file package check exited 0. Mode `reviewed_layout_only`;
**full-symbol checks NOT RUN on M1**. M5's separate full-symbol VM, actual-client
synthetic scenarios, assembler comparisons and REA work remain offline evidence;
they were not rerun on M1.

31L source manifest SHA-256:
`c7cc43434da7fb386e2486691a0a639053751396760624a6827d8588b5a9d26f`.
Retained 3,932,160-byte boot021 image SHA-256:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Client remains clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
Retained package manifest:
`60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
Frozen K254/J226/I202/host6 inputs and all prior consumed evidence remain intact.
The earlier 24-test 31L offline analysis remains separate and unchanged.

After readiness publication, the human confirmed **“Start 31L; all confirmed”**:
fresh M5 Running proxy, powered Macs, direct known-good cable, healthy awake/
unlocked/open-lid M1 and independent timer. These conditions are human-reported.
The timer cue immediately preceded the single supervisor invocation; wrapper
start **2026-10-22 18:46:45.036 UTC / 2:46:45 PM Eastern**.
One owned bounded caffeine assertion was requested for this command; no sleep
setting changed. No preliminary checker, handshake or reconnect was performed.

## Connection, consumption and bounds

| Evidence | Recorded value |
|---|---|
| Cached registry queries attempted / returned | 1 / 1 |
| Classification / output | primary_verified / xml_plist |
| Query stderr | absent |
| Modem interfaces / primary candidates | 2 / 1 |
| Query start offset / elapsed | 0.000150 s / 0.020625 s |
| Total discovery elapsed | 0.021114 s |
| Discovery ready / native_ready | true / false |
| Source recheck | passed |
| Import, serial, UART, proxy, construction attempted / returned | all true / true |
| Native reservation attempted / child consumed | true / true |
| Final connection phase | controller_run |
| Transport close attempted / closed | true / true |
| Connection / native journal failure | false / false |

Discovery's device_opens=0 and target_requests=0 describe the cached discovery
phase only. They do not describe the subsequent successful serial open and
native campaign. The pure reset-format validator's hardware_operations=0 is
likewise local validation scope. Parent invocation reservation alone is not
native consumption; the child's consumed flag and exclusive native journal are.

Connection journal: **19 complete JSON rows**. Native journal: **297 complete
JSON rows**. Both final rows equal the controller's final JSON. Stderr contains
only the expected client-pin verification line. No finalization/interruption
error field was emitted; no connection/native journal failure was recorded.
The supervisor reports `controller_exited`, not its outer deadline.

The reviewed child 60 s, supervisor 65 s, serial 2 s, arrival 3 s and two local
control 2 s bounds were retained. No window was extended. All six live-use files
are retained and block reuse. No source fix, additional target query or retry
was used to obtain the result.

## CPU0 controls and pre-start gates

| Evidence | Device control | Normal control |
|---|---|---|
| Result | CPU0_OBSERVER_CONTROL_PASS | CPU0_NORMAL_CONTROL_PASS |
| Read intents / attempted / completed | 24 / 24 / 24 | 24 / 24 / 24 |
| Store intents / attempted / acknowledged | 2 / 2 / 2 | 2 / 2 / 2 |
| Marker observed | true | true |
| Canaries preserved | true | true |
| Original scratch restored | true | true |
| Error | journal_failed=false | error=null |
| Elapsed field | 0.013107 s | not emitted |
| CPU1 visibility tested by control | no | no |

The successful control sequences restore their separate scratch before starts.
This is not post-fault cleanup. Neither control establishes CPU1's incoming
translation regime, first fetch/store, record visibility or execution.

RAM/BootArgs predicates pass, revision 3; direct USB/expected diagnostic UART
checks pass, two initially enabled diagnostics and RAM zero publication recorded.
CPU0 EL2/regime, inherited code/Device/control probes, both power and opaque-state
probes, cold probes and all **20 Normal permission predicates** passed. Probe
booleans mean the expected permission checks passed, including expected write
denials; no mapping was changed.

The exact ADT/runtime census validates **18 cores: 12 Performance (ADT M) and
6 Super (ADT P)**. CPU1 alone, in CPU0's active Performance cluster, is targeted.
The fixed start mapping is unchanged. Other clusters' legacy-mask differences
are classified only; no extra core is started.

Both inherited body/hook/whole-text readbacks passed. Normal vector body/hook,
cold body/hook and whole-text verification all passed. Known-zero record
freshness passed before starts; `cold_entry_armed` and `normal_entry_armed`
are true. Normal records remain in the owned helper allocation, with separate
CPU0 control. Cache publication occurred before start intents only. No
post-start cache maintenance, remap or installed-image write was performed.

Reset observation: two reads/returns/immediate guards/validated rows, equal
mirrors, error null; `RESET_ADDRESS_READBACK_PASS`. Both address-field classifiers
match image_base, bit0 lock classifier true, bit11 false, low10:1 and 47:42 zero,
upper63:48 present/uninterpreted. Exact entry offset and effective reset route
remain UNKNOWN. No reset destination was redirected.

## Entry-channel observations

| Channel | Samples attempted / complete | Reads attempted / complete | Highest phase | Identity | Error |
|---|---:|---:|---:|---|---|
| Normal vector | 169 / 169 | 507 / 507 | 0 | not_committed | null |
| Normal cold | 169 / 169 | 507 / 507 | 0 | not_committed | null |
| Device vector | 84 / 84 | 420 / 420 | 0 | not_committed | null |
| Device cold | 169 / 169 | 676 / 676 | 0 | not_committed | null |

Total Normal reads **1,014**. Both Normal `any_record_seen` flags false;
`cpu1_prefix_identity_observed=false`. Device vector state is
`no_recorder_publication_seen`, identity flags false, complete=false, closed=false.
Device cold state is `no_cold_publication_seen`, any_record_seen/stop_required/
complete/record_complete/park_verified false. Exception-level and identity fields
remain null. The inherited entry classification is `no_reset_record_seen`.
These are measured phase/identity-channel observations, not proof that CPU1
executed neither path, nor a claim that every raw record word was sampled.

Both Normal prefixes store phase before reading MPIDR. A Normal-store fault
could prevent the later Device recorder from running; CPU0 cached polling can
also miss noncoherent stores. Positive CPU0 controls do not remove these unknowns.
**Negative channels cannot exclude CPU1 execution or distinguish a cache/Device
visibility cause from an earlier entry problem.** No committed CPU1 identity,
reset provenance, verified terminal park or CPU1 program counter was obtained.
`device_visibility_cause=UNKNOWN` is retained.

## Power, opaque state and exact stop

| Sequential phase | CPU0 PS desired/actual | CPU1 PS desired/actual | CPU0 opaque byte | CPU1 opaque byte |
|---|---|---|---:|---:|
| before_start | 0/15 | 0/0 | 2 | 0 |
| after_first_start | 0/15 | 0/0 | 2 | 0 |
| after_second_start | 0/15 | 0/15 | 2 | 2 |
| final | 0/15 | 0/15 | 2 | 2 |

Four complete pairs, **8/8 reads each** for PS and opaque state. All PS
parent_missing/device_disabled/auto_enabled flags false. Both errors null;
state journal_failed=false, terminal_observation_error=null. CPU0 change flags
remain false after baseline; CPU1 false/true/true; pair equality false/false/
true/true. The sequential pairs are not simultaneous measurements. Opaque byte2
and legacy PS actual15 do not establish t6050 running/reset/PC semantics.
Entry/reset/running remain NOT_ESTABLISHED, PC NOT_OBSERVED, register semantics
UNKNOWN.

**144 mutation request intentions** include the reviewed RAM instrumentation,
controls/cache publication and retained starts; this is not 144 power writes.
CPU1 starts attempted/acknowledged **2/2**. Eight inherited timer callbacks remain
listed as planned by the base state, but 31L authorizes none: requests_completed
**0**, empty round-trip list, counter progress=false and park=false.

This run ended with natural **cpu1_arrival_timeout**, distinct from 31K's
in-flight `cpu1_arrival_observation_deadline` and the outer wall deadlines.
The inherited natural-timeout path recorded the final PS/state pair before
returning its result. No extra sampling occurred after the supervisor outcome.
No positive-prefix stop or Device-only arrival occurred. No callbacks followed.

## Return and handoff

Immediately on the supervisor outcome, before detailed result inspection, the
human was told to power off and choose Macintosh HD. Usual desktop return
confirmed at **2026-10-22 18:47:23.836 UTC / 2:47:23 PM Eastern**, **+38.799 s**
from wrapper start, within 90 s. This measures the recorded confirmation
interval, not exact shutdown/boot duration. No return problem was reported.
Both owned bounded caffeine processes were absent during return bookkeeping;
no process was signaled then.

All prior receipts, earlier 31L offline work, source pins, boot021 installation,
retained boot042 and pinned client remain intact. No M1 restart, image transfer,
reinstall, firmware/volume/security/default change, new MMIO/reset operation,
post-outcome target command, cleanup RPC, reconnect or retry. Routine policy
checks remain waived: original Full/lab Permissive and Macintosh HD default are
last reported states, not freshly verified here.

M5 owns interpretation before any separate next experiment. The consumed native
31L result supersedes frozen pre-execution NOT RUN wording only for this session.
**CPU1 execution/effective entry remain unverified; Linux boot/native SMP NOT RUN.
No CPU speed, desktop latency or performance-parity conclusion follows.**

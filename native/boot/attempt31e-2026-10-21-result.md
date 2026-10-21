# Attempt 31E — publication verified; no CPU1 recorder progress observed

**Observed, 2026-10-21:** one authorized supervised 31E session returned
**STOP / `cpu1_arrival` / `cpu1_arrival_timeout`**, controller/supervisor exits
**1 / 1**, supervisor deadline **false**. All **16 CPU0 translation probes**
passed in the verified **EL2/VHE regime**. Recorder body, hook and whole-text
readback checks passed. Both CPU1 startup stores were attempted and
acknowledged; arrival was not verified within three seconds.

CPU1 recorder observation: **93 complete samples / 465 reads**, highest phase
**0**, identity **not seen**, complete **false**, error **null**, tracker closed
**false**. Reset/spin observation: **`no_reset_record_seen`**, **94 samples**.
No timer request ran; final park remains unverified. Controller elapsed
**4.587 s**, supervisor **5.024 s**. Human confirmed usual Macintosh HD return
at **+45.867 s**, within the independent 90 s bound.

**31E is consumed.** No retry, reconnect, rollback, code restoration, extra
core, timeout extension or Linux continuation. CPU0 permission/readback success
does not prove CPU1 instruction visibility, reset entry or lack of execution.
**Linux/native Linux SMP, timer callbacks, final park, renderer performance
and energy tests NOT RUN/unverified.**

Exact schema-reviewed final outputs:
[controller](attempt31e-controller-2026-10-21.json),
[supervisor](attempt31e-supervisor-2026-10-21.json).
Raw receipts, stderr, target memory, addresses and identifiers stay private
under ignored build. Only original summary and reviewed final schemas are public.

## Provenance and offline limits

M5 handoff **`a79a275e7b69fd0c9b6522eb5da98c7b02288473`**;
published M1 readiness/execution **`76514f05d4047db6b82a3009c7cf6f2bba75bd2d`**.
[Independent M1 intake](attempt31e-m1-offline-2026-10-21.md): **112 source pins**,
**141 Python methods PASS**, no skips/fixes, both documented commands exit 0,
zero hardware operations before start. Symbol mode **`reviewed_layout_only`**;
full-symbol checks **NOT RUN on M1**, explicitly not selected in this mode.
M5's separate 181-method full-symbol VM evidence was reviewed, not rerun or
relabeled native. Additional retained-package intake verified all **13 files**.

Source-manifest SHA-256:
`5be6295c5f523f58e771d5e896729b909ac2593ff67defdb46e843fc4a66d17a`.
Existing 3,932,160-byte boot021 image:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Clean client remains **`57a9339ffd1876e78297b17d34dece8cff8fa1ba`**.
Original recorder/permission-tail/startup-helper bytes are those independently
validated in `attempt31e/controller-validation.md`. No source, mapping,
protection-policy or installed-image change was made to pass the native gates.

Prior 31B/31C/31D evidence digests remain unchanged. All five real 31E live-use
files were absent before/after offline intake; the actual run created its
separate immutable evidence. No receipt was deleted or reset. No new image,
host install, VM or routine M1 restart was needed. A bounded owned caffeine
assertion kept the helper awake.

## Native sequence and observations

After publication, the human explicitly confirmed starting 31E, a fresh M5
lab proxy session, both Macs powered, direct cable, healthy awake/unlocked/
open-lid M1 and an independent 90 s timer. These preparation facts are
human-reported. The timer cue immediately preceded the single fixed supervisor
with `--confirm START-CPU1-J716C-31E`. Command start:
**22:33:49.956 UTC / 6:33:49 PM Eastern**.

| Evidence | Recorded result |
|---|---|
| RAM predicates / BootArgs revision | 11 true / 3 |
| Direct USB / expected UART bases / initially enabled count | true / true / 2 |
| UART RAM zeroes published | true |
| CPU0 permission regime / all 16 probes / overall gate | EL2/VHE / PASS / PASS |
| Recorder body / hook / whole immutable text | verified / verified / verified |
| Explicit mutation intents | 72 |
| CPU1 start writes attempted / acknowledged | 2 / 2 |
| CPU1 arrival verified | false |
| Recorder sample attempts / completions | 93 / 93 |
| Recorder read attempts / completions | 465 / 465 |
| Highest recorder phase / identity / complete | 0 / false / false |
| Recorder error / closed | null / false |
| Reset/spin classification / sample count | no_reset_record_seen / 94 |
| Timer requests planned / completed | 8 / 0 |
| Request round-trip samples / counter progress / final park | empty / false / false |
| Linux boot / native Linux SMP | NOT RUN / NOT RUN |
| Controller elapsed / supervisor elapsed | 4.587 s / 5.024 s |

The permission booleans include **expected identity-code write denials**;
`hook_identity_write:true` means that denial was verified, not that identity
code became writable. Existing writable-alias translation checks passed.
Actual guarded stores, alias/identity readback and whole-text comparison also
passed. No remapping, security change or arbitrary permission relaxation followed.

**Inferred from exact flow and recorded gates:** inherited preflight and
helper/CPU1/UART setup completed, followed by helper extension and permission
checks. The original 204-byte recorder body was published before its four-byte
entry hook, with cache maintenance and both-view readback. Whole-text comparison
allowed only those two RAM-code deltas. The same two startup stores then ran
through the original guard-free helper. The **72 mutation intents** match the
documented fully published arrival-timeout path; intentions are distinct from
the two acknowledged startup stores. No request phase was reached.

The reset/spin count includes one observation between startup stores; recorder
sampling begins in the arrival window. This explains 94 versus 93 samples.
No nonzero exception-count/guard flag was reported in the saved receipt; no
raw counter value or universal absence-of-fault conclusion is published.

`no_recorder_publication_seen` refers to **CPU1's telemetry record**, not the
CPU0 recorder-code publication, which passed. Phase 0 with no identity does not
establish that every record word was zero or that CPU1 executed no instruction.
Incoming EL and SCTLR M/C/I bits remain **unknown/null**, not disabled/EL0.
The zero-phase result can reflect no entry, an earlier fault or invisible
writes; this run cannot distinguish them. CPU0 readback and ISB do not establish
the offline secondary's instruction/cache state. Sequential samples are not an
atomic snapshot or PC trace; final barrier/replay and final parked state are
not established. UART muting also limits fallback early-fault diagnostics.

The private consumed receipt has **92 records**. Public output contains only
the reviewed final controller/supervisor schemas. No round-trip measurements
exist because no callback ran; overall durations include USB, Python, host
scheduling and journaling and are not CPU latency benchmarks.

## Return and next M5 review

Immediately on the supervisor result, the human was told to power off and
select Macintosh HD. No further target RPC, rollback, restoring code, freeing
allocations or reconnect occurred. The controller closed its transport.
Human return recorded **22:34:35.823 UTC / 6:34:35 PM Eastern**, **+45.867 s**
from command start, including UI/confirmation overhead. Only the owned caffeine
assertion was stopped after confirmation. No return problem was reported.

Loaded RAM code changed for this one session and was retained until power-off;
the installed boot021 object, client pin, macOS, firmware, mappings/protections,
boot/security/default/volume settings stayed unchanged. Routine policy/default
rechecks remained waived; original Full/lab Permissive/Macintosh HD default
remain last reported, not freshly verified.

**M5 next: review the successful CPU0 publication/permission gates alongside
the absent CPU1 recorder/reset progress, then select a separately reviewed
earlier-entry or visibility observation.** Preserve all consumed evidence.
No unchanged retry, speculative power/RVBAR write, protection change or Linux
continuation. CPU1 entry evidence still precedes two-core Linux correctness,
timer/IPI/coherence and renderer/memory measurements. Current coordination and
this result supersede frozen pre-execution controller NOT RUN wording.

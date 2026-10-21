# Attempt 31F — vector recorder published; no first marker observed

**Observed, 2026-10-21:** the one authorized 31F session returned **STOP /
`cpu1_arrival` / `cpu1_arrival_timeout`**, controller/supervisor exits **1 / 1**,
supervisor deadline **false**. All **16 CPU0 translation probes** passed in
the verified **EL2/VHE regime**. Recorder body, vector hook and whole-text
readback checks passed. Both CPU1 start stores were attempted and acknowledged.

The vector-first recorder retained **phase 0**, **94 complete samples / 470
reads**, identity **not committed**, error **null**, tracker closed **false**.
Reset/spin observation remained **`no_reset_record_seen`**, **94 samples**.
CPU1 arrival was not verified within three seconds. Eight callbacks were
planned but **0 ran**; counter progress and final park remain unverified.
Controller elapsed **4.567 s**, supervisor **5.003 s**.

Human corrected an accidental **Return problem** selection: **“hit wrong
button returned fine.”** Usual Macintosh HD return is confirmed; no actual
return fault was reported. The corrected confirmation was recorded at
**+80.498 s** from command start, within the independent 90 s bound. This
interval includes the mistaken selection/correction and is not boot time.

**31F is consumed.** No retry, reconnect, rollback, code restoration, timeout
extension, extra core, power/RVBAR operation or Linux continuation occurred.
CPU0 publication does not establish CPU1 instruction visibility, effective
reset destination or zero executed instructions. **Linux/native Linux SMP,
callbacks, final park, renderer performance and energy tests NOT RUN/unverified.**

Exact schema-reviewed final outputs:
[controller](attempt31f-controller-2026-10-21.json),
[supervisor](attempt31f-supervisor-2026-10-21.json).
Raw receipts, stderr, target memory, addresses and personal identifiers remain
private under ignored build. Only the original summary and final schemas are public.

## Provenance and offline verification

M5 handoff **`6092b11acb2f4a06a29a616a0ccc6db1b0b3707b`**;
published M1 readiness/execution **`56f68f14e9a113ca469ce4627908d08ca6492492`**.
[Independent intake](attempt31f-m1-offline-2026-10-21.md): **138 source pins**,
**194 Python methods PASS**, no skips/fixes; both documented commands exit 0,
zero hardware operations before start. Symbol mode **`reviewed_layout_only`**;
full-symbol checks **NOT RUN on M1**. The 23-method full-symbol suite was not
selected in this documented mode. M5's 217-method/full-symbol VM, assembly and
wire-integration evidence remained separate offline facts.

Source-manifest SHA-256:
`d5de4d4ba2372ec7cf0c0d4c509f8feeea07a096fc466cf18026ac2d8c3b0161`.
Existing 3,932,160-byte boot021 image:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Original 168-byte recorder:
`52f9d1b312725cdc9261e0fbf1c31991e9078a663827734b9ba54c9d171106bc`.
Clean client pin remains `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
Additional retained-package verification passed all **13 files**. No source
or guard was changed to make the live gates pass.

All five real 31F live-use files were absent before/after offline intake.
The actual session created separate immutable evidence; no receipt was deleted
or reset. Prior 31B/31C/31D/31E live evidence digests remain unchanged. No image
transfer, install, VM or routine M1 restart was needed.

## Execution and exact partial result

After readiness publication, the human explicitly confirmed starting 31F,
a fresh M5 lab proxy session, both Macs powered, direct cable, healthy awake/
unlocked/open-lid M1 and independent 90 s timer. These are human-reported
preparation facts. The timer cue immediately preceded the single fixed
supervisor with `--confirm START-CPU1-J716C-31F`. Local command start:
**23:20:46.164 UTC / 7:20:46 PM Eastern**.

| Evidence | Recorded value |
|---|---|
| RAM predicates / BootArgs revision | 11 true / 3 |
| Direct USB / expected UART bases / initially enabled count | true / true / 2 |
| UART RAM zeroes published | true |
| CPU0 regime / all 16 probes / permission gate | EL2/VHE / PASS / PASS |
| Recorder body / vector hook / whole text | verified / verified / verified |
| Explicit mutation intents | 63 |
| CPU1 start writes attempted / acknowledged | 2 / 2 |
| CPU1 arrival verified | false |
| Recorder sample attempts / completions | 94 / 94 |
| Recorder read attempts / completions | 470 / 470 |
| Highest phase / identity status / complete | 0 / not_committed / false |
| Recorder error / closed | null / false |
| Reset/spin classification / samples | no_reset_record_seen / 94 |
| Timer requests planned / completed | 8 / 0 |
| Round-trip samples / counter progress / final park | empty / false / false |
| Linux boot / native Linux SMP | NOT RUN / NOT RUN |
| Controller / supervisor elapsed | 4.567 s / 5.003 s |

Permission booleans include the required **identity-code write denials**;
`hook_identity_write:true` means expected denial was verified, not that the
identity mapping became writable. Existing writable-alias translation checks,
actual guarded stores, both-view readback and immutable-text comparison passed.
No mapping, HCR or protection policy was changed.

**Inferred from exact flow and recorded gates:** inherited preflight/helper/
CPU1/UART setup completed, followed by helper extension, permission checks,
body-before-vector-hook publication and whole-text comparison allowing only
the two reviewed RAM-code deltas. There were **63 mutation intents**: 14 setup
intents, 42 body-word stores plus two cache-maintenance intents, one hook store
plus two cache-maintenance intents, and two startup stores. Intent count is
distinct from acknowledged startup and observed CPU behavior.

One recorder/reset observation occurred between startup stores and showed no
progress/error, allowing the second store under the reviewed rule. The other
93 complete observations occurred in the arrival window. No timer-request
phase was reached. The receipt reports no nonzero exception-count/guard flag;
that is not a universal absence-of-fault claim. No raw counter is published.

`no_recorder_publication_seen` describes **CPU1 telemetry publication**, not
the CPU0 recorder-code publication, which passed. No identity was committed,
so observed CPU/class, incoming EL and SCTLR M/C/I flags remain **unknown/null**,
not disabled or assigned to CPU0. Phase 0 does not establish that all record
words were zero. The earliest visible marker depends on effective entry,
instruction visibility and the first store; no marker does not distinguish
wrong dispatch, an earlier fault or invisible execution/data writes.

The vector also serves a synchronous exception slot. A marker would not by
itself prove CPU1 reset provenance; no such marker was observed here.
Sequential RAM samples are not an atomic snapshot or PC trace. CPU0 readback
and instruction maintenance do not prove CPU1's incoming cache/mapping state.

The saved topology metadata matches the exact ADT/runtime census: 18 defined
CPU records, clusters of six, reviewed classes **12 Performance (ADT M) +
6 Super (ADT P)**. CPU1 is the same-cluster Performance target. These labels
combine the verified layout with the reviewed macOS class mapping; no CPU1
MPIDR was newly observed. This is not 18 online Linux CPUs or calibrated
scheduler capacity; those fields explicitly remain uncalibrated/NOT RUN.

The private consumed receipt has **84 records**. Public output contains only
the reviewed final schemas. Callback round-trip measurements are empty; total
durations include USB, Python, host scheduling and journaling, not CPU latency.

## Return and next M5 review

Immediately on the supervisor result, the human was instructed to power off
and choose Macintosh HD. The controller/supervisor had already completed;
transport was closed. No subsequent target RPC, cleanup, restore, reconnect
or retry occurred. After the mistaken button press, the human explicitly
confirmed the return worked normally. Corrected confirmation recorded
**23:22:06.662 UTC / 7:22:06 PM Eastern**, **+80.498 s** from command start.
Only the owned bounded caffeine assertion was stopped afterward.

Loaded RAM code changed for this session and stayed reserved until power-off.
Installed boot021/client, macOS, firmware, mappings/protection policy and
boot/security/default/volume settings remained unchanged. Routine policy/default
rechecks stayed waived; original Full/lab Permissive/Macintosh HD default are
last reported, not freshly verified.

**M5 next: offline investigation of effective reset target/instruction
visibility and the first-store boundary, as the 31F no-marker branch specifies.**
Preserve every consumed receipt. No unchanged retry, speculative power/RVBAR
write, protection change or Linux continuation. CPU1 entry evidence remains
the gate before two-core Linux correctness, timer/IPI/coherence and renderer/
memory measurements. Current coordination and this result supersede frozen
pre-execution controller NOT RUN wording.

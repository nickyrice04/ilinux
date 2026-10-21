# Attempt 31B — RAM-bound preflight refusal, zero mutations

**Observed, 2026-10-21:** one authorized supervised 31B attempt returned
**STOP / preflight / `ram_bounds`**, controller exit **1**. The controller
reported **0 mutation requests, 0 start writes attempted/acknowledged, 0 requests
completed**, arrival/counter progress unverified. Supervisor elapsed **1.192 s**,
controller **0.781 s**, supervisor deadline **false**. No allocation, helper
upload, CPU1 setup or start occurred. Human Macintosh HD return confirmed;
no retry, reconnect, gate edit or further target command.

**31B is consumed despite the preflight refusal. CPU1 entry, native Linux SMP,
Linux boot, renderer, performance and energy tests remain NOT RUN.** A RAM-range
guard refusal is not evidence that CPU1 cannot start or that physical RAM is
faulty. Actual rejected bounds were not recorded; the exact cause is unknown.

Schema-reviewed final outputs:
[controller](attempt31b-controller-2026-10-21.json),
[supervisor](attempt31b-supervisor-2026-10-21.json).
The raw durable consumed receipt and stderr remain private and ignored.

## Provenance and completed offline gate

M5 handoff **`7d505fd`**, published readiness/execution
**`a6ced1708c87800d94a99c8046e85a6e7b33c217`**. Independent
[M1 readiness](attempt31b-m1-offline-2026-10-21.md) preceded the live command:

* All **36** source pins passed; no source/procedure/guard change during this
  session. Source-manifest SHA-256
  `ea37bdfe6a9f32531c07dcdada340465833e49f7d1ecb72e36c1fe3d814dbd14`
  is also the controller's recorded manifest digest.
* Boot042's 13 files matched manifest
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
  Installed boot021 image, 3,932,160 bytes:
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
  Clean client remained `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* Controller SHA-256
  `9fea909adeb0bdef74a5c544af6c0b95f1ecda4740a95d4ff683c91238a6bced`;
  supervisor `2f66b7d0d51ffaaeef0dbe55b02c00e49fa45e9f3f5b27027d86b6514d2eb6aa`;
  original 192-byte helper
  `dc046b303191b9a4fcb26a9e689fa4ec7b936dd1ae67dc5fd9b81c4edf4bf8aa`
  verified offline but **not uploaded/executed on the target**.
* **46 Python methods PASS**: 19 controller, 3 supervisor, 11 census, 5 audit,
  8 renderer. All seven offline processes exited 0; no skips, failures or fixes.
  The offline controller opened no USB, allocated no target RAM and created no
  real live-use receipt.
  Supervisor tests terminated only their own dummy children.
* All five prescribed live-use files were absent before/after offline tests;
  none was erased or reset. No competing reader/proxy/controller was found.

M5's separate helper/secondary-loop/client-serialization/real-parser VM evidence
remains offline evidence. No ARM64 helper was executed on M1 or new image/VM
downloaded. Human stated M1 restart/M5 Running proxy, then confirmed power,
direct reseat, unlocked/open-lid M1 and 90 s timer readiness. Restart is human-
reported; this run did not independently measure M1 boot freshness.

## Live boundary and exact failure location

After readiness publication, the human received the 90 s timer cue immediately
before the documented supervisor ran **once**, with existing boot021 and
`--confirm START-CPU1-J716C-31B`. Local execution-note start:
**20:15:44.301 UTC / 4:15:44 PM Eastern**. Controller 60 s, supervisor 65 s with
bounded child termination, serial 2 s, arrival 3 s and request 1 s bounds were unchanged.
No deadline expired; neither arrival nor request windows were reached.

The fixed reason `ram_bounds` originates in `smp31b.py:ram_bounds`, reached
from `Controller.preflight` before helper preparation. **Inferred from exact
control flow and the recorded reason:** internal census predicates completed
(chip/board/topology, installed startup/SMP windows, mirror locks/vector class,
no secondary), then the boot-args physical RAM-range predicate refused.
This is not a separately rerun census 31A or evidence that all 31B preflight
checks passed. Full relocated-text/features/fresh RAM checks follow this bound
and were **not reached**; helper setup and every explicit mutation follow later.

| Controller field | Recorded value |
|---|---|
| result / phase / reason | STOP / preflight / ram_bounds |
| mutation_requests | 0 |
| start_writes_attempted / acknowledged | 0 / 0 |
| cpu1_arrival_verified | false (no start attempted) |
| requests_completed | 0 |
| counter_progress_verified | false (not tested) |
| linux_boot / native_linux_smp | NOT RUN / NOT RUN |
| controller_elapsed_seconds | 0.781 |
| supervisor controller_exit / deadline / elapsed | 1 / false / 1.192 s |

Private durable receipt contains three records, all with no explicit mutation
intent. Only final schema-reviewed JSON is published. No target RAM range,
address/base, timer value, ADT, serial/UUID, USB path or raw console is included.
The source's range assumption and pinned BootArgs parser need offline review;
the saved evidence cannot distinguish the failing numeric component without
additional separately authorized observation. Do not invent actual bounds,
blindly relax the guard or infer a secondary/hardware fault from this refusal.

## Return and handoff

The human was instructed to power off and choose Macintosh HD immediately on
STOP, before saved-result inspection. No target cleanup/rollback, extra USB
probe, shell, CPU stop, reconnect or second command. Serial was closed by the
controller. Return confirmation recorded **20:16:42.185 UTC / 4:16:42 PM Eastern**,
**+57.883 s from command start**; within the human 90 s bound. This is a confirmation
interval including controller/UI overhead, not an OS boot or CPU-start benchmark.
Only the owned bounded caffeine assertion was stopped afterward. No live
controller, reader, SSH or relay remains. No local parsing/source repair occurred.

Existing macOS, installed entry/m1n1, security/default/volume settings and firmware
were untouched. Routine policy/default rechecks remained waived; original Full,
lab Permissive and Macintosh HD default remain last reported, not reverified.
No new image transfer, frequency change, secondary initialization, module,
Linux or renderer experiment occurred. The broader 31B scope was write-capable,
but this attempt stopped before its first explicit mutation; ordinary preflight
proxy diagnostics are not a claim that all internal bootloader RAM stayed static.

**M5 next: review the RAM-bound assumption and pinned boot-args interpretation
offline, add a representative regression fixture and select a separately
reviewed observation/fix.** Preserve all current once/consumed receipts; no reuse
or deletion to obtain another 31B run. CPU1 entry remains unobserved. Old copy31
and rebuilt-image candidate remain held; Linux two-core DT/spin-table handoff,
timer IRQ/IPI/coherence and renderer comparison need later entry evidence.
The source-pinned checklist/current pointer remain frozen for provenance; this
result and current coordination supersede their pre-execution readiness text.

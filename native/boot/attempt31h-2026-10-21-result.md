# Attempt 31H — reset-format refusal before mutations; normal return

**Observed, 2026-10-21 Eastern:** one authorized supervised 31H session returned
**STOP / `preflight` / `reset_format_requires_review`**. The two existing reset
mirror reads completed with immediate zero exception-count acknowledgements,
**mirrors equal**, no observer error. Each matches the image-base address field
but has an unexplained high field. The strict preflight refused to proceed.

**0 mutation intents, 0 CPU1 start stores attempted/acknowledged.** No recorder
publication, PS observations, added core-state reads or CPU1 timer callbacks.
**Linux boot/native Linux SMP NOT RUN; CPU1 entry unverified.**

Controller/supervisor exits **1 / 1**, elapsed **2.045 / 2.457 s**. No supervisor
deadline. Human confirmed usual Macintosh HD return at **+37.692 s**, within
90 s. **31H is consumed; no retry, reconnect, rollback or further target command.**

Sanitized final outputs:
[controller](attempt31h-controller-2026-10-21.json),
[supervisor](attempt31h-supervisor-2026-10-21.json).
Only exact reviewed final schemas are copied; private receipts, stderr, ADT,
full register words, addresses and identifiers remain under ignored build.

## Provenance and offline readiness

M5 handoff: `c89faf74a32ece167b878db2439ee8971c325ef2`.
Published readiness/execution: `1910070e21987fc0e291522897edc13c1a7e34be`.
[Independent M1 intake](attempt31h-m1-offline-2026-10-21.md): **186 pins,
344 test methods PASS**, no skips or source fixes. Both documented offline
commands exit0; additional retained-package intake verifies all13 files.
Symbol mode `reviewed_layout_only`; **full-symbol checks NOT RUN on M1**.
The separate M5 VM/full-symbol/firmware work was not independently rerun here.

Source manifest SHA-256:
`00fefcb2c61fc2fa42de6afd1ce26b28e13d9897e065c4694518c3ed9defc155`.
Retained 3,932,160-byte boot021 image:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Clean client remains `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
Existing boot042 package, recorder/helper bytes and installed entry unchanged.
Prior31B–31G evidence digests remain unchanged. No source/guard was changed to
pass the live check; all186 source pins were checked before execution/afterward.

After readiness publication, human explicitly authorized **“Start 31H; all
confirmed”**: fresh lab proxy, direct cable, powered Macs, M1 awake/unlocked/
open lid without unresolved panic/USB fault, independent90s timer ready. Those
preparation facts are human-reported. Timer cue immediately preceded the single
fixed supervisor with `--confirm START-CPU1-J716C-31H`.

Command wrapper start: **2026-10-22 01:43:22.957 UTC / 2026-10-21 9:43:22 PM
Eastern**. No preliminary live connection or separate target check was run.

## Reset observation and refused gate

Both rows were committed only after their existing read's immediate
exception-count acknowledgement returned integer zero. Exactly **2 read
attempts / 2 returns / 2 guard checks / 2 validated rows**. Observation state
`complete`, pending CPU null, mirrors_equal true, error null.

| Reviewed classification | CPU0 | CPU1 |
|---|---|---|
| Legacy page field matches vectors | true | true |
| Legacy bit0 lock classifier | true | true |
| Legacy unknown low bits11:1 | zero | zero |
| Bit11 set | false | false |
| Upper bits63:48 present | true | true |
| Firmware bits41:11 relation | image_base | image_base |
| Firmware outside low bits10:1 | zero | zero |
| Firmware outside high bits63:42 | nonzero | nonzero |
| Subfield bits47:42 | zero | zero |

The strict gate requires equal mirrors, firmware field=image_base, low10:1 zero
and high63:42 zero. The **high63:42 condition failed** on each row;
`reset_format_gate_passed:false`. No raw value or particular high-bit pattern
is retained in the public schema. Bit0 is the inherited classification label;
it is not independent proof of a t6050 lock mechanism.

**Confirmed:** the existing classifier's image-base relation coexists with an
unexplained upper field on this session. **Unknown:** high-field semantics,
exact entry offset and effective reset route. Matching mirror fields do not
prove instruction fetch/PC, correct reset ownership or a usable cold-entry
hook. This outcome does not establish that a configuration is faulty, or that
ignoring the upper field would be valid. No additional RVBAR read was added.

## Other gates and stages not reached

| Evidence | Saved result |
|---|---|
| RAM predicates / BootArgs revision | 11 true / 3 |
| Direct USB proxy / expected-or-zero UART bases | true / true |
| Initially enabled diagnostic UART count | 2 |
| Live ADT binding / all18 topology routes | true / true |
| Bound PS width / CPU IDs | 32 bits / 0 and1 |
| CPU1 startup mapping unchanged | true |
| CPU0/code/PS/core-state permission results | empty; stages not reached |
| Recorder body/hook/whole-text publication | empty; not reached |
| Recorder observation / reset-spin observation | empty / not_sampled |
| Recorder reads / arrival samples | 0 / 0 |
| PS observations / core-state observations | empty / empty; NOT RUN |
| Explicit mutation intentions | 0 |
| CPU1 starts attempted / acknowledged | 0 / 0 |
| CPU1 arrival / counter progress / final park verified | false / false / false |
| Requests planned / completed / round trips | 8 / 0 / empty |
| Terminal observation error | null |
| Controller / supervisor reason | reset_format_requires_review / controller_exited |
| Supervisor started / deadline | true / false |
| Linux boot / native Linux SMP | NOT RUN / NOT RUN |

Preflight refusal occurred before UART-zero publication, RAM helper upload,
permission probes or recorder publication. Empty stage objects mean **not
reached**, not failed accesses or zero-valued hardware observations. There is
no added-register accessibility or low-byte result to interpret from31H. No
CPU1 entry/arrival timeout occurred: the run stopped earlier at the format gate.

Topology preserves18 cores,12 Performance (ADT M) plus6 Super (ADT P), three
clusters of six. CPU1 remains the same-cluster Performance target. Later-cluster
legacy-mask mismatch IDs6–17 are structural metadata, not later-core activity.
Linux scheduler capacity remains uncalibrated/all-core operation NOT RUN.
Live binding/table validation is not an execution or access-safety guarantee.

Private consumed journal: **14 complete records**, including reservation and
partial/final state. Mutation count is the controller's explicit intent count,
not a count of diagnostic read/exception-ack transactions. Durations include
USB/Python/host/journaling overhead and provide no CPU performance measurement.

## Return and next M5 work

Immediately on the supervisor outcome, human was instructed to power off and
select Macintosh HD before detailed result inspection. Human confirmed the
usual desktop; return confirmation was recorded **2026-10-22 01:44:00.649 UTC /
2026-10-21 9:44:00 PM Eastern**, **+37.692 s** after wrapper start. This is the
recorded confirmation interval, not a precise power-off or macOS boot duration.
No target command followed supervisor termination. The owned bounded caffeine
process had already exited; no process was signaled during return bookkeeping.
No helper panic/USB fault or return problem was reported by the human.

Routine policy checks remain waived; original Full/lab Permissive and Macintosh
HD default remain last reported, not freshly verified. No install, volume,
security/default/firmware change, image/root transfer, Linux launch or extra
core start. Installed boot021/client/macOS/settings remain intact.

M5 owns the next offline interpretation under the plan's **unexplained-fields**
outcome: trace the exact firmware ownership/entry path and high-field format
before proposing another separately reviewed campaign. Preserve consumed31H
sources/receipts and frozen navigation. Do not relax the gate, select another
hook, issue extra reads/writes or retry automatically. CPU1 execution/reset
release, all-core Linux, renderer performance and energy parity remain unproven.
Frozen pre-execution NOT RUN text is historical; this report supersedes it for
the consumed31H session only.

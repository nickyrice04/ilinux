# Attempt 31N — independent M1 offline readiness

**OFFLINE READY, 2026-10-22 Eastern. Native31N and Linux SMP NOT RUN;
CPU1 execution remains unverified.** Main fast-forwarded cleanly from
`0a2590b` to release `adc9542566e595354216b474532ea9ddbf5fa6f3`.
No local change was discarded. Every consumed receipt remains intact.

## Verification

Both documented offline commands exit **0**, without skips or repairs. Intake:
`OFFLINE_CHECKS_PASS_AWAIT_HUMAN_START`, **330 pins / 932 methods PASS**,
hardware_operations=0, restart_ready=false. Packaged controller output exactly:
`OFFLINE PASS: 31N source/image verified; no discovery or USB open; restart_ready=false`.
Direct intake uses Python3.13.5 and **reviewed_layout_only** mode.

**Full-symbol checks NOT RUN on M1**, exact symbols not supplied. The23-method
full-symbol suite is not selected in this documented mode, rather than skipped.
M5's955 full-symbol VM methods,51 actual-client synthetic scenarios and independent
GNU44-byte assembly comparison remain separate offline evidence, not rerun on M1.
The first two VM runs failed before full intakes and are not relabeled passes;
the corrected integer-subclass contract passed the final VM073 release run.
The earlier nine-method/pending-integration research paragraph is historical.

| Selected coverage | Methods PASS |
|---|---:|
| Inherited47 suites from31M | 870 |
| Fixed leaf/plan contracts and independent narrow decode | 10 |
| Prior synthetic inter-store gap | 1 |
| Controller/completion/phase adapter | 19 |
| Intake/source closure | 9 |
| Supervisor/receipts/deadlines | 23 |
| Total:52 suites | 932 |

Exact-image cold/control audits, default controller source/image/helper checks
and modeled entry contracts also passed. New tests cover every fixed-word
mutation and interruption prefix, valid parsed-integer subclasses without
coercion, padding/publication/permission refusals, partial pair completion,
lost/bad return, guard fault, intent/completion journal failures, all mutation
failure prefixes, positive/error observer stops and actual sampling phases.
These are software contracts, not Apple firmware, cache or timing emulation.

Intake81.645s; packaged default controller0.618s; retained-package check0.349s.
No production/test source or fixture was repaired on M1.

## Inputs and preservation

- 330-file manifest SHA-256:
  `00dea9b06831a0e3d57fff4d2f92103ea469c887779ae5bce661bf0e0523e70a`.
- Frozen M306/L281/K254/J226/I202/H186/host6 closures independently PASS unchanged.
- Retained boot021 image:3,932,160 bytes,
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
- Clean client `57a9339ffd1876e78297b17d34dece8cff8fa1ba` retained.
- Retained13-file package PASS, manifest
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
- Exact original44-byte leaf:
  `8c591d55d1d92a6b466a33a9cc5af69f869504df066728862119c5f39037bf19`.
- Before/after digests of prior attempt31 receipts and offline evidence match.
  No consumed file was cleared, renamed, overwritten or forced. All six new31N
  live-use files remain absent. Private readiness, logs and digest snapshots stay
  ignored under `build/native-intake/attempt31n/`.

**0 real discovery queries, device opens, target requests or native invocations.**
No M1 restart, VM/REA run, image transfer, installation or settings change.

## Independent review

Reviewed the plan/assembly/audit, full new controller and phase adapter, tests,
release review/validation and all three research notes. Supervisor runtime is
identical after namespace/static-closure normalization; the live wrapper is
identical after namespace normalization. No code-level blocker found for this
bounded test; the hardware timing hypothesis remains unproven.

The44-byte leaf at helper+0x240 occupies a separate64-byte line inside the owned
16KiB allocation. First/last translations, explicit line initialization,
code/padding readback, PoC cleaning, RX instruction publication and readback
must pass. The leaf has no arguments, stack/memory reads, system-register write
or cache operation. It issues only the same two aligned32-bit writes of2 to the
same existing addresses in order, with DSB SY before/between/after. It does not
mask interrupts, make the pair atomic or guarantee an inter-store deadline.
CPU1 prefixes and paired cached/maintained observers remain unchanged.

Durable pair/mutation intents and every freshness/stack/target check precede
dispatch. There is no observation or host transaction between the stores, hence
**no between-store abort opportunity**. A matching return token is validated
before the diagnostic target query; only that token plus clean diagnostics
confirm the pair. Missing/bad return or diagnostic failure preserves zero/one/
two possible stores, acknowledges none and allows no follow-up query/retry.
Confirmed completion remains confirmed if a subsequent journal write fails.
Acknowledgments never prove CPU1 instruction execution.

The adapter reports three actual phases: before_start, after_second_start, final,
with at most6 reads per tracker. after_first_start is explicitly omitted, never
filled with zeros. Final sampling is only on natural arrival timeout. Every
positive/partial/error stops when observed. Only committed expected identity
proves prefix execution; negatives cannot exclude it. No callbacks, extra core,
new MMIO/reset address, firmware replay or Linux continuation follows.

## Next single session

Publish readiness, then await the human's fresh start with M5 Running proxy,
powered Macs, known-good direct cable, healthy awake/unlocked/open-lid M1 and
independent90-second timer. No routine M1 reboot or repeated policy check.
Original Full/lab Permissive/Macintosh HD default remain last reported, not
freshly verified. Installed boot021, retained boot042 and client stay unchanged.

One supervisor includes bounded discovery and one serial attempt. No preliminary
handshake, old runner, fallback/reconnect or retry. Child60s/supervisor65s,
serial2s/arrival3s/control2s and human90s bounds remain. Operation-bracketed
arrival/control budgets are not hard per-RPC interrupts. Any result, lost proxy
or timer requires immediate M5 power-off and Macintosh HD return before detailed
inspection. No extra read, cleanup RPC or automatic next operation.
**Native31N/Linux SMP NOT RUN, invocations0; CPU1/performance parity unverified.**

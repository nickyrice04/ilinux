# 31L Normal-memory release — independent M1 intake

**OFFLINE READY,2026-10-22 Eastern. Native31L/Linux SMP NOT RUN; CPU1 unverified.**
Pulled `11cc2afc973838a6426f7882db6b2924893e85ae` by `git pull --ff-only`.
The previous uncommitted first31L offline review overlapped status files; a
recoverable snapshot/Git stash retained all six original files before pull.
Its exact report and status sections were carried forward without applying
conflicting changes or touching native receipts.

That [earlier24-test analysis](attempt31l-m1-offline-2026-10-22.md) on `e1cdf7a`
is separate from this new physical-release intake. Its historical hold/no-push
wording describes the earlier handoff. It is published with this readiness for
continuity; the exact report bytes remain unchanged. The new release supersedes
the earlier analysis-only hold after this intake and a fresh human start.

## Verification

Both documented offline commands exit **0**; intake
OFFLINE_CHECKS_PASS_AWAIT_HUMAN_START: **281 source pins,796 methods PASS,
0 skips,0 repairs**,hardware_operations0,restart_ready false (intentional).
Packaged default controller output exactly:
`OFFLINE PASS: 31L source/image verified; no discovery or USB open; restart_ready=false`.

- Source manifest SHA-256:
  `c7cc43434da7fb386e2486691a0a639053751396760624a6827d8588b5a9d26f`.
- Frozen K254/J226/I202/host-only6 pins independently PASS unchanged.
- Existing3,932,160-byte boot021 image
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
- Clean client `57a9339ffd1876e78297b17d34dece8cff8fa1ba` retained.
- Additional retained-package verification exit0,all13 files,manifest
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
- Mode **reviewed_layout_only**,Python3.13.5 for the direct intake. **Full-symbol
  checks NOT RUN on M1**,no symbol file supplied. The23-method full-symbol suite
  is not selected in this documented mode,not a unittest skip. Candidate exact-
  image checks ran without fresh symbol validation. M5's819 full-symbol VM
  methods,60 actual-client synthetic scenarios and10 independent assembler
  comparisons remain separate offline evidence. M1 did not rerun that VM,
  assembly or REA work. M5's final integration was completed/reviewed by its
  root; preliminary independent reviews are not relabeled final integration.

| Selected coverage | Methods PASS |
|---|---:|
| Inherited37 suites from31K | 716 |
| Exact Normal-first candidate/model | 24 |
| Normal observer and returning CPU0 control | 16 |
| New controller lifecycle/stop cases | 8 |
| Intake/source closure | 9 |
| Supervisor/receipts/deadlines | 23 |
| Total:42 suites | 796 |

Cold-entry/CPU0-control exact-image audits and new controller source/image
check also PASS. New regressions cover partial/uncommitted identities,fault
prefixes,no callback after any positive or Device-only arrival,strict mappings,
source closure and sanitized diagnostics. Synthetic tests do not emulate Apple
firmware or prove CPU1 entry/coherency/access safety. No source repair on M1.

Reviewed the two new research findings,candidate audit/model/assembly/encoder,
Normal observer/control,controller,supervisor and release review/validation.
Supervisor runtime is unchanged after namespace/static-closure normalization.
No code-level blocker was identified for the documented bounded experiment;
unknown incoming CPU1 mapping/fetch/store visibility and negative-result limits
remain material. No firmware cleanup/cluster-restoration sequence is replayed.

## Preservation and zero live operations

Consumed31B–31K receipts,retained J/K evidence,separate host-only31J and earlier
31L offline review keep identical before/after digests. All six new31L live-use
files remain absent. Private logs/readiness/digest snapshots stay under ignored
`build/native-intake/attempt31l/`; the earlier analysis keeps its separate folder.
No receipt was cleared,renamed,forced or overwritten. The recoverable notes
stash is retained. Only public original notes and sanitized readiness are pushed.

**0 real registry queries,serial/device opens,target requests or native
invocations.** No VM,host install,image transfer,Mac restart or settings change.
Bounded owned caffeine assertion active,no competing reader. Installed boot021,
retained package and client pin intact.

## Normal-record and stop-semantics review

The already owned16KiB helper allocation provides separate64-byte Normal records
on128-byte boundaries and a distinct CPU0 control. CPU0 Normal write-back/
outer-shareable identity read/write probes,initialization/cache publication,
known-zero freshness,returning control and instruction/full-text readback are
prerequisites. No remap,new allocation,arbitrary address or installed-image write.
Both CPU0 controls are bounded2s and restore only on their successful path;
faults authorize no cleanup. No record cache maintenance after a start intent.

Two60-byte original prefixes materialize the full record address,store phase1
before MRS,commit low24 MPIDR at phase2,then branch toward the existing Device
recorders. They preserve x0,SP,LR,NZCV. Any visible Normal value—including an
uncommitted identity—or error stops with acquired counts. Only committed expected
CPU1 identity proves the prefix executed and became visible. It does not prove
reset provenance,the following branch/Device recorder,or a historical cache cause.
No post-positive Device comparison is permitted. A failed Normal store can
prevent later Device evidence; CPU0 cached polling can miss uncoherent stores.
Negative channels cannot exclude execution or select a startup fix.

**No callbacks authorized**,even after complete Device-only arrival. Expected
positives deliberately return STOP/exit1 and are not failures merely because of
exit status. The inherited cold terminal spin stays externally bounded,not a
verified architectural park. No new MMIO/system-register/reset/clock operation.

## Next single session

Readiness publication precedes fresh human lab start at Running proxy,direct
known-good cable,powered Macs,healthy awake/unlocked/open-lid M1 and independent
90s timer. No routine M1 reboot or policy recheck; original Full/lab Permissive/
Macintosh HD default remain last reported,not freshly verified.

One supervisor includes existing bounded discovery,strict identity/path/source
gates,separate connection/native journals and one serial attempt. No preliminary
checker/handshake. Child60s,supervisor65s plus bounded termination,serial2s,
arrival3s,controls2s each. No extended human window. Any result/lost proxy/timer
requires immediate power-off and Macintosh HD return,no extra target read,
retry,reconnect,cleanup,cable troubleshooting,Linux or extra core.
**Native31L/Linux SMP NOT RUN; CPU1/performance parity unverified; invocations0.**

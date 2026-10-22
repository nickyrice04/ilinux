# 31L — independent M1 offline verification

**PASS,2026-10-22 Eastern; native31L HOLD/NOT RUN.** Pulled main by
`git pull --ff-only` from a clean worktree to
`e1cdf7a5ea285e34b09824e431cca5bea6a65242`.

Both documented commands used the retained boot021 image and the published31K
controller JSON: **exit0,24 test methods PASS,0 skips**,checker
**OFFLINE_ENTRY_CONTRACT_PASS**. Tool version **Python3.13.5**. Artifact/report
checks were selected; no source repairs or extra test runs. Mode
**reviewed_layout_only**; **full-symbol validation NOT RUN on M1**,no symbols
supplied. Image-only mode omits the symbol-corruption branch without skipping
the containing method. M5's full-symbol/VM/mutant validation remains separate.

## Bound inputs and preservation

- Retained boot021 image SHA-256:
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
- Published31K report SHA-256:
  `53462743e99a935e8374d4ea6add4201bacbe4de555abb94537e94cc3b7e7861`.
- Checker source SHA-256:
  `416a1d4c8356ad21499a7ec025c57127365356e31a60baa5d8f901765920a8b6`.
- All3 released checker/test/README hashes match validation.json.
  Frozen K254/J226/I202/host6 manifests and every file digest match.
- Prior consumed31B–31K receipts plus retained J/K and host-only evidence
  have identical before/after digests. Nothing reset,deleted,renamed or
  overwritten. No native31L directory or receipt was created.

Private test logs,checker result,verification metadata and preservation
snapshots are retained under ignored `build/native-intake/attempt31l-offline/`.
No raw diagnostics,absolute local paths or identifiers are included here.

## Checker result and limits

| Result | Recorded value |
|---|---|
| Checker | OFFLINE_ENTRY_CONTRACT_PASS |
| Symbol mode | reviewed_layout_only |
| Synthetic address cases | 56 |
| Supplied translation cases | 112 |
| Nonidentity/MMU-off cases reaching a different record | 42 |
| Compatible injected hypotheses | 8 |
| Native next attempt ready / hardware emulator | false /false |
| CPU1 effective entry | UNKNOWN |

Canonical checker output matches the released contract-results.json after
removing only the explicit symbol-mode/digest fields. The actual31K canonical
report binding remains intact. The cases test software arithmetic and supplied
premises; they are not measurements of CPU1's context or cache behavior.
CPU0 positive control and phase-zero recorder evidence still do not select a
single cause or exclude either candidate path. No new hardware operation is
qualified by this PASS.

Checks ran under a bounded owned caffeine assertion,released afterward; all
temporary analysis files stayed in ignored workspace build. **0 real registry
queries,device opens,target requests,native invocations or restarts.** No proxy
client/old supervisor run,VM,install,image transfer,macOS/volume/security/default
change or global sleep-setting change.

**CPU1 execution unverified; Linux SMP NOT RUN; native31L HOLD/NOT RUN.**
M5 owns further evidence-backed discriminator design. Local report/status notes
only: no commit or push made in this handoff.

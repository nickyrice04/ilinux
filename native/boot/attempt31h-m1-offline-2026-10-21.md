# Attempt 31H — independent M1 offline readiness

**OFFLINE READY, 2026-10-21. Native 31H/Linux SMP NOT RUN; CPU1 entry unverified.**

M1 pulled `c89faf74a32ece167b878db2439ee8971c325ef2` with `git pull --ff-only`
from a clean worktree. Independent intake returned
`OFFLINE_CHECKS_PASS_AWAIT_HUMAN_START`: **186 pins, 344 methods PASS, no
skips/fixes, hardware_operations 0, restart_ready false** (expected).

## Verified inputs

- Source manifest SHA-256:
  `00fefcb2c61fc2fa42de6afd1ce26b28e13d9897e065c4694518c3ed9defc155`.
- Both documented offline commands exit **0**. Default controller prints exactly
  `OFFLINE PASS: 31H source/image verified; no USB or CPU start; restart_ready=false`.
- Clean client stays at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
- Additional retained-package verification exits **0**, all **13 files**, status
  `checksums_and_declared_revision_verified`; package manifest
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
- Existing boot021 image: **3,932,160 bytes**,
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
- Retained 168-byte recorder:
  `52f9d1b312725cdc9261e0fbf1c31991e9078a663827734b9ba54c9d171106bc`;
  retained 16-byte read helper:
  `c2316a02024b7ce2dfed2d4640c5c57abdce4bab81c9c4380a2d8cb3bbcb4dcd`.

## Test results and limits

| Selected suites | Methods PASS |
|---|---:|
| Retained 31G controller / supervisor | 26 / 15 |
| PS plan / tracker / publication audit / topology | 11 / 5 / 8 / 7 |
| Retained permissions / telemetry / campaign | 11 / 29 / 21 |
| Classifier / audit / held-stack collector / interpreter | 6 / 4 / 18 / 22 |
| Retained intake / vector permissions / topology | 6 / 11 / 32 |
| 31H controller / reset audit / observer / core-state tracker | 45 / 8 / 21 / 14 |
| 31H intake / supervisor | 6 / 18 |

All **22 selected suites, 344 methods PASS**. Native controller offline
source/image/helper check also PASS. Symbol mode is `reviewed_layout_only`;
**full-symbol checks NOT RUN: symbol file not supplied**. The 23-method
full-symbol suite is not selected in this documented mode, not a skipped test.
M5's VM066/full-symbol and 24 actual pinned-client synthetic cases remain
separate evidence; M1 did not rerun that VM or firmware analysis. Synthetic
models do not validate reset, caches, timing or register accessibility.

The controller, supervisor, observer, tracker, reset findings, plan, reviews
and validation were reviewed. No production/test source changed. No physical
USB opened, target helper executed, VM launched, host install or image transfer.
Private logs/receipts remain in ignored `build/native-intake/attempt31h/`.
No competing reader found; a bounded owned caffeine assertion is active.

All five real 31H live-use files remain absent. Prior 31B–31G live evidence
has identical digests before/after intake; nothing deleted, reset or replaced.
Installed boot021, verified package, client and all settings are unchanged.

## Next single session

Follow `tools/m1n1-client/attempt31h-instructions.md`: publish readiness, then
await the fresh human start of the existing lab proxy with direct cable,
powered awake/unlocked/open-lid M1 and an independent **90 s** timer.
Healthy M1 needs no routine reboot; routine policy checks remain waived.
Original Full/lab Permissive/Macintosh HD default remain last reported,
not freshly verified.

31H preserves the same two CPU1 starts, vector recorder and arrival gates.
Exactly the existing two reset-mirror reads gain more precise classification;
unexplained formats stop before mutations. At most eight existing PS reads
plus eight exploratory fixed 32-bit core-state reads, ordered into four pairs.
Baseline is guarded, later reads use the unchanged fixed helper. New pairs
have a one-second soft deadline; final sampling only on natural arrival expiry
or verified park. First fault/deadline stops; partial evidence is retained.
Never-started-core access and t6050 register semantics are unverified; guards
cannot guarantee containment of asynchronous faults or a bus hang. Published
low bytes are opaque and do not prove execution, running state or reset release.
Effective reset destination and PC remain unknown.

Controller 60 s, supervisor 65 s plus bounded termination, serial 2 s, arrival
3 s, conditional callback 1 s. Only complete CPU1 entry permits eight callbacks
and final park. On any result/timer immediately power off and return to
Macintosh HD; no retry/reconnect, extra core, rollback or target cleanup.
No new RVBAR/PS/stop/security write, installed-image change or Linux command.
**Live attempts 0; native 31H/Linux SMP NOT RUN; CPU1 entry unverified.**

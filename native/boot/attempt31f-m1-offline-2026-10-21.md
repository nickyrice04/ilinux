# Attempt 31F — independent M1 offline readiness

**OFFLINE READY, 2026-10-21. Native 31F/Linux SMP NOT RUN; CPU1 entry unverified.**

M1 pulled **`6092b11`** with `git pull --ff-only` from a clean worktree.
Both documented offline commands exit **0**. Intake result:
`OFFLINE_CHECKS_PASS_AWAIT_HUMAN_START`, **138 source pins**, **194 methods
PASS**, no skips/fixes, **hardware_operations 0**, **restart_ready false**.
The last flag is expected: only a fresh human start authorizes the live session.

## Verified inputs and evidence limits

* All 138 source digests match. Manifest SHA-256:
  `d5de4d4ba2372ec7cf0c0d4c509f8feeea07a096fc466cf18026ac2d8c3b0161`.
* Symbol mode **`reviewed_layout_only`**; full-symbol checks **NOT RUN:
  symbol file not supplied**. The 23-method full-symbol recorder suite was
  not selected in this documented mode. M5's 217-method VM/full-symbol,
  independent assembly and real-client evidence remain separate offline facts.
* Client/default controller prints exactly
  `OFFLINE PASS: 31F source/image/helper verified; no USB, allocation or CPU start`.
  Clean client pin: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* Additional retained boot042 package intake exits 0, verifies **13 files**,
  status `checksums_and_declared_revision_verified`; manifest
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
  Existing 3,932,160-byte boot021 image:
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
* Original 168-byte recorder SHA-256:
  `52f9d1b312725cdc9261e0fbf1c31991e9078a663827734b9ba54c9d171106bc`.
  Reviewed the controller/supervisor changes, entry/startup/controller reviews
  and validation, builder, permissions, telemetry and topology scope. The
  ordinary stack and existing permission/start helpers remain unchanged.

| Selected M1 suite | Methods PASS |
|---|---:|
| Controller / supervisor | 19 / 15 |
| Frozen / vector-hook permissions | 11 / 11 |
| New telemetry / campaign replay | 29 / 21 |
| Prior classifier / static audit / held-stack observer | 6 / 4 / 18 |
| Entry interpreter / source closure / topology | 22 / 6 / 32 |

All twelve suites PASS, **194 methods total**, with no skips or source repairs.
Models and synthetic Linux sysfs fixtures do not establish native reset,
coherency, scheduling capacity or topology performance. The Linux collector
was not run on the M5; retained-DT/full-recorder checks reported by M5 remain
separate validation. No ARM64 helper executed on M1, VM started, install or
image transfer occurred. Test temporary files/logs stay under ignored build.

All five real 31F live-use files are absent before/after intake; prior
31B/31C/31D/31E evidence digests are unchanged. No receipt was deleted or reset.
No competing proxy/controller/reader found. A bounded caffeine assertion is
owned; a healthy M1 needs no routine restart.

## One next session

Publish readiness, then await the human's fresh existing M5 lab proxy session
and independent **90 s** timer. Powered, awake/unlocked/open-lid M1 and direct
USB; no unresolved helper panic/USB fault. No routine policy recheck.

31F publishes the recorder body before its four-byte loaded-RAM vector hook,
checks 16 fixed translations and both code views/whole text, then performs the
same two CPU1 startup stores. It samples after the first store and stops before
the second on progress/error. Only verified arrival and a complete expected
CPU1 record allow eight callbacks and final park. A vector marker can also be
an exception entry and is not CPU1 reset provenance. No mappings/protections,
installed boot object, frequency, extra core or Linux handoff are changed.

Controller **60 s**, supervisor **65 s** plus bounded termination, serial **2 s**,
arrival **3 s**, each conditional request **1 s**. Immediately after any result
or timer, power off and return to Macintosh HD. No retry/reconnect, code restore,
target cleanup or speculative power/RVBAR operation.

**Live attempts 0; native 31F, recorder publication, CPU1 entry and Linux SMP
NOT RUN/unverified.** Existing boot021/client/macOS/settings remain intact;
original Full/lab Permissive/Macintosh HD default are last reported, not freshly
verified. Performance, efficiency and all-core operation remain unproven.
Procedure: `tools/m1n1-client/attempt31f-instructions.md`.

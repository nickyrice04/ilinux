# Attempt 31G — independent M1 offline readiness

**OFFLINE READY, 2026-10-21. Native 31G/Linux SMP NOT RUN; CPU1 entry unverified.**

M1 pulled **`449eb6e`** with `git pull --ff-only` from a clean worktree.
Both documented commands exit **0**. Intake result:
`OFFLINE_CHECKS_PASS_AWAIT_HUMAN_START`, **166 source pins**, **232 methods
PASS**, no skips/fixes, **hardware_operations 0**, **restart_ready false**.
The last flag is expected; fresh human start follows publication.

## Verified inputs and limits

* All 166 file digests match. Manifest SHA-256:
  `a06d3c201818a046b7964147a171d1d6c50e5b4d78a47dbdcd40584b321a4532`.
* Symbol mode **`reviewed_layout_only`**; full-symbol checks **NOT RUN:
  symbol file not supplied**. The 23-method full-symbol recorder suite was
  not selected in this documented mode. M5's 255-method VM/full-symbol,
  real-parser/client, assembler and width-harness checks remain separate
  offline evidence, not native power/entry or independently rerun M1 results.
* Default controller command prints exactly
  `OFFLINE PASS: 31G source/image/helper verified; no USB, allocation or CPU start`.
  Client stays clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* Additional retained-package verification exits 0, **13 files**, status
  `checksums_and_declared_revision_verified`; package manifest
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
  Existing 3,932,160-byte boot021 image:
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
* Retained recorder: 168 bytes,
  `52f9d1b312725cdc9261e0fbf1c31991e9078a663827734b9ba54c9d171106bc`.
  New fixed-width read helper: 16 bytes,
  `c2316a02024b7ce2dfed2d4640c5c57abdce4bab81c9c4380a2d8cb3bbcb4dcd`.
  Reviewed controller/supervisor changes, live binding, plan/tracker, helper,
  topology planner, reviews/validation and reset-routing findings. No new
  power address/mask is selected for CPU1; no extra core is authorized.

| Selected suites | Methods PASS |
|---|---:|
| Controller / supervisor | 26 / 15 |
| PS plan / partial-preserving tracker / publication audit | 11 / 5 / 8 |
| New topology / retained topology | 7 / 32 |
| Frozen / vector-hook permissions | 11 / 11 |
| Telemetry / campaign / classifier | 29 / 21 / 6 |
| Static audit / held-stack observer / instruction interpreter / source closure | 4 / 18 / 22 / 6 |

All sixteen selected suites PASS: **232 methods**, no skips/failures/repairs.
Synthetic models and topology fixtures are not Apple reset/power/cache
emulation. No physical USB opened, ARM64 helper executed on M1, VM launched,
host install or image transfer. Logs/test temporary data stay under ignored
build. A bounded caffeine assertion is owned; no competing reader was found.

All five real 31G live-use files are absent before/after intake. Prior
31B/31C/31D/31E/31F evidence digests stay unchanged; no evidence was deleted,
edited or reset. Existing entry/client/macOS/settings are unchanged.

## Next single session

Await fresh human M5 lab proxy start, healthy powered awake/unlocked/open-lid
M1, direct cable and an independent **90 s** timer. No routine M1 reboot or
policy recheck. Existing boot021/Boot Lab and verified package only.

31G retains recorder publication/permission gates and both CPU1 startup stores.
It binds CPU0/CPU1 PS addresses and all 18 routes to live ADT, installs the
fixed 32-bit read helper and checks two additional translations. At most
**8 PS reads**: baseline pair, pair after each acknowledged start and a final
pair only on natural arrival expiry or verified park. Guarded baseline precedes
startup; later reads are guard-free and fixed-width. Every read intent and
partial decoded result is retained; first fault stops. An in-flight observation
deadline is distinct from natural expiry and permits no trailing pair.

No PS control write, other-core start, guessed power/RVBAR operation, mapping/
protection change or Linux continuation. Legacy-active PS values would not
prove reset release, CPU instructions or effective reset destination. Only
verified entry permits eight callbacks and final park.

Controller 60 s, supervisor 65 s plus bounded termination, serial 2 s, arrival
3 s, each callback 1 s. Immediately on any outcome/timer, power off and return
to Macintosh HD. No retry/reconnect, restore or target cleanup.

**Live attempts 0; native 31G, PS observations, CPU1 entry and Linux SMP NOT
RUN/unverified.** Original Full/lab Permissive/Macintosh HD default remain
last reported, not reverified. Installed boot021/client/macOS/settings intact;
performance, efficiency and all-core operation remain unproven. Procedure:
`tools/m1n1-client/attempt31g-instructions.md`.

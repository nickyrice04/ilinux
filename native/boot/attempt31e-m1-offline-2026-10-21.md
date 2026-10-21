# Attempt 31E — independent M1 offline readiness

**OFFLINE READY, 2026-10-21. Native 31E and Linux SMP NOT RUN; CPU1 entry unverified.**

M1 pulled **`a79a275`** with `git pull --ff-only`, from a clean worktree.
Both documented offline commands exited **0**. The intake returned
`OFFLINE_CHECKS_PASS_AWAIT_HUMAN_START`, **112 source pins**, **141 Python
methods PASS**, no skips/fixes, `hardware_operations:0`, `restart_ready:false`.
The latter is the expected separation between offline readiness and the
required fresh human start. No live supervisor or target connection ran.

## Inputs and checks

* Source-manifest SHA-256:
  `5be6295c5f523f58e771d5e896729b909ac2593ff67defdb46e843fc4a66d17a`.
  All 112 file digests independently match before intake and in the runner.
* Symbol mode: **`reviewed_layout_only`**. Exact image/layout checks PASS;
  **full-symbol checks NOT RUN: symbol file not supplied**. The two full-symbol
  suites (40 methods) were not selected in this documented M1 mode. This is
  an explicit verification limit, not a skipped or failed test. M5's 181-method
  VM/full-symbol and independent assembler evidence was reviewed separately.
* Pinned-client/default controller command exits 0 and prints exactly
  `OFFLINE PASS: 31E source/image/helper verified; no USB, allocation or CPU start`.
  Client remains clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* An additional retained-package verification exits 0: **13 files**, status
  `checksums_and_declared_revision_verified`; manifest
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
  Existing 3,932,160-byte boot021 image:
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
* Reviewed the bounded controller/supervisor, publication and controller
  reviews/validation, permission/observation/telemetry code, original recorder
  and source-pinned intake. Existing controllers remain frozen. No new image,
  third-party install, VM launch or ARM64 helper execution on M1.

| M1 suite | Methods PASS |
|---|---:|
| Native controller model | 16 |
| Independent supervisor | 15 |
| Permissions | 11 |
| Recorder telemetry | 22 |
| Campaign replay | 21 |
| Entry classifier | 6 |
| Static entry audit | 4 |
| Held-stack observer | 18 |
| Entry instruction interpreter | 22 |
| Intake source closure | 6 |

All ten selected suites PASS, totaling **141** methods. The instruction model
reports eight synthetic scenarios, hardware model false and native execution
NOT RUN. It is not CPU1 execution evidence. Supervisor tests terminate only
their own dummy children. Test temporary files/logs remain under ignored build.

All five live-use files are absent before/after intake: `supervisor-once.json`,
`consumed.jsonl`, `controller.json`, `controller.stderr`, `supervisor-result.json`.
Prior 31B/31C/31D evidence digests are unchanged; no evidence was deleted,
edited or reset. No competing proxy/controller/reader was found. A bounded
caffeine assertion is owned; a healthy M1 needs no routine restart.

## One authorized next session

Publish this report before the human's fresh M5 lab start. Keep the powered M1
awake/unlocked/lid open, direct USB attached, no unresolved helper panic/USB
fault, and an independent **90 s** return timer ready. Existing boot021/Boot Lab
only. No further policy-check loop or M1 restart is requested.

The RAM-only experiment checks 16 CPU0 translations, publishes the original
204-byte recorder body before its four-byte hook through the existing writable
alias, verifies both address views and immutable text, and issues the same two
CPU1 startup stores with the new guard-free helper. Only verified arrival and
a complete record permit eight callbacks and the final park check. It changes
loaded RAM code, not the installed boot object, mappings or protection policy.
CPU0 readback does not prove CPU1 instruction visibility or coherency.

One fixed supervisor: controller 60 s, parent 65 s plus bounded TERM/KILL,
serial 2 s, arrival 3 s, each conditional request 1 s. On any outcome or timer,
power off and return immediately to Macintosh HD. No retry, reconnect,
restoring code, freeing target allocations, extra core or Linux continuation.
New once/consumed receipts remain immutable even on early failure.

**Live attempts 0; native 31E, recorder publication, CPU1 entry and Linux SMP
NOT RUN/unverified.** Installed boot021/client/macOS/default/security/volumes
remain unchanged. Routine rechecks stay waived; protections remain last
reported. A future recorder/callback result is not Linux SMP, timer IRQ/IPI,
coherency under load, CPU latency, stability, performance or energy parity.
Procedure: `tools/m1n1-client/attempt31e-instructions.md`.

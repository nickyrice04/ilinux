# Attempt31I — independent M1 offline readiness

**OFFLINE READY,2026-10-21 Eastern. Native31I/Linux SMP NOT RUN; CPU1 entry
unverified.** M1 pulled `89a0947d6d3d80e2e71511ff96695d9aedb3a8ad` using
`git pull --ff-only` from a clean worktree.

Both documented offline commands exit **0**. Intake result
`OFFLINE_CHECKS_PASS_AWAIT_HUMAN_START`: **202 source pins,429 methods PASS**,
no skips/fixes, hardware_operations0, restart_ready false (intentional).
Default controller prints exactly
`OFFLINE PASS: 31I source/image verified; no USB or CPU start; restart_ready=false`.

## Verified inputs and limits

- Source manifest SHA-256:
  `5c8279f96f85b424df0eaee2792a2be830a7d4604fa3e976fa3e2c3047b4a2c6`.
- All186 frozen31H pins also independently match their original manifest
  `00fefcb2c61fc2fa42de6afd1ce26b28e13d9897e065c4694518c3ed9defc155`.
- Client stays clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
- Additional retained-package verification exit0, all13 files, status
  `checksums_and_declared_revision_verified`, package manifest
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
- Existing boot021 image:3,932,160 bytes,
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
  No new image/root transfer, installation or recorder/helper bytes.
- Symbol mode **reviewed_layout_only**; **full-symbol checks NOT RUN: symbol
  file not supplied**. The23-method full-symbol suite is not selected in this
  documented mode, not a unittest skip. M5's452-method VM/full-symbol and24
  pinned-client scenarios, plus firmware-byte validation, remain separate
  evidence; M1 did not rerun the VM or analyze firmware here.

## Selected tests

| Suite | Methods PASS |
|---|---:|
| `native/boot/test_smp31g.py` | 26 |
| `kernel/experiments/smp31g-observation/test_plan.py` | 11 |
| `kernel/experiments/smp31g-observation/test_tracker.py` | 5 |
| `kernel/experiments/smp31g-publication/test_audit.py` | 8 |
| `kernel/experiments/cpu-topology31g/test_topology.py` | 7 |
| `tools/m1n1-client/test_attempt31g_supervisor.py` | 15 |
| `kernel/experiments/smp31e-entry/test_permissions.py` | 11 |
| `kernel/experiments/smp31f-entry/test_telemetry.py` | 29 |
| `tools/boot-campaign/test_campaign.py` | 21 |
| `kernel/experiments/smp31e-entry/test_observe.py` | 6 |
| `kernel/experiments/smp31e-entry/test_audit.py` | 4 |
| `kernel/experiments/smp31e-observer/test_collector.py` | 18 |
| `kernel/experiments/smp31e-emulator/test_emulate.py` | 22 |
| `tools/m1n1-client/test_attempt31g_offline.py` | 6 |
| `kernel/experiments/smp31f-entry/test_permissions.py` | 11 |
| `kernel/experiments/cpu-topology31f/test_topology.py` | 32 |
| `native/boot/test_smp31h.py` | 45 |
| `kernel/experiments/smp31h-reset-format/test_audit.py` | 8 |
| `kernel/experiments/smp31h-reset-format/test_observer.py` | 21 |
| `kernel/experiments/smp31h-reset-format/test_cpu_state.py` | 14 |
| `tools/m1n1-client/test_attempt31h_offline.py` | 6 |
| `tools/m1n1-client/test_attempt31h_supervisor.py` | 18 |
| `native/boot/test_smp31i.py` | 48 |
| `kernel/experiments/smp31i-readback/test_gate.py` | 13 |
| `tools/m1n1-client/test_attempt31i_offline.py` | 6 |
| `tools/m1n1-client/test_attempt31i_supervisor.py` | 18 |

**26 suites,429 methods PASS**. Native controller offline source/image/helper
check also PASS. New regressions cover the actual published31H observation,
all65,536 synthetic upper-field patterns, strict malformed/known-field rejection,
H/I success/timeout target-trace parity, inherited fault/deadline stops, separate
live dispatch/receipts and complete source closure. Synthetic tests are not
hardware reset/cache/MMIO validation and do not establish access safety.

Reviewed research outcome table, controller/gate/inheritance and supervisor,
source closure, reviews/validation and tests. Only original documentation is
added; no production/test source repair. No USB opened, hardware operation,
VM, host install or live31I reservation. Private logs, test temporary data and
readiness stay under ignored `build/native-intake/attempt31i/`. Bounded owned
caffeine assertion active; no competing reader found.

All five real31I live-use files absent before/after intake. Prior31B–31H live
receipt digests unchanged, none reset or overwritten. Installed boot021,
verified boot042 package, client and all settings intact.

## Next single session

Publish readiness, then await fresh human start per
`tools/m1n1-client/attempt31i-instructions.md`. Existing lab proxy/direct cable,
powered Macs, healthy awake/unlocked/open-lid M1, independent90s timer.
Healthy M1 needs no routine restart; routine policy checks remain waived.
Original Full/lab Permissive/Macintosh HD default remain last reported,
not freshly verified.

The firmware-backed readback correction accepts matching uninterpreted
upper63:48 fields while preserving full-word mirror equality and all address,
bit0,bit11,low10:1/47:42 and immediate guard checks. It adds no target operation
to31H and proves no effective entry/reset release. Existing two CPU1 starts,
vector recorder and at most8 PS plus8 opaque fixed32-bit core-state reads stay
bounded. Core-state t6050 semantics/access remain unverified; zero/nonzero or
change does not prove execution/reset/running state or PC. First fault/deadline
stops with retained partial evidence; no improvised accesses or recovery.

Controller60s, supervisor65s plus bounded termination, serial2s, arrival3s,
conditional callbacks1s, core-state pairs1s soft deadline. Only verified complete
CPU1 arrival/identity permits8 callbacks and final park. On any result/timer,
immediately power off and return to Macintosh HD, no retry/reconnect/rollback
or target cleanup. No new power/RVBAR/stop/security write, extra core, settings
change or Linux continuation. **Native31I/Linux SMP NOT RUN; CPU1 entry
unverified; live attempts0.**

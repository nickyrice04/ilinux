# Attempt 31M — independent M1 offline readiness

**OFFLINE READY, 2026-10-22 Eastern. Native31M and Linux SMP NOT RUN;
CPU1 execution remains unverified.** Main fast-forwarded cleanly from
`eb1ac1c` to release `24aa8eba5fe39b9587dd3a27d55d56159e9d8077`.
All consumed receipts and prior offline evidence remain intact.

## Independent verification

Both documented commands exited **0**, without skips or repairs. Direct intake
reports `OFFLINE_CHECKS_PASS_AWAIT_HUMAN_START`, **306 pins / 870 methods PASS**,
hardware_operations=0 and restart_ready=false. Packaged controller output is
exactly `OFFLINE PASS: 31M source/image verified; no discovery or USB open; restart_ready=false`.
Direct intake used Python3.13.5, mode **reviewed_layout_only**.

**Full-symbol checks NOT RUN on M1:** the exact symbol file was not supplied.
The 23-method full-symbol suite was not selected, rather than skipped. M5's
893 full-symbol VM methods, 46 synthetic actual-client scenarios, independent
CTR-leaf assembly comparison and REA work remain separate offline evidence;
M1 did not rerun them. VM072's initial non-executable-job launch ran no tests;
the corrected complete validation run is recorded separately by M5.

| Selected coverage | Methods PASS |
|---|---:|
| Inherited 42 suites from 31L | 796 |
| Paired observer, geometry and fault cases | 21 |
| Exact pinned cache-dispatch audit | 3 |
| Controller lifecycle and stop cases | 18 |
| Intake/source closure | 9 |
| Supervisor/receipts/deadlines | 23 |
| Total: 47 suites | 870 |

Additional inherited exact-image cold/control audits and default controller
source/image/helper checks passed. The new tests include geometry refusals,
both journal boundaries, cached/maintained partial and committed observations,
all target-operation fault prefixes, control deadlines, wrong live indirections,
guard faults, and no callback/retry/cleanup after failure. They validate software
contracts, not Apple's cache hierarchy or CPU1 startup.

Intake duration60.701s; packaged controller0.666s; additional retained-package
verification0.339s, all exit0. No source or fixture repair on M1.

## Pinned inputs and preservation

- 306-file manifest SHA-256:
  `b89a052048cb6af45cf5065a96983df0c6c3012c5d2ec705212310679ac3da97`.
- Frozen L281/K254/J226/I202/H186/host6 source closures independently verified
  unchanged. The earlier 31L result and both offline reviews remain intact.
- Retained boot021 image: 3,932,160 bytes,
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
- Clean client `57a9339ffd1876e78297b17d34dece8cff8fa1ba` retained.
- Retained package verification PASS for all13 files, manifest
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
- Before/after digests of prior attempt31 evidence are identical. No consumed
  receipt was cleared, renamed, overwritten or forced. All six new31M live-use
  files remain absent. Private logs and digest/readiness records stay ignored
  under `build/native-intake/attempt31m/`.

**0 real discovery queries, device opens, target requests or native invocations.**
No image transfer, installation, M1 restart, VM/REA run or settings change.

## Independent source review and limits

Reviewed the new observer/audit/CTR leaf, full controller additions and live
wrapper, supervisor changes, release validation/review, tests and three research
notes. Supervisor runtime is identical after namespace and static-closure
normalization; live wrapper is identical after namespace normalization.

31M retains the exact31L CPU1 prefixes and two start stores. New CPU0 work binds
the live GOT/dispatch table and selected non-Cyclone feature path, publishes an
8-byte returning CTR reader, and requires EL2/VHE/stage2-disabled context.
Independent DMinLine/CWG qualification accepts64/128-byte bounds only; unknown
CWG or unsupported geometry refuses before CPU1 starts. Complete128-byte owned
granules, matching Normal translations, pre-start initialization/clean/readback
and no later CPU0 record stores are required. A separate maintenance control
must pass48 reads,2 marker stores and2 maintenance requests with canaries and
restoration under its2-second local bound.

Only an all-zero cached phase/identity/phase triad permits a fixed64-byte CIVAC
request and maintained triad. The owned128-byte span bounds the supported
granule. The pinned proxy's DSB SY/ISB completion and immediate non-clearing
exception check precede acknowledgment. Maintenance is CPU0-issued and can
affect other caches in the shareability domain; it is not guaranteed CPU0-local.
After starts, only the two fixed Normal records are eligible, with no Device,
code, MMIO, arbitrary-address, whole-cache or invalidate-only operation.

Every partial, positive or error stops. Only committed expected identity proves
CPU1 prefix execution. A maintained positive does not establish cache causality:
CPU1 may arrive between samples. All-negative still cannot exclude execution,
private dirty CPU1 data or an earlier fault. No new firmware/reset/MMIO operation,
callbacks, extra core, verified park or Linux continuation follows. Planned and
completed callbacks are both0 in31M. No code-level blocker was found for this
bounded hypothesis test; native qualification and visibility remain unknown.

## Next single session

Publish this readiness, then await the human's fresh start with M5 Running proxy,
powered Macs, direct known-good cable, healthy awake/unlocked/open-lid M1 and
independent90-second timer. No routine M1 reboot or repeated policy check.
Original Full/lab Permissive/Macintosh HD default remain last reported, not
freshly verified. Existing installed boot021 and retained boot042 stay unchanged.

One supervisor includes bounded discovery and one serial attempt; no preliminary
handshake, fallback or reconnect. Child60s/supervisor65s/serial2s/arrival3s and
each control2s remain. Arrival/control budgets are checked around operations,
not hard per-RPC interrupts; the independent supervisor and human bounds matter.
Any result, lost proxy or timer requires immediate M5 power-off and Macintosh HD
return before detailed inspection. No extra read, cleanup, retry or Linux launch.
**Native31M/Linux SMP NOT RUN, invocations0; CPU1/performance parity unverified.**

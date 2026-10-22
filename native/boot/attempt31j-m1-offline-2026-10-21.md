# Attempt31J — independent M1 offline readiness

**OFFLINE READY,2026-10-21 Eastern. Native31J/Linux SMP NOT RUN; CPU1 entry
unverified.** M1 pulled `ad9892e9858e34539d611ee2f9b7645c25a5ad6d` using
`git pull --ff-only`, clean worktree. Both documented offline commands exit0,
intake `OFFLINE_CHECKS_PASS_AWAIT_HUMAN_START`: **226 pins,579 methods PASS**,
no skips/fixes, hardware_operations0, restart_ready false (intentional).
Default packaged controller prints exactly
`OFFLINE PASS: 31J source/image verified; no discovery or USB open; restart_ready=false`.

## Verified inputs and test limits

- Manifest SHA-256:
  `360c1939430bbcf3a0b946a00fc1fe5d20b96b0b711998c36fde07cecf6fe765`.
  Frozen31I202 and host-only31J6 pins also independently PASS unchanged.
- Client remains clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
- Additional retained-package check exit0, all13 files; manifest
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
  Existing3,932,160-byte boot021 image
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
- Symbol mode **reviewed_layout_only**. **Full-symbol checks NOT RUN on M1:
  symbol file not supplied**. The23-method full-symbol suite is not selected
  in this documented mode, not a unittest skip. M5's602-method full-symbol VM
  and24 actual pinned-client synthetic cases remain separate offline evidence;
  M1 did not rerun that VM or firmware work.

| Selected coverage | Methods PASS |
|---|---:|
| Inherited26 suites from31I | 429 |
| Historical USB identity | 16 |
| Frozen host-only diagnostic | 19 |
| Bounded connection/discovery | 24 |
| Native wrapper, inheritance/parity and error phases | 64 |
| New intake/source closure | 6 |
| New supervisor/exclusive receipts/deadlines | 21 |
| Total:32 suites | 579 |

Native controller offline source/image/helper check also PASS. Reviewed full
handoff/outcome table, controller/connection module, supervisor, source closure,
reviews/validation and boundary coverage. The new tests include real parsing
through the wrapper with registry/serial dependencies mocked, first-fault
stops, strict identity/path checks, journals/interrupt provenance and exact
31I/J target-operation parity on synthetic success/timeout paths. These models
do not prove physical enumeration, reset/cache behavior, MMIO safety or CPU1
execution. No production/test source changes were made on M1.

**No real discovery query, serial open, target operation, VM, host install or
image transfer.** All six real31J live-use files absent before/after intake.
Separate host-only31J folder and prior31B–31I live receipts retain identical
digests; nothing reset/deleted/overwritten. Private logs/temp/readiness stay in
ignored `build/native-intake/attempt31j/`. No competing reader; bounded owned
caffeine assertion active. Installed boot021/package/client/settings unchanged.

## Next single session

Follow `tools/m1n1-client/attempt31j-instructions.md`: publish readiness then
await fresh human start of existing lab proxy, healthy powered awake/unlocked/
open-lid M1, direct known-good cable and independent90s timer. No routine M1
reboot or policy recheck. Original Full/lab Permissive/Macintosh HD default
remain last reported, not freshly verified.

Only the one supervisor performs real discovery: at most4 cached queries,
3s each,1s waits,15s total. Wait only for empty/absent enumeration; malformed,
query, ambiguous identity or path failure stops. Strict source/pin rechecks
precede native reservation and one serial-open attempt. No extra manual USB
checker or handshake. Parent invocation reservation is not native consumption;
child connection evidence and native consumed flag determine what occurred.
Connection-only receipts also block rerunning the invocation.

CPU sequence remains31I: same firmware-backed gate/two CPU1 starts/recorder,
at most8 PS and8 opaque32-bit core-state reads, conditional8 requests and park.
Core-state access remains exploratory; observed fields cannot independently
prove execution or reset release. Controller60s includes discovery/finalization;
parent65s plus bounded termination; serial2s,arrival3s,callbacks1s,core-state
pair1s soft deadline. Human90s bound includes discovery; no extension.

On every outcome/timer immediately power off and select Macintosh HD. No
reconnect, cable troubleshooting, rollback/cleanup RPC, extra core, new start/
reset/power/security write, settings change or Linux continuation. No native
invocation has been reserved: **invocations0,native31J/Linux SMP NOT RUN,
CPU1 entry unverified**. Offline readiness does not establish future enumeration.

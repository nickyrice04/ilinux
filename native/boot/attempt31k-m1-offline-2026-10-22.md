# Attempt31K — independent M1 offline readiness

**OFFLINE READY,2026-10-22 Eastern. Native31K/CPU0 control/cold tripwire/Linux
SMP NOT RUN; CPU1 entry unverified.** M1 pulled
`7043b1732e58686f8550e942d35a6c4d8d2fe3ba` with `git pull --ff-only`, clean
worktree. Both documented offline commands exit0. Intake returned
`OFFLINE_CHECKS_PASS_AWAIT_HUMAN_START`: **254 pins,716 methods PASS**, no skips/
repairs, hardware_operations0,restart_ready false (intentional). Packaged runner:
`OFFLINE PASS: 31K source/image verified; no discovery or USB open; restart_ready=false`.

## Verified inputs and test limits

- Manifest SHA-256:
  `cfb3a24b9f4447b6267938063ed09ee809218a90a8e7e2e235eca62d69c1668c`.
  Frozen31J226/31I202/host-only31J6 pins independently PASS unchanged.
- Clean client `57a9339ffd1876e78297b17d34dece8cff8fa1ba` retained.
- Additional retained-package check exit0,13 files, manifest
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
  Existing3,932,160-byte boot021 image
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
- New original CPU0 returning leaf:16 bytes,
  `4f6701c7d4c6e10bc9e2e000c2b839c7b7c0b29293aa3e305b006e0098277f77`.
  Original cold tripwire:76 bytes,
  `c49763521a8ea3c7b063c16a915139b41d39cef00a48800903059f0f3f7b5f98`.
- Symbol mode **reviewed_layout_only**; **full-symbol checks NOT RUN on M1:
  symbol file not supplied**. The23-method full-symbol suite is not selected
  in this documented mode, not a unittest skip. Image-only audits repeat the
  pinned-image/layout/reference checks without fresh symbol verification.
  M5's739-method VM/full-symbol checks,105 actual pinned-client synthetic
  scenarios, two independent assembly comparisons and REA/LLVM work remain
  separate evidence; M1 did not rerun that VM, assembly or firmware analysis.

| Selected coverage | Methods PASS |
|---|---:|
| Inherited32 suites from31J, including host boundary | 579 |
| CPU0 observer control, fault prefixes and address normalization | 26 |
| Cold tripwire image audit/model/telemetry | 49 |
| Controller lifecycle/positive/error/guard/deadline cases | 35 |
| New intake/source closure | 6 |
| New supervisor/receipts/deadlines | 21 |
| Total:37 suites | 716 |

New exact-image cold-entry/CPU0-control audits and default controller check
also PASS. Reviewed handoff/outcome table, controller, returning leaf/control,
cold encoder/assembly/model/telemetry/permission and reference audits, supervisor
namespace/source closure and review/final validation. No source repair on M1.
Models do not establish Apple reset dispatch, CPU1 mappings/fetch/store visibility,
MMIO/coherency safety or native performance. The fixed BootArgs integer-subclass
normalization from the released VM regression is retained unchanged.

No real registry query, serial open, target operation, VM, host install or image
transfer. All six real31K live-use files absent before/after intake. Prior31B–31J
receipts plus separate host-only31J evidence retain identical digests; none
reset/deleted/overwritten. Private logs/temp/readiness remain under ignored
`build/native-intake/attempt31k/`. No competing reader; bounded owned caffeine
assertion active. Installed boot021/package/client/macOS/settings unchanged.

## Next single session and interpretation limits

Publish readiness, then await fresh human start per
`tools/m1n1-client/attempt31k-instructions.md`: existing lab at Running proxy,
powered Macs, direct known-good cable, healthy awake/unlocked/open-lid M1 and
independent90s timer. No routine M1 reboot or policy recheck. Original Full/lab
Permissive/Macintosh HD default stay last reported, not freshly verified.

One supervisor handles bounded discovery (4 queries,3s each,1s waits only for
empty/absent enumeration,15s total), strict identity/path/source gates, separate
connection/native journals and one serial attempt. No extra manual checker or
handshake; connection-only receipts also block reentry.

Returning CPU0 control uses separate64-byte Device scratch,24 reads and2 stores
under2s, preserving seven canaries and verifying restoration to known zero.
Stale scratch refuses without erasure; fault permits no cleanup/retry. Control
PASS demonstrates only CPU0's observation path, never CPU1's state/visibility.

Only then can fixed RAM cold body-before-hook publication arm. Natural candidate
cold entry is intercepted without changing reset destination; a pre-MRS marker,
identity and CurrentEL can commit, then an unconditional self-loop prevents
shared stack/relocation/BSS continuation. Any nonzero/partial/wrong-identity/
error evidence stops; phase3 proves EL publication only, not terminal-PC/park.
Unexpected CPU0 cold arrival can lose the proxy; human timer bounds the run.
Negative channels cannot exclude either entry path or fetch/store failure.

Existing two CPU1 starts, vector recorder, at most8 PS/8 opaque core-state reads
and conditional8 callbacks/park remain. Cold ceiling2048 samples/8192 reads is
not a goal; original3s arrival and wall bounds stay. Controller60s,supervisor65s
plus bounded termination,serial2s,callback1s,core-state pair1s soft deadline.
Normal complete arrival timeout95 mutation intents; vector success103; partial
refusals can stop earlier. Intention is not acknowledgement or CPU execution.

On every result/timer immediately power off and choose Macintosh HD. No reconnect,
retry,cable troubleshooting,target rollback/cleanup,extra core,new MMIO start/
power operation,reset redirect,installed boot/security/volume/default change or
Linux continuation. **Invocations0; native31K/CPU0 control/cold tripwire/Linux SMP
NOT RUN; CPU1 effective entry UNKNOWN.** Offline readiness is not native success.

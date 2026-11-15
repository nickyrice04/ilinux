# M1: staged 31AR kit and page readiness

November 15, 2026. M5 reviewed your `39c09f9` report: source, controller and
exact pages pass, with 52 methods passed and the production-copy method
explicitly skipped. There is no actionable source finding. Reuse that review
and the unchanged producer copy/sanitizer evidence; do not repeat the suites.

The user authorized staging and boot-test preparation. The owner authenticated
locally and supplied successful staging JSON for all four exact production
files on lab Data. M5 accepts that receipt without repeating the copy:

| Staged file | Bytes | SHA-256 |
| --- | ---: | --- |
| ilinux31aj-reader | 125168 | 1008f610f03b979043787bfa67aa850aed4c5e6bc73416579e80f0aafe0a842a |
| profile.json | 823 | 27e265da1fac084db457f084dcd8f52b63e5daa1629575a13de64d68f24b4ecc |
| candidate.macho | 153190400 | 1ea24f0de4aa7d3e82c70a1b35f815791a48342db1a060100226b84dca7d7d01 |
| m1n1-boot021.bin | 3932160 | ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664 |

The copy installed no boot object and ran no native controller, policy read,
Preboot mount or boot/security/default change. The destination is the new
`31ar-kit` under lab Data `Users/Shared/iLinuxBoot`. Preserve all old kits,
profiles, keys, baseline files, state and consumed markers. No restaging or
state deletion is requested. Boot021 restoration is still **OUTSTANDING**.

M5 then selected iLinux Boot Lab temporarily in the original System Settings,
without clicking Restart. A fresh read-only selected-device/real-group comparison
confirmed current ORIGINAL, default LAB and distinct target groups. No policy
read or security change was made. Keep M5 running: the lab selection prepares
paired Recovery, not permission to boot the old lab object.

## Serve the already reviewed source-only page

Missing production helper delivery on M1 does not block serving. Your source-
profile preparation already produced all six exact outputs, and all three page
checks passed. The server reads the reviewed source closure, public profile
and exact HTML; it never executes or needs the helper. Recovery on M5 verifies
its staged bytes before copying and again before execution. Keep M1 binary
delivery recorded as unverified; page equality is not binary delivery.

Pull the commit containing this handoff. Reuse your already prepared exact
combined `recovery.html`. The earlier handoff's standard location is shown
below; if your retained review used another workspace build directory, use
that actual reviewed path. Do not overwrite, delete or regenerate a matching
page just to adopt a new pathname.

```bash
python3 -I tools/recovery31ar/package.py \
  --page build/31ar-m1-source-page/recovery.html --check-only
```

Require `EXACT_PAGE_VERIFIED`, 162 sources, and this unchanged combined page:
**15264 bytes**, SHA-256
`0dd56773d0551b1e226a5cec3c2d88acb07c7b6e9e51a036c47f9049aa623ed4`.
The source inventory is
`9ff372bba278c053a639b5b158fbc907fe17def5f7ef87142fa2daf3147d80fc`.
The visible title is **31AR guarded native transaction**. Both complete
install and independent restore text boxes must remain present.

After the check passes, start only the bounded reviewed page server. Supply
the M1's current private IPv4 address locally, without adding it to Git:

```bash
python3 -I tools/recovery31ar/package.py \
  --page build/31ar-m1-source-page/recovery.html \
  --bind "$ILINUX31AR_M1_IPV4" --port 8031 --seconds 1800
```

Set `ILINUX31AR_M1_IPV4` locally to the actual current address before that
command; do not pass the variable name as a literal address. Use the same
reviewed page path as the check. This service exposes only the fixed page at
`/31ar`; it is not a download, upload, shell or guest-control service.

Return the complete printed live URL privately to the human, including all
four IPv4 numbers, port and `/31ar`. Verify the served response matches the
reviewed page before reporting readiness. Publish a new sanitized readiness
report with the page bytes/hash, source inventory, route, bounded lifetime and
exact-byte verification. Keep the private URL, process/session identifiers and
network details out of Git. Record source-only page verification separately
from the owner-confirmed exact M5 staging; do not claim M1 binary delivery.

An expired read-only page server may be refreshed without repeating any
Recovery operation. Keep the independent restore box accessible through the
second Recovery visit. Do not restart M1, start a USB proxy, rebuild a package,
repeat tests, transfer a large image or run another camera-calibration session.
Keep M5 running until M5's later cue. No physical operation is requested here.

## Planned physical scope, not yet executed or authorized by this page task

The retained temporary lab-default/Original-default-return approval applies to
the same paired Recovery selection workflow. It does not authorize a writer to
Macintosh HD. The current request authorizes staging and preparation; do not
claim that the new 31AR Apple writers have run or are authorized by this handoff.
M5 will supply the separate concrete physical authorization and restart cue.

That planned transaction is one lab-only candidate installation with temporary
identity-verified shared-Preboot RW access, followed by one independently timed
**maximum 90-second RAM diagnostic**. Capture Aura entry, Linux entry, distinct
concurrent pinned workers, checksums/timers and **60-second liveness** separately.
Tick labels are not wall-clock time, and a CPU list alone proves no concurrent
work. The candidate is a RAM diagnostic, not the Omarchy desktop or a performance
parity result. M1 supplies the external deadline; no M1 restart or USB proxy is
required for the embedded diagnostic.

Return to paired lab Recovery for the independent restore using the same new
transaction's saved key, profile, baseline and target commitment. That path
does not require the candidate file. It conditionally prepares only lab CTRR,
then restores exact raw boot021 and verifies the supported policy and cleanup
postconditions. Restore Macintosh HD as Startup Disk separately and confirm
its desktop/default return. Macintosh HD must remain **Full Security**.

Do not treat a passing result-display validator as installation success: it
also safely displays a well-formed refusal. A boot cue requires actual
`INSTALL_COMPLETE`, `candidate_verified=true`, `cleanup_verified=true`, writer
exit zero, and the final shell success record with helper exit zero. Restore
requires actual `RESTORE_COMPLETE`, `rollback_verified=true`, known cleanup and
final shell success. A verified already-restored no-op may have writer exit
minus one. Missing records, refusal or uncertainty mean no boot or retry.

Each visit uses one whole-box copy, browser quit and one Terminal paste. No
clipboard exercise or edited command retry. Keep recording **OFF throughout
Recovery authentication and Apple command output**; start it only for the later
authorized native window after installation/readback/cleanup succeed. Preserve
all state after any refusal, timeout, interruption or ambiguous result. Do not
force unmount, reset policy, remove spent markers or repeat a writer.

Actual 31AR Recovery/RW mount/install/restore/native entry/Linux/SMP/performance
remain **NOT RUN**. Staging and source-page readiness do not establish those
results. Publish only finite sanitized readiness evidence; no policy values,
identifiers, credentials, camera media or proprietary artifacts.

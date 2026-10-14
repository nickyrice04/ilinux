# Stage B attempt 4: DAPF correction and controller PASS; Linux not observed

Session: 2026-10-13 America/New_York (UTC timestamps below).
Execution/readiness commit: `d4209d3fd77f1269adacae9bd0cbd01f612dd085`.
Reviewed code/handoff: `2773a73`. The human reported Running proxy after
published readiness, starting the one documented attempt. No retry.

## Observed controller result

* Start UTC **2026-10-14T03:13:05.896584+00:00**; end UTC
  **2026-10-14T03:13:16.354836+00:00**. **Exit 0, elapsed 10.458 seconds**.
* Package, unique primary USB identity, chip, packaged boot021 marker, initial
  secondary state, ADT root and initial board/framebuffer checks passed.
* First required checkpoint, before uploads:
  **`DAPF layout PASS: AOP has DART/GAPF only; RAM correction planned.`**
  The guard verified packaged-image provenance, matching live function bytes,
  relocated table/names and the reviewed live ADT instance layout.
* Payload upload and final prepared-DT checks passed: framebuffer geometry/
  format/range, exactly one exposed CPU, disabled NVMe/cpufreq and fixed
  arguments. Secondary state was rechecked.
* Second required checkpoint:
  **`DAPF RAM table corrected: omitted absent AOP DAPF; other entries retained.`**
  The single 96-byte data-table write and readback completed. This validates
  that bounded correction on this session; it does not establish Linux liveness
  or general DAPF/GAPF hardware compatibility.
* Handoff checkpoint **2026-10-14T03:13:16.120938+00:00**:
  `Preflight PASS; handing off. Observe the M5 display; USB console ends here.`
  `kboot_boot` returned successfully and controller cleanup completed without
  an error. No USB reconnect, extra handshake, shell or further target command.
  A successful request/reply does not prove the kernel executed afterward.

## Human screen evidence and return

* User reports **the same logo remained**, with substantial text scrolling
  too quickly to read or photograph. The text cannot be identified as m1n1
  or Linux from that description; no transcript or photo was supplied for
  this attempt at reporting time.
* **Linux kernel, PID 1, online_cpus=1 and 60-second liveness: NOT OBSERVED.**
  No identifiable panic/exception or readable first/last kernel line was
  reported. This is an observation gap, not a proved kernel failure, blank
  screen, specific driver diagnosis or Linux success. One-CPU DT validation
  is distinct from an observed running Linux CPU count.
* Screen limit: **2026-10-14T03:15:16.120946 UTC / 23:15:16 Eastern**, 120 seconds
  after handoff. M1 instructed the human to stop at that deadline and return
  via power-off/startup options to Macintosh HD. Actual power-off time was
  not measured. No further attempt was made.
* **User confirms successful return to the usual Macintosh HD desktop.**
  Fresh build/default/protection checks remain NOT CHECKED this attempt.
  Earlier original Full/lab Permissive JSON is the M5-reviewed pre-attempt
  baseline; desktop return alone does not independently reverify those settings.

## M5 next work

User-confirmed return is recorded. M5 should perform the planned read-only
macOS/default/protection checks. The previous framebuffer and DAPF controller gates now pass. Preserve
those checks and the single-core/storage limits. Establish an observation path
for the earliest unconfirmed handoff/kernel milestone before proposing another
physical attempt: the current screen report does not locate a failure.
Do not infer that the previous SError recurred or was fully eliminated from
unreadable text. Offline review/instrumentation and a plan to retain readable
screen evidence come before a new separately authorized attempt. No automatic
retry, reinstall, boot-setting change or additional live diagnostic is authorized.

## Provenance

* Boot022 archive unchanged:
  `b59db87bee50f5a2b57f65ea54e9ecd9fc07d410251bb38175001ac056ee6862`.
* Intake manifest unchanged:
  `862391dd99ee93d07c196e502196cefc869b2549274d6139d781f564b4bc50a0`.
* Launcher: `a9d14ec1019de2c728c81779472b84a90265620969f0d8d23f1b411e924ece89`.
* DAPF guard: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`.
* Clean client pin remains `57a9339ffd1876e78297b17d34dece8cff8fa1ba`;
  installed boot021 m1n1/marker unchanged, marker checked live PASS.
* Offline readiness: package verification, all 13 retained receipt files,
  archive/manifest/source hashes, 31 launcher + 16 guard + 2 pinned DAPF-parser
  + 4 root-ADT cases PASS. Previous unchanged-component tests remain historical.
* One unchanged reviewed launcher `main(argv)` invocation with documented
  arguments through the sanitized wrapper and `run.sh`. Both exact DAPF
  checkpoint strings were retained; fixed errors/safe traceback would have
  been retained on failure. No raw ADT, target memory, callout identifiers,
  absolute addresses or image were saved.
* Separate ignored records: `build/native-intake/results/boot022-stage-b-attempt4.json`
  and `.md`; retained receipt `build/native-intake/receipts/boot022.json`.
  Previous attempts/receipts preserved. No volume/security/default/boot-object
  changes or reinstall; only the documented live RAM/register/hardware work.

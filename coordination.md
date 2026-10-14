# Coordination: agents working in this workspace

Created 2026-10-13. Read this together with `AGENTS.md`, `progress.md`,
`blockers.md` and `decisions.md` before starting work. If this file and an
older plan disagree, this file wins for ownership and order of work.

## Roles

### Current M1 result — attempt 3 m1n1 exception; return confirmed, 2026-10-13

* One boot022 invocation at `c5f515c`: controller exit 1, **32.059 s**,
  UTC 02:34:32.733054–02:35:04.792407 on 2026-10-14.
* **All preflight checks passed**, including the corrected prepared framebuffer,
  single-core DT and disabled storage/cpufreq. Live boot021 marker PASS.
  Handoff requested at **02:34:42.905947 UTC**; `kboot_boot` reply timed out.
* Human photo shows **m1n1 SError in EL2**, followed by `Unhandled exception,
  rebooting...`, after DT preparation and PCIe messages. Safe relative code
  offset and exact text are in the result; no raw addresses/register dump saved.
  Message proximity does not establish PCIe as the cause.
* **Linux kernel/PID 1/online_cpus=1/60-second liveness NOT OBSERVED.** Handoff
  requested is distinct from kernel execution; this is not the earlier
  preflight-only NOT RUN result. No native success or performance claim.
* **User confirms usual Macintosh HD desktop return.** Fresh build/default/
  protection checks remain for M5. No settings changes, reinstall or retry;
  boot022, installed m1n1 and clean client pin unchanged.
* M5: read `native/boot/stage-b-2026-10-13-attempt3-result.md`, perform read-only
  return checks, then investigate matching-build symbols and pinned pre-kernel
  hardware setup offline. Preserve the passing observation gate. This one
  attempt is consumed; no new live session or boot-setting changes authorized.

### Historical M1 readiness — boot022 intake PASS, 2026-10-13

* Pulled `3c7eae1` (descendant of `bf79263`) and read the current handoff.
  Downloaded private boot022 to its own ignored directory; verified the
  Git-tracked archive checksum **before extraction**, then offline launcher
  verification and all **13 intake-file hashes/declared revision PASS**.
* Archive (16,717,590 bytes):
  `b59db87bee50f5a2b57f65ea54e9ecd9fc07d410251bb38175001ac056ee6862`.
  Intake manifest:
  `862391dd99ee93d07c196e502196cefc869b2549274d6139d781f564b4bc50a0`.
  New receipt: ignored `build/native-intake/receipts/boot022.json`.
* **31 launcher + 5 framebuffer + 4 actual pinned-ADT tests PASS** locally,
  all offline. Reran ADT cases because the changed FDT gate/test fixture is
  in that path. Prior 20 USB tests remain applicable to unchanged selector/
  client. M5's C/serializer/intake tests are separate reported evidence.
* Reviewed source hashes match the checklist. Clean client stays pinned at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Compared actual package files:
  only the Stage-B DT differs; kernel/initramfs/m1n1 and other payloads match
  boot021. The installed **boot021 m1n1 marker is correct**; no reinstall.
* M5 policy prerequisite is already PASS per `3c7eae1`: user-supplied original
  Full/lab Permissive JSON, both exit 0, reviewed by M5. No duplicate check.
* Separate ignored `boot022-stage-b-attempt3.json`/`.md` evidence prepared;
  earlier receipts and attempts preserved. **Ready for the authorized Stage B
  attempt 3**, after the human selects the existing lab and reports proxy ready.
* **Attempt 3/Linux NOT RUN; current live checks NOT RUN.** No USB opened,
  settings changed or target commands sent during intake. One invocation only,
  then observe kernel/PID 1/online_cpus=1/60-second liveness within the documented
  limits and return to Macintosh HD. No retries or boot-setting changes.

### M5 handoff reviewed by M1 — boot022 / Stage B attempt 3, 2026-10-13

Code and checklist: `0bea8f2` or later. Download:
https://github.com/nickyrice04/ilinux/releases/tag/native-j716c-boot022
Both assets published; remote archive digest and size verified against local.

Latest: Stage B attempt 2 never handed off to Linux. Boot021 lacked m1n1's
required framebuffer placeholder. Job 022 reproduces this with the actual
pinned C function and corrects only the Stage-B DT; boot022 is verified offline.
Kernel/initramfs/installed m1n1 unchanged; the boot021 marker remains correct.
M1 must intake boot022 before one reviewed attempt 3. The user's fresh read-only
post-return JSON reports original Full/lab Permissive, both exit 0; reviewed,
not independently rerun. Native correction NOT TESTED, Linux NOT RUN. Original root/build,
FileVault/SIP/authenticated-root and staged m1n1 were independently rechecked.
No volume/security/default/boot-object changes. Current instructions:
`tools/m1n1-client/stage-b-instructions.md`; evidence:
`virtualization/jobs/022-framebuffer-handoff/RESULTS.md`.

M5 owns the completed DT-only package and regression. M1 owns offline intake,
one bounded live controller invocation after readiness and human lab selection,
sanitized screen/checkpoint evidence and original-macOS return. Do not reinstall
m1n1 or repeat Recovery. Download/verify before restart; no extra readiness
round trip through the M5 agent is required once intake and policy checks pass.
Use a separate attempt-3 record; preserve prior failures. Keep original Full
Security and the existing single-core RAM scope. No automatic retry.

Policy prerequisite is now satisfied. At this update, GitHub main still ends at
`bf79263`, with no M1 boot022 intake report visible. M1 can complete intake and
confirm readiness directly to the human; do not request the same M5 policy
check again before this attempt. No new boot or settings change was performed
while recording the supplied result.

### Historical M1 result — Stage B attempt 2 stopped; return confirmed, 2026-10-13

* One corrected attempt at `993a6af`: **exit 1, 10.202 s**, UTC
  2026-10-14 01:58:58.489367–01:59:08.692220. Package/primary/target checks
  passed; corrected ADT root access and initial board/framebuffer checks passed.
* RAM payload upload completed. Prepared-DT validation stopped with exact
  **`no enabled boot framebuffer; observation path absent`** at `fdt.py:90`,
  called by `launch.py:113`. No Linux handoff or `kboot_boot`; **Linux NOT RUN**.
  Live packaged-marker verification PASS. Missing versus disabled/mismatched
  framebuffer node remains unresolved; no raw target DT was retained.
* Human confirms return to the usual **Macintosh HD desktop**. Photo shows
  m1n1 DT preparation ending at `FDT prepared` (address omitted), consistent
  with the controller's subsequent rejection. A freeze is not established.
  Linux NOT RUN; fresh build/default/protection checks NOT CHECKED this attempt.
* Boot021, launcher and clean client pin unchanged; no volume/security/default/
  boot-object changes, no reconnect or retry. Existing offline tests remained
  valid and post-pull package verification passed. Attempt 1 evidence preserved.
* Separate sanitized result: `native/boot/stage-b-2026-10-13-attempt2-result.md`.
  Next: M5 read-only return checks and offline framebuffer investigation.
  The one corrected attempt is consumed; no further live session authorized.

### Consumed M5 handoff — corrected Stage B attempt 2, 2026-10-13

The user requests review, next-boot preparation and repository instructions
for M1 after the lab boot. B reviewed/fast-forwarded `fff8b95` and `1635ff0`:
attempt 1 failed before upload/handoff; the ADT root-lookup defect is confirmed
against the pinned source. Keep its original evidence immutable. Linux NOT RUN.

The next step is one fresh Stage B attempt with M1's corrected launcher. This
current user direction authorizes that reviewed continuation, not an automatic
retry of the consumed attempt. Original Full Security, no volume/security/
boot-object/default changes, no SMP or storage expansion. No repeat approval
or redundant readiness-message round trip is needed for this exact scope.

M1's 31+4 corrected-code tests and unchanged USB/intake readiness remain valid;
B independently reran 31 launcher cases, checked the ADT API, and verified the
real package. Launcher/payload/pin unchanged by B. Read-only M5 checks: original
Macintosh HD/build 25G83, original System/Data FileVault, SIP/authenticated-root,
AC, no project VMs, staged m1n1 hash match. The user supplied fresh read-only
original Full/lab Permissive JSON, both exit 0. Default/installed-object checks
were not rerun and are not inferred from this policy result.

Human may shut down and pick iLinux Boot Lab once. M1 then pulls/reads
`tools/m1n1-client/stage-b-instructions.md`, confirms listed source hashes/pin
and offline package verification, creates a distinct attempt-2 evidence record,
and executes the launcher once after the human reports proxy ready. Record the
new RAM-utility/ADT checkpoints as well as screen milestones, stop at the
specified bounds and return to Macintosh HD. Publish sanitized actual results.
No new native action occurred in B's review; attempt 2 remains NOT RUN.


### Historical M1 result — 2026-10-13: Stage B attempt 1 failed; return confirmed; ADT lookup fixed offline

* Single authorized launcher attempt at `fff8b95`: **exit 1, 1.135 s**, UTC
  2026-10-14 01:38:53.644283–01:38:54.779211. Package/USB identity and target
  chip/packaged-marker/secondary checks passed; **KeyError** before board/
  framebuffer confirmation, payload upload or Linux handoff. No retry.
* Live packaged m1n1 marker check is now **PASS**. **Linux remains NOT RUN**;
  kernel/PID 1/one-CPU/60-second screen milestones were not reached.
* User reported “heap limit” (normal utility setup output in pinned source)
  and confirms return to Macintosh HD. New post-attempt build/default/security
  checks are not reported. No volume/security change, no reconnect during diagnosis.
* Offline: confirmed `utils.adt["/"].compatible` misuses the pinned ADT API;
  root access is `utils.adt.compatible`. Corrected locally, retained board/CPU/
  DT gates and added real pinned-parser regressions with synthetic data.
  **31 launcher + 4 new ADT tests PASS; real package offline verification PASS**.
* The defect matches the live checkpoint/type, but the raw exception argument/
  traceback was not retained, so the precise live throw site remains uncertain.
  Boot021/client pin unchanged; fix has not been tried on hardware.
* Full sanitized result/investigation: `native/boot/stage-b-2026-10-13-result.md`.
  M5 should review and perform read-only return checks. **No retries**; current
  task is offline diagnosis/reporting, not a new boot authorization.

### Historical M1 readiness — 2026-10-13: ready for the authorized Stage B attempt

* Pulled/read authorization `b06c56e19a172771866c6e8c8c9a490db105cc84`
  and the exact Stage B checklist. User authorizes one RAM Linux attempt after
  this readiness report, then Macintosh HD return, preserving original Full
  Security with no volume/security changes, retries or additional setup.
* Documented offline launcher verification **PASS**. **31 launcher, 20 USB
  (including four upstream fake-transport cases), and 7 intake tests PASS**:
  58 cases total, each suite exit 0. No device was opened by these tests.
* Rechecked all **13 received boot021 files** against the retained receipt and
  SHA256SUMS against the tracked digest
  `9d2b9ec1ae9dad601fb25a6536e838b57ab436160ab6ceddf208b764de41f581`.
  Payload/receipt unchanged; client clean/pinned to
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* Launcher SHA-256:
  `96af0a81b332376d5707a8e0d52aab6aca08959743d41f510b994772ed0f8364`.
  Shared USB selector SHA-256:
  `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`.
* Prepared fresh ignored `build/native-intake/results/boot021-stage-b-authorized.md`
  from the current template, plus a sanitized JSON record. They retain Git/code/
  procedure/package provenance and prior Stage A PASS separately. Prior screen
  preparation is historical; this authorized-session record is current.
* **Ready for the authorized Stage B attempt.** M1 will guide one lab boot,
  execute the documented `--launch --device auto` command once after the human
  reports m1n1 running, observe checkpoints/screen milestones, then guide return.
  No separate handshake, upstream shell/launcher or secondary startup.
* At this readiness checkpoint **Stage B/Linux and live target-version checks
  remain NOT RUN**. Runtime checks occur only during the authorized attempt.
  The controller deadline is 180 seconds; screen observation ends at the
  60-second liveness message, explicit failure or 120 seconds after handoff.
  M5 read-only return verification follows the user's return report.

### Consumed authorization — one Stage B attempt after M1 readiness, 2026-10-13

The user explicitly approves one Stage B Linux RAM boot after M1 confirms
readiness, then return to Macintosh HD. Keep Macintosh HD at Full Security;
no volume/security changes. This supersedes earlier Stage B permission holds
for this exact session. No repeat permission question is needed.

M5 preparation: current root Macintosh HD, original System/Data FileVault on,
build 25G83, AC power, no project VM processes, staged m1n1 matches boot021.
The user's fresh original Full/lab Permissive result from the preceding turn
remains the policy baseline. No code/payload changed since `e2c0cc7`; the
existing M5 test results apply, with no redundant run.

At this preparation checkpoint no M1 readiness commit after `e2c0cc7` is
visible on GitHub. M1 must pull this authorization, complete/report 31 launcher,
20 USB and 7 intake cases plus package verification, and confirm ready before
the human shuts down M5. Use `tools/m1n1-client/stage-b-instructions.md` for
one `--device auto` launcher attempt with the existing boot021/client pin.
No separate P_NOP, retry, shell, SMP start, installation or Recovery operation.
Stop at success/failure/time bound, return via the held-power picker to
Macintosh HD, and publish sanitized actual results. Linux remains NOT RUN
until observed; the M5 agent has not restarted or opened USB during preparation.


### Current M5 handoff — Stage B prepared offline, 2026-10-13

B reviewed/integrated `974e894`: Stage A P_NOP PASS and user-confirmed desktop
return. Read-only M5 checks now confirm original build 26.6.2/25G83, original
System/Data FileVault, SIP/authenticated-root and unchanged staged m1n1 hash.
The user's fresh post-return JSON reports original Full/lab Permissive, both
exit 0; B reviewed that output, not an independent privileged rerun. Default
startup selection and the installed boot object were not newly inspected.

B fixed Stage B's stale P_01 filename gate by sharing M1's descriptor selector
through `tools/m1n1-client/usb_identity.py`. Use `--device auto`; no guessed
path, second-port probing or fallback. Serial-init failures close the port,
transport errors redact identifiers and safe launch checkpoints aid diagnosis.
The boot021 payloads, manifest, pin and CPU/DT restrictions remain unchanged.
31 launcher, 16 stdlib identity/CLI and 7 intake tests pass; local payload
verification PASS. No native Linux or new live USB test ran.

M1 may now pull and perform the offline checks in
`tools/m1n1-client/stage-b-instructions.md`, including all 20 USB cases with
its prepared upstream client environment. Record readiness and preserve the
completed Stage A result. Wait for the human's explicit Stage B approval and
readiness before any restart/launch. Stage B is one RAM Linux attempt, no SMP
start, disabled Linux NVMe/cpufreq, PID 1/one CPU/60-second screen liveness,
then Macintosh HD return. No Recovery/reinstallation/security change required.
B owns subsequent target-specific kernel/DT diagnosis and CPU/power REA work;
M1 owns physical-session coordination/results, C waits for tested Linux access.

### Current M1 handoff — 2026-10-13: Stage A P_NOP passed; Macintosh HD return confirmed

* User started a new Stage A attempt after checker fix `70ad452`. On M1,
  discovery and connection-time re-identification found **one primary** among
  two modem interfaces: **VID/PID 1209:316d, CDC data interface 1**. No callout
  names, serial numbers or raw registry output are retained in the handoff.
* Actual command: `tools/m1n1-client/run.sh tools/m1n1-client/usb-check.py --connect`.
  **PASS, exit 0; one P_NOP replied in 0.158 seconds**, within the 10-second
  deadline. UTC start **2026-10-14T01:13:02.764830+00:00**, end
  **2026-10-14T01:13:02.922801+00:00** (2026-10-13 evening in America/New_York).
  The port closed; no retries, feature negotiation, memory/register requests
  or boot/launcher requests were sent by M1.
* After the guided power-off/held-power picker return, the user confirmed:
  **back at the usual Macintosh HD desktop**. This is user-observed return,
  not remote M5 inspection. Current build, default selection and protection
  states have not been freshly rechecked after this attempt. Earlier original
  Full/lab Permissive and FileVault/SIP/authenticated-root results are baseline.
* Local sanitized evidence: ignored
  `build/native-intake/results/stage-a-20261014T011302Z.json`, now updated with
  user-confirmed return. Boot021, original intake receipt and clean client pin
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba` are unchanged.
* This validates descriptor-based primary selection and a responding m1n1
  proxy on this setup. **Live target-version verification, Linux/Stage B and
  native Omarchy remain NOT RUN.** No runtime-version or Linux compatibility
  claim follows from P_NOP. No new test was run for this documentation update.
* M5 agent next: review the evidence and perform the planned read-only return
  checks. Stage A handshake and desktop return succeeded; do not repeat setup
  or automatically start another boot. Stage B requires separate authorization.

### Earlier M1 handoff — 2026-10-13: Stage A stopped before handshake; USB naming fixed offline

* Controlled M5 m1n1 boot reached `Running proxy...` (user/screen observed).
  M1 discovery saw two modem callouts, but neither matched the checker's
  hard-coded `P_01` suffix. No serial port was opened and no P_NOP was sent.
  This was an identification stop, not a failed USB exchange. User confirms
  subsequent return to Macintosh HD. No fresh post-attempt protection check
  or default-selection check has been reported; the earlier checks are baseline.
* Pinned m1n1 source explains the assumption: `usb_build_serial()` uses the
  ADT serial when available; `P-0` is only the fallback. Descriptors identify
  VID/PID 1209:316d, primary CDC control/data interfaces 0/1 and secondary
  virtual UART 2/3. `usb.c` assigns the primary pipe to console/proxy. USB0,
  USB1 and USB2 screen labels do not identify the host CDC callout role.
  No actual callout names or photographs are retained in the repository.
* Fixed the local checker to walk cached macOS IORegistry USB ancestry and
  require exactly one matching primary data interface 1/class 0x0a. Missing
  metadata, unrelated devices, secondary interfaces, ambiguity and stale or
  linked/non-device paths stop before opening. There is no filename fallback.
  Bare `--connect` re-identifies the sole primary; paths/serials/raw registry
  stay in memory and are not printed or saved. Printed results include UTC
  start/end and elapsed time for the eventual single handshake.
* Validation: **20 offline tests pass**, including synthetic fallback and
  serial-derived names, secondary/wrong/missing/ambiguous identity, stale paths,
  privacy, no-open discovery and no retries. Fake transport verifies one
  serialized P_NOP with zero arguments, the 10-second alarm and closure on
  success, timeout and initialization error. M1's read-only discovery with
  M5 back in macOS finds no primary and stops without opening any port.
* Boot021, ignored intake receipt and clean client pin
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba` are unchanged. No target commands,
  security changes, installations or boots were performed during this repair.
* **NOT RUN:** live USB/P_NOP, live target-version verification, Linux and
  native Omarchy. The new metadata mapping is offline-tested, not yet verified
  with M5 in m1n1. This request prepares another Stage A attempt; do not start
  one automatically. When the user starts the next session, use the revised
  checklist, one bounded handshake without retries, then original-macOS return.

### Prior Stage A authorization — session ended before handshake, 2026-10-13

The user explicitly approved **one m1n1 boot, one USB handshake, then back to
Macintosh HD**, keeping Macintosh HD at Full Security. This supersedes earlier
Stage A approval holds; no repeat approval is needed for this exact scope.
Follow `tools/m1n1-client/stage-a-instructions.md`. Stage B/Linux, upstream
shells/launchers, register/memory requests, policy changes and reinstallations
are outside this session.

M5 checks: current root Macintosh HD/FileVault on, staged m1n1 hash/size match,
AC power, no project VM processes. Fresh original Full/lab Permissive policy
result was supplied by the user in the preceding turn. Artifacts are unchanged;
existing offline tests/receipt remain applicable, no redundant test run.

M1 pulls this handoff and confirms ready before the user shuts down the M5.
Use the held-power picker, **iLinux Boot Lab → Continue**, leaving Macintosh
HD as default. On M1 discover the actual primary port and run the existing
10-second-bounded P_NOP checker once. Record actual outcome; no retries. After
success or failure, power off M5, use the held-power picker for **Macintosh HD
→ Continue**, then verify return/protections and publish sanitized results.
All Stage A results are still **NOT RUN** until observed. The M5 agent has not
restarted this computer or opened any USB connection during preparation.

### M5 review after return — 2026-10-13

B reviewed and fast-forwarded M1 report `c6f2c6f`. Native m1n1 reached
`Running proxy...` by the screen evidence reviewed by M1; that is an actual
bootloader milestone on this unit. USB/P_NOP and Linux remain NOT RUN.

Read-only M5 checks now independently confirm original root **Macintosh HD**,
**26.6.2 / 25G83**, original System/Data FileVault enabled, SIP enabled and
original authenticated-root enabled. The csrutil installation menu changed
order between queries: choose by the name in the same live prompt, never by
a cached number. Staged m1n1 size/hash still match; the installed boot object
was not separately read. Default restoration remains the user's observation.

The user supplied the fresh post-return helper result: **original Full / exit
0; lab Permissive / exit 0; read_only true**. This completes the return-policy
check; B did not independently rerun the privileged query. The M5 local helper
now accepts `--expected-lab Permissive` so the intended lab policy is not
mistaken for a failure. No policy/startup/payload changes were made this review.

Next session is now authorized above: the existing Stage A checklist, one
bounded P_NOP on the actual primary M1 USB path, then return to Macintosh HD.
The installed entry is ready for that test; no Recovery/reinstallation
is needed for the planned boot. After Stage A, review and authorize Stage B's
one-core RAM Linux/PID-1/60-second heartbeat diagnostic. Native desktop,
peripheral functionality and performance parity remain unvalidated.

### Current M1 handoff — 2026-10-13: lab m1n1 installation and original macOS return complete

Evidence: human-entered commands on the M5, user-reported results and screen
photos reviewed by M1; no remote M5 query by M1. Only sanitized conclusions
are retained. Raw photographs, policy identifiers and credentials are not copied.

* Lab desktop build confirmed **26.6.2 / 25G83** before paired Recovery.
  Staged helper SHA-256 matched
  `e65636d03cfb7a7000f86810fdc8888e209b99bedaa1b36ca7a125de4bf72188`.
  Recovery lacked `shasum`; a temporary same-shell function accepted only
  `shasum -a 256 FILE` and delegated to `/sbin/sha256 -q`. No helper file
  or system tool was modified. The helper/payload checks then passed.
* Read-only preflight: **exit 0; original Full; lab Full; lab paired 1TR**.
  An initial mistyped readiness variable stopped the guarded operation;
  the corrected command subsequently reached authentication and succeeded.
* Authorized lab policy update succeeded: **lab Permissive, kernel CTRR
  Disabled**, with helper postcheck **original Full / lab Permissive / paired
  1TR**. The guarded installation rechecked policy and payload before kmutil.
* User reports **kmutil exit 0; Installed yes**, and final policy check
  **original Full / lab Permissive**. This completes boot-object installation.
* **Incidental m1n1 startup observed:** user released the power button early
  during the return sequence. Their photo shows m1n1 screen output/logo and
  `Running proxy...`. User reports promptly powering off, then successfully
  returning to the usual Macintosh HD desktop and selecting **Macintosh HD
  as the default startup disk**. This is screen evidence of m1n1 execution,
  not a completed Stage A test or evidence of Linux execution. Duration and
  exact running version were not verified; USB initialization text does not
  establish a controller connection or a successful P_NOP exchange.
* **NOT RUN:** live USB connection/P_NOP, live target-version check, Stage A
  controlled handshake, Stage B/native Linux and native Omarchy. No launcher
  was run by M1. No Linux boot, liveness or performance result is claimed.
* Boot021 package/ignored intake receipt are unchanged. M1 rechecked the clean
  client pin: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. No new offline
  test run was needed for this documentation-only update; prior results stand.
* Next: M5 agent reviews this handoff and can verify original macOS protections
  read-only after return. The Full/Permissive result above was observed in
  Recovery after installation; post-return policy/SIP/FileVault checks have
  not been newly reported. Do not repeat installation. Wait for explicit
  Stage A authorization before any controlled m1n1 boot or USB connection;
  Stage B requires its own approval.

<details>
<summary>Historical preparation handoff (superseded by the execution results above)</summary>

### Current authorization: lab-only Recovery policy and m1n1 installation

The user explicitly authorized lab-only Recovery setup, Permissive Security,
disabling kernel CTRR and installing the verified m1n1 boot object, while
keeping **Macintosh HD at Full Security**. This supersedes prior security and
custom-boot holds for this exact lab scope. No repeat approval is needed.
B prepared/staged a tested read-only Recovery helper and the one-operation-
at-a-time instructions. M1 guides the human on the M5 through sections 5–6 of
`kernel/native-enablement/boot-entry-setup.md`, records actual results and helps
return to original macOS. M1 must not run the M5 commands on itself.
Stage A/P_NOP and Stage B/Linux testing are still not authorized by this setup.

**Observed progress:** B created the unique empty APFS lab volume, preserving
the original volumes' names/roles/FileVault states. Original policy reports
Full Security; SIP/authenticated-root enabled. Repeated installer verification
PASS. Normal GUI launch succeeded; after the user authorized its license, B
selected and visually verified **iLinux Boot Lab** as destination.

**M1 return handoff (user-observed):** the user completed installation/setup,
reached the lab desktop and reported `sw_vers` **26.6.2 / 25G83**, then confirmed
successful return to the usual **Macintosh HD** desktop. These observations
establish lab first boot and return; M1 has not remotely inspected the M5.
B reviewed/integrated M1 report `f34970e` and independently confirmed current
Macintosh HD build 26.6.2 / 25G83, FileVault/SIP/authenticated-root enabled,
and a separate mounted lab System/Data group with the same installed build.
The user subsequently ran the read-only policy helper and supplied its JSON:
**original Full / exit 0; lab Full / exit 0; read_only true**. B reviewed this
user-provided result; it is not an independently rerun query or an inference
from the pre-install baseline. This resolves the pending policy read.
B has now staged the exact m1n1 binary at
`/Volumes/iLinux Boot Lab - Data/Users/Shared/iLinuxBoot/m1n1.bin` after
rechecking the lab System/Data roles and separate volume group. The reread
copy matches the tracked manifest: 3,932,160 bytes, SHA-256
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Only the new staging folder, m1n1 and now the read-only `recovery-preflight.sh`
were created on lab Data; no existing file was overwritten. Helper SHA-256:
`e65636d03cfb7a7000f86810fdc8888e209b99bedaa1b36ca7a125de4bf72188`.
Its 21 preflight cases, seven documented-operation guard cases and syntax checks
pass with stand-ins; no real policy writes were tested. Current root and payload
were rechecked; AC power, no project VM processes. System Settings already
shows **iLinux Boot Lab** selected. B opened the pane but did not change its
selection or click Restart. No security/custom-boot change has run yet.
Boot021 and the existing client pin are unchanged.
Live USB/P_NOP, live target-version check, native m1n1/Linux/Omarchy remain
**NOT RUN**. Current handoff: `kernel/native-enablement/boot-entry-setup.md`.

**Next human/M1 session:** pull this handoff before restarting. Boot lab macOS,
shut down and enter its paired Recovery with one continuous power hold. Run
the helper and gated policy/install commands; verify original Full/lab
Permissive and actual kmutil exit. Stop on failures without bypass/retry loops.
Return via the picker to Macintosh HD and restore it as default. Publish only
sanitized observed outcomes. Stage A later tests only m1n1/P_NOP; Stage B separately
tests one-core Linux PID 1 and 60-second liveness. The result template now
separates controller output, screen observations, timing and macOS return.
No persistent USB Linux console or SSH is present. Blank screen means output
not observed; establish logging before another blind attempt.

**M1 offline preparation complete:** `tools/m1n1-client/stage-a-instructions.md`
contains the later authorized handshake checklist. Stage B evidence draft is
local/ignored at `build/native-intake/results/boot021-stage-b-prepared.md`,
pre-filled from the current template and verified package with provenance,
expected milestones and timing bounds. All 13 payload checksums still match;
boot021 and the clean client pin are unchanged. M1 read B's policy-result
handoff at `1607f2a`, without an independent target query. B integrated M1's
`1420572` report. Lab Recovery installation is now authorized as stated above;
live Stage A/B approvals remain pending. All live USB/target-version/native
tests are **NOT RUN**.

</details>

### Current boot-package assignment (user authorized 2026-10-13)

B now owns preparing/exporting the boot package, correcting the single-core
launcher and first-boot instructions, testing them in isolation and pushing
the M1 handoff. Work is in `native/boot/` and job 021; A's QEMU/latency work
is untouched. The M1 agent downloads/verifies and reports offline readiness.
**Earlier package-only boundary, superseded by the current lab authorization
above.** Partition changes and live native tests remain on hold.
Payload publication is authorized; these are open-source
build outputs, not Apple artifacts. Follow the corrected first-boot plan;
older statements about an empty APFS stub or persistent proxy console are
superseded. No native hardware success is claimed by this handoff.

B's next preparation milestone is complete: the user requested exact dedicated
entry steps while M1 verifies. `kernel/native-enablement/boot-entry-setup.md`
selects a second full macOS installation named `iLinux Boot Lab`, matching the
available 26.6.2 / 25G83 installer. It documents paired-Recovery checks,
lab-only policy/boot-object commands and macOS return. At that preparation
milestone no volume creation, policy change or reboot had run. The current
handoff above records subsequent installation and authorization; an offline
receipt alone does not authorize host changes.

**Download and verification result:** the matching 26.6.2 / 25G83 installer is
downloaded. User subsequently authorized resolving verification without
disabling security checks. Its original package passes Apple's signature and
Gatekeeper install assessment; all five signed entries and the installed
695 files/226 directories/26 symlinks match. Three executable signature checks
and eleven synthetic verifier regressions pass. The outer app's custom-omit-
rule rejection remains unchanged; no security exception or bypass was used.
See `native/boot/macos-installer-download.md` and D-046.
M1 has now published its observed offline results below and in `progress.md`.
USB/P_NOP, live target-version check, native m1n1, native Linux and native
Omarchy remain **NOT RUN**. The current authorization above supersedes the
earlier installer-launch and lab boot-security holds; native-test holds remain.

### M1 offline receipt: ready for coordination, physical testing on hold

Verified handoff commit: `58dc2baffceda76d546b0e6fb8f101089dfd35b8`.
Private prerelease `native-j716c-boot021` was downloaded and its archive
SHA-256 matched Git before extraction:
`b534680fc25dff78d8eaecfb96ed5b9733a3f408ae20cb4947722cb8163edc15`.
Offline launcher and intake verification passed for all 13 files; SHA256SUMS
matched tracked digest
`9d2b9ec1ae9dad601fb25a6536e838b57ab436160ab6ceddf208b764de41f581`.
Tests passed: **17 launcher, 7 intake, 2 fake-serial USB**. LLVM 23.1.3 passed
ARM64 assembly/link/objcopy/nm/disassembly. The clean client remains pinned
to `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.

M1's complete JSON receipt is local and ignored:
`build/native-intake/receipts/boot021.json` (2026-10-13 20:02:34 UTC).
It records `boot_authorized: false` and `target_version_observed_live: false`.
There are no offline verification blockers. USB discovery opened no port and
found no modem paths; it does not establish cable status. First live test is
still the separately authorized bounded handshake. Boot-entry provisioning
and explicit physical-test approval remain pending. B reviewed and integrated
this report (`dfdf8cf`) while completing installer content verification. The
subsequent normal GUI launch succeeded; installation is pending as recorded above.

### Second-machine checkout (2026-10-13)

The user designated a separate macOS computer as the second-machine agent.
Its checkout is `~/Documents/ilinux`, tracking the private
`https://github.com/nickyrice04/ilinux.git` repository. GitHub authentication
as `nickyrice04`, fetch access and account push permission are verified.
This role is distinct from research agent B and post-boot configuration
agent C. It supports the m1n1 USB proxy and cross-machine handoffs; USB
connectivity and native boot have not been tested by this setup.

The user explicitly authorized repository pushes for agent communication,
superseding the older local-only Git rule. Fetch and use `git pull --ff-only`
before work, commit explicit paths, then push without force. If another
machine advances the branch, fetch and reconcile before retrying; never
reset away another agent's work. Local advisory locks do not coordinate
separate computers: record ownership and handoffs here before shared work.
Credentials remain in the OS credential store, never in tracked files.
Ignored VM disks, build payloads and local third-party checkouts are not
downloaded by Git. Proxy-client dependencies now pass offline imports; see
`tools/m1n1-client/README.md`. LLVM 23.1.3 now passes offline ARM64 assembly,
link and disassembly. A bounded P_NOP-only USB check is prepared and fake-
transport tested. Physical connectivity and target boot-entry readiness
remain unverified; no target session has run.

**User direction (2026-10-13, package handoff):** the second-machine agent has
received B's corrected single-core package/launcher and completed offline
verification only. Keep the client pinned to the agreed target revision.
Do not run upstream `proxyclient/tools/linux.py`. First live test is the
separately authorized bounded USB handshake; thereafter record only approved
diagnostic boots. Intake requirements and the result template are in
`tools/m1n1-client/README.md`; current package instructions are in `native/boot/README.md`.

| Agent | Who | Owns |
|---|---|---|
| **A** | The session that wrote this plan (`AGENT_ID=agent-a`) | VM responsiveness: goals 2–3. QEMU source and patches (`virtualization/qemu/src/qemu`, `patches/qemu/`), the VM kernel config (`omarchy-arm64/kernel/linux-ilinux-vm/`), latency benchmarks |
| **B** | The second build agent (`AGENT_ID=agent-b`) | Goals 4–7: video default, native readiness (`kernel/`, new `virtualization/jobs/`), backup preparation, the configuration handoff kit |
| **C** | A configuration agent, later | Omarchy configuration on a natively booted install (goal 9). Starts only after gate N4 |

The user makes every gated decision (N1–N4 below). No agent changes boot
security, partitions, firmware or the macOS installation.

### Agent B scope update from the user (2026-10-13)

The user has directed B to focus on REA/backend setup and targeted macOS
binary research, with an evidence and implementation handoff for A. B will
leave A's wakeup, QEMU and display work untouched and defer live-guest video
changes while A owns that VM. B's current files are under
`reverse-engineering/rea-lab/` and
`reverse-engineering/findings/rea-native-2026-10-13/`. Analysis tools will run
in a separate diskless Linux job, never against the live Omarchy disk.
Build/analysis jobs must acquire `quiet` so A's measurements do not overlap.
The agent C configuration handoff remains required before native desktop use.

B milestone: REA/Ghidra works; original extraction/evidence tools and a
read-only startup-layout experiment pass ARM64 Linux tests. See
`reverse-engineering/findings/rea-native-2026-10-13/handoff.md` (F-070–F-072).
The analysis VM is stopped and B's locks are released. A's live VM, QEMU,
vmpoll and frame-rate work remain A-owned. The candidate native masks are
not validated MMIO semantics and must not be installed as a hardware fix.

B's next user-authorized pass covers GPU/display, network/Bluetooth, ANE's
ordinary host interface, camera, audio/microphone, HID input and shared
transports. Findings live in `reverse-engineering/findings/driver-interfaces-2026-10-13/`;
original protocol experiments live in `kernel/experiments/driver-contracts/`.
B retains the isolated lab and does not own A's live VM/video changes.
Protected services and personal sensor recordings remain excluded.

B completed F-073–F-075: 17 REA functions, independent byte/LLVM evidence,
a Linux-tested DockChannel HID patch and original offline N1 ACIPC queue
helpers. Full handoff: `reverse-engineering/findings/driver-interfaces-2026-10-13/handoff.md`.
The lab is stopped and B's `quiet` lock released. A's goal-5 native build
can apply `kernel/experiments/driver-contracts/dockchannel-hid/0001-dockchannel-hid-validate-input-bounds.patch`
to a disposable checkout and compile the full driver object. Do not install
it in the VM's virtio-input path or advertise native input as tested.

## Shared resources: rules

### Current assignment (user confirmed 2026-10-13)

A owns goals 5–7: the complete native kernel/schema build, first-boot
observation plan, backup preparation and C's configuration handoff. Goals
2–3 are checkpointed unless they block native development. B owns targeted
REA work on CPU startup, GPU/display and idle/DVFS, with original offline
experiments and findings for A. The older owner table and goal ordering
below are historical where they conflict with this assignment.

B's completed startup/idle pass is recorded in
`reverse-engineering/findings/cpu-startup-2026-10-13/`. Its optional startup
guard passed eight Linux cases with sanitizers and startup-object compilation;
the analysis VM is stopped and B's locks are released. B has not modified A's
kernel build jobs, native payloads or handoff kit. The dockchannel proxy is
not established as a Linux console; early-boot observability remains a
goal-5 prerequisite.

1. **Locks** (`tools/lock.sh`, advisory, stored in the gitignored
   `virtualization/run/locks`):
   * `vm`: hold it for any QEMU Omarchy VM console command, restart, or
     install into the guest. `tools/vm-restart.sh` refuses to restart while
     another agent holds it, so export `AGENT_ID`.
   * `quiet`: hold it for power and latency measurements. While someone holds
     it, nobody else builds, benchmarks or restarts a VM. Keep it short
     (usually 30 minutes or less); measurements are invalid without it.
   * `qemu-build`: QEMU and virglrenderer builds and `runtime/` installs.
   * `git-history`: history rewrites. Only with the user's OK, and only while
     no other agent is committing.

   Run `tools/lock.sh status` before heavy work. Release locks as soon as you
   are done. Never clear another agent's lock unless it is stale and the
   user agrees.
2. **Git:** one shared working tree and branch. Commit with explicit paths
   only: no `git add -A`, `git add .` or `git commit -a`. Never commit another
   agent's uncommitted files. Use the attribution line from your session
   instructions.
3. **Shared docs** (`progress.md`, `decisions.md`, the findings catalog,
   `blockers.md`, READMEs): re-read right before editing, make small
   targeted edits, and never rewrite a whole shared file from a stale copy.
   Each agent writes its own progress entry.
4. **ID ranges:** agent A uses F-054–F-069 and D-032–D-039. Agent B uses
   F-070–F-089 and D-040–D-049. Agent C uses F-090 and up, and D-050 and up.
5. **Native kernel builds** run in the separate job VM
   (`virtualization/jobs/`). They load the host heavily, so never run one
   during someone else's `quiet` window.
6. **The floating VM window** (`COCOA_FLOAT=1`, which keeps the VM window on
   screen) is for on-screen measurements only. Tell the user before a session
   that uses it.

## Goals, in order

| # | Goal | Owner | Done when |
|---|---|---|---|
| 1 | Commit the verified Mesa video work | A | Done: `47efd62` |
| 2 | **Cross-core wakeup latency.** Message passing between two processes takes 1.6 µs on one vCPU (macOS: 3.8 µs) but about 21 µs across vCPUs. QEMU uses Apple's hardware GIC (`kernel-irqchip=on`), so the leading suspect is an idle vCPU being parked and then woken through the macOS scheduler. Bounded spinning before parking (in QEMU's HVF idle path, and/or the guest's `cpuidle-haltpoll`, which our kernel does not build) is the candidate fix. Note: arm64 7.1.6 ignores `idle=poll` | A | Cross-vCPU pingpong and syscall improve measurably; idle power is unchanged within noise; the poll window is bounded and documented; new QEMU patch or kernel config committed |
| 3 | **F-050 frame-rate collapse:** 7–19 fps on alternating fresh boots. Re-test after goal 2, then trace DRM flips, fences and Hyprland frame callbacks during an affected boot | A | Cause identified with evidence; fixed or documented with a workaround |
| 4 | **Video fix as the default** (`mesa-virgl-video-ilinux`, now opt-in via `ilinux-video`). Do an on-screen playback and power check first | B | Plain `mpv`/FFmpeg use the fixed driver; pixel-exact and zero-copy regressions pass |
| 5 | **Native track, safe steps:** full kernel build and `dtbs_check` for `kernel/patches/t6050` in the job VM; a written first-boot plan (see gates) | B | Kernel links; schema warnings triaged; plan committed |
| 6 | **Backup preparation:** a scrub list (local paths, the test VM password), licences (GPL-2.0 for QEMU patches, MIT for virglrenderer and Mesa patches, a choice for our own code), and a plan to remove the 640 MB of Core ML weights from history or start fresh from a clean snapshot | B prepares; user approves; `git-history` lock to execute | Private repo ready to push on the user's go-ahead |
| 7 | **Configuration handoff kit for agent C** (below) | B | `native/handoff/` committed and reviewed by A |
| 8 | Native gates N1–N4 (below) | User decides; then A and B | Per gate |
| 9 | **Omarchy configuration on the native install** | C | Acceptance checks in the handoff kit pass |

Agents may pull work forward when blocked, but keep goal 2 before goal 3 (3
re-tests 2). Keep goal 4's guest changes out of the VM while agent A holds
the `vm` lock.

## Native gates (all user decisions)

* **N1. Prerequisites.**
  * A current full macOS backup (Time Machine or equivalent).
  * A second computer and a USB-C data cable for the pre-Linux m1n1 proxy.
    Native Linux output is initially attempted on the M5 framebuffer;
    no persistent USB Linux console is established.
  * A separately reviewed and authorized OS boot environment with Apple boot
    assets, paired recovery and its own custom boot policy. An empty APFS
    volume is insufficient. Exact layout and installation remain gated; see
    `kernel/native-enablement/first-boot-plan.md`.
* **N2. RAM-only boots** over USB from the second computer: kernel,
  initramfs and device tree, with nothing written to the Mac's disk. In
  order:
  1. single-core console;
  2. secondary CPU start-up (SMP);
  3. NVMe read-only identification;
  4. keyboard and trackpad;
  5. boot framebuffer.
* **N3. Linux root partition.** Resizing the APFS container is a separate
  user decision, made after another backup.
* **N4. Omarchy installed natively.** Hand over to agent C with the kit.

## Configuration handoff kit (goal 7, for agent C)

Agent B writes it in `native/handoff/`. It must cover:

1. **VM-only files that must not be applied natively:**
   * `omarchy-arm64/configuration/vm-integration/*`: host bridge, vdagent,
     NAT DNS, `MESA_VK_WSI_DEBUG=nowlts`, the VM `mpv.conf`, autologin;
   * the VM kernel package.
2. **What carries over:**
   * `omarchy-qos` and the QoS tiers;
   * kernel options (16 KiB pages, uclamp);
   * the t6050 energy-model and OPP drafts (unvalidated);
   * the aarch64-apple package choices.
3. **A hardware matrix for the boot under test:** what works, what is
   absent, and the fallback for each absent device:
   * llvmpipe instead of GPU acceleration;
   * USB Ethernet or tethering for networking, since N1 Wi-Fi has no driver;
   * an external libfprint reader or FIDO2 key instead of Touch ID;
   * no Neural Engine.
4. **Access:** how agent C reaches the system. It needs network for itself:
   USB Ethernet, or running from the second computer over the serial or
   SSH link.
5. **Acceptance checks:**
   * all 18 CPUs and their capacities;
   * storage health;
   * display and input;
   * audio;
   * idle power with the WFI workaround in place;
   * suspend (expected not to work yet);
   * Omarchy's own test suite where applicable.
6. **Guardrails:**
   * never touch macOS volumes or the APFS container;
   * no firmware, SEP or boot-policy changes;
   * no credential handling;
   * record every change as a package or config file in this repository.

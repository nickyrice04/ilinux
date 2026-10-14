# Stage B attempt 2: prepared-DT framebuffer rejection; Linux NOT RUN

Session: 2026-10-13 local (America/New_York), 2026-10-14 UTC.
Execution/handoff commit: `993a6af8a64b4322e9cec598cf1f741cb60ad960`.
The human reported `Running proxy` and explicitly authorized one corrected
attempt. That single attempt is consumed; no retry or new live action is authorized.
Attempt 1's report and ignored evidence remain unchanged.

## Observed result

* Start UTC: **2026-10-14T01:58:58.489367+00:00**.
  End UTC: **2026-10-14T01:59:08.692220+00:00**.
  **Exit 1, elapsed 10.202 seconds**, one launcher invocation, no retry.
* Package and unique primary USB checks passed. Target chip, packaged m1n1
  marker and initial secondary-state checks passed. Live packaged-marker
  verification is **PASS** for this attempt, not a full binary attestation.
* Corrected root ADT access reached **Board/framebuffer PASS**. The initial
  m1n1 boot-argument framebuffer base/width/height were nonzero. The earlier
  root-lookup defect did not recur on this path.
* **DT, initramfs and kernel upload to RAM completed.** m1n1 DT preparation
  returned success, and the controller parsed/read-checked the prepared DT.
* Exact stop: **`ValueError: no enabled boot framebuffer; observation path absent`**.
  Safe traceback identifies `launch.py:113` (`launch_session`) calling
  `fdt.py:90` (`check_stage_b`). The final DT did not satisfy the enabled
  `simple-framebuffer` requirement. Missing versus disabled/mismatched node
  is not distinguished by this error; no raw prepared DT was retained.
* **No handoff checkpoint or `kboot_boot` call was reached. Linux NOT RUN.**
  Kernel/PID 1/online-CPU/liveness screen milestones were not reached. The
  120-second post-handoff observation window did not start.
* Human subsequently supplied a photo and confirms return to the usual
  **Macintosh HD desktop**. Fresh post-return build/default/security checks
  remain NOT CHECKED. Successful desktop return does not independently prove
  the current policy or default selection.
* Photo shows m1n1 CPU disabling/topology pruning and DT warnings, ending at
  **`FDT prepared`** (address omitted). Visible non-sensitive messages include
  `FDT: unknown compatible, skip display reserved-memory setup`,
  `ADT: GPU: unsupported chip!`, and `FDT: '/reserved-memory' not found`.
  These are m1n1 preparation output, not Linux kernel/PID 1 milestones.
* User thought the screen froze. The still image does not establish a hang;
  it is consistent with completed m1n1 DT preparation followed by the controller
  framebuffer rejection. These warnings alone do not establish which condition
  caused the missing enabled framebuffer; keep the recorded rejection precise.
* No volume, boot-policy, boot-object or default-startup changes were issued
  by M1. Target RAM writes and DT preparation did occur; this was not read-only.
  The transport cleanup path ran and no close error was reported. No reconnect.

## Provenance and evidence handling

* Ordinary offline package verification after pull: PASS, exit 0. Existing
  unchanged-code results remain 31 launcher + 4 pinned-ADT + 20 USB + 7 intake.
* Launcher SHA-256:
  `d3dcebceaaab2716cf7e4dc51dfaac10be8cb01eca308409f7574311b69b821f`.
* USB selector SHA-256:
  `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`.
* Boot021 and clean client pin
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba` are unchanged.
* Separate ignored evidence: `build/native-intake/results/boot021-stage-b-attempt2.json`
  and `.md`. JSON includes timestamps, fixed checkpoints, code/procedure/payload
  digests and safe module/function/line traceback metadata.
* The unchanged launcher's `main(argv)` was invoked exactly once with the
  documented arguments through a sanitized logging wrapper, using `run.sh`
  for pin/toolchain setup. All launcher gates and cleanup remained intact.
  The wrapper preserved the reviewed fixed error text and withheld unreviewed
  output. No raw ADT, target memory dump, serial-bearing path or photo was saved.

## Next action

Macintosh HD return is user-confirmed. M5 should perform read-only protection
and default-startup checks. Investigate framebuffer setup in the packaged DT and pinned m1n1
source offline; do not remove the observation gate or infer Linux/display
hardware failure from a controller preflight rejection. No rebuild, reinstall,
security change, retry or additional native session was performed by this task.
Any later live attempt requires a new reviewed handoff and user instruction.

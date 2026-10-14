# Stage A controller instructions — authorized, execution pending

Updated after reviewed M1 handoff `c6f2c6f`. The custom boot object is installed;
incidental m1n1 startup reached `Running proxy...`, and original-macOS return
checks are complete. On 2026-10-13 the user explicitly authorized **one m1n1
boot, one USB handshake, then return to Macintosh HD**, retaining Full Security.
This supersedes the previous Stage A hold; no repeat approval is needed for
this exact session. Stage B/Linux remains unauthorized. Do not repeat Recovery
or boot-object installation. All actual Stage A results remain NOT RUN.

## Before the authorized session

* B's post-return review confirms original build/FileVault/SIP/authenticated-root.
  The user's fresh read-only policy result is original Full/lab Permissive,
  both exit 0. M1 has not independently queried M5 policy.
* The lab Recovery/pairing/policy/custom-boot procedure succeeded as recorded
  by M1. Use the installed entry; keep Macintosh HD as the default and use
  the held-power startup picker for the test. No policy command belongs in it.
* Stage A authorization is recorded above. Backup completion is user-confirmed.
  Keep both Macs powered, the direct USB data cable connected and the M5 screen
  visible. M1 pulls this handoff and confirms readiness before the M5 shuts down.
* Preserve boot021 and clean client revision
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Record actual session time and
  approval scope; reuse the offline receipt only while artifacts are unchanged.

## Stage A only — commands below are NOT RUN

1. Save M5 work and shut down normally. Hold power continuously until startup
   options load, then select **iLinux Boot Lab → Continue** for this boot.
   Leave Macintosh HD as the default; do not use Startup Disk settings or
   choose Options/Recovery. Record visible non-sensitive m1n1 text/version,
   or NOT OBSERVED. The M5 desktop agent is offline during the test; M1 guides
   the human. A missing entry or unexpected recovery/security prompt means stop.
2. From the controller repository root, discover actual USB paths:

   ```sh
   tools/m1n1-client/run.sh tools/m1n1-client/usb-check.py
   ```

   Discovery opens no port. Choose the actual primary `P_01` path; `P_03`
   is not the primary proxy. If none appears or identification is ambiguous,
   stop and report it; do not infer a failed cable from absence alone.
3. With the recorded authorization and verified actual path, run one handshake.
   This example path must match the discovered device before use:

   ```sh
   tools/m1n1-client/run.sh tools/m1n1-client/usb-check.py --connect /dev/cu.usbmodemP_01
   ```

   Record start/end timestamps, elapsed time, printed result and exit status.
   The checker sends only P_NOP, has a 10-second handshake deadline and closes
   its port. Opening the serial device can interrupt m1n1 autoboot into proxy
   mode. No upstream shell, feature negotiation, register/memory query or
   launcher belongs in Stage A. Stop after any failure; no automatic retries.
4. A successful P_NOP proves a responding proxy only. It does not identify
   the target's exact build or establish Linux execution. Keep the live
   target-version check NOT RUN; a visible version is a separate observation.
5. After either handshake success or failure, close the test session and return
   to Macintosh HD. Hold the M5 power button until off, release it, then hold
   it continuously again until startup options load. Select **Macintosh HD →
   Continue**. Do not retry the handshake or boot Linux. M5/user records return,
   build and protection outcomes. Default should remain Macintosh HD. Do not
   infer return or protection checks from P_NOP. If the original entry is
   absent/unbootable, stop and report; no automatic restore/revive or policy reset.
6. Review Stage A before seeking separate Stage B authorization. Do not
   chain a Linux launch onto the handshake.

M1 records observed start/end times, actual device path (local only), command
exit/result, elapsed time, non-sensitive screen observations and return outcome.
Commit/push sanitized summaries to `progress.md` and `coordination.md`; retain
NOT RUN for the live target-version query and Stage B/Linux. No raw screen
photos, identifiers or policy dumps in Git. If a failure prevents the handshake,
record why it was NOT RUN rather than treating discovery as a successful test.

On return, the human can run this original read-only helper in the M5 Terminal:

```sh
sudo /usr/bin/python3 -I '/Users/nickyrice/Documents/iLinux/ilinux-publish/build/installer-verification/check-boot-policies.py' --expected-lab Permissive
```

Expected original Full / lab Permissive, both exit 0. Enter the password only
in Terminal. B will also check build/FileVault/SIP/authenticated-root read-only;
choose the original by its name in the current csrutil prompt, not a cached index.

## Stage B evidence prepared separately

Local draft: `build/native-intake/results/boot021-stage-b-prepared.md`.
It pre-fills provenance and expected observations from the tracked launcher
and receipt, not measured results. The controller's 180-second deadline is
distinct from the proposed screen limit of 120 seconds after handoff.
Stop observation at the 60-second liveness message, explicit failure or that
screen limit, whichever comes first, then follow the agreed return procedure.

Native USB ends at handoff. Record readable kernel/PID-1/CPU/heartbeat evidence
from the M5 screen. Blank or missed output is NOT OBSERVED; establish logging
before another blind attempt. Keep raw identifiers, ADT, policy dumps and
recordings out of Git. Publish only reviewed, sanitized observations.

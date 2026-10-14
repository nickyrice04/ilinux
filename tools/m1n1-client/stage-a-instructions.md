# Stage A controller instructions — naming fix tested offline

The first authorized controlled boot reached `Running proxy...`. Discovery
found two modem callouts but the old checker assumed a `P_01` suffix, so it
stopped before opening a port. P_NOP was **NOT RUN**. The user confirms return
to Macintosh HD. The current task fixes discovery offline; do not automatically
boot again or connect. Use the checklist when the user starts the next Stage A
attempt. Stage B/Linux and live target-version checks remain **NOT RUN**.
Do not repeat Recovery or boot-object installation.

## Before the authorized session

* B's post-return review confirms original build/FileVault/SIP/authenticated-root.
  The user's fresh read-only policy result is original Full/lab Permissive,
  both exit 0. M1 has not independently queried M5 policy.
* The lab Recovery/pairing/policy/custom-boot procedure succeeded as recorded
  by M1. Use the installed entry; keep Macintosh HD as the default and use
  the held-power startup picker for the test. No policy command belongs in it.
* Confirm the user is starting the next Stage A attempt. Backup completion is user-confirmed.
  Keep both Macs powered, the direct USB data cable connected and the M5 screen
  visible. M1 pulls this handoff and confirms readiness before the M5 shuts down.
* Preserve boot021 and clean client revision
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Record actual session time and
  approval scope; reuse the offline receipt only while artifacts are unchanged.

## Next Stage A attempt — handshake still NOT RUN

1. Save M5 work and shut down normally. Hold power continuously until startup
   options load, then select **iLinux Boot Lab → Continue** for this boot.
   Leave Macintosh HD as the default; do not use Startup Disk settings or
   choose Options/Recovery. Record visible non-sensitive m1n1 text/version,
   or NOT OBSERVED. The M5 desktop agent is offline during the test; M1 guides
   the human. A missing entry or unexpected recovery/security prompt means stop.
2. From the controller repository root, identify the primary USB interface:

   ```sh
   tools/m1n1-client/run.sh tools/m1n1-client/usb-check.py
   ```

   Discovery reads cached macOS IORegistry metadata without opening a port.
   Require exactly one m1n1 **VID:PID 1209:316d, CDC data interface 1** and a
   currently present character-device callout. Interface 3 is the secondary
   virtual UART. Names may contain the device serial; they are kept in memory
   and redacted from output. No suffix, sort-order or USB0/USB1 guess is used.
   Missing metadata, no match or multiple primaries means stop; return code 2
   is a discovery stop, not a failed handshake. Do not infer cable failure.
3. During the agreed session, run one handshake. This re-reads metadata and
   selects the sole verified primary without entering a device path:

   ```sh
   tools/m1n1-client/run.sh tools/m1n1-client/usb-check.py --connect
   ```

   Record the printed UTC start/end timestamps, elapsed time and command exit
   status: 0 = P_NOP replied, 1 = handshake failed, 2 = discovery stopped before
   opening. Discovery-mode exit 0 means identified only, not handshake success.
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

M1 records observed start/end times, interface number/VID/PID, command exit/result,
elapsed time, non-sensitive screen observations and return outcome. Keep device
paths and raw registry data in memory only; they may contain serial numbers.
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

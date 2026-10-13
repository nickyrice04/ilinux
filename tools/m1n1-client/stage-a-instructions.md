# Stage A controller instructions — prepared offline, NOT RUN

Prepared against handoff `1607f2a` (includes `2438c01`). This checklist does
not authorize Recovery, policy/custom-boot changes or a live USB connection.
The staged lab Data file is not yet an installed custom boot object.

## Before a later authorized session

* B's handoff reports user-supplied read-only policy results: original Full,
  lab Full, both exit 0. M1 has not independently queried M5 policy.
* Wait for explicit authorization and M5 confirmation that the separate
  lab-only Recovery/pairing/policy/custom-boot procedure succeeded. Do not
  run those M5 commands on this controller.
* Require explicit Stage A authorization, backup confirmation, power to both
  Macs, direct USB data cable, the M5 screen visible and the agreed return path.
* Preserve boot021 and clean client revision
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Record actual session time and
  approval scope; reuse the offline receipt only while artifacts are unchanged.

## Stage A only — commands below are NOT RUN

1. Human boots only the approved lab m1n1 entry using the agreed M5 procedure.
   Record visible non-sensitive m1n1 text/version, or NOT OBSERVED.
2. From the controller repository root, discover actual USB paths:

   ```sh
   tools/m1n1-client/run.sh tools/m1n1-client/usb-check.py
   ```

   Discovery opens no port. Choose the actual primary `P_01` path; `P_03`
   is not the primary proxy. If none appears or identification is ambiguous,
   stop and report it; do not infer a failed cable from absence alone.
3. After verifying authorization and the actual path, run one handshake.
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
5. Return the M5 to original Macintosh HD using the reviewed procedure in
   `kernel/native-enablement/boot-entry-setup.md` section 7. M5/user records
   return, build and protection outcomes. Do not infer those from P_NOP.
6. Review Stage A before seeking separate Stage B authorization. Do not
   chain a Linux launch onto the handshake.

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

# Approved native diagnostic session — NOT RUN

Copy this template into ignored `build/native-intake/results/` for each
approved session. Fill only observed results; distinguish FAIL, NOT OBSERVED
and NOT RUN. Do not store serial numbers, UUIDs, MAC addresses, raw ADT or
other personal identifiers. Publish only a reviewed, sanitized summary.

* Session date/time and time zone:
* User's approved scope and backup-complete confirmation:
* Sender handoff / package ID:
* Verified receipt path and SHA256SUMS digest:
* Target's declared m1n1 revision / pinned client revision:
* Corrected single-core launcher path and SHA-256:
* Reviewed boot-entry procedure path and SHA-256:
* First live test — bounded P_NOP handshake: NOT RUN
* Handshake timestamp, elapsed time and result:
* Visible m1n1 marker/version: NOT OBSERVED (P_NOP alone does not verify it)
* Stage A return to original macOS/build/protection checks: NOT RUN
* Decision to proceed / reason to stop:

For each separately approved diagnostic boot:

* Exact launcher invocation and kernel command line:
* Controller output/exit status and last preflight checkpoint:
* Handoff message observed and local timestamp: NOT OBSERVED
* Kernel / DTB / initramfs SHA-256 (from verified receipt):
* Expected observation and maximum observation duration:
* Actual console milestone reached:
* PID 1 message, model string, online CPU count, heartbeat: NOT OBSERVED
* First/last readable kernel line and verbatim non-sensitive panic/error:
* CPU online mask; memory/interrupt excerpt if readable: NOT OBSERVED
* Explicit 60-second liveness message: NOT OBSERVED
* Observation stop reason: success / explicit failure / 120-second screen limit / other
* Result: NOT RUN
* Failure/timeout checkpoint and recovery outcome:
* Reviewed evidence reference and limitations:
* Next action and approval status:

The 180-second controller deadline is distinct from the proposed 120-second
post-handoff screen-observation limit. USB ends at native handoff; absence of
subsequent USB output is not a Linux failure. If the screen is blank, record
NOT OBSERVED and establish a logging path before another blind attempt.

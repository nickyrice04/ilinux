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
* Decision to proceed / reason to stop:

For each separately approved diagnostic boot:

* Exact launcher invocation and kernel command line:
* Kernel / DTB / initramfs SHA-256 (from verified receipt):
* Expected observation and maximum observation duration:
* Actual console milestone reached:
* PID 1 message, model string, online CPU count, heartbeat: NOT OBSERVED
* Result: NOT RUN
* Failure/timeout checkpoint and recovery outcome:
* Reviewed evidence reference and limitations:
* Next action and approval status:

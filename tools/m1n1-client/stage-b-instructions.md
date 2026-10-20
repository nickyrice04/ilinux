# Current native handoff — attempt 28 CPU observation

M1: follow **[attempt28-instructions.md](attempt28-instructions.md)** and
[its validation/pins](../../native/boot/attempt28/validation.md).
Read the complete new checklist before any command. It uses the new
`cpu-observe` profile and **two new private images**. The old `ramroot` profile
and attempt-27 files are not this CPU experiment.

The user authorized CPU preparation, offline testing and publication. First
verify the published commit, unchanged boot042 package and both new images,
then report offline readiness with native/live **NOT RUN**. Wait for the human
to start the M5's existing iLinux Boot Lab entry before the one boot/send.
No native attempt is started by pulling the repository.

Attempt 28 identifies the actual boot core, observes its command state through
an explicitly no-write driver, and runs short CPU/memory/desktop measurements.
It keeps one core, the working USB/keyboard path, the RAM root, existing idle
restrictions and disabled storage. No frequency/voltage increase, SMP, Wi-Fi,
SSD or agent setup is part of this attempt. Do not add a live experiment if
collection succeeds or its state mapping is unfamiliar.

Keep Macintosh HD intact, at Full Security and as the default. No boot policy,
Recovery, installer, volume, firmware or installed-m1n1 change. Repeated routine
policy checks remain waived; the previous policy values are last reported.

Attempt 27 is consumed. Its [result](../../native/boot/stage-b-2026-10-20-attempt27-result.md)
records successful delivery/typing, remaining delay, the key-parser mistake
and deadline overrun. Its old checklist is retained in Git at
`a6ad886:tools/m1n1-client/stage-b-instructions.md`; do not replay it. The old
storage-attempt-28 assignment is superseded by the separate CPU observation.

# Current handoff — 31F vector-first CPU entry and core topology

31E is consumed; **31F native execution is NOT RUN**. Follow
[attempt31f-instructions.md](attempt31f-instructions.md): offline intake,
publish M1 readiness, fresh human M5 lab start, one supervised controller,
then immediate Macintosh HD return. A healthy M1 needs no routine restart.
No new image transfer, installation, security change or policy-check loop.

31E verified CPU0 code publication but observed no CPU1 record. The new original
168-byte recorder writes a marker before system-register reads or identity
filtering, then records identity, EL and cache state in separate phases. It
replays the original vector instruction. Unexpected identities and partial
progress are retained; progress before the second startup store stops it.
Only verified CPU1 arrival and a complete record allow eight timer callbacks
and a final park check. No Linux continuation or additional CPU start.

The exact topology is 12 Performance cores (two ADT M clusters) and 6 Super
cores (one ADT P cluster). CPU1 is in CPU0's Performance cluster. Current
Linux capacity numbers are uncalibrated; core entry does not prove scheduler,
frequency, memory, GPU or efficiency parity.

Review and validation: `native/boot/attempt31f/`. The instruction model cannot
prove physical reset, firmware or cache visibility. Vector+0 also serves a
synchronous exception slot, so a marker alone does not prove reset provenance.
Preserve installed boot021, all consumed sources/receipts and macOS.

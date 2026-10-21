# Current native handoff — 31C corrected CPU1 memory gate

Read [attempt31c-instructions.md](attempt31c-instructions.md).
31B stopped before allocation or CPU startup: its address ceiling was below
this M5's physical DRAM. The new gate checks the actual BootArgs usable range
against this machine's observed DRAM and the target ADT. CPU1 startup code is
unchanged. Review and evidence: `native/boot/attempt31c/review.md`.

M5 offline preparation PASS: 60 Python methods and the real pinned parsers/
high-address serializer PASS. **Native 31C NOT RUN; M1 intake pending.**
M1 verifies the new source manifest and retained boot042 package, publishes
readiness, then waits for a fresh human start. Existing Boot Lab/boot021,
one CPU1 entry/two-request test, immediate Macintosh HD return.

Both 31A and 31B are consumed; preserve their receipts. 31C uses a distinct
fixed directory and literal confirmation. No new image/root transfer, Linux
launch, chainload, installation or security/default/volume change. Routine
policy checks remain waived. Old copy31/rebuilt m1n1 remain held.

Use `native/boot/attempt31c/source-sha256.txt`. Earlier manifests remain
historical and pin earlier versions of this pointer; do not regenerate them.
Bootloader entry success would precede two-core Linux/timer/IPI/coherence and
renderer work; it is not proof of Linux SMP, performance or efficiency.

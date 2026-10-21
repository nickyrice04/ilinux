# Current native handoff — 31D CPU1 diagnostic-console experiment

Read [attempt31d-instructions.md](attempt31d-instructions.md).
31C is consumed: RAM gate passed, both CPU1 startup writes acknowledged,
arrival timed out; usual Macintosh HD return confirmed. No Linux boot.

31D tests a source-backed hypothesis: unbounded diagnostic UART output before
the arrival flag. It zeros two diagnostic UART RAM variables, cache-publishes
them before start, retains direct USB, and records partial CPU1 reset/spin
identity. Existing installed boot021, unchanged start/request sequence, no
code/RVBAR/power/security/volume change or new MMIO probe. No files to AirDrop.

M5 offline preparation PASS: 73 Python methods, actual client/parsers, compiled
UART harness normal/ASan/UBSan, exact compiled-image binding audit. Fresh REA
and independent byte/LLVM cross-checks inform the decision; no native fix is
yet established. **M1 intake pending; native31D NOT RUN.**

Use `native/boot/attempt31d/source-sha256.txt`. M1 publishes offline readiness,
then waits for a fresh human start and 90-second timer. One bounded CPU1 test,
then immediately Macintosh HD, even on success. Preserve every prior receipt;
no retry, reconnect or Linux continuation. Routine policy rechecks stay waived.

Review: `native/boot/attempt31d/review.md`. CPU1 entry success precedes two-core
Linux timer/IPI/coherency and renderer tests. Performance/efficiency are unproven.

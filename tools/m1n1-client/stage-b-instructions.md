# Current handoff — 31E early CPU1 recorder

Follow [attempt31e-instructions.md](attempt31e-instructions.md): offline intake,
M1 readiness report, fresh human M5 lab start, exactly one supervised controller,
then immediate Macintosh HD return. M1 does not need an automatic reboot if its
helper-health checks pass. No new image transfer, installation or policy check.

31D is consumed. The new controller adds an original stackless recorder in
loaded RAM through the existing writable alias, fixed translation/readback and
cache-publication checks, and guard-free CPU1 startup stores. It preserves
partial observations; only verified arrival plus a complete record permits
eight bounded timer callbacks and a final park check. No Linux continuation,
additional core, RVBAR change, security change or storage access.

Offline validation and review are in `native/boot/attempt31e/`:
`controller-validation.md`, `controller-review.md`, `publication-review.md`.
Native31E/CPU1/Linux SMP remain **NOT RUN** until the M1 reports this attempt.
The older offline-only HOLD applies to the earlier proposal, superseded by
this reviewed controller handoff. Preserve all consumed sources and receipts.

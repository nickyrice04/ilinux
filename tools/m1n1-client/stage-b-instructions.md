# Current handoff — 31G CPU1 power-state and entry observations

31F is consumed. **Native31G/CPU1/Linux SMP NOT RUN.** Follow only
[attempt31g-instructions.md](attempt31g-instructions.md): offline intake,
publish M1 readiness, fresh human M5 lab start, one supervised controller,
then immediate Macintosh HD return. A healthy M1 needs no routine restart.
No image transfer, installation, security change or policy-check loop.

31G retains the existing vector recorder and CPU1 start addresses/masks,
adds strict live topology/power-domain binding, and at most8 fixed-width
power-state reads. This distinguishes power-state observations from code-entry
observations; neither acknowledged starts nor an active PS field prove CPU1
execution. No PS writes or additional cores. Unexpected state/error stops.

REA and safe macOS topology collection also identified the later-cluster
four-core-mask assumption: this machine has12 Performance cores (ADT M) and6
Super cores (ADT P), in three clusters of6. An original table-driven planner
covers all18, but native operations remain limited to CPU1.

Review/validation: `native/boot/attempt31g/` and
`research/native31g-reset-routing.md`. Preserve installed boot021 and all
consumed sources/receipts. VM tests do not emulate Apple firmware/power/reset.

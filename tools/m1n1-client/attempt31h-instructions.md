# M1: 31G consumed; 31H offline investigation only

**No restart or live command is requested. 31H has no native-ready controller.**
The current decision is [the M5 post-31G plan](../../native/boot/attempt31h-plan.md).
Older README/stage-B readiness directions are frozen inputs to consumed
attempts; use current AGENTS.md and coordination.md for order of work.

31G observed CPU1 PS actual 0 → 15 after the second start, with no CPU1
marker. Keep the report, private receipts and source pins intact. Do not rerun
31G, extend timeouts, adjust power registers or reinstall anything.

Useful optional offline review:

1. Review the new eight-test synthetic reset-format audit. It proves that
   prior reports discarded fields; it does not prove bit11 is an address.
2. If existing sanitized local evidence independently describes the reset
   register format, identify its provenance. Do not collect new target data,
   publish raw mirrors/Apple bytes, or assume discarded bits were zero.
3. Report any contradiction to the plan through the repository. No routine
   M1 restart, policy check, image transfer or lab boot is needed.

M5 owns the offline artifact/entry-contract work and future controller.
M1 intake, exact new pins, tests, live command and a human restart cue will
come in a separately reviewed handoff. Linux SMP remains unverified.

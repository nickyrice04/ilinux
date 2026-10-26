# 31AF immutable entry diagnostic

This original-only package replaces the observer's unqualified record/stack
dependency with a register-only path. The dedicated monitor reservation is never
used as observer scratch memory. The only intended memory stores draw a bounded
128×64 centered checkerboard in the validated framebuffer. It does not invoke
monitor services, start another CPU or boot Linux.

Read [the decision](../../../research/native31af-decision.md),
[public contract](../../../research/native31af-public-contract.md),
[manifest](manifest.json), [validation](validation.json) and
[M1 handoff](../../../tools/m1n1-client/attempt31af-instructions.md).

`verify.py` checks the archive against the manifest from reviewed Git before
reading its members; it does not execute or install them. Reviewed source
generates independent one-paste Install/Rollback blocks. No clipboard smoke step
is needed. Native changes require approval of the exact new image and full
install/one timed observation/exact boot021 rollback/original-return sequence.

All 31AE sources, reviews, authorization and physical result remain frozen.
Installation, firmware entry, visible marker, live target version, Linux, SMP,
GPU and performance are distinct outcomes. Prior installation success is not
promoted to native execution success, and a missing marker is not Apple-only
proof. Keep Macintosh HD Full Security and the existing lab/restore arrangement.

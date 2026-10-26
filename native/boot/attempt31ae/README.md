# 31AE: DATA-before-code resident-entry diagnostic

This original-only package repairs the exact 31AD installer arithmetic error.
Read the [findings](../../../research/native31ae-data-order.md),
[validation](validation.json), [delivery pins](manifest.json) and
[M1 instructions](../../../tools/m1n1-client/attempt31ae-instructions.md).

The frozen 31AD image reproduces the reported error offline. The new image
derives all fourteen boot properties with Apple's read-only inspector and passes
the stricter original format validator. GNU two-base linking is byte-identical;
the complete payload passes 26 QEMU cases. These tests do not establish native
installer/firmware acceptance or SMP. No host boot change was performed.

`verify.py` verifies the archive against this Git manifest before reading its
members, rejects unsafe/link/duplicate/extra entries and never executes data.
M1 reviews exact pins and regenerates independent one-paste install/rollback
pages using `tools/recovery31ae/prepare.py`. An offline review does not authorize
a native write. The consumed 31AD test is not retried.

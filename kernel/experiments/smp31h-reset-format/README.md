# Offline reset-format evidence audit

This original Python experiment demonstrates information lost by the frozen
31A RVBAR classifier. It does not read hardware, import a target client,
implement a CPU driver or determine the t6050 register format.

From the repository root:

```sh
/usr/bin/python3 -I kernel/experiments/smp31h-reset-format/test_audit.py
/usr/bin/python3 -I kernel/experiments/smp31h-reset-format/audit.py
```

**Validation, 2026-10-21:** eight unittest methods PASS on macOS using its
Python interpreter. The CLI uses synthetic values only: old classification
collides, new classification distinguishes, bit11 address meaning remains
NOT_ESTABLISHED, hardware operations zero. No VM or native CPU experiment ran.

`classify()` separates the legacy page/lock interpretation from unknown low
and high set bits. It emits no absolute address and always marks exact entry
offset and effective reset route UNKNOWN. Unknown bits are evidence, not
permission to reinterpret or modify a register. This is an offline analysis
format, not an approved public schema for future target captures; the next
controller must separately review bounded classifications for publication.

The test imports the frozen original classifier to reproduce its actual
collision for synthetic `base|1` and `base|0x801`. Input checks reject invalid
width/type, sentinels and a misaligned image base. Other tests cover omitted
bit preservation and distinguish a different legacy page. This prevents
accidentally upgrading a page match into proof of an exact reset destination.

See [the 31H plan](../../../native/boot/attempt31h-plan.md). Native 31H is
NOT RUN; there is no live mode or restart instruction in this directory.

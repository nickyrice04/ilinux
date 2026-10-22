# 31H reset-format and opaque CPU-state observations

The original eight-test `audit.py` regression below remains a historical
demonstration of information loss; by itself it cannot establish bit semantics.
The subsequent matching-firmware REA finding establishes a static bits41:11
format, while its reviewed caller aligns to4KiB. See
[the current findings](../../../research/native31h-reset-entry.md).

`observer.py` preserves and classifies the controller's two existing RVBAR
reads without issuing new requests. It commits a row only after the immediate
exception acknowledgement, keeps raw words transient, and restores the
original proxy after preflight. Its bounded firmware-format relations are not
effective-entry claims. `test_observer.py` covers partial failures, privacy,
bit11/41/42 boundaries and invalid inputs.

`cpu_state.py` is a pure four-pair tracker for a bounded exploratory32-bit
CPU_IMPL+0x100 observation. It retains only low bytes/comparisons, never full
words. Every intent/result is durably offered to the caller; any error freezes
the tracker. Its tests cover every read-failure position, journal failure,
invalid words, reentrancy and interruptions. The component does not read
hardware, select a transport, or assign t6050 register semantics.

The31H controller supplies live ADT/translation binding and guarded baseline
versus guard-free post-start transport. VM tests validate our implementation,
not Apple's register safety, reset firmware or coherence. Native31H NOT RUN.

## Historical synthetic regression

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
NOT_ESTABLISHED, hardware operations zero. No VM or native CPU experiment ran
in that initial audit.

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

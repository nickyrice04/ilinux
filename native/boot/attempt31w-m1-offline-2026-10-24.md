# 31W — independent M1 offline pressure-composition review

**OFFLINE_PASS_NATIVE_HOLD, 2026-10-24 Eastern. Native31W HOLD / NOT RUN.**
Reviewed on `0f382bb74c2c0783a53cb8a41d1a900d9a6c82e8`, pulled cleanly from
`9befeb3`. This outstanding31W review is separate from31X research and31Y tests.
[Reviewed metadata](attempt31w-m1-offline-2026-10-24.json).

The documented isolated-Python command exited **0 in9.555s**. **509 pins /
243 Python methods /111 portable C groups PASS**, no skips or repairs. Actual
M1 tools: Python3.13.5 and Apple clang17.0.0 (clang-1700.3.19.1). Prior234 Python/
103 C plus new9 Python/8 C passed. Strict C11/O2 warning builds and exact component
success tokens passed; compiler temporaries were removed. New composition tests
cover256 empty,256 near-full and256 full positions, exact note/order/binding,
false acceptance with zero status, effectful failures, reentrancy and one attempt.

Review output is byte-identical to released host/curated/VM output:
`494f820637d72344701dc4663806c110e8bfb7d6e6cfe0e525ce93485908cf6c`.
Manifest SHA-256:
`e1690dd97e55c88dbbb80abc853269ec315be8108a63eeda19d0184ba2cda89c`.
Linux ASan/UBSan and VM083 were **NOT RUN on M1**; M5's sanitizer result is
separate evidence for the new eight groups, not a repeat sanitizer run of all111.

Read the original code/header/tests/README, intake and all three31W notes with
validation limits. **No actionable issue in the documented offline contract.**
The outer API captures validated31V state without callbacks. At the one-free-slot
snapshot it requests one opaque note before record copy/publication; ordinary
positions skip it and full refuses without waiting. Explicit note acceptance is
independent of status, so suppressed/uncertain zero-status notes stop before
copying. Later write/publication uncertainty retains the embedded31V receipt.
Reentrant outer calls are refused and terminal objects cannot be reused.

Caller serialization, stable acquired indices, sole-producer ownership,
nonaliasing, callback/context lifetime and platform-qualified DMA ordering remain
required through note and publication. Only the outer API may drive its embedded
31V object. Provider role0/selector0x21 values do not prove actual provider admission
or endpoint identity. The same word is called halt by another firmware comparator;
no benign wake/flush meaning is established. A note before a record exists cannot
acknowledge it. There is no native transport, GPU readiness or performance result.

M5's one CPU primary-entry query and two GPU queries remain separate retained
static evidence, not reproduced on M1. The primary-entry context and conditional
extension are not a native callable bootstrap or CPU1 release. Removed-block and
prior cross-boundary/truncation refusals remain intact. Firmware restriction is
plausible but an Apple-only necessity is unproved.31X/Y later refine the software
route; this historical31W stop decision does not override their new offline work.

REA/private decoding/evaluators, full symbols, upstream builds/refetch, Linux
sanitizers, VM execution and live checks **NOT RUN on M1**. No third-party source
or client imported/executed. No native operation, USB, transfer, install, policy/
volume/default/firmware change or restart. Existing receipts and client57a9339
unchanged. The [31Y report](attempt31y-m1-offline-2026-10-24.md) records the joint
preservation checks. Publish and wait; this pass grants no boot readiness.

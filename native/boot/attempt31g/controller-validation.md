# 31G offline validation

Native31G, CPU1 execution and Linux SMP: **NOT RUN**.

The reproducible job is `virtualization/jobs/065-smp31g/run.sh`, using the
existing isolated ARM64 Linux VM, pinned m1n1 parser/client57a9339 and retained
exact boot021 image/symbol listing. Results and toolchain are summarized in
`validation.json` after successful completion.

Tests cover all prior recorder/controller lifecycle paths plus all8 new PS
read failure positions, terminal-error reason preservation, preflight binding
and translation refusal, strict four-phase-prefix observations, and every
mutation failure/lost acknowledgment. Wrong/early identities still stop.

The real client test serializes the full controller through independent literal
opcode/helper allowlists. It parses original synthetic BootArgs/ADT bytes,
including 18 CPU topology records and two PS domains. A separate real-parser
suite mutates live-binding invariants and requires refusal.

Both GNU and Clang assemble the original32-bit helper for comparison with
Python-emitted bytes. A VM user-mode harness checks returned width and uses a
protected adjacent page to detect accidental64-bit loads. This exercises the
instruction, not Apple MMIO semantics. Cache-range modeling separately checks
64/128/256-byte coverage; it does not establish CPU1 cache visibility.

The human M1 intake deliberately returns `restart_ready:false`: offline scripts
cannot initiate or authorize hardware boot by themselves. Publish readiness,
then wait for the human's fresh target start under the fixed instructions.

# 31H offline validation method

Native31H / CPU1 execution / Linux SMP: **NOT RUN**. Reproducible job:
`virtualization/jobs/066-smp31h/run.sh`, existing isolated ARM64 VM and clean
pinned m1n1 client57a9339. Exact boot021 image/symbol digests are unchanged.
Completed measurements/counts are in `validation.json` in this directory.

The job runs full-symbol intake and M1-style image-only intake, each including
all inherited31G tests plus original reset-format observer, CPU-state tracker,
controller, source-closure and supervisor tests. Existing entry instruction
models are retained and explicitly report that they are not hardware models.

The actual pinned proxy and BootArgs/ADT parser run only inside the Linux VM,
against independent literal protocol/address/helper allowlists and synthetic
memory. Cases cover EL1/EL2 success/timeout, strict bit11 refusal before mutation,
failed translation before access, and every CPU-state read failure on successful
and natural-timeout branches. The test verifies two guarded32-bit baseline
reads, six post-start helper reads, immediate diagnostics, exact startup writes
and absence of post-start guarded RPCs. It does not open a serial device.

Controller tests additionally cover trap/lost-ack prefixes, delayed-read
termination, failed journaling on intent/result, source/image binding, exclusive
receipts, publication and inherited mutation-failure cases. Pure tracker tests
cover invalid values at every read, every journal-failure position, partial
state, privacy, interruption, reentrancy, order and budget.

The32-bit helper bytes match the frozen31G helper; its prior GNU/Clang/Python
encoding and guard-page width tests remain applicable unchanged.31H reuses
that exact code rather than introducing another binary helper. VM tests do not
prove Apple MMIO width semantics, reset firmware, CPU1 code visibility or cache
coherence. Native benchmarking is deferred until actual CPU1 entry is observed.

Source pins are checked before and after intake. Offline output deliberately
keeps `restart_ready:false`: M1 readiness publication plus the human's fresh
start are separate prerequisites. No validation run authorizes itself to boot.

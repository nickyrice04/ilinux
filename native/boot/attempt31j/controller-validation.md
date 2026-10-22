# 31J reproducible offline validation

Run `virtualization/jobs/068-smp31j/run.sh` in the existing isolated ARM64 VM,
with repository and pinned m1n1 client57a9339 mounted read-only. It runs full-
symbol intake,24 real-client wire scenarios, then image-only intake. Run the
same image-only intake on macOS. Counts, versions and digests: validation.json.

The intake includes frozen31I coverage plus the historical USB identity suite,
frozen host diagnostic, new bounded connection module,31J wrapper, source closure
and supervisor tests. All discovery subprocess/metadata/path/serial dependencies
are simulated in tests; no physical USB device or native CPU is exercised.

Boundary cases include exact empty stdout followed by enumeration, persistent
absence, malformed/truncated data, query timeout/failure, ambiguous/wrong identity,
stale/symlink paths, callback/journal/source failures and interrupted discovery.
Native reservation and serial open must not precede verification; a failed open
must not retry. Output must preserve the stage and exclude identifying data.

CPU-level success/timeout traces match31I; actual pinned-client serialization and
ADT parsing use independent literal allowlists in the VM. Existing helper and
recorder bytes are unchanged, so no kernel/image rebuild is needed. Unit tests
cannot prove physical enumeration, MMIO safety, reset routing, CPU execution or
performance. Native31J and Linux SMP remain NOT RUN until the M1's separate run.

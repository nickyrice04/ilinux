# 31L offline validation procedure

The reproducible job is virtualization/jobs/071-smp31l/run.sh. It runs in the
existing isolated ARM64 VM using2vCPU/4GiB, no network or physical USB. It checks
the pinned clean m1n1 client, independently assembles both original prefixes at
five synthetic helper addresses, tests the candidate/observer/controller and
supervisor, then exercises actual client serialization and BootArgs/ADT parsing
against synthetic memory. Full source/image intake runs in full-symbol and
image-only modes; missing input checks/skips are refused. Model and fault cases
are explicitly software scenarios, not Apple firmware emulation.

The companion validation.json records actual outcomes, counts, tool versions
and output hashes. Native31L, CPU1 first-fetch behavior, all-core Linux and
performance/efficiency measurements remain NOT RUN or unverified. A PASS means
offline release readiness, followed by independent M1 intake; it is not native
compatibility. Frozen254 K,226 J,202 I and6 host-only source closures stay intact.

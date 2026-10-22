# 31N offline validation

Run job 073 in the existing isolated ARM64 VM with 2 vCPUs, 4 GiB, no network
and no physical USB. Independently assemble the fixed pair leaf and compare its
bytes; run pure plan, controller, intake and supervisor tests. Exercise the real
pinned m1n1 client against an original synthetic target, including partial pair
execution and lost acknowledgements, then run full-symbol and image-only intakes.

The companion validation.json records actual results, versions, digests and any
corrections. Synthetic targets are software-contract tests, not Apple firmware,
cache, power or timing emulation. CPU1 execution, native 31N, Linux SMP and
performance remain unverified until the separate supervised physical session.

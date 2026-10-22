# 31M offline validation procedure

Run virtualization/jobs/072-smp31m/run.sh in the existing isolated ARM64 VM,
2vCPU/4GiB, with no physical USB or network. Verify the pinned client and original
CTR leaf assembly, observer/controller faults, supervisor/source closure, actual
pinned-client wire serialization, and full-symbol plus image-only intakes.

The companion validation.json records actual outcomes and hashes. Synthetic cache
and fault scenarios exercise the controller, not Apple firmware or coherency.
Native31M, CPU1 execution, all-core Linux and performance remain unverified until
a separate supervised physical attempt. Preserve every consumed receipt and all
frozen31L/K/J/I/host source closures. M1 independently verifies the released
image-only handoff before the human starts a fresh lab session.

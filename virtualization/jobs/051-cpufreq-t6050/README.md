# Job 051 — offline t6050 CPU frequency candidate

Run through the existing isolated job runner only after the shared VM owner
releases its lock. No new VM image or packages are needed. Inputs are the
existing boot042 kernel tree at `/var/tmp/ilinux-boot042/linux`, verified
boot042 files under ignored `build/`, and `kernel/experiments/cpufreq-t6050/`.

The job builds an external module against boot042's exact headers and symbol
versions, executes extracted-callback ASan/UBSan tests, runs Python regression
suites, and compiles/validates the candidate DT with a narrow binding. It does
not load a module, boot the candidate or access hardware. The base Image and
config are checked before and after. Outputs under `out/` are ignored and are
not a native boot package.

See the experiment README for evidence, the proposed separately reviewed
launcher allowance, measurement limits and the hardware go/no-go plan. Attempt
27 and attempt 28 are unchanged by this offline work.

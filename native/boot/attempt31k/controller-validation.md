# 31K reproducible offline validation

Run `virtualization/jobs/069-smp31k/run.sh` in the existing isolated ARM64 VM,
with the repository and pinned m1n1 client57a9339 mounted read-only. The job
assembles the original returning CPU0 leaf and cold tripwire, compares both
against independently encoded bytes, runs full-symbol intake, actual pinned-
client wire scenarios and image-only intake. Run image-only intake on macOS too.
The final counts, versions, digests and results are recorded in validation.json.

Coverage includes the frozen31J tests, new scratch and tripwire fault models,
new target lifecycle, connection wrapper, source closure and supervisor tests.
Both successful and interrupted observations must retain sanitized evidence;
failed prerequisites must prevent CPU1 start, and late cold evidence must prevent
further starts/requests. Unexpected identity/EL, stale RAM, translation failure,
publication corruption and target/journal/deadline errors stop without retry.

The cold instruction model follows only original candidate instructions. It
models each instruction boundary, including a fault before the first store,
publication phases and terminal spin. It does not emulate Apple's firmware,
SPTM, reset controller, interconnect or cache/coherency implementation. Assembly
matching, correct proxy serialization and a synthetic successful CPU1 cannot
prove physical execution. Fresh native31K, Linux SMP and performance remain
NOT RUN/unverified until separately measured on hardware.

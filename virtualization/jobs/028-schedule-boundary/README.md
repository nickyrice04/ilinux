# Job 028 — boot027 scheduling-boundary diagnostics

Run `run.sh` through the existing virtiofs job runner with repository share
`ilinux` read-only and this directory as `job`. It copies retained
`/var/tmp/ilinux-boot027-v3/linux` into absent `/var/tmp/ilinux-boot028/linux`,
checks source hashes, applies the original helper/strip/scheduler instrumentation,
runs both actual-code ASan/UBSan harnesses, builds the full Image with `-j2`,
compares unchanged config and ELF-to-Image bytes, and exports only an Image
replacement over boot027's files. Prior source/package remain intact.

See `kernel/experiments/schedule-boundary/README.md` and `validation.json` for
REA provenance, exact package pins, generic VM results and native limitations.
`out/` and VM binaries/logs stay ignored. No host or native disk attached beyond
the existing isolated Linux build image. No installer or live launch in this job.

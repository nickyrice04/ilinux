# Job 029 — independent diagnostic display and context-switch checkpoints

Run `run.sh` through the existing virtiofs job runner, repository share `ilinux`
read-only and this directory as `job`. It copies retained boot028 into absent
`/var/tmp/ilinux-boot029/linux`, validates source digests, and applies only the
original diagnostic changes. It runs helper, scaled-renderer and actual
DT/parser/mapping sanitizer tests, then reproduces the old lifecycle defect.
libfdt comes from the retained kernel source and executes only in the VM.

Full `make -j2 Image`, unchanged-config comparison and ELF-to-Image roundtrip
follow. Exports replace only Image over the retained boot028 files. `out/`
and logs stay ignored; previous source and artifacts are preserved.

Use `kernel/experiments/context-display/README.md` and `validation.json` for
exact evidence, package and test boundaries. This build job does not boot the
Mac, change settings or test native hardware. No new VM disk is created.

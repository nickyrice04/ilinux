# Job 025: t6050 AIC restricted bring-up

See [experiment evidence and validation](../../../kernel/experiments/aic-t6050/README.md).
The executable `run.sh` runs in the existing Linux build VM, with this directory
as writable `job` and the repository as read-only `ilinux` virtiofs shares.
Requires the retained digest-checked job024 Linux tree and unpacked boot024
package. It creates an independent reflink copy, runs sanitizer tests against
actual driver functions, builds Image, checks unchanged config and exports
matching symbols/disassembly. `out/` stays ignored.

No m1n1 build/install or target boot-setting change occurs. Packaging uses:

```sh
python3 -I native/boot/make-package.py \
  --out virtualization/jobs/025-aic-t6050/out \
  --destination build/native-boot025 --name ilinux-j716c-boot025
```

Use an absent destination archive; preserve previous packages. The package
maker compares all unchanged files against `boot024-package-manifest.json`.
Native execution of boot025 remains NOT RUN; use the current M1 checklist.

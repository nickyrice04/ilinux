# Job 052: attempt-28 CPU observation payload

Build in the existing workspace Arch VM; no host install, boot-policy change,
new disk or native MMIO. Inputs are the exact boot042 build tree and the two
private attempt-27 images. `run.sh` verifies them, builds the original patched
cpufreq module and bounded benchmarks, runs sanitizer/refusal tests, and adds
only the explicit-load CPU assets to the working root. It repins stage one.
All output remains ignored under `out/`.

```sh
caffeinate -i tools/vm-job.sh virtualization/jobs/052-cpu-observation cpu28
```

Check the **guest** exit in `out/run.log` and `out/build/summary.txt`; the VZ
runner can exit successfully after a guest job failed. Toolchain and tests
are in `out/build/`. Compile against boot042; the build VM's kernel is not
the shipping kernel. No module is loaded in this job.

`controller/run.sh` runs the transport-injected controller suites in the
existing VM with the pinned m1n1 client and its two pinned Python dependencies
in a VM-only venv. It mounts source read-only, connects no target and performs
no real proxy/MMIO requests. Do not run both jobs against the shared disk at
once; `tools/vm-job.sh` holds its existing VM lock.

After reviewing/copying the new public JSON records to `native/boot/attempt28/`,
use job049's existing test machinery with this output directory. Preserve any
previous run before reusing its `vm/` directory:

```sh
printf '%s\n' 'MANIFEST=/mnt/ilinux/native/boot/attempt28/omarchy-root-manifest.json' \
  > virtualization/jobs/052-cpu-observation/out/job.env
JOB_OUT="$PWD/virtualization/jobs/052-cpu-observation/out" CPU_OBSERVE_TEST=1 \
  caffeinate -i virtualization/jobs/049-two-stage-boot/run-qemu.sh
```

The QEMU/HVF diskless boot test uses job041's **test** kernel with dummy_hcd,
one vCPU and 32 GiB. It tests the exact shipping image pair with isolated VM
keys/probes: bad image, truncated transfer, corrupt transfer, successful switch,
Omarchy desktop, second link and inherited image fixes. It verifies the CPU
assets and refuses the VM at the native identity gate **before module load**.
There is no Apple DVFS or real USB/MTP emulation. Do not interpret this as
native module initialization, frequency, keyboard, SMP or efficiency evidence.

See `native/boot/attempt28/validation.md` and the M1 attempt-28 checklist for
actual results, limits and the only reviewed native scope.

# Job097 — readable original diagnostic variant

Run only in the existing isolated ARM64 Linux build VM. Mount the project
read-only at `/mnt/ilinux` and this job directory writable at `/mnt/job`; the
coordinating parent owns VM locks and execution:

```sh
bash /mnt/ilinux/virtualization/jobs/097-direct31aj-readable/run.sh
```

The job compiles the portable renderer test, new original collector object and
static executable. It requires the object relink and a direct source build to
be byte-identical, runs both old generic selftest modes and the new synthetic
`--display-test`, and creates the exact five-entry RAM root. It neither launches
another VM nor boots a kernel or physical device.

Outputs under `out/`:

- `diag-init`, `diag-init.o`, `initramfs-direct31aj.cpio.gz`.
- `panel-tests.json`, normal/stall selftest records and `display-test.txt`.
- `source-binding.json` and `build-result.json`, binding the C/header/test inputs,
  hashes, unchanged Image/config/DT references, compiler/runtime scope and common
  license-text provenance. Common texts do not complete runtime attribution or
  public source closure. Source changes during compilation refuse closure.

The unchanged kernel inputs are in `build/direct31ah-kernel/job/out/`; no kernel
rebuild or module change is needed. No old artifact is overwritten. The root
contains no storage modules or additional programs. No host setting, font,
framebuffer, brightness, partition, security, boot object or firmware is changed.

Before publication also run the four host-safe boundary methods:

```sh
python3 -I kernel/experiments/direct31aj/test_collector.py
bash -n virtualization/jobs/097-direct31aj-readable/run.sh
```

## Separate generic VM control

After the build, the parent uses the established diskless VZ runner with four
vCPUs, four GiB RAM, no NIC/disks, the unchanged Image and **new** initramfs.
Use the existing collector opt-in, `console=hvc0 rdinit=/init
ilinux31ah.vmcontrol=1 quiet loglevel=3`; this is a generic control, not a new
native boot argument or new machine identity. The unchanged guard intentionally
retains its original opt-in name.

Keep console capture private and bounded. The frozen
`virtualization/jobs/095-direct31ah-kernel/check_vm.py` can verify the unchanged
JSON worker/RAM/timer/sixty-second semantics; block rows are non-JSON and are
ignored by that receipt parser. Review the new `display-test.txt` and bounded
block output separately. Source/renderer tests establish formatting, not physical
screen/camera readability. The generic VM cannot qualify native M5 execution,
CTXR, eighteen cores, display hardware, N1/GPU/NVMe or performance.

The collector remains running after its completion marker; the parent performs
the separately bounded VM stop and records its actual outcome. It does not
claim a requested guest shutdown or a self-enforced physical boot deadline.

Repin new executable/root/candidate artifacts before M1 intake. In particular,
the frozen `tools/boot-object31aj/payload.py` knows the original 31AI hash; a new
readable candidate needs a separate reviewed binding, not a change to that old
seven-pin closure. Native authorization and readiness remain false.

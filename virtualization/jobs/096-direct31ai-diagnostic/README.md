# Job096 — diagnostic object and local handoff binding

Run only inside the existing isolated ARM64 Linux VM, with the repository mounted
read-only at `/mnt/ilinux` and this job directory writable at `/mnt/job`:

```sh
bash /mnt/ilinux/virtualization/jobs/096-direct31ai-diagnostic/run.sh
```

The recipe reads the frozen original C and prior tested executable, writes a new
object and relinked executable under `/mnt/job/out`, and requires byte equality.
It exercises both generic selftest modes. This VM's glibc/gcc-libs packages have
no separate notice directories, so it exports explicitly labelled common SPDX
LGPL/GPL license texts plus the actual installed GCC runtime exception, recording
their provenance. These are not complete glibc-specific copyright notices.
Inputs and old outputs are not modified. No native kernel,
host installation, device, firmware, boot/security/volume change or network is
used. The coordinating agent owns VM locks and execution.

Receipt: `out/relink-result.json`, schema `ilinux-direct31ai-relink-v1`. It records
source/object/executable digests, byte equality, normal/stall-control results,
runtime versions, common-text provenance and notice inventories. It explicitly
records incomplete runtime-specific attribution/public source closure. `native_tested` and
`public_binary_release` remain false. The static diagnostic's full public libc
source closure is deliberately not claimed.

After this job, use the separate original
`kernel/experiments/direct31ai/diagnostic/package.py` builder/reader and its
README. The default documented output is this job's ignored `out` directory;
the coordinator can choose another workspace build directory. The public
handoff contains source, manifest/digests and sanitized evidence. The compiled
tar/root/object remain a private local-user transfer.

Host-safe tests:

```sh
python3 -I kernel/experiments/direct31ai/diagnostic/test_package.py
bash -n virtualization/jobs/096-direct31ai-diagnostic/run.sh
```

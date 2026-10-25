# Original 31AB image packaging and instruction tests

This is an executable **offline diagnostic**, not a native boot release. It
packages the original [entry payload](../sptm31ab-host/README.md) into the flat
Mach-O form tested in 31Y, preserving every payload offset. Nothing here installs,
signs, selects or boots an image. Native firmware acceptance, monitor calls and
physical secondary execution remain untested.

The payload is 81,920 bytes. The complete image is 114,688 bytes, including its
reserved header, deterministic original metadata and link-edit region. The
packager never copies an Apple implementation. Its eight tests check placement,
permissions, entry metadata, arithmetic rejection and preservation of the input.
They supplement the producer's instruction/ELF audit; they do not replace it.

From the repository root, using existing tools:

```sh
python3 -I -m unittest discover -s kernel/experiments/bootimage31ab -p 'test_image.py'
python3 -I kernel/experiments/bootimage31ab/image.py \
  --payload build/31ab-host-linked/payload.bin --output build/31ab-packaged
```

The read-only `kmutil inspect` experiment derived the expected boot properties
for the actual linked image. That utility parses the format; it does not simulate
firmware acceptance. Its exit status alone is insufficient: inspection must also
reject error diagnostics, as the frozen 31Y probe does.

## Instruction execution, separate from firmware emulation

`emulate.py` executes the original payload in QEMU's standard ARM `virt` machine
using TCG. It supplies no Apple firmware, network, block device or physical USB.
The guest bootstrap and deliberate BRK mutation are test fixtures, excluded from
the packaged diagnostic. QMP observes the owned record independently of the
payload. The record starts poisoned, so zero-initialization is tested explicitly.

Nine cases passed in the isolated ARM64 Linux VM:

| Configuration | Entry at two load addresses | Actual BRK after vector installation |
| --- | --- | --- |
| EL1 | 2 | 1 |
| EL2 without VHE | 2 | 1 |
| EL2 with E2H/TGE | 2 | 1 |

The checks preserve full-width incoming arguments, use deliberately noncanonical
pointer fixtures to detect accidental dereferences, verify owned stack/vector
addresses, and check HCR only where accessible. The three BRK cases exercise
architectural vector slot 4 and inspect the captured syndrome, return address,
saved execution state and stack. The other vector slots are statically audited,
not all dynamically exercised. Higher/guarded exception routing is not modeled.

The reusable VM script is
[`run-emulation.sh`](../../../virtualization/jobs/086-offline31ab/run-emulation.sh).
It requires an existing QEMU with TCG, a linked payload at `/mnt/artifacts/host`,
the repository at `/mnt/ilinux` and a fresh writable `/mnt/job/out`. Do not run
the VM job scripts directly on macOS. Root orchestration owns the shared VM and
quiet locks. No published script installs packages or retrieves firmware.

None of these tests executes GENTER or validates SPTM semantics, native image
permissions, framebuffer visibility or CPU startup. Their runtimes are test
timings, not performance measurements. See the
[31AB receipt](../../../native/boot/attempt31ab/validation.json) for exact hashes,
versions, setup failures and the remaining physical-test boundary.

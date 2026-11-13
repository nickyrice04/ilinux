# 31AI exact diagnostic delivery — local offline review

This separate handoff supplies the diagnostic executable/RAM image omitted from
31AH. It reuses the **unchanged, already tested** kernel and collector. Frozen
31AH code, package, evidence and approvals remain untouched.

The selected loader reference is 31AH's **baseline** padded Aura, SHA-256
`f73b8feea8f05a67408fb1a7e86b679ce33e9f2ff9ae97746549a126bf07cace`.
The original experimental USB2 alternative is not selected. No loader is
installed or included in the diagnostic tar; the separately reviewed 31AH
bundle supplies that exact reference.

## What is bound

`policy.py` pins the exact tested Image, resolved config, sanitized J716c DT,
static collector, compressed RAM root, collector source, build-source binding,
generic VM receipt and frozen 31AH manifest. `package.py` verifies these before
writing a package. The reader repeats the checks without extracting or executing.
The existing kernel/DT validators run only after their frozen source hashes pass.

The private tar contains:

- The pinned Image/config/DT and exact static `/init`/compressed RAM root.
- Original collector C and a fresh relocatable object, accompanied by a receipt
  proving that relinking it produces the **byte-identical tested executable**.
- Clearly labelled common SPDX license texts, the installed GCC exception,
  runtime versions, generic VM evidence, source
  bindings, the prior manifest and a fixed storage policy.
- An explicit local-review notice. **No native readiness or permission to boot.**

The root has exactly five entries: empty `dev`, `proc`, `sys`, `run` directories
and the regular static `init` file. Its newc metadata and complete single gzip
stream are checked. No modules, firmware, filesystem tools, keys, accounts,
personal files, Apple artifacts or raw serial logs are added. Runtime mounts
remain proc/sys/devtmpfs/RAM tmpfs and optional native configfs. The collector
requests no block-device opens, storage filesystem mounts, raw MMIO, frequency
writes or persistent storage writes. Native hardware behavior remains unverified.

## Build and local delivery

Run job096 in the existing isolated Linux build VM first. It compiles original
source, links the new object against the installed runtimes, requires byte
equality to the tested executable and runs normal/intentional-timeout controls.
The installed glibc/gcc-libs packages have no separate notice directories in
this VM. The job copies common SPDX LGPL/GPL texts and the installed GCC
exception into its own output directory, recording those exact origins. These
are not presented as complete glibc-specific attribution. The job does
not rebuild a kernel, boot hardware, open USB or change macOS.

Then the workspace-only Python builder can run on macOS. From the checkout root,
using the job output chosen by the coordinating agent:

```sh
python3 -I kernel/experiments/direct31ai/diagnostic/test_package.py
python3 -I kernel/experiments/direct31ai/diagnostic/package.py build \
  --kernel-out build/direct31ah-kernel/job/out \
  --vm-receipt build/direct31ah-kernel/diagnostic-vm-result.json \
  --relink-out virtualization/jobs/096-direct31ai-diagnostic/out \
  --output virtualization/jobs/096-direct31ai-diagnostic/out/ilinux-direct31ai-diagnostic.tar.gz \
  --manifest virtualization/jobs/096-direct31ai-diagnostic/out/diagnostic-manifest.json
```

The builder refuses an existing output. Its final read-only self-review must
pass before the manifest is published. The coordinating agent records the new
manifest/source inventory and sanitized receipt in the 31AI handoff. It does
**not** publish the tar, executable, object or RAM root as a binary Release.

The user can transfer the private tar directly between their own computers.
No upload, message, automatic AirDrop or other transfer is performed by this
tool. M1 obtains the new public source/manifest normally, preserving local work,
and runs the 40 tests plus `package.py review --manifest COMMITTED_MANIFEST
--package LOCAL_TAR`. AirDrop may rename the file; pass its actual local path.

The strict reader verifies compressed/member hashes, CRC, complete single-gzip
and strict regular USTAR structure, names, metadata, limits and semantic runtime
bindings. It refuses hidden PAX/GNU metadata, symlinks, path traversal, duplicates,
truncation, unknown files, extra storage modules and a mismatched `/init`.
It outputs only a small sanitized receipt, with `extracted:false`,
`executed:false`, `device_opened:false` and `native_ready:false`.

## License and runtime limits

The original collector and delivery tools use MIT SPDX identifiers. The static
executable also includes glibc/GCC runtime code. Common SPDX license texts, the
installed GCC exception and a working relink object accompany this same-user
local review. Complete runtime-specific copyright notices remain unavailable;
the receipt explicitly records that gap. These materials do not
claim complete public libc corresponding-source delivery. **Public binary
source/relink closure remains incomplete; no public binary Release is prepared.**
This records the engineering delivery boundary, not a legal conclusion about
other distribution arrangements.

The generic VM demonstrated four permitted CPUs, arithmetic/timers, a RAM
checksum and 60.498 seconds of liveness. Those results establish neither
eighteen physical cores nor native CTXR, CPU frequency, N1, GPU, NVMe, sleep or
macOS performance parity. Static M/M/P DT capacities are source descriptions,
not measured online core behavior. The public T6050 Linux USB path remains
host-only; this handoff does not repair or bypass that guard.

Firmware pairing, lab-only installation, independent observability, complete
restoration/default recovery and separate authorization remain the coordinating
agent's gates. Do not restart or prepare Recovery solely because this reader
passes.

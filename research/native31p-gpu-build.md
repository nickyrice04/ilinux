# 31P GPU build foundation — offline, native HOLD

2026-10-22. This is a parallel route toward usable native Omarchy while the
secondary-core firmware question remains unresolved. It does not authorize a
native attempt, change the 31O checkpoint, or enable a GPU node in the boot image.
The original macOS environment and existing native packages remain unchanged.

## Why this work now

**Observed in our project:** the current desktop uses software rendering on one
CPU core at 3456×2160. CPU startup and accelerated rendering are separate missing
capabilities; obtaining GPU support could remove substantial composition work
from that core. **Unknown:** how much of the observed application delay would
remain after acceleration. Neither a compiler build nor another platform's
frame rate measures that improvement on this M5 Max.

The immediate deliverable is a reproducible, isolated build of the most relevant
public implementation, plus original validation of this machine's two firmware
processor interfaces. No generation alias, copied Apple implementation, firmware
replay, or GPU MMIO is included.

## Pinned foundations and evidence boundaries

| Component | Exact source | What it provides | What it does not prove |
|---|---|---|---|
| Gravity Mesa | `87ac51d411f0e58a9433567ec2666f457be89e1d` | Apple9 compiler IR, optimization, allocation and instruction generation; Asahi layout/library tests | G17C device support, firmware compatibility, working native rendering |
| Gravity Linux | `4fc326f6c25ccceb7515e2635c22e01fde5d3bac`, kernel 7.1.13 | Rust DRM/RTKit integration and the `DRM_ASAHI_M4` driver | T6050/G17C initialization, matching firmware handoff or all-core startup |

**Confirmed source compatibility:** the two pins contain byte-identical
`asahi_drm.h` UAPI headers, SHA-256
`eb9f39e87dfe448dc044f54ab2d11b7493bf1359faca8fb76ece5f3583469015`.
This checks the public host/driver header pairing; it does not establish the
private firmware ABI or native behavior.

The kernel's
[device match table](https://github.com/GravityLinux/linux/blob/4fc326f6c25ccceb7515e2635c22e01fde5d3bac/drivers/gpu/drm/asahi/asahi_m4.rs)
contains `apple,agx-t8132`. Its
[Kconfig](https://github.com/GravityLinux/linux/blob/4fc326f6c25ccceb7515e2635c22e01fde5d3bac/drivers/gpu/drm/asahi/Kconfig)
requires Rust, built-in DRM, ARM64 Apple support, 16 KiB pages and PM. These are
build prerequisites, not a recipe for changing this machine's compatible string.

Mesa's
[device implementation](https://github.com/GravityLinux/mesa/blob/87ac51d411f0e58a9433567ec2666f457be89e1d/src/asahi/lib/agx_device.c)
recognizes the newer G16G/G17P paths. The
[Apple9 compute admission](https://github.com/GravityLinux/mesa/blob/87ac51d411f0e58a9433567ec2666f457be89e1d/src/gallium/drivers/asahi/agx_apple9.c)
still restricts compute to G16G. Shared instruction-generation work does not
establish a compatible command submission format for G17C.

**External evidence only:** Gravity reports substantial native M4 GLES3 testing
in its [Apple9 ES3 record](https://github.com/GravityLinux/mesa/blob/87ac51d411f0e58a9433567ec2666f457be89e1d/src/gallium/drivers/asahi/README.apple9-es3.md).
This establishes a useful foundation; it is not our native result or a full
conformance claim. The base-M5 project's
[GPU handoff](https://github.com/sh1ftmaker/m5-linux-research/blob/d220c02ab2bc3cedb9a956061bce5106a1e44049/research/handoff-final/gpu.md)
separately reports bootstrap no-op compute progress but a failing Mesa user job.
Its T8142 findings must not be treated as a working M5 Max desktop driver.

## Job 075: real compilation in an isolated ARM64 Linux VM

`virtualization/jobs/075-gpu31p/` contains original orchestration and manifests.
Third-party archives and packages remain ignored build inputs; they are not
committed. The exact SHA-256 and sizes are in `sources.json` and `packages.json`.
The Mesa archive is 134,319,568 bytes and the kernel archive is 263,270,476 bytes.
Ten pinned dependency packages total 113,162,736 bytes. An earlier truncated
Mesa download was discarded; only the complete pinned archive is admitted.

Run using the existing VM launcher, 4 virtual CPUs and 12 GiB RAM, with **`--no-net`**.
The root coordinating agent owns the shared VM locks and disk. Required shares:

- `job`: this job directory, read/write for its `out/` directory.
- `gpu31p-sources`: only the public archives, packages and detached signatures,
  read-only. Do not include private firmware or analysis files.
- `ilinux`: a curated public project staging tree, read-only; never the whole
  workspace with its ignored private `build/` tree.

The job verifies that `/sys/class/net` contains only `lo` and records that check.
Mesa sources, an isolated compiler prefix, build outputs and compiler temporaries
use a dedicated 6 GiB guest tmpfs at `/var/tmp/ilinux-gpu31p`. Previous disk builds,
installed packages and package caches are preserved. The job requires at least
11 GiB guest RAM in total and 9 GiB available before mounting it. A nonempty
existing work directory or unexpected mount is refused.

All 22 input archive/signature hashes are checked. Every package's installed-size
metadata is cross-checked against its pinned `.PKGINFO`. Before any package is
extracted, GPG must return success with exactly one `GOODSIG`, one `VALIDSIG` and
one `TRUST_FULLY` or `TRUST_ULTIMATE` status. Bad, expired, revoked, unknown-key,
partial-trust or multiple-signature results are refusals. Verification uses only
tmpfs copies of the guest's existing public keyring and trust database; private
keys are neither accessed nor copied. No keys or ownertrust are imported, no
network retrieval occurs and the system keyring is not modified.

Only `usr/` package payloads are extracted into the isolated prefix, using the
Python archive data filter; maintainer scripts and hooks never run. The exact
package binaries remain unchanged. An original wrapper qualifies `llvm-config`
paths, and original relocation changes only extracted pkg-config prefix metadata,
with before/after hashes recorded. The job sets its own PATH/library search path
and verifies LLVM's prefix, include and library directories. System pkg-config
entries remain available for libdrm/gtest. Installed package lists must be
identical before/after; there is **no package installation or dependency bypass**.

The compiler family is pinned together to LLVM/Clang 23.1.3; translator 23.1.2
matches the required LLVM major/minor interface. SPIR-V Tools/Headers are pinned
to 1.4.363.0; bindgen is 0.73.2. Existing guest build prerequisites include GCC,
Meson, Ninja, CMake, Python Mako/PyYAML/packaging, gtest and libdrm. Missing or
incompatible dependencies are failures to resolve, not permission to disable
checks. The job records actual tools and Meson options.

Each run extracts fresh sources into its own guest directory and starts a fresh
build; no modified source cache is trusted. The build has no Meson network
fallbacks. It compiles:

1. `agx_tests`, exercising upstream shader compiler tests, including Apple9.
2. `asahi_layout_tests`, exercising texture/layout calculations.
3. `libasahi_tests`, exercising packing and tilebuffer logic.
4. `agx_apple9_tiny_tool`, a reusable offline shader development executable.

It runs all three selected test executables through Meson and retains the test
JSON, configured options, tool versions, build logs and artifact hashes. This is
an ARM64 VM compilation/test result, not hardware rendering or a performance
benchmark. The tool executable stays in ignored output for further VM analysis.

`kernel.sh` retains an optional unmodified M4 Rust-object build recipe, but the
current run **skips it explicitly**. The installed Rust package requires LLVM
23.1.1, while this isolated Mesa compiler uses 23.1.3. Mixing those silently would
invalidate the check. A separately qualified kernel toolchain and sufficient
guest disk space are required before that build. No native package is produced,
installed or loaded in this pass.

## Actual validation

**PASS:** job075 completed in the ARM64 Linux VM from 21:55:37 to 21:56:36 UTC
on 2026-10-22, exit 0. The 59-second wall time includes verification/configuration/
compilation/testing; it is not a native GPU performance measurement. Ninja
completed 514 build actions. All three selected test executables passed:

| Executable | Individual gtests passed | Failures |
|---|---:|---:|
| `agx_tests` |366|0|
| `asahi_layout_tests` |25|0|
| `libasahi_tests` |5|0|
| **Total** |**396**|**0**|

The actual build used GCC/G++ 16.1.1, isolated Clang/LLVM 23.1.3, Meson 1.12.1,
Ninja 1.13.2 and gtest 1.18.0. The translator and SPIR-V Tools pkg-config versions
were 23.1.0.0 and 2026.4.1 respectively; their package versions are separately
pinned in `packages.json`. The protected system Rust remained 1.99.0.

All ten package signatures passed with `VALIDSIG` and `TRUST_FULLY`. The network
preflight saw only `lo`. Installed package lists were byte-identical before and
after. The original helpers' seven disk-budget tests and six isolation tests
passed inside the VM and on the host. No downloaded code executed on macOS.

The unmodified upstream Apple9 test source produced four compiler warnings:
two enum comparisons, one narrowing conversion and one dangling-else warning.
There were no compiler errors and no failing selected tests. These warnings are
retained as upstream test-source limitations, not silently removed from the log.

The exported offline `agx_apple9_tiny_tool` has SHA-256
`ee5f90e1e59cc0a174418c9603eb55efd284ac71bbcf9e3bdbba2b49de4f0e72`.
The static compiler library and all three test executables have recorded hashes.
Full structured results, evidence-log hashes and executed/published helper hashes
are in `virtualization/jobs/075-gpu31p/validation.json`. After the successful run,
only SPDX MIT comments were added to eight original helper scripts; both source
versions are identified and the current helper tests were rerun successfully.

Two preceding refusals are preserved: the initial disk guard stopped with
585,388,032 bytes available; the next run passed its package-space budget but
pacman rejected the exact-version Rust dependency conflict before installation.
A bounded official-mirror check did not find the matching older LLVM development
package. The successful isolated-prefix run resolved the build dependency
without altering installed packages, deleting prior builds or clearing caches.

**Kernel object:** explicitly skipped; its Rust/LLVM environment needs separate
qualification. **Native GPU initialization, command submission and graphics:**
NOT RUN. **Native performance and energy improvement:** UNMEASURED. Neither the
successful compile nor these 396 tests establish G17C hardware compatibility.

## Remaining G17C implementation work

1. Bind resources to the actual T6050 identity and both GFX processor roles.
   Preserve the full widths of each address domain; a firmware-local address is
   not automatically CPU physical memory. The original codec and tests are
   recorded separately in `research/native31p-gpu-contract.md`.
2. Establish the matching firmware ABI and the two processors' respective roles,
   initialization ownership, shared-memory publication and mailbox endpoints.
   macOS release numbers are not firmware ABI versions.
3. Reconstruct the relevant UAT/page-table and command-queue formats, with
   independent evidence for widths, alignment, cache maintenance and lifetime.
   Existing M4 and base-M5 examples are comparisons, not valid G17C templates.
4. Write and test original Linux serialization, validation and initialization
   components from those findings. Review error paths and bounded resource
   ownership before a hardware probe.
5. Only after a separately reviewed native plan: identify resources, establish
   firmware communication, submit a bounded no-op, then a small validated render
   workload. A booting firmware endpoint alone is not a functioning DRM driver.
6. Integrate the proven path with Mesa and Hyprland, then measure frame delivery,
   input-to-display latency, application startup, power and thermal behavior
   against the same machine's macOS baseline.

This ordering permits useful offline compiler and interface work immediately,
while retaining a clear requirement for actual G17C execution evidence before
promising a responsive accelerated desktop.

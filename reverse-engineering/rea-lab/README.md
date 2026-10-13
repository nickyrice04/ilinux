# Isolated REA / Ghidra lab

Validated 2026-10-13. See
[`../findings/rea-native-2026-10-13/handoff.md`](../findings/rea-native-2026-10-13/handoff.md)
for findings, confidence and the implementation handoff.

The expanded [driver-interface pass](../findings/driver-interfaces-2026-10-13/handoff.md)
adds 17 queries across device families, original Linux input hardening and
an N1 software queue experiment. `analyze_drivers.py` runs only explicitly
selected, digest-pinned targets inside Linux, with per-query time limits;
`crosscheck_drivers.py` verifies saved instruction bytes using existing host
LLVM tools. The latter accepts `--carrier` for a narrowly extracted dyld-cache
analysis carrier. All raw results stay in ignored lab paths.

This is a diskless, 2-vCPU/8-GiB Linux job. It never attaches the live
Omarchy disk. Only `build/rea-lab` is shared writable; source and the existing
REA npm tree are read-only. Downloaded tools execute only in this VM. Raw
Apple inputs, complete disassembly/pseudocode and generated tool installations
stay under ignored `build/rea-lab`. No macOS installation or global agent
configuration is changed. This share is isolation from the reference OS,
not a claim that VM software cannot change its explicitly writable lab files.

## The compiler issue

REA 6.4.0 needs an analysis provider; installing its npm package does not
install Ghidra. For pinned Ghidra 12.1.4, a full JDK 21 supplies `javac`, and
Linux ARM64 requires a native decompiler build. This compiles the **analysis
tool**, not Apple's target binary. See the
[pinned Ghidra guide](https://github.com/NationalSecurityAgency/ghidra/blob/Ghidra_12.1.4_build/GhidraDocs/GettingStarted.md#building-native-components)
and [REA installation documentation](https://github.com/morluto/rea/blob/main/docs/installation.md).
The installed REA package, not changing upstream `main`, governs our commands.

Our minimal build uses the bundled C++ Makefile, explicitly overriding its
outdated Linux architecture inference:

```sh
make -j2 ARCH_TYPE= OSDIR=linux_arm_64 ghidra_opt
```

Copy `ghidra_opt` to
`Ghidra/Features/Decompiler/os/linux_arm_64/decompile`. It is the Ghidra IPC
target; `decomp_opt` is a different console executable. The tested environment
sets `GHIDRA_INSTALL_DIR` and `JAVA_HOME`. Minimal guest fixes also include
`procps` for REA's owned-process checks, `/dev/fd` links for Bash, and a
`/mnt/node_modules` symlink for the read-only npm share's dependency lookup.

Alpine is outside REA's official supported distro list. Audit-wide `doctor`
reports that limitation and missing optional engines/integrations. Actual
REA/Ghidra operations passed the original-code smoke test and four bounded
Mach-O queries. Do not describe all of REA as fully certified on Alpine.

## Inputs and reproduction

Run from the repository root. Required existing tools are Python 3, the
project `virtualization/bin/vzrun`, and its stock 4-KiB-page `Image`.

1. Cache these official inputs in `build/rea-lab/downloads/`:
   - [Ghidra 12.1.4](https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.1.4_build/ghidra_12.1.4_PUBLIC_20260921.zip), SHA256
     `ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db`;
     checked against GitHub's release asset digest.
   - [Alpine 3.23.0 aarch64 minirootfs](https://dl-cdn.alpinelinux.org/alpine/v3.23/releases/aarch64/alpine-minirootfs-3.23.0-aarch64.tar.gz), SHA256
     `5552106ac866be0c46fdff7a2991a1ed85c0464301a1ac87454c41739d5b6431`;
     checked against the official adjacent `.sha256` file.
2. Prepare matching kernel modules from the existing Arch archive, into an
   absent output directory. The current `build/rea-lab/modules` already exists:

   ```sh
   python3 -I reverse-engineering/rea-lab/prepare_modules.py \
     virtualization/images/downloads/ArchLinuxARM-aarch64-latest.tar.gz \
     build/rea-lab/modules
   python3 -I reverse-engineering/rea-lab/make_initramfs.py \
     build/rea-lab/downloads/alpine-minirootfs-3.23.0-aarch64.tar.gz \
     build/rea-lab/initramfs.cpio.gz --modules build/rea-lab/modules
   ```

3. Check `tools/lock.sh status`. Acquire `quiet` before starting; if another
   agent owns it, wait for their work to finish. No live-guest `vm` lock is
   needed because this job has no disk attached. Use a five-minute window
   for cached verification; the first backend build needs a longer window.

   ```sh
   tools/lock.sh acquire quiet agent-b 'isolated REA lab' 20
   cp reverse-engineering/rea-lab/verify-guest.sh build/rea-lab/job.sh
   caffeinate -i virtualization/bin/vzrun \
     --kernel virtualization/images/alarm/Image \
     --initrd build/rea-lab/initramfs.cpio.gz \
     --cmdline 'console=hvc0 quiet rdinit=/init' --cpus 2 --mem 8 \
     --share "$PWD/build/rea-lab:lab" \
     --share "$PWD/reverse-engineering/rea-lab:source:ro" \
     --share "$PWD/tools/rea/node_modules:rea:ro"
   tools/lock.sh release quiet agent-b
   ```

   Release the lock after the VM stops, including failures. The lock does
   not stop the VM automatically. `init` caps a batch job at 240 seconds;
   setup/build duration is separate. For an interactive analysis session,
   remove **only** `build/rea-lab/job.sh` before boot; finish with `poweroff -f`.
   Never kill or signal another agent's VM. The cached tool root is about
   273 MiB compressed and is not a VM disk. APK versions are recorded, but
   the public Alpine repositories can update; the local cache is the tested
   package snapshot.

## Target pipeline

`extract_kernel_payload.py build/rea-lab/artifacts` copies just the readable
IM4P `krnl` LZFSE payload, omitting IMG4 personalization and unique Preboot
directory names. It refuses nonunique carriers, unknown types and opaque
payloads. It does not establish which carrier the running boot selected.

Build the public [LZFSE tool](https://github.com/lzfse/lzfse) at
`e634ca58b4821d9f3d560cdc6df5dec02ffc93fd` inside the guest and decode there:

```sh
make -C /mnt/lab/lzfse-src -j2
/mnt/lab/lzfse-src/build/bin/lzfse -decode \
  -i /mnt/lab/artifacts/kernelcache.lzfse -o /mnt/lab/artifacts/kernelcache.macho
```

`derive_member.py` creates a small static-analysis derivative for one
allowlisted member. It preserves code/data bytes and virtual addresses,
rewrites file offsets and member-owned string indexes, rejects unsupported
metadata, and emits a provenance map. It does **not** apply collection fixups
or resolve cross-member authenticated pointers. These files are not bootable.
Example host-side parsing (no target execution):

```sh
python3 -I reverse-engineering/rea-lab/derive_member.py \
  build/rea-lab/artifacts/kernelcache.macho com.apple.driver.ApplePMGR \
  build/rea-lab/artifacts/ApplePMGR.macho
```

In the VM, verify the provider on original code first:

```sh
cc -O2 -g -Wall -Wextra -Werror /mnt/source/smoke.c -o /mnt/lab/smoke
/mnt/lab/smoke
rea decompile /mnt/lab/smoke saturating_add_u32 --provider ghidra --format json
rea function /mnt/lab/artifacts/ApplePMGR.macho 0xfffffe00094964a4 \
  --provider ghidra --format json > /mnt/lab/evidence/pmgr-enable-core.json
```

Addresses are build-specific; do not reuse them with another binary digest.
Run `check_evidence.py` before drawing conclusions. It rejects pseudocode
whose high-pcode PCs escape the provider's own function body—even if REA
labels those operations `member`. A passing gate still requires manual
assembly review and independent evidence. No Apple pseudocode is used as
original Linux source.

`startup_layout.[ch]` and `audit_startup_layout.py` are original, read-only
experiments over public-source geometry and sanitized ADT data. They perform
no MMIO and do not enable any CPU. Their interpretation needs physical
validation before integration into m1n1 or a native kernel path.

# Native REA artifact handoff — metadata only

Agent B subtask, 2026-10-13. Read `AGENTS.md` and `coordination.md`; no VM,
locks, builds, commits, QEMU inspection or shared-document edits. All host
access was read-only: selected plists, Mach-O headers/load commands/symbol
names, and bounded IMG4 container headers. No binary was executed, copied,
hashed or decompiled. No identifier-bearing paths or personalization data
were retained.

**Observed host:** macOS 26.6.2, build 25G83 (`sw_vers`). The project's prior
sanitized inventory identifies Mac17,6 / J716c / chip-id 0x6050 and
`mBoot-18000.161.10`; firmware identity was not freshly measured here.

## Target bundles

Each path below is `/System/Library/Extensions/<name>.kext/Contents/Info.plist`.
Every plist exists and declares the matching `CFBundleExecutable`, but the
corresponding `Contents/MacOS/<executable>` does **not** exist. These bundles
are metadata, not standalone ARM64 analysis inputs.

| Bundle name / identifier suffix | Version | Selected class, provider and match |
|---|---|---|
| `AppleT6050PMGR` (`com.apple.driver`) | 1 | `AppleT6050PMGR`; `AppleARMIODevice`; `pmgr1,t6050` |
| `AppleARMPlatform` (`com.apple.driver`) | 1.0.2 | `AppleARMCPU` / `IOPlatformDevice` / `cpu`; `AppleARMPE` / `IOPlatformExpertDevice` / `AppleARM` |
| `AppleT6050CLPC` (`com.apple.driver`) | 1 | `AppleCLPC`; `ApplePMGRNub`; `clpc,t6050` |
| `AppleT6050SOCTuner` (`com.apple.driver`) | 1 | `AppleT6050SOCTuner`; `ApplePMGRNub`; `soc-tuner,t6050` |
| `IONVMeFamily` (`com.apple.iokit`) | 2.1.0 | `AppleANS3CGv2Controller` and `AppleANS3NVMeController`; `RTBuddyService` |

**Confirmed:** “AppleANS3” is a class-family target inside `IONVMeFamily`,
not a discovered `AppleANS3.kext`. These are declarative class associations;
current runtime binding is established only by the earlier sanitized
`hardware/adt/driver-map.tsv`, not by this plist inspection.

## Available carriers and analysis boundaries

| Carrier | Observed packaging | Use / limit |
|---|---|---|
| `/System/Library/KernelCollections/BootKernelExtensions.kc` | 67,584,000 bytes, x86_64 (`cputype=0x1000007`), `MH_FILESET` (12), 831 load commands | Contains `LC_FILESET_ENTRY` `com.apple.iokit.IONVMeFamily` at file offset 39,550,976, static VM address `0xffffff80026b8000`. Its member is x86_64 `MH_KEXT_BUNDLE` (11), with 2,386 symbol entries. **Wrong architecture for t6050.** None of the other requested bundle names occurs in the fileset entries. |
| `/System/Library/KernelCollections/SystemKernelExtensions.kc` | 361,922,560 bytes, x86_64 `MH_FILESET`, 686 load commands | No requested target appears in its fileset-entry names. Do not mistake this for the running ARM collection. |
| `/System/Library/Kernels/kernel.release.t6050` | 17,168,528 bytes, ARM64 (`0x100000c`), arm64e subtype `0xc0000002`, `MH_EXECUTE` (2), 31 load commands | Standalone kernel; 6,896 `LC_SYMTAB` entries and 38,208 bytes of `LC_FUNCTION_STARTS`. No fileset entries. No symbol name contains the five requested driver/class fragments. Useful for a small XNU/provider check, not a substitute for PMGR/ANS driver code. |
| Preboot kernelcache, found with `/System/Volumes/Preboot/*/boot/*/System/Library/Caches/com.apple.kernelcaches/kernelcache` | One readable match; 30,316,177-byte carrier. Outer `IMG4`, inner `IM4P`, type `krnl`; payload starts at file offset 70, length 30,306,795, first magic `bvx2` | LZFSE-compressed kernel payload. Unique directory names are deliberately not retained. No decompression, signature/personalization inspection or extraction was performed. **ARM Mach-O architecture, target fileset membership and driver symbol availability are still Unknown.** This is the next candidate for the parent's isolated parser. |

`bvx2` is the LZFSE V2 block magic in the
[reference compression header](https://github.com/lzfse/lzfse/blob/master/src/lzfse_internal.h).
Mach-O fileset/entry semantics are defined in
[Apple's loader header](https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/EXTERNAL_HEADERS/mach-o/loader.h).
No encryption or access-control circumvention was attempted. A readable
carrier and compressed payload header do not by themselves establish that
it is the exact collection selected by the running boot configuration.

For the isolated next step: resolve the carrier without logging its unique
directory components, read only the IM4P payload (omit outer personalization
material), decompress into an ignored workspace, then validate Mach-O
architecture and enumerate only the five bundle IDs before selecting code.
Do not import the entire collection blindly into Ghidra or copy protected
services into the research dataset. Record firmware/build provenance and
content digests in that isolated pass; none were calculated here.

## Available small kernel entry points

These are **static file symbol addresses**, not runtime addresses. All are
defined in section 19 of `kernel.release.t6050`.

| Symbol | Static address |
|---|---|
| `_ml_processor_register` | `0xfffffe0007508254` |
| `_PE_cpu_machine_init` | `0xfffffe0007c3b868` |
| `_PE_cpu_signal` | `0xfffffe0007c3b96c` |
| `_PE_cpu_machine_quiesce` | `0xfffffe0007c3b9cc` |
| `_PE_cpu_start` and alias `_PE_cpu_start_from_kext` | `0xfffffe0007c9bfc8` |
| `_processor_start` and alias `_processor_start_from_kext` | `0xfffffe000739d11c` |

**Caution:** public current XNU
[IOCPU.cpp](https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/iokit/Kernel/IOCPU.cpp)
distinguishes the internal CPU-start dispatch from an unimplemented kext
entry. Therefore the exported `PE_cpu_start` alias is a candidate for
confirming tool operation, not evidence of the PMGR start sequence.
[machine_routines.c](https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/osfmk/arm64/machine_routines.c)
is the public comparison point for CPU registration/topology. Public `main`
is not proven identical to the installed kernel build.

## Bounded questions, in practical order

1. **PMGR / CPU startup:** when the actual ARM `AppleT6050PMGR` and
   `AppleARMPlatform` members are available, locate only the `Core` platform
   function dispatch and the CPU-start call chain. Determine whether it
   translates CPU IDs or sequences additional ordinary PMGR operations.
   Compare with existing m1n1 `src/smp.c` and the sanitized ADT
   `function-enable_core`; do not infer a fix from register-address proximity.
   Linux result: an original startup/DT correction if corroborated by a
   separately authorized native observation. Locked RVBAR and historical
   secondary-entry failure remain unresolved; no write or workaround is
   proposed from metadata alone.
2. **ANS register split:** inspect only ordinary queue initialization and
   completion/invalidation routines in the ARM `IONVMeFamily` member.
   Questions: which resource supplies NVMMU versus NVMe registers, when are
   IOQ base registers programmed, and which status offset belongs to this
   controller revision? Compare existing m1n1 `src/nvme.c`/`sart.c` and
   Linux patches 0001–0005. The existing m1n1 source uses IOQ offsets
   `0x1200/0x1208` and NVMMU status `0x29120`; the Linux discrepancy is already
   recorded in the native plan. Exclude storage contents, key handling and
   security services. Linux result: correct the unbooted draft only with
   independent evidence; later native read-only identification/read tests.
3. **CLPC/SOCTuner policy boundary:** identify registration callbacks and
   inputs/outputs between these PMGR nubs, frequency requests and IOReport
   telemetry. First determine whether policy or mechanism is being observed;
   class names do not prove a governor algorithm. Compare the existing
   OPP/EAS/QoS implementation and bounded macOS frequency/energy results.
   Linux result: an original policy over cpufreq/EAS only after physical
   DVFS semantics are validated. Do not translate decompiled algorithms
   directly into driver code or treat policy reconstruction as an idle fix.

Public-source reference for this comparison remains workspace m1n1
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`. The existing native series has
object/DT compilation evidence, no physical boot validation. macOS 26.6.2
driver behavior may depend on the current firmware and cannot be assumed
to apply to a different boot firmware or to older Apple Silicon.

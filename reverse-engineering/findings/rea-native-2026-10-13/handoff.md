# Agent B handoff: REA is operational; native SMP hypothesis sharpened

2026-10-13. Continued the existing project at `f05839b`; Claude/agent A owns
wakeup latency, the VM kernel and F-050. A subsequently committed
`f4baf47` and `37da5fc`. B changed none of that work or the live guest.
The earlier Mesa work is already committed as `47efd62`.

## What is ready

**Confirmed:** REA 6.4.0 with Ghidra 12.1.4 successfully decompiled original
ARM64 test code, then produced four bounded Apple driver function dossiers.
The C++ decompiler was built inside a separate diskless Linux VM. JDK 21,
the ARM64 native executable, and `procps` were required. No host tool install
or global REA configuration was needed. This resolves the missing-backend
blocker for this local workflow; Alpine remains outside REA's officially
supported distribution list.

The [lab instructions](../../rea-lab/README.md) are reproducible, and
[validation.json](validation.json) records versions and tests. The VM is
shut down; B's `quiet` lock is released. Full pseudocode, disassembly and
Apple binaries remain only in ignored `build/rea-lab/`.

## Artifacts actually analyzed

The standalone bundle executables are absent. `/System/Library/KernelCollections`
contains Intel collections and is the wrong ARM research input. The readable
Preboot carrier supplies an unencrypted LZFSE `krnl` payload; our parser copies
only that payload and omits personalization and unique directory names.
After decompression its header is ARM64e `MH_FILESET`, with these relevant
members present: AppleARMPlatform, ApplePMGR, AppleT6050PMGR,
AppleT6050CLPC, AppleT6050SOCTuner and IONVMeFamily.

Carrier digest:
`26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`.
The selected running boot identity was **not** established; provenance is
the readable carrier on macOS 26.6.2 / 25G83 on this Mac17,6/t6050 machine.
See [artifact inventory](artifact-inventory.md) and the manifest JSON files.

Three small Mach-O derivatives retain each selected member's original
code/data bytes and VM addresses. Only load-command offsets and local
symbol-string metadata are rewritten. The entire shared LINKEDIT string
table is not copied. Collection pointer fixups are **not** applied, so
indirect calls, authenticated pointers and cross-member targets can remain
unresolved. These derivatives are static analysis inputs, never boot files.

## Results and evidence quality

| Function | Assembly checked | What can be used |
|---|---:|---|
| `ApplePMGR::enableCPUCore(unsigned)` at `0xfffffe00094964a4` | 16 instructions / 64 bytes | For valid core IDs, builds a one-bit 64-bit mask, passes enable=true and tail-dispatches through a virtual call. The destination is unresolved here; this is not an MMIO write. |
| `ApplePMGR::configMiscCores(mask, bool)` at `0xfffffe0009495968` | 449 / 1,796 bytes | Assembly exposes table-dependent packing and indirect dispatch. Whole-function pseudocode is rejected: 449 of 1,633 high-pcode operations lie outside the provider's reported body. |
| `AppleT6050PMGR::configCPUComplexPowerState` at `0xfffffe0009880a64` | 51 / 204 bytes | Bounded assembly/call-site evidence only. Whole-function pseudocode rejected: 93 of 129 operations lie outside its body. |
| `AppleANS2CGv2Controller::SetupIOQARegister` at `0xfffffe000a649fb0` | 38 / 152 bytes | The attempted queue-setup trace reaches unresolved dependencies. Pseudocode rejected: one operation escapes the body. It does not resolve the NVMMU status offset or establish ANS3 runtime dispatch. |

All 554 instruction words match their original carrier bytes and were
independently decoded with Apple's LLVM. See
[llvm-cross-check.json](llvm-cross-check.json). That validates extraction and
instruction observations, not runtime behavior or every inferred C type.

**Confirmed tooling defect/limitation:** REA labels all these high-pcode
operations `member`, including out-of-body PCs. Missing cross-member
no-return knowledge is a plausible cause of Ghidra's fall-through recovery,
but that cause is not proven. The original `check_evidence.py` compares
numeric PCs with the provider's body instead of trusting that label. It
rejects those three complete pseudocode results. Do not copy them into a
driver or treat their extra loops as the selected function's behavior.

## Original Linux-compatible implementation

This follows up **existing H2** in `kernel/native-enablement/plan.md` §1.2;
the four-bit collision was already noted there. New work makes it executable
and connects it to bounded PMGR evidence.

**Observed ADT:** PMGR `clusters` bytes are
`060000000600060006000c00`. A candidate little-endian `(u16 count, u16 first_bit)`
interpretation gives `(6,0), (6,6), (6,12)`. Independently, all 18 CPU
`function-enable_core` declarations carry `BIT(cpu-id)`, with affinities
`0x000–005`, `0x100–105`, `0x200–205`.

**Confirmed public-source arithmetic:** pinned m1n1
[`smp.c`](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/smp.c)
uses `4 * cluster + core` for one startup mask. On this inventory, CPU pairs
4/6, 5/7, 10/12 and 11/13 alias bits 4, 5, 8 and 9. The candidate descriptor
layout yields 18 unique masks, each matching the declared ADT selector.
See [startup-layout-audit.json](startup-layout-audit.json).

**Implemented:** original portable C `startup_layout.[ch]` accepts explicit
cluster widths/start positions, validates the complete layout, and computes
global/local masks. It rejects overlaps, out-of-range shifts and invalid
core indexes without changing the output. A read-only Python audit ties its
test geometry to the sanitized ADT. The code derives from that data and
ordinary bitset arithmetic, not translated Apple pseudocode.

**Tested:** GCC 15.2.0 ARM64 Linux build (`-O2 -std=c11 -Wall -Wextra -Werror`),
18-core uniqueness and all 5,984 valid single-cluster masks, invalid-layout
cases, and 24 Python tests. The same C tests pass on macOS with AddressSanitizer
and UndefinedBehaviorSanitizer. Linux ran in the diskless VM; these are
software correctness tests, not native boot or hardware benchmarks.

**Still a hypothesis:** these candidate masks are the correct CPU_START
register encoding for this firmware, and correcting them would make SMP
work. The ADT platform-function argument is not automatically a register
value. We have not identified the complete t6050 dispatch/register sequence.
The locked RVBAR/entry-point hypothesis H1 is still open. No m1n1 startup
write or Linux hardware driver was changed, and no native performance gain
is claimed.

## Next work, without overlapping A

1. A continues its controlled vmpoll/IPI measurements and then F-050.
   These native PMGR findings do not explain a virtual CPU's HVF wakeup path.
2. B can repair the analysis boundary: resolve only the relevant external
   symbols/no-return calls and selected collection fixups, then re-run the
   failed pseudocode gates. Do not mark every cold function no-return by name.
3. Trace where PMGR obtains its cluster descriptors and the selected `Core`
   virtual dispatch. Corroborate any proposed startup sequence with public
   source and, after explicit native authorization, bounded register/entry
   observations. Keep RVBAR and mask hypotheses separate.
4. Resume native full-kernel/schema validation in a separate job after A's
   measurements. The layout helper can become a draft adapter only after
   the hardware-facing contract is established; it is not ready to paste
   into `smp_start_cpu()` as a validated fix.
5. At the native boot gate, the planned configuration agent C uses a fresh
   hardware capability inventory and repository-backed packages/configuration.
   It must not transplant the VM kernel, host video/AI bridges, NAT settings
   or polling policy into native Omarchy. Reach the machine over the approved
   second-computer console/network path, record changes, and run acceptance
   checks before enabling acceleration. `coordination.md` keeps that handoff
   after the relevant native gates.

Boot policy, partitions, firmware, SEP/credentials, model-history rewriting
and uploads remain untouched. A private backup and native installation still
require their separate user decisions.

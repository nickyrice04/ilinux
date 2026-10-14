# M5 AOP DAPF handoff correction — 2026-10-13

## Evidence and diagnosis

Attempt 3 passed every boot022 preflight, including the native framebuffer
fix. At handoff, m1n1 raised an asynchronous SError in EL2. Linux execution was
not observed. [M1 result](../../../native/boot/stage-b-2026-10-13-attempt3-result.md)
retains the code-relative PC `0x16458` without target identifiers.

**Confirmed:** the retained ELF reproduces the installed raw m1n1 image exactly
with GNU objcopy. Its symbols/debug lines place the PC in `dapf_init_t8110a`,
inlined into `dapf_init`, at a byte load from the configuration record. A DAPF
MMIO store occurs eight instructions earlier at `0x16438`. **The asynchronous
exception does not identify that store conclusively as the triggering write.**

**Confirmed inventory mismatch:** m1n1's fixed table selects register region 1
of `/arm-io/dart-aop`. This Mac's sanitized ADT declares only DART instance 0
and GAPF instance 0 there; it declares **no DAPF**. Thus the routine applies
DAPF offsets to a different block. By contrast, MTP declares DAPF at index 1,
and ISP0 at index 5, matching the pinned table. The first table entry is AOP,
and no successful DAPF initialization message appeared before the exception.
This is a concrete defect and a **likely cause**, not a hardware-validated fix.

## REA / decompilation

REA 6.4.0 / Ghidra 12.1.4 decompiled `dapf_init` from the exact ELF in the
existing isolated Linux lab. Ghidra loads this PIE at +0x100000; the first
unrebased address query returned no procedure, then lookup by **symbol name**
succeeded at `0x1160e0`. No host decompiler install was needed.

All 300 instructions are covered by the provider body. All 319 high-pcode
operations stay inside it; no truncated-control-flow marker. GNU objdump and
Apple LLVM independently decode 300 instruction words matching the shipped raw
bytes. Apple LLVM rejects the ELF metadata, so `audit.py` wraps only the exact
1,200 function bytes in an analysis-only Mach-O object, preserving addresses.
Neither target nor wrapper is executed. Five ELF relative relocations establish
the runtime work-list pointer layout used below. [evidence.json](evidence.json)
records hashes, offsets, boundary checks and sanitized instance types.

Pseudocode agrees with public source about the fixed index and write sequence.
We do not treat its recovered C types as verified hardware specifications.
This problem is in our open-source bootloader path; no proprietary macOS code
was needed or copied into the fix. Complete REA results stay in ignored local
`build/rea-lab/dapf-boot023` in the original research checkout.

## Implementations

1. **Source fix:** `ilinux_dapf_layout.h` is an original byte-safe selector for
   ADT instance metadata. `m1n1-instance-guard.patch` applies it before any power
   or register access. It finds DAPF instance zero, skips absent DAPF while
   leaving other filters unchanged, rejects malformed/ambiguous metadata, and
   preserves the historical path if no instance property exists. Apply the patch
   to pin `57a9339ffd1876e78297b17d34dece8cff8fa1ba` and copy the header into
   `src/`; job 023 does both on an isolated copy. Full raw/macho/ELF build PASS.
   **This new binary is not installed or selected for the next attempt.**
2. **Narrow RAM workaround for the existing installed binary:**
   `native/boot/dapf_guard.py` verifies the exact packaged image, live function
   bytes, relocated table, entry names and live ADT metadata. It requires the
   reviewed AOP DART+GAPF layout and correct DAPF indexes for every other present
   entry. Unknown layouts stop before upload. After the existing prepared-DT
   and secondary-state gates pass, it shifts the other entries plus terminator
   over the absent AOP DAPF entry and verifies readback. Exactly one 96-byte
   write stays inside m1n1's RAM data table. No instruction patch, filter MMIO,
   security control, persistent boot object or original macOS file is changed
   by the workaround. Other m1n1 handoff hardware initialization remains active.

The RAM path is intentionally narrower than the source fix: it does not guess
new indexes, alter firmware filter policy, or suppress arbitrary errors. A
changed/already-patched table or failed readback stops handoff; return to macOS,
not an automatic retry. A fresh boot restores the installed table. This is a
bring-up workaround, not a Linux AOP/GAPF driver or an accelerated desktop.

## Tests and limits

* Original pinned C reproduced all five DAPF writes to the synthetic AOP GAPF
  region. The mock records those writes; it never accesses physical MMIO.
* Patched actual C: **12 scenarios PASS under ASan/UBSan**. Absent DAPF has zero
  register/power operations; valid MTP/ISP and moved DAPF work; legacy/no-metadata
  and 56-byte records preserved; malformed/duplicate layouts rejected.
* Linux VM: **31 launcher + 14 RAM-guard + 2 actual-parser + 4 root-ADT + 1 real
  serializer + 5 framebuffer tests PASS**. The parser regression caught raw
  `reg` bytes being counted as ranges; corrected to handle both raw and decoded
  representations. **16 RAM-guard tests PASS on macOS** after adding two final
  end-to-end failure-order tests (not independently rerun in Linux).
* Those final cases verify a bad layout prevents every upload and a failing
  prepared-DT gate leaves the RAM table untouched. Failed correction readback
  also prevents `kboot_boot`. Tests use synthetic memory and ADTs only.
* Existing boot022 archive/manifest/payloads remain byte-identical. Current
  offline launcher verification PASS. No hardware benchmark or native attempt
  was run here. No performance/efficiency gain is claimed.

VM: 2 vCPU/4 GiB, Linux 7.1.6-vzrun2 aarch64, GCC 16.1.1 20260430,
Python 3.14.8; host Python 3.9.6. C tests use `-std=c11 -O1 -g -Wall -Wextra
-Werror -fsanitize=address,undefined -fno-omit-frame-pointer`. m1n1 is built
with its pinned flags via `M1N1_VERSION_TAG=ilinux-57a9339-dapf-guard make -j2
ARCH= BUILDSTD=1`; no compiler warnings/errors in the incremental build log.
Build/test job 02:53:16–02:53:17 UTC first stopped on the parser regression;
corrected Python suites passed at 02:56:26 UTC, 2026-10-14. These durations are
job timings, not native boot benchmarks. All VMs stopped; quiet locks released.

## Next experiment

M1 pulls the new controller code and verifies it against the **existing boot022
package**. No download, reinstall or Recovery is required. Fresh post-attempt-3
policy JSON supplied by the user is original Full/lab Permissive, both exit 0.
Independent return checks confirm Macintosh HD/build 25G83, System/Data
FileVault, SIP/authenticated-root and staged m1n1 hash. Default/installed boot
object not independently queried.

The next proposed attempt uses the existing lab entry and a fresh m1n1 session.
It must capture both new DAPF checkpoints, the handoff, visible kernel/PID 1,
one CPU, 60-second liveness and original-macOS return. See the
[current M1 checklist](../../../tools/m1n1-client/stage-b-instructions.md).
Native correction NOT TESTED; Linux execution NOT OBSERVED. If the exception
changes or remains, use the new precise checkpoint rather than dropping gates.

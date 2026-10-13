# Agent B: CPU startup references and diagnostic guard

User-directed native priority pass, 2026-10-13. A owns the full native
kernel/schema build, first-boot observation plan and agent C configuration
handoff. B owns this research and its isolated experiments. No live Omarchy
configuration, native kernel build job or macOS reference state is changed.

## Findings that affect the next engineering step

**Confirmed static metadata:** the selected ARM64e kernel collection uses
Apple's documented `DYLD_CHAINED_PTR_64_KERNEL_CACHE` format (8). The new
original `kernelcache_refs.py` checks page-chain membership before decoding
a selected reference. It supports only the observed format and cache level
0, rejecting unknown formats, missing bases, malformed pages and pointers
that are merely pointer-shaped data. It reads files; it never authenticates,
signs, installs or executes a pointer.

Twelve selected references in AppleT6050PMGR's dispatch table now resolve
to exact defined symbols. Eleven call-site diversity constants were also
checked against the encoded metadata; the readReg32 row has no such check.
The address-point bias is 16 bytes. See `pmgr-references.json`. This proves
static table contents, not the identity of a live runtime object.

* `enableCPUCores` dispatches through slot `0xd18` to the shared
  `ApplePMGR::configMiscCores` implementation in this table.
* `configCPUComplexPowerState` dispatches through `0xf50` to
  `ApplePMGR::enableCluster`; it is not itself the raw CPU_START write.
* Startup writes through `0x1058` select t6050's `writeReg32` override.
  The override has a register-map/offset/die exception before forwarding
  to the shared writer. Thus neither an abstract offset nor an ADT
  platform-function argument is automatically a physical MMIO address.

**Stronger support for H2:** a separately bounded, original-byte/LLVM-checked
slice in `ApplePMGR::initDriver` refers to the literal `clusters` property,
obtains its data and stores a four-byte-record table at object offset
`0x6310`. The already REA/LLVM-checked `configMiscCores` instructions read
that same member, using two 16-bit fields per record. The source bytes in
our sanitized ADT describe `(6,0), (6,6), (6,12)` under the candidate
count/bit-position interpretation. A zero position has a fallback in the
generic code; do not generalize our unit's interpretation to other SoCs.

This is additional static evidence for descriptor-based packing, beyond
the original arithmetic collision. It does **not** establish which generic
branch executes on this firmware, the complete register-map initialization,
or whether changing m1n1's four-bit stride makes a secondary enter. H1
(entry vector), H2 (mask/register contract), H3 (early shared state) and H4
(early exceptions) remain separate. Retest the current m1n1 baseline first.

**Confirmed bounded idle-hook behavior:** REA obtained `cpuComplexIdleEnter`
and `cpuComplexIdleExit`, with no out-of-body pcode in those two functions.
Both have a loop that calls `readACCReg` with selector `0xe20020` and checks
bit 31. The entry hook conditionally skips it and may dispatch a voltage-rail
widget operation, depending on runtime state. `0xe20020` is an abstract ACC
selector here, **not a confirmed physical address**. The hook names do not
prove the complete architectural WFI/context-restore sequence. Keep the
existing idle workarounds until a complete safe Linux path is established.

Independent public-source context: XNU's `machine_idle()` chooses a WFE
recommendation or `Idle_context()`, while `cpu.c` selects retention or plain
WFI under build-time conditions. Its reset assembly also distinguishes cold
startup and idle-resume handlers. These public paths corroborate the need
to understand context preservation; they do not identify this binary's
build configuration or demonstrate a working Linux resume path.

## Original implementation

`kernel/experiments/native-startup/0001-smp-stop-on-locked-rvbar-mismatch.patch`
adds an optional conservative startup guard to public m1n1. The baseline
prints a failed locked-RVBAR comparison but still changes shared state and
writes CPU_START. The experiment returns before those actions. It reads no
new register and performs no hardware operation here.

This change is based on the public m1n1 source and H1; it is not a translation
of Apple's startup routine. It does not fix H2 or enable a native CPU. The
experiment README documents the possible firmware-trampoline limitation.

## Evidence and validation

The input is the same readable carrier as F-070–F-075, SHA256
`26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`,
from this Mac17,6 running macOS 26.6.2 / 25G83. Which carrier the running
boot selected remains unestablished. All raw Apple binaries and complete
disassembly/pseudocode remain in ignored `build/rea-lab/`.

REA 6.4.0/Ghidra 12.1.4 runs in the diskless ARM64 Linux lab. Two successful
analysis batches completed six functions / 872 independently LLVM-checked words.
`enableCluster` fails the whole-function pseudocode gate; its decompiled
control flow must not guide a driver implementation. The two idle hooks
pass the consistency gate and were manually reviewed against their assembly.
`readACCReg` confirms a table lookup and selector-to-map translation before
the shared read helper. The register writer retains an unresolved indirect
jump in pseudocode, resolved separately using the original collection's base
table reference. `initRegMaps` reports removed blocks, so its whole decompiled
control flow is not treated as established; only bounded assembly sites are
usable. None of these gates establishes runtime hardware behavior.
The cluster-property slice adds 51 independently checked instruction words;
it is explicitly a slice, not a recovered complete function.

Validation completed in the isolated Linux lab after A released its build
lock: GCC 15.2.0 reproduces the baseline mismatch regression, with two
startup-register writes despite the warning. All eight patched cases pass;
seven unchanged cases also pass on the baseline. Clang 21.1.2 ASan/UBSan
passes the eight patched cases. The full patched `smp.c` compiles to an
AArch64 relocatable object. A first object-build attempt exposed a missing
`config.h` in the disposable setup; the preparer now copies it and the final
batch passed. Seventeen reference-parser tests pass on ARM64 Linux; all
43 analysis-tool Python tests pass on the host. See `validation.json` and
the retained test logs. No full m1n1 image link or native run is claimed.

No performance benchmark is inferred from this guard. Mock operation counts
are correctness checks, not physical latency or power measurements. The
analysis VM is stopped and B's `quiet` lock is released.

## Handoff to A

1. Use A's successful full native build from job 020 / F-056 to resolve
   the remaining DT schema/probe issues and establish the physical
   observation path.
2. At the approved hardware gate, run the unmodified pinned m1n1 baseline
   and retain CPU identity, entry-vector diagnostics and secondary-entry
   evidence before changing startup logic.
3. If the baseline reports a locked-vector mismatch, distinguish a possible
   firmware trampoline from a wrong image entry. This guard offers an
   explicitly conservative diagnostic alternative, not a bypass.
4. Do not install a guessed six-bit stride or remove `idle=nop`/
   `arm64.nowfxt` based on these findings. Resolve the runtime register-map
   and low-power context requirements first.
5. C configures native userspace after usable access exists. VM polling,
   host GPU/video bridges and guest power settings are not native defaults.

## Sources and reproduction

* [Public pointer layout](https://github.com/apple-oss-distributions/dyld/blob/main/include/mach-o/fixup-chains.h)
* [Pinned m1n1 startup source](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/smp.c)
* [Public XNU idle selection](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/arm64/machine_routines.c),
  [CPU idle/start](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/arm64/cpu.c),
  [reset and resume entry](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/arm64/start.s)
  (read 2026-10-13; not asserted to match the installed kernel).
* Local REA plan: `analysis-plan.json`; byte checks: `llvm-cross-check.json`;
  supplemental slice: `cluster-property-evidence.json`.

For each address in `pmgr-references.json`, run the original parser against
the same digest-pinned carrier; include the two PMGR symbol members:

```sh
python3 -I reverse-engineering/rea-lab/kernelcache_refs.py \
  build/rea-lab/artifacts/kernelcache.macho 0xfffffe0008166590 \
  --symbols-member com.apple.driver.ApplePMGR \
  --symbols-member com.apple.driver.AppleT6050PMGR
```

Replay all twelve stored references and the property slice with
`verify_cpu_references.py CARRIER FINDINGS_DIRECTORY`. It also checks the
ordinary kernel allocation/copy helper symbol identities. This replay
verifies bytes and metadata, not instruction or runtime semantics.

The native-startup README specifies source pinning and Linux tests.
The isolated lab README specifies VM startup, time limits and locking.

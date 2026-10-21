# Exact-instruction reset-entry model

Original dependency-free Python interpreter for a narrow path in the pinned,
public m1n1 boot021 image. It reads and decodes actual instruction words from
`cpu_reset` through the **first stack-pair store** of `_cpu_reset_c`; it does
not rewrite the algorithm in C and does not execute the input file on the host.
The complete image must match its retained SHA-256 pin and reviewed instruction
bindings. A supplied original symbol table must also match its SHA-256 pin.
This directory contains no Apple firmware or proprietary code.

The model answers a specific question: with explicitly synthetic entry state
and accessible RAM, which stack does the existing code select and where does
its first C prologue save the return address? It does not establish the real
reset state, physical start success, exception behavior, memory attributes,
cache publication, coherency, timing, energy or Linux SMP.

## Boundaries

- Synthetic CPU1 MPIDR, EL1/EL2/EL3 entry, image relocation, reset table and
  fallback/dedicated stack regions. No actual machine address or RAM is read.
- Every interpreted instruction comes from the supplied pinned image. Only
  the reset-entry interval, the actual one-instruction `debug_putc` RET and
  the first C prologue instruction can be fetched. Execution stops immediately
  after that store. No subsequent C body or EL3 exception return is modeled.
- Supported forms are MOVZ, B/BL/RET, the two specific MRS reads, add/subtract
  immediate, EQ/NE branches, AND immediate, ADRP, literal/unsigned/unscaled
  LDR, CBZ/CBNZ, post-index LDP, the needed register compare/MOV alias and the
  first pre-index STP. Unknown forms, sysregs, unmapped memory and bounds fail.
  AND-immediate to SP/WSP is explicitly outside the supported subset; it is
  not silently treated as a zero-register destination.
  NOP and DSB SY have explicit model events; the latter implements no physical
  memory-ordering guarantee. WFE, unknown hints and arbitrary MSRs are refused.
- Default 256 interpreted steps; hard maximum 4096. No privileged execution,
  external emulator, USB, device files, subprocesses or native launcher.
- RAM writes can reach only the two synthetic stack allocations. The model
  deliberately assumes ordinary accessible bytes. It **cannot decide whether
  the actual stack's Device/Normal mapping permits an architectural access**.
  That requires an independent page-table/architecture audit and native evidence.

Table-miss, second-slot hit, matching entry with zero stack, last-slot hit,
different MPIDR entry, high MPIDR flag bits and EL2/EL3 cases are included.
EL3 bypasses the table and reaches the first C prologue with its distinct BL
return offset; nothing here proves that EL3 is the real machine entry level.
The shared-padding stack fixture spans image offsets `0x94000..0xa0000`
(48 KiB). This is a synthetic test fixture, not a deployment choice.

## Reproduce with retained artifacts

From the repository root, replace the variables with the retained package's
image and original job021 symbol text; no extraction or download is needed:

```sh
python3 -I kernel/experiments/smp31e-emulator/test_emulate.py \
  --image "$BOOT021_IMAGE" --symbols "$BOOT021_SYMBOLS" -v
python3 -I kernel/experiments/smp31e-emulator/emulate.py \
  --image "$BOOT021_IMAGE" --symbols "$BOOT021_SYMBOLS" --case all
```

`--trace` emits only image-relative locations and decoded operation labels.
Inputs that fail their pins are refused before interpretation. `--symbols` is
optional for the M1 retained package, which does not contain the original
symbol text. With it, results report `symbol_validation:full_symbol_digest`;
without it, `reviewed_layout_only` and a null checked symbol digest. The latter
uses the reviewed fixed layout, exact full-image digest and instruction
bindings; it does not claim a fresh symbol-file verification. The CLI emits
one JSON object with a `scenarios` array. Decoder unit
tests intentionally use synthetic instruction variants through the internal
`Machine` class; the CLI and public `simulate()` have no pin bypass. The tests
require the exact image rather than silently skipping integration coverage.
CLI failures expose only fixed model-refusal labels or an exception's type;
filesystem paths, input bytes and external exception messages are omitted.

The expected first-frame store saves FP at entry-SP minus 32 and LR at minus
24. The expected saved LR is image-relative `0x974` for the non-EL3 call and
`0x97c` for the EL3 call. A matching retained stack-table entry chooses the
dedicated stack; no match or a zero stack chooses the fallback pointer. These
are interpreter results conditional on the synthetic inputs, not native facts.

## Independent single-instruction differential in the ARM64 Linux VM

`first_frame.S` contains the exact pinned STP word followed by original
trampoline code that restores the caller's SP/FP/LR. `test_first_frame.c`
compares the entire synthetic stack against expected bytes for four FP/LR
patterns. It checks the linked instruction word, SP delta and canaries.
Only the ordinary userspace STP is tested; the privileged reset path is never
executed. The C harness rejects non-Linux or non-ARM64 builds.

Inside the existing VM, with output under its writable job directory:

```sh
cc -std=c11 -O2 -Wall -Wextra -Werror \
  kernel/experiments/smp31e-emulator/test_first_frame.c \
  kernel/experiments/smp31e-emulator/first_frame.S \
  -o "$JOB_OUT/test-first-frame"
"$JOB_OUT/test-first-frame"
```

VM results are recorded by the coordinating job. This differential checks
the STP interpretation against a real ARM64 userspace instruction; it cannot
validate boot-time Device mappings, caches, firmware or the reset contract.

## Evidence separation

Image/symbol pins and the public-source entry audit select the exact bytes.
Synthetic tests establish decoder/model behavior. The isolated differential
establishes one instruction's userspace store behavior. Native frame remnants,
if later observed, still are not a live PC or proof that a function returned.
No model success authorizes a target operation or advances a consumed attempt.

## Separate recorder equivalence model

`recorder_check.py` verifies the original full image and symbol digests, calls
the sibling original recorder builder, and requires its exact 204-byte digest
and entry branch. It overlays those two bounded intervals in memory only. It
does not weaken the unchanged-image mode or accept an arbitrary patched file.
The derived image is never executed or written to disk.

The extra decoder forms are MOVK, the specific low-24-bit UBFX, STR to four
allowlisted record fields, and the three selected SCTLR MRS forms. System
register values are synthetic. Unknown operations, arbitrary writes, MMIO,
incorrect EL selection and out-of-scope instruction fetches refuse.

Eleven scenarios cover EL1/EL2/EL3, two unsupported EL values, two other-CPU
filters, high MPIDR flag bits and selected-SCTLR read faults at each supported
EL. Original and patched paths are compared at `0x900` and `0x904` for X0,
every register except temporarily dead X8, SP and LR; X8 joins the comparison
after its original redefinition at `0x908`, and NZCV after its original CMP at
`0x90c`, before the conditional branch consumes it. All sixteen initial NZCV
patterns are regression-tested for the successful replay paths.

Fault scenarios stop at the modeled read, retain phase 2 and never claim
replay equivalence, exception handling or recovery. Unsupported EL scenarios
record phase 255 and perform no selected-SCTLR read. Phases and field ordering
are instruction-model events; DSB instructions do not make physical cache
visibility or architectural entry state part of this model.

```sh
python3 -I kernel/experiments/smp31e-emulator/test_recorder_check.py \
  --image "$BOOT021_IMAGE" --symbols "$BOOT021_SYMBOLS" -v
python3 -I kernel/experiments/smp31e-emulator/recorder_check.py \
  --image "$BOOT021_IMAGE" --symbols "$BOOT021_SYMBOLS"
```

The CLI emits one sanitized JSON document, including artifact digests, modeled
phase events, checkpoint comparisons and explicit native HOLD. Full symbols
are required for this separate overlay audit. No target adapter, code
publication mechanism, protected-memory workaround or native launcher is
provided. The interpreter, assembler-byte comparison, mapping audit and native
observations remain independent kinds of evidence.

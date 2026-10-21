# Attempt 31F: observe the first vector entry before register reads

Status: **offline instruction/layout checks PASS; native 31F NOT RUN**.
This changes diagnostic coverage, not CPU performance or Linux SMP support.
Attempt 31E and its receipts remain unchanged.

## Evidence and the question being tested

**Observed, 31E:** CPU0 passed all 16 translation probes and verified the
recorder body, hook and remaining loaded text. Both approved CPU1 start stores
were attempted and acknowledged. The 93 recorder samples contained no visible
phase or identity; the 94 reset/spin samples contained no reset record. No Linux
handoff or timer callback ran. See [31E result](../attempt31e-2026-10-21-result.md).
These observations establish CPU0 publication/readback, not CPU1 instruction
fetch, entry state, cache coherence, or execution of zero instructions.

**Confirmed from pinned public source and the actual boot021 image:** the path
before the old hook at image offset `0x8fc` is only two instructions: the vector
at offset zero assigns `X9 = 48`, then the branch at `0x4` targets `cpu_reset`
at `0x8fc`. There is no intervening UART, stack or C initialization to hide.
The existing recorder, however, reads MPIDR and checks its low 24 bits against
the expected CPU1 identity **before its first RAM store**. An unexpected
identity or fault at that first system-register read can therefore leave the
same all-zero record as no observed entry. This is an observation gap, not
evidence that CPU1 actually has a different identity.

The next precise question is: **does any execution reach vector offset zero,
and how far does it proceed before the original reset path?** The new recorder
removes the initial identity filter, records a marker before any `MRS`, then
records identity and entry registers in separate phases. Unexpected identities
remain diagnostic evidence; they never authorize callbacks or Linux entry.

## Original recorder and exact layout

Only the vector's first four bytes are replaced with a branch into existing
zero padding at `0xa00`. The body is **168 bytes**, SHA-256
`52f9d1b312725cdc9261e0fbf1c31991e9078a663827734b9ba54c9d171106bc`.
The hook word is `0x14000280`. Record storage remains the reviewed 64-byte
window `0x90a40..0x90a80`; only its first four 64-bit fields are written.

| Phase | Committed meaning | Fields available after a stable snapshot |
| --- | --- | --- |
| 0 | No marker observed | No secondary state can be inferred |
| 1 | First entry marker, before every system-register read | Identity still unknown |
| 2 | Unfiltered MPIDR low 24 bits stored | Observed identity, including an unexpected one |
| 3 | CurrentEL stored, before selected SCTLR read | Identity and entry EL |
| 4 | Selected SCTLR stored | Complete register sample; not a reset-arrival or park proof |
| 255 | CurrentEL was unsupported by this recorder | Identity and unsupported EL; stop |

Field offsets are phase `+0`, CurrentEL `+8`, MPIDR low24 `+16`, selected SCTLR
`+24`. The remaining 32 bytes are untouched. Valid EL paths publish
`1→2→3→4`; unsupported paths publish `1→2→3→255`. Each completed field precedes
the following phase store and publication barriers. The very first store at
`0xa0c` follows only ADRP, ADD and MOV; the first MRS is at `0xa14`.

The body uses no stack and changes no LR, MMIO or system register. It temporarily
uses X9 for CurrentEL, then replays the exact original `MOV X9,#48` at `0xaa0`
and resumes at the unchanged branch at `0x4`. X0, X8 and NZCV are dead until the
original reset prefix defines them at `0x8fc`, `0x904` and `0x908`, respectively.
The actual linked `debug_putc` called in this prefix is a single RET. The model
checks all other registers, SP and LR at every checkpoint, adds X0 once it is
defined, then X8, then NZCV. At `0x90c` the complete modeled register state is
identical to the original prefix.

## Important limits and stop conditions

* Vector offset zero is also the architectural current-EL/SP0 synchronous
  exception slot. A marker does not uniquely identify reset entry or CPU1.
  Faults can re-enter this slot, overwrite a partial record, or recur. The
  offline model **stops at faults** and does not model exception recursion,
  recovery or their eventual hardware behavior. Phase regression, conflicting
  samples or an unexpected identity must stop the controller.
* Phase 1 still depends on fetching the hook and address instructions and
  successfully storing through the entry address view. A zero record remains
  compatible with failed dispatch, wrong effective vector, stale code visibility,
  inaccessible memory, or a fault before/at the first store. It is not proof of
  no executed instructions. CPU1 MMU/cache state remains unknown until measured.
* A phase store may be observed before its following DSB completes. Even phase 4
  does not prove return to the original path, arrival at the reset table, a
  live secondary controller, or a successful park. Existing independent arrival
  and liveness checks remain necessary.
* Existing RVBAR samples are **mirror-only** observations. They do not prove the
  effective reset target. No new RVBAR/security/cluster-power write is justified
  by 31E's timeout. The same two reviewed startup writes are sufficient for
  this diagnostic comparison.
* CPU0's publication/readback checks cannot prove an offline secondary's
  instruction-cache visibility. The recorder adds no guessed cache-control
  changes. See [31E publication review](../attempt31e/publication-review.md).
* The experiment starts only the existing selected CPU1. It does not treat all
  18 cores as interchangeable. Core type, cluster, CPU identity and PMGR mask
  remain distinct inputs; retained unexpected identities are classified by the
  reviewed topology and rejected for controller execution. Enabling the other
  clusters and scheduler capacity/frequency modeling are later work.

## Reproducible offline validation

The implementation is original project code under
`kernel/experiments/smp31f-entry/`. `builder.py` independently encodes the narrow
instruction subset; `recorder.S` is the separate assembler input. The parent
validation job must independently assemble it and compare bytes before native
use. No host instruction execution, target access, or hardware operation occurs
in these checks.

Using the retained boot021 image and full symbol file:

```sh
python3 -I kernel/experiments/smp31f-entry/test_recorder_check.py \
  --image virtualization/jobs/063-smp31e-controller/out/boot021.bin \
  --symbols virtualization/jobs/063-smp31e-controller/out/m1n1-symbols.txt
```

**Measured offline:** 23 test methods pass, covering 13 scenarios, all 16 initial
NZCV patterns for each of 10 nonfault scenarios, six replay checkpoints, and
332 injected stops immediately before/after reached MRS, STR and DSB operations.
Every statically present recorder boundary is reached by the case matrix.
The first-MRS fault now retains phase 1 in the interpreter. The first-store
fault may still leave zero. CPU0, zero MPIDR, another same-cluster identity and
another cluster are recorded rather than filtered. Record-tail canaries remain
unchanged. Wrong X9 replay, changed input/overlay pins, nonrecord writes and
unsupported instructions are refused. Public model output contains no raw
synthetic register/address values and explicitly denies hardware simulation.

The audit verifies the entire image and symbol digests, unchanged vector and
reset-prefix instructions, zero padding, allocated symbols, relative relocations,
direct branches/literals and ADR/adjacent-ADRP-plus-ADD references. This is not
a proof against computed addresses or broad range operations.

Evidence provenance:

| Public input | Pin |
| --- | --- |
| m1n1 source commit | `57a9339ffd1876e78297b17d34dece8cff8fa1ba` |
| `src/start.S` SHA-256, checked locally | `91de75024c12f034a046171e88c8be9377bb09e4bfe95bf1ac5ba3cdd1e423ea` |
| Actual retained boot021 image SHA-256 | `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664` |
| Full symbol table SHA-256 | `751a9643a2196eda44efba4789aa789465b2b75e9546be460946d2fa4c70ac11` |

No proprietary pseudocode or Apple bytes were needed for this specific reset
prefix: the exact failing component is the project's public m1n1 build.
REA findings about macOS startup inform the parallel startup review; they do
not convert this narrow interpreter into a firmware emulator.

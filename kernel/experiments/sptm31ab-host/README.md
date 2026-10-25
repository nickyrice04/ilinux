# 31AB original entry image and uncalled bootstrap transports

This module builds a small original AArch64 executable image with owned capture
storage, a16KiB stack, a complete vector table and three separate bootstrap-call
routines. It is a concrete linked artifact for packaging and instruction testing.
**NOT_DEPLOYABLE:** no installed image, accepted firmware handoff, live monitor
invocation, native observation channel or physical CPU-start result is supplied.

The entry first reads `CurrentEL`, DAIF and the incoming SP, masks interrupt
classes, and initializes its own256-byte record. It stores incoming x0/x1/x2
without interpreting or dereferencing them. It never reads the incoming stack.
EL1 and EL2 continuations select the current EL's stack, set the owned SP and
install the corresponding explicit VBAR bank. HCR_EL2 is read only on EL2; no VHE
state or normal T6050 execution level is inferred. Other captured EL values are
recorded and refused. EL0 is outside the privileged entry precondition and may
trap before a record can be written. Initial entry/vector access permissions and
RW image mapping still require qualification; owning storage in an image does
not establish that firmware mapped it.

All16 architectural vector slots identify their slot and branch to an original
stackless fatal recorder. It records the current EL's ESR/ELR/FAR/SPSR, SP and
masked DAIF, then parks. It does not resume the interrupted instruction, perform
ERET, install a monitor return handler or implement guarded exception return.
Exceptions routed to a higher EL or guarded mode are outside this table's
coverage. DAIF masking does not prevent synchronous faults or establish routing.
The handler assumes its own record remains writable; it cannot recover from a
fault while writing that record.

Phase1 means the initial registers were captured; phase2 means the local vector
installation reached the diagnostic park; phase3 means a fatal vector recorded
an exception; phase0x80 means unsupported captured EL. None means monitor readiness,
registration success or firmware acceptance. DSB/ISB provide architectural ordering
for the written record and VBAR update; this is not a cache-flush or external
observer guarantee. The RAM marker has no established native observation channel.
There are no peripheral accesses, argument-record reads, callbacks, WFI/WFE or
monitor calls in the capture/fatal path. The park is a direct self-branch.

The separate external-AAPCS routines prepare the published fixed bootstrap
dispatches:15 with no argument,14 with one64-bit physical-affinity argument,
and18 with one64-bit return-handler address. Each owns a16-byte aligned frame,
preserves its frame pointer/link register, puts the dispatch identifier in x16,
uses the published GENTER selector0 encoding and restores its frame before
returning. They do not touch x18 or SIMD registers and return no success value.
They are ordinary externally declared functions, not inline assembly with an
invented compiler clobber list. Actual transport preservation and allowed runtime
context remain native integration obligations. The diagnostic does not call any
of these routines; no test here executes GENTER.

Dispatch15 resides in the initially executable boot region for any future early
use. Dispatch14/18 reside in separate late text; making that text executable and
establishing each service's actual prerequisites remain separate steps. Qualify
the dispatch transport and only helper services actually used; this image does
not require initializing unused opaque helper state. The public/behavioral basis
is the [31AA minimal contract](../../../research/native31aa-public-contract.md)
and [bounded local handoff findings](../../../research/native31aa-handoff.md).
No Apple decompiler output or extracted implementation was used to write this code.

The canonical payload is exactly0x14000 bytes, with these image-relative spans:

| Span | Purpose | Permissions |
| --- | --- | --- |
|0x0000–0x4000|Zero canvas reserved for the parent packager's header|Not an ELF load segment|
|0x4000–0x8000|Owned record and reserved zero data|RW|
|0x8000–0xc000|Owned16KiB stack|RW|
|0xc000–0x10000|Entry, vectors at0xc800, fatal recorder, dispatch15 at0xf000|RX boot|
|0x10000–0x14000|Separate dispatch14/18 routines and zero reserve|RX late|

Every internal address reference is ADR relative to the executing instruction.
There are no absolute pointer data, external dependencies, literal address loads,
runtime relocations or chained pointer fixups in this original payload. The
independent audit checks the complete nonzero payload, exact allowed instruction
classes and operands, all branch targets, owned-record stores, all16 vector
slots, all three transport bodies, section/segment permissions, symbols and ELF
relocation/undefined-symbol tables. This conclusion comes from those checks,
not merely the absence of fixup metadata. The audit also verifies byte-identical
payloads linked at base0 and0x40000000. Qualified image placement and native memory
permissions remain required even when pointer rebasing is unnecessary.

On an existing AArch64 Linux toolchain, run:

```sh
python3 kernel/experiments/sptm31ab-host/run.py \
  --output build/31ab-host-linked --cc cc --ld ld
```

Outputs include `canonical.elf`, `slid.elf`, exact `payload.bin`, `layout.json`,
per-base audit metadata and source-bound logs/results. `layout.json` exposes
symbol offsets including entry/park/fault-park, vectors, capture and stack bounds,
all record fields and phase meanings. The parent owns Mach-O packaging, inspector
comparison and execution of this original code in an existing emulator. Neither
the builder nor its audit executes the payload or a monitor call.

The runner includes six audit groups and16 adversarial ELF/instruction mutations
per linked base. Host object compilation can be checked separately without an
ELF linker:

```sh
python3 kernel/experiments/sptm31ab-host/run.py \
  --output build/31ab-host-objects --cc clang \
  --target aarch64-none-elf --compile-only
```

Compile-only results explicitly omit linking, payload and relocation-free claims.
The runner needs only existing compilers and Python's standard library, requires
a fresh result directory, pins all nine source files and refuses source changes
during a run. Actual instruction execution under standard ARM emulation can test
capture and fatal-vector behavior. It cannot validate Apple monitor semantics,
firmware acceptance, native EL/routing, memory ownership or physical CPU startup.

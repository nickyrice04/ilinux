# CPU1 early-entry audit for a possible 31E

**Offline candidate only. Native deployment remains HOLD.** Nothing in this
directory accesses target hardware or changes the installed boot image. The
input is the project's compiled **public m1n1** image, not a macOS binary.

## What attempt 31D establishes

The recorded CPU1 request produced 171 sequential samples with an untouched
reset record and no arrival flag. This establishes that the observer did not
see `smp_secondary_entry` publish its identity. It does **not** establish that
CPU1 executed no instructions: reset assembly, UART output, CPU setup, formatted
output and exception setup all precede that publication.

No concrete missing PMGR write or wrong CPU1 topology selection was established
by this audit. CPU1 is cluster 0/core 1, so the known distinction between four-bit
and six-bit cluster bitmap packing does not change its start bit.

## Verified defect in the old observer

Public source assigns stack before MPIDR in `smp_secondary_entry`. The exact
boot021 binary stores **MPIDR first**, then stack, then executes `DSB SY`:

| Image offset | Operation |
| --- | --- |
| `0x30da0` | Store CPU1 MPIDR into its reset record |
| `0x30da8` | Store the compiled dedicated stack top |
| `0x30dac` | `DSB SY` |

The 31D classifier rejects the valid intermediate `(0x40001, 0)` tuple. This
did not cause the reported 31D timeout, because all its samples were fresh. It
would become a false refusal as soon as a sample caught the actual publication.

`observe.reset_stage()` accepts both partial orders and still requires complete
matching reset and spin identities for a nonzero arrival flag. The caller must
also validate the expected phase-specific flag count. For a coherent arrival
observation, read the flag **before** the identities, or bracket the identity
reads and retry a changed flag. Reading identity first and flag last can produce
a torn tuple while the core is successfully arriving; that is not corruption.

## Earlier execution evidence without modifying instructions

Reset entry loads `_reset_stack`, sets SP, then calls `_cpu_reset_c`. Its first
instruction stores the frame pointer and return address to `[SP-32]`. A known
return address at **actual entry SP minus 24** is therefore useful evidence
before any UART or CPU setup happens. Other compiled call frames offer more
specific positive evidence. `observe.stack_markers()` emits only named boolean
matches, not arbitrary RAM contents.

| Offset from actual entry SP | Image-relative return address | Frame evidence |
| --- | --- | --- |
| `-24` | `0x974` / `0x97c` | Non-EL3 / EL3 reset-C entry |
| `-56` | `0x32924` / `0x32934` | Secondary / primary UART path |
| `-72` | `0x32958` | `init_cpu` |
| `-696` | `0x32944`, `0x32954`, `0x3296c` | Reset-C formatted output |
| `-744` | `0x15024`, `0x15064` | CPU identification formatted output |

The last two groups can overwrite each other over time. A marker is not a
current PC, a complete chronological trace, proof that a function returned, or
proof that reset completed. Missing markers cannot exclude execution.

## Candidate diagnostic stack and the remaining gate

The largest whole 16 KiB pages after live SMP-shared objects are
`[image+0x94000, image+0xa0000)`: **48 KiB**. The image has no symbol in the
padding after `0x90a28`; all padding bytes are zero. The static audit checks all
1,371 relative relocations and every ADR/ADRP encoding in the text range and
finds no reference into these candidate pages. Linker source places no other
section there. These checks do not rule out every computed address or dynamic
range access.

Public `memory.c:mmu_remap_smp_shared` maps the whole shared region as
**Device-nGnRnE** in CPU0's identity and three alternate mappings. It was
designed for communication with secondaries whose MMU is off. This suggests a
way to inspect early stack writes without adding a new alias or invalidating a
possibly dirty CPU1 cache. Do not invalidate CPU1's ordinary stack after start
to make an observation appear visible.

But a stack in Device memory is a runtime change. The exact normal startup path
has these bounds, under the conditions in `audit.json`:

- Deepest reviewed console path: **976 bytes** (`reset` 32 + `init_cpu` 48 +
  `debug_printf` 672 + console 112 + helper 48 + wrapper 32 + UART write 32).
- Formatting path: **912 bytes**, including `vsnprintf` 96 and `fmtint` 64.
- A provisional 2 KiB normal-path allowance fits easily in 48 KiB. This is a
  conditional path bound, **not a complete hardware stack bound**.

The public build uses `-mstrict-align -mgeneral-regs-only`. Formatting uses byte
accesses for strings/buffers and naturally aligned varargs/length fields; its
compiled calls are only `fmtint` and `fmtstr`, not `memcpy`. The known CPU part
`0x68` has a null part-specific init callback. Nevertheless, CPU1's incoming
MMU state is unobserved. With its MMU on, the console can take a different path
through locks, arbitrary registered devices and `memcpy`. Exception recursion
and that alternate path are not bounded by this audit. No complete dynamic
alignment proof has been produced for a Device-memory stack.

**Keep live use on HOLD** until the entry/MMU and stack-access assumptions are
resolved or a reviewed earlier-entry recorder avoids executing this C path on
Device memory. The companion instruction-level reset emulator can test the
first prologue store but cannot establish the physical reset state or memory
attributes of this CPU.

If later approved, the candidate must retain these constraints:

1. Reserve/check the entire candidate range before starting CPU1. Record only
   allowlisted boolean markers and a bounded canary footprint.
2. Keep actual entry SP at `image+0xa0000` separate from the **compiled reset
   record top `image+0x178000`**. `smp_secondary_entry` records its usual stack
   top but does not switch SP to it.
3. No deep WFI, reset re-entry, arbitrary dispatch or Linux continuation while
   on the diagnostic stack. Any timer/payload extension needs its own ABI,
   memory-access and stack review.
4. No cleanup cache invalidation while CPU1 might still be running. End after
   one bounded observation, as prescribed by the campaign controller.

## Implemented offline alternative: a recorder before stack setup

`recorder.S` is original project assembly that avoids the Device-memory C-stack
problem. `build_recorder.py` produces an **offline patch proposal**, not a live
patcher, and never changes the input image. The ordinary CPU1 stack remains
`image+0x178000`. No firmware, boot-volume, security-policy or RVBAR write is
part of this design.

The pinned image has zero padding at `0xa00..0xc00`, after `.init` ends at
`0x9ec`. It shares the first 4 KiB page with `cpu_reset` at `0x8fc`, so this
design does not introduce a new executable page into the early path. The
builder verifies zero padding, no allocated symbol, no relative relocation,
no direct branch/literal/ADR reference, and no adjacent ADRP/ADD reference into
the proposed code or record ranges. Computed-reference exclusion still needs
source review; zero bytes alone are not an allocation proof.

The proposed hook changes the one `MOV W0,'O'` at `0x8fc` into a direct branch
to the recorder. Its **204 bytes** fit within the verified padding. It uses
only `x0`, `x8` and NZCV; it never uses SP, changes LR, calls C or accesses MMIO.
Those registers are dead at this point in the original sequence. The original
`MOV` is replayed, then a direct branch resumes the unchanged `BL debug_putc`
at `0x900`. In this image `debug_putc` is a single `RET`; the original
`MRS CurrentEL` and `CMP` at `0x904/0x908` redefine `x8` and flags before any
condition consumes them. The branch distances are only hundreds of bytes,
well within the architectural direct-branch range. The original locked RVBAR
continues to point to the same vector entry.

The recorder filters for CPU1's low-24-bit MPIDR `0x40001`, then writes four
aligned words in existing shared RAM at `0x90a40..0x90a80`:

| Word offset | Meaning |
| --- | --- |
| `+0` | Phase: 1 identity stored; 2 before SCTLR read; 3 sample complete; 255 unsupported EL |
| `+8` | `CurrentEL` |
| `+16` | MPIDR low 24 bits |
| `+24` | SCTLR for the observed EL; meaningful only after phase 3 |

EL1/EL2/EL3 paths read their corresponding SCTLR; an unsupported EL does not
attempt a higher-privilege register read. A fault at a selected SCTLR read can
leave phase 2, provided the earlier stores became visible. The stub reads
architectural state only and changes no control register. Every phase
publication has `DSB SY` before and after it. These barriers order the core's
writes; they **do not establish CPU1 cache coherence or an unknown incoming
translation's memory attributes**. Public reporting should emit only the
matching identity, phase, EL and decoded M/C/I booleans, not raw SCTLR/RAM.
An absent record still cannot distinguish no instruction fetch from a fault
or an invisible record store.

### Can installed boot021 support this without installation changes?

**Public source provides a plausible RAM-only route, but hardware permission
and instruction visibility have not been established.** `memory.c` makes the
identity text mapping read/execute, while its existing `REGION_RW_EL0` alias
maps the same RAM read/write. `proxy.c` exposes guarded memory writes and cache
maintenance. Thus the locked RVBAR alone does not require an installation:
it fixes the address, whereas this proposal modifies the authorized project's
RAM contents at that same address. A read/write alias is not proof that CTRR,
SPTM or another hardware protection allows the write. The design must refuse
if the already-existing permissions do not permit it; it must not loosen them.

The next implementation work is concrete:

1. Independently assemble/link `recorder.S` at VMA `0xa00` in the VM and match
   every byte against the Python builder. Test original and instrumented paths
   to the original continuation for CPU1 and other MPIDRs, EL1/EL2/EL3,
   unsupported EL, and a fault on each new read/store. Prove SP/LR and all live
   registers match, apart from the intentionally recorded memory.
2. Review the writable alias's effective page permissions and any hardware
   protection using existing read-only evidence. Preserve the installed boot
   object. A guarded write acknowledgement is insufficient: any later approved
   adapter must verify readback and refuse unexpected exceptions or bytes.
3. Review code publication on this exact chip: publish the complete recorder
   before installing its single-word hook; clean data through the writing
   alias to the required visibility point; order it; invalidate the relevant
   instruction-fetch view; complete the required barriers before CPU1 starts.
   m1n1's C cache-range helpers contain cache operations without implicit
   DSB/ISB, but `proxy.c`'s common request-dispatch epilogue supplies **DSB SY
   and ISB**. The frozen controllers check that wrapper; no missing-barrier
   defect in their helper publication is established here. Review and pin the
   complete RPC sequence, aliases and wrapper, rather than judging a C helper
   alone or adding redundant barriers without a reason. CPU0 readback cannot
   prove CPU1 sees new instructions, particularly with unknown incoming cache
   state. Do not invalidate a running CPU1's data cache to force a result.
4. Extend the existing immutable preflight with the exact hook, replay path,
   padding, record initialization and relocation-aware image checks. Permit
   only two fixed code ranges and one fixed record; require fresh CPU1 state.
   No general patch address, retry-after-start, RVBAR edit or Linux continuation
   belongs in this diagnostic. Review any later timer payload separately.
5. Only after those checks pass, prepare a separate bounded live allowance and
   review it. Until then the generated proposal is `native_deployment_ready:
   false`; it offers no transport or automatic native execution.

If the existing RAM mapping or hardware protection prevents modification of
the loaded entry page, there is **no established RAM-only interception route**
before C while RVBAR remains locked. Merely chainloading a different image
does not redirect that CPU1 reset address. The fallback is a reviewed
instrumented lab m1n1 boot object using the existing lab security policy, with
separate authorization for replacing that boot object; original macOS remains
untouched. No protection bypass is proposed.

## Reproduction

Pinned m1n1 public source: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
Image and symbol SHA-256 values are checked in `audit.py` and `audit.json`.

```sh
python3 -I kernel/experiments/smp31e-entry/test_observe.py
python3 -I kernel/experiments/smp31e-entry/test_audit.py
python3 -I kernel/experiments/smp31e-entry/test_recorder.py \
  --image build/native-boot042/verified/m1n1.bin \
  --symbols virtualization/jobs/021-native-boot-package/out/m1n1-symbols.txt
python3 -I kernel/experiments/smp31e-entry/audit.py \
  --image build/native-boot042/verified/m1n1.bin \
  --symbols virtualization/jobs/021-native-boot-package/out/m1n1-symbols.txt
python3 -I kernel/experiments/smp31e-entry/build_recorder.py \
  --image build/native-boot042/verified/m1n1.bin \
  --symbols virtualization/jobs/021-native-boot-package/out/m1n1-symbols.txt
```

Generated patch bytes and their plan go only into this directory's ignored
`out/`; no full modified image is generated. Every output leaf is checked before
writing: existing symlinks and nonregular files refuse the whole write. Fresh
mode-0600 temporary files are atomically renamed, so an existing hardlink never
receives an in-place write. Failed writes clean their temporary files and use
fixed error labels. Guest independent compilation:

```sh
aarch64-linux-gnu-as -march=armv8.2-a recorder.S -o recorder.o
aarch64-linux-gnu-ld -Ttext=0xa00 --entry=smp31e_recorder --defsym=smp31e_record=0x90a40 --defsym=smp31e_resume=0x900 recorder.o -o recorder.elf
aarch64-linux-gnu-objcopy -O binary --only-section=.text recorder.elf recorder-gnu.bin
```

Host tests execute original standard-library Python parsers only. They do not
execute m1n1 instructions, imported upstream tools, Apple binaries, VM jobs or
hardware operations. Native checks: **NOT RUN**.

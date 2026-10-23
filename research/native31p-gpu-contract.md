# 31P GPU contract: preserve complete descriptors before enabling hardware

Date: 2026-10-22. Scope: original offline software and retained sanitized ADT.
No Apple binary, disassembly or decompiler output was used to write this codec.
No hardware operation, new native attempt, or macOS change occurred in this work.

## A concrete correction to the existing GPU research

**Confirmed from retained metadata and public format:** the older
[`gpu-g17` scope table](../kernel/experiments/gpu-g17/README.md) displays only the
low 32-bit cell of each firmware segment's first address. The actual descriptor
contains a 64-bit field. All four first-address high words are `0x100`; dropping
them changes the address. The older document is retained as historical evidence;
this note supplies the correction.

The sanitized collector decodes these cells little-endian in
`hardware/scripts/adt_extract.py`, `as_u32` and `decode`. Public m1n1 at
[`57a9339ffd1876e78297b17d34dece8cff8fa1ba`, `src/adt.h`](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/adt.h)
declares the descriptor's shape as three 64-bit fields (`phys`, `iova`, `remap`)
and two 32-bit fields (`size`, `unk`). This is a 32-byte descriptor, eight
little-endian 32-bit cells. Public `src/kboot.c`, `dt_reserve_asc_firmware`,
consumes all these address fields and rounds unaligned sizes for reservation.
That generic consumer is useful format evidence, not proof that its reservation
policy is valid for this T6050 GPU boot state.

| Role / segment | Full `descriptor_phys` | IOVA | Size | Last word |
|---|---|---|---|---|
| GFX / `__TEXT` | `0x10001000000` | `0xfffffc0000000000` | `0x4c000` | `1` |
| GFX / `__DATA` | `0x100026f0000` | `0xfffffc000004c000` | `0x130000` | `0` |
| GFX1 / `__TEXT` | `0x1000104c000` | `0xfffffc0000000000` | `0x54000` | `1` |
| GFX1 / `__DATA` | `0x10002820000` | `0xfffffc0000054000` | `0x130000` | `0` |

The retained remap field equals `descriptor_phys` in each of these four records.
The parent ASC and its nub contain identical descriptor bytes for each role.
These are sanitized descriptor facts, not copied firmware contents.

**Unknown:** whether that named `phys` field is directly usable as a CPU physical
address in this boot state, needs address-domain translation, or belongs to a
firmware-managed address space. The name and equality with remap are insufficient
to decide. Consequently no CPU DRAM reservation or GPU PTE is generated from it.
Neither the discarded high words nor a guessed translation may be restored by
merely aliasing an older GPU generation.

## Engineering decisions and original implementation

The original [GPU31P tooling](../kernel/experiments/gpu31p/README.md) makes this
format usable without silently guessing the missing hardware behavior:

| Evidence or uncertainty | Implemented decision |
|---|---|
| First address requires 41 bits in all four retained records | Python and C preserve the complete 64-bit field; synthetic high-word golden vectors catch truncation and byte-order mistakes |
| Last 32-bit word's meaning is unknown | Preserve it exactly; do not turn it into permission or role flags |
| GFX/GFX1 overlap in virtual address ranges | Validate spans within each role; report the three cross-role overlaps rather than treating both roles as one address space |
| Parent/nub duplicated descriptors | Require byte-equivalent records before accepting the contract |
| Shared mapper and AIC references | Resolve the nine contract nodes and require coherent scalar phandle relationships; handle renumbering is permitted |
| `sgx` MMIO is an aggregate containing narrower windows | Validate exact observed resources, without a false global no-overlap rule |
| `gptbat-ready`, `ttbat-phys-addr-base`, and address-space mode values were sanitized away | Record property presence only; UAT layout/readiness remains unknown |
| Source format and a profile are different claims | Generic codec accepts positive bounded byte spans; separate observed-machine profile requires 16 KiB alignment |
| Malformed external metadata could reach future Linux code | Bounded lengths/counts, strict integer types, checked additions, transactional C outputs, fixed CLI refusal labels, and fault tests |

The C library is a small portable building block for a future original Linux
handoff/driver path. It deliberately does not write DT reservations, UAT entries,
RTKit messages or GPU queues: the necessary address translation, endpoint and
message semantics are not yet established. Software tests of this library are
useful now because future hardware work must not lose address bits or silently
merge the two coprocessor roles.

## Actual metadata versus synthetic test evidence

The input is `hardware/adt/adt-sanitized.json`, SHA-256
`6f143434d2f05310067559f8fa3836ae564dd9934ebc5912660f2a9f5a8a73af`.
The [actual validation metadata](../kernel/experiments/gpu31p/adt-validation.json)
reports nine contract nodes, two roles, two 32-byte records per role, matching
parent/nub descriptors, and the address-domain/UAT/firmware-ABI unknowns.

The encoded GFX descriptor pair hashes to
`d7619805c5c69587fbe839da3923b2f200d60f63c78aac35aa78eb85de25fdd8`;
GFX1 hashes to
`e39089b7f7c41db977595bf50089e0c7ce735c647cb8622dfa8663fcbff791ad`.
These identify sanitized metadata bytes, not firmware images.

**Host tests observed:** 38 Python test methods pass with Python 3.9.6. Original
C compiled using Apple clang 21.0.0 with C11, `-Wall -Wextra -Werror -pedantic -O2`;
all 12 C test groups pass. Golden vectors are independently written synthetic
bytes, including nonzero high address words and a nontrivial opaque word. The
suites include partial records, excessive counts, wrong integer types, overflow
in each address domain, overlap versus adjacency, alignment policy, null inputs,
unaligned byte buffers, insufficient output capacity and unchanged outputs on
failure. ADT tests include role swaps, inconsistent mapper/nub/resource identity,
duplicate contract nodes, malformed JSON, special files and accidental input
disclosure. Root's VM076 integration records Linux compilation/sanitizer results
separately; this note does not claim those results before they exist.

## What will enable a real GPU test

This is one prerequisite, not a completed driver. The next information needed is
the ownership and translation of these descriptor addresses during the existing
raw boot; the exact G17C firmware ABI and required GFX/GFX1 startup relationship;
the UAT/GPTBAT table format and cache/coherence contract; then one queue submission
and bounded completion protocol. The current source build foundation must also
identify actual G17C ISA/compiler coverage, rather than treating an M4 or base-M5
success as this machine's support.

REA should next answer those bounded behavior questions using matching binaries
and independent instruction checks, with all Apple bytes/pseudocode retained only
under ignored `build/`. A first eventual hardware experiment needs a checked
compute result or pixel readback and a bounded failure/return path. A profile
pass here supplies neither that test nor permission to run it. Native GPU
enablement remains **HOLD / NOT RUN**; acceleration, responsiveness, all-core
execution and macOS performance/energy parity remain unverified.

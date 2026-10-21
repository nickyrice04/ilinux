# 31E CPU0 publication review

2026-10-21. Independent offline review of the retained public boot021 image,
its symbol table, original recorder, and the clean public m1n1 source/client
at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. No target command, macOS change,
Apple binary extraction, or boot-object modification was performed by this
review. It does not establish physical CPU1 entry or instruction visibility.

## Concrete allowed spans

All offsets below are relative to the already verified installed image base.

| Purpose | Byte span | Permitted operation |
| --- | --- | --- |
| Recorder | `[0xa00, 0xacc)` | Publish exactly the reviewed 204 bytes |
| Entry branch | `[0x8fc, 0x900)` | One aligned original-MOV to reviewed-B replacement, last |
| Shared record | `[0x90a40, 0x90a80)` | Require fresh zeroes; initialize/observe only this reserved block |
| Reserved code padding | `[0xa00, 0xc00)` | Verify remaining zeroes; do not expand the write allowance |

The hook and recorder are in the same first 4 KiB, hence the same page for
every supported architectural granule. The entire image base is checked for
16 KiB alignment by existing preflight. The shared record is in the existing
shared section, which the source maps as Device-nGnRnE in all four views.
Its reserved tail is a canary, not permission to use arbitrary shared padding.

## Permission checks before instruction publication

**Confirmed source behavior:** `memory.c:mmu_add_default_mappings` maps the
identity text read/execute and creates a separate read/write RAM view at
`physical | 0xa0000000000`. `mmu_add_mapping` selects **Outer Shareable (2)**,
not Inner Shareable (3). The latter is a Linux measurement and must not be
reused as this bootloader's expected attribute. Normal RAM uses MAIR `0xff`;
shared RAM uses Device-nGnRnE `0x00`. Runtime mappings must still be checked.

`permissions.py` provides sixteen fixed AT checks over the hook, both ends of
the recorder, and both ends of the shared record. Each successful translation
must name the expected physical page and memory type; Normal mappings must
have the expected shareability. An identity write must produce a permission
fault, not an address-size, missing-translation or access-flag fault. Reads and
writes through the existing writable alias must succeed as translations.

The original `permission_helper.S` appends 160 bytes after the existing
192-byte helper. It preserves/restores PAR_EL1 and changes no translation or
permission register. Its fixed entry offsets are:

| Helper offset | Operation |
| --- | --- |
| 192 / 224 | EL1 read/write AT using S1E1 |
| 256 / 288 | EL2 read/write AT using S1E2 |
| 320 | Read HCR_EL2 only when CurrentEL is EL2; otherwise return zero |

Do not assume the proxy is always EL1. Pinned `exception_initialize` explicitly
supports EL2 and configures a VHE host with E2H and TGE set. Choose the AT regime
from the checked CurrentEL; EL2 additionally requires the reviewed HCR regime.
The gate requires E2H=TGE=1 and VM=0, not an exact value for unrelated HCR
fields that can read as zero when their architectural feature is absent.
Record only the named regime result, not the raw HCR value.
Do not read HCR or issue S1E2 from EL1. The assembly issues ISB before reading
the AT result and after restoring PAR. It uses only caller-clobbered registers
and leaves SP/LR unchanged. These helpers are pre-start only.

**Limit:** AT tests the selected architectural translation/access regime. It
does not promise that an Apple physical protection permits a subsequent
store, nor that CPU1 can execute the bytes. The actual bounded publication must
use guarded stores with immediate exception checks and exact readback through
both views. A fault or mismatch is a stop; do not alter protection registers,
tables, boot policy or the installed boot object to make the write succeed.
An acknowledgment alone is insufficient.

## Publication order and exception accounting

1. Complete immutable-image, CPU topology, fresh-secondary, direct-USB,
   permission and zero-padding checks before patching. Keep the ordinary CPU1
   C stack; the Device-memory replacement-stack proposal remains held.
2. Publish the recorder completely through the existing writable alias using
   fixed aligned stores. Read the adjacent exception-count/guard pair through
   the guard-free helper after **each** operation. Compare exact alias and
   identity bytes. Never use REQ_MEMWRITE to patch a running image: its probe
   changes the endpoints to zero, and its receive path is not a per-word guard.
3. Clean the written alias to PoC with DC CVAC, then invalidate the identity
   instruction-fetch view with IC IVAU. Use conservative aligned ranges
   `[0xa00, 0xb00)` and `[0x8c0, 0x900)` for recorder and hook, respectively.
   These spans are maintenance ranges, not expanded byte-write allowances.
4. Install the single aligned hook only after recorder publication succeeds.
   Clean/invalidate it with the same ordering, then read back the branch and
   recorder. Compare unchanged surrounding bytes as well as the patched bytes.
   Record intent before each operation; a lost acknowledgment is uncertain
   execution, never grounds to resend, roll back or continue starting CPU1.
5. Only then make the existing bounded start transition. No code write, cache
   maintenance, general memory transfer, guard mutation or exception-counter
   clear belongs after that transition. Observation uses fixed guard-free
   reads; unexpected exception/guard state ends the attempt.

**Confirmed source behavior:** cache range functions advance by 64 bytes and
do not themselves append barriers. Each normal proxy dispatch appends
**DSB SY; ISB**, including cache requests and guarded writes. The complete
write/clean/invalidate/RPC sequence therefore matters; reviewing the cache
function alone would falsely identify a missing barrier. The existing immutable
text preflight covers those proxy and cache routines. Do not infer that CPU0's
ISB or instruction invalidation forces an offline CPU1's unknown incoming
state; that uncertainty is part of the diagnostic result, not a proven fix.

`P_GET_EXC_COUNT` clears the counter. REQ_MEMREAD also clears it and temporarily
changes the global guard; P_READ/P_WRITE temporarily change that guard. The
existing original helper's aligned 64-bit count/guard read is therefore the
right diagnostic once it is published, and the only allowed diagnostic after
CPU1 might run. Reject nonzero count **or** guard. Check before a memory
transfer could clear prior evidence and immediately after any guarded store.

## Validation and evidence boundaries

The new pure decoder has **11 passing test methods**, covering all named
ranges, malformed values, wrong pages, attributes, shareability, fault types,
regime mismatches and every one-byte helper mutation. Apple LLVM independently
assembled the original 160-byte helper; its bytes match the recorded words,
SHA-256 `44dfcab7a9c4aa49f7e18b4e635061f2c3f5da2bf1b928862785e8bd485ca0db`.
The controller's VM job must also independently assemble and compare this new
tail, test exception and transport failures at every publication boundary, and
check that start is impossible after an incomplete publication.

Architectural reference: Arm's [Memory management guide, section 9](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/LearnTheArchitecture-MemoryManagement-101811_0100_00_en.pdf?revision=1fdc3375-d81c-4457-b786-04fb98557de0)
describes selecting translation/access regimes with AT and reporting either
the translated address/attributes or a fault in PAR. Public source anchors:
`src/memory.c` (`mmu_add_mapping`, `mmu_add_default_mappings`,
`mmu_remap_smp_shared`, cache-range helpers), `src/exception.c`
(`exception_initialize`, guard/fault handling), `src/proxy.c`
(`proxy_process`), `src/uartproxy.c` (memory-transfer cases), and
`src/memory.h`/`src/arm_cpu_regs.h` (mapping/PAR definitions), all at the pin
above. This is original behavioral analysis of public bootloader code; no
Apple pseudocode is included.

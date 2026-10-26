# 31AF immutable original resident-cold observer

This assembly-only nonreturning payload never uses SP, calls C, initializes a
monitor helper, invokes an SPTM service, or writes its image. Its only memory
store instruction is a 32-bit pixel store into a fully checked framebuffer plan.
The on-disk reservation starts zero. The synthetic fixture fills it with known
sentinels and maps the complete image read-only, checking it after execution.
No Apple binary, decompiler output or SDK header is a build input.

| Payload offsets | Purpose | ELF protection |
|---|---|---|
| `0..0x4000` | Reserved header canvas | no load |
| `0x4000..0x58000` | Reserved SPTM comparator extent | read |
| `0x58000..0x5c000` | Separate unused normal-text self branch | read/execute |
| `0x5c000..0x60000` | Entry, vectors and every reachable helper | read/execute |

Entry is `0x5c000`, vectors `0x5c800`, body `0x5d000`. The public comparator's
`0x54000` reserved extent is a format comparator, not a T6050 sizing measurement.
The parent-owned Mach-O wrapper controls its segment names and protections.

The finite profile is resident-cold x0=0, x1 ARM64 revision/version2 BootArgs,
x2 the qualified monitor record, EL2, MMU on, little-endian and HCR E2H/TGE00 or11.
Incoming DAIF is captured in x18 and then masked; its original mask does not
prevent painting. The original qualified D128/TCRX/TCR2 and PS/IPS checks retain
the 64-bit PAR decoder. Unsupported profiles park without dereferencing pointers.
No MMU, page-table, memory-attribute, trap-control or guarded-state rewrite is used.

Before any source load, read AT validates the entire covered interval with
NormalNC0x44 or NormalWB0xff attributes. The88-byte BootArgs prefix,24-byte helper
at x2+416, helper version10, u32 count1..64 and count*24-byte table are bounded.
Boot/helper/table pointers require their declared8-byte alignment; count requires4.
Every16KiB range endpoint is checked for overflow; physical and virtual overlap
refuse. Source4KiB physical pages and every payload page must not overlap the
complete declared framebuffer. The full payload must be readable NC/WB.
Mappings and source contents must remain stable between checks and accesses;
repeated AT does not make the source snapshot atomic or authenticate its producer.

A centered128x64 rectangle writes exactly8192 four-byte pixels,32768 bytes.
It requires contiguous PAPT translation across the bounding span, then checks
write AT, exact untruncated PA and NC/WB attributes for every intersecting pixel
page before the first store. Width/height/stride and the whole framebuffer's
arithmetic are checked first. The4-pixel border surrounds8x8 alternating cells;
foreground is white (`0x00ffffff` depth32, `0x3fffffff` depth30), background black.
Rotation, scale, alpha and actual scanout are not inferred from RAM contents.

If any target page is WB, CTR_EL0 supplies a16..2048-byte cache-line size. Every
rounded clean interval is separately checked inside the framebuffer, translated
through PAPT to the same VA, and write-AT checked before painting. After stores,
DC CVAC covers each row's lines and DSB SY completes the sequence. Repeated lines
may be cleaned repeatedly; a maximum2112 clean operations follows from64 rows,
512 bytes/row and the minimum16-byte line. NC-only rows need DSB SY. Cleaning can
include checked adjacent framebuffer bytes but performs no extra pixel stores.
PAR's low64 bits are restored around every AT. PoC completion is not a panel test.

The native result remains ambiguous if no marker is seen: non-entry, unsupported
profile, source refusal, translation/protection trap and invisible display can
still look alike. A visible marker establishes entry through the framebuffer
store/display path, without requiring a writable image or stack. It establishes
neither monitor readiness nor service15, Linux, SMP, GPU or performance.
Synchronous EL2 vectors are stackless and retain ESR/ELR/FAR in registers before
parking; exceptions routed elsewhere are outside this diagnostic.

At terminal park x27=7 means all stores/maintenance completed and x28=0; x26=8192
counts pixels, x25 counts clean operations. x24 retains depth in bits7:0, WB in
bit8 and line bytes in31:16. x18 retains incoming DAIF. On refusal x27=0x80 and
x28 is an IF31 status; x25/x26 still hold working values. Fatal EL2 x27=0xdead,
x28=ESR_EL2, x29=ELR_EL2, x16=FAR_EL2, x17=vector slot. Only the emulator has a
register/RAM observer; those registers are not independently readable natively.

`run.py` compiles one original object, links at zero and0x40400000 with GNU ld,
requires byte equality and audits every function/vector instruction. Its finite
instruction allowlist rejects SP operations, other stores, indirect calls,
translation-control writes, guarded/supervisor transitions, unresolved symbols,
relocations and unaudited nonzero boot bytes. It is not a formal proof of the
address-validation algorithm. The separate complete-payload harness is in
`../immutable31af-test/`; native acceptance/execution remain NOT RUN.

```
python3 -I kernel/experiments/immutable31af/run.py --output build/immutable31af-host --cc clang --target aarch64-none-elf --compile-only
python3 -I kernel/experiments/immutable31af/run.py --output build/immutable31af-link --cc cc --ld ld
```

AT can have architectural access-flag/dirty-table effects under the incoming
translation controls. Zero explicit image stores is not a claim that every AT
operation is universally free of those effects; the synthetic tables have their
access state set and are checked unchanged. No mapping/control rewrite is used.

# 31AE original data-first visible-entry payload

This links the unchanged, hash-pinned original `visible31ac` entry, probes,
runtime and C bridge with the unchanged `observer31ab` implementation. Only
this experiment's GNU linker script changes their placement. It does not copy,
move or patch encoded instructions. No Apple binary or decompiler output is
an input. Native execution and installer acceptance remain NOT RUN.

| Payload offsets | Purpose | Protection |
|---|---|---|
| `0..0x4000` | Reserved header canvas | read |
| `0x4000..0x10000` | Owned record and stack | read/write |
| `0x10000..0x14000` | Normal executable late park | read/execute |
| `0x14000..0x24000` | Boot entry, vectors and body | read/execute |

`native_record=0x4000`, `native_stack_bottom=0x8000` and
`native_stack_top=0x10000`. The entry, vector and body offsets remain
`0x14000`, `0x14800` and `0x16000`. All offsets are payload-relative.
`run.py` verifies all seven reused source SHA-256 pins before and after building,
records its own four source bindings, compiles five freestanding objects, links
at zero and `0x40400000`, audits both ELF images and requires byte-equal payloads.
GNU AArch64 ld is the canonical linker; host compilation alone is not link proof.

```
python3 -I kernel/experiments/visible31ae/run.py --output build/visible31ae-host --cc clang --target aarch64-none-elf --compile-only
python3 -I kernel/experiments/visible31ae/run.py --output build/visible31ae-link --cc cc --ld ld
```

`audit.py` checks exact ELF/load/section geometry, record/stack symbols,
relocations, undefined symbols, vector slots, parked branches, original AT
helpers and the existing system-operation/branch allowlist. This is not a
complete proof of C behavior. The complete synthetic runtime suite lives in
`../visible31ae-test/`; no native controller or monitor call is added.

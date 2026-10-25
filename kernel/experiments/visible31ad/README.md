# 31AD ordered visible-entry diagnostic

This original derived build relinks the unchanged, hash-pinned 31AC entry,
translation helpers, runtime and C bridge with the unchanged 31AB observer. The
only payload change is linked placement. No encoded code is moved after linking,
and the linker resolves references to `native_image_base` for the new positions.
The C capacities, record ABI, marker behavior and `0x24000` payload size remain
those of 31AC. See `../visible31ac/README.md` for that behavior and its limits.
Native installer acceptance, execution and display visibility are not established.

The new layout puts the unused normal executable self-branch at `0x4000..0x8000`,
owned data at `0x8000..0x14000`, and every live instruction in boot-executable
`0x14000..0x24000`. The 512-byte record begins at `0x8000`, the 32 KiB stack spans
`0xc000..0x14000`, entry is at `0x14000`, vectors at `0x14800`, fatal handler at
`0x15000` and the remaining code begins at `0x16000`. The image base remains zero
in the canonical link. Normal executable text now precedes boot-executable text,
as required by the applicable split-protection range ordering. This addresses
the identified ordering defect without proving complete firmware acceptance.

`run.py` compiles five freestanding objects directly from the pinned original
sources, links at zero and `0x40400000`, audits both ELFs and requires byte-equal
payloads. The derived MIT audit verifies the ordered section/load geometry,
zero storage and padding, symbols, vector instructions, park branches, AT helpers,
function/branch containment and selected system instruction classes. It refuses
undefined symbols, retained relocations and dynamic linkage. It does not prove
all generated C behavior. Every source is rehashed after building.

Root runs these commands inside the isolated ARM64 Linux VM with existing GNU
tools; this builder never executes the payload:

```sh
python3 -I kernel/experiments/visible31ad/run.py \
  --output build/31ad-linked --cc cc --ld ld
```

A host compile-only check uses `--cc clang --target aarch64-none-elf
--compile-only` and a fresh output directory. The complete QEMU experiment is
in `../visible31ad-test/`. Packaging and installer-contract inspection are separate
work; no install, boot, security change, CPU start or monitor call is performed
by this source tree. The old 31AC files stay frozen and are bound by SHA-256.

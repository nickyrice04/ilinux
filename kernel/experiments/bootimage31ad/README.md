# 31AD ordered nested-fileset experiment

`ordered.py` packages the newly relinked original `../visible31ad/` payload
inside a containing Mach-O fileset. Normal executable text precedes
boot-executable text in both headers and in the file. The applicable
split-protection range requires `__TEXT_EXEC.fileoff <= __TEXT_BOOT_EXEC.fileoff`
before unsigned subtraction. The old 31AC order violates that invariant;
wrapping the old payload in a nested fileset alone does not fix it.
**No installer or firmware acceptance is claimed, and this directory does not
authorize a boot.**

The generator and independent validator use the public Mach-O format, original
payload geometry and the qualified range-order finding. The implementer did not
open Apple disassembly, decompiler output, Apple program bytes or private REA
material. The public format is defined in
[Apple's pinned `loader.h`](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/EXTERNAL_HEADERS/mach-o/loader.h).
The `com.apple.kernel` entry identifier is a format string; the image contains
the project's original payload.

## Geometry and limits

The outer `MH_FILESET` has one `LC_FILESET_ENTRY` pointing at an original inner
`MH_EXECUTE` header. A new 16 KiB page precedes the already relinked 31AD payload.
The inner virtual base, capture/stack addresses, entry, vector and code offsets
remain those of that linked payload. All its bytes after the reserved first
header page remain equal. The linker resolves references for the new placement;
the packager never moves encoded code within the payload. The wrapper adds no
executable instructions, pointer fixups, signing operation or monitor request.

| Region | File offset | VA relative to inner base | Bytes |
|---|---:|---:|---:|
| Outer fileset header | `0` | `-0x4000` | `0x4000` |
| Inner image header | `0x4000` | `0` | `0x4000` |
| Original normal executable text | `0x8000` | `0x4000` | `0x4000` |
| Original capture/stack | `0xc000` | `0x8000` | `0xc000` |
| Original boot code | `0x18000` | `0x14000` | `0x10000` |
| Original-format metadata | `0x28000` | `0x24000` | `0x4000` |
| Link-edit reservation | `0x2c000` | `0x28000` | `0x4000` |

Total file length is 196608 bytes. The outer `__TEXT` mapping covers both header
pages; the inner mapping covers its own header page. Each header's segment list
has no internal overlaps. Shared region descriptions are intentional. Every
segment and section file offset, including those in the inner header, is
collection-absolute. Both thread commands name the same original entry.

Entry is inner base plus `0x14000`, vectors plus `0x14800`, and the record plus
`0x8000`. Normal executable bytes are excluded from the zeroed capture/stack
check. Metadata begins exactly after the original payload ends.

The separate validator imports no generator helpers. It checks command extents,
unique entry/name, mapping consistency, permissions, file/VA bounds, metadata
and original-payload equality. Both parsed headers must pass the checked
split-protection ordering. It accepts only this experiment's finite profile;
a PASS does not emulate or replace the Recovery installer. The separate
`validate_ordered.range_check(data)` API also accepts finite flat `MH_EXECUTE`
and flat `MH_FILESET` profiles, so an old image can fail directly at the ordering
guard without depending on the new nested-header requirement.

## Offline use

```sh
python3 -I kernel/experiments/bootimage31ad/test_ordered.py
python3 -I kernel/experiments/bootimage31ad/ordered.py \
  --payload build/31ad-linked/payload.bin --output build/31ad-ordered
python3 -I kernel/experiments/bootimage31ad/validate_ordered.py \
  build/31ad-ordered/ilinux-31ad-ordered.macho \
  --payload build/31ad-linked/payload.bin
```

The CLI output directory must be new and beneath ignored repository `build/`.
The 32 test methods cover deliberate entry, header, segment, section, thread,
metadata and payload corruptions; both flat root types and the prior unordered
nested control are negative range-order regressions. CLI tests package only
synthetic markers, refuse malformed inputs and existing outputs, and remove
their temporary files. Tests do not execute a payload. Native preparation must
additionally bind the actual linked payload, inspect the complete image and
qualify the installer contract; those actions are parent-owned.

## Historical unordered nested control

`image.py`, `validate.py` and `test_image.py` retain the earlier nested-only
control unchanged. Their old structural PASS does not check the now-qualified
split-protection ordering, and that image is not the ordered candidate. The new
suite first confirms the old control's limited parser PASS, then requires the
independent ordering guard to reject it. Preserve those files as control history.

# 31AF immutable-entry nested image

This original offline serializer wraps the newly linked 31AF immutable probe.
It replaces only its zero header page and prepends the outer header page; it
does not relocate encoded instructions, reuse the consumed 31AE instruction
body, or allocate an observer record/stack. The payload's own instruction audit
and runtime harness establish its access behavior separately from this format
validator. No Apple binary or decompiler artifact is an input.

| Role | Inner-base VA delta | Collection file offset | Bytes | Declared protection |
|---|---:|---:|---:|---|
| Outer `__TEXT` | `-0x4000` | `0` | `0x8000` | R |
| Inner `__TEXT` | `0` | `0x4000` | `0x4000` | R |
| `__DATA_SPTM` reservation | `0x4000` | `0x8000` | `0x54000` | RW |
| `__TEXT_EXEC` | `0x58000` | `0x5c000` | `0x4000` | RX |
| `__TEXT_BOOT_EXEC` | `0x5c000` | `0x60000` | `0x4000` | RX |
| `__PRELINK_INFO` | `0x60000` | `0x64000` | `0x4000` | R |
| `__LINKEDIT` | `0x64000` | `0x68000` | `0x4000` | R |

The default inner base remains `0xfffffe0007004000`; entry is inner base plus
`0x5c000`. Payload size is `0x60000`; complete image size is `0x6c000`
(442368 bytes). All inner file/section offsets are collection absolute. Every
byte after the replaced payload header must equal the new linked payload.
`_PrelinkKCID` retains the existing original convention: the first sixteen
SHA-256 bytes of the complete zero-header payload. The independent validator
reconstructs and hashes that payload even without a supplied payload argument.

The reservation is zero initialized on disk and is **not observer-owned data**.
Its declared RW protections are retained from the previously accepted image
profile; they do not establish OS ownership or actual native write permission.
An emulator may map/populate it read-only to test that the immutable probe never
writes it. No ordinary DATA/BOOTDATA region is present in this profile.

The `0x54000` reservation is an explicit public-build comparator. Pinned XNU
`ac9718fb1af618d5ce8678d0dc6e8a58f252216f` reserves one 16 KiB SPTM/CTRR page and,
under its macOS conditional, twenty 16 KiB read-only table pages in
[`osfmk/arm/data.s`](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/osfmk/arm/data.s#L98).
This is not a proven T6050 minimum or a complete firmware loader specification.

`validate.py` independently copies and adapts the project's original strict
31AE parser; it imports no producer code. It checks both headers, the exact
segment set/order, declarations, affine file/VA mapping, complete nonoverlapping
extents, entry, canonical fileset command, metadata section start/geometry,
payload binding and all header/tail padding. Its finite arithmetic model checks
both profile values and the five guarded start differences: boot minus normal
code for profile true; selected start minus TEXT; LINKEDIT minus PRELINK;
normal code minus DATA_SPTM; and PRELINK minus boot. Profile false selects
PRELINK, while true selects DATA_SPTM. Arithmetic helper fallback cases are
tested independently; the complete image still requires all six segment roles.

The 21-method synthetic suite covers positive reconstruction, multiple bases
including the last valid uint64 base, reservation contamination, invalid inputs,
header/command/section/permission/entry/extent corruption, five arithmetic paths,
metadata corruption and hash changes. The separate five-method regression
requires the exact locally retained consumed 31AE candidate and pins the frozen
31AE validator source. It checks old-profile success, new-profile refusal and
refusal after merely padding old bytes to the new size. The old installation
and silent native observation are separate from these structural checks.

```
python3 -I kernel/experiments/bootimage31af/test_image.py
python3 -I kernel/experiments/bootimage31af/test_rejected31ae.py build/research31ae/ordered-package/ilinux-31ae-ordered.macho
python3 -I kernel/experiments/bootimage31af/image.py --payload build/visible31af-link/payload.bin --output build/visible31af-package
python3 -I kernel/experiments/bootimage31af/validate.py build/visible31af-package/ilinux-31af-immutable.macho --payload build/visible31af-link/payload.bin
```

Producer API: `image.py: package(payload: bytes, base=DEFAULT_BASE)` returns
`(image_bytes, packaging_report)`. Validator API:
`validate.py: validate(image_bytes, payload=None)` returns the independently
derived report. Packager output must be an absent directory under repository
`build/`. The candidate filename is `ilinux-31af-immutable.macho`.

A structural PASS does not invoke the installer or establish firmware handoff,
native entry/display visibility, monitor services, physical secondary execution,
Linux, GPU or performance. Native installation remains a separate reviewed
proposal with its own authorization and bounded observation/rollback sequence.

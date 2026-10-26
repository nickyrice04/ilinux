# 31AE data-first nested fileset experiment

This original offline format experiment wraps the newly **relinked** original
`../visible31ae/` payload. It places owned data before normal executable text,
then boot executable text, while retaining the 31AD nested-header and metadata
scheme. No encoded instructions are moved by the packager; only the reserved
payload header is replaced. Entry/vector/body remain payload offsets `0x14000`,
`0x14800`, `0x16000`; record is `0x4000`, stack `0x8000..0x10000`.
No Apple program bytes or decompiler output are inputs. Native acceptance is
NOT TESTED; a matching own-image profile is not installer validation.

| Role | Payload VA delta | Collection file offset | Bytes | Own protection |
|---|---:|---:|---:|---|
| Outer `__TEXT` | `-0x4000` | `0` | `0x8000` | read |
| Inner `__TEXT` | `0` | `0x4000` | `0x4000` | read |
| `__DATA_SPTM` | `0x4000` | `0x8000` | `0xc000` | read/write |
| `__TEXT_EXEC` | `0x10000` | `0x14000` | `0x4000` | read/execute |
| `__TEXT_BOOT_EXEC` | `0x14000` | `0x18000` | `0x10000` | read/execute |
| `__PRELINK_INFO` | `0x24000` | `0x28000` | `0x4000` | read |
| `__LINKEDIT` | `0x28000` | `0x2c000` | `0x4000` | read |

Both headers list data before normal text. All inner file and section offsets
are collection-absolute. Total image size stays `0x30000` (196608 bytes), payload
shift stays `0x4000`, and all bytes after the reserved payload header must equal
the supplied relinked payload. Metadata binds the reconstructed zero-header
payload even when the validator receives no separate payload argument.

`validate_ordered.py` is an independently copied original strict parser,
adapted from frozen 31AD; it imports no producer code. It retains finite Mach-O,
command, thread, section, permission, metadata, padding and nesting checks. Its
corrected split contract requires `TEXT <= DATA <= TEXT_EXEC <= BOOT_EXEC <=
PRELINK_INFO <= LINKEDIT` in **both file and virtual space**, complete bounded
extents, no overlap, and guarded start differences and end gaps at every adjacent
boundary. Start order alone cannot hide extent overflow or overlap.

It also reports an explicitly local arithmetic model for profile false and
profile true. With `T=TEXT`, `D=DATA`, `E=TEXT_EXEC`, `B=BOOT_EXEC`, `P=PRELINK_INFO`,
`L=LINKEDIT`, true reports `B-E` (or `E.size` if boot text is absent). Both modes
report selected-start minus T (P for false, D for true, or E if D is absent),
`L-P`, `E-D` when D is present, and `P-B` when B is present. Every subtraction
is guarded first. Optional-role fallback tests concern this arithmetic helper;
the complete 31AE profile still requires all six roles. These are model results,
not a claim about the active Recovery profile or Apple's acceptance decision.

The 51-method synthetic suite preserves the earlier strict-parser corruption
coverage and adds the actual data-order regression, each nested header in
isolation, file/VA order independence, all adjacent full extents, uint64 bounds,
exact false/true arithmetic, optional-role fallbacks and intrinsic payload
binding. The five-method separate exact-byte regression requires a locally
retained released 31AD image and verifies its complete SHA-256 before checking
that the frozen old validator passes and the new guards reject it. No binary
fixture is committed. The 31AD control validator itself is SHA-256 pinned.

```
python3 -I kernel/experiments/bootimage31ae/test_ordered.py
python3 -I kernel/experiments/bootimage31ae/test_rejected31ad.py build/research31ad/release-assets/ilinux-31ad-ordered.macho
python3 -I kernel/experiments/bootimage31ae/ordered.py --payload build/visible31ae-link/payload.bin --output build/visible31ae-package
python3 -I kernel/experiments/bootimage31ae/validate_ordered.py build/visible31ae-package/ilinux-31ae-ordered.macho --payload build/visible31ae-link/payload.bin
```

Build output directories must be fresh and under repository `build/` for the
packager. The payload is built/audited at two bases by `../visible31ae/run.py`;
the complete 26-case runtime suite is in `../visible31ae-test/`. Those checks do
not establish native entry, monitor readiness, Linux, SMP, GPU or performance.

# 31AO: qualify the policy display before changing the reader

## Evidence

The owner's finite desktop observation is preserved in
`native/boot/attempt31an/desktop-result-2026-11-14.json`. Both roles returned
four uncatalogued tag rows, Boolean-shaped `lobo`, opaque-shaped `love` and
absent `auxp`/`auxi`/`auxr`. LAB also had one malformed row. Both JSON display
commands exited successfully, but the old JSON shape scanner refused them.
No raw policy output was requested or saved. Desktop observations do not prove
Recovery admission or that Recovery uses exactly the same display.

A separate analysis session examined only the generic installed `bputil`
executable. REA 6.4.0/Ghidra 12.1.4 ran in the existing network-disabled,
diskless analysis VM; raw Apple bytes, disassembly and decompiler output stayed
ignored. Both workspace quiet locks were released and the VM stopped normally;
the previous lab job was restored. No live policy query or host setting change
was performed by the analysis session.

The universal executable is 196,320 bytes, SHA-256
`dcd2d73fbeb18d6ce3092605c151790d4a01ac9caeeb99fa23a4098e9559f545`.
Its arm64e slice has SHA-256
`80c9ae8b7536d0ee923a034198d201fe8773d71eea7b9f4bcb3244a2a2a630c2`.
The formatter occupies `[0x100002da0, 0x100005374)`, 9,684 bytes, with body
SHA-256 `35f37c14dcc91ef5eeeb10532120f0bf278957c8b4d5efca2c92c509b0d59c7e`.
Independent LLVM coverage agrees with all 2,421 instruction addresses. The
formatter's 1,473 P-code operations, version helper's 29 and JSON helper's 53
passed the body-bound/truncation gates. Five original-code smoke controls also
passed. These checks support bounded behavior findings, not source equivalence.

## Confirmed static behavior and original engineering decisions

| Formatter finding | Original reader change |
|---|---|
| TEXT emits `CEPO` and `SDOM` with a fixed `0x` prefix and an unsigned 64-bit hexadecimal rendering. | Accept those exact spellings and bounded hexadecimal grammar; canonicalize privately without truncating high bits. |
| TEXT emits `CPRO`, `CSEC` and `lobo` as unsigned Boolean values. | Store canonical Boolean values and explicit presence; duplicates, invalid values and unqualified `absent` variants refuse. |
| TEXT `love` renders six unsigned 32-bit decimal components as `D.D.D.D.D,D` (reference `0x100003684`). | Implement that exact bounded vector grammar. Do not accept arbitrary strings or model it as Boolean. |
| The exact parenthesized `smb0 && smb1` row has a true value, replaces the ordinary `smb0` row when both bits are set, and has no separate TEXT `smb1` row (reference `0x100004eb4`). | Decompose only that true conjunction into the existing two true semantic fields. False/absent expressions refuse; ordinary duplicate and mode-consistency checks still apply. |
| TEXT spells `CPRO` (reference `0x10000362c`); the JSON dictionary key spells `CRPO` (`0x100004198`). | Keep the spellings distinct. Never globally alias them. |
| `smb5` is a JSON Boolean only; the TEXT formatter does not emit it. | Do not add a speculative required TEXT field or relax the tag-group limit. |

The complete catalog for this bounded TEXT formatter is:

`BORD CEPO CHIP CPRO CSEC ECID SDOM auxi auxp auxr coih kuid lobo love lpnh nsih ronh rpnh sip0 sip1 sip2 sip3 smb0 smb1 smb2 smb3 smb4 spih stng vuid`.

The complete owner-run desktop observation subsequently confirms the four
missing architecture/security fields, the version grammar and LAB conjunction.
Both proposed real C parsers accept, both old parsers reject at generated line
50, and both text scans have zero unknown or malformed rows. The safe derived
record is `native/boot/attempt31ao/desktop-result-2026-11-15.json`.

The JSON helper at `[0x100002d08, 0x100002da0)` serializes an object with pretty
printing, converts it to UTF-8 and emits a final newline. Its version helper is
`[0x100002c74, 0x100002d08)`. The entry dispatcher's value-flow capture was
truncated at 3,000 operations. Consequently the old JSON-shape failure remains
unknown: no arbitrary prefix stripping or complete-dispatch claim is justified.
The new observer reports a fixed JSON failure stage instead.

## Independent source context

[Apple's pinned Image4 header](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/EXTERNAL_HEADERS/img4/runtime.h)
defines generic `LOVE` as a long OS version string and documents typed Image4
identifiers. It does not specify the lowercase `bputil` display grammar above.
[Asahi's pinned catalog](https://github.com/AsahiLinux/docs/blob/ae823b273477073a5419050ba826ac9be22e246a/docs/fw/boot.md)
lists `love` as Boolean; that assumption is unsuitable for this executable's
six-component output. Static analysis resolves this concrete disagreement
without copying Apple implementation code.

## Validation boundary

The new parser is original code. Its six stored fields participate in the
zero-initialized private `Policy` comparison and a tagged, domain-separated
v3 metadata HMAC. The old rotating `lpnh`, custom-object and SIP2/CTRR handling
remain explicit existing rules. This is preservation of supported fields,
not byte-for-byte comparison of every LocalPolicy attribute.

The old 111-source closure is unchanged. Reversing the anchored extension
reproduces the frozen observed source; stripping the original observation marks
then reproduces the original state source. This proves preservation outside
the declared extension, not identical acceptance behavior everywhere.

23 focused compiled-C tests pass normally and under ASan/UBSan after tightening
the new fields' absent-value refusal. The current production syntax checker is
35,200 bytes, SHA-256
`b6fbafe3c863416a1d2f442f00fa33753d50089830e6822e86a04657f826cc44`,
built with Apple clang 21.0.0, SDK 27.2, arm64/minimum macOS 13.0.
It contains only the extracted real old/proposed parsers and private stdin
handling; the host collector is not compiled into this executable.

The complete desktop check passed, privately in memory. Both JSON captures
still refuse at `ENVELOPE / OBJECT_OR_ARRAY_REQUIRED`; no arbitrary extraction
was used and the actual prefix cause remains unknown. Text parsing is sufficient
for the existing native collector, so this does not block integration.

Desktop success cannot prove paired Recovery, installation, Linux entry,
secondary-core startup or performance. Next is offline integration of the
same parser into a new read-only Recovery companion using the unchanged 31AM
engine. No restart, staging or boot/security action occurred. Boot021
restoration remains outstanding.

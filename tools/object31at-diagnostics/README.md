# Original finite object diagnostics, fixtures only

31AS's saved readback records an `UNKNOWN` candidate payload and lab CTRR
`disabled`, with the other common/binding/preservation predicates passing. Those
are two separate failed contracts. This adapter prepares finite object-failure
diagnostics; it does not fix the CTRR contract or establish a firmware fault.

There is **no live mode, deployment, controller integration, policy/Preboot scan,
writer, security change or reboot** in this directory. Nothing reads actual
private transaction state or a personalized installed object. All exercised
inputs are synthetic controls or retained project-owned candidate/codec files.

## Acceptance remains the original recognizer's decision

`diagnostics.c` includes the unchanged original MIT
`tools/boot-object31aj-native/core.c` after the builder verifies its frozen hash
and matching `reader.h`. Its first operation is the original `identify_object`.
Only that result supplies `recognizer_completed`, `known_exact`, `identity` and
`candidate_exact`. No diagnostic branch can change those decisions or make an
unknown/transformed/decryption-requiring payload acceptable.

The adapter reuses the original private framing and LZFSE-frame helpers to
explain rejection. It does not create another acceptance parser, decrypt data,
or decode twice. If the original compressed stream bound/frame/declaration
preconditions pass but the original recognition failed, the remaining original
decoder path supplies the `DECODE_REJECTED` class. If recognition completed but
its decoded hash was unknown, the class is `DECODED_UNMATCHED`.

`known_exact` alone is not controller acceptance. For example the original
recognizer can identify BOOT021, 31AF or 31AI exactly; only `candidate_exact`
matches this build's explicit own candidate definition. Target/selection,
wrapper authentication, policy, CTRR, rollback and firmware execution remain
separate matters and are not verified here.

## Finite stages

| Stage | Original condition explained |
| --- | --- |
| `INPUT_BOUND_REJECTED` | Empty/invalid memory input or whole-file bound |
| `DER_FRAMING_REJECTED` | Original IM4P/IMG4 framing rejects, including unsupported metadata/trailers |
| `KEYBAG_BLOCKED` | Original parser reports opaque keybag; no decryption |
| `COMPRESSED_BOUND_REJECTED` | Original 32 MiB compressed limit |
| `LZFSE_FRAME_REJECTED` | Original block/trailer/raw-total framing rejects |
| `DECLARED_SIZE_MISMATCH` | Framed raw total differs from optional declared size |
| `DECODE_REJECTED` | Original decoder fails after accepted frame and size preconditions |
| `DECODED_UNMATCHED` | Decoding succeeds but full own payload identity is unknown |
| `UNCOMPRESSED_DECLARATION_REJECTED` | Declared LZFSE size with a non-LZFSE body |
| `GZIP_UNSUPPORTED` | Original recognizer does not accept gzip |
| `UNCOMPRESSED_BOUND_REJECTED` | Original 160 MiB raw payload limit |
| `UNCOMPRESSED_UNMATCHED` | Raw body has no exact known identity |
| `KNOWN_MATCHED` | Original recognizer identifies exact known own bytes |

All returned strings are static enums. There are no hashes, sizes, input paths,
policy references, identifiers, private bytes or exception text in the fixture
result. The original read-stage failure is reported separately by the fixture
CLI as fixed `REFUSED`; that CLI deliberately uses the original bounded,
no-symlink/special-file/concurrent-change-refusing workspace reader.

## Build and test

Compile a new workspace build using the installed Apple SDK and the fixed
production candidate definition:

```sh
/usr/bin/python3 -I tools/object31at-diagnostics/build.py \
  --output "$PWD/build/object31at-diagnostics-review"
```

No-argument and `--help` entry points are inert. The only input operation is
`--fixture` with an absolute file beneath this checkout's `build/` directory;
all path components refuse symlinks/dot traversal. There is no outside-workspace
or live fallback:

```sh
build/object31at-diagnostics-review/object31at-diagnostics --fixture \
  "$PWD/build/ilinux-31ar-kit/candidate.macho"
```

Run only the new focused suite, normally and with ASan/UBSan:

```sh
/usr/bin/python3 -I tools/object31at-diagnostics/test_diagnostics.py
/usr/bin/python3 -I tools/object31at-diagnostics/test_diagnostics.py --sanitize
```

The suite compiles a separate original-core-only oracle and compares the four
authoritative result fields for every object case. Controlled fixtures exercise
every stage, exact raw bytes that resemble malformed DER, opaque contexts,
keybags, declarations, incomplete/trailing streams, decoder failure after a valid
frame, limits, inert CLI, path/FIFO/symlink refusals and output privacy. The
synthetic candidate is 64 KiB with its own explicitly synthetic hash definition.

A separate production-definition build checks the real retained
153,190,400-byte candidate against its public SHA256, then tests that raw file,
the retained own LZFSE and IMG4/LZFSE codec fixtures, and their trailer-negative
control. These are original project artifacts, not installed personalized boot
objects. If absent elsewhere, this integration test explicitly skips; it must
not be reported as local physical evidence. Both build modes use only the
system compiler/frameworks, produce receipts in ignored workspace storage,
and remove test binaries/fixtures afterward. Non-macOS hosts explicitly skip
this SDK-dependent class.

## Future integration boundary

The pure `object_diagnostics31at(Bytes, ObjectDiagnostics31AT *)` function can
explain bytes already read by a later separately reviewed controller. It owns
no path/selection/mount/policy operation. Its inclusion strategy means a future
build compiles `diagnostics.c` **instead of** separately compiling `core.c`:
the same original public recognizer functions remain present exactly once.
No such build or controller change has been made here.

A future controller should preserve current refusal behavior, emit bounded
categories before rollback, and keep target bindings and exact original payload
matching. This offline adapter is not authorization to replay a spent
transaction, weaken a guard, reinstall a boot object, or perform another native
boot.

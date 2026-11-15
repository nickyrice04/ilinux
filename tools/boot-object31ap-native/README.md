# Read-only Recovery companion with the qualified policy schema

31AP links the immutable 31AO schema extension into the existing conditional
read-only Preboot companion. It keeps 31AM's `preboot.c`, `preboot.h`, `main.c`
and `result.c`, and 31AL's diagnostic support byte-for-byte. Its CLI and result
schema consequently retain their original 31AM labels. There is no new install,
restore, policy-write, force, boot or repair operation.

`build.py` verifies every retained 31AM source pin (111) and 31AO source pin
(14), including both pinned inventory digests, before and after compilation.
The original generator applies the declared six-field/true-conjunction change;
exact reversal restores the instrumented frozen state, and stripping its marks
restores the original reader. Core object recognition, final admission and
snapshot/result validators remain unchanged. Accepted optional metadata is kept
in the private whole-policy comparison and metadata HMAC, as qualified in 31AO.

Build into a fresh workspace directory with the installed SDK:

```bash
python3 -I -B tools/boot-object31ap-native/build.py \
  --output build/boot-object31ap-native/production-v1 \
  --candidate-definition tools/boot-object31aj-native/candidate-definition.json
```

The focused tests reuse that binary and a verified original project 31AF payload
already held privately in the workspace. They build their own synthetic IMG4
surroundings (39-byte description, 300-byte inner opaque context, 2,680-byte outer
context; total 445,430 bytes), without copying Apple manifest data. Real object
recognition, collection, initial admission and mount/cleanup fixture paths run
together. No selected-object identity is mocked. The immutable reference stays
unchanged. An alternative original 31AF raw/IMG4 artifact may be supplied with
`--reference31af`; its contained payload must match the pinned original hash.

```bash
python3 -I -B tools/boot-object31ap-native/test_native.py \
  --compiled build/boot-object31ap-native/production-v1/ilinux31aj-reader \
  --output build/boot-object31ap-native/tests-normal-v1 \
  --reference31af build/boot-object31aj-native/validation-v1/synthetic-img4-OTHER-exact31af.bin
```

For sanitizer testing, build into another fresh directory with `--sanitize`,
then pass that binary to the tests with their own fresh `--output` and
`--sanitize`. Existing engine syscall suites and 31AO unit suites are retained
as prior evidence rather than repeated. Fixtures simulate mount state using
ordinary workspace directories; they execute no mount or policy commands.

These checks establish offline integration only. Actual paired Recovery,
conditional read-only mounting, field formatting there and final admission
still need the separately authorized read-only physical check. No staging,
Startup Disk selection, boot-object replacement or restart follows from a build.

# Qualified full transaction phase helper

31AQ is a new build of the original read-only transaction helper. It keeps the
31AJ full CLI, core object recognizer, JSON parser and type header byte-for-byte.
It uses the complete qualified 31AO policy state, including the six private
metadata fields, true SMB conjunction, whole-policy reread comparison and tagged
v3 HMAC. It does not reuse the smaller 31AP diagnostic-only CLI.

The builder verifies all 140 retained 31AP pins and the three source-page pins.
It runs the pinned 31AO generator, verifies exact extension reversal, then strips
only the reversible 31AL diagnostic marks before compiling the full helper.
The observed source and compiled pure source are both recorded under ignored
build output. No old source, profile, key, baseline or receipt is overwritten.

```bash
python3 -I -B tools/boot-object31aq-native/build.py \
  --output build/boot-object31aq-native/production-v1
```

The candidate stays the existing 153,190,400-byte image. The helper supplies
guarded snapshots, phase validation, fixed file verification and generation of
32 own random bytes into an empty private regular file. It contains no new
`kmutil`, policy-write, volume, install or restart operation. A separately
reviewed shell controller owns any authorized transaction writes.

The full collector requires a valid, identity-bound Preboot view before each
snapshot. The surrounding lifecycle must acquire and verify that view, release
only an owned mount, and check cleanup before later writes or default-volume
actions. An earlier diagnostic pass cannot substitute for this fresh evidence.

Focused tests use only new workspace fixtures and fresh keys/baselines. They
verify original project artifacts read-only: the known 31AF payload inside new
synthetic opaque IMG4 surroundings, the current candidate and boot021 rollback.
The real collector and keyed validators execute the initial-admission, initial,
candidate, before-restore, raw-policy and restored chain. No selected identity
or HMAC is mocked. No host policy, disk, Recovery or live capability command runs.

```bash
python3 -I -B tools/boot-object31aq-native/test_native.py \
  --compiled build/boot-object31aq-native/production-v1/ilinux31aj-reader \
  --output build/boot-object31aq-native/tests-normal-v1 \
  --reference31af build/boot-object31aj-native/validation-v1/synthetic-img4-OTHER-exact31af.bin \
  --candidate build/31aj-m5-prepared-final/candidate.macho \
  --rollback build/31aj-m5-prepared-final/m1n1-boot021.bin
```

Build sanitizers into another new directory with `--sanitize`, then use that
binary, a fresh test output and the test runner's `--sanitize` option. Production
default/help is inert. Offline build or test success grants no staging,
security, native-boot or restart authorization.

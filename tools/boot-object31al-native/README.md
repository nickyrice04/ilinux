# 31AL diagnostic-only native reader

This new original helper observes the unchanged snapshot/initial-admission
logic that refused during 31AK. It does not fix, reinterpret or bypass a guard.
No Recovery/native result is supplied by this offline implementation.

`generate.py` pins the original project's `core.c`, `json.c`, `reader.h` and
`state.c`. The first three are copied byte-for-byte into ignored build output.
The marked state source adds only diagnostic calls and truth-preserving wrappers
around existing conditions. Stripping those additions must reproduce every byte
of the pinned original state source. Each wrapper evaluates its original
expression once, retains its boolean result and preserves short-circuit order.
The generator refuses a changed anchor or a failed stripping comparison.
No frozen source, helper, target, parser, command argument or decision changes.

The new main exposes only these modes:

- `--diagnose-snapshot --target-volume LAB --original-volume ORIGINAL --profile P`
  uses the original fixed lab/original mounts and guarded Recovery collector.
- `--diagnose-fixture WORKSPACE_PLIST --profile P` uses original synthetic CF
  fixture handling and is labeled `SYNTHETIC_CONTROL`.
- `--validate-diagnostic FILE --profile P` reads at most 8192 bytes through the
  unchanged descriptor/no-follow reader and prints only a normalized diagnostic.

Default/help are inert. There are no install, write, RNG, private-group,
snapshot-value, full-snapshot or phase-validation CLI modes. The unchanged
profile loader still requires the basename `ilinux31aj-reader`; the new binary
has its own size/hash and must have a separately reviewed self-bound profile.
Candidate and boot021 identity constraints remain unchanged.

## Output and interpretation

The exact 16-key schema is `ilinux31al-snapshot-diagnostic-v1`. Scope is either
`RECOVERY_READ_ONLY_DIAGNOSTIC` or `SYNTHETIC_CONTROL`; status is `REFUSED` or
`INITIAL_ADMISSION_PASS`. `stage`, `failure_kind`, `reason` and `command` use only
the finite literal tables in `diagnostic.c`. No input string becomes a label.
`command_exit` is null or an integer 0 through 255. `stdout_bytes` is an integer
0 through 1048577. No stderr is retained or printed; original capture behavior,
byte caps and 20-second per-command deadline remain unchanged.

`read_only` is true. `writes_authorized`, `native_ready`, `identifiers_returned`
and `policy_values_returned` are false. The record contains no paths, UUIDs,
groups, hashes, policy values, unknown field names or full snapshot. A failed
capture's stage/command/exit/count are retained even if the original control
flow subsequently performs another capture. Those later commands still run in
their original order; only their observation updates are suppressed.

Known predicates distinguish metadata format and required field gates, policy
missing/duplicate/malformed/cardinality/unsupported-field errors, genuine
pairing/security/CTRR guards, command failures, and reread inconsistencies.
A guard refusal is evidence that its predicate failed; it is not a compatibility
bug diagnosis or permission to weaken the predicate. Some combined original
predicates intentionally share a finite reason. Missing/unrecognized selected
payload can still yield a collected snapshot; the subsequent unchanged
initial-admission check has its own `INITIAL_ADMISSION_GUARD` outcome.

Diagnose returns 0 only for initial-admission success, otherwise 2. Validation
returns 0 for either valid structured outcome, including a valid `REFUSED`
record. It returns 2 for malformed, unknown, oversized, unsafe-path or
inconsistent input. It never prints the raw input. Validation is a display
boundary, not authenticated evidence of hardware state or write authorization.
The profile is independently checked against the executable before any mode.

## Offline checks and build

Run only the new original fixtures, not a live mode:

```sh
python3 -I tools/boot-object31al-native/test_native.py
python3 -I tools/boot-object31al-native/test_native.py --sanitize
```

Synthetic CF fixtures exercise the real collector with original predicates.
Own child processes test nonzero exits, bounded stdout and first-failure
attribution without calling Apple inspection commands. The pass control uses
an explicitly synthetic Snapshot with the original initial-admission validator;
it does not assert a real selected-object identity. Privacy controls inject
synthetic secrets into metadata, values and unknown fields. The validator tests
exact keys/types/enums, consistency, byte caps, duplicate/deep JSON and symlinks.

`build.py --output NEW_WORKSPACE_BUILD_PATH --candidate-definition DEFINITION`
compiles original C with the installed SDK only. `--sanitize` enables ASan/UBSan.
The definition uses the existing `ilinux31aj-compiled-candidate-v1` schema.
Production binds the unchanged 153190400-byte candidate hash from the frozen
31AJ profile. Receipts record original source hashes, stripping proof, compiler/
SDK versions, ABI/minimum OS, binary hash/size, and all live/native flags false.
Generated C, test fixtures and binaries stay under ignored `build/`.

# 31AU original diagnostic boot transaction controller

This new controller derives the qualified 31AR/31AO transaction implementation
without editing any frozen input or previous kit, profile, state, key, baseline
or spent marker. Building and fixture testing perform no Recovery admission,
mount, policy, boot-object, security, default-selection or firmware operation.
Native execution remains a separately reviewed and authorized step.

## Interface and isolated state

The controller preserves the transaction/result-observer command interface:

```sh
ilinux31au-reader --transaction install|restore \
  --profile ABSOLUTE_SCRATCH/profile.json --scratch ABSOLUTE_SCRATCH

ilinux31au-reader --validate-transaction-result RESULT_FILE \
  --operation install|restore
```

Default and `--help` are inert. There is no force, reset, retry, native boot or
Startup Disk action. The executable basename is `ilinux31au-reader`; profile
schema is `ilinux31au-recovery-profile-v1`, with the same fixed eight-key profile
contract and exact candidate/boot021/helper pins. The profile's initial payload
is now **BOOT021**, and initial admission additionally requires lab CTRR disabled.
The previous 31AF candidate is not accepted as a new starting point.

Scratch is private, canonical, current working directory and named
`ilinux31au.` plus 6–32 alphanumeric bytes. Persistent state is exclusively
created as `ilinux31au-state` under the existing trusted lab Data
`private/var/db` parent. Existing AU state is refused without adoption, deletion
or overwrite. The old `ilinux31ar-state` is never opened or modified. A distinct
profile/helper hash and fresh own comparison key bind all new baseline and
target commitments. The private snapshot stays the qualified AJ-v2 schema;
its profile hash distinguishes the new transaction contract.

Initial admission, target-role/UUID binding, typed policies, Original Full and
CTRR enabled, lab Permissive, comparison-key/profile binding, complete semantic
and private-metadata preservation remain mandatory. Candidate acceptance still
requires exact original candidate bytes **and lab CTRR enabled**. No speculative
interpretation of a public report relaxes either condition.

## Diagnostics from the same selected read

The generated collector retains its original selected-path formula, guarded
before/after policy reads and controller before/after target/mount checks. It
calls the frozen original `identify_object` through the 31AT adapter on the
**same bytes from the existing selected read**. There is no second file read,
additional policy query, alternate Preboot scan, alternative decoder, decryption
or alternative acceptance parser. The exclusion of the old 31AI identity stays.

The finite diagnostic distinguishes absent reference, read refusal, DER framing,
keybag, bounds, LZFSE framing/declaration/decode failure, unmatched decoded bytes
and exact known own payload. It also reports the captured CTRR classes and
independent preservation/object/CTRR/whole-phase Boolean predicates.

A separate comparison establishes whether the selected COIH/NSIH reference
changed between the immediately checked prewrite observation and postwrite
observation. Both references come from already-collected Policy structures.
An in-memory HMAC binds them to the own key, profile, LAB role and a new domain.
Only `selection_comparison_available` and `selected_reference_changed` leave
memory. No reference or reference HMAC is serialized, printed, persisted or
reused across Recovery visits. The comparison is diagnostic and does not change
the candidate's acceptance decision.

Each attempted writer still gets guarded readback even when its exit is nonzero
or interrupted, where possible. After a collected postwrite snapshot, its finite
diagnostic is durably and exclusively persisted as `candidate-diagnostic.json`,
`ctrr-diagnostic.json` or `boot021-diagnostic.json` in the private AU state.
Snapshot/exit/diagnostic durability failure refuses readiness. Candidate
postcondition refusal leaves its finite diagnostic available and its marker
spent. No file or identifier, hash, errno, opaque metadata or raw policy value is
returned by the public result.

Result schema is `ilinux31au-transaction-result-v1`, with one new `diagnostics`
object. Its strict observer checks the exact 21 nested keys, fixed enum values,
Boolean types and relationships. Stage, container, codec, recognizer completion
and exactness must form a combination the frozen original adapter can produce.
Available diagnostics belong to candidate phase for install and raw-policy or
restored phase for restore, including refused results without success flags.
Unknown strings/keys or contradictory exactness/read/phase/CTRR/comparison claims
refuse without echoing input.
A validator display pass is not transaction success. Synthetic results cannot
be displayed as live results by the result observer.

## Independent restoration and preserved transport

Restoration needs the AU helper/profile/boot021 and the AU private baseline/key;
it never needs the candidate file or successful candidate admission. Exact
boot021 plus disabled CTRR is a guarded read-only no-op. Otherwise the original
conditional lab-only CTRR preparation and one fixed raw boot021 operation remain,
followed by exact restored validation and owned cleanup. Spent writers are never
repeated. A partial/refused install can therefore use independent restoration.

The existing foreground-terminal handoff, authentication input handling,
termios restoration and 180-second child deadline are unchanged; the builder
asserts exact transport source equality with frozen 31AR. No credential capture,
automated password entry, changed confirmation handling or new PTY protocol is
introduced. Existing RO/RW APFS ownership checks and cleanup remain unchanged.

## Offline builds and meaningful tests

```sh
python3 -I tools/boot-object31au-native/build.py \
  --output "$PWD/build/boot-object31au-native/production-v2"
python3 -I tools/boot-object31au-native/build.py \
  --output "$PWD/build/boot-object31au-native/sanitized-v2" --sanitize
```

Run the new complete controller suite with the retained project-owned inputs:

```sh
python3 -I tools/boot-object31au-native/test_native.py \
  --compiled "$PWD/build/boot-object31au-native/production-v2/ilinux31au-reader" \
  --output "$PWD/build/boot-object31au-native/test-normal-review" \
  --reference31af "$PWD/build/boot-object31aj-native/validation-v1/synthetic-img4-OTHER-exact31af.bin" \
  --candidate "$PWD/build/ilinux-31ar-kit/candidate.macho" \
  --rollback "$PWD/build/ilinux-31ar-kit/m1n1-boot021.bin"
```

For the sanitizer suite select `sanitized-v2/ilinux31au-reader`, use another
fresh test output and add `--sanitize`. The legacy `--reference31af` fixture is
retained only for negative initial-admission coverage and artifact preservation;
it is not the accepted new baseline. Missing genuine artifacts are an error,
not a synthetic substitute or implicit integration pass.

The builder verifies all 143 retained qualified-source pins, the original AR
controller and frozen AT adapter. It proves exact reversal of the five AU state
edits to the pure qualified AO state, and exact reversal of the three profile
parser edits to the original JSON implementation. Original core/reader and typed
policy extension bytes remain exact. Build receipts record source/helper hashes,
compiler/SDK, sanitized mode and the explicit initial/candidate policy contracts.

The complete fixture suite executes the actual new controller with genuine own
candidate/boot021/owned compressed carriers and synthetic APFS/policy/mount/writer
backends. The original independent exec guard forbids synthetic fixtures from
falling into live system commands. It retains the earlier 25 integration cases
and adds restored initial admission, old-state isolation, explicit read/recognition
failure classes, both reference-comparison outcomes, real compressed controls,
durable refusal evidence, candidate-free restoration and strict nested-result
rejection. Normal and ASan/UBSan results must be recorded separately. No native
compatibility or performance is inferred from these fixtures.

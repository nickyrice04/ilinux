# 31AW bounded decoder integrated into the original transaction controller

This is a new offline-built component, not a staged kit or native boot approval.
No build or fixture run dispatches an actual policy, disk, mount, SEP, install,
security or default-selection operation. The previous 190 AU source inputs,
AV proposal and all consumed transaction state remain unchanged.

## What changed

The generated selected-object collector now calls the reviewed bounded buffer
recognizer. Complete strict DER/LZFSE framing, declared counts, compressed/raw/
file limits, keybag blocking and exact known size/SHA-256 remain required. The
decoder allocates framed output plus one byte and rejects count disagreement;
API return alone is not identity. Its explanatory subreason distinguishes
`ALLOCATION_ERROR`, `DECODE_RETURN_ZERO` and `DECODE_OUTPUT_MISMATCH`. Successful
decoding is `DECODED`, while nondecode paths remain `NOT_APPLICABLE`.

The existing selected read supplies both recognition and diagnostic results.
There is no second selected-file read, alternate scan, decryption or guessed
acceptance. Original core/header bytes remain identical. The reviewed AV proposal
is derived with only a reversible split of its generic failure reason; it is
not edited in place.

Bounded runtime controls encode/decode a deterministic own 1 MiB sequence and
refuse trailing/truncated/invalid/count/bound controls. They run before install
can reach target, mount, persistent state or writer work. Their finite result is
part of the strict transaction result. Failed capability blocks installation;
it does **not** block candidate-independent guarded raw boot021 restoration.

The component also repairs a discovered observer defect. The frozen JSON parser
rejects all negative literals, although pre-writer results legitimately contain
`writer_exit=-1`. A new reversible generated-parser change admits exactly
canonical numeric `-1`. The observer still allows that exit only when no writer
was attempted. Unsigned profile counts and deadlines still reject negatives;
`-0`, `-01`, other negatives, signs, floats and exponent forms are not admitted.

## Preserved contracts

New basename/profile/result/private-state names use `31aw`. There is no adoption,
reset or overwrite of old AU/AR state. Initial admission is exact boot021 with
disabled lab CTRR. Candidate admission remains exact candidate **and enabled
CTRR**. Original Full/CTRR, private and semantic preservation, target/role/owner
binding, one-shot durable writers and owned mount cleanup remain mandatory.

The builder compares 26 namespace-normalized safety function bodies against AU,
including writer/terminal/mount/target/state/durability/cleanup. Removing the
exact preflight block reverses the transaction-flow change. Generated state,
profile and parser edits have explicit reversal checks. All 190 frozen source
pins are checked before and after the build. There is no new policy writer:
the documented whole-policy reconstruction lead is a separate unimplemented
experiment, not part of this integration.

## Build and run only offline controls

From the repository root, choose fresh outputs:

```sh
/usr/bin/python3 -I tools/boot-object31aw-native/build.py \
  --output "$PWD/build/boot-object31aw-native/review-normal"
/usr/bin/python3 -I tools/boot-object31aw-native/build.py \
  --output "$PWD/build/boot-object31aw-native/review-sanitized" --sanitize
"$PWD/build/boot-object31aw-native/review-normal/ilinux31aw-reader" --codec-capability
```

`--codec-capability` runs only synthetic in-memory controls. Default/help are
inert. No Recovery/target/private-state dispatch occurs. Do not invoke live
transaction commands without a separate reviewed authorization.

Run the actual compiled controller with synthetic OS/writer backends and
already-held genuine own artifacts:

```sh
/usr/bin/python3 -I tools/boot-object31aw-native/test_native.py \
  --compiled "$PWD/build/boot-object31aw-native/review-normal/ilinux31aw-reader" \
  --output "$PWD/build/boot-object31aw-native/test-review-normal" \
  --candidate "$OWN_CANDIDATE" --rollback "$OWN_BOOT021"
```

Set the two artifact paths to retained workspace copies; exact candidate and
boot021 pins are enforced by the real helper. For sanitizers use the sanitized
binary, another fresh test output and `--sanitize`. Optional
`--reference31af "$OWN_LEGACY31AF"` adds the genuine legacy-start rejection
control. Without it only that method is explicitly skipped; enabled-boot021
initial refusal remains independently tested. No source adapter or new kit is
needed. The harness generates two own compressed carriers from the genuine
candidate in fresh output and deletes them after the run, avoiding an old build
cache dependency. Test backends cannot fall through into live system commands.

## Validation and limits

Root's final builds passed **52 methods normally and 52 under ASan/UBSan**, zero
skips with the retained legacy control. The optional-input path separately passed
its enabled-boot021 check and explicitly skipped its one absent legacy check.
Independent review passed five decisive controller methods plus the standalone
capability command, matched source/build pins and checked the safety reversals.
See the separately attributed [offline receipt](../../native/boot/attempt31aw-offline-2026-11-15.json).

The tests include complete install/restore fixtures, genuine compressed
candidate recognition, the former valid-input rejection now decoded but kept
unknown identity, failed capability before any install writer, raw restore with
failed capability/missing candidate/unrecognized compressed selection, disabled
CTRR refusal despite an exact candidate, finite failure/display relations,
negative-number controls, Original preservation and durability failure cases.

The decoded output allocation may reach **160 MiB + 1 byte**, plus library
scratch. Candidate output is 153,190,401 bytes. Runtime controls use a smaller
bounded input and do not prove Recovery can sustain that peak. Builds/tests
qualify original software paths, not real APFS/SEP transitions, actual Recovery
compatibility, firmware acceptance, Linux, physical SMP/GPU or performance.
No native boot or policy behavior is established by these offline passes.

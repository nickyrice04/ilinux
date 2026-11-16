# 31AX offline lab reconstruction and functional rescue controller

This original component implements a proposed local OS boot-lab experiment
through Apple's supported commands. Building and fixture testing do not run those
commands, query installed policies or objects, mount a volume, change firmware or
security settings, or create a kit. The original macOS installation remains
protected by the controller's unchanged Full Security checks and additional
never-rebased Original invariants. Native execution needs a separately reviewed
and authorized handoff; this directory does not supply one.

## Reset and candidate path

The new profile schema and helper/state names use `31ax`. The required profile
strategy is exactly `reconstruct_lab_then_boot021_rescue`; publication does not
authorize writes. Old AW/AU/AR state, baselines, keys and spent markers are never
adopted, reset or overwritten.

Initial admission requires exact boot021, disabled Lab CTRR, paired one-true
Recovery context, matching target/role bindings, fully typed policy fields and
no other Lab downgrade. Before any reset writer, the helper durably enrolls:

- A fresh own key/profile and target commitment.
- The pre-reset Original semantic/private policy anchor.
- Typed Original and Lab hardware/VUID/KUID and protected-option commitments,
  plus the known Lab manifest commitment.

The private anchor authentication binds the protected snapshot HMACs and both
labeled semantic vectors as well as the typed projections, profile and key. A
valid-looking replacement snapshot therefore cannot silently rebase an anchor.
No identity, raw policy or raw field value is returned publicly.

One durable `reset-attempt` marker permits only the fixed command
`bputil -n -v BOUND_LAB_GROUP`. This reset command does not include `-c`.
The existing interactive authentication transport is unchanged. An unknown
writer operation is refused rather than falling through to raw enrollment.

Strict post-reset admission requires enabled CTRR, the immutable Original
anchor, unchanged typed Lab protected identity, unchanged Lab protected private
metadata and manifest, and a selected payload of NONE or exact boot021. Lab
LPnH/signature/envelope reissuance and the explicitly modeled COIH/SIP2 changes
are separate from those stable requirements. Safe default representation changes
are allowed only for Lab: false versus absent for SMB2/3/4 and SIP1/SIP3, and a
zero SIP0 mask versus absent. True or nonzero values are refused. Original
semantics remain exact.

A strict reset observation must be saved as a separate candidate baseline and
durable `reset-ready` marker before candidate installation. Original's anchor is
never replaced. The candidate still requires its exact known size/SHA-256 and
enabled CTRR; a changed, unknown or rescue-only observation cannot become its
baseline. Nonzero writers, readback failures and durability failures spend their
operation and stop the candidate path.

## Independent functional rescue

Restore needs the pre-reset enrollment and exact boot021 artifact; it does not
need the candidate or a fresh candidate baseline. Failed codec capability also
does not prevent guarded raw restoration. A transient failure of the first reset
readback can be observed again by this independent operation. Current Original,
target, authority context, typed identity/security and auxiliary-field guards
must still pass before any rescue writer. Persistent unreadability or an unsafe
or unknown schema refuses and requires a separate manual recovery procedure.

The narrowly exceptional rescue path may observe typed Lab private/manifest
issuance differences without comparing the old aggregate Lab HMAC for admission.
It classifies these groups as **UNQUALIFIED_TRANSITION**, not as proven normal
reset behavior. Hardware/VUID/KUID, production/domain/epoch/Local Boot and
Original invariants stay protected. KUID and Local Boot are not a human owner
identity or an owner-list verification claim; Apple performs authentication for
each fixed interactive command.

Before a rescue writer, the helper durably freezes the **current** safe Lab
snapshot and typed contract under a separate authenticated rescue anchor.
Persistence failure permits zero rescue writers. Existing complete anchors are
loaded before even an already-restored no-op; partial or tampered anchors cannot
be overwritten or bypassed by rebasing to new observations.

Current Lab private metadata and semantics remain fixed across rescue writes.
The conditional existing `-c` operation must preserve the selected-reference
tuple and manifest. The raw boot021 operation may change COIH; NSIH must remain
the current manifest, except that a missing manifest may become only the known
pre-reset manifest. The final result requires exact boot021 and disabled CTRR.
Every writer retains its durable one-shot marker and guarded readback.

A successful restore reports scope `FUNCTIONAL_BOOT021_CTRR_DISABLED` and never
asserts old Lab metadata restoration (`old_lab_metadata_restored=false`). It does
not promise old policy signatures, bytes or issuance commitments were restored.
No result authorizes a native boot or claims native readiness.

## Typed observations and retained code

The added closed parser requires BORD/CHIP as unsigned 32-bit hex values, ECID
as unsigned 64-bit hex, one typed VUID/KUID each, and two 96-hex LPnH rows.
Both policy roles bind VUID to their observed APFS group; hardware values must
agree and CHIP must be T6050. The three known auxiliary trust rows must each
occur once as ABSENT. Optional `prot`/`hrlp`/`losv` omission follows the already
qualified formatter; a present row must be ABSENT. Duplicate, malformed,
unsupported or unsafe rows refuse. Unknown future fields are not assumed safe.

The same guarded policy reads supply the typed view and selected-object decoder;
there is no additional policy query or selected-object scan. LPnH may rotate
between observations as Apple documents, but inconsistent before/after data
within a single observation still refuses.

The bounded AW decoder and synthetic runtime controls are retained. Temporary
decoded output can reach 160 MiB plus one byte, plus framework scratch; the
small runtime control does not qualify that peak in Recovery. The pure
`--codec-capability` command remains available without target or policy access.

The builder verifies the pinned AW receipt, its 14 inputs and all 190 AU inputs.
It compares 21 namespace-normalized filesystem/mount/target/durability safety
bodies and the original candidate/raw/conditional-CTRR writer body, including
the interactive transport. Six typed-state changes have exact reversals to AW.
The new command and state-machine changes remain explicit original AX code.

## Offline reproduction

Choose fresh build/test outputs from the repository root:

```sh
/usr/bin/python3 -I tools/boot-object31ax-native/build.py \
  --output "$PWD/build/boot-object31ax-native/review-normal"
/usr/bin/python3 -I tools/boot-object31ax-native/test_native.py \
  --compiled "$PWD/build/boot-object31ax-native/review-normal/ilinux31ax-reader" \
  --output "$PWD/build/boot-object31ax-native/test-review-normal" \
  --candidate "$OWN_CANDIDATE" --rollback "$OWN_BOOT021" \
  --reference31af "$OWN_LEGACY31AF"
```

Use already-held exact own artifacts. The legacy reference is optional; omitting
it explicitly skips that one negative method. The harness generates its own
compressed carriers and cleans fresh fixture transactions. For sanitizers add
`--sanitize` to the build and harness and use distinct fresh outputs.

The independent pure typed-contract suite uses no controller/collector/writer:

```sh
/usr/bin/python3 -I tools/boot-object31ax-native/test_policy.py
ILINUX31AX_POLICY_SANITIZE=1 /usr/bin/python3 -I tools/boot-object31ax-native/test_policy.py
```

Current validation and attributed final counts belong in the project AX offline
receipt. These fixtures exercise software paths; actual Reconstruction/Recovery/
SEP behavior, firmware acceptance, Linux, physical SMP/GPU and performance remain
unverified. No staging or restart package is included.

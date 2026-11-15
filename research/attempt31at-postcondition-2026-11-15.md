# 31AT: classify the preserved 31AS refusal before another restart

Independent source audit, November 15, 2026. No live policy, private transaction
file, selected boot object, mounted volume or device was read for this note. No
Apple policy/boot command, writer, mount, security change or restart was
performed. Review inputs were public project source and finite owner-confirmed
results; execution was restricted to the original workspace fixture tests below.

## Established result and next decision

The actual 31AS install reached the Apple writer and returned writer exit zero,
then refused at `POSTCONDITION / POLICY_OR_OBJECT`. Its guarded candidate
snapshot was collected and saved before that refusal. This is a successful
writer invocation followed by failed verification, not a successful candidate
installation or a native Linux test. The later owner-authenticated saved-state
observation identifies two failed contracts: the selected payload was
`UNKNOWN`, and the captured lab CTRR setting was explicitly `disabled`.
The underlying object-recognition failure and the reason for the policy state
remain **Unknown**. See the [physical result](../native/boot/attempt31as-recovery-2026-11-15-result.md)
and [finite owner-output summary](../native/boot/attempt31at-postcondition-2026-11-15.json).

The human independently confirmed `RESTORE_COMPLETE`, rollback verification,
cleanup verification and the final shell helper exit zero, then Macintosh HD
desktop and default. Those confirmations close the restoration task. They are
not an independently recorded restore transcript or a fresh target observation;
the raw restore writer exit is unavailable. No redundant policy check is
required to interpret this result.

The strictly read-only observer has now distinguished the failed contracts
without another install, Recovery visit or reboot. It did not reset, consume,
repair or replay the old transaction. The next engineering work is a finite
object-read diagnostic and qualification of the expected CTRR transition;
neither acceptance requirement is relaxed.

## Exact candidate-phase predicate matrix

The production controller uses the qualified 31AO-generated `state.c`, not the
earlier AJ-only policy commitment. The generated phase validator retains the
AJ phase rules, with 31AO's private v3 metadata commitment. Source references:
[controller](../tools/boot-object31ar-native/controller.c),
[state implementation](../tools/boot-object31aj-native/state.c),
[qualified generator](../tools/boot-object31ao-native/generate.py),
[finite extras](../tools/boot-object31ao-native/extra_policy.c).

| Predicate class | Candidate requirement | What can be reported safely |
| --- | --- | --- |
| Snapshot format | Exact v2 schema, fixed guarded Recovery scope and false claim flags | Format accepted/refused |
| Common target flags | Guarded, paired lab Recovery; Original Full with CTRR enabled; lab Permissive; complete parsed policy | Fixed Boolean comparisons |
| Profile | Candidate and initial baseline bind the exact public profile | Match/refused, without an identifier |
| Key binding | Loaded comparison key; metadata bound; captured key ID equals key's ID | Bound/unbound only |
| Initial baseline | Exact 31AF selection with valid common/profile/key predicates | Baseline valid/refused |
| Original policy semantics | Eight canonical semantics equal initial baseline | Equality Boolean |
| Lab policy semantics | Eight canonical semantics equal initial baseline | Equality Boolean |
| Original private metadata | Captured role-bound v3 HMAC equals initial baseline's commitment | Equality Boolean |
| Lab private metadata | Captured role-bound v3 HMAC equals initial baseline's commitment | Equality Boolean |
| Candidate object | Exact selected payload identity is `CANDIDATE` | Finite object class and exactness Boolean |
| Candidate CTRR | Captured lab CTRR is `enabled` | Required predicate Boolean |

The controller's refusal ordering matters. A failed observation or failed
durable snapshot save would instead report `READBACK / READBACK_OR_DURABILITY`.
A nonzero writer or interruption would report a writer refusal. The actual
postcondition refusal therefore establishes a persisted candidate snapshot,
but does not select a row in this table.

The collector itself establishes paired Recovery, expected Original/lab modes,
Original CTRR, stable before/after policy reads and exact target-role bindings.
The observer should still apply the stored schema and binding checks rather
than infer that every captured predicate must be true from the report label.

## Identity and compression remain distinct hypotheses

The [owned object recognizer](../tools/boot-object31aj-native/core.c) requires
the full uncompressed byte count and SHA-256 of the selected payload to match
the original candidate. It accepts bounded raw, IM4P and IMG4 framing, plus a
bounded, fully consumed LZFSE stream. Keybags, unsupported framing, inconsistent
compression metadata, extra trailing bytes and unsuccessful decoding refuse.
An equivalent but byte-different Mach-O does not satisfy exact identity.

The released candidate is 153,190,400 bytes. The recognizer bounds uncompressed
output at 160 MiB, compressed streams at 32 MiB, and the carrier separately.
Owned-codec controls cover the exact candidate as raw LZFSE and synthetic IMG4
LZFSE, together with negative trailer controls. They establish those original
fixtures; they do not prove that every actual `kmutil` carrier or transformed
payload is recognized. See the [retained controls](../native/boot/attempt31aj-kit/owned-codec-controls.json).

Possible identity-refusal classes include framing, compression bounds/format,
failure to read the selected path, a blocked keybag, an explicitly excluded old
identity, or a byte-different decoded payload. The saved `UNKNOWN` class does
not distinguish these. The owner-authenticated observation independently rules
out a role-semantics or captured private-commitment mismatch: both roles pass
those comparisons. It also establishes an explicit disabled CTRR observation,
rather than an unknown/unreported status. Boot021 restoration follows a
different raw-object path and does not identify the candidate's failure cause.

The exact policy parser makes this distinction meaningful: a recognized
`Disabled` status requires SIP2 explicitly true. A recognized unsupported,
duplicate or contradictory CTRR row would fail policy parsing and prevent the
saved candidate capture. An unknown CTRR enum instead would mean no recognized
status row; the v2 result excludes that case here. These are captured evidence
facts, not a fresh current-policy query.

The retained [31AG REA evidence](../reverse-engineering/findings/cpu-startup31ag/validation.json)
qualifies bounded `kmutil` protection-profile/serialization and selected-path
behavior, with independent instruction-word checks. It does not qualify a full
Mach-O compression/normalization pipeline or prove the exact Recovery binary's
runtime behavior. Whole-function pseudocode was explicitly rejected where
provider output was truncated or removed blocks. A fresh REA query should be
chosen only after a finite predicate result identifies the relevant branch.

## Observer truth and privacy contract

The observation concerns **preserved transaction evidence**, not current policy,
current selected object, firmware acceptance, successful candidate boot,
physical secondary execution or performance. Equal metadata commitments report
equality of the captured role-bound commitments. They are not a fresh policy
query or independent recomputation from raw policy, which is not retained.

Snapshot v2 has no HMAC-domain-version field. Qualification of the six additional
31AO fields must come from the frozen generated helper/source lineage and exact
transaction profile; an observer must not invent an encoded v3 field. Opaque
commitments must never be printed, copied, abbreviated or entered into Git.

An offline-tested observer should:

1. Be inert by default, with a distinct explicit live read option and fixed
   target path. Invoke no shell, mount, Apple utility, writer or network API.
2. Hold directory/file descriptors, refuse symlinks and special files, check
   root ownership and restrictive modes, cap file sizes and all reads, and
   compare identity/metadata before and after reads. Refuse active transaction
   locking instead of racing a writer. Do not alter the lock or its metadata.
3. Reject duplicate/extra JSON keys, invalid Unicode/escapes, embedded NUL,
   wrong scalar types, noncanonical commitments, excessive depth and size,
   missing or inconsistent bound snapshots, and unsupported phase labels.
4. Validate the exact frozen source/profile contract and key binding in memory.
   Never export the key, key ID, HMAC, policy values, paths or target identifiers.
5. Emit a fixed schema of finite result labels and Boolean predicates. Refusal
   text must be fixed and must not interpolate exception details or input.
6. Separate candidate failure classification from any preserved restoration
   snapshot classification; do not turn a file's presence into rollback proof.
7. Test synthetic positive and one-predicate-negative cases, malformed inputs,
   stale/concurrent state, unsafe modes/links, bounded reads and finite-output
   leakage controls before asking the human for one authenticated read.

## Relation to working public M5 code

The public native route uses a padded Mach-O Aura Stage 1, an executable-window
contract shared with its kernel, and distinct Stage 2 loading. This supplies
original reusable code and a more promising route than declaring an Apple-only
barrier. It does not make a mismatched object-verification guard safe to bypass.
The existing [matched-board review](attempt31as-boot-and-firmware-2026-11-15.md)
identifies a reported J716c/all-18-core/accelerated-graphics stack, while noting
its bounded frequencies and missing reproduction inputs. The next candidate
should preserve the exact firmware/Stage 1/Stage 2/kernel/window/DT contracts.
Neither that external report nor our current writer exit proves macOS parity.

No new native attempt is warranted until the object-read and CTRR investigation
supports a concrete, independently tested repair or a materially more informative
reviewed transaction. A writer zero and a saved `UNKNOWN` object are insufficient
to approve a Linux boot.

## Independent observer review

The frozen original observer in
[tools/postcondition31at](../tools/postcondition31at/README.md) was reviewed
against the exact source contracts above. Its source contains no subprocess,
network, writer, mount or current-policy operation. The finite output keeps
captured evidence separate from current verification and explicitly declines
to revalidate the target commitment or claim snapshot authentication.

An independent run of `python3 -I
tools/postcondition31at/test_probe.py -v` passed **31 tests, zero skips**, in
0.850 seconds. The tests include real Darwin empty-ACL fixture reads, unsafe
mode/link/FIFO/lock/change refusals, inert and invalid argument behavior,
per-predicate negative controls, finite private output and a differential
oracle compiled from six digest-pinned generated 31AR/31AO production sources.
The native oracle only parses synthetic workspace captures and validates the
candidate phase; it does not dispatch a live controller or Apple utility.

No actionable finding remained in this source review. No actual comparison
key, baseline, candidate capture, target metadata, selected boot object or
current policy was read by the reviewer. The first v1 review preceded the
owner-authenticated result; its inability to distinguish the two enum classes
was retained rather than retrospectively changing that evidence.

The subsequent v2 change adds four informational enum-comparison Booleans
outside the phase conjunction, with no read-set or acceptance change. Independent
`/usr/bin/python3 -I tools/postcondition31at/test_probe.py -v` passed **32 tests,
zero skips**, in 0.756 seconds. The parent's owner-supplied v2 output then confirms
`UNKNOWN`, not `NONE`, and disabled, not unknown CTRR. All other candidate
predicates pass; the saved restored phase passes exact BOOT021 and disabled CTRR
alongside all baseline preservation requirements. No fresh selected-object or
policy verification is inferred.

## Reusable diagnostic adapter review

The new original [object diagnostics adapter](../tools/object31at-diagnostics/README.md)
preserves the pinned original `identify_object` as its sole recognition/exactness
authority. It only reuses the original pure framing helpers to assign finite
refusal categories; it performs no second decode and cannot turn a rejected or
unknown object into acceptance. Its CLI is restricted to workspace build
fixtures. No live or controller integration is present.

The independent focused normal suite passed **17 tests, zero skips**, in
2.267 seconds. Each object case compares authoritative fields against a
separately compiled pinned original-core oracle. Tests include the exact retained
153,190,400-byte project candidate, own real LZFSE/IMG4 carriers, trailer-negative
controls, malformed/unsupported formats, decoder failure, memory/file bounds,
and inert/path/FIFO/symlink/private-output controls. The producer separately
reports 17 ASan/UBSan passes; that sanitizer result was not repeated by this
reviewer. No actionable finding remained.

The [new bounded REA evidence](../reverse-engineering/findings/boot-object31at/README.md)
locates compression and IMG4 construction call boundaries with 785 independent
instruction-word matches. Its finite report correctly withholds whole-function
semantics because of dead/truncated high-pcode. It neither proves which algorithm
or branch ran in Recovery nor diagnoses the installed carrier. The saved
postcondition report and this static evidence have distinct provenance and are
not promoted to firmware acceptance, SMP, GPU or performance results.

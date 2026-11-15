# Preserved 31AS postcondition discriminator

This original, standard-library Python observer explains which *saved*
31AR candidate predicates failed. It does not repeat the boot transaction.
31AS reached writer exit 0 but its candidate readback was refused at
`POSTCONDITION/POLICY_OR_OBJECT`. The independent boot021 restoration and
Macintosh HD desktop/default return were subsequently human confirmed.
Neither this tool nor that writer result proves firmware acceptance or SMP.

The next useful evidence is the preserved `baseline.json` and `candidate.json`,
not another reboot. No actual preserved state was read during development.

## Owner command, after independent review

Run from this repository's root in the M5's Macintosh HD Terminal, with the
administrator password entered only in Terminal:

```sh
sudo /usr/bin/python3 -I "$PWD/tools/postcondition31at/probe.py" --live
```

The only live target is the existing private transaction directory on the
already mounted lab Data volume. The tool does not mount it if unavailable.
It reads only the original public profile, own comparison key, enrollment and
spent markers, writer-exit record, target commitment, and saved baseline,
candidate and optional restored captures. It takes a nonblocking shared advisory
lock on the existing session lock. No file is created, modified, deleted,
copied, reset or overwritten; ordinary filesystem read/access-time semantics
still apply. It does not list the directory.

It does not run `diskutil`, `bputil`, `kmutil`, a writer, the boot-object reader,
any subprocess, or any network request. It makes no current policy/boot-object
query, Recovery admission check, firmware/security/Startup Disk change, or
installation attempt. Macintosh HD stays at its required Full Security.

No arguments prints `INERT`; `--help` prints static help. Both avoid the state
reader. Invalid options return only a fixed refusal, without echoing arguments.

## Interpretation and limits

`status: OBSERVED` means bounded capture files were securely read, decoded and
compared. It does **not** mean the candidate passed: examine
`candidate_phase_contract` and the finite Booleans in `candidate`.

The v2 report adds separate informational `candidate_classification` Booleans.
They distinguish a captured `NONE` selection from an `UNKNOWN` selection, and
captured lab CTRR `disabled` from `unknown`. They are deliberately outside the
candidate contract conjunction: a valid candidate has all four information
Booleans false. `NONE` means the collector recorded no custom-object reference;
`UNKNOWN` conflates a read/open refusal, unsupported carrier/codec, blocked
keybag, unknown decoded bytes or the explicitly excluded 31AI identity. It does
not identify which of those occurred. These classes are captured enum
comparisons, never raw policy flags or a fresh object/path query.

The first independently audited v1 source (probe SHA256
`8e3a32913ca94a55dae3e7fa82da097bd572acaba6f9f02dc4f1f0442cb37ff9`) was
preserved in ignored workspace build storage before this v2 change. The first
owner result remains v1 evidence; v2 does not retroactively add observations to it.

The candidate contract reproduces the frozen native functions:

- `parse_snapshot`: exact v2 keys, strict JSON/semantic types, Boolean guards,
  Original Full and CTRR enabled, lab Permissive, SMB contracts, unclaimed
  verification fields false, consistent selected-object exactness.
- `validate_snapshot(..., "candidate", ...)`: matching scope/profile/comparison
  key; an initial exact 31AF baseline; preservation of both roles' eight semantic
  fields and opaque private commitments; exact CANDIDATE payload; lab CTRR enabled.

The shape decoder separates well-typed guard changes from malformed schema so
the output can name a false guard without exposing its value.
`native_parse_contract` includes **all** native parse value/guard requirements;
`native_common_contract` additionally includes scope/profile/key binding.
The aggregate remains false whenever either native function would reject.
An invalid baseline is reported separately and prevents candidate acceptance.
Malformed JSON, duplicate decoded keys, unknown fields, noncanonical hashes or
semantics, missing required files, unsafe permissions or unstable evidence
produce a fixed refusal, never raw contents or exception text.

`restored.json` is optional. If present, its saved restored-phase predicates are
also compared with the baseline. `restored_phase_contract` refers only to that
capture. `rollback_verified` deliberately remains false: this observation does
not freshly verify the currently selected boot object, and does not supersede
the separately human-confirmed restoration.

Key SHA256 identity and role HMAC equality are computed/compared in memory.
There are no keys, HMACs, policy scalars, UUIDs, input paths, raw errors or private
field values in output. This tool neither recomputes private policy commitments
nor treats them as signatures over snapshot JSON. Snapshot v2 has no HMAC-domain
version field. The fixed 31AR profile pins the qualified helper lineage (31AO/v3
comparison extension), without inventing a new authenticity guarantee.
`target_commitment_format_valid` checks only canonical commitment framing;
`target_commitment_revalidated` stays false because fresh private target metadata
is outside this observer's scope. All `*_recorded` fields describe captured
claims, not a current revalidation.

Root-owned 0700 state, 0600 single-link regular files, descriptor ACL checks and
held/name-stable FDs protect reading the preserved evidence. The immediate
parent must have the expected owner, no group/other write bits and no extended
ACL. Every path component is walked without following symlinks and held until
final inode/stat stability checks. Ownership/ACL checks apply to the immediate
trusted parent, private state and opened files; ancestor components receive
no-follow/name/descriptor stability checks. Files are bounded to their required
small sizes or 64 KiB snapshots; optional-file absence is rechecked. ACL checks
are descriptor-only Darwin API calls. An active exclusive controller lock,
nonregular file, hard link, ACL, rename/replacement, mode or size change refuses.
These are evidence-access safeguards, not cryptographic snapshot authentication.

## Offline tests

```sh
/usr/bin/python3 -I tools/postcondition31at/test_probe.py
```

Synthetic fixtures stay beneath the checkout's ignored
`build/postcondition31at-fixtures`. Tests cover each native predicate, both role
semantic/HMAC comparisons, key/profile/baseline binding, malformed schema/JSON,
state/phase absence, private modes, symlinks/ancestors, hard links, wrong owner,
FIFO refusal without blocking, lock contention, ACL refusals, bounded reads,
replacement/change, optional restored capture, inert entry points and finite
private output.

The macOS-only differential test compiles `native_fixture.c` against the
**original pinned generated production-v2 31AR sources**, including qualified
31AO `state.c`, and calls only `parse_snapshot`, `load_comparison_key` and
`validate_snapshot` on synthetic workspace files. It independently compares
Python acceptance with the real native candidate predicate over the valid
control and per-field/semantic mutations. It never dispatches production CLI
modes or queries hardware. The source pins are checked before compilation.
Generated binary/fixtures are removed after tests. A non-macOS run explicitly
skips the Darwin ACL integration and native differential class.

No prior controller, writer, helper, production profile, consumed state,
bootstrap, page, or frozen source input is changed.

# 31AN: identify the policy-schema blocker before another Recovery visit

## Decision

Review of M1 commit `2a28915` confirms that 31AM's conditional read-only
Preboot preparation and cleanup worked. The next repair belongs to our policy
reader. Obtain the missing field-category observation from the current macOS
desktop first. Do not change parser acceptance from a byte count or send the
user through another blind Recovery check.

## Evidence and limits

The physical result is recorded in
`native/boot/attempt31am-recovery-2026-11-14-result.json`. It reports initial
`UNMOUNTED_EMPTY`, an owned mount, verified read-only state, mount/unmount exits
0/0, cleanup `UNMOUNTED` and no mount-state uncertainty. The nested diagnostic
then refused `LAB_POLICY / FORMAT / UNSUPPORTED_METADATA`; its policy-display
command succeeded and returned 2,822 bytes. Snapshot collection and admission
did not complete.

**Confirmed from our source:** the frozen parser in
`tools/boot-object31aj-native/state.c` emits that refusal for either a non-absent
protected auxiliary field (`auxp`, `auxi`, `auxr`, `prot`, `hrlp`, `losv`) or a
four-character tag outside its supported sets. The finite physical output
does not identify which branch, tag or token was involved. A successful display
command is not successful policy admission.

**Unknown:** the actual rejected field, whether the desktop reproduces the
Recovery schema, and any later Original-policy, final pairing/security or
selected-object result. This result contains no Aura/Linux entry, CPU-startup,
GPU or performance observation. It provides no new evidence of an Apple-only
firmware barrier. Boot021 restoration remains outstanding. M1 records human
confirmation of Macintosh HD desktop and default restoration; no repeated
routine security-mode command is requested.

## Why observe, rather than ignore, the metadata

[Apple's LocalPolicy documentation](https://support.apple.com/en-ca/guide/security/secc745a0845/web)
describes protected pairing/version and auxiliary-kernel metadata. Presence of
such a field is not sufficient evidence of a misconfiguration. The reader's
absence-only assumption may be too restrictive, but accepting arbitrary data
would weaken its comparison guarantees.

[Asahi's public boot-policy catalog](https://github.com/AsahiLinux/docs/blob/main/docs/fw/boot.md)
also lists the Boolean tags `lobo` and `love`, which the frozen reader does not
handle. They are candidates for observation, not the established cause.
The installed `bputil(1)` manual documents `-j` as a display-only JSON mode.
Its actual JSON structure is not yet qualified for native admission.

No new proprietary disassembly or decompilation was needed for this diagnosis:
the rejecting branches are our own code. If static analysis of the formatter
is subsequently needed to qualify an observed type, use the existing local
REA workflow and keep Apple bytes and decompiler output out of Git and reports.

## Implemented desktop observation

`tools/policy31an/probe.py` is an original, standard-library-only tool. Default
and help are inert. Explicit `--live` requires root, Darwin, the exact model,
current Original and the frozen target/volume guards. It hash-checks its
dependencies and admits the existing 111-source closure before loading them.

For each lab and Original group it performs one bounded text policy display
and one display-only JSON request. It returns only fixed known field names,
presence/syntax classes, aggregate unknown counts and catalog-key JSON types.
Unknown names, raw text/JSON, identifiers and policy values are never returned
or saved. Each policy capture is bounded to 20 seconds and 65,536 stdout bytes;
stderr is drained and discarded. A fresh target observation after the reads
must match the original private binding. Interruptions stop further queries.
Unexpected exceptions produce a fixed redacted refusal without a traceback.

The schema scanner follows the native row grammar but is deliberately **not
native admission**. It reports an unsupported candidate only. It does not
evaluate all earlier native semantic checks, and it does not misclassify the
two legitimate ordered `rpnh` rows as a duplicate error. A failed JSON display
does not erase a useful text observation. All public readiness, admission and
parser-change flags remain false.

## Validation and current execution status

- 20 focused synthetic/mocked tests passed in the producer's run and an
  independent audit run. The audit found no remaining actionable issue.
- Tests cover grouping, all three unsupported categories, redaction, legitimate
  repeated metadata, JSON duplicate/depth/node bounds, immutable dependency
  loading, fresh identity re-observation, interruption and exception redaction.
- Existing native/capture suites were reused, not rerun. No native collector,
  profile, kit, page, consumed state or candidate was edited.
- A noninteractive local `sudo` attempt stopped for authentication before the
  probe executed. The owner-run desktop observation is pending. No policy
  value, identifier, mount, boot-object or setting change was produced.

## Next implementation, conditional on the observation

1. If a known published field reproduces the unsupported category and its type
   is qualified, add only that typed field in new generated source. Preserve
   the old 111-source closure and keep all other refusals.
2. Store presence and canonical values in the private `Policy` struct so the
   existing before/after comparison includes them. Distinguish unseen,
   explicit absent and Boolean states. Reject duplicate and malformed rows.
3. Extend the keyed private metadata commitment with tagged, separated fields
   and a new domain. Do not silently omit new fields from future transaction
   comparisons or reuse old snapshots/keys/state. The public snapshot need
   not expose their values.
4. Prove the anchored extension reverses to the exact frozen generated source.
   Test mutation detection, malformed/duplicate refusal, domain separation and
   unchanged Original Full/lab security, pairing and target guards. Retain the
   physically successful 31AM Preboot engine unchanged.
5. If the desktop does not reproduce the field, or returns only an uncatalogued
   category, keep the cause unknown and obtain another bounded schema fact.
   Do not add speculative acceptance, install anything or schedule a restart.

A later read-only companion success would qualify collection only. Installing
the matched Aura/kernel and checking native entry/all 18 cores still require
their own demonstrated transaction and physical result. Performance parity
remains the objective, not a conclusion from parser or build tests.

# 31AX: closed policy transition and independent functional rescue

November 15, 2026. Original offline design following M1's `d679622` review of
31AW. No live policy, private state, selected object, owner or device was queried.
This is a review contract, not installation or restart authorization.

## Evidence that constrains the design

M1 passed both 52-method AW suites and its standalone codec controls, while
retaining the native hold. Those fixtures do not qualify a policy reset.

Apple's [LocalPolicy field documentation](https://support.apple.com/en-ca/guide/security/secc745a0845/web)
distinguishes global LocalPolicy nonce rotation (`lpnh`) from RemotePolicy/Find My
changes (`rpnh`), Recovery updates (`ronh`), and OS/cryptex identities or generation
(`nsih`, `spih`, `stng`, `love`). Any LocalPolicy change can re-sign all policies
with a new `lpnh`. `vuid` identifies the APFS group; `kuid` is a KEK context, not
a user's identity. `coih` identifies the custom boot object. These distinctions
do not establish what this target's reset will actually produce.

The installed `bputil(1)` manual, independently checked by both Macs, documents
Permissive reconstruction separately from the CTRR-disable option. Reconstructing
without that downgrade is a meaningful hypothesis. It is not enable-only and
does not guarantee preservation of a previous policy's signed bytes.

AW's current stable commitment includes remote/recovery/cryptex data and its six
typed extra fields. It intentionally omits `lpnh`. However AW recognizes but
does not retain/type-check/count the identity tags `BORD`, `CHIP`, `ECID`, `vuid`
and `kuid`. AX must close that gap rather than claim the old snapshot already
binds those values. Existing APFS/role commitments remain required.

## Closed field classes

Every observed tagged row must belong to the finite qualified catalog, have its
qualified type and multiplicity, and be stable during each individual snapshot.
Reject unknown tags, conflicting/duplicate singleton rows, overflow, malformed
UUIDs/hashes/counters and unsupported security options. Private values stay in
memory or role/profile/key-bound commitments; public results expose only classes.

| Class | Fields and exact rule |
| --- | --- |
| Persistent target identity | Container, Lab System/Data, Original System, Preboot and volume-group identities keep the pre-reset APFS/role binding. Names or disk numbers alone are insufficient. |
| Typed policy authority | `BORD`, `CHIP`, `ECID`, `vuid`, `kuid`: required, canonical bounded types, preserved against the pre-reset role anchor. Bind each `vuid` to its observed APFS group; do not assume `kuid` equals `vuid`. CHIP must match T6050. Reject changed authority in strict and rescue paths. |
| Other stable policy properties | `CEPO`, `SDOM`, `CPRO`, `CSEC`, `lobo`: preserve the pre-reset role commitment. Original's `nsih`, `coih` and all other protected fields remain anchored too. No firmware, OS or boot-owner migration is authorized. |
| Strict reset protected data | Lab `rpnh` vector, `ronh`, `spih`, `stng`, `love`, and `nsih` remain equal to the pre-reset contract to admit a candidate baseline. A changed value is an unqualified transition, not automatically a normal reset effect. |
| Authorized issuance | Type-check `lpnh` without requiring value equality across writers, for both roles; signatures/envelope bytes can also be reissued. Never rebase Original's protected anchor. Lab `coih` may be retained/cleared during reset and replaced by the exact candidate or boot021 during their respective enrollment phases. |
| Security state | Original remains Full with CTRR enabled and its pre-reset semantic vector unchanged. Lab is always Permissive; only the phase-specific CTRR downgrade may vary. No extra downgrade or auxiliary trust may appear. |

The required row counts must follow a qualified formatter contract. The prior
public shape has two `lpnh` and two `rpnh` rows in distinct rendered contexts;
preserve bounded order/context and exact counts rather than accepting unlimited
duplicates. A synthetic fixture with a shorter hash is not evidence for widening
the real hash grammar. An omitted optional row may mean absent only where the
formatter's omission rule is qualified; unknown omission is not authorization.

For Lab admission, `smb2`/`smb3`/`smb4`, `sip1` and `sip3` must mean no downgrade,
and `sip0` must mean zero/default. A known false-versus-absent or zero-versus-absent
default representation may normalize to the same non-downgraded meaning. This
does not permit arbitrary values. Require known auxiliary fields to be absent;
do not reset away an existing trust configuration and pretend to restore it.
Original's pre-reset semantic anchor does not receive this Lab-only rebasing.

Owner authentication is delegated to Apple's foreground authenticator for the
bound Lab group. KUID and filesystem ownership are not a human owner identity.
Without a separately qualified owner-set collector, report this scope honestly:
reject changed authority context, and let Apple reject unauthorized credentials;
do not invent a live `owner_verified` Boolean from fixture data.

## Phase and durability contract

1. **Enroll the pre-reset anchor.** Verify exact boot021 and disabled Lab CTRR,
   safe Lab options, target/authority binding and Original Full/protected state.
   Durably retain the new profile, key, Original anchor, Lab stable contract and
   target commitment. Authenticate the persisted pre-reset snapshot's protected
   commitments and labeled semantic vectors along with its typed identity/manifest
   contract; require the strict initial validator to force all remaining fields.
   File permissions or valid JSON alone must not permit a changed baseline to
   rebase Original's protected data.
   Never adopt or reset an earlier transaction.
2. **Spend reset once.** Recheck the same preconditions immediately before the
   fixed lab reconstruction writer. Persist its one-shot intent before dispatch.
   Capture its exit and post-readback even when the writer fails or is interrupted.
   No timeout or missing output authorizes retry.
3. **Admit a fresh candidate baseline only on the strict path.** Require enabled
   CTRR, exact target/Original invariants, no extra Lab downgrade, and the strict
   field-change contract above. Persist the separate post-reset Lab observation
   and its readiness marker last. Missing/refused/undurable readback cannot reach
   candidate installation.
4. **Install only from that ready baseline.** Require successful codec controls,
   exact candidate bytes, enabled CTRR, and the bound Original/Lab contracts.
   Reissued `lpnh` never becomes an equality requirement for a subsequent writer.
   A candidate cannot borrow admission from the rescue exception below.

## Functional rescue before a fresh Lab baseline exists

The independent restore entry loads the durable **pre-reset** anchor, key,
profile and exact boot021. It requires neither a post-reset baseline nor a
candidate file, successful compressed decoding, or a reset retry. A selected
object that is absent, unreadable or unrecognized is not itself a reason to
block raw restoration; policy/authority/Original reads still must succeed.

For rescue only, root's selected contract permits typed differences in the
closed Lab set `rpnh`, `ronh`, `spih`, `stng`, `love`, `nsih`, `coih`. Classify
these as **unqualified observed transitions**, not proved reset effects or recovered
old metadata. Everything outside that set and documented issuance remains bound
to the pre-reset stable/security contract. No unknown tag, unsafe option,
auxiliary trust, changed hardware/VUID/KUID, or changed Original anchor is admitted.

Durably bind the currently readable rescue observation before writing. Freeze its
protected Lab values across the rescue writer sequence; only `lpnh`/envelope,
the conditional CTRR change and the raw object's reference may change by phase.
One narrow final raw-enrollment exception may recover an **absent** current
`nsih` to the exact pre-reset, already committed nonempty Lab manifest. It may
not replace a different nonempty current manifest or admit an arbitrary new
manifest. The CTRR-only preparation must preserve the current manifest.
If already exact boot021 with disabled CTRR, perform no writer. Otherwise use
the conditional existing CTRR-disable preparation and one exact raw boot021
enrollment. Never invoke reset or candidate installation from rescue.

Final success verifies **exact boot021 payload and disabled Lab CTRR**, continued
Original protection, authority/target binding, current rescue-field preservation,
and owned cleanup. It explicitly does not verify restoration of old Lab policy
bytes, signatures, hashes, version/generation data or Find My/Recovery/cryptex
semantics. The result must retain that limitation even if all final flags pass.
If any required policy/authority/Original read is unavailable, refuse further
writers and request the separately reviewed manual Recovery rescue. Filesystem
copies are not a signed-policy restoration procedure.

## Required fault cases before proposing hardware work

| Injected condition | Required outcome |
| --- | --- |
| Reset succeeds, first policy read fails; or strict reset admission rejects a permitted rescue-class delta | No candidate baseline/boot; independent restore uses the pre-reset anchor and a later valid current observation. |
| New Lab baseline save/fsync/ready-marker publication fails | Candidate stays unavailable; rescue does not need that baseline. |
| Reset writer returns nonzero, times out or is interrupted after changing state | Preserve spent intent and readback; no retry; independent functional rescue remains available if its own guards pass. |
| Current Lab `rpnh`/cryptex/version/manifest differs but authority/security/Original remain valid | Strict candidate admission refuses; rescue records finite changed classes and freezes current data across its own writers. |
| Original protected data, Full/CTRR state, target/group, typed VUID/KUID/hardware, or safe Lab option contract changes | No reset, candidate or rescue writer; manual Recovery handoff. Global typed `lpnh` rotation alone is distinct from these failures. |
| Candidate missing, codec capability fails, selected file missing or malformed | No candidate installation; exact raw boot021 rescue can proceed under independent guards. |
| Crash after spending a rescue writer, stale baseline/key/profile, foreign mount or failed cleanup | Preserve evidence and consumed markers; no automatic replay, reset or assumed success. |
| Valid-shape pre-reset snapshot content changes while the typed-view file remains intact | Authenticated anchor binding refuses load; no writer or rebase. |
| Current rescue NSIH is absent | Final raw enrollment may recover only the exact pre-known manifest; other nonempty replacements refuse completion. |
| Rescue writer changes another protected current Lab field or final payload is unknown | Refuse completion; report actual state and cleanup outcome, with no native boot cue. |

Offline fixtures establish control flow and refusals only. Whether the one Lab
reconstruction produces enabled CTRR still requires a separately authorized,
bounded physical observation. Nothing here establishes an Apple-only blocker,
native Linux readiness, or performance parity.

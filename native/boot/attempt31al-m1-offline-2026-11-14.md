# M1 independent 31AL offline review — November 14, 2026

**OFFLINE_PASS_LIVE_DIAGNOSTIC_HELD.** Reviewed main `483dab6`. No actionable
finding in the new diagnostic, renderer, controller or staging boundary. This
is a diagnostic-only preparation; no install retry or physical visit occurred.

## Fresh verification

All **92** source inputs are tracked and hash-exact before and after review;
all **72** retained 31AK bindings remain unchanged. Inventory SHA-256:
`f62824f3dd91fdce6179f064d6c1582bbecace6a3b4efd884eae89969a91292c`.
The supplied two-file kit is present and exact:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| ilinux31aj-reader | 106416 | 5c30802f6cf6821588e4f8fd22e8cb179b00ae84cbf8316448c043bbcf543a00 |
| profile.json | 823 | 1e33fd7824f5f89aab8b7e06209b7736c4ff7c5067d87d6744019c36a4fb06bb |

The public profile equals Git bytes. Only these two already-delivered files were
copied into the clean checkout's ignored build tree because preparation requires
checkout-contained paths. The pinned production helper was not executed or
replaced by a locally compiled binary. No candidate/rollback/root was transferred.

Ran the requested **86 unique methods**, `python3 -I` under `caffeinate -i`;
command-local TMPDIR was inside the workspace, including disposable shell/stage
fixtures. No global configuration was changed.

| New suite | Methods | Result | Seconds |
| --- | ---: | --- | ---: |
| native diagnostic | 29 | PASS | 2.668 |
| renderer | 19 | PASS | 29.768 |
| package | 14 | PASS | 1.842 |
| staging fixtures | 24 | PASS | 2.334 |

M1 used Python 3.9.6, Apple clang17.0.0 and SDK26.0. Native tests compiled and ran
only original synthetic controls. The generated source proof passes: core/json/
header are byte-identical to the frozen inputs, and stripping diagnostic marks
reproduces the exact original state source. Tests exercise real original
collector/parser/validator behavior with synthetic CF fixtures and own child
processes; no live Recovery/disk/policy backend ran.

Actual inert page preparation PASS; receipt equals M5's preparation record.
Socket-free page check likewise matches M5. The one full block passes `bash -n`.
All three generated size/hash pairs are exact:

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| diagnose-paste.txt | 5342 | 6c4ba0d76e85774e9968a80f04dd70a5e734d9fd2357c7fd490552fe9b7e7000 |
| profile.json | 823 | 1e33fd7824f5f89aab8b7e06209b7736c4ff7c5067d87d6744019c36a4fb06bb |
| recovery.html | 7755 | 824708ed2e0da1991f1a5fbf7870597aca7dc1aaf554622c5a33b17a6e36b835 |

## Source, privacy and guard review

Diagnostic wrappers evaluate each original predicate once and retain its boolean
result and short-circuit order. Observation updates are separate from original
collector state; a first capture failure retains its stage/exit/byte count even
if the unchanged original flow issues a later command. The stripping proof,
macro review and new controls support guard preservation, not a claim that real
Recovery admission now succeeds. Command deadlines/caps and strict pairing,
security, target identity, no-follow and consistency predicates are retained.

The helper CLI exposes diagnosis, synthetic fixture diagnosis and strict safe
record validation only. No full-snapshot, private-group, RNG/key, installation,
restoration or write-authorizing CLI is available. The 16-key native schema
contains finite enum labels, bounded command outcome/count and fixed false
privacy/readiness/authorization flags. It prints no raw policy, identifiers,
private paths/keys, arbitrary unknown metadata or unknown-object hashes. The
validator reconstructs allowlisted output; malformed/private/oversized input is
not echoed. A valid refusal can validate with exit0 while diagnosis returned2;
that is display validation, not target admission or permission to write.

The shell distinguishes input/work/output-open/child-exit/missing-output/validator
failures. Only one diagnosis and one validation command appear in its one-box
page. It checks the held canonical work directory, uses noclobber capture,
suppresses raw stderr/signal diagnostics, prints validated finite output before
fixed-file cleanup, and has no persistent transaction directory or install/
restore command. Existing old kit/state are not touched by the diagnostic block.
A passing INITIAL_ADMISSION_PASS remains read-only and native_ready false.

The controller admits exact retained/new source and build/delivery/profile
bindings before loading new modules. Its separate future --stage mode receives
already-verified controller functions rather than importing a mutable controller
path. Staging fixtures forbid constructing the production LiveBackend, retain
original metadata/FileVault/current-original guards, and cover no-overwrite,
source/name/descriptor replacement, before/after target checks, private modes,
partial-copy cleanup and foreign/old-state preservation. No production staging
or administrator authentication was requested or run on M1.

## Reuse, preservation and limits

Unchanged prior suites and Linux/Aura builds were not rerun. M5's build/clean
Git-export/production self-bound control and 29-method ASan/UBSan result were
reviewed as producer receipts; those producer runs were not reproduced on M1.
The fresh M1 normal synthetic compilation is not the delivered production build.
No Apple inspector, REA, VM, raw policy collection or hardware query was needed.

All **54** snapshotted existing kit/page/review/session/receipt files remain
hash-exact, including retained intake receipts and the completed 31AK ledger.
Older frozen source, binaries, pages, unfinished notes and consumed state remain
untouched. No reset/re-arm, service, camera, proxy, Mac restart, security/volume/
default operation or native attempt. Boot021 restoration remains outstanding;
prior configured contained EXACT_31AF is not a fresh query. Prior Macintosh HD
return/default confirmations remain the completed 31AK visit's evidence.

**31AL lab staging / live Recovery diagnosis / native Linux / SMP / performance:
NOT RUN.** The reviewed inert diagnostic page is ready for a later explicitly
started staging/read-only Recovery sequence. That visit must only collect the
finite safe result and return to Macintosh HD/default. M5 interprets it before
any new install proposal; real guard refusals stay stops. This review starts no
server and supplies no physical execution authorization.

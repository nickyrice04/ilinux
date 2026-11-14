# 31AK Recovery result — November 14, 2026

**RECOVERY_CAPABILITY_PASS / INITIAL_SNAPSHOT_REFUSED_BEFORE_ENROLLMENT.**
The single corrected install-block invocation stopped before baseline creation or
boot-object/policy mutation. No native observation occurred. M5 owns further
offline diagnosis; do not repeat a phase, modify flags or bypass a refused guard.
Original desktop/default return for this visit is pending human confirmation.

## Photo-confirmed result

The human confirmed the lab Recovery browser and was guided through the new 31AK
install box once. The supplied Recovery Terminal photo shows:

* `RECOVERY_CAPABILITY_PASS`, with recovery_execution_admitted true;
* target_state_verified false, target_state_requires_snapshot true;
* read_only true, writes_authorized false, native_ready false;
* `STOP: initial guarded admission snapshot.`;
* `PRE_ENROLLMENT_STOP`, stating no boot or policy command was attempted and
  warning against blind restoration without its persisted baseline/key.

The prompt returned. Numeric helper/block exits were not reported. There is no
emitted CANDIDATE READBACK VERIFIED result; that text higher in the photo is the
pasted source of a later statement. No kmutil installation confirmation is shown.
Media was inspected in chat, not copied into Git or uploaded.

## What advanced, and where it stopped

The actual Recovery capability PASS establishes that this invocation passed
profile/executable binding, the root/model/CDIS Recovery check and the synthetic
compression control. Thus the corrected physical work-directory path cleared
the earlier 31AJ capability blocker in Recovery. This is useful execution
evidence for the procedure correction, not target-state or Linux readiness.

The reviewed block then checks absence of transaction state and invokes
`observe_admission`. That function checks the work binding and calls the helper
with `--snapshot`, the fixed lab/original paths and profile; stdout is redirected
to the owned temporary snapshot file. The observed STOP means this collection
step returned nonzero before the separate initial-admission validator.

Snapshot collection spans Recovery/path checks, disk/APFS volume/role/container
and mount metadata, policy parsing and pairing/security checks, selected-object
inspection and repeated-policy consistency. The photo does not distinguish
these branches, a work-binding failure, or snapshot-output creation failure.
**Exact cause: Unknown.** Do not diagnose a policy downgrade, firmware/CPU fault,
unsupported metadata shape or a second symlink solely from this generic failure.
The capability JSON explicitly says target state still needs a snapshot.

The snapshot helper is read-only but may have issued disk/APFS and policy reads
before failing; which commands ran is not captured. No fresh target pairing,
Original Full/lab Permissive result or selected-object identity was established.
Do not turn capability admission into a claim of successful target admission.

## Mutation boundary and evidence limits

This call precedes initial-admission validation, state-directory creation,
comparison-key generation, saved baseline/profile, mutation markers and kmutil.
Consequently enrollment and policy mutation were NOT REACHED by this invocation;
no new persistent transaction baseline/key was created by it. The initial
transaction-absence check preceded the reported failure. This is source-derived
control-flow evidence, not a new raw-state listing on M5.

The helper command is configured to redirect stdout to temporary snapshot
output, so any helper refusal would not be shown directly. The photo does not
establish whether the helper ran or the file was created. Fixed-file EXIT
cleanup includes snapshot.json; contents and cleanup were not independently
captured. Do not claim that a detailed reason or raw diagnostic was preserved. M5 should review
bounded, sanitized stage-specific diagnostics and pre-enrollment evidence
retention offline before proposing another execution. No additional live helper,
metadata collection, state change or in-session retry was requested.

| Step | Result |
| --- | --- |
| Corrected install-block invocation | One observed invocation |
| Recovery capability / profile and codec control | PASS, photo-confirmed |
| Initial guarded admission snapshot | FAILED; branch Unknown |
| Separate initial-admission validation | NOT REACHED |
| Transaction baseline/key / candidate mutation marker | NOT REACHED |
| Candidate install / boot-policy mutation | NOT REACHED |
| Candidate readback | NOT REACHED |
| Native / Linux / SMP / performance | NOT RUN; zero native windows used |
| Independent restoration | NOT RUN; no new baseline available |
| Macintosh HD desktop/default return for this visit | PENDING human confirmation |

Boot021 restoration remains outstanding. The last supplied M5 object observation
was configured contained EXACT_31AF; it was not re-queried in this session.
Earlier Macintosh HD desktop/default confirmations belong to the prior visit
and are not reused as this visit's return. Full Security on the original remains
the required invariant; no new mode-verification claim is made.

## Preservation and handoff

All 72 frozen source pins and the four reviewed generated file size/hash pairs
remain exact. No source/helper/candidate/profile/page repair, test-suite rerun,
rebuild, resend, restage, state deletion or receipt re-arm. Earlier unfinished
notes and consumed receipts are preserved. The verified fixed-page server was
stopped after the refusal, exited 0, and was not restarted. Camera stayed off;
no M1 restart, USB/proxy or native boot cue occurred.

Authorization 6133859 and handoff bbeb4a3 were read; the failed guard ends this
invocation without an automatic retry. Return through the startup picker to
Macintosh HD and confirm desktop/default separately. Do not run restoration
blindly for this pre-baseline failure. M5's next step is offline investigation
and an evidence-based proposal, not another boot or security change.

# M1 review: 31AJ offline foundation and plan

2026-11-13. Reviewed commit `2dd9948af978998bb7acbbbf35ad4e2e2e0c8dd9`.
Result: **PASS_COMPONENT_ONLY; NATIVE_HOLD**. No actionable issue found in this
component review. This is not approval of a Recovery transaction or native kit.

## Independent checks performed

- Seven entries in `attempt31aj-source-sha256.txt`: PASS.
- `caffeinate -i python3 -I tools/boot-object31aj/test_payload.py`: 36 methods
  PASS. These use original synthetic data and explicitly injected test codecs;
  no live object, Apple binary or native code is executed.
- Source review of the new identity primitive, tests, README and proposed plan.
  Literal 31AI size/hash agrees with the frozen candidate manifest; 31AF and
  boot021 bindings agree with the pinned existing reference reader.
- Frozen 31AH 41-entry and 31AI 46-entry source inventories: PASS unchanged.
  No old full suite, binary intake, camera calibration or hardware query rerun.

The primitive compares complete bytes and digest, bounds raw/compressed sizes
and shallow DER fields, refuses malformed/trailing data, and sanitizes output.
Compressed decoding requires an explicitly trusted provider with size, input
consumption and EOF checks. These checks do not constrain a hung or dishonest
provider. Exact payload identity never sets selection, wrapper authenticity,
policy, restoration, bootability or write authority true. UNKNOWN can exit zero;
future callers must use the explicit status and identity, not process exit alone.

## Evidence reused and limits

M5's actual raw 31AI/31AF/boot021 fixture results are recorded in its offline
receipt; those actual-fixture runs were not reproduced in this review. Existing
31AI artifact-integrity and camera evidence are reused. The CLI ships no codec
or live mode, and actual compressed candidate verification is still UNKNOWN
without a real codec. Recovery compatibility, selected-object provenance and
the final transaction are not established by the synthetic tests.

The plan incorporates M1's camera/text/brightness limits and uses the actual
contained 31AF starting state. Final boot021 is the intended final restoration,
not a claim of returning to the initial 31AF bytes. A separate raw boot is not
needed solely to fit the old assertion model. Entry, permissions and physical
SMP are experimental questions, not prerequisites that must already be proved
before an otherwise concrete reviewed experiment.

M5 next completes the bounded real codec and Recovery adapter, new transaction
model and guarded install/independent restoration blocks with full object,
CTRR, unrelated-policy and default postconditions. Command/policy semantics
remain part of that future review; this review validates no live command flags.
Readable summary changes require a new pinned root/candidate and focused tests.
Review changed material only; preserve old closures and consumed approvals.

## Session boundary

No camera session, restart, proxy/USB, live target query, VM, installation,
security/volume/default operation or native test occurred. No new download or
host dependency was needed. The original checkout's unfinished notes and
unrelated files were preserved by using the clean isolated checkout.
Native/live tests **NOT RUN**; **no restart ready**. No new physical authorization
is inferred from this software review.

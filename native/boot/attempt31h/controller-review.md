# 31H controller review

Scope: one CPU1 research campaign using existing boot021 and existing lab
setup. Native31H **NOT RUN**. No new installed object or Linux image.

Reviewed the matching-board REA findings, public m1n1 access paths, pure
observers, inherited31G lifecycle, native adapter, source closure and supervisor.
The next physical test is justified as an exploratory observation; no missing
startup operation was established. Register semantics/safety are not inferred
from an ADT extent or successful VM execution.

## Changes and invariants

- Reset mirror observations reuse the existing two read64/exception-ack pairs.
  Firmware-format relations and unknown fields remain sanitized. Unequal
  mirrors, unexpected field destination or unexplained bits refuse before any
  mutation. Effective reset destination remains unknown even on a match.
- Exact18-core census binds CPU0/CPU1 implementation windows and extents; both
  are in the same active cluster. New translation checks require identity
  Device mappings, with the existing EL1 or EL2/VHE access regime.
- At most8 additional32-bit reads: two guarded baseline accesses before any
  start intent, then six fixed-helper accesses. The helper bytes are unchanged
  from31G; no global guard manipulation is added after startup.
- The tracker publishes intent, validates before commit, preserves partial
  prefixes and freezes on error. Only low bytes/comparisons survive. A local
  finally refresh preserves the terminal journal-failure flag without another
  target call or journal retry.
- One-second pair deadline checks surround reads and diagnostics, including
  immediately after a returning read. An overdue read cannot dispatch another
  diagnostic request. Existing60/65/90-second outer bounds cover stalls.
- PS failure prevents the added observation. Only natural arrival expiry
  permits a final pair; faults and observation deadlines do not. A final error
  is retained alongside the original arrival-timeout reason.
- Same two CPU1 startup writes, RAM recorder, permission/cache publication and
  whole-text verification. No cold-entry redirect, RVBAR/PS/stop/security write,
  remap, extra core or Linux continuation. Success still needs complete entry,
  independent arrival/identity,8 callbacks, progressing counter and final park.
- 31H has distinct token/receipts. Supervisor and controller check complete
  source closure; consumed31A–31G files/receipts remain unchanged. Source
  manifests cannot omit inherited code or newly added observation code.

## Review findings resolved

Independent review identified a stale copied journal-failure flag and a
post-deadline diagnostic call. Both are fixed and covered by controller
regressions. Earlier tests also exposed incomplete fault injection in the fake
register model; the injection now sets the actual diagnostics RAM field.
Transport errors are sanitized while fixed controller deadline/exception
reasons survive. No private failure details enter public summaries.

No blocking code issue remains after these repairs and final offline checks.
The physical access has documented uncertainty: a synchronous guard cannot
contain every possible asynchronous fault or bus hang. No recovery/retry policy
pretends otherwise. The human return procedure remains mandatory.

M1 must independently pass offline intake, publish readiness and wait for the
human's fresh lab start. Offline PASS is not native compatibility. No CPU speed,
all-core operation or performance improvement is claimed.

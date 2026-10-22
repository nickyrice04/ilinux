# 31J review scope

Native31J/CPU1/Linux SMP NOT RUN. Release concerns the M1 connection boundary.
Existing31I CPU Controller methods and every target transaction are inherited;
new wrapper owns31J dispatch, confirmation, journals and source bindings.

Pre-open cached enumeration is bounded to4 queries/15s, each at most3s,1s between
only absent/empty results. Malformed metadata, query failures, ambiguous identity
and path failures stop. Strict
primary/lstat/source verification precedes native consumption and one serial-open
attempt. No target operations occur in the discovery module or supervisor.

Invocation reservation is not native consumption. Separate connection evidence
survives discovery failure; the consumed journal is exclusive and created only
after readiness. All previous sources/receipts remain frozen. Late source changes,
callback/journal failures, outer deadlines and interrupts must not open serial,
issue another query or trigger a target retry. Private paths and exception text
are never serialized. Missing CPU counters are not replaced with zero values.

The60s connection/native deadline includes discovery and finalization, within
the independent65s child-process deadline; no extended human90s window. Return to
Macintosh HD on every outcome. No image, installed boot021, boot policy, volume,
firmware or macOS change. The remaining inability to prove physical enumeration
from offline checks is explicitly documented, as is unverified CPU1 execution.

Review and test results are recorded in validation.json. New tests cover the
previously untested host discovery boundary and compare31I/J target traces.

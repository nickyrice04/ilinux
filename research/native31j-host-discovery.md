# After31I: fix host discovery before another CPU experiment

2026-10-21 Eastern. Native31J **HOLD / NOT RUN**. This work performs no USB open,
proxy request, boot/security change or target mutation.

## What the result establishes

M1 report `native/boot/attempt31i-2026-10-21-result.md`, commit `dec2f89`:
31I returned STOP / connect / InvalidFileException in0.099s, supervisor0.526s,
with a normal Macintosh HD return confirmed+35.607s. No completed Controller construction or preflight result was available. No new
reset-gate, PS/core-state or entry observations exist. Startup/mutation counters are absent, not measured zeros.
The correct reset predicate from31I remains untested on hardware.

## Confirmed software gap; probable cause remains qualified

The frozen host discovery calls `plistlib.loads()` on captured `ioreg` stdout.
Its empty-output case is unhandled. The31I intake runs26 suites but none is
`test_usb_identity.py`; its wrapper tests mock discovery and selection, and
its real-client VM tests begin after those stages. The historical discovery
suite has only a valid synthetic-plist subprocess case. Thus hundreds of CPU
and protocol checks did not exercise this host boundary.

**Observed on M5, read-only:** the production cached-registry query returned
exit0, valid plist/list,2 roots,60851 stdout bytes and zero stderr bytes. The same
query with a deliberately absent fixture class returned exit0 and exactly zero
stdout/stderr bytes. The old parser raises InvalidFileException on that result.
Only counts/classifications were retained; no actual registry properties or
identifiers were saved or published. No serial device was opened.

**Confirmed public-source behavior:** Apple's [ioreg source](https://github.com/apple-oss-distributions/IOKitTools/blob/main/ioreg.tproj/ioreg.c)
initializes the search result to no object and creates a result array upon a
match. Its archive-output path serializes only when a result object exists;
normal completion exits0. This explains how a successful no-match query can
produce no plist at all. The source corroborates the local experiment; it does
not identify which bytes the M1 returned during31I.

Historical attempts17 and18 recorded the same exception with no proxy device
visible; the human's cable move/reseat preceded successful enumeration. These
are useful precedents, not proof the31I cable, port or controller failed.
Actual31I stdout and traceback were not retained. Empty query output is a
**likely** explanation, not an established cause. A malformed nonempty plist,
valid empty list, absent primary interface and command failure remain distinct.
No new REA session is needed for this host bug: public source and repeatable
read-only observations provide direct evidence. Firmware findings stay unchanged.

## Work completed and next release boundary

New `tools/m1n1-client/usb-discovery31j.py` is a host-only diagnostic, separate
from all frozen sources. One fixed cached IOService query, bounded15s, raw
output held only in memory. It reports fixed query/parse/shape/identity/path
categories and counts, never registry data, callout paths, arbitrary exception
messages, raw stderr or a hash of identifying registry data. No automatic
retry, guessed port, prefix-stripping fallback or handshake exists.

Default mode diagnoses the helper environment with M5 still in macOS. Target
absence is expected in that state and is not CPU/link readiness. Optional
`--require-primary` additionally requires the exact m1n1 VID/PID, data interface1
class0x0a and a character-device callout; it still opens nothing. `native_ready`
is always false. A discovery observation is a snapshot, not a reserved device
or guarantee that a later serial open will succeed.

**Validation:**19 new synthetic methods and16 historical identity methods PASS
on Python3.9.6, with independent review. One actual M5 cached-registry diagnostic
returned valid XML, classified zero primary candidates, native_ready=false and
zero opens/target requests. No raw registry was retained. This validates the
host-tool path only; M1 classification and native behavior remain untested.

The current release contains **no native31J controller or live instructions**.
M1 can run the host-only check now, without another M5 restart. Once that report
is available, prepare a separately pinned31J wrapper that preserves31I's entire
CPU experiment and records precise connection-stage evidence. Include discovery
and wrapper error-path suites in its intake. In the later fresh proxy session,
verify discovery before consuming the native experiment, within the same human
90s window. No repeat CPU start, reconnect or fallback after native execution.

## Planned efficient next attempt

1. Now: M1 runs the new tests and one default host diagnostic while M5 stays in
   macOS; publish sanitized JSON and exit code. Do not claim the target is ready.
2. Offline: use that classification to implement/review the31J connection wrapper,
   including source closure, never-open-on-error tests and exact31I CPU-operation
   parity. Keep the existing image and firmware contract.
3. Once released: one fresh M5 lab session, a discovery-only check first, then
   the single combined power/core-state/entry campaign only if the primary is
   verified. Return to Macintosh HD on completion/failure, without retry.
4. CPU1 arrival would permit a separate two-core Linux coherence/timer/IPI and
   renderer batch. No arrival means interpret the combined fields before choosing
   another hardware change. Neither case yet establishes all18 cores or parity.

Do not repeat31I, change its202 pins, erase a receipt, use an arbitrary serial
path, infer a CPU fault from this host exception, or modify macOS settings.

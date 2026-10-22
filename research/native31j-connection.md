# 31J: verify USB enumeration before consuming the CPU experiment

2026-10-21 Eastern. Native31J and CPU1/Linux SMP **NOT RUN**.

## Evidence and scope

M1's host-only result (report commit `ed3a63a`, execution `aa3f668`) confirms that one successful cached-registry
query returned exact empty stdout, without stderr, while M5 stayed in macOS.
No inventory or primary interface was established; zero device opens/target
requests belong specifically to that host diagnostic. Its6 pins and19 tests
passed. This supports the empty-output explanation for31I, but the actual31I
input was not retained, so its historical cause remains unconfirmed.

The defect we can fix is in our connection workflow: empty stdout previously
reached `plistlib.loads()` and failed after native reservation. The intake mocked
this entire boundary. No new firmware decompilation is called for here; the
public-source and read-only evidence in `native31j-host-discovery.md` already
isolates the software gap. A parser fix cannot guarantee physical enumeration.

## Original connection change

31J uses a new module, leaving all202 consumed31I files and the6-file host
handoff unchanged. It performs at most4 cached IOService observations before
opening any device, with a3-second cap per query,1-second inter-observation
wait and15-second overall discovery bound. Only exact empty stdout or a valid
registry with no primary candidate can wait for another observation. Empty
output remains unclassified, never invented as an empty plist.

Malformed output, command failure/timeout, invalid tree/metadata, ambiguous
primary, stale callout and non-character/symlink paths refuse immediately.
The exact VID/PID, interface1/class0x0a, nearest USB ancestry and lstat checks
remain mandatory. No prefix stripping, arbitrary path, alternative transport,
automatic port choice beyond the verified identity or hardware reset is added.
The selected path stays in memory; reports contain categories/counts only.

Every observation is journaled with a bounded prefix. Callback, journal,
interrupt and deadline failures stop; they cannot schedule another query or
serial open. The original outer deadline reason is retained. Discovery's zero
opens/requests describe that phase only, not subsequent transport activity.

A separate exclusive connection journal preserves the pre-open history. The
supervisor reservation records only its invocation. The native consumed journal
is created only after primary verification and before the single serial-open
attempt. Source pins are rechecked before native consumption. Connection phases
and attempted/completed flags distinguish backend import, serial open, UART
initialization and controller construction. Missing CPU counters remain missing
when no controller state exists. No arbitrary exception text, registry contents,
identifying path or traceback appears in public JSON.

The60-second connection/native budget includes discovery and finalization;
the parent retains one65-second child-process deadline, including initial
source/client checks, and bounded child termination. The human90-second window
also starts before discovery. No extra time or retry is introduced after any
serial-open attempt. All outcomes require an immediate Macintosh HD return.

## CPU behavior and validation boundary

The native Controller subclasses31I and changes only the experiment label.
Its firmware-backed reset gate, all18 live topology routes, same two CPU1 starts,
RAM recorder, up to8 PS and8 exploratory opaque-state reads, conditional timer
requests and park remain unchanged. Upper reset-field meaning/effective entry
and CPU1 execution stay unverified; opaque core-state access is still exploratory.
This release fixes host orchestration, not a demonstrated CPU startup defect.

The new intake includes the formerly omitted USB identity suite, frozen host
diagnostic tests, bounded discovery tests, real subprocess-result parsing through
the wrapper, source/receipt gates, supervisor deadlines and exact31I/J target
transaction parity. The real pinned m1n1 client/BootArgs/ADT wire scenarios run
in the existing ARM64 VM. No physical device is exposed there. Counts, hashes,
tool versions and results are in `native/boot/attempt31j/validation.json`.

The M1 must independently pass intake before the human restarts M5. The later
single supervisor command performs readiness discovery and the CPU campaign
within one bounded session. A healthy M1 needs no restart; use the existing
boot021 entry and boot042 package. Do not reset old receipts or alter macOS.

## Interpret the next result

| Outcome | Meaning and next action |
|---|---|
| Discovery never verifies a primary | Native run not consumed; retain exact query categories. Review physical enumeration before any new CPU hypothesis. Return to macOS; no retry. |
| Primary verified, later connection failure | Use the precise import/open/UART/construction phase. No inferred CPU measurement. Return; no reconnect. |
| Controller refuses before starts | Interpret actual gate/guard evidence; do not guess a new register write. |
| Power/state transitions without a recorder | Review effective dispatch/first-store visibility using combined evidence; fields alone do not prove execution. |
| Complete CPU1 arrival,8 requests and park | Prepare a separate two-core Linux batch covering coherence, atomics, timers/IPIs, clock/memory throughput and renderer/input latency. |

No result here establishes all18 cores, native Linux SMP or performance/efficiency
parity. A failed discovery does not establish a cable fault or a firmware defect.

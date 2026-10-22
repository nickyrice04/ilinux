# Attempt31H: reset-format and core-state campaign

2026-10-21. Native31H **NOT RUN**. This replaces the investigation hold after
matching-board firmware analysis and offline implementation. M1 must complete
independent intake and publish readiness before the human starts the M5 lab.

31G observed CPU1 PS actual0→15 after the second start, with no entry marker.
31H preserves those starts and the vector recorder, adding two complementary
observations in the same bounded session. It is a diagnostic campaign, not a
proven startup fix or an all-core Linux boot.

## Evidence and decision

[REA findings](../../research/native31h-reset-entry.md) establish a firmware
reset-address field at bits41:11 plus bit0; the reviewed caller first aligns
the input to4KiB. The old page-only report dropped bit11. This justifies precise
observation and a stricter preflight, **not** moving the hook to image+0x800.
The PMGR path does not support a missing stop-clear operation.

Public m1n1 supports32-bit accesses at CPU_IMPL+0x100. Its low-byte meaning and
accessibility for a never-started t6050 CPU remain unverified. A guarded
baseline, live ADT/mapping checks and CPU0 reference make this a bounded,
explicitly exploratory observation. No native model can establish safety from
address membership alone; first fault/lost acknowledgement/deadline stops.

## Fixed sequence

1. Existing exact boot021/census/ADT/topology checks; observe the same two
   RVBAR reads without adding another read. Preserve legacy and firmware-format
   relations without raw words. Require equal mirrors, firmware field=image
   base, and no unexplained fields before mutations. Otherwise stop for review.
2. Keep existing RAM/UART isolation,16 code-translation checks and vector-first
   recorder publication. No cold-entry hook, mapping change or RVBAR write.
3. Keep all four PS pairs. Add two CPU-state translation checks, then guarded
   CPU0/CPU1 baseline32-bit reads at the fixed+0x100 locations before startup.
4. Same two CPU1 start stores only. After each, collect PS then CPU-state pairs.
   Use the existing guard-free32-bit helper once any start intent exists.
   Preserve every completed prefix; no new helper bytes or mutation types.
5. Existing three-second arrival loop and recorder/reset/spin checks. Collect
   final PS/state pair only on natural arrival timeout or verified final park.
   A fault/deadline is not permission for terminal reads. At most8 PS reads and
   8 CPU-state reads; each CPU-state pair has a one-second soft deadline checked
   before and after calls. Outer controller/supervisor and90-second human bounds
   still apply to stalls that cannot be synchronously interrupted.
6. Only independently verified arrival plus complete recorder permits the
   existing eight timer requests and final park validation. Always return to
   Macintosh HD afterward. No Linux continuation or additional CPU.

The unchanged successful path has74 mutation intentions; ordinary timeout66.
Read-only observations do not add mutation intentions. No performance claim is
based on USB round-trip timing or VM emulation.

## Outcome table: what the next boot can tell us

| Outcome | Supported interpretation and next action |
|---|---|
| Mirror field=image+0x800, differing mirrors or unexplained bits | Old page-only match hid a configuration difference. Stop before mutations; trace the exact firmware ownership/entry path offline before selecting a hook. |
| Exact image-base field, state-read access/translation fault | Format ambiguity narrows; the proposed state access is not usable under this setup. Stop, retain the prefix and analyze the exception/access contract. No width/address scan. |
| CPU1 PS changes and low byte changes, marker remains zero | Two independent hardware fields respond; instruction execution is still unproved. Prioritize effective dispatch and entry/store visibility over changing the start mask. |
| CPU1 PS changes, low byte stays unchanged, marker zero | Power response lacks an observed low-byte transition. Investigate reset/release and the opaque register semantics. This does not prove a stuck reset or no instructions. |
| CPU0 low byte changes unexpectedly | Reference state is not stable; do not treat CPU1 equality as arrival. Correlate phase/exception evidence before another operation. |
| Partial recorder | Localize the earliest committed software stage, respecting identity/EL/visibility limits; no automatic continuation. |
| Complete entry, eight requests, counter progress and park | CPU1 controller success only. Next prepare a separate two-core Linux batch for coherence, atomics, IPI wakeups, clocks, memory and renderer latency. |
| Lost reply, fault or observation deadline | State may already have changed. No retries, cleanup RPCs or terminal observations; immediate human return. |

No negative opaque-state result alone chooses a new register write. A matching
mirror does not prove effective reset destination, and a vector marker can also
be an exception entry. Source/image bindings and the arrival gates remain
independent.

## After CPU1

Retain actual topology:12 Performance (ADT M) and6 Super (ADT P), three clusters
of six. Validate one representative per remaining cluster before all-core
operation, then measure capacity, frequency, memory and energy policy. Current
idle=nop workaround is already present; replacing it safely remains necessary
for efficiency. Native GPU acceleration is a separate requirement for smooth
high-resolution rendering. Storage/network work follows without reinstalling
or reopening security setup.

M1 handoff: [attempt31h-instructions.md](../../tools/m1n1-client/attempt31h-instructions.md).
Consumed31A–31G sources/receipts/manifests and pinned old navigation stay frozen.

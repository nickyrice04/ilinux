# Census31A — reset-vector mirrors and Macintosh HD return

**Observed, 2026-10-21:** the single authorized census completed with
**`CENSUS_COMPLETE_REVIEW_REQUIRED`**, exit **0 in 1.155 seconds**.
Exactly **two guarded RVBAR reads**, **zero CPU starts**. Both CPU0 and CPU1
report locked mirrors targeting the installed m1n1 vector entry, image offset
`0x0`. **Native SMP, Linux boot and renderer tests remain NOT RUN.** The human
confirmed return to the usual Macintosh HD desktop; no retry or continuation.

The exact schema-reviewed output is
[attempt31a-census-2026-10-21.json](attempt31a-census-2026-10-21.json).

| CPU ID | Locked | Target relation | Image-relative offset | Evidence scope |
|---|---|---|---|---|
|0 |true |vectors |`0x0` |mirror only |
|1 |true |vectors |`0x0` |mirror only |

**Interpretation:** the two mirrors satisfy this particular static entry
condition of the offline startup candidate. A mirror value does not prove
that the waiting CPU actually fetches or executes those vectors, establish its
reset state, or authorize deploying that candidate. No CPU was started to test
execution. 31B remains a separately reviewed deployment and native validation.

## Provenance and independent M1 checks

M5 handoff **`964aaac`**; readiness/execution commit
**`f105ed080349a70dc0c2e0dd5c06798dbd0a6822`**. Independent
[M1 readiness](attempt31a-m1-offline-2026-10-21.md) was pushed before execution:

* All **31** entries in `attempt31/smp-source-sha256.txt` verified before live
  execution, including census, checklist, current handoff, guards and evidence.
* Boot042's **13** files verified against manifest SHA-256
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
  Existing boot021 image, 3,932,160 bytes:
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
* Clean client remained pinned to
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. No client update, image rebuild,
  install, replacement or chainload.
* Offline census reported `OFFLINE PASS` without USB access. **19 test methods
  PASS**: 11 census, 8 renderer; zero skips or fixes. All four offline processes
  exited 0. Synthetic tests and M5's VM/REA evidence are not native CPU starts.
* Reviewed census source SHA-256
  `c65aa957c1019eb2623f5744dcdce9c7507de2063f9f76da2c21f489dc47a 90e`;
  source-pin file and source-pinned checklists remain unchanged after the run.

The human reported the M1 restart and M5 Running proxy, then confirmed power,
direct cable reseat, unlocked/open-lid M1 and a 90-second timer ready. The timer
cue immediately preceded the sole live command. Restart is human-reported;
this census did not independently measure M1 boot freshness. No video was
requested or supplied; console/ADT/USB paths and identifiers were not published.

## Guarded live sequence and bounds

The documented command ran once through the pinned client wrapper with
`--live --device auto --confirm CENSUS-J716C-SMP-31A` and the existing verified
boot021 file. Discovery was performed within that command using the existing
descriptor-checked primary-interface selection; no arbitrary port or separate
P_NOP/USB test was opened. A durable local one-use receipt was written first.

Successful completion requires all implemented guards: t6050/board, all 18 ADT
topology records and cluster descriptors, immutable startup/SMP text equality,
boot CPU/no started secondaries, installed SMP RAM-state and 32-record table
consistency, and no pre-existing diagnostic exception before MMIO. The ADT was
parsed only in transient memory with error output suppressed. Both RVBAR reads
returned valid values without a guarded exception, and the final no-secondary
check passed. No live PMGR read, other-CPU scan, SPTM operation or target heap
utility was used.

`read_only_hardware:true` is the tool's precise scope: it performs no hardware,
reset-vector, CPU-start, code, security or policy write. The existing proxy's
diagnostic exception counter is read/cleared as documented; this is not a
claim that every byte of m1n1's diagnostic RAM remains unchanged.

Tool bounds were **60 s overall / 5 s serial read**, with a local 75 s process bound
and the human 90 s timer. Observed command interval:
**18:52:25.206–18:52:26.360 UTC / 2:52:25–2:52:26 PM Eastern**.
No timeout, refusal, read trap or command error. Serial closed in the tool's
finally block. Output matched the exact eight-field top-level/five-field row
schema, two CPU IDs, booleans, relative classes/offsets and NOT RUN statuses.
No raw target value or image base is present in the published JSON.

## Return, limits and M5 next

Immediately after completion, the human was instructed to power off and select
Macintosh HD. No proxy shutdown, CPU-stop, shell, reconnect or second census.
Return confirmation durably recorded **18:53:47.240 UTC / 2:53:47 PM Eastern**,
**+82.036 s from census start**. This is a confirmation-record interval, not an
OS boot benchmark. Both command and recorded return were within 90 s.
Only this session's bounded caffeine assertion was stopped; no USB reader,
SSH/relay, Linux launcher or census process remains.

One post-return local bookkeeping snippet used a Python reserved keyword and
failed at parsing before any action. It was corrected only to save the return
receipt and stop the owned caffeine process; no target command was retried or
source/gate changed. Raw receipts/stderr remain ignored privately.

Original macOS, installed entry/m1n1, boot/security/default settings, volumes
and firmware were unchanged. Routine policy/default checks remained waived;
original Full/lab Permissive and Macintosh HD default remain last reported,
not freshly verified. No image transfer, CPU-frequency operation, module,
renderer change, Linux boot, SMP stability/performance or energy test ran.
The older copy-only31 pair/profile/collector remain **HOLD**.

**31A is consumed.** M5 reviews these matching mirror observations against a
concrete RAM startup deployment and obtains first-instruction/park evidence
before any separately authorized 31B. Linux two-core topology, timer/IPI,
coherency, return-path checks and renderer integration remain unvalidated.
The result does not establish 31B readiness or native speed/efficiency/parity.
The current coordination/result supersede the frozen source-pinned checklist's
pre-execution NOT RUN/readiness wording; do not replay it.

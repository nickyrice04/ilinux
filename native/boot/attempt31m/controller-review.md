# 31M controller review

This release tests visibility of CPU1's existing Normal-memory entry records.
Native execution, CPU1 arrival, Linux SMP and macOS parity remain unverified.
The consumed31L outcome is preserved; no31L file or receipt is changed.

## Inherited and new operations

31M inherits31L's exact boot021, client57a9339, topology/reset/source gates,
CPU0 Device/Normal controls, two CPU1 start stores, vector/cold prefixes, timeout
and durable-connection behavior. CPU1 prefix generation is unchanged from31L (identical bytes for identical
load/helper addresses). There is no
new secondary initialization, reset redirect, firmware replay or MMIO address.
Callbacks planned/completed are explicitly0, correcting inherited metadata.

New CPU0 operations occur in the existing owned16KiB helper allocation:

1. Preflight binds the selected feature pointer through the live GOT and the
   signed dispatch-table entry for the existing CIVAC proxy opcode. The exact
   image audit validates its call target, completion barriers and false legacy
   Cyclone workaround flag. The workaround's system-register writes are not used.
2. After translation checks, publish an8-byte returning CTR reader at+0x220.
   Qualify CPU0 EL2/VHE/VM0 and independent DMinLine/CWG64-or128-byte geometry.
   Unknown CWG, larger granules or another regime refuse before CPU1 starts.
3. Initialize, clean and verify complete128-byte vector/cold/control granules
   at+0x1000/+0x1080/+0x1100. Existing records use the first64 bytes. No CPU0
   record store follows initialization. Existing prefix publication changes
   disjoint code; it cannot dirty those record granules.
4. A separate pre-start CPU0 maintenance control reads48 words, stores/clears
   one marker and issues2 maintenance requests. Marker/canaries/restoration and
   immediate exception checks must pass within2seconds. It proves the local
   operation works, not CPU1 coherency or instruction execution.
5. After each start, acquire cached phase/identity/phase. Only all-zero sampled
   fields permit one `DC CIVAC` request covering the fixed record's first64
   bytes, followed by another triad. The pinned helper emits one cache
   instruction; its common DSB SY/ISB epilogue completes before acknowledgment.

Cache maintenance is CPU0-issued, not necessarily CPU0-local. It can propagate
within the memory's shareability domain. Clean-and-invalidate was selected over
invalidate-only to avoid intentionally discarding a dirty peer record. Owned
clean CPU0 granules prevent this observer from writing stale dirty zeros back
onto a secondary's publication. CPU1's incoming regime remains unknown.

Only the two record addresses are eligible after starts. Control maintenance
is pre-start only. No bulk-memory access, guarded read/write, exception-counter
clear, extra start, callback, post-fault cleanup or retry is allowed after starts.
An immediate non-clearing diagnostic helper read follows each successful
request, as in the inherited controller. If a request raises or times out,
there is no follow-up target query. The common proxy epilogue restores its saved
guard, without temporarily changing it for the cache operation.

## Evidence and stop semantics

Maintenance intent is journaled before dispatch. Attempt and acknowledged counts
remain distinct on fault. A snapshot commits expected identity only when its
first phase already proves commitment and its identity matches CPU1. Partial,
unexpected or invalid records stop; every positive also stops before callbacks.
Two zero snapshots do not prove no execution. A post-maintenance positive cannot
by itself distinguish cache behavior from CPU1 arriving between snapshots.

The parent retains its65-second bound; the child60-second, arrival3-second,
serial2-second and human90-second return windows remain. All six use files are
exclusive and never cleared for retry. Any result requires immediate Macintosh
HD return. No macOS, volume, boot/security/default or installed-image change.

The offline observer/controller tests inject faults, stale snapshots, delayed
publications, wrong mappings, geometry and source bindings. Independent GNU
assembly checks the CTR leaf. Real pinned-client serialization runs only inside
the isolated VM against an original synthetic target. These checks do not
emulate Apple's cache hierarchy or prove native compatibility. Actual outcomes
are recorded in validation.json, followed by independent M1 intake.

Timing limit: the3-second arrival budget is checked around observation batches,
not a hard per-RPC interrupt. Local control budgets are checked before/after
operations; an in-flight request can reach its serial timeout. The independent
supervisor and human return bounds remain necessary.

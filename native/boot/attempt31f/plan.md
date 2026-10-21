# 31F: resolve the earliest entry blind spot, then validate each core class

31E's native record proves that CPU0 could publish and read back the recorder;
it does not establish CPU1 instruction/data visibility. Both startup stores
were acknowledged, but 93 recorder samples remained at phase0. Arrival, timer
requests, Linux SMP and performance improvement were not observed.

The previous recorder read MPIDR and filtered for CPU1 before its first store.
That conflates an unexpected identity, an early register-read fault, a different
effective entry target and invisible writes. The exact public boot021 image
permits an earlier, original RAM recorder at vector+0. It stores phase1 first,
then commits unfiltered identity, EL and SCTLR separately. A strict observer
stops on unexpected identity or invalid state instead of suppressing evidence.
Vector+0 also serves a synchronous exception slot; neither a marker nor a full
register record proves reset provenance or final arrival.

## Implemented experiment

1. Verify exact image, live ADT/runtime CPU census, RAM and direct-USB state.
2. Check existing CPU0 translation regime and 16 fixed code/record probes.
3. Publish the 168-byte recorder before its vector branch, using the existing
   writable RAM alias; check readback, cache operations and immutable text.
4. Make only the same two fixed CPU1 startup stores. Observe after the first;
   any recorded progress or error stops before the second store.
5. Capture bounded sequential phase/identity/EL/cache/reset/spin observations.
6. Only verified arrival plus complete expected identity enables eight timer
   requests and final park. Return to Macintosh HD after any outcome.

No boot-object, mapping, RVBAR, permission, security, volume or macOS change.
The default/offline command cannot access USB. One-shot receipts prevent retry;
controller/supervisor/human deadlines remain 60/65/90 seconds respectively.
No firmware simulation is claimed. Original instruction interpretation,
failure injection, byte comparison and real-client serialization eliminate
software defects before spending a native boot.

## Core types and subsequent batches

The host inventory is **12 Performance + 6 Super**, in three six-wide clusters.
ADT M names the Performance clusters0/1; ADT P names Super cluster2. CPU1 shares
CPU0's Performance cluster. Existing six-wide startup packing is important for
later clusters but produces the same value2 mask for this CPU1 attempt. It cannot
explain 31E by itself. See `research/cpu-topology31f.md` and the new offline DT
audit/read-only Linux inventory tools.

After bootloader entry is established, prepare one reviewed two-core Linux
session with timer/IPI correctness, coherent shared-memory stress, CPU-local
throughput, memory bandwidth, input-to-frame tracing and renderer threading.
Then bring up a representative of cluster1 and the Super cluster, validate
their distinct identity/frequency/cache domains, and expand to all18. Calibrate
scheduler capacities and frequency invariance from measurements, then measure
idle behavior, thermal limits and energy per completed task. Existing capacity
values are hypotheses, not a macOS-equivalent scheduling policy.

Networking and read-only storage remain separate tracked enablement work.
Native GPU support remains necessary for a fully efficient desktop; all CPU
cores alone cannot establish macOS-level graphics behavior. No throughput,
latency or energy gain is claimed by 31F's offline tests.

## Analysis provenance

This iteration uses the exact public bootloader image/source and the existing
REA findings in `reverse-engineering/findings/cpu-startup-2026-10-21/`.
Those findings did not establish another CPU1 power operation. Fresh decompiling
was not needed to identify this original recorder's ordering defect; no new
Apple power writes are guessed. Proprietary code/output stays outside Git.
The handoff's outcome table specifies the next evidence-driven investigation.

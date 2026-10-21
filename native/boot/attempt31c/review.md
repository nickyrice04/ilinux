# 31B review and corrected CPU1 experiment 31C

2026-10-21. **31B consumed; native 31C NOT RUN.**

## What the M1 actually observed

Report `4fb684c`, execution `a6ced17`: STOP / preflight / `ram_bounds` in
0.781 seconds; supervisor 1.192 seconds, no deadline. Zero mutation requests,
zero CPU-start writes, no allocation/helper upload, and no CPU1 entry test.
Human Macintosh HD return confirmed at +57.883 seconds. No evidence of a CPU1
or physical RAM fault. The report does not retain the rejected numeric fields,
so their exact values in that session cannot be reconstructed from its JSON.

## Confirmed controller defect and evidence

`smp31b.py:ram_bounds` requires `phys_base + mem_size < (1 << 40)`. That is a
physical-address ceiling of 1 TiB, not a RAM-capacity limit. This machine's
DRAM starts at **0x10000000000 (1 TiB)** and spans **0x2000000000 (128 GiB)**.
Every nonempty usable interval within that aperture fails the old predicate.

Evidence independently checked:

* A read-only macOS IODeviceTree `/chosen` query on this machine returned those
  two DRAM properties. Only those properties were emitted; no raw registry or
  personal identifiers were saved. The separate sandboxed `hw.memsize` query
  was denied, so it supplied no new evidence. The existing hardware inventory
  already records 128 GiB from an earlier successful observation.
* Earlier native [attempt22](../stage-b-2026-10-18-attempt22-result.md) records
  high-address heap placement; [attempt26](../stage-b-2026-10-19-attempt26-result.md)
  independently records the keyboard DMA window in the same address range.
* Pinned public m1n1 `57a9339` uses 64-bit fields in `src/xnuboot.h` and
  `proxyclient/m1n1/tgtypes.py`. Revisions 2 and 3 have the same physical-base
  and memory-size offsets, 16 and 24. The later command-line lengths differ.
* `src/kboot.c:dt_set_memory` declares exactly the BootArgs usable interval;
  `src/memory.c:mmu_add_default_mappings` derives its RAM base dynamically.
  `mmu_configure` uses `TCR_IPS_4TB` (42-bit physical addressing). The controller's
  narrower 40-bit assumption has no basis in this pinned implementation.

**Confirmed:** the controller rejects this machine's known aperture.
**Strongly supported explanation of 31B:** the invalid ceiling caused its
refusal. Exact per-field attribution for that run remains unavailable.
This is our controller/test defect; the offline suite substituted an older
low-address RAM fixture and injected its bounds, missing the production reader.
The prior “real ADT parser” test did not exercise the real BootArgs parser.

## Correction and unchanged scope

`smp31c.py` subclasses the frozen 31B controller and replaces only its RAM-bound
reader plus attempt identification. BootArgs must be a supported, consistent
revision and a nonempty, non-overflowing 64-bit interval. It must fit the exact
observed 128 GiB machine aperture and the pinned 42-bit physical address space.
The ADT pointer is checked against that narrower interval before reading; its
`/chosen` DRAM base and size must independently match. No fallback is allowed.
The original usable interval is returned unchanged, preserving firmware
exclusions for subsequent image/helper containment checks. It does not make
carveouts usable or alter mappings, permissions or memory speed.

No new hardware command or startup sequence: the same two CPU1 start writes,
dedicated stack, helper, guard-free post-start observations, WFE parking and two
bounded timer requests. The original image/code/relocation/topology checks,
fault handling, diagnostic limitations and timeouts all remain. The original
31B source, tests, manifests and consumed receipts are preserved. 31C has a
separate fixed receipt directory and literal confirmation; no force/reset.
Public results add only boolean RAM predicates and the supported revision.

Fresh REA is unnecessary for this failure: it concerns our own range check
and the fully available public bootloader source. The accepted earlier REA
PMGR behavioral findings still support the unchanged CPU1 sequence; no rejected
pseudocode or proprietary code is used or published.

## Offline verification

The new raw fixture is original synthetic data using the observed aperture;
it is not a saved BootArgs/ADT dump. It encodes fields independently of the
parser under test. Host tests reproduce the old refusal, exercise the new gate,
and cover zero/overflow/outside bounds, missing/mismatched ADT properties,
unknown/inconsistent revisions, invalid/short ADT reads, image containment,
no retry and separate receipts. They run the complete inherited CPU1 controller
at high addresses with the production bounds function. Host uses a parser
model; job 060 runs the same tests with the actual pinned BootArgs/ADT parsers.

Job 060 also runs the full high-address controller through the actual pinned
client's request serializer and readstruct path. A fixed-opcode endpoint models
RAM/CPU1 responses; no USB is opened and no real CPU start occurs. The unchanged
31B helper's dual-compiler and actual ARM64/sanitizer evidence stays in job 059.
Native entry, cache behavior, Linux SMP and performance remain unproven.

**Final guest exit 0, 60 Python methods PASS:** 11 new RAM/controller tests,
three new supervisor tests, and 46 prior regressions. Host's 14 new methods
also PASS. Real pinned-client high-address serialization/struct/ADT test PASS.
Initial VM fixtures failed because the parser also requires a PMGR node and
two device records; both fixture omissions were corrected before this result.
No production gate was relaxed to make those tests pass. Source hashes and
guest timing are recorded in [validation.json](validation.json).
Reproduce with the existing VM under the quiet/VM locks:

```sh
mkdir -p virtualization/jobs/060-smp31c/out
cp build/native-boot042/verified/m1n1.bin virtualization/jobs/060-smp31c/out/boot021.bin
tools/vm-job.sh virtualization/jobs/060-smp31c smp31c
```

## Next decision

Offline validation passes. M1 verifies the new source manifest and existing
boot042 package, publishes readiness and waits for a fresh human start. One
31C CPU1 test, then immediate Macintosh HD return, using
`tools/m1n1-client/attempt31c-instructions.md`. No new boot image, root transfer,
settings change or routine policy check is needed. If it passes, prepare
two-core Linux DT/spin-table/launcher and timer, wakeup and coherence tests,
then the renderer-threading comparison. A bootloader PASS alone is not Linux
SMP or macOS performance parity. Do not restart before M1 readiness.

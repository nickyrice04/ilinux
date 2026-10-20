# Attempt29: separate cache, translation and placement effects

2026-10-20. **Offline ready; native NOT RUN.** This is an original Linux
diagnostic and per-allocation huge-page experiment, not a claimed performance
fix. [M1 instructions](../../../tools/m1n1-client/attempt29-instructions.md),
[validation](../../../native/boot/attempt29/validation.md).

## What attempt28 changed about the diagnosis

Observed boot CPU0 is MPIDR `0x40000`, part `0x068`, `apple,sotra-m`. Its
requested state6 maps to 2.652 GHz and the independent dependent-ADD estimate
was 2.650/2.651 GHz. The driver initialized without writes. Accurate typing and
zero leaked menu pollers did not remove the unusable application delay.
The unchanged `chase_short` measured about 332–337 ns at 32/128 MiB.

That number alone does not identify a broken memory controller. The same
source on this Mac's macOS 26.6.2/25G83 gave these contextual medians:

| chase28 working set | Native Linux before module | macOS default | macOS process background policy |
|---|---:|---:|---:|
| 16 KiB | 1.142 ns | 1.518 ns | 2.239 ns |
| 4 MiB | 9.287 ns | 15.205 ns | 43.140 ns |
| 32 MiB | 331.582 ns | 63.736 ns | 327.713 ns |
| 128 MiB | 333.914 ns | 105.359 ns | 361.144 ns |

**Measured, unmatched contexts:** macOS default and background placement differ
strongly. Separate short CPU tests estimated 4.597 GHz with default QoS and
1.337 GHz with background QoS, with CPU migrations recorded. These are neither
simultaneous clocks for the chase nor pinned-core comparisons. They show why
subtracting Linux from one macOS result would misattribute placement/frequency
effects to the OS. No throughput or energy parity ratio is claimed.

Both OSes use 16 KiB base pages. macOS reports Super/Performance cache levels:
128/64 KiB L1D and 16/8 MiB L2. Crossing a cache's capacity naturally changes
latency; the cause and magnitude on native Linux still need isolation. The
new matrix records CPU numbers at each timed sample's boundaries, faults,
context switches, and actual huge-page backing. Same boundary CPU does not
exclude a migration away and back during a sample.

## REA findings and their engineering consequences

REA 6.4.0 / Ghidra 12.1.4 ran inside the existing diskless ARM64 lab on copied
macOS artifacts. Five bounded function dossiers completed, and **265 instruction
words** were independently checked by Apple LLVM against the original carrier.
Artifact digests, byte ranges, function addresses and exact rejected gates are
in [rea-plan.json](../../../native/boot/attempt29/rea-plan.json) and
[rea-validation.json](../../../native/boot/attempt29/rea-validation.json).
All Apple bytes, disassembly and pseudocode remain private under ignored build.

| Static target | What the evidence supports | Consequence |
|---|---|---|
| `AppleT6050PMGR::_setDCSPerfState`, `0xfffffe00098806d0`, 304 bytes | Its terminal block calls the shared SOC clock-generator read/write/wait interfaces. Index `0x400` is supplied at `+0xd8`, `+0xec`, `+0xf8`; the wait supplies bit31 and expected zero at `+0xfc`, `+0x100`. The upper-28-bit preservation mask appears at `+0xe0`. | Memory-related DCS requests have a path distinct from CPU DVFS. A CPU requested-state observation is not a memory-frequency observation. No DCS write is justified by this alone. |
| `ApplePMGR::_getClockReqMemory`, `0xfffffe00094a5ac4`, 412 bytes | A named memory-request interface exists; the derived dossier reaches substantial code outside its reported body. | Request metadata is not proof of actual DRAM clock. Do not transplant its rendered pseudocode or add speculative reads. |
| `readMPMGRClkGenSOCReg`, `0xfffffe0009499c7c`, 64 bytes; `writeMPMGRClkGenSOCReg`, `0xfffffe0009499cbc`, 68 bytes | Bounded helper bodies have matching original bytes and no out-of-body pcode. Dispatch remains indirect. | Register index `0x400` is **not** an independently established physical address. No guessed MMIO access in attempt29. |
| `AppleT6050PMGR::initRegGroups`, `0xfffffe000987f094`, 212 bytes | Group initialization is relevant to address resolution, but its high-pcode includes external code. | Preserve the previous bounded group evidence; physical DCS mapping, completion semantics and thermal constraints remain open. |

Whole-function pseudocode gates **reject** the DCS, clock-request and group
functions for cross-boundary operations; DCS also has a truncation warning.
The two small helpers are `manual_review_required`, not certified equivalent.
The useful DCS facts above come from its carrier-verified terminal instructions
and symbol-resolved call targets, not the rejected whole-function pseudocode.
Two initial broad standalone-XNU queries were cancelled at their time limits;
they produced no usable cache-setup conclusion. No failure is counted as a pass.

The public XNU [register definitions](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/arm64/proc_reg.h)
provide architectural context, not proof of this boot's live values. The exact
boot042 Linux `proc.S` configures write-back table walks and Normal memory;
source intent must be checked against live SCTLR/TCR/MAIR. This motivates the
original architectural observer instead of replaying private register writes.

## Implementation and scope

* `ilinux_mem29.c`: one explicit module load, board/SoC/CPU-count/MIDR/MPIDR
  guards, standard architectural reads only. Snapshot SCTLR/TCR/MAIR/CTR/CLIDR
  and the loader's initial stack PTE attributes, with mmap/PTE locking. No
  physical/virtual address or user contents emitted. Absent mapping is reported
  as level0; it does not invalidate the other register readings. No MMIO,
  system-register write or page-table modification. No unknown Apple HID read.
* `memory29.c`: 32 MiB-aligned anonymous allocations, fixed permutation seed,
  128-byte links, full-cycle validation/warmup, four sizes and three samples.
  Compare global-random with shuffled-page/local-within-page traversal, then
  compare `MADV_NOHUGEPAGE` and `MADV_HUGEPAGE` on otherwise identical Linux
  mappings. Peak allocation is under 170 MiB. Alarm80s. Linux produces48 rows;
  macOS24 because Linux page advice is unavailable there. No global THP knobs,
  forced collapse, locked memory or persistent files.
* `collect.py`: verifies the known native identity and existing CPU28 assets,
  binds to CPU0, loads only the new memory module, runs pre/post clock estimates,
  unchanged chase28 and the new matrix, and captures available telemetry.
  CPU28's cpufreq module must remain unloaded. No policy changes.
* `receive.py` and the M1 helper: check exact bundle size/hash and four regular
  members, refuse links/paths/duplicates, create one exclusive directory only
  after confirming `/run` is tmpfs, then execute under systemd's runtime bound.
  Same journal-key check and fixed600s switch-time window as the proven run.

The kernel [THP documentation](https://docs.kernel.org/admin-guide/mm/transhuge.html)
explains why larger mappings can reduce translation costs and why an allocation
hint does not guarantee huge backing. `AnonHugePages` is recorded before/after
each sample; `-1` means unavailable. It is not a complete census of every mTHP
size. Page-local traversal changes both cache and translation locality and is
not a pure TLB test. The matrix's fixed order is exploratory, not a randomized
energy/performance trial. Any positive result needs a controlled follow-up.

## Decisions after the one native run

| Observed outcome | Next engineering step |
|---|---|
| Unexpected cache enable, MAIR or table-walk attributes | Audit the exact Linux entry/setup and m1n1 handoff; build a narrow correction only after identifying where the value changes. Do not patch live registers from SSH. |
| Huge advice obtains substantial huge backing and improves global-random latency with stable CPU estimates | Repeat an interleaved comparison, then prototype aligned/per-process allocation in the measured bottleneck. Do not globally change Omarchy's memory policy from this one test. |
| Page-local improves but huge advice does not obtain backing | Keep cache-versus-translation attribution open; inspect page coverage and alignment before blaming hardware. |
| Normal attributes and little verified page-size effect | Prioritize SMP/booting a performance core, software-renderer profiling and the separate memory/DCS request lifecycle. CPU-clock and fabric-clock questions remain distinct. |
| Native refusal/fault or missing observations | Keep the partial evidence; return to macOS and fix the narrow diagnostic. No on-boot retry or added experiment. |

SMP, usable thermal/energy feedback, idle retention and native graphics remain
necessary for macOS-class CPU/desktop efficiency. N1 Wi-Fi and ANS storage stay
separate tracks. This experiment preserves the successful installation and
does not require another multi-gigabyte root rebuild or transfer to the M1.

# Revised attempt31: native SMP preparation and renderer threading

2026-10-21. Original implementations, offline only. No macOS/volume/security
change, installed m1n1 replacement, CPU start, hotplug or frequency write.
The copy-only attempt31 remains held. **31A is a bounded reset-vector census,
not a faster-desktop boot.** M1 instructions are
`tools/m1n1-client/attempt31-smp-instructions.md`.

## What is established

The previous diagnostic attributed most VM terminal first-buffer delay to
compositor rendering. Four configured workers on six allowed guest CPUs gave
about42ms instead of812–976ms. That supports testing threading; it does not
prove native SMP, physical presentation, full GPU capability or efficiency.
See `native/boot/attempt31/diagnosis/README.md` for the complete limitations.

The existing startup research contains a supported bitmap correction and an
unproven reset-entry hypothesis. They must not be treated as one verified fix:

* **Confirmed static:** the sanitized ADT has18 CPUs in three six-core clusters;
  PMGR descriptors are `(6,0), (6,6), (6,12)`. m1n1's four-bit stride aliases
  four pairs. CPU1 is in cluster0: its bit is2 under both layouts, so fixing
  the stride alone does not explain failure of that first secondary.
* **Confirmed static:** misc-cores is PMGR reg[0]+`0x88000`, physically
  `0x280688000`; cluster control is a separate group at `0x280620000`.
* **Unknown native:** the offline CPU's locked reset-vector mirror and actual
  entry path in this custom raw boot. macOS's SPTM/XNU entry contract does not
  establish that path. A mirror matching an address is necessary for this
  conservative candidate, but not proof that a core actually executes it.

Fresh REA6.4.0/Ghidra12.1.4 analysis of this Mac's AppleT6050PMGR
`initRegGroups` at `0xfffffe000987f094` completed in the existing isolated lab.
Independent LLVM/carrier checking verified all53 instruction words/212bytes.
The provider crossed into a shared helper and its whole-function pseudocode
was **rejected**. No pseudocode informed new code. The bounded constant/call
analysis agrees with the already recorded register-group evidence in
`reverse-engineering/findings/cpu-startup-2026-10-19/`. Raw outputs stay ignored;
`rea-validation.json` contains only provenance, counts and rejection classes.

## Implemented code and why

`prepare.py` transforms a clean public m1n1 `57a9339` into a disposable build.
It checks the exact `smp.c` digest. `layout31.h` consumes the exact reviewed
descriptor and refuses missing/truncated/overlapping/unexpected layouts;
there is no fallback to the known-wrong stride on t6050. Other chips retain
the existing packing. The old October15 patches are not applied.

The new retained `smp31_start_one()` symbol is an **offline candidate**, with
no proxy opcode or deployment wrapper. It admits only CPU1 from boot CPU0 on
the exact t6050 topology, initialized PMGR base and no started secondary.
It requires locked primary and secondary RVBAR mirrors equal to the existing
vector entry. It never writes RVBAR, CPU frequency, cluster power or security
state. It selects WFE parking before the two existing core-start writes,
retains the100ms polling bound, refuses retries and retains the dedicated
stack on timeout in case entry arrives late. Bulk starts, generic stops and
switching back to deep-WFI parking are refused on this candidate's t6050 path.
It does not patch `_start`, copy SPTM initialization or infer a trampoline.

`test_start.c` runs the **actual extracted candidate functions**, with synthetic
register hooks. It checks exact write addresses/values, zero writes on refusal,
timeouts/stack retention, retry exclusion and all18 distinct mask bits, in
normal and ASan/UBSan builds. Linking a complete image establishes build
compatibility; no new m1n1 image has been installed or chainloaded.

`renderer.py` computes workers from the intersection of Linux-online CPUs and
the process's affinity: one CPU→0 workers, two→1, six→4, cap4. It is opt-in,
executes a supplied compositor command, and changes only that command's
`LP_NUM_THREADS`. It does not enable cores, change affinity, lower resolution
or alter blur/animation/color. Its environment can be inherited by children;
VM client launches explicitly use0 workers to isolate the compositor. A
native session integration must preserve that separation and validate actual
worker creation. Four is an experimental cap, not a native optimum. CPU count
is not CPU capacity; power, core-class placement and thermal policy remain open.

`coherence.c` provides a bounded Linux two-CPU smoke test: verified affinity,
2,000 shared-payload/futex round trips, acquire/release ordering and a5s
software deadline. One allowed CPU returns77 rather than inventing an SMP
result. This checks a useful scheduler/coherency path, not every timer/IRQ/IPI
mechanism or stability. A separate external timeout remains necessary.

## Native sequence and blockers

1. **31A now:** M1 verifies the census offline, then one human-started session
   on installed boot021. Two guarded RVBAR reads, no starts or launch. Retain
   only sanitized classifications; return to Macintosh HD. No image transfer.
2. Review the result. An unknown target remains unknown: no guessed branch,
   reset-vector overwrite, chainload or live edit. A matching mirror still
   needs review of a concrete RAM deployment and first-instruction evidence.
3. A separately packaged31B may start one secondary, establish a stable entry
   and heartbeat, then verify Linux spin-table handoff and exact two-core DT.
   Current launcher deliberately prunes inactive CPUs and caps Linux at one;
   changing `maxcpus` alone will not enable SMP. Its exact topology/DT checks,
   boot arguments and independent timeout must change together after review.
4. Before expanding to another cluster: per-core timer progress, bidirectional
   scheduler wakeups/IPIs, cache/coherency and bounded load, plus return path.
   Keep frequency unchanged and `idle=nop arm64.nowfxt`. Busy idle across more
   cores increases power; SMP alone is not macOS-class efficiency.
5. Integrate the tested renderer policy into a new paired RAM root, compare
   original versus threaded rendering at identical pixels/visual settings,
   measure input-to-buffer and physical response separately, and collect the
   existing native CPU/memory baselines. Then expand cores under evidence.

No current candidate proves usable native performance. G17 GPU acceleration,
safe idle/thermal/frequency policy, networking and storage remain distinct
parts of the target. Static REA cannot replace this missing raw-boot observation.

## Offline results and reproduction

`validation.json` records full-build pins, toolchains, test counts and initial
harness failures. Final build, parser and renderer jobs each returned guest0.
Fourteen actual-start cases passed both normal and ASan/UBSan builds;11 census
and8 renderer tests passed. The actual pinned ADT parser passed a synthetic
18-CPU fixture with boot-args revisions2/3 and rejected revision4. The shared
payload smoke completed2,000 round trips on VM CPUs0/1 in40.6ms; on one CPU it
refused with77. This is correctness evidence, not a native wakeup benchmark.

At3456×2160, the new VM trial recorded:

| Allowed compositor CPUs | Configured workers | Terminal first-buffer ms (3 samples) | Full callback median ms |
|---|---:|---|---:|
| 0–1 | 0 | 684.6,753.6,750.6 | 220.8 |
| 0–1 | 1, adaptive wrapper | 40.6,37.3,37.1 | 216.3 |
| 0–5 | 4, adaptive wrapper | 41.4,41.0,39.9 | 59.2 |

One worker strongly changed event-loop responsiveness in this workload but
barely changed full-frame throughput. Additional workers improved the latter.
These are sequential exploratory sessions, not randomized trials. Actual
Mesa worker enumeration, energy and physical presentation were not measured.
All terminal and frame samples are retained in
`native/boot/attempt31/smp-vm-results.json`; quarter-pixel controls are not a
proposed native setting. The diagnostic compositor is the previous pinned
trace build, with drain mode off and visual settings unchanged.

Build in the existing Linux VM, under the project quiet lock:

```sh
printf 'build\n' > virtualization/jobs/057-smp31/out/mode
tools/vm-job.sh virtualization/jobs/057-smp31 smp31
printf 'parser\n' > virtualization/jobs/057-smp31/out/mode
tools/vm-job.sh virtualization/jobs/057-smp31 smp31
VZRUN_EXTRA='--gui --size 3456x2160' \
  tools/vm-job.sh virtualization/jobs/058-renderer-policy smp31
```

The job wrapper takes the VM lock. Check each job's `out/run.log` guest exit,
not only the VZ process exit, and release quiet after stopping. No downloads,
new disks, root-image repack or native image deployment are performed.

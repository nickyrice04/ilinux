# Attempt29 offline validation — 2026-10-20

**Offline ready. Native attempt29 NOT RUN.** M1 intake and human start remain.
The unchanged attempt28 pair already worked natively; it was not rebuilt or
relabelled as a new full-desktop VM test. New work is the small diagnostic bundle,
the separately confirmed launcher profile and bounded collection instructions.

## Exact artifacts

* Boot042 Image remains `0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c`.
* Stage one/root/CPU DT remain exactly the pins in `../attempt28/`; no image
  changes, operator overlay or new automatic module load. Installed boot021,
  client `57a9339`, all existing hardware checks and one-core limits retained.
* New bundle: **143,360 bytes**, SHA256
  **`561b6395d1ef9b6fcd2e8bfd8fcadaac0d449b2f952acd50d8d56913ff04f714`**.
  Exactly four regular members; [asset pins](assets.json), [bundle pin](bundle.json).
  Privately staged at `build/attempt29-transfer/memory29.tar`. No Apple bytes,
  credentials, keys, root filesystem or test-control module in this bundle.
* Native module: `730bdfe809dd7a7de58bab8f707db5ee593549a9c2e711d8a8e17f9727b54f7c`,
  no dependencies, matching `7.1.9-g863199d8b4a3-dirty` vermagic. It retains the
  exact board/SoC/one-core/MIDR/MPIDR guards. The isolated VM control is separate.

## Executed checks

1. Job053 builds the original module against the exact existing kernel with
   W=1, no warning/error lines in the final build. GCC16.1.1, benchmark
   `-O3 -march=armv8.4-a -Wall -Wextra -Werror`; ASan/UBSan build also passes
   all48 result rows and graph checks. Optimized shipping binary passes48 rows;
   disassembly retains the dependent `ldr x0,[x0]` loop in the timed function.
   Module disassembly contains no MSR instruction. No boot042 Image rebuild.
2. **315 controller methods PASS**, including both observation profiles, exact
   payload/fake handoff, modified-payload refusal, DT/controller/OPP/storage/
   CPU guards and old profiles. **13 M1 helper methods PASS**, including
   deadline/key/bundle rejection before SSH. **12 decoder/bundle methods PASS**,
   including malformed archive, traversal/link/duplicate and hash refusals.
   These are separate suites; do not add repeated host/VM runs as unique cases.
3. Actual final bundle receiver ran in the build VM: size/hash/member validation,
   tmpfs extraction and Python exec succeeded; collector rejected missing native
   DT before module load. A second extraction was refused. No test mocked away
   the receiver's tar/hash/filesystem operations. The M1 SSH transport itself
   remains the proven preceding-attempt path; no live M5 connection occurred.
4. The unchanged **exact boot042 Image** booted disklessly in Virtualization.framework.
   Shipping module returned **ENODEV** on virtual hardware. A separate VM-only
   identity-bypass control exercised the same snapshot and locked stack-page
   walker, returned0, and reported level3/16KiB/valid/write-back/inner-shareable
   memory. Control bytes never enter the shipping bundle. First control run's
   console log level suppressed the attribute line; a fresh loglevel7 run
   captured it and the actual collector decoder validated it. Both VMs stopped.
5. REA/Ghidra completed **five** selected driver dossiers. LLVM independently
   verified **265 instruction words** against the original carrier. Three
   whole-function pseudocode gates rejected cross-boundary operations; two
   small helpers need manual interpretation. Only bounded instruction and call-
   target facts inform the findings; no private implementation is published.
6. Short same-source macOS reference measurements and a final CPU-placement-
   tagged matrix completed under quiet locks. [Sanitized results](macos-baseline.json)
   preserve QoS, compiler and unmatched-core/frequency limits. Linux VM huge
   advice produced zero recorded PMD huge backing; it proves no huge-page speedup.

Reproduction: `tools/vm-job.sh virtualization/jobs/053-memory-observation OWNER`,
then `tools/vm-job.sh virtualization/jobs/053-memory-observation/verify OWNER`.
The verification job assumes the existing pinned controller venv from job052.
The diskless test uses its `out/refusal.cpio.gz` and boot042 Image, one vCPU,
2GiB/no disk/no network, `console=hvc0 rdinit=/init ... loglevel=7`. No VM
exposes the native memory-controller interface or validates native CPU behavior.

## Failures retained, not hidden

Private evidence is under ignored `build/attempt29/` and job053 `out/`.
Initial build lacked the read-only source mount and failed before compilation.
The next build used old `pud_sect`/`pmd_sect` names; corrected to the pinned
kernel's leaf helpers. Linking a direct-map reader failed because `init_mm`
is not exported. The final design inspects the loader's own userspace mapping.
Review then added page-table locking; the convenience map-lock helper is also
not exported, so the implementation now holds mmap's write lock to stabilize
topology and the inline PTE lock for the entry, without modifying a mapping.
The final locked reader compiles and passes the VM positive control.

An integration assertion initially expected a wrong-board string, whereas
this VM lacks `/sys/firmware/devicetree/base/compatible` entirely. The collector
had correctly stopped before module load; the test now distinguishes those two
explicit refusals. Both failed and passing records remain. Broad XNU REA
queries timed out/cancelled, with no inferred results. Initial sandboxed sysctl
and process-background-policy calls were denied; ordinary read-only metadata
and process-local benchmark runs subsequently completed with scoped execution
permission. No security setting was disabled.

## Native limits and next action

No native frequency/voltage/DRAM change, extra core, storage, Wi-Fi, desktop
reconfiguration or performance improvement is claimed. Thermal/energy feedback
remains unavailable on the native reference run. The module samples one loader
stack mapping, not every benchmark/application mapping; smaps and the matrix
provide complementary evidence. Actual native MMU readings and huge-page
backing remain unknown until the one instructed run.

M1 follows [attempt29-instructions.md](../../../tools/m1n1-client/attempt29-instructions.md),
verifies the small bundle and retained pair, publishes readiness, then waits for
the human's boot. No original-macOS, default-disk, policy, volume or firmware
changes. Routine policy rechecks stay waived. Return by the fixed switch-time
600-second window; only collectors are automatically time-bounded.

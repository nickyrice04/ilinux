# REA low-level analysis and next steps (2026-10-14)

## REA status on the M5 host

The host REA MCP server (6.4.0) runs, but it has **no deep provider**.
Ghidra reports `not_configured` (no `GHIDRA_INSTALL_DIR`), Hopper is not
installed and IDA is not configured. So decompile, pseudo-code and
call-graph tools cannot run on the host. Earlier decompilation ran in the
isolated Linux lab (`reverse-engineering/rea-lab/`). Extracted kext members
are deliberately not kept on disk, so new decompiles need that lab again.

## Why we are where we are

1. **Only one CPU starts (`cpus=1`).** m1n1 `src/smp.c:193,229` writes
   `1 << (4 * cluster + core)` to CPU_START. On t6050, ApplePMGR's
   `configMiscCores` reads the ADT `clusters` table, and our unit gives
   `(6,0), (6,6), (6,12)`. That is 6 cores per cluster at bit offsets
   0/6/12 (an REA- and LLVM-checked slice; see
   `findings/cpu-startup-2026-10-13/handoff.md`). With a 4-bit stride,
   cores 4–5 of cluster 0 alias cluster 1's bits, and every later cluster is
   misaddressed. This is hypothesis H2. It is the strongest static candidate
   for "secondaries do not start", but it is **not hardware-verified**.
   Abstract offsets also pass through t6050's `writeReg32` die/map override,
   so the physical register is not proven either.
2. **The boot stalls at P05/W00 after `deferred_probe_initcall`.** The
   deferred-probe worker shows no bus-probe progress (W00), and the scheduler
   has `pending=1`. The confirmed contributor is our own diagnostic: the
   framebuffer is repainted inside scheduler hooks while locks are held.
   Boot033 removes that. This is a Linux-side issue, so decompiling macOS
   would not explain it. Attempt 14 is the test.
3. **The parity gap is structural.** macOS gets its efficiency from PMGR
   DVFS, cluster idle (`cpuComplexIdleEnter`/`Exit` poll ACC selector
   `0xe20020` bit 31), the GPU firmware and the ANE. Linux has none of these
   for t6050 yet. Without SMP, DVFS and the deep idle states, native Linux
   cannot approach macOS performance per watt.

## Next steps, in order

1. **Run attempt 14 (boot033) as planned.** If the worker progresses, the
   P05 stall was caused by the diagnostics.
2. **Turn H2 into an exact rule with REA (lab).** Decompile
   `ApplePMGR::configMiscCores` and t6050's `writeReg32` override. Recover:
   - the bit formula (position + core vs. 4·cluster + core);
   - the register-map and die selection;
   - the zero-position fallback.

   Then write an original m1n1 patch that derives the bit from ADT
   `clusters`. Do not copy Apple's code. Test it offline against the ADT
   first, then in one guarded secondary-start attempt.
3. **Map PMGR power domains and DVFS** (`ps-regs`/`devices`, the
   performance-state tables) for cpufreq and genpd in the t6050 DT.
4. **Model idle.** Map the `cpuComplexIdleEnter`/`Exit` ACC sequence onto
   Asahi's `apple-idle`/cpuidle design, so cores reach deep idle states.
5. **Measure.** After that, continue with GPU (G17 firmware interface),
   NVMe/ANS and Wi-Fi. Measure each step against the macOS baselines in
   `reports/performance-parity.md`.

To enable host-side REA: install Ghidra 12.1.x + JDK 21 project-locally and
set `GHIDRA_INSTALL_DIR` in `.mcp.json` (requires approval), or keep using the
lab VM.

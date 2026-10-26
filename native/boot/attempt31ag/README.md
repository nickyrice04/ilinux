# 31AG: offline handoff qualification, not a new boot attempt

2026-10-26 Eastern. **No native image, installer package or experimental restart
is prepared.** The 31AF install/observation is consumed; its restoration/default
confirmation remains open. Existing boot021 and all frozen earlier records stay
unchanged.

This checkpoint contains:

* Eight fresh REA queries and independent verification of 751 instruction words
  in 22 bounded ranges. Rejected/truncated decompiler results remain rejected.
  [Analysis and limits](../../../research/native31ag-handoff.md),
  [validation](../../../reverse-engineering/findings/cpu-startup31ag/validation.json).
* Original entry-profile controls: the unchanged 31AF instructions paint under
  the supported EL2 resident fixture, silently refuse at actual EL1, and silently
  refuse raw-style arguments. Three full emulator cases PASS; the 13-method
  evidence classifier passes on host and guest. This is not a native readback
  channel. [Runtime validation](offline-validation.json).
* An original conditional reserved-range auditor, with 18 tests. It distinguishes
  a caller-supplied producer/layout relation from an actual measured Recovery
  dictionary. The published legacy inspector properties are reference data for
  our own image, not proof of the historical installation profile.
* An original read-only selected-lab-object diagnostic based on Asahi's public
  installer path contract. Thirty-four synthetic methods PASS. Its live mode
  needs local administrator authentication and has **not run by the agent**;
  the human result is pending.
  It outputs only a match label and read-only flag; private identifiers remain
  in memory. A match would not prove default selection, prior execution, SPTM
  activation or completion of the whole rollback procedure.
* A [public M4/Asahi comparison](../../../research/native31ag-asahi-m4.md).
  We already extend Asahi Linux/m1n1. Published M4 raw boot and the experimental
  resident-monitor entry contract are different controls; current startup sources
  do not provide a newly published M5 core-start repair.

There are **65 distinct unit methods** across three suites, plus three complete
emulator cases. The guest reruns the 13-method classifier subset; do not add that
rerun to the distinct count. No stock firmware emulator with security checks
patched out, private selector override, original macOS write or native monitor
call was introduced.

Two additional read-only context inspections failed identically, including the
generic reference control; neither yielded properties or a Recovery-mode
measurement. [Context records](context-controls.json). They provide no
image-specific failure diagnosis. A narrow recent diagnostic-filename check
found no matching reports; absence does not locate the native failure.

M1 follows the [current offline instructions](../../../tools/m1n1-client/attempt31ag-instructions.md).
Further native experiments require a qualified actual handoff/property context,
matching positive control or independent entry/failure observation. No new boot
approval is requested by this checkpoint.

# 31L controller review

Original RAM-only visibility hypothesis test. CPU1 is the sole secondary target
in the validated12 Performance/6 Super census. Existing reset checks/start
stores and consumed K/J/I inputs are unchanged. No macOS/installed image,
volume, security, default boot, MMIO-power or reset-vector change is included.

The existing16KiB helper allocation supplies two64-byte Normal records at
+0x1000/+0x1080 and a separate control at+0x1100. CPU0 translations must show
Normal WB/outer-shareable and expected physical addresses. Only pre-start
initialization and publication use cache maintenance; no record invalidation
occurs after a start. The separate CPU0 Normal control verifies24 reads and
2 stores, known-zero restoration and canaries. It cannot prove CPU1 visibility.

Two60-byte prefixes use x8/x9, preserve x0/SP/LR/NZCV and branch to the existing
Device recorders. All code and hook endpoints, body-before-hook ordering,
readback and whole immutable text are checked. The existing early cold path
remains contained; no relocation/shared BSS continuation is introduced.
Any Normal publication stops; committed expected MPIDR is the only positive
CPU1 identity. Uncommitted nonzero identity also stops without attribution.
Unexpected Device-only complete arrival stops before callbacks. No Linux boot,
extra core, reconnect/retry, fault cleanup or post-fault target request follows.

Review caught uncommitted identity being ignored in the first observer draft;
this was corrected and regression tested. Target-read exceptions retain partial
counts/state. ValueErrors become sanitized controller refusals. CPU0 positive
control has bounded checks before/after every callback and never restores after
a fault. Journaling a local failure is not target cleanup. The source closure
includes the full K closure and refuses changed/symlinked/noncanonical paths.

The original independent candidate review and pre-release controller review
were performed by separate sessions. Root completed integration and final
review after those sessions became unavailable; do not describe the final
integration as separately reviewed by those sessions. M1 independent intake
and review remain required before the human starts a physical session.

Limitations: no firmware model/native validation. Both channels zero remains
ambiguous; an early Normal fault can prevent the subsequent Device recorder.
A positive Normal identity does not prove the subsequent branch ran or identify
the historical cause. Stop before a comparative Device sample; do not claim
that Device visibility is proven broken. CPU0's positive result does not show
CPU1 mappings, reset provenance or Linux SMP. See validation.json for actual
executed test results, and the M1 handoff for the only live command.

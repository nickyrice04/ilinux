# 31AE Recovery installation and observation result — 2026-10-25

**Installation PASS. One lab boot showed only an Apple logo; diagnostic entry is
unconfirmed. Exact boot021 rollback and Macintosh HD return/default are reported
successful by the human. No automatic retry. Linux/live checks NOT RUN.**

## Reviewed input and authorization

Execution handoff `33c10913019c41eab7d923cd394a292fa6fa482f` follows independent
M1 review `e52528f77c9e1e1d14edf83fe77cabb591483b98`. The direct human start and
separate `attempt31ae-authorization-2026-10-25.json` cover the lab installation,
one observation, exact boot021 rollback and original/default restoration.

Candidate: 196608 bytes, SHA-256
`ccdc9c8c8ef78fda2d9e2a56550919d0c20030037486215d194e8762a85748aa`.
Recovered linked payload:
`35bcecdff17ca1b927fccdffd057c9f149577df5698f250b7dbe93f5c71fe13b`.
Install paste SHA:
`0bc65c87184e9071a4d031b4817bbd671f99fda1d8b96171964fef062d6d5c8a`;
rollback paste SHA:
`7b09569a39417c45f2dbb08787efaa0145744b059ccbfec4064efb8ee56f755e`.
Those exact reviewed blocks and HTML were reverified and served locally from the
restricted reviewed directory. The server is now stopped; listener closure
verified. No public address, server log or raw Recovery evidence is included.

## Observed installation result

The human reported Recovery browser arrival and clipboard smoke PASS. M1 issued
the unchanged complete Install block once; the human operated it on M5. The
provided installation photo shows:

- Valid Mach-O recognized; boot properties derived and payload wrapped.
- Boot object installation reached `done`.
- Configure exit **0**, capture exit **0**, install block exit **0**.
- `INSTALL_SUCCESS_ENTRY_NOT_OBSERVED`, with configure and original Full/lab
  Permissive postcheck passed.

**Confirmed from the photo:** this candidate passed the actual Recovery
installation operation. The prior 31AD format rejection did not recur in this
installation. This establishes installer acceptance for this operation, not
firmware entry or successful execution of the diagnostic.

The exact block requires the fresh lab identity, expected build, paired Recovery,
separate original, helper, rollback and Full/Permissive guard before configure.
Raw guard/postcheck files and the Recovery executable hash stayed local on M5
and were not transferred. Temporary lab-default completion was not separately
reported; do not turn the prompted flow into an additional measured result.

## Single boot observation

The human reported the first boot of the newly configured lab showed **only an
Apple logo after several minutes**. No checkerboard, diagnostic text or explicit
firmware error was reported. No photo/video of that observation was received in
this result handoff. **Entry/display-path execution remains unconfirmed.**

The instruction was one 30-second observation. The reported several-minute wait
exceeded that cap; exact duration is unknown. M1 then instructed immediate power
off and return to lab-paired Recovery, with no further lab boot before rollback.
No candidate retry was instructed or reported. The Apple logo alone does not
identify the execution or firmware stage where progress stopped, or establish
that the diagnostic never ran. No root cause is claimed.

## Rollback and return

The human subsequently reported rollback completed and Macintosh HD desktop
return. A separate follow-up confirmed **rollback configure/capture/block exits
0 / 0 / 0, the success marker, and Macintosh HD as default Startup Disk**.
These values are **human-reported**, unlike the installation values observed in
the photo. No rollback image/log, exact invocation count or separately numeric
policy-postcheck exit was received. The success marker in the reviewed rollback
block requires the postcheck; raw logs/installed slot were not independently
queried on M1. No fresh desktop policy query was run.

The reviewed rollback restores staged boot021, 3932160 bytes, SHA-256
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`,
with raw entry 2048 and lowest virtual address 0, under its own fresh guard.
No alternate flags, replacement image, security downgrade or volume operation
was guided. Original Full/lab Permissive remain the required levels.

## Preservation and next owner

All 26 source manifests verify: 5944 listed hash checks across 691 distinct
files. The 25 earlier closures, 675 prior ignored evidence files and consumed
receipts are unchanged. Client remains clean at
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`; reviewed pages remain exact. No reset
or re-arm of prior receipts, new M1 test suite, VM, USB/proxy connection, native
launcher, host restart or M1 settings change occurred. The offline 77-method PASS
is reused from the published review, not claimed as rerun.

M5 owns the next **offline analysis and proposal**. This session authorizes no
new image, repeat observation or further boot/settings operation. Diagnostic
entry is unconfirmed; monitor calls, live target-version checks, restored-boot021
proxy check, Linux, SMP, GPU and performance remain **NOT RUN**. Preserve the
installation success and inconclusive boot observation as separate outcomes.

Raw credentials, machine identifiers and media are excluded. Raw Recovery temp
file retention after reboot is unverified. Private session checkpoints remain
under ignored `build/native-intake/attempt31ae-recovery-session/`.

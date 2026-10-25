# 31AC authorized handoff — next transition is lab-paired Recovery

**Current as of 2026-10-25: M1 review passed and the human explicitly authorized
the concrete sequence.** This supersedes the approval-pending status in the
frozen package and historical review. It does not alter their bytes or convert
offline evidence into a native result.

Read this first, then follow the unchanged
[reviewed Recovery procedure](attempt31ac-instructions.md). Do not repeat the
completed M1 review, restart the M1, run a proxy launcher, or provision the lab
again. The M1 remains in ordinary macOS as the instructions/transfer helper.

## Approval and present checkpoint

The human's instruction was:

> M1 pushed the 31AC review. Check it, and if it passed, go ahead with the lab-only
> boot replacement, temporary Startup Disk changes, one test and boot021 rollback.
> Keep Macintosh HD at Full Security and tell me when to restart.

M1's `f6fae6c` review of `8c5b691` is PASS with no actionable offline blocker.
The previously missing approval is now given, including the possible preparatory
boot021 start to apply the temporary default selection. This is one experiment,
not permission for automatic retries or subsequent changed images.

M5 rechecked the archive, all 31 source pins, and the existing staged rollback
and helper without executing them. All match. In System Settings → Startup Disk,
the human completed authentication and the UI now explicitly says **iLinux Boot
Lab selected**. The agent has not clicked **Restart…**. Selection alone is not a
confirmed completed default-change flow. No candidate installation, restart,
diagnostic observation or rollback installation has occurred at this checkpoint.

## Next restart — M1 guides the human

1. Keep these instructions on the M1 before restarting the M5. Keep AC connected
   and save M5 work. The M1 does not need a restart.
2. On M5, complete the visible **Restart…** flow for the selected **iLinux Boot
   Lab**, checking the target name in any confirmation. Allow the existing
   boot021 screen to appear if required to apply the selection. Do not connect
   a proxy client. Hold power to shut down.
3. From shutdown, hold power continuously until Startup Options; choose
   **Options → Continue**. The next task is Recovery, not launching Linux.
4. In M5 Recovery Terminal, follow section 2 of the frozen procedure. Its guard
   must verify the separate lab System/Data group, build, exact staged rollback,
   original Full/lab Permissive and **lab-paired 1TR** before a write. Do not run
   the older helper's Full/Full `ilinux_preflight` function. This identity/pairing
   guard is required for this new target write; no additional routine desktop
   policy check is requested.

## Transfer, install, observe and restore

Follow frozen sections 3–7 in order, without changing their commands:

- Use the already verified M1 package. If needed, serve **only its extracted
  package directory** with the bounded local-network HTTP server in section 3,
  download the candidate into Recovery `/tmp`, and stop the server after transfer.
  Never serve the repository, personal files or private research. Do not overwrite
  the staged `m1n1.bin`. Keep local addresses and identifiers out of public reports.
- The exact candidate is **180224 bytes**, SHA-256
  `261d44447442f32ba6c41bbf0f69179e8c9eb4c33507b60762f0ea8c2e54ab72`.
  Compare against the independently reviewed manifest. Install it **once** in
  Mach-O mode, **without `--raw`**, using section 4, targeting only the lab.
- Only after installation exit 0 and the required checks pass, shut down and
  select the lab once from Startup Options. Observe for **30 seconds**. Look
  closely at the **32 × 16 pixel bordered checkerboard at the top-left**; record
  a visible pattern, no pattern, or actual displayed firmware error separately.
  Then power off. No USB proxy, SPTM call or secondary release is part of this test.
- With the lab still the default, enter paired Recovery again. Re-enter the
  guard definitions in the new Terminal and require a fresh PASS. Restore the
  exact pre-existing boot021 via section 6's raw command, with entry **2048** and
  lowest virtual address **0**. Its hash is
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
- After successful rollback and checks, return to **Macintosh HD**. Restore it as
  default Startup Disk through the completed Apple flow, including its ordinary
  restart if required. No extra boot021 execution or handshake is needed.

If configure fails, do not assume it left the lab slot unchanged. Preserve the
sanitized error and exit code; do not change flags or retry the candidate. The
reviewed rollback is allowed only while its identity/policy guard still passes.
If that guard fails, stop and report rather than guessing targets or reducing
security. No erase, firmware, DFU, volume operation, new security downgrade or
change to Macintosh HD's Full Security is authorized.

## Report after the run

Publish a new sanitized result referencing the reviewed candidate and this
authorization. Record each actual transition: temporary default confirmation,
paired-Recovery guard, install exit, observation duration/outcome, fresh rollback
guard, restore exit, return to Macintosh HD and final default restoration.
Distinguish human observations from independently measured evidence. Do not
publish identifiers, raw policy/disk output or unredacted Recovery photographs.

A visible marker establishes this original entry/display path only. An absent
marker is inconclusive. Neither outcome establishes monitor readiness, physical
secondary startup or an Apple-only restriction. Linux, SMP, GPU and performance
remain **NOT RUN** for 31AC. Do not repeat an unchanged attempt.

The frozen manifest's `install_authorized: false` and review's approval-pending
fields describe their publication time. Preserve them; the separate
[authorization receipt](../../native/boot/attempt31ac-authorization-2026-10-25.json)
records this later human decision.

# J716c native handoff — attempt 27 consumed; CPU preparation next

**Native attempt 27 completed on 2026-10-20.** Two-stage delivery, Omarchy,
the second USB/SSH link and automatic keyboard startup passed. The user typed
without extra letters but menus/apps remain slow. Read the
[native result](stage-b-2026-10-20-attempt27-result.md) and
[current workstation plan](post-attempt27-plan-2026-10-20.md).

M1: the [Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md)
is consumed. Retain the files/receipts and await a new pinned handoff. Proposed
attempt 28 is separate CPU baseline/bounded-frequency work; it is not yet a
ready package or live authorization. No restart is needed for this review.

[Attempt 26](stage-b-2026-10-19-attempt26-result.md) already booted Omarchy
natively, established USB/SSH, enabled the internal keyboard manually and ran
for 63 minutes 34 seconds. It measured severe software-rendering latency on one
CPU. This is the existing installation; do not repeat entry provisioning.

Attempt 27 uploaded a small stage one through m1n1 and sent the new Omarchy root
over the established USB SSH pipe. The root includes the repeat-delay,
menu-poller, weather, keyboard-startup/rerun and SSH fixes. The native checks
covered full-size transfer integrity, the root switch, USB reconnection and
automatic keyboard startup. Menu cleanup remains inconclusive; consult the
result for all qualifications rather than assuming every image fix passed.

The [boot042 package](boot042-keyboard-modules-2026-10-19.md), installed boot021
m1n1, client pin and launcher remain unchanged. Keep Macintosh HD at Full
Security and as the default. No security, volume, firmware, bootloader or host
network-setting changes. NVMe and cpufreq remain disabled; only one CPU is
online. The CPU-first plan supersedes the old storage-attempt-28 assignment;
storage and CPU work still need separate reviewed launcher profiles. Routine
policy rechecks remain waived; Full/Permissive are last reported, not newly
verified by this review.

`package-manifest.json`, `archive-sha256.txt` and `intake-manifest-sha256.txt`
still describe `native-j716c-boot042`. `ramroot-manifest.json` describes stage
one; `omarchy-root-manifest.json` describes stage two. Both images, test
overlays, raw diagnostics and proprietary artifacts stay out of this public
repository and Releases.

This is a RAM boot with no intentional target filesystem writes. m1n1 and
Linux still initialize hardware and access RAM/registers. VM passes establish
software behavior, not native controller support, GPU acceleration or measured
macOS-level performance. [The continuation plan](resume-plan-2026-10-19.md)
records the completed side-session recovery; use the current workstation plan
above for priorities and the [Claude workflow](claude-workflow.md) for context.

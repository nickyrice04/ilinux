# J716c native handoff — current attempt31C

**Current:** use [31C CPU1 instructions](../../tools/m1n1-client/attempt31c-instructions.md)
and [31B review/31C validation](attempt31c/review.md). M5 preparation PASS; M1
intake pending; native31C NOT RUN. 31B stopped before allocation/start because
of the RAM-range gate; 31C checks the actual high-address memory map.
Existing installed boot021, one CPU1 start
and two bounded parked-loop requests, then Macintosh HD. No Linux launch or
new boot image. Census31A, 31B and earlier attempts are consumed. The historical
attempt28 directions below are context, not the next live command.

## Historical handoff — attempt 28 CPU observation

**Native attempt 27 completed on 2026-10-20.** Two-stage delivery, Omarchy,
the second USB/SSH link and automatic keyboard startup passed. The user typed
without extra letters but menus/apps remain slow. Read the
[native result](stage-b-2026-10-20-attempt27-result.md) and
[current workstation plan](post-attempt27-plan-2026-10-20.md).

M1: use the new [attempt-28 checklist](../../tools/m1n1-client/attempt28-instructions.md)
and [validation/pins](attempt28/validation.md). The CPU observation package
adds a separate launcher profile and bounded collector with frequency writes
disabled. First independently verify both private images, then await the human
start. Native attempt 28 remains NOT RUN; attempt 27 is consumed.

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
m1n1 and client pin remain unchanged. The new launcher adds only the separate
CPU observation profile with exact input/prepared-tree checks. Keep Macintosh HD at Full
Security and as the default. No security, volume, firmware, bootloader or host
network-setting changes. NVMe remains disabled; only one CPU is online.
CPU observation explicitly permits command reads through a no-write module;
older profiles continue disabling cpufreq. Storage is a separate later attempt. Routine
policy rechecks remain waived; Full/Permissive are last reported, not newly
verified by this review.

`package-manifest.json`, `archive-sha256.txt` and `intake-manifest-sha256.txt`
still describe `native-j716c-boot042`. `ramroot-manifest.json` describes stage
one for attempt 27; `omarchy-root-manifest.json` describes that older stage two.
Attempt 28 uses the separate manifests under `attempt28/`. Both images, test
overlays, raw diagnostics and proprietary artifacts stay out of this public
repository and Releases.

This is a RAM boot with no intentional target filesystem writes. m1n1 and
Linux still initialize hardware and access RAM/registers. VM passes establish
software behavior, not native controller support, GPU acceleration or measured
macOS-level performance. [The continuation plan](resume-plan-2026-10-19.md)
records the completed side-session recovery; use the current workstation plan
above for priorities and the [Claude workflow](claude-workflow.md) for context.

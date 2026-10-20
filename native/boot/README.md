# J716c native handoff — attempt 27: two-stage Omarchy on boot042

**Handoff approved for publication on 2026-10-20; native attempt 27 and live checks NOT RUN.**
M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md)
after the reviewed handoff is published. Read the
[validation record](attempt27-two-stage-validation.md), verify both privately
delivered images and the existing boot042 package, publish offline readiness,
then wait for the human's start.

[Attempt 26](stage-b-2026-10-19-attempt26-result.md) already booted Omarchy
natively, established USB/SSH, enabled the internal keyboard manually and ran
for 63 minutes 34 seconds. It measured severe software-rendering latency on one
CPU. This is the existing installation; do not repeat entry provisioning.

Attempt 27 uploads a small stage one through m1n1 and sends the new Omarchy root
over the established USB SSH pipe. The root includes the repeat-delay,
menu-poller, weather, keyboard-startup/rerun and SSH fixes. The native checks
are full-size transfer integrity, the root switch, USB reconnection, automatic
keyboard startup and those image fixes.

The [boot042 package](boot042-keyboard-modules-2026-10-19.md), installed boot021
m1n1, client pin and launcher remain unchanged. Keep Macintosh HD at Full
Security and as the default. No security, volume, firmware, bootloader or host
network-setting changes. NVMe and cpufreq remain disabled; only one CPU is
online. Storage is attempt 28 behind a separately reviewed launcher change;
the offline frequency/SMP work is not in this attempt.

`package-manifest.json`, `archive-sha256.txt` and `intake-manifest-sha256.txt`
still describe `native-j716c-boot042`. `ramroot-manifest.json` describes stage
one; `omarchy-root-manifest.json` describes stage two. Both images, test
overlays, raw diagnostics and proprietary artifacts stay out of this public
repository and Releases.

This is a RAM boot with no intentional target filesystem writes. m1n1 and
Linux still initialize hardware and access RAM/registers. VM passes establish
software behavior, not native controller support, GPU acceleration or measured
macOS-level performance. [The continuation plan](resume-plan-2026-10-19.md)
and [Claude workflow](claude-workflow.md) describe the next tracks.

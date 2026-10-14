# J716c native handoff — attempt 14 / boot033

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
Verify private boot033, publish readiness, then one filmed human-started RAM
boot and Macintosh HD return. **Native attempt 14/live checks NOT RUN.**
Preserve installed boot021/current entry; no repeated setup or settings changes.

[Attempt 13](stage-b-2026-10-14-attempt13-result.md) passed controller GPIO gates
but showed no attributed GPIO operation or native userspace. [Boot033](../../kernel/experiments/scheduler-ram-only/README.md)
removes full-panel rendering from scheduler checkpoints, retaining RAM state
and watchdog-sampled S. This fixes instrumentation overhead; the native effect
remains unproven. Boot032's five GPIO exclusions and all hardware gates remain.

Only Image changes. Full Image/ELF roundtrip, actual-hook sanitizer regression,
102 controller cases, 13-file intake and 13+8 intake/evidence cases PASS. Linked
hook has 14 instructions and no calls, verified against packaged Image.
Exact-image one-CPU/4-GiB diskless/networkless VZ reaches PID 1 and 60s liveness
at 60.192455 kernel seconds. This does not validate physical GPIO/IRQs or parity.
User reports post-attempt-13 Full/Permissive; original-root/build/FileVault/SIP/
staged-m1n1 read-only checks PASS. No fresh policy exit codes supplied, no settings
changed, default/installed object/authenticated-root not rechecked.

Private prerelease `native-j716c-boot033` carries the archive pinned by
`archive-sha256.txt`, `intake-manifest-sha256.txt`, `package-manifest.json`.
Prior manifests through boot032 remain. No Apple artifacts or raw data published.
[Claude handoff](claude-workflow.md) explains roles and targeted REA workflow.
Native userspace/control remain prerequisites for a Linux-side agent and Omarchy.

Build foundation: kernel base `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` plus
t6050 patches 0001–0007, with job024's original instrumentation, job025's restricted AIC patch and
job027's deferred-probe diagnostics, job028's scheduling-boundary instrumentation,
job029's display/context instrumentation and job030's probe-path diagnostics and job031's GPIO handoff repair and job032's reserved GPIO support, plus job033's RAM-only scheduler instrumentation.
GCC 16.1.1, Linux 7.1.9, original 16-KiB config. The separate post-link DockChannel proof
patch remains absent. m1n1 is still the unmodified pin
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`, marker
`##m1n1_ver##ilinux-57a9339-boot021`; the source-guard proof binary from job023
is not installed or included as a replacement.

The Stage-B DT adds the boot032 main-GPIO reserved ranges and still disables NVMe and cpufreq and provides the
framebuffer placeholder filled by m1n1. The effective DT must expose exactly
one CPU and a valid enabled framebuffer. The noninteractive diagnostic
initramfs still mounts only proc/sys/devtmpfs, prints PID 1 and five-second
heartbeats, and has no shell/network/SSH/resident agent. No secondary starts,
cpufreq initialization, upstream `m1n1.setup`, or PMU counter reset is requested.

The USB proxy ends at native handoff. There is no Linux USB console or guaranteed
crash recorder in this package. m1n1's phram log is not a Linux panic log. Screen
recording and explicit milestone reporting are required for this attempt.
Controller success alone is not native Linux success; VM liveness and synthetic
framebuffer tests are not native compatibility or performance measurements.

This is a RAM boot, with no intentional target filesystem writes; m1n1 and
Linux still perform hardware initialization and RAM/register accesses. The
original macOS remains protected. Existing entry provisioning is historical
in [boot-entry-setup.md](../../kernel/native-enablement/boot-entry-setup.md);
do not repeat it. The longer [native plan](../../kernel/native-enablement/first-boot-plan.md)
places later input/network, persistent root, configuration-agent and desktop
work after the first verified Linux liveness milestone.

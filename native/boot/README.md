# J716c native handoff — attempt 8 / boot027

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
It contains the new package/intake commands, exact tests/hashes, readiness,
one filmed launch and Macintosh HD return. **Native attempt 8 NOT RUN.**
Keep the established Boot Lab entry and installed boot021 m1n1. Do not repeat
provisioning, Recovery, Stage A or installation; no boot/security/volume changes.

Attempt 7 reached later Linux initialization and stopped visibly at
`deferred_probe_initcall`. [M1's report](stage-b-2026-10-14-attempt7-result.md)
does not prove the blocking PC. Exact REA/source show a debugfs call and two
worker flushes. [Boot027 diagnostics](../../kernel/experiments/deferred-probe/README.md)
identify those boundaries, test counter/tick progress and report worker/retry
state. Both flushes remain. Root cause is unknown; no additional initcall skip.

Only **Image** differs from boot025. The fixed `ilinux_probe_diag=1` argument
activates diagnostics; the sole clock-debug skip is retained. Hardware checks
now verify t6050 CPU topology, AIC3 geometry and timer routes in the packaged
and effective DT. Existing chip/board/pin/DAPF/framebuffer/one-core/storage gates
remain. The receipt's stale provisioning hint is corrected to the current stage.

Full Image/ELF link, 11 actual-helper sanitizer scenarios, 90 controller cases
and 13-file intake PASS. Exact Image/initramfs in diskless/networkless generic
VZ reports timer PASS/25 ticks in 100 ms, phases 1–9, PID 1/one CPU and the
60-second checkpoint. This is not native M5 interrupt/driver validation.
Fresh post-attempt-7 original Full/lab Permissive policy JSON already PASS.

The private prerelease `native-j716c-boot027` carries the 16.7 MB archive.
`archive-sha256.txt`, `intake-manifest-sha256.txt` and `package-manifest.json`
pin its bytes. Keep prior packages/receipts; `boot021-package-manifest.json`
`boot022-package-manifest.json`, `boot024-package-manifest.json` and
`boot025-package-manifest.json` preserve
payload baselines. Binaries are
release assets, never Git history. No Apple binary, raw device tree, serial,
credential or personal file is in the package.

Build foundation: kernel base `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` plus
t6050 patches 0001–0007, with job024's original instrumentation, job025's restricted AIC patch and
job027's bounded deferred-probe diagnostics. GCC 16.1.1,
Linux 7.1.9, original 16-KiB config. The separate post-link DockChannel proof
patch remains absent. m1n1 is still the unmodified pin
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`, marker
`##m1n1_ver##ilinux-57a9339-boot021`; the source-guard proof binary from job023
is not installed or included as a replacement.

The boot022 Stage-B DT still disables NVMe and cpufreq and provides the
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

# J716c native handoff — boot025 restricted AIC bring-up

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
It contains download/checksum/test commands, readiness reporting, the one-shot
launch command, screen-recording requirements and the Macintosh HD return plan.
Complete offline readiness before the human restarts. Native attempt 6 is
**NOT RUN**. No installation, Recovery, volume/security/default changes or
m1n1 reinstall are part of this handoff.

Attempt 5 reached readable native Linux, then an undefined instruction at
`aic_init_cpu+0x9c`. Exact boot024 disassembly identifies the legacy guest-timer
FIQ enable write. See the [attempt-5 report](stage-b-2026-10-13-attempt5-result.md)
and [REA evidence, implementation and tests](../../kernel/experiments/aic-t6050/README.md).

Boot025 adds an exact t6050 AIC profile: preserve host timers/fast IPIs, mask
unused guest timers through architectural registers, withhold unsupported
legacy guest IRQ/KVM handling and avoid unvalidated legacy uncore accesses.
Only `Image` differs from boot024. Every other payload and installed boot021
m1n1/client pin remain unchanged. The early framebuffer console/rectangles,
96-byte DAPF RAM correction, verified 16-byte framebuffer descriptor and all
controller gates remain. No installed boot files are patched.

The full Image build, 38 actual-driver scenarios with ASan/UBSan, 65 controller
cases, 13-file intake and exact packaged generic VM PID-1/one-CPU/60-second
liveness check pass. Native AIC/timer behavior remains unvalidated.

The private prerelease `native-j716c-boot025` carries the 16.7 MB archive.
`archive-sha256.txt`, `intake-manifest-sha256.txt` and `package-manifest.json`
pin its bytes. Keep prior packages/receipts; `boot021-package-manifest.json`
`boot022-package-manifest.json` and `boot024-package-manifest.json` preserve
payload baselines. Binaries are
release assets, never Git history. No Apple binary, raw device tree, serial,
credential or personal file is in the package.

Build foundation: kernel base `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` plus
t6050 patches 0001–0007, with job024's original instrumentation and job025's restricted AIC patch. GCC 16.1.1,
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

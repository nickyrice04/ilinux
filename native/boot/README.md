# J716c native handoff — attempt 12 / boot031

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
Verify the private package, publish readiness, then one filmed human-started RAM
boot and Macintosh HD return. **Native attempt 12/live checks NOT RUN.**
Preserve installed boot021/current entry and all gates. No repeated setup or
boot/security/volume changes.

[Attempt 11](stage-b-2026-10-14-attempt11-result.md) identifies main GPIO/pinctrl
callback entry at D=C=0059/B63. [Boot031](../../kernel/experiments/gpio-handoff/README.md)
repairs t6050 cache bounds and inherited-IRQ handoff, adding 17 internal stages.
This is a candidate fix; no exact native fault or performance improvement proven.
REA evidence explicitly rejects cross-boundary Apple pseudocode and relies on
independently verified instructions/public Linux source. No Apple code copied.

Only Image changes from boot030. Full link/ELF roundtrip, actual-code sanitizer
regressions, 90 controller cases and 13-file intake PASS. Exact-image one-CPU/
4 GiB diskless/networkless VM reaches PID 1 and 60s liveness at **60.189741 s**.
Native GPIO/AIC/MMIO remain untested by VZ. User post-attempt-11 Full/Permissive
policies and independent original macOS return checks PASS.

Private prerelease `native-j716c-boot031` contains the 16.7 MB archive, pinned by
`archive-sha256.txt`, `intake-manifest-sha256.txt`, `package-manifest.json`.
Prior manifests through boot030 remain. No Apple binaries, raw host DT or
personal data in Git/release. Record GPIO handoff counts/errors, probe return,
all panel rows and userspace separately. Preserve previous attempts.

Build foundation: kernel base `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` plus
t6050 patches 0001–0007, with job024's original instrumentation, job025's restricted AIC patch and
job027's deferred-probe diagnostics, job028's scheduling-boundary instrumentation,
job029's display/context instrumentation and job030's probe-path diagnostics and job031's GPIO handoff repair.
GCC 16.1.1, Linux 7.1.9, original 16-KiB config. The separate post-link DockChannel proof
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

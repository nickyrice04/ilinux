# J716c native handoff — attempt 9 / boot028

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
It has exact package/tests/hashes, readiness, one filmed launch and Macintosh HD
return. **Native attempt 9 NOT RUN.** Keep the established lab entry and installed
boot021 m1n1. No repeated provisioning/Recovery/Stage A or settings changes.

[Attempt 8](stage-b-2026-10-14-attempt8-result.md) proves native timer progress
(25 ticks/100 ms) but stops visibly before diagnostic phase 2. Exact REA/source
identify a gap: boot027 can reschedule before its watchdog is armed. The idle
NOP branch already exists. The native cause remains unknown.

[Boot028](../../kernel/experiments/schedule-boundary/README.md) pre-arms the
watchdog, adds scheduler checkpoints and one bounded stack, and writes a small
P/S/W/H status strip in existing framebuffer RAM without printk or timer IRQs.
It is a diagnostic correction, not a claimed fix of the native hang. Only Image
differs from boot027. DT/config/initramfs/m1n1, arguments and hardware guards
are unchanged; the sole clock-debug skip remains. No device work is bypassed.

Full Image/ELF link, actual-helper/renderer ASan/UBSan, 90 controller cases and
13-file intake PASS. Exact Image/initramfs in one-CPU diskless/networkless VZ
reports timer PASS, pending reschedule, phase 13, all later phases, PID 1/one CPU
and 60-second liveness. No native AIC or framebuffer is tested by that VM.
Fresh post-attempt-8 original Full/lab Permissive policy JSON already PASS.

Private prerelease `native-j716c-boot028` carries the 16.7 MB archive.
`archive-sha256.txt`, `intake-manifest-sha256.txt` and `package-manifest.json`
pin its bytes. Prior boot021/022/024/025/027 manifests preserve baselines.
Release binaries stay outside Git history. No Apple binary/raw DT/personal data
is included. Keep previous receipts/results. M1 must review the video and
capture the small bottom-left status strip before reporting observations.

Build foundation: kernel base `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` plus
t6050 patches 0001–0007, with job024's original instrumentation, job025's restricted AIC patch and
job027's deferred-probe diagnostics and job028's scheduling-boundary instrumentation. GCC 16.1.1,
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

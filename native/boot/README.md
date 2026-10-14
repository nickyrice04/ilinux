# J716c native handoff — attempt 10 / boot029

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
It contains exact package/tests/hashes, offline readiness, one filmed launch and
Macintosh HD return. **Native attempt 10/live checks NOT RUN.** Keep the existing
lab entry and installed boot021; no repeated provisioning, Recovery or Stage A.

[Attempt 9](stage-b-2026-10-14-attempt9-result.md) observes native timer progress,
phases 1/10/11/12 and pending=1/strip=0. Phase 13 and diagnostic userspace are
unobserved. REA/source and an actual-function regression test confirm that the
old diagnostic mapper skips absent/retired consoles. The native strip failure's
specific prerequisite and the native hang cause remain unknown.

[Boot029](../../kernel/experiments/context-display/README.md) initializes the
strip independently from validated DT, reports preparation/mapping status,
enlarges its glyphs and adds context-switch checkpoints. Only Image changes
from boot028. It repairs a diagnostic lifecycle defect, not a demonstrated
native scheduler fault. Full source/LLVM/linked-byte review supplements REA's
incomplete context-switch output; no Apple binary extraction was needed.
DT/config/initramfs/m1n1, args and hardware gates remain unchanged. No new skip.

Full Image/ELF roundtrip, actual-helper/renderer/parser/mapper ASan/UBSan,
old-defect reproduction, 90 controller cases and 13-file intake PASS. Exact
Image/initramfs in one-CPU/4 GiB diskless/networkless VZ report pending=1,
phase 13/all later phases, PID 1/one CPU and liveness at 60.192201 seconds.
Generic strip=0/display=1 is expected; no native AIC/scanout is tested in VZ.
Fresh post-attempt-9 original Full/lab Permissive policy JSON already PASS.

Private prerelease `native-j716c-boot029` carries the 16.7 MB archive.
`archive-sha256.txt`, `intake-manifest-sha256.txt` and `package-manifest.json`
pin its bytes. Prior manifests through boot028 preserve baselines. Release
binaries stay outside Git history. No Apple binary/raw DT/personal data is
included. M1 verifies/publishes readiness before the human restarts, then
captures display state and literal enlarged P/S/W/H values. Review the video
before reporting; preserve prior receipts/results and report visibility limits.

Build foundation: kernel base `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` plus
t6050 patches 0001–0007, with job024's original instrumentation, job025's restricted AIC patch and
job027's deferred-probe diagnostics, job028's scheduling-boundary instrumentation
and job029's display/context instrumentation. GCC 16.1.1,
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

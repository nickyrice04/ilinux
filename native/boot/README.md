# J716c native handoff — attempt 11 / boot030

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
It includes package/tests/hashes, readiness, one filmed launch, decoding and
Macintosh HD return. **Native attempt 11/live checks NOT RUN.** Preserve installed
boot021/current lab entry; no provisioning, Recovery, Stage A or settings changes.

[Attempt 10](stage-b-2026-10-14-attempt10-result.md) directly reads P:05 S:09 W:04:
source places that at the first deferred-work flush and before bus probing.
Three lanes now render natively; H/small fields/userspace remain unobserved or
unconfirmed. No exact driver/fault established. [Boot030](../../kernel/experiments/probe-path/README.md)
adds 56 operation boundaries, 286 public DT device indexes and a four-row panel.
D identifies the root retry; C the last marked device; B the operation. Decode
literal values offline. REA/source/LLVM/linked-byte evidence supports the static
call path, not a native root-cause diagnosis or working desktop.

Only Image changes from boot029. DT/config/initramfs/m1n1/args/hardware gates and
the single clock-debug skip remain unchanged. Full Image/ELF roundtrip, actual
helper/panel/identity/platform-probe/parser sanitizers, 90 controller cases and
13-file intake PASS. Exact Image/initramfs in one-CPU/4 GiB diskless/networkless
VZ reaches all phases/PID 1/one CPU and liveness at 60.190510 seconds. Generic
strip=0/display=1 is expected; no native AIC/MMIO/scanout is exercised by VZ.
Post-attempt-10 original Full/lab Permissive JSON already PASS.

Private prerelease `native-j716c-boot030` contains the 16.7 MB archive.
`archive-sha256.txt`, `intake-manifest-sha256.txt` and `package-manifest.json`
pin it. Prior manifests through boot029 preserve baselines. Release binaries
remain outside Git history; no Apple binaries/raw host DT/personal data included.
M1 publishes readiness before restart, films all four panel rows through the stop
criterion and reviews early/final frames before reporting. Preserve prior results.

Build foundation: kernel base `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` plus
t6050 patches 0001–0007, with job024's original instrumentation, job025's restricted AIC patch and
job027's deferred-probe diagnostics, job028's scheduling-boundary instrumentation,
job029's display/context instrumentation and job030's probe-path diagnostics.
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

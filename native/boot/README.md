# J716c native handoff — attempt 18 / boot038 (the USB control channel, ACM + ECM)

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
Verify private boot038, publish readiness, then one human-started RAM boot,
filmed, read over the ACM serial port and reached over SSH, and Macintosh HD
return. **Native attempt 18/live checks NOT RUN.** Preserve installed
boot021/current entry; no repeated setup, security, volume or network-settings
changes.

[Attempt 17](stage-b-2026-10-16-attempt17-result.md) proved the Linux side of
boot036's USB link on hardware (three dwc3 cores, the gadget, enumeration in
8 s, no faults) and found that macOS 26.0.1 on the M1 has no CDC-EEM driver.
[boot038](boot038-control-channel-2026-10-16.md) changes only the gadget's
functions: a CDC-ACM serial port that carries the kernel log (written only by
the M5) plus CDC-ECM networking with key-only SSH for the M1's own key. Image,
kernel config, Stage-B DT, m1n1 and the launcher are byte-identical to boot036.

Private prerelease `native-j716c-boot038` carries the archive pinned by
`archive-sha256.txt`, `intake-manifest-sha256.txt`, `package-manifest.json`.
Prior manifests through boot036 remain. No Apple artifacts or raw data published.
[Claude handoff](claude-workflow.md) explains roles and targeted REA workflow.

Build foundation: kernel base `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` plus
t6050 patches 0001–0007 and every experiment through job 036's genpd fix and
release ladder, with `USB_LIBCOMPOSITE=y` and `USB_CONFIGFS=y` (job 041). The
Image is reproducible (pinned build time, user and host) and the shipped
`kernel.config` is the config embedded in it (`kconfig_guard.py`). m1n1 is the
unmodified pin `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, marker
`##m1n1_ver##ilinux-57a9339-boot021`.

The Stage-B DT is boot036's: no SMC-owned domains, GPIO reserved ranges, NVMe
and cpufreq disabled, the framebuffer placeholder filled by m1n1, three dwc3
device-mode cores, the ATC 0–2 domains disabled. The initramfs keeps the
diagnostic PID 1 (proc/sys/devtmpfs, PID 1 and five-second heartbeats) and adds
the two-function gadget, an IPv6 link-local address and key-only dropbear; it
has no password login, no IPv4, and nothing reads from the serial port.

This is a RAM boot, with no intentional target filesystem writes; m1n1 and
Linux still perform hardware initialization and RAM/register accesses. The
original macOS remains protected. Existing entry provisioning is historical
in [boot-entry-setup.md](../../kernel/native-enablement/boot-entry-setup.md);
do not repeat it.

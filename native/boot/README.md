# J716c native handoff — attempt 17 / boot036 (the USB control channel)

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
Verify private boot036, publish readiness, then one human-started RAM boot,
filmed and reached over SSH, and Macintosh HD return. **Native attempt 17/live
checks NOT RUN.** Preserve installed boot021/current entry; no repeated setup,
security, volume or network-settings changes.

[Attempt 16](stage-b-2026-10-15-attempt16-result.md) gave the first stable
native baseline: boot035 ran the whole 74-domain release ladder and stayed alive
past 108 s. [boot036](boot036-control-channel-2026-10-15.md) adds a CDC-EEM USB
network link and key-only SSH into native Linux over the M1 cable: the gadget
stack built into the kernel, three dwc3 device-mode cores on the PHY state m1n1
leaves, the ATC 0–2 power domains left alone, and an `/init` that sets up one
gadget per controller and dropbear for the M1's own key.

Private prerelease `native-j716c-boot036` carries the archive pinned by
`archive-sha256.txt`, `intake-manifest-sha256.txt`, `package-manifest.json`.
Prior manifests through boot035 remain. No Apple artifacts or raw data published.
[Claude handoff](claude-workflow.md) explains roles and targeted REA workflow.

Build foundation: kernel base `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` plus
t6050 patches 0001–0007 and every experiment through job 036's genpd fix and
release ladder, now with `USB_LIBCOMPOSITE=y` and `USB_CONFIGFS=y` (job 041).
The Image is reproducible: job 041 pins the build time, user and host, and two
builds gave the same bytes. The shipped `kernel.config` is the config embedded
in the Image, which `make-package.py` checks (`kconfig_guard.py`). m1n1 is
still the unmodified pin `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, marker
`##m1n1_ver##ilinux-57a9339-boot021`.

The Stage-B DT is boot035's (no SMC-owned domains, GPIO reserved ranges, NVMe
and cpufreq disabled, the framebuffer placeholder filled by m1n1) plus the USB
nodes. The effective DT must expose exactly one CPU and a valid enabled
framebuffer. The initramfs keeps the diagnostic PID 1 (proc/sys/devtmpfs, PID 1
and five-second heartbeats) and adds the USB gadget, an IPv6 link-local address
and key-only dropbear; it has no password login and no IPv4.

The m1n1 USB proxy ends at native handoff; Linux then presents its own USB
device on the same cable. Controller success alone is not native Linux
success; VM liveness and the VM USB self-test are not native compatibility or
performance measurements.

This is a RAM boot, with no intentional target filesystem writes; m1n1 and
Linux still perform hardware initialization and RAM/register accesses. The
original macOS remains protected. Existing entry provisioning is historical
in [boot-entry-setup.md](../../kernel/native-enablement/boot-entry-setup.md);
do not repeat it.

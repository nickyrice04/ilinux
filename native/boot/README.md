# J716c native handoff — attempt 19: the Omarchy RAM root on boot035

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
Verify the boot035 package (attempt 16's) and the privately delivered RAM-root
image, publish readiness, then one human-started RAM-root boot, filmed, and
Macintosh HD return. **Native attempt 19/live checks NOT RUN.** Preserve
installed boot021/current entry; no repeated setup, security, volume or
network-settings changes.

[Attempt 16](stage-b-2026-10-15-attempt16-result.md) made boot035 the first
stable native baseline. Attempts [17](stage-b-2026-10-16-attempt17-result.md)
and [18](stage-b-2026-10-16-attempt18-result.md) brought up the USB controllers
but not yet a working link. Attempt 19 launches boot035 unchanged with the
launcher's RAM-root profile ([profile notes](ramroot-profile-2026-10-15.md)):
the Arch RAM root from VM job 039 run 30, pinned in `ramroot-manifest.json`,
with Hyprland on simpledrm and software rendering on one CPU. boot035's DT has
no USB controllers, so this attempt involves no USB link at all.

The handoff records (`package-manifest.json`, `archive-sha256.txt`,
`intake-manifest-sha256.txt`) are boot035's, the private prerelease
`native-j716c-boot035`. The RAM-root image is never committed or published:
it holds its SSH host key and reaches the M1 privately. Prior manifests remain.
[Claude handoff](claude-workflow.md) explains roles and targeted REA workflow.

This is a RAM boot, with no intentional target filesystem writes; m1n1 and
Linux still perform hardware initialization and RAM/register accesses. The
original macOS remains protected. Existing entry provisioning is historical
in [boot-entry-setup.md](../../kernel/native-enablement/boot-entry-setup.md);
do not repeat it.

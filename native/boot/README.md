# J716c native handoff — attempt 25: Omarchy itself with the USB link and Claude Code, on boot041

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
Re-verify the boot041 package, verify the privately delivered Omarchy image with the link, build
and review `usb-pipe`, publish readiness, then one human-started boot with `--profile omarchy`,
filmed, with the SSH session, the clock step, web access through the M1 and the human's Claude
sign-in, and Macintosh HD return. **Native attempt 25/live checks NOT RUN.** Preserve installed
boot021/current entry; no repeated setup, security, volume or network-settings changes.

[Attempt 24](stage-b-2026-10-18-attempt24-result.md) proved boot041's USB link from the M5 to the
M1 for ten minutes. [Attempt 22](stage-b-2026-10-18-attempt22-result.md) proved the installer-built
Omarchy desktop on the M5. Attempt 25 joins them: Omarchy's own root, built with the link, Claude
Code and Omarchy's passwordless-sudo grant (VM job 045,
[report](../../omarchy-arm64/omarchy-root-link-report-2026-10-18.md)), on boot041's package, so
agents can run inside Omarchy on the M5.

The handoff records (`package-manifest.json`, `archive-sha256.txt`,
`intake-manifest-sha256.txt`) are boot041's, the `native-j716c-boot041` prerelease; the image pin
is `omarchy-root-manifest.json`. The image is never committed or published. Prior manifests remain.
[Claude handoff](claude-workflow.md) explains roles and targeted REA workflow.

This is a RAM boot, with no intentional target filesystem writes; m1n1 and Linux still perform
hardware initialization and RAM/register accesses. The original macOS remains protected.
Existing entry provisioning is historical in
[boot-entry-setup.md](../../kernel/native-enablement/boot-entry-setup.md); do not repeat it.

# J716c native handoff — attempt 24 / boot041: both DART instances per USB controller

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
Verify the `native-j716c-boot041` package and its delta against attempt 23's boot040, re-check the
read-only bulk-log reader, publish readiness, then one human-started boot with the default
`stage-b` profile: M1 freshly restarted, cable re-seated (a second Boot Lab boot if the M5 stays
invisible), recording started before the launch, the reader started right after the handoff, and
Macintosh HD return. **Native attempt 24/live checks NOT RUN.** Preserve installed
boot021/current entry; no repeated setup, security, volume or network-settings changes.

[Attempt 23](stage-b-2026-10-18-attempt23-result.md) found the USB link's stall on the DART
instance the Stage-B device tree left out. boot041 ([report](boot041-two-darts-2026-10-18.md))
gives each USB controller both instances, as Asahi's device trees do, and keeps boot040's kernel
Image and diagnostics. [Attempt 22](stage-b-2026-10-18-attempt22-result.md) ran the
installer-built Omarchy desktop; the Omarchy root with the SSH link is prepared for the attempt
after this one.

The handoff records (`package-manifest.json`, `archive-sha256.txt`,
`intake-manifest-sha256.txt`) are boot041's, the `native-j716c-boot041` prerelease. Prior
manifests remain (`boot035-`, `boot039-` and `boot040-package-manifest.json`).
[Claude handoff](claude-workflow.md) explains roles and targeted REA workflow.

This is a RAM boot, with no intentional target filesystem writes; m1n1 and Linux still perform
hardware initialization and RAM/register accesses. The original macOS remains protected.
Existing entry provisioning is historical in
[boot-entry-setup.md](../../kernel/native-enablement/boot-entry-setup.md); do not repeat it.

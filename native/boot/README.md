# J716c native handoff — attempt 22: Omarchy itself (VM job 045) as a RAM root on boot035

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
Re-verify the boot035 package (attempt 16's) and the privately delivered 2.34 GB image, review
the launcher diff (the new `omarchy` profile), publish readiness, then one human-started boot
with `--profile omarchy`, filmed from before the launch to ten minutes after the handoff, and
Macintosh HD return. **Native attempt 22/live checks NOT RUN.** Preserve installed
boot021/current entry; no repeated setup, security, volume or network-settings changes.

[Attempt 16](stage-b-2026-10-15-attempt16-result.md) made boot035 the first stable native
baseline. [Attempt 19](stage-b-2026-10-16-attempt19-result.md) and
[attempt 20](stage-b-2026-10-16-attempt20-result.md) ran an Omarchy-style RAM root on it
(hand-picked packages, our own session) for ten stable minutes. Attempts 17, 18 and
[21](stage-b-2026-10-18-attempt21-result.md) worked on the USB link; attempt 21 proved the
bulk-only port against macOS and then met a DMA fault, which boot040 investigates. Attempt 22
boots boot035 unchanged with the root that **Omarchy's own installer** built (VM job 045, pinned
in `omarchy-root-manifest.json`): Omarchy's session, first run and menu, on simpledrm with
software rendering on one CPU, view-only and offline. The image is 2.34 GB, so the launcher
gained an `omarchy` profile with a larger proxy-client heap and a 900 s deadline
([profile notes](ramroot-profile-2026-10-15.md)).

The handoff records (`package-manifest.json`, `archive-sha256.txt`,
`intake-manifest-sha256.txt`) are boot035's, the `native-j716c-boot035` prerelease. The image is
never committed or published: it holds the build's machine-id and reaches the M1 privately.
Prior manifests remain. [Claude handoff](claude-workflow.md) explains roles and targeted REA
workflow.

This is a RAM boot, with no intentional target filesystem writes; m1n1 and Linux still perform
hardware initialization and RAM/register accesses. The original macOS remains protected.
Existing entry provisioning is historical in
[boot-entry-setup.md](../../kernel/native-enablement/boot-entry-setup.md); do not repeat it.

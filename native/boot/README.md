# J716c native handoff — attempt 23 / boot040: the bulk-only USB log port with the DART fault made visible

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
Verify the `native-j716c-boot040` package, re-check the read-only bulk-log reader, publish
readiness, then one human-started boot with the default `stage-b` profile: M1 freshly restarted,
cable re-seated (a second Boot Lab boot if the M5 stays invisible), recording started before the
launch, the reader started right after the handoff, and Macintosh HD return. **Native attempt
23/live checks NOT RUN.** Preserve installed boot021/current entry; no repeated setup, security,
volume or network-settings changes.

[Attempt 22](stage-b-2026-10-18-attempt22-result.md) ran the installer-built Omarchy desktop on
boot035 for ten stable minutes, view-only. [Attempt 21](stage-b-2026-10-18-attempt21-result.md)
proved the bulk-only USB port against macOS, then stalled on a DMA bus error that Linux's DART
driver did not report. boot040 ([report](boot040-dart-fault-2026-10-18.md)) keeps that link
unchanged and makes the fault visible: DART fault reporting and, on a DART of version 2.2 or
later, acknowledgement in that version's fault layout, plus the failing DMA address and short
per-port lines on screen.

The handoff records (`package-manifest.json`, `archive-sha256.txt`,
`intake-manifest-sha256.txt`) are boot040's, the `native-j716c-boot040` prerelease. Prior
manifests remain (`boot035-package-manifest.json`, `boot039-package-manifest.json`).
[Claude handoff](claude-workflow.md) explains roles and targeted REA workflow.

This is a RAM boot, with no intentional target filesystem writes; m1n1 and Linux still perform
hardware initialization and RAM/register accesses. The original macOS remains protected.
Existing entry provisioning is historical in
[boot-entry-setup.md](../../kernel/native-enablement/boot-entry-setup.md); do not repeat it.

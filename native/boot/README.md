# J716c native handoff — attempt 26: the M5's keyboard, switched on over SSH, on boot042

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
Re-verify the boot042 package and its delta against boot041, verify the privately delivered Omarchy image
(attempt 25's root with its four fixes and the keyboard modules), publish readiness, then one human-started boot
with `--profile omarchy`, filmed, with the reader on the journal, the SSH session, the clock step, and the keyboard
switched on one module at a time with `sudo ilinux-keyboard` while the human types on the M5, and Macintosh HD
return. **Native attempt 26/live checks NOT RUN.** Preserve installed boot021/current entry; no repeated setup,
security, volume or network-settings changes.

[Attempt 25](stage-b-2026-10-19-attempt25-result.md) proved data from the M1 to the M5: SSH, the clock step, web
access through the M1 and a signed-in Claude Code. The machine still has no input of its own. boot042
([report](boot042-keyboard-modules-2026-10-19.md)) is boot041 with the MTP keyboard path and the storage drivers built
as modules, and the MTP nodes and its DART in the Stage-B device tree; nothing else changed. The one new hardware
change at boot is the DART driver's reset of the MTP's DART; the keyboard modules load afterwards from the SSH session.
No storage in this attempt: the launcher refuses an enabled NVMe node, and read-only storage is attempt 27, behind a
separate launcher change the user reviews.

The handoff records (`package-manifest.json`, `archive-sha256.txt`,
`intake-manifest-sha256.txt`) are boot042's, the `native-j716c-boot042` prerelease; the image pin
is `omarchy-root-manifest.json`. The image is never committed or published. Prior manifests remain
(`boot041-package-manifest.json` is boot042's baseline).
[Claude handoff](claude-workflow.md) explains roles and targeted REA workflow.

This is a RAM boot, with no intentional target filesystem writes; m1n1 and Linux still perform
hardware initialization and RAM/register accesses. The original macOS remains protected.
Existing entry provisioning is historical in
[boot-entry-setup.md](../../kernel/native-enablement/boot-entry-setup.md); do not repeat it.

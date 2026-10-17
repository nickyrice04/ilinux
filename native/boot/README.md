# J716c native handoff — attempt 21: boot039, a bulk-only USB log port with the dwc3 state on screen

**M1: follow [the current Stage B checklist](../../tools/m1n1-client/stage-b-instructions.md).**
Verify the `native-j716c-boot039` package. Build and offline-test the read-only
bulk-log reader ([brief](../../tools/m1n1-client/bulk-log-reader-brief.md)) with only
what macOS provides, installing nothing. Publish readiness. Then make one
human-started boot with the default `stage-b` profile: M1 freshly restarted, cable
re-seated, recording started before the launch, the reader started after the
handoff, filmed for ten minutes. Return to Macintosh HD. **Native attempt 21/live
checks NOT RUN.** Preserve installed boot021/current entry; no repeated setup,
security, volume or network-settings changes.

[Attempt 16](stage-b-2026-10-15-attempt16-result.md) made boot035 the first
stable native baseline. Attempts [17](stage-b-2026-10-16-attempt17-result.md)
and [18](stage-b-2026-10-16-attempt18-result.md) brought up the USB controllers.
In attempt 18, macOS configured boot038's ACM + ECM device, and then its control
endpoint timed out. Attempts [19](stage-b-2026-10-16-attempt19-result.md) and
[20](stage-b-2026-10-16-attempt20-result.md) booted the Omarchy RAM root on boot035:
a stable desktop, view-only, with on-screen benchmarks. Attempt 21 returns to the
link with [boot039](boot039-bulk-log-2026-10-16.md):

* **One function per controller:** the kernel's generic serial function `gser` (vendor
  class, bulk IN + bulk OUT, **no interrupt endpoint**), which carries the M5's kernel
  log, written only by the M5.
* **The status line names any wedge without a USB link:** every heartbeat shows each
  dwc3 core's link, events, interrupts, EP0 commands and endpoint rings.
* **The rest is boot036's:** Image, config, DTs and m1n1 are byte-identical, and the
  initramfs differs in `/init` only.

The handoff records (`package-manifest.json`, `archive-sha256.txt`,
`intake-manifest-sha256.txt`) are boot039's, the `native-j716c-boot039`
prerelease (public, like the repository; GitHub's asset digest verified against the
archive). The RAM-root profile and its image pin (`ramroot-manifest.json`, attempt 20's
run 33) are unchanged; the RAM-root image is never committed or published. Prior
manifests remain. [Claude handoff](claude-workflow.md) explains roles and targeted REA
workflow.

This is a RAM boot, with no intentional target filesystem writes; m1n1 and
Linux still perform hardware initialization and RAM/register accesses. The
original macOS remains protected. Existing entry provisioning is historical
in [boot-entry-setup.md](../../kernel/native-enablement/boot-entry-setup.md);
do not repeat it.

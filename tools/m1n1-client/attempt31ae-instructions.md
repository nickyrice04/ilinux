# 31AE: review the DATA-first fix, then hold for a human decision

**M1 task now: offline review only. No restart, proxy, Recovery command, boot
replacement or settings change.** The 31AD authorization/test is consumed.
The source and package below are a new candidate for a separate concrete human
decision after review. Preserve Macintosh HD Full, lab Permissive and boot021.

## Review the actual fix

Pull main with `git pull --ff-only`, preserving local work. Read the actual
[31AD result](../../native/boot/attempt31ad-recovery-2026-10-25-result.md) and
[31AE findings](../../research/native31ae-data-order.md). The old image reproduces
the exact arithmetic error offline despite inspector exit 0; the new image
derives all 14 properties. Do not treat inspector exit 0 alone as a PASS.

Verify every entry in `native/boot/attempt31ae/source-sha256.txt`, the published
archive using `native/boot/attempt31ae/verify.py --archive <download>`, and the
standalone candidate using the Git manifest. No untrusted extracted program is
executed. Reuse unchanged 31AD frozen evidence where exact bindings match;
do not rerun the known incompatible host LLD script or unrelated suites.

New focused suites (from repository root, existing tools only; 72 methods below,
plus five exact-old-image regression methods when the retained control is available):

```sh
python3 -I kernel/experiments/bootimage31ae/test_ordered.py
python3 -I tools/recovery31ae/test_write_render.py
python3 -I tools/recovery31ae/test_prepare.py
python3 -I native/boot/attempt31ae/test_verify.py
```

Use the actual new linked payload from the M5's ignored build only if available;
otherwise reconstruct its reserved zero header page from the downloaded image,
verify its hash from the Git manifest, validate and round-trip the candidate with
the reviewed source packager. The independent verifier requires exact mapping,
DATA-before-normal-before-boot-before-metadata-before-linkedit, payload binding
and both headers. Its original arithmetic model is not Apple's full validator.
The exact old 31AD image is an optional hash-pinned negative control via the
regression command documented in `bootimage31ae/README.md`.

Separate M5 evidence: five host compile objects; isolated GNU two-base link;
26 complete QEMU cases; exact three predicted boot instruction-word changes;
old/new actual read-only Apple inspector comparison. State which evidence was
rerun, reused or only reviewed. No native Apple firmware or monitor is emulated.
Publish a sanitized review with exact commit, hashes, commands and findings.

## Prepare the one-paste pages without executing them

After verifying the Git pins:

```sh
python3 -I tools/recovery31ae/prepare.py --output build/31ae-reviewed-pages
```

This verifies its source closure, derives the real profile from the Git manifest,
and writes an HTML page plus independent install/rollback blocks. Review hashes
and `bash -n` each complete block. The original-only archive also carries the
rendered page and paste blocks as data. Compare their bytes with the regenerated
blocks. Serve the reviewed directory to the M5's Recovery browser by the same
private local-page method used successfully for 31AD; do not start a server or
request a restart merely because offline review passed.

## Concrete future physical sequence (not authorized by this document)

After M1 PASS and a fresh human approval of this exact image and full sequence:

1. Use the previously reviewed temporary lab Startup Disk/paired Recovery flow.
   The existing lab entry and security levels are retained. No M1 restart or USB
   proxy is needed for this entry diagnostic. The browser is in Recovery after
   Options → Continue → authentication, not in the initial disk picker.
2. In Recovery choose Web Browser → Continue. Copy the short harmless clipboard
   smoke test, quit the browser, open Utilities → Terminal and paste once:
   `printf '%s\n' ILINUX_CLIPBOARD_OK`. This worked in 31AD; verify this session.
3. Reopen the browser and copy **one complete Install block**. Quit the browser,
   open Terminal and paste once. No shared variables or manual transcription.
   The block checks the lab identity, paired Recovery, expected build, exact
   helper/rollback and Full/Permissive policies, then downloads and verifies the
   exact candidate pathname before one Mach-O configure invocation. No raw flag.
4. Read Apple's prompts. If asked for a volume administrator username, enter it
   first; enter the password only when asked. Keep credentials in Terminal.
   Capture the full error and configure/capture/block exits privately. **Any
   nonzero result stops candidate testing**; no changed-flag retry or boot.
5. Only on the install success marker, boot the lab once and observe the screen
   for 30 seconds. Record a bordered checkerboard marker or firmware message.
   This diagnostic parks; it does not load Linux or start another core.
6. Return to paired Recovery. Copy the independent **Rollback block** again.
   It has its own fresh guard and needs no download or previous variables. It
   restores exact boot021 with raw entry 2048 and lowest virtual address 0.
   Record numeric success and policy-postcheck exits; do not assume rollback.
7. Return to Macintosh HD and restore it as default. Report both confirmations.

The browser and Terminal need not coexist. Each complete phase is self-contained.
Do not use the historical Full/Full preflight or hand-edit guards. No volume,
security downgrade, firmware, DFU, recovery bypass or automatic reboot is part
of this plan. Original macOS remains intact and Full Security.

## Result boundaries

Installation, entry/marker, rollback, live version, Linux, SMP, GPU and performance
are separate outcomes. All are NOT RUN for 31AE at this handoff. A marker proves
entry/display-path visibility only; silence stays inconclusive. The specific
31AD format error is repaired offline, but no claim is made that all firmware
contracts or CPU startup are solved. After any native result, publish a sanitized
record and stop for analysis before another changed experiment.

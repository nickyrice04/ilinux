# 31AH M1 review and optional camera evidence

This supplements the current
[31AH instructions](../attempt31ah-instructions.md). The package manifest and
parent instructions own the actual build results, hashes and native-readiness
decision. This directory does not authorize a boot, installation, firmware
update, policy operation, proxy connection or camera access.

## Current M1 work: offline only

1. Pull the published handoff while preserving unrelated local changes. Verify
   the current source inventory and artifact digests named in the parent
   instructions. Do not reuse an old native-attempt approval.
2. Check that the package binds Aura, kernel, J716c DT, configuration, modules,
   padding method and any CDC difference separately. Identify reconstructed
   configuration versus the November 11 operator's unprovided exact inputs.
3. Review build evidence separately from generic VM evidence. Neither proves
   that this M5 has entered the loader, started all cores or enforced a CTXR
   window. The current host and lab were version-read as 26.6.2/25G83; the
   matching external J716c report used 27.2.1/26B131. Do not install that version
   or change firmware in response to this note.
4. Run this original host-safe test and inspect the helper:

   ```sh
   python3 -I tools/m1n1-client/direct31ah/test_timeline.py
   python3 -I tools/m1n1-client/direct31ah/timeline.py --help
   ```

   The tests use synthetic JSON and temporary files under ignored `build/`.
   They do not open cameras, microphones, USB, network connections or other
   apps. They do not query boot policy. Expected test count: 24 methods.
5. Return an offline verdict referencing the exact reviewed commit and
   inventory. Identify any actionable source/artifact issue. Retain current
   native, firmware, camera, policy and restoration evidence independently.
   Do not mark the camera checked or a native result observed from these tests.

Current camera availability and recording on M1: **NOT CHECKED / NOT RUN**.
Old 31AF rollback and Macintosh HD default restoration are still unconfirmed
unless a separate later report actually closes them. This review must not
silently overwrite those states or request another routine desktop policy loop.

## What the helper does

`timeline.py` has two commands:

* `record`: writes typed, fixed event labels with a monotonic timestamp, a UTC
  sample and the clock-sampling bracket. It never launches a controller or a
  recorder. Its output directory must be new, nonsymlink and strictly inside
  this checkout's ignored `build/` tree. Arbitrary input is refused without
  storing or echoing it. A session is limited to 256 records and 30 minutes;
  this is a file bound, not the native attempt's deadline.
* `align`: reads a closed private timeline and estimates its event positions in
  a separately recorded video, from one manually identified visual-sync media
  timestamp. The operator must supply both manual and video-time uncertainty.
  The result explicitly assumes a 1x clock rate with no drift correction and
  never claims native entry or CPU execution.

All marks are **operator observations**. A `proxy_reconnected` mark is when the
operator noticed reconnection; the actual USB controller log owns packet timing.
`cpu_workers_complete` does not validate the workers' result: the diagnostic
collector and its independent per-core evidence own that claim.

Video mapping uses the media's actual presentation timestamp, not frame index
divided by an assumed FPS. A 30 FPS camera can drop frames or use variable frame
timing. A QuickTime playback time read to 0.1 seconds requires at least that
resolution to be included in the uncertainty. Manual keypress/visual action
delay is separate and generally much larger than the clock-sampling bracket.

Compare the controller and timeline only when their timestamps are known to
use the same M1 monotonic clock in the same host boot. Never subtract the M5's
kernel-relative timestamps directly from M1 timestamps. USB buffering and
delivery latency remain unmeasured unless the controller has separate evidence.
UTC helps locate a session, but a clock correction does not alter the helper's
monotonic event differences.

## Optional next native capture, after separate authorization

The user's webcam idea is useful: a camera on M1 can watch the M5 panel while
M1 independently records USB/control events. The recording can show whether a
logo remains, a diagnostic marker appears, the panel blanks, or a reset occurs.
It cannot locate a silent instruction fault or prove that an unseen CPU ran.

The dormant setup and correlation procedure are in
[camera-protocol.md](camera-protocol.md). It is not a reason to restart M1 now.
Use an existing human-operated recorder. Camera and audio remain off during
this offline work; this helper controls neither. Do not install software or
change system permissions as part of the offline review.

Keep `timeline.jsonl`, camera media, raw USB/serial logs and alignment output
local in ignored `build/`. Do not upload or commit them. Publish only a reviewed,
non-identifying summary with the measured uncertainty and the appropriate
source label. A video capture or hash is not an approval to publish that media.

## Attribution and test scope

The helper and tests are original MIT-licensed project code. They use Python's
standard library only. Synthetic tests exercise overwrite/path protection,
incomplete or corrupted evidence, clock changes, exact decimal timestamps and
uncertainty propagation. The tests do not measure a real camera or establish
cross-device synchronization accuracy.

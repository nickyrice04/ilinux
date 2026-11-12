# Optional M1 camera protocol for a future approved 31AH session

**Dormant plan. No recording, proxy or native test is authorized by this file.**
The parent handoff determines whether a native package and firmware environment
are qualified. Camera availability on M1 is NOT CHECKED, recording is NOT RUN,
and audio is intended to remain off. Neither this document nor `timeline.py`
changes permissions, starts capture, or extends an attempt's stop deadline.

## Setup when that physical session is approved

Use a webcam connected to the helper M1, pointed at the M5 panel. A built-in M1
camera also works if the machines can be positioned without moving the M5's
known debug cable/port. Prefer a different M1 port from the tether if available;
camera load and shared-bus behavior have not been measured. No extra camera is
required to continue offline development, and a missing camera need not block a
separately qualified USB-log-only attempt.

Frame only the M5 panel and a small area for a physical sync card. Keep people,
personal desktops, serial labels, recovery passwords, Apple-account details and
other identifiers out of frame. Cover the lens or pause before any Recovery
authentication or original-macOS return. Do not record the whole room or the
M1's private controller terminal. Use local storage, without cloud recording.

QuickTime Player is the first option because it is already part of macOS.
Apple documents **File > New Movie Recording** and selecting a built-in or
external camera from the recording options. The operator selects the intended
camera and **Microphone: None**, if that option is available, before recording.
If this setup cannot make a video-only recording, use an already approved
video-only recorder or omit the optional video; do not enable audio silently.
No new recorder installation or global permission change is part of this plan.
[Apple's recording guide](https://support.apple.com/en-gb/guide/quicktime-player/qtp356b55534/mac)

1080p at 30 FPS is normally enough to read large checkpoints. Higher resolution
and frame rate increase helper/USB load without proving faster CPU startup.
Record actual settings and dropped-frame observations if available; never
assume fixed frame timing from the configured rate. Actual M1 recording
performance and file size are unmeasured. Keep the film as short as the
approved observation window permits and stop by that window's deadline.

## Start together, without automating the boot

The parent-approved controller remains in one M1 terminal and writes its own
private timestamped log. A second terminal can run the independent operator
timeline below. This command records text labels only and opens no camera:

```sh
python3 -I tools/m1n1-client/direct31ah/timeline.py record \
  --out build/direct31ah-capture/run01
```

The directory must be new. An existing directory is refused, so the helper
cannot overwrite or silently append to a previous attempt. A different label
for a recording file is not permission to repeat a consumed native attempt.

The human starts the video manually, then types `camera_recording_observed`
into the timeline terminal. Before handoff, briefly cover the M5 panel with a
plain card and type `visual_sync` at the visible transition. Use a distinctive
single cover/uncover sequence and note which edge is the anchor. Pressing Enter
and moving the card are not simultaneous; estimate a conservative manual
uncertainty rather than treating the keypress as the camera's exact timestamp.
This action does not press a key or change the display state on M5.

Continue the exact approved boot procedure. Optional operator marks include:

* `handoff_requested`
* `proxy_disconnected` and `proxy_reconnected`
* `linux_console_visible` or `linux_desktop_visible`
* `cpu_workers_complete`, only after the independent collector says so
* `stop_condition`

These labels describe what the operator noticed. The USB log, collector and
video supply their respective evidence. A visible marker can corroborate its
corresponding executed checkpoint only when the candidate's code establishes
that association; the Apple logo alone does not establish pre-entry failure.

If practical, make a second visual sync near the end using the same method.
Stop the movie manually and mark `camera_recording_stopped`. Type `stop` to
close the timeline. A second sync lets review compare the alignment estimates
and detect clock/video drift. Never keep Linux running beyond the controller's
deadline to finish a recording, and never let the timeline replace rollback or
the approved return to Macintosh HD.

## Offline correlation

Afterward identify the chosen sync transition's **actual media time** in the
video. Do not infer it from nominal FPS alone. Take the `visual_sync` sequence
number printed by the helper and provide the observation uncertainties. For
example only, if sequence 2 is the chosen mark and the transition is seen at
2.433 seconds with a conservative 0.5-second manual uncertainty and 0.1-second
playback-time uncertainty:

```sh
python3 -I tools/m1n1-client/direct31ah/timeline.py align \
  --timeline build/direct31ah-capture/run01/timeline.jsonl \
  --sync-sequence 2 --video-seconds 2.433 \
  --manual-uncertainty-seconds 0.5 \
  --video-time-uncertainty-seconds 0.1 \
  > build/direct31ah-capture/run01/alignment.json
```

Replace the example values with measured/reasoned values; do not report the
example as evidence. Values in `alignment.json` remain operator estimates. A
second invocation using the later sync should agree within the uncertainty
budget; otherwise report drift or unresolved synchronization rather than
silently selecting a more convenient anchor. The helper does no video parsing,
clock calibration, drift correction or automatic USB-log joining.

The helper deliberately refuses incomplete final lines, unclosed sessions,
out-of-order monotonic timestamps and invalid fields. Preserve a partial file
unchanged if M1 crashes; it remains potentially useful manual evidence but
cannot be promoted to a complete aligned session. Buffered video/timeline data
may be lost if M1 panics. A camera on M1 does not independently survive an M1
failure; a separately powered camera/phone is an optional additional source.

## Publish a small summary only

Keep full media and logs private under ignored `build/`. A useful public report
contains source/artifact pins, which observations came from USB versus the
camera versus the human, approximate visible transition times with uncertainty,
and native phases actually reached. Leave performance, all-core work, CTXR
enforcement and restoration conclusions to their separate measurements.

# Local webcam preview and bounded silent recorder

Original macOS camera UI, separate from every boot controller. Built using the
existing Swift toolchain, AppKit and AVFoundation; no dependencies or host install.
It records an external camera pointed at the M5, not the M1 desktop.
No native boot, USB/proxy, network, Recovery, policy or settings command exists here.

Current M5 planning handoff: [recording sequence, text design and brightness
uncertainty](m5-recording-handoff.md). The measured quality clip supports partial
text qualification; tiny console characters and boot-time brightness control
remain unqualified. No additional test is requested by that handoff.

## Build, then use when the human requests a camera session

From this checkout root:

```sh
python3 -I tools/m1n1-client/camera/build_recorder.py
```

Build only: does not launch an app, enumerate/open a camera or request permission.
Generated app is `build/camera-recorder/iLinux Camera.app`. To build and open its UI:

```sh
python3 -I tools/m1n1-client/camera/build_recorder.py --launch
```

For later sessions, open the already built app directly; rebuilding is unnecessary:

```sh
open -n "build/camera-recorder/iLinux Camera.app"
```

1. Choose the external camera. **Start preview** opens only that video device;
   macOS may ask the human for camera permission. No microphone permission is
   requested, no audio input is created and audio recording connections are disabled.
2. Square the lens to the M5 screen; include all four corners and the bottom
   status text. Move closer rather than using digital zoom, focus, and reduce
   glare. The preview preserves the whole frame with letterboxing, not cropping.
   Use harmless small text while both Macs remain in macOS. Optional calibration
   page: `framing-target.html`, opened on the M5 by the human.
   Preview inspection has 1.5×/2×/3× enlargement and drag-to-pan; it enlarges
   captured pixels and cannot recover missing detail. The recording stays full
   frame. Any zoom change clears approval; return to 1× and recheck all corners
   before recording. Physical camera distance/focus still determine text detail.
3. Tick **Frame checked NOW** only after checking the smallest center/bottom text
   and excluding private information. The app cannot detect camera movement or
   automatically certify sharpness/angle; recheck if it moves after approval.
4. First select **10 seconds — quality check**, then **Record**. Wait for the
   visible **RECORDING** status, not merely the starting message. The human or
   agent can inspect this same UI; no boot is triggered by recording.
5. Recording ends at its duration/file limit or **Stop**. Camera preview closes
   after finalization. Every subsequent clip requires a new preview and framing
   check, including after moving/reconnecting the camera or a failed capture.
6. Play `camera.mov` locally and inspect actual smallest text at center/corners/
   bottom. The default ten-second test is a camera-only check, not a native test.

The session uses the first supported preset from 1080p, 720p and 480p; no fixed
frame rate or readability is assumed. Recorded resolution/nominal frame rate,
actual duration and audio/video track counts go in the receipt. `audio_tracks=0`
and one video track are required for LOCAL_VIDEO_RECORDED. That label means
saved media passed these checks, not that text quality passed human inspection.
Actual dropped frames and synchronization uncertainty remain unmeasured.

The target page includes 6/8/12/16/24 CSS-pixel synthetic challenges and corner
markers. Browser zoom/display scaling affect physical glyph size; passing a
page sample is not proof that every native console font will be readable.
For a short local-network target session, serve only that fixed page:

```sh
python3 -I tools/m1n1-client/camera/serve_target.py --bind <M1-LAN-address>
```

It prints an ephemeral URL, serves no directories/media/other files, logs no
requests and expires in fifteen minutes (maximum thirty with `--seconds 1800`).
Open that URL on M5 at 100% browser zoom/full screen; no native boot is needed.
Stop the server with Control-C after calibration. The LAN address is local-use
information and must not enter public test reports.

Each clip gets a new private `build/camera-capture/session-*/` directory with
`camera.mov`, `events.jsonl` and `receipt.json`. Media is never overwritten,
uploaded or committed. Events contain fixed labels and clocks, not camera names,
serials, paths or target information. The generated app contains its local
workspace path only in its ignored build metadata, never in Git. Symlink output
paths are refused. Prior recordings and consumed native receipts remain intact.

## Bounds and failure behavior

Selectable camera limits are 10/60/180/300 seconds, never above five minutes. Both
AVCaptureFileOutput's duration/file limits (256 MiB) and a UI timer request stop.
This is not a hard real-time watchdog: actual hardware/driver failure can prevent
completion. A ten-second start watchdog requests stop if recording never starts;
no successful start or boot cue may be inferred then. Interrupted or unverifiable
media stays PARTIAL_OR_UNVERIFIED; preserve it. No automatic retry, device switch
or re-arming. Closing the app during a recording asks it to finish the movie;
if the capture backend hangs, preserve partial output and stop using that session.

These camera-only bounds do not change any native attempt's shorter deadline.
For a separately authorized native attempt, camera duration must cover the
approved observation window. Its clock begins when recording actually starts,
not at Linux handoff. Do not let camera finalization delay an independent human
M5 stop/return deadline. A camera on M1 does not independently survive M1 failure,
provide Linux control or replace the human Recovery path. Keep authentication
out of frame; stop/cover the camera before returning to Recovery or personal data.
Use the existing private operator timeline for explicit visual-sync alignment;
these camera event clocks alone do not prove frame-exact correspondence.

## Offline verification

The app can be compiled and the pure policy/boundary checks run without opening
a camera. Compile policy test output only under ignored build:

```sh
mkdir -p build/camera-recorder
swiftc -swift-version 5 -module-cache-path build/camera-recorder/module-cache \
  tools/m1n1-client/camera/CapturePolicy.swift \
  tools/m1n1-client/camera/test_policy.swift -o build/camera-recorder/test-policy
build/camera-recorder/test-policy
TMPDIR="$PWD/build/camera-recorder" python3 -I tools/m1n1-client/camera/test_launcher.py
```

Policy tests cover missing/stale approval, invalid durations, duplicate starts,
early stop/late callbacks and failure reset. Path tests cover symlink escape,
traversal and preserving old media. Compilation/tests do not establish actual
camera quality, permissions, audio track behavior, disconnect/finalization or
native readiness. The November 13 camera quality test is recorded separately in
the linked handoff and receipt; it does not establish native readiness.

Apple primary API references:
[preview gravity](https://developer.apple.com/documentation/avfoundation/avcapturevideopreviewlayer/videogravity),
[capture authorization](https://developer.apple.com/documentation/avfoundation/avcapturedevice/requestaccess(for:completionhandler:)),
[movie output](https://developer.apple.com/documentation/avfoundation/avcapturemoviefileoutput),
[file size limit](https://developer.apple.com/documentation/avfoundation/avcapturefileoutput/maxrecordedfilesize).

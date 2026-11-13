# M5 handoff: recording plan and diagnostic readability

2026-11-13. Human-requested documentation handoff only. No camera retest,
restart, native attempt, brightness change or boot-setting change in this update.
M5 may continue its next offline analysis and proposal; native31AI remains HOLD.

## Evidence available

**Observed:** the external-camera workflow recorded one silent quality clip:
1920x1080, nominal approximately 15 fps, actual 9.867 seconds for a requested
ten-second limit, one video track and zero audio tracks. No capture error or
interruption was reported by the receipt. Frames at 1, 5 and 8 seconds retained
all four synthetic-target corners and the bottom margin with stable framing.
The 24/16 CSS-pixel samples were readable, 12 largely readable; exact characters
in the 6/8 samples were not qualified. Left-side reflections remain. Browser
scaling and the native framebuffer differ, so these CSS sizes are comparative
samples, not a native font-size prescription or a complete console-readability
guarantee. Rapid scrolling and dropped frames were not qualified.

Measured receipt: [camera quality test](../../../native/boot/camera-quality-test-2026-11-13.json).
Recorder use and limits: [README](README.md). Media and extracted frames remain
private under ignored build directories; none are uploaded or committed.

## Guidance for M5-produced diagnostics

The human requests minimizing reliance on tiny text wherever the new original
diagnostic code permits. Moderate, readable text is sufficient; giant text is
not required. Apply these recommendations in a separately reviewed proposal:

- Give key milestones a concise, high-contrast, comfortably sized label with
  adequate spacing. Prefer a few stable status lines over dense register dumps
  or a rapidly scrolling wall of output as the sole evidence.
- Keep the essential result, phase and failure code visible in a consistent
  location with margins. Avoid requiring exact recovery of long addresses or
  tiny characters from the camera alone. Detailed logs can remain available
  through an already approved evidence channel, when one exists.
- Preserve critical status long enough to be recorded where this does not
  change the experiment, timing-sensitive code or approved stop deadline. Do
  not introduce delays, expensive output, or additional hardware operations
  merely to make the camera view easier without reviewing those changes.
- Some early firmware/third-party console text may be outside the diagnostic's
  control. Record this limitation explicitly. Unreadable or absent camera text
  is inconclusive; do not convert it into proof that a phase did not execute.

Do not rewrite frozen sources, binaries or consumed receipts to retrofit these
recommendations. New diagnostic changes belong in the next reviewed proposal.
The camera provides visual evidence, not Linux remote control or guaranteed
capture of every message.

## Brightness uncertainty to retain

**Human reported:** the recorded display looked fairly dim, while the brightness
setting was described as the second-highest setting. Slider position, luminance
and exposure were not measured. Do not relabel this as a measured low setting
or infer a numeric brightness value.

**Unknown:** whether that setting persists into the separate native boot, whether
the relevant boot stage supports brightness adjustment, and whether the same
readability/exposure will hold there. The M1 recorder does not control M5 display
brightness. No present brightness-control capability is claimed for the native
diagnostic. Keep this as an observation risk in the next plan; the human does
not request another brightness or camera test now. No brightness-control code,
display-register write or global setting change was made in this update.

## Recording sequence for a future separately approved attempt

1. Human places the camera and M5 in the checked positions. After any movement,
   M1 opens a fresh preview and checks focus, reflections, all four corners and
   bottom text. Preview inspection zoom adds no captured detail; return to 1x
   for framing approval. Keep personal information/authentication out of frame.
2. M1 obtains the fresh framing approval, selects a camera duration sufficient
   for the approved preparation and observation window, starts recording and
   verifies the actual **RECORDING** state. Only then does M1 give the human the
   recording-start cue; camera startup alone is not a boot cue.
3. Human starts only the separately approved native sequence. The independent
   human stop/return timer remains authoritative; recording duration and movie
   finalization never extend it. Do not modify the attempt to compensate for
   a camera problem or retry automatically.
4. Stop/cover the camera before Recovery credentials or personal desktop use.
   Preserve the private clip and event receipt, inspect saved frames, and report
   the actual visible milestones and uncertainties. Every new clip requires a
   new preview/framing check; the app does not detect camera movement.

Camera preparation is sufficiently concrete for M5's next offline planning,
with the fine-text and brightness limits above. It does not close the existing
native install/restoration, firmware-pairing, readback or authorization gates.
No native/live check was run or re-armed in this handoff.

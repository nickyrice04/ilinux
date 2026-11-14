# M1: 31AJ physical transaction authorized, November 14

The user explicitly authorized the lab-only 31AJ install, **one** timed RAM boot
and exact boot021 rollback, keeping Macintosh HD Full Security. M5 reviewed your
`a417183` PASS. Authorization: `native/boot/attempt31aj-authorized-2026-11-14.json`.
This supersedes only older authorization-pending statements. Frozen source pins,
page bytes and historical receipts are unchanged. No new review cycle is needed.

## Start the handoff now

Pull this commit into your existing isolated review checkout, preserving other
work. Reuse the exact page you prepared for the November 14 PASS. Start the
portable adapter's fixed-page server with that file, M1's explicit private LAN
address, an available port and `--seconds 1800`. Give the resulting `/31aj` URL
privately to the user, and confirm the server is actually running. Do not put
the address in Git. No rebuild, resend, stage repeat, M1 restart or USB/proxy.

The server lifetime is independent of the native deadline. If it expires while
waiting, restart only that read-only page service. Do not replay a spent install
or restore operation. Keep the exact install and independent restore boxes
available for both Recovery visits. Camera recording stays off/covered during
authentication and personal desktop use.

M5 prepares the authorized temporary **iLinux Boot Lab** Startup Disk selection.
No automatic restart: the human receives the shutdown/hold-power/Options cue
after the page is available. Selection must not become a premature native boot
of the old 31AF object. The first visit is the lab's paired power-button Recovery.
The native helper is the admission check; an unpaired/refused guard is not
permission to alter flags, reset policy or bypass checks.

## First Recovery visit: install once

1. Human follows the M5 restart cue into Recovery and authenticates locally.
   Open Recovery's browser and the private `/31aj` URL.
2. Click inside **install**, Command+A, Command+C; quit the browser, open
   Utilities → Terminal, paste the entire block once. No clipboard smoke test.
   Passwords stay in the system Terminal prompt; keep the camera off/covered.
3. The pinned helper must admit exact lab/original/Data target, lab-paired 1TR,
   Original Full and lab Permissive before creating its private baseline/key or
   enrolling. Do not copy raw policy, identifiers, comparison keys or metadata
   commitments into chat or Git.
4. Only successful enrollment **and** the exact candidate/CTRR/supported-policy
   postcondition permit the native observation. Success text is
   `CANDIDATE READBACK VERIFIED`. A nonzero exit or guard failure means no native
   boot or automatic retry. Record a sanitized outcome and use the independent
   restore path when its guard admits the observed state.

## One native observation, maximum 90 seconds

Human positions the camera. After any move, check fresh preview/framing at 1x;
no additional quality clip. Start the existing recorder and verify actual
**RECORDING** before giving the human boot cue. Use a duration sufficient for
preparation and observation, but start the independent **90-second native timer
at the boot cue**. The camera's own clock never extends this limit.

Boot the installed iLinux Boot Lab once. This is an autonomous RAM diagnostic,
not the Omarchy desktop. Capture Aura/Linux progress and the readable 31AJ
panel: online/worker CPU count out of18, CPU/RAM/timer results and liveness.
The panel's Txx is a loop tick, not the authoritative wall clock. Fine text,
brightness and silent/blank intervals remain observation limitations.

Stop at the first fault, completed diagnostic outcome or 90-second deadline,
whichever applies. No second native try. A frozen/blank/logo-only display does
not extend the deadline or prove an Apple-only blocker. Stop/cover recording
before returning to Recovery credentials.

## Second Recovery visit: independent restoration

Return through power-button Options to paired lab Recovery. Reopen the same
verified page and copy/paste **restore** once using the same browser/Terminal
switch procedure. The candidate is not required for this block.

The block validates the persisted private baseline/key and current policy. It
uses only the reviewed lab CTRR operation if needed, then exact raw boot021
enrollment (entry2048, lowestVA0). Require exact boot021, disabled lab CTRR and
preserved supported policy postconditions. Original remains Full. No `bputil -n`,
firmware, partition, new volume, unrelated setting or original-policy write.

A spent operation is never re-armed by deleting its marker/state. Failed or
ambiguous commands stop that invocation and require review of their fresh
readback. Do not claim restoration from a command exit or desktop return alone.

After verified restoration, select Macintosh HD as Startup Disk and return to
its desktop. Confirm both desktop and default restoration separately. Keep the
private clip, original event receipt and saved-frame evidence under ignored
build directories. Publish a sanitized report with actual milestones, timer,
install/restore results, core results and uncertainties. Unrun steps stay NOT RUN.

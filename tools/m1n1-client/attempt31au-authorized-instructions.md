# 31AU authorized handoff: one guarded diagnostic window

November 15, 2026. The owner explicitly answered **“Yes, proceed with 31AU”** to
the scoped temporary lab Startup Disk, one lab-only install, conditional maximum
90-second Linux RAM observation, boot021 rollback and Original-default return.
Macintosh HD stays at Full Security. No volume, firmware or additional policy
change is authorized except the existing lab-only CTRR preparation if raw
rollback requires it. This supersedes the pending-authorization state in the
reviewed handoff; all code, profiles, kits and consumed state remain unchanged.

## M5 is prepared and stopped before restart

M1 review `9faac49` is accepted with its stated missing-input limits. Owner-staged
four-file V2 delivery and all 190 source inputs match. M5 selected **iLinux Boot
Lab** in Startup Disk. A fresh read-only device/group comparison reports current
system ORIGINAL, default LAB, distinct groups and selector exit zero, without
returning identifiers or querying policy. No Restart button or restart command
was invoked. No controller, Preboot, install or new rollback operation has run.

The new attempt's independent boot021 restoration and Original default/desktop
return will be required afterward. The earlier successful restoration remains
the preparation baseline; it is not a new post-attempt result.

## M1: serve the reviewed page directly

Reuse the exact source-only V2 outputs from your review. Start the existing
`tools/recovery31au/package.py` server on **/31au** with the reviewed combined
page. Tell the owner your live private URL directly. No separate M5 URL check,
readiness approval round, repeated suite/build/staging, M1 restart, proxy,
large-file transfer or clipboard calibration is required. Refresh only serving
if it expires; never replay installation to refresh a page.

The combined page is 18,133 bytes, SHA-256
`2361cfc8be8e1664da1cfe24117f760e45756ed5430766f7cdf8293fb8acc3c4`.
It contains complete independent install and restore boxes. Keep the restore
box accessible through the whole session. The locally built M1 fixture helper
must never replace the staged production helper.

Once M1 is serving and the owner has the URL, the owner may perform the prepared
shutdown/paired-Recovery sequence. M5 does not need another server report first.

## Owner sequence and hard stops

Follow the detailed eight-step sequence in
`attempt31au-reviewed-handoff.md`, under this now-confirmed authorization:
its first step, the temporary Startup Disk selection, is already complete.
Continue with its shutdown/Recovery step; no repeat selection or authentication
for Startup Disk is requested.

1. Shut down M5; hold power until Startup Options; choose **Options → Continue**
   for the lab's paired Recovery. Installation comes before selecting the lab
   tile for a candidate boot.
2. Keep recording off for Recovery authentication and every Apple command.
   Open M1's **/31au** page; copy the whole **install** box; switch to Terminal
   and paste once. No simultaneous browser and Terminal windows are needed.
3. On refusal, preserve the finite diagnostics and run the complete independent
   **restore** box once, then return to Macintosh HD. Do not boot, edit/retry
   install, reset state or treat display validation as successful installation.
4. Only `INSTALL_COMPLETE`, `candidate_verified=true`, `cleanup_verified=true`
   and final shell helper exit zero permit one candidate boot. The existing
   exact-byte, enabled-CTRR and policy-preservation checks must all pass.
5. If permitted, time **one** RAM diagnostic observation for at most **90 seconds**.
   Stop on reset/deadline; prevent an automatic second candidate boot. Capture
   loader/Linux/core/liveness evidence only after authentication is finished.
6. Return to paired Recovery and run the complete independent restore box.
   Require `RESTORE_COMPLETE`, `rollback_verified=true`, `cleanup_verified=true`
   and final shell helper exit zero. Restore **Macintosh HD** as default Startup
   Disk and separately confirm its normal desktop return.

If restoration refuses, preserve its actual finite result, stop and return to
Macintosh HD without claiming boot021 was restored. No force/reset or extra
writer is authorized. Credentials, raw policies, identifiers, private URLs and
camera files stay out of Git; report only finite observations.

## Expected decision value

This is a diagnostic Recovery window, not a promised Linux or Omarchy boot.
The CTRR cause remains unqualified. Same-read object stages and selected-reference
changed/unchanged evidence should explain whether the previous failure was
selection, access, framing/decode/exactness or policy. A failed candidate contract
continues to prohibit native entry. The old candidate is unchanged; no new GPU,
desktop responsiveness or macOS-performance result is implied.

M1 reports actual install/diagnostic output, whether any native window occurred,
its duration/markers, actual restore output and the separate Macintosh HD
default/desktop confirmations. Preserve every old and new consumed receipt and
all private transaction state. Do not repeat the manual security-mode check just
to restate the previously known configuration.

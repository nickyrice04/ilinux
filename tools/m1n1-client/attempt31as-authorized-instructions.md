# M1: prepare the authorized 31AS install, test and boot021 rollback

November 15, 2026. M5 reviewed **850f96c**: the 31AS source and exact pages
pass, with no actionable source finding. The user has requested preparation
of the lab-only installation, one maximum 90-second native test and exact
boot021 rollback, keeping Macintosh HD at Full Security. The existing concrete
scope is retained; no repeated approval of that same scope is needed. Execution
still waits for the new live-page evidence to be accepted and M5's human cue.
This handoff does not claim that a server, installation or native test has run.

## Accept the review with its stated coverage limit

M1 executed **six package/page methods**. Its separate **13-method shell
bootstrap class did not run** because the production kit was absent. One
class-level skip record is not one missing method, and neither is it 19 local
passes. Preserve that distinction in later reports. M5's producer and
independent 19/19 runs, including the 13 executed shell controls, are retained
evidence. Their utility and controller fixtures are not Recovery or hardware
execution. The earlier real-controller and PTY evidence also remains separate.

No repair, build, test rerun, helper transfer or restaging is requested. All
167 frozen inputs, the original 162 inputs and inventory, helper, profile,
candidate, boot021 and transaction namespace remain unchanged. Do not modify
the old 31AR page to make it appear corrected. The new page is 31AS; native
31AR schema labels, `ilinux31ar.` scratch prefix, `31ar-kit` and
`ilinux31ar-state` are intentional.

The exact four-file kit was already owner-confirmed on M5 lab Data. Missing
production bytes on M1 do not block this page workflow: the source-only server
does not read or execute that helper, and the M5 paste verifies its staged
bytes before copying and again before dispatch. Keep M1 binary delivery marked
unverified. Do not substitute an M1 build or manufacture test artifacts.

M5 has now selected iLinux Boot Lab temporarily in the original System Settings,
without clicking Restart. A fresh read-only selected-device/group comparison
confirms current ORIGINAL, default LAB and distinct target groups. No policy
query, boot-object installation or security change occurred. Keep M5 running
until the new live page is confirmed and M5 supplies the shutdown cue.

## Check and serve the new page

Pull the commit containing this handoff and reuse the exact source-only outputs
from your accepted 31AS review. The standard path below is from the prior
instructions; if your review used another workspace build directory, use that
actual retained path. Do not overwrite or regenerate an already matching page.

```bash
python3 -I tools/recovery31as/package.py \
  --page build/31as-m1-source-page/recovery.html --check-only
```

Require `EXACT_PAGE_VERIFIED`, 167 sources, and the following unchanged pins:

| Item | Bytes | SHA-256 |
| --- | ---: | --- |
| Combined recovery page | 18124 | a3f22c83e2fab094fd389e3d8e09098a2f8f39d0f9a491684b659b824db68f78 |
| Install paste | 6600 | eefadf83393949e04d5cbb564c61eeb5896bcc349d973a818d58fdd9eef04ddc |
| Independent restore paste | 6186 | a7f74f3c0fc228604d794e41099f4a81cb4f52967399285fb84f60881638823d |

The source inventory is
`3bd089cc7b2a009d5bc503b7f973baac4d8c179192a31188bf4997bf24216350`.
The visible title must be **31AS Recovery profile verification**. Both complete
install and restore text boxes must be present. The old `/31ar` page does not
contain this repair.

Set `ILINUX31AS_M1_IPV4` locally to the M1's actual current private IPv4 address,
then start only the reviewed bounded service:

```bash
python3 -I tools/recovery31as/package.py \
  --page build/31as-m1-source-page/recovery.html \
  --bind "$ILINUX31AS_M1_IPV4" --port 8031 --seconds 1800
```

Use the same actual reviewed page path as the check. The service exposes the
fixed page at **`/31as`**; it offers no artifact download, upload, listing,
shell or guest control. Verify the actual HTTP response equals the reviewed
18,124-byte body, then return the complete printed private URL to the human and
publish a new finite readiness report. Omit the address, process/session
details and other private network metadata from Git. Do not label the earlier
offline review as live-page readiness.

Keep M5 running until M5 accepts that readiness evidence and supplies the
shutdown cue. M5 handles temporary lab Startup Disk selection under the retained
selection/Original-return approval. Do not restart M1, start a USB proxy or run
another camera-calibration session. An expired read-only server may be refreshed
without repeating a Recovery operation; keep the independent restore box
available through the second visit.

## First visit: paired lab Recovery and one install

On M5's cue, the human saves work and shuts down M5. From fully off, hold power
until startup options appear, then choose **Options → Continue** into paired
lab Recovery. If Recovery asks which installation to recover, choose the lab.
**Do not boot the old lab tile before verified installation.** Credentials stay
in the local system prompt or Terminal. Keep recording off or covered throughout
Recovery authentication and Apple command output.

Open the exact new `/31as` page. Click inside the complete **install** box,
press Command-A and Command-C, quit the browser, open Utilities → Terminal and
paste once. No clipboard exercise, edited pathname, changed flags or repeated
paste. The corrected shell checks tool availability and exact profile/artifact
pins, then the unchanged controller performs fresh model, distinct target,
paired-Recovery, Original Full and typed policy admission.

The authorized scope permits the owned, identity-verified shared-Preboot RO
observation and RW transition, fresh private durable state, one fixed lab-only
candidate writer, guarded readback and owned cleanup. It permits no Original
policy writer, raw-device write, firmware or OS update, new volume/partition,
forced mount, old-state reset or repeated writer.

Before any native boot, require both emitted success records:

- Controller `INSTALL_COMPLETE`, `candidate_verified=true`,
  `cleanup_verified=true` and writer exit zero.
- Final shell success with helper exit zero and cleanup verified.

A result-display pass alone is not installation success: the validator can
safely display a well-formed `REFUSED` result. A missing-tool preflight refusal,
missing record, nonzero writer, timeout, interruption or uncertain cleanup means
no boot or retry. Preserve scratch and private state and report the finite
outcome. If the block stops before enrollment or a writer, do not run restore
blindly: a usable baseline/key might not exist. Return to Macintosh HD/default
after a known clean pre-write refusal. After a writer attempt, independent
restore proceeds only when its existing state/target/policy guards admit it.

## One native RAM diagnostic, maximum 90 seconds

After installation, readback and cleanup all succeed, start the existing camera
recorder if used and confirm actual recording before the human native boot cue.
M1 independently starts a **90-second wall-clock maximum** at that cue. Camera
duration and the diagnostic's tick labels do not extend the deadline.

Observe one iLinux Boot Lab boot. Record Aura entry, Linux entry, distinct
concurrent pinned workers, CPU/RAM checksums, timer results and 60-second liveness
separately. A CPU list, online mask, Apple logo, partial text or unreadable frame
does not prove those other outcomes. This image is a RAM diagnostic, not the
Omarchy desktop or a macOS performance-parity result.

Stop at a fault, completed outcome or the external deadline. There is no second
native window or automatic retry. Stop or cover recording before returning to
Recovery authentication. No M1 restart or working guest USB is required.

## Second visit: independent boot021 rollback and Original return

Return through power-button Options to paired lab Recovery. Reopen the same
verified `/31as` page and use the complete **restore** box with the same
whole-box copy, browser quit and one Terminal paste. This path does not require
the candidate file. Preserve the new transaction's saved private key, profile,
baseline and stable target commitment exactly; do not migrate or reset state.

The controller conditionally prepares **only lab CTRR**, then performs one exact
raw boot021 installation with the fixed entry/lowest-address arguments. The
rollback remains 3,932,160 bytes, SHA-256
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Do not improvise policy resets, disk identifiers, raw commands or spent-marker
removal. Every attempted writer remains spent even after a failed command.

Require controller `RESTORE_COMPLETE`, `rollback_verified=true`, known cleanup
and final shell success with helper exit zero. A writer must return zero;
an exact already-restored no-op may report minus one. A command exit or return
to macOS alone does not establish boot021 restoration. Refusal or ambiguity
remains unconfirmed and is reported without retry.

After verified rollback, restore **Macintosh HD as Startup Disk** and return to
its desktop. Confirm desktop and default return separately. Macintosh HD stays
**Full Security** throughout. Do not repeat a routine desktop policy-mode query
or change its security settings. Boot021 remains OUTSTANDING until the actual
restore evidence proves otherwise.

Publish only finite sanitized actual results and keep every unrun phase marked
NOT RUN. Keep credentials, policy values, identifiers, comparison keys and
commitments, private URLs, personal paths, camera media and proprietary bytes
outside Git. Preserve prior evidence and all spent state. M5 decides the next
engineering step from the observed stopping stage; no automatic new attempt
follows this handoff.

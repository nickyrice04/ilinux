# 31AE authorized handoff: prepare M1's page, then restart M5

**2026-10-25 Eastern: M1 review PASS and the human explicitly authorizes this
exact experiment.** Read this before the frozen
[31AE instructions](attempt31ae-instructions.md). Approval-pending statements
in that package and review describe their publication time; preserve their bytes.
The separate [authorization receipt](../../native/boot/attempt31ae-authorization-2026-10-25.json)
records the later decision. No second approval loop is needed for this sequence.

The human requested: check M1's 31AE review and, if it passed, proceed with the
lab-only install, one boot test and boot021 rollback; keep Macintosh HD Full
Security and tell them when to restart. Review `e52528f` passes with no actionable
blocker. M5 independently reverified the archive, candidate, all 38 source pins,
and the existing staged boot021 and Recovery helper: all PASS, unchanged.

## Current checkpoint and M1 task

M5 System Settings → Startup Disk visibly shows **iLinux Boot Lab selected** and
Restart available. The agent opened the page but did not select a different
entry, enter credentials or click Restart. This UI selection does not prove
completion of the temporary default-change flow. No native 31AE installation,
boot observation or rollback has run. Current desktop policy was not redundantly
queried; fresh original Full/lab Permissive and lab-paired checks remain required
inside each reviewed Recovery phase immediately before its write.

M1 now prepares the human-operated session, without repeating the completed
offline review or restarting M1:

1. Pull main and read this handoff and authorization. Reuse M1's exact reviewed
   `build/native-intake/attempt31ae-m1-offline/reviewed-pages/` and its existing
   downloaded package. If the pages are unavailable, regenerate into a fresh
   ignored directory using `tools/recovery31ae/prepare.py`. They must match the
   reviewed install and rollback hashes below. No production block runs on M1.
2. Serve **only the reviewed page directory** using the same bounded private
   local-page workflow that worked in 31AD. Do not serve the repository, personal
   data, research or private logs. Keep local addresses out of public reports.
   Confirm the page and both complete blocks are available. No firewall or
   network-security change is authorized. Stop the server after the session.
3. Tell the human the page is ready. Only then should M5 complete the visible
   **Restart…** flow for **iLinux Boot Lab**. Keep AC connected and save M5 work.
   M1 stays in ordinary macOS; no USB proxy, controller or launcher is needed.

## One physical sequence

1. Complete Apple's temporary lab Startup Disk flow, authenticating locally if
   asked and checking the lab name. If applying the selection starts existing
   boot021 first, allow that screen, then hold power to shut down. Do not run a
   proxy session. This preparatory boot021 start is separate from the single
   authorized 31AE diagnostic boot.
2. From shutdown, hold power to Startup Options, then **Options → Continue** and
   authenticate. Keep the lab temporarily selected through **both** Recovery
   entries so the fresh guards can verify lab-paired 1TR. No new security change.
3. Use Recovery's Web Browser, not the initial Startup Options disk picker.
   Copy the harmless clipboard smoke test, quit the browser, open
   **Utilities → Terminal**, and paste once. Then copy the **complete Install
   block**, quit the browser, open Terminal and paste once. The browser and
   Terminal do not need to remain open together. Never hand-type a long block.
4. The unchanged reviewed block requires the fresh lab identity/pairing/policy,
   helper and rollback guard; it downloads and hashes the same resolved candidate
   pathname immediately before **one Mach-O configure invocation, without raw
   flags**. Read Apple's prompts: if asked for a volume administrator username,
   enter it before entering the password when requested. Keep credentials local.
5. Record configure, capture and block exits and the full actual error privately.
   A nonzero candidate result **stops testing**: no retry, altered flag, raw
   candidate fallback or diagnostic boot. Do not assume the lab slot is unchanged.
   Proceed only to the independent exact rollback while its fresh guard passes.
6. Only on install success plus policy postcheck, shut down, select the lab once
   and observe for **30 seconds**. Look for the **32×16 bordered checkerboard at
   top-left**, or record the actual firmware message/absence of a marker. The
   diagnostic parks; power off after the observation. No Linux, monitor call or
   physical secondary-core release occurs in this image.
7. Enter lab-paired Recovery again. Copy the **complete independent Rollback
   block** afresh. It needs no downloaded image, previous variables or inherited
   PASS. Its own guard must pass. It restores the exact staged boot021 with raw
   entry **2048**, lowest virtual address **0**. Capture numeric configure,
   capture, policy postcheck and block exits, and the success marker.
8. Return to **Macintosh HD** and restore it as the default Startup Disk using
   Apple's normal flow, including its ordinary restart if required. Confirm both
   the original desktop return and default restoration separately.

If a fresh guard fails, stop and report. Never guess another volume, weaken
security, erase, repartition, use DFU or change Macintosh HD's Full Security.
The two independent phase blocks and exact boot021 restore are the approved path.

## Exact reviewed pins

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| 31AE candidate | 196608 | `ccdc9c8c8ef78fda2d9e2a56550919d0c20030037486215d194e8762a85748aa` |
| Archive | 256353 | `6b0c0ae6fdce31b69c72861c27297f0cb4d8873c586448fced41ed4e02910fa1` |
| Exact staged boot021 | 3932160 | `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664` |
| Complete install paste | 6135 | `0bc65c87184e9071a4d031b4817bbd671f99fda1d8b96171964fef062d6d5c8a` |
| Complete rollback paste | 5872 | `7b09569a39417c45f2dbb08787efaa0145744b059ccbfec4064efb8ee56f755e` |

The unchanged [manifest](../../native/boot/attempt31ae/manifest.json) supplies
the exact release URLs. Do not substitute 31AD or change the source closure.

## Record the result

M1 guides the human on M5; M1 does not remotely issue Recovery policy commands.
Publish a new sanitized result referencing the reviewed candidate, this
authorization and each actual transition: temporary lab default, pairing guard,
install exits, observation outcome/duration if permitted, fresh rollback guard,
restore exits/postcheck, original return and default restoration. Distinguish
human reports from independently captured values. Retain failed authentication
and errors as evidence rather than resetting receipts. Never upload credentials,
raw policy/disk identifiers, private logs or unredacted Recovery photographs.

A marker establishes entry/display-path visibility only; silence is inconclusive.
Native acceptance, live version, monitor readiness, Linux, SMP, GPU and
performance remain separate claims. No second experiment follows automatically.

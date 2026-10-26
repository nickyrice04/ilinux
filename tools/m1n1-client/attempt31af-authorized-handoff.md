# 31AF authorized handoff: prepare M1's page, then restart M5

**2026-10-25 Eastern: M1 review PASS; the human authorizes this exact sequence.**
Read this before the frozen [31AF instructions](attempt31af-instructions.md).
The earlier approval-pending fields describe publication time and remain frozen.
The separate [authorization receipt](../../native/boot/attempt31af-authorization-2026-10-25.json)
records the current decision. Do not ask for another approval of the same phases.

M1 review `5352c07` is OFFLINE_REVIEW_PASS with no actionable blocker. Its
supplemental `layout.h` pin closes the noted primary-inventory omission for this
exact candidate; do not rebuild, modify the inventory or substitute an image.
M5 independently reverified all 34 primary pins, the supplemental header, archive,
candidate, staged helper and exact boot021: PASS. Both existing reviewed paste
blocks match the archive and pass bash-n. No production block has run on M5.

## M1: prepare the already reviewed session

1. Pull main and read this handoff and authorization. Reuse your exact reviewed
   `build/native-intake/attempt31af-m1-offline/reviewed-pages/` and downloaded
   artifacts. If unavailable, regenerate into a fresh ignored directory with
   `tools/recovery31af/prepare.py` and compare the three page/phase hashes below.
   Do not repeat the completed 47-method review, inspector matrix or VM work.
2. Serve **only that reviewed page directory** through the private local-page
   workflow used in 31AE. Do not serve the repository, private logs, personal data
   or research artifacts. No firewall or network-security changes. Keep the
   local address out of public reports and stop the server after the session.
3. Confirm to the human that the page and its two complete phases are available.
   **M5 restarts only after this confirmation. M1 stays in macOS:** no M1 restart,
   USB proxy, controller, launcher or remote Recovery commands.

M5's Startup Disk state is **not verified in this handoff**: computer-use returned
no usable System Settings window. No entry was selected or authenticated and no
Restart was clicked. The human can open **System Settings → General → Startup
Disk**, select **iLinux Boot Lab**, and use Apple's normal temporary selection
flow, authenticating locally when asked. Save work and keep AC connected first.
Do not change either security level. M1 should guide the established paired
Recovery flow rather than infer the current default from this document.

## One physical sequence

1. After M1 confirms page readiness, complete the temporary **iLinux Boot Lab**
   Startup Disk Restart flow. If existing boot021 starts as part of that flow,
   allow that screen, then power off; no proxy session. That preparatory start
   is separate from the single authorized 31AF test.
2. From shutdown, hold power for Startup Options, then **Options → Continue**
   and authenticate. Keep the lab temporarily selected through **both** Recovery
   entries so the fresh guard can establish lab-paired 1TR.
3. Open M1's reviewed page in Recovery's Web Browser. Copy the **complete Install
   block**, quit the browser, open **Utilities → Terminal**, and paste once.
   **Skip the clipboard smoke test.** Do not hand-type or alter commands.
4. The block freshly checks lab identity/pairing/build, exact helper and staged
   rollback, and **original Full / lab Permissive**. It hashes the same candidate
   pathname immediately before one Mach-O configure invocation, without raw
   candidate flags. Read Apple's prompts: supply the administrator username if
   requested, then the password when requested. Credentials stay in Terminal.
5. Record configure, capture and block exits, the policy-postcheck/success marker,
   and any actual error privately. Any nonzero result ends candidate testing:
   no retry, altered flags, raw fallback or diagnostic boot. Use only the fresh
   independent boot021 rollback if its guards pass; do not assume a failed
   configure left the lab object unchanged.
6. **Only after install and policy-postcheck success**, boot the lab once. Start
   a **30-second timer** for that test. Look at the **center of the display for a
   128×64 black/white bordered checkerboard**; record any firmware message too.
   **At 30 seconds power off, including if only the Apple logo remains.** Record
   actual timing and marker visibility, with a photo/video privately if feasible.
   This observer parks; it does not start Linux or secondary cores.
7. Enter lab-paired Recovery again. Open the reviewed page and copy the **complete
   independent Rollback block**, quit the browser, open Terminal and paste once.
   It needs no previous download, variables or inherited PASS. Its own fresh
   guard precedes exact staged **boot021**, raw entry **2048**, lowest VA **0**.
   Record configure/capture/block exits and policy-postcheck/success marker.
8. Return to **Macintosh HD** and restore it as default Startup Disk through
   Apple's normal flow, including its ordinary restart if required. Confirm the
   original desktop return and default restoration separately; stop M1's server.

If a fresh guard fails, stop and report; do not guess a target or weaken security.
No new volume, security downgrade, DFU, erase, firmware update or automatic retry.
No repeated normal-desktop policy query is needed; the immediate pre-write
Recovery guards remain mandatory. This approval authorizes one experiment only.

## Exact reviewed pins

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| 31AF candidate | 442368 | `166bea74bf515473057dfd29dc89127d04768945a451e497cc80a9fc53d4951b` |
| Archive | 254936 | `52412ecf4a52cabd3cab23969ba3941572d691bd16efa7e6ff657c3746738eda` |
| Exact staged boot021 | 3932160 | `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664` |
| Complete install paste | 6137 | `5dc9aa45f5469604155b750597772c414ca87b10157d18acc7d001df3f225b68` |
| Complete rollback paste | 5872 | `7e363bf5cd4db770fb58635de213d7d79bfd06c7d94384a3685345454cfbe195` |
| Recovery HTML | 16562 | `f6c8b2d4bf5f0df8af06d46a64d7c5cfe25a780ce4e5c5486eccc678dc612f23` |

The frozen [manifest](../../native/boot/attempt31af/manifest.json) gives exact
release URLs. The header supplemental SHA is
`3da9aba03614899241641fd80cf2c52067491de9c011f4aead66903babb2404b`;
the matching six-file build-binding digest is
`874ac4cdd21ac70ea8a90a094c4b3f4474398b5e02ca4fabbcaed4a058ce1de4`.

## Publish the actual result

M1 guides the human; M1 does not remotely run Recovery write commands. Publish a
new sanitized 31AF result referencing this authorization and reviewed pins. Record
each actual transition, prompts/errors/exits, observation duration and marker,
rollback and original/default return. Distinguish photographed/observed values
from human reports and retain failed attempts as evidence. Do not publish raw
policy identifiers, credentials, local addresses or unredacted Recovery images.

A marker supports entry through validated framebuffer stores. Silence remains
inconclusive. Neither outcome alone proves monitor readiness, Linux, physical
SMP, GPU support, performance parity or an Apple-only dependency. No subsequent
experiment is authorized automatically.

# 31AD — installer arithmetic rejection; rollback and original return reported

**Observed/reported, 2026-10-25 Eastern:** one reviewed 31AD candidate configure
invocation failed after human confirmation: **configure 71 / capture 0 / block
71**. No candidate retry or diagnostic boot followed. The first exact boot021
rollback invocation also failed, at administrator authentication. The human
subsequently identified the need to enter the username first, reported successful
rollback and safe return to Macintosh HD, and separately confirmed Macintosh HD
as the default Startup Disk.

**Result: INSTALL_REJECTED_ROLLBACK_REPORTED_RETURNED.** The 31AD diagnostic boot,
30-second marker observation, live target-version checks, monitor calls, Linux,
physical secondary startup, GPU and performance remain **NOT RUN**. The human
assigns further analysis and the fix to the M5 agent. No new image, flags or test
is proposed or launched by this handoff.

## Inputs and scope

Released candidate handoff: `150dc67f30b017369b6099d56ca9751ef4c19ca2`.
M1 readiness/execution handoff: `9a4ec0342cbf358b923bfe9c3d7361564dbbb6d5`.
The human requested the test after that review and reported the M5 shut down.
M1 guided temporary lab Startup Disk selection, paired Recovery, clipboard smoke
test, read-only diagnosis, one guarded installation and exact rollback.
All M5 commands were human-operated on M5; M1 served only reviewed local pages.

| Input | Bytes | SHA-256 |
|---|---:|---|
| Release archive | 251825 | `3f3eb70ea933d6e2aa3becb2aa08f721f5a8bbc48666bd496f0b18a7ebfcf61e` |
| Candidate | 196608 | `406be900521795608073fa9f050f4e5f00b595793c95b0a155e510893cc16309` |
| Linked payload | 147456 | `6da621da67de37437300e7205e8c3919dcac997600f7eb6e8fedae29e6b0fc88` |
| Immutable boot021 rollback | 3932160 | `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664` |

The earlier [release review](attempt31ad-release-m1-offline-2026-10-25.md)
contains the full offline intake and review qualifications. Its 67 unchanged
methods plus 3 new delivery methods and five compile objects were not rerun here.
Frozen package, profiles and historical review receipts were not edited.

## Clipboard and read-only diagnosis

The human copied the harmless smoke command in Recovery's browser, quit it,
opened Terminal and pasted successfully: **ILINUX_CLIPBOARD_OK**. Clipboard
retention worked in this particular session; this is not a general macOS promise.
Each subsequent phase was copied as a complete independent block, avoiding manual
transcription and inherited state.

Human-reported inspector exits: **flat31ac 0, nested31ad 0, rawboot021 71**;
diagnosis-block exit **0**. Both Mach-O files parsed, while the raw negative
control did not. This does not establish installer acceptance: configure rejected
the ordered candidate afterward. The diagnosis block captured private raw
stdout/stderr and input/tool metadata in Recovery temporary storage, but these
files were not transferred to M1. The actual Recovery tool hash/version is not
available in this public result.

## Actual candidate rejection

The human's photo shows the reviewed guarded command with no raw flag. After
answering the Apple confirmation, it reported:

> Fileset Error: Invalid Mach-O boot properties. Arithmetic Error: arithmetic overflow detected subtracting FilesetOffset(rawValue: 49152) from FilesetOffset(rawValue: 32768)

The screen then shows **configure exit 71**, **capture exit 0**, the stop message
and **31AD install block exit 71**. No success marker. Reaching configure in the
issued block requires the fresh lab identity/pairing/policy/helper/rollback guard
and exact same-path candidate size/hash checks to pass; M1 did not separately
receive those private guard files. Failure was not assumed atomic.

M1 made one read-only check of its retained hash-verified candidate. In both
headers, **32768 is `__TEXT_EXEC.fileoff`** and **49152 is
`__DATA_SPTM.fileoff`**; the mathematical difference is **-16384**. This is an
observed correspondence to the error operands, not proof of which internal
installer check selected them or of a correct replacement layout. No changed
layout/flags, further Apple analysis or additional install test followed.
The prior normal-text-before-boot-text invariant alone did not predict this
installer acceptance result.

## Rollback authentication and final return

The independent rollback block was copied from the same unchanged reviewed page.
The next photo shows raw boot object recognition/wrapping, followed by a sanitized
boot-policy error: **not a valid admin user for the volume**. Its exits are also
**configure 71 / capture 0 / rollback block 71**, with no success marker.
This was an authentication failure, not a repeated candidate-format test.

The human explained that after a long pause they pressed Enter and tried the
password, then later reported: username entry first resolved it, rollback was
successful and Macintosh HD was reached safely. **Final rollback success is
human-reported.** Its numeric exits, exact subsequent command/invocation count,
and final Full/Permissive postcheck were not separately captured. Expected policy
levels remain original Full/lab Permissive; no new downgrade or volume change was
guided. No new live boot021 execution/version verification is claimed.

M1 had tentatively considered hidden/buffered credential prompts, then began a
foreground-prompt repair draft. The human resolved the authentication issue
before that draft was tested, rendered, served or supplied for execution.
Those drafts were removed from the working source tree and retained only as
ignored, unused scratch material. **No pipe/TTY defect was established or fixed**
in the reviewed renderer. Do not turn that tentative explanation into a finding.

The human separately confirmed **Macintosh HD is the default Startup Disk**
after the return. M1 stopped the page server. Original installation/raw evidence
remained local to the human's Recovery session; retention after reboot is
unverified. No raw policy, identifiers, credentials or unredacted media enter Git.

## Handoff to M5

Investigate the captured installer subtraction offline and decide the next fix.
The candidate is consumed for this installation test; there is no unchanged
retry, changed-flag fallback, new security operation or automatic next boot.
Keep successful inspection, failed installation and unobserved native entry
separate. The cause of 31AC's earlier generic exit 71 remains unconfirmed; the
specific arithmetic error above is actual evidence from 31AD.

Before publication, M1 rechecked the 24 earlier frozen manifests plus current
37-pin 31AD closure, clean client `57a9339ffd1876e78297b17d34dece8cff8fa1ba`,
prior ignored evidence and consumed receipts. No test or production source change
is included. The [sanitized receipt](attempt31ad-recovery-2026-10-25-result.json)
records the available evidence and unknown final rollback details explicitly.

Publication incorporated upstream `c27d437`: only the stale section-1 delivery
status and its source pin were refreshed. That metadata update does not change
the candidate, renderers or this execution result; the refreshed 37 pins pass.

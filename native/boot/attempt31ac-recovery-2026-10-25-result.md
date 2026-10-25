# 31AC — candidate installation rejected; boot021 rollback and safe return reported

**Observed/reported, 2026-10-25 Eastern:** the human invoked the authorized
lab-only candidate installation once in M5 Recovery. After answering the Apple
confirmation, the human reported a **fileset error, configure exit 71**, and the
guarded failure message. The candidate was not retried or booted. A fresh
read-only base guard passed with exit 0. The human then reported the exact
boot021 reinstall success message, safely returned to Macintosh HD, and separately
confirmed Macintosh HD as the default Startup Disk.

**Result: INSTALL_FAILED_ROLLBACK_REPORTED_RETURNED.** The 31AC diagnostic boot,
30-second marker observation, live target-version checks, monitor calls,
physical secondary startup, Linux, GPU and performance remain **NOT RUN** for
this attempt. This is an installation rejection, not an observed payload crash
or a blank-screen native result. No unchanged second attempt is authorized.

## Reviewed inputs and evidence boundaries

Execution/authorization handoff: `6aa6acde78a68e1ba2a3e7099eb7264ebbd94abd`.
Implementation: `8c5b691210a1923d647412985c8bfa53a6c9feba`.
Independent M1 review: `f6fae6ce053722c796ff11e9bcc5575b12952037`.
The separate [authorization](attempt31ac-authorization-2026-10-25.json) and
[frozen instructions](../../tools/m1n1-client/attempt31ac-instructions.md)
governed the sequence. Earlier approval-pending reports retain their historical
meaning and bytes.

| Input | Bytes | SHA-256 |
|---|---:|---|
| Reviewed archive | 249011 | `7cc585d69ebd023e2683b9842320b96ba30c9056e5082fa61aa18b74a0f60fdd` |
| Candidate Mach-O | 180224 | `261d44447442f32ba6c41bbf0f69179e8c9eb4c33507b60762f0ea8c2e54ab72` |
| Exact boot021 rollback | 3932160 | `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664` |
| Frozen Recovery helper | 3590 | `e65636d03cfb7a7000f86810fdc8888e209b99bedaa1b36ca7a125de4bf72188` |

M5 actions and outcomes are human-operated and human-reported; selected earlier
read-only outputs were also visible in private photographs. M1 did not remotely
execute Recovery commands or independently inspect the resulting installed slot.
No raw error log or installation transcript was supplied. Exact error wording
beyond "fileset error" is unavailable; exit 71 is a human report of the stored
configure exit. No component-level cause is established.

## Actual sequence

1. The human initially reported Running proxy, then entered Recovery and chose
   iLinux Boot Lab when prompted. The preparatory Startup Disk Restart flow was
   not separately confirmed. Recovery selection alone was not accepted as proof
   of pairing: the actual read-only guard subsequently passed, reporting separate
   expected lab volumes/build, verified rollback, original Full/lab Permissive,
   lab-paired 1TR and exit 0.
2. The helper hash matched. M1 rechecked the candidate's size/hash and served
   only the verified extracted package directory on a temporary local server.
   One candidate GET completed with HTTP 200; M1 stopped the server after the
   transfer. The human confirmed the M5 file's size/hash and candidate guard PASS
   with exit 0. No image was written at the staged boot021 pathname.
3. Manual transcription errors occurred before installation: a `start`/`stat`
   typo, an incomplete checksum-function name, unmatched quotes while defining
   the candidate function, and an installation guard missing `31` in its name.
   The photographed missing-function guard took the no-write branch, so its
   `kmutil` body did not execute. These corrections are not candidate-install
   retries. Recovery did not allow this human to keep browser and Terminal open
   together; subsequent commands were typed manually.
4. In the corrected guarded installation, the human confirmed Apple's prompt,
   then reported fileset error and exit 71. No changed flags, raw fallback or
   second candidate invocation followed. Because failure was not assumed atomic,
   M1 requested a fresh base guard; human reported PASS and exit 0 before rollback.
5. M1 supplied the approved exact boot021 raw rollback, entry 2048 and lowest
   virtual address 0, targeting only the guarded lab. Human reported "reinstalled
   succeeded." This is the guarded success-branch report: in the supplied block
   it requires restore exit 0 and the Full/Permissive policy postcheck. The numeric
   restore exit and full postcheck were not separately transcribed or captured;
   do not describe them as independently measured M1 evidence.
6. Human confirmed safe return to Macintosh HD, then separately confirmed it as
   the default after the requested Startup Disk flow. No 31AC candidate selection
   or 30-second observation took place. No additional boot021 execution/version
   check was requested to prove rollback.

## Preservation, remaining blocker and next work

Before publication, M1 reverified all **31 frozen source pins**, a clean client
at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, and **539 prior ignored evidence
files** against the retained pre-review digest inventory, including consumed
receipts. The existing 31AC offline evidence was snapshotted for preservation.
No source, package, prior receipt or frozen authorization was edited. The earlier
11 Python methods and five compile-only objects remain the offline review result;
they were not rerun to diagnose this installation error. This handoff changes
documentation only.

**Unknown/blocker:** actual Recovery `kmutil` acceptance of the reviewed Mach-O
has failed. The root cause needs offline investigation of the packaged format
and the applicable installer contract. This result establishes neither a
firmware-entry failure nor an Apple-only CPU restriction. No automatic retry,
new security downgrade, volume operation, M1 restart, USB/proxy connection or
Linux/SMP experiment follows. Original Full/lab Permissive are retained as the
reported guard state and conditional rollback-success state, not a new M1 query.

The accompanying [sanitized receipt](attempt31ac-recovery-2026-10-25-result.json)
records missing evidence explicitly. Raw photographs, addresses and local service
logs are excluded from publication.

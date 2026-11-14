# M1: staged 31AL read-only Recovery check

November 14, 2026. M5 reviewed your `5bb5639` offline PASS. The user authorized
the lab Data copy and preparation of the read-only Recovery diagnostic. The
user's staging JSON matches both reviewed files exactly. No source, helper,
profile, page, old receipt or consumed state changed. No suite or build rerun.

The user then explicitly approved temporary lab Startup Disk selection and
Macintosh HD default restoration after the read-only diagnostic. M5 selected the
lab in System Settings, without clicking Restart. A separate read-only
`bless --getBoot` plus in-memory internal-volume/group/container comparison
confirms **LAB** as default, while Macintosh HD is still running. Earlier
sandboxed lookups were unconfirmed and are superseded by this successful
read-only observation. No security-policy query or change was made.

This supersedes the staging-authorization-pending language in the frozen offline
handoff, without changing that historical evidence. It does **not** authorize
installation, restoration, security changes, a policy reset or Linux boot.
Boot021 restoration is still outstanding; the prior contained EXACT_31AF is
not a fresh query. Never tell the human that an installed boot021 screen is
expected. No lab boot belongs to this diagnostic.

## Prepare M1's browser page

Use the already verified `build/31al-m1-pages/recovery.html` from your review,
through the same reviewed controller. Do not rebuild, retransmit files, restage
or repeat the 86-method suite. Its exact HTML is 7755 bytes with SHA-256
`824708ed2e0da1991f1a5fbf7870597aca7dc1aaf554622c5a33b17a6e36b835`.
The title must say **31AL read-only diagnosis**. This is the one-box diagnostic,
not any old install/restore page. The route remains `/31aj`.

When the human is ready, start the bounded read-only page server with your
explicit private LAN IPv4 address, using the controller's `--page`, `--bind`,
`--port 8031` and `--seconds 1800` arguments. The controller verifies the page
and source closure before opening a socket. Send its complete live URL directly
to the human; keep LAN addresses out of Git. No proxy, USB session, M1 restart
or camera calibration is needed. Camera stays off/covered for credentials.

Before M5's shutdown cue, require M5 confirmation that staging succeeded,
the exact new page is available and the paired-Recovery entry gate below is
resolved. Starting the server is not a restart cue. An expired server may be
restarted without repeating any Recovery diagnostic.

## Paired-Recovery entry gate

Held-power Recovery follows the default/blessed installation. A login-volume
chooser or merely highlighting a Startup Options tile does not establish lab
pairing. This behavior is documented by
[Apple](https://support.apple.com/en-mide/guide/security/sec4cf9d63a6/web) and
[Asahi](https://asahilinux.org/docs/platform/security/#paired-recovery).

The temporary selection and return are now explicitly authorized and selection
is confirmed; no further approval or selection operation is needed. This
resolves the repository host-protection gate for this exact default change.
The next sequence is:

1. M1 starts the exact reviewed page and gives the human its complete private
   live URL. M5 checks readiness before giving the shutdown cue. There is no
   need to restart M1 or repeat the Startup Disk selection.
2. After the exact new page is ready, save work and shut M5 down. From fully
   off, hold power until startup options appear, then choose **Options →
   Continue**, not the lab boot tile. Authenticate only in the system prompt.
3. After the diagnostic, restore **Macintosh HD** as the default and return to
   its desktop. An ordinary restart into Macintosh HD for that return is part
   of the explicit temporary-selection approval. Never change security modes,
   SIP, CTRR, boot objects, partitions or firmware.

Do not give the restart cue until the new page is available. If Recovery reports a different pairing,
record the finite refusal and stop; do not interpret it as a firmware or parser
failure, choose another target or retry the block.

## One read-only diagnostic, then original return

In the lab's paired Recovery browser, open the verified new page. Click its
single box, Command+A, Command+C, quit the browser, open Utilities Terminal and
paste once. No clipboard trial or second install/restore box. This diagnostic
copies only helper/profile to private scratch, reads guarded metadata and shows
only the strict finite record before cleanup. No persistent baseline or key is
created. The helper has no installation, restoration or write-authorizing mode.

Capture the safe helper and shell JSON visibly emitted in Terminal before
leaving: `status`, `stage`, `failure_kind`, `reason`, command/exit/count and fixed
flags. A photo of just that safe result is sufficient; keep credentials, raw
policy, identifiers, private snapshots and other screen contents out of it.
Pasted source text is not emitted evidence. A diagnostic refusal exit2 can have
valid display-validator exit0; that remains a refusal. Do not print rejected raw
output after `VALIDATOR_FAILED` or treat `INITIAL_ADMISSION_PASS` as boot permission.

Stop after this one diagnostic, whether pass or refusal. Return to Macintosh HD
and its default through the approved sequence. Confirm desktop and default
separately, without another routine policy command. Publish only the finite
safe record and actual result. Keep install/restore/Linux/SMP/performance NOT RUN
and boot021 restoration OUTSTANDING. M5 interprets the finding before proposing
any change; genuine pairing/security/identity refusals remain stops.

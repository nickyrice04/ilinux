# Attempt31I — connection-stage exception; normal Macintosh HD return

**Observed,2026-10-21 Eastern:** one authorized31I supervisor invocation returned
**STOP / connect / InvalidFileException**, controller/supervisor exits **1/1**,
no supervisor deadline. Controller elapsed **0.099s**, supervisor **0.526s**.
Human confirmed the usual Macintosh HD desktop at **+35.607s**, within90s.
**31I is consumed; no retry, reconnect or further target command.**

The minimal saved result establishes a connection-stage failure before a
Controller instance/preflight result was available. **No new reset readback,
PS/core-state, recorder/arrival, CPU1 timer or park evidence exists.** Mutation
and startup counters are absent rather than measured zeros. **Linux boot and
native Linux SMP NOT RUN; CPU1 entry remains unverified.** This is not a CPU1
arrival timeout or a test of the corrected reset gate on hardware.

Sanitized exact final schemas:
[controller](attempt31i-controller-2026-10-21.json),
[supervisor](attempt31i-supervisor-2026-10-21.json).
Private journal/stderr, registry data, USB paths, identifiers and Apple artifacts
are not published. No actual registry dump or traceback was retained for this
failure. No full register value appears in either public result.

## Provenance and offline gates

Handoff `89a0947d6d3d80e2e71511ff96695d9aedb3a8ad`;
published readiness/execution `ca8d7acf9081f1d07037cb41d864711f1388d49b`.
[Independent readiness](attempt31i-m1-offline-2026-10-21.md): **202 pins and429
image-only test methods PASS**, no skips/source repairs. Both documented
offline commands and retained13-file package verification exit0. Symbol mode
`reviewed_layout_only`; **full-symbol checks NOT RUN on M1**. M5's separate
firmware/VM evidence was not independently rerun on this Mac.

31I source-manifest SHA-256:
`5c8279f96f85b424df0eaee2792a2be830a7d4604fa3e976fa3e2c3047b4a2c6`.
All186 frozen31H source pins also remain unchanged. Existing3,932,160-byte
boot021 image SHA-256:
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
Client stays clean at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
Prior31B–31H live receipt digests unchanged; no receipt reset/deletion/replacement.

After publication, human authorized **“Start 31I; all confirmed”**: fresh M5 lab
proxy session, direct cable, powered Macs, healthy awake/unlocked/open-lid M1,
independent90s timer. Those setup facts are human-reported. Timer cue immediately
preceded the single documented supervisor with `--confirm START-CPU1-J716C-31I`.
Wrapper start **2026-10-22 02:14:13.068 UTC / 2026-10-21 10:14:13 PM Eastern**.
No separate preliminary live check was run.

## Recorded outcome and evidence limits

| Field | Saved result |
|---|---|
| Controller result / phase / reason | STOP / connect / InvalidFileException |
| Controller started (supervisor) | true; child process spawned |
| Controller / supervisor exit | 1 / 1 |
| Controller / supervisor elapsed | 0.099s / 0.526s |
| Supervisor reason / deadline | controller_exited / false |
| Private consumed journal | 2 complete records: reservation and minimal final result |
| Controller stderr | only expected clean-client pin verification line |
| Reset readback decision / observation | absent; NOT RUN |
| RAM/UART/live-ADT/permission/publication checks | absent; not reached |
| PS / added core-state / recorder / arrival samples | absent; NOT RUN |
| CPU1 startup counters / mutation counters | absent; no recorded counts |
| CPU1 callbacks / progress / park | absent; not established |
| Linux boot / native Linux SMP | NOT RUN / NOT RUN |

`controller_started:true` means the supervisor spawned its child; it does not
mean that the native Controller class ran, or that CPU1 started. The final
connect fallback is emitted when the class has not been constructed. All
later-stage absence is retained instead of filling in hypothetical zero values.
No reset-gate PASS/refusal or register-access safety conclusion follows.

## Offline investigation of the exception class

**Likely:** host USB discovery's plist parse. `usb_identity.discover()` runs
a read-only IOService query and passes its stdout directly to
`plistlib.loads()` before serial selection/construction. The reviewed local
path exposes `InvalidFileException` for non-plist data. The live wrapper saves
only the exception class and deliberately discards private console details;
there is no traceback or stdout available to prove the exact call/input.

Three synthetic offline cases were run with the discovery subprocess fully
mocked; no actual IORegistry call, USB open or target request:

| Synthetic stdout | Result |
|---|---|
| Empty bytes | InvalidFileException |
| Non-plist bytes | InvalidFileException |
| Valid plist containing an empty list | Discovery parses; zero ports |

This reproduces a plausible software path, **not the original input**. Actual
empty/malformed output, enumeration/cable timing, command behavior and other
possible causes remain unconfirmed. A valid empty registry differs from an
unparseable stdout; do not conflate them or call this a proven target USB
hardware failure. No real follow-up registry query was issued, no discovery
retry, and no pinned production/test source changed. Private synthetic evidence
is in ignored build; only these original conclusions are public.

The pinned source places serial construction after successful discovery. If
this identified path caused the recorded exception, it occurred before a serial
open/target RPC. That conclusion is **conditional static inference**, not a
saved transport trace. The result supplies no new hardware mutation count or
CPU1 measurement; previous31G/H observations remain separate.

## Return and next action

Immediately on supervisor completion, human was instructed to power off and
select Macintosh HD before inspecting details. Human confirmed usual desktop;
confirmation recorded **2026-10-22 02:14:48.675 UTC / 2026-10-21 10:14:48 PM
Eastern**, **+35.607s** from wrapper start. This is the confirmation interval,
not precise power-off or macOS boot duration. No return problem was reported.
No post-outcome target command, retry/reconnect, cleanup RPC or rollback.
Owned bounded caffeine process had already exited; no process was signaled.

Routine policy checks remain waived. Original Full/lab Permissive and Macintosh
HD default stay last reported, not freshly verified. Installed boot021,
verified boot042 package, client, macOS and all settings remain intact.
No image/root transfer, install, extra core, volume/security/default/firmware
change or Linux command. No performance or all-core support claim.

M5 owns the next review: diagnose the host discovery/parser failure and prepare
a separately pinned remedy with offline error-path coverage before a fresh
human-started session. Preserve consumed31I/source closure/receipts. Do not rerun
31I, catch the exception and continue, guess a USB port, or weaken the reset/
address/lock/guard gates. CPU1 campaign measurements remain uncollected.
Frozen pre-execution NOT RUN wording is historical; this report supersedes it
only for the consumed31I supervisor session.

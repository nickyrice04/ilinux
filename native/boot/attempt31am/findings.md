# 31AM: conditional read-only Preboot preparation

November 14, 2026. Implementation is qualified offline. All actual Recovery
mounts and native tests remain NOT RUN; no host settings or boot objects change.

31AL's captured `PREBOOT_MOUNT_PATH` identifies a lexical guard failure, not its
actual input or an Apple CPU failure. The new preparation code addresses the
missing mounted-volume prerequisite without changing the original collector.
The already-built reported18-core Aura/Linux source pair stays unchanged.

## Original and reused components

The frozen31AL generator still checks the four original C/header source hashes
and proves its observation marks strip to byte-identical original state code.
The old collector, policy parser, identity/path/paired-Recovery/security predicates
and initial-admission validator are retained. The new companion adds only a
conditional preparation stage, strict outer result, cleanup and corresponding
fixture controls. No installer, restoration, private snapshot/key or boot mode
is introduced.

Asahi's pinned installer informed the role-selection → preparation → fresh
observation sequence. The ordinary installer mount is not copied wholesale.
The new implementation uses a fixed Apple mount helper directly, with read-only,
nobrowse and nofollow options, avoiding the Disk Arbitration frontend that
documents a possible preliminary filesystem check. No fsck/repair/update/force
command or fallback is present. The installed mount manuals support these
options; they do not prove live Recovery executable availability or internal
filesystem/firmware behavior. Missing prerequisites cause a finite refusal.
See the pinned public source comparison in
`research/attempt31am-preboot-next-2026-11-14.md`.

## Evidence-based mount state

A bounded read-only desktop metadata observation, after the frozen target
identity checks, found an absolute Preboot path and `Writable=true`, while
`Mounted` and the queried read-only plist fields were absent. Only those known
field classes were returned; no private identifiers or policy data were saved.
`metadata-shape.json` records this. It does not establish Recovery's field shape.

The new preflight therefore never interprets a missing field as unmounted.
It corroborates path state with a successful bounded kernel mount-table
observation, repeats target identities before attempting a mount, and checks
kernel filesystem source/mount point/read-only flags afterward. Optional
metadata cannot contradict that evidence. Unsupported, ambiguous, incomplete
or inconsistent observations stop.

Existing valid mounts are not changed. Only positively unmounted Preboot with
empty mount path may be mounted once at a new private scratch child. The lab and
Original share this container's Preboot; there is no invented lab-only volume.
The new mount is bound to its source and owned scratch parent. Its overlaid
directory has different identity while mounted; the underlying directory is
checked after unmount, not mistaken for the mounted filesystem root. Cleanup
never touches an existing or foreign mount and never forces unmounting.
If cleanup remains uncertain, preserve the result and stop. The separately
approved Original return can leave Recovery through shutdown and a one-time
Macintosh HD selection, then restore its default in the running Original OS.
It does not require an improvised unmount or a Recovery Startup Disk write
through the potentially read-only shared Preboot.

## Output and limits

The safe outer result distinguishes initial state, attempt, observed ownership,
actual read-only verification, original diagnostic result and cleanup. The
strict validator reconstructs only finite allowed fields; raw captured bytes,
stderr, paths, identifiers, private policies and unknown-object hashes are not
displayed. Shell scratch copies are filesystem writes, so flags refer expressly
to **Preboot** filesystem write requests, boot-object and security changes.
Mount-table state can change; publication grants no execution authorization.

Fixture backends model original and overlaid directory identities, mount-command
failure after a mount appeared, metadata/key omissions, invalid paths, uncertain
source, read-only checks, cleanup refusal and failures in the later diagnostic.
They execute no real mount, unmount, disk or policy commands. SDK compilation,
normal/sanitizer tests and a clean source-only export are recorded separately
from any live outcome in `build.json` and `offline-verification.json`.

The 50 changed methods pass: 28 native, 12 renderer and 10 package controls, plus
the same 28 native methods under ASan/UBSan. Independent review also exercised
the changed suites; after a final narrow exit-contract correction it reran only
the two affected controls normally and under sanitizers. No old86-method suite
or unchanged Linux/Aura build was repeated. The new SDK helper is124464 bytes;
the local two-file kit and its canonical profile are pinned in `delivery.json`.

M1 next performs the focused offline review in
`tools/m1n1-client/attempt31am-instructions.md`. New staging, page serving,
Startup Disk selection and Recovery execution wait for review and explicit
physical authorization. No restart is ready at offline publication. Original
Full Security stays unchanged; boot021 restoration remains outstanding.

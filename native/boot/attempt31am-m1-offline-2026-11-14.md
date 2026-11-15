# M1 independent 31AM offline review

November 14, 2026. Reviewed main **cb610d8** in the clean review checkout.
**OFFLINE_PASS_PHYSICAL_CHECK_HELD**; no actionable finding from this review.
The dirty primary checkout and all previous artifacts remain preserved.

## Verified inputs and focused execution

All **111 tracked source pins PASS**, retaining all **92** 31AL bindings exactly.
Inventory SHA-256: `0d080629d2cb8ae35d347431cc754ab8bd45807f8a83f17b26b03e8c78b65231`.
The new local directory contains exactly two regular files, independently checked
against Git delivery/profile pins before copying those two files into ignored
review build storage:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| ilinux31aj-reader | 124464 | dea9e20ab3c81d2054790af0922d304f4abe1ae621bee43992373b1666a3f28f |
| profile.json | 823 | 0ee80fb6bc186f964795eb0cc35e1bd47bc642602a4ce8153cf460830b119f6a |

Canonical profile equals Git exactly. The unchanged candidate and boot021 entries
are identity metadata; no candidate, rollback, RAM root or key was retransferred.
The production helper was not executed or replaced with a locally compiled one.

Fresh workspace-only suites, Python3.9.6 / Apple clang17.0.0 / SDK26.0:

| Suite | Methods | Seconds | Result |
| --- | ---: | ---: | --- |
| Native synthetic controls | 28 | 3.593 | PASS |
| Renderer | 12 | 22.067 | PASS |
| Package | 10 | 3.794 | PASS |

**50 unique methods PASS**, each process exit0. Runs used caffeinate and temporary
storage under build. The tests compiled original synthetic C controls and ran
fixture backends, not live mount, disk or policy commands. The original-generator
stripping/byte-identity proof passes. The prior86-method review is reused.
M5's six lexical regression controls and 28 new native sanitizer controls were
reviewed as separate producer evidence, not rerun. M5 SDK/export/self-bound
production controls also remain attributed evidence; their raw execution was not
reproduced by running the production helper on M1.

## Review findings

**Confirmed in source and synthetic controls:** missing Mounted metadata is not
interpreted as false. Positive bounded kernel-table absence, an empty path and
repeated identity observations gate the single new mount. Existing valid mounts
are bound and left untouched. The mount uses the derived role-selected device,
fixed read-only/nobrowse/nofollow options and an owned child of held scratch CWD.
The lab and Original share this container's Preboot; this is not a separate
lab-only Preboot volume.

Fresh post-mount descriptors check kernel source/path/APFS/read-only binding;
the underlying directory's retained FD is kept separate. Only a verified owned
read-only mount can receive a nonforced unmount. Mount/unmount command failures
are followed by fresh observations. Changed identity, unverified read-only state,
partial failure or uncertain cleanup stays a refusal, with conservative output
if a result invariant fails. No shell fallback unmount, recursive deletion,
repair, writable remount, installer or native-boot mode exists.

The unchanged collector and initial validator still own pairing, security,
selected-object and policy checks. Preparation is not proof those checks pass.
The finite20-key outer result and16-key nested record are reconstructed by strict
validation; rejected raw captures are not echoed. Fixed scratch cleanup cannot
recursively remove a native mount child. The future stage mode retains the
reviewed target guards and changes only its new destination name.

Installed Apple mount_apfs(8), mount(8) and diskutil(8) were read without executing
any mount tool: the named options and documented frontend distinction are
supported locally. This does not establish Recovery availability, live kernel
metadata shape, internal APFS behavior or successful cleanup. Actual kernel
mount enumeration/commands remain unrun. Fixture complete-success records are
exercised through the strict output validator; no physical success is claimed.
The prior physical MountPoint remains unknown; unmounted/empty remains a
hypothesis. M5's existing attributed CPU/Asahi source comparison was reviewed;
no new external retrieval, firmware query or native reproduction occurred here.

## Exact inert page and preservation

Actual preparation and socket-free check match both M5 receipts exactly. The
HTML has one inert textarea whose decoded contents equal the complete command
block; Bash syntax passes. No production block or server ran.

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| diagnose-paste.txt | 5615 | 22146e7dc64d08556a2681eedcef2fb341190e87d93d2acbc68230d04ae9c207 |
| profile.json | 823 | 0ee80fb6bc186f964795eb0cc35e1bd47bc642602a4ce8153cf460830b119f6a |
| recovery.html | 8343 | e76b0b1c2d55c6b7d91d429b9b24bb3ad43c49d267bb1bef9c4f0b81fa522a9f |

All **75** inventoried previous kit/page/review/evidence/closed-session files
verify unchanged before and after, including the earlier54-file preservation set.
All111 source pins remain exact. No old receipt/state reset, Linux/Aura rebuild,
old-suite repetition, host metadata/mount query, camera, proxy, Mac restart,
settings/security/volume action or external artifact upload.

## Handoff

M5 can review this result before obtaining one explicit combined authorization
for the new tiny-kit lab Data copy, temporary lab default/Original return and
one conditional read-only shared-Preboot Recovery check. A read-only mount still
changes mount-table state. No restart is ready merely from publication. Existing
valid mounts stay untouched; uncertain cleanup requires a stop and report, then
the separately approved one-time Original return, not improvised mount commands.

New staging, Recovery/mount/cleanup, install/restore/Linux/SMP/performance remain
**NOT RUN**. Boot021 restoration remains **OUTSTANDING**. Original Full is required;
31AL's desktop/default return remains the last human-confirmed result. No fresh
policy query or boot permission follows from offline preparation or admission.

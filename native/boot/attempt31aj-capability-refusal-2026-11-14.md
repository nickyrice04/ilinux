# 31AJ Recovery capability refusal — November 14, 2026

**Result: RECOVERY_PREFLIGHT_REFUSED_BEFORE_ENROLLMENT.**
The supplied Recovery photo confirms a deployment-path incompatibility sufficient
to explain the refusal. This session stops; no install/restore retry or native
boot follows. Original desktop/default return is still pending human confirmation.

## Observed evidence

The first pasted install block returned `REFUSED`, reason `preflightRefused`,
read_only true, writes_authorized false and native_ready false, followed by
`STOP: helper capability`. No candidate success result is shown. The success
string at the top of the photo is part of the pasted shell source, not an emitted
postcondition result.

The photo resolves the earlier transcription uncertainty: root is 0, model is
`Mac17,6`, `/System/Installation/CDIS` is a directory, and Recovery reports macOS
26.6.2 / 25G83. The decisive listing is:

```
/private -> System/Volumes/Data/private
```

`/private/tmp` resolves to a directory. The separate staged-helper
`--codec-selftest` returned `SYNTHETIC_CODEC_PASS`, controls 4, real_lzfse_api true,
host_queried false, writes_authorized false, native_ready false, exit 0. This is a
synthetic in-memory Recovery runtime control, not target-state admission or a
native Linux result. Human-provided media was inspected in chat and is not copied
into Git or uploaded.

## Confirmed source incompatibility and inference limits

`tools/recovery31aj/render.py` creates WORK with
`mktemp -d /private/tmp/ilinux31aj.XXXXXX`, copies the pinned profile/helper into
it, and passes the lexical WORK/profile.json pathname to the helper. Shell hash
checks follow that system link. `main.c` loads the profile before
`recovery_admission()` or its embedded compression control. In `json.c`, that
profile is read by `read_file()`; `core.c:secure_open()` opens every component
using O_NOFOLLOW and directories using O_DIRECTORY. The first `private`
component is therefore rejected in the photographed Recovery layout. Only the
executable pathname is canonicalized by main; the supplied profile pathname is
not canonicalized.

**Confirmed:** the frozen renderer/helper pair cannot read its profile through
this observed system alias. **Source-derived inference:** this accounts for the
generic capability refusal before admission. No instrumented branch trace or
errno was collected, and no canonical-path retry was performed. Fixing this
incompatibility does not prove that later pairing, snapshot, policy or native
checks will pass. The successful separate codec control does not change those
limits. No firmware prohibition or native CPU/performance conclusion follows.

## Mutation boundary and current status

The capability check precedes transaction-state creation, comparison-key
generation, initial target snapshot, mutation markers and every kmutil/bputil
write in the reviewed block. Consequently this reported execution did not reach
boot-object installation or policy mutation. Temporary copies were made; their
cleanup is specified by the EXIT trap and was not independently listed afterward.
No successful paired-Recovery admission or fresh policy preservation readback is
claimed. Prior initial 31AF selection is an earlier observation, not a new read.

The independent restore block requires a persisted baseline/key, which this
invocation did not create, and contains the same work-path issue. Do not run it
blindly after this pre-mutation refusal. No state or consumed receipt has been
deleted, reset or re-armed. Current status:

| Step | Result |
| --- | --- |
| First Recovery capability check | REFUSED, photo-confirmed |
| Separate Recovery synthetic compression control | PASS, four controls, exit 0 |
| Candidate installation / policy mutation | NOT REACHED |
| Transaction baseline/key creation | NOT REACHED |
| Native observation / 90-second window | NOT RUN; zero windows used |
| Linux / SMP / performance | NOT RUN |
| Restoration block | NOT RUN |
| Macintosh HD desktop/default return | PENDING human confirmation |

## M5 handoff

M5 owns the offline correction proposal. Preserve all frozen inventories and
artifacts. Review canonicalization of the newly created, owned work directory
before deriving helper/profile/snapshot paths, while retaining descriptor-based
no-follow checks and directory identity/ownership binding. Do not weaken the
no-follow rule, alter Recovery's /private link, or perform an in-session pathname
edit/retry. Add an end-to-end Recovery-like symlinked-/private fixture covering
both install and restore rendering, not only final-file symlink rejection.
Phase-specific failure advice should distinguish this pre-baseline refusal from
an uncertain post-write result; restore must still require its independent guards.
These are proposed offline review directions, not a validated patch or boot cue.

All 62 tracked portable source pins and all four original reviewed page/phase
output size/hash pairs were rechecked PASS. Inventory SHA-256 remains
92b7612fe86ad7fc58dca09ac94b09160d00e1733365e139f077f1e37b5ec92f.
No suite rebuild/rerun or production-helper execution on M1 was needed. Existing
247-method and 23-method reviews remain historical evidence and did not cover
this actual Recovery deployment outcome. Code, binaries, pages, earlier dirty
notes and consumed receipts remain untouched. Camera remains off; no M1 restart,
USB/proxy, volume operation, new security change or extra native experiment.

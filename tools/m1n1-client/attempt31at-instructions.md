# 31AT M1 handoff: offline review, no restart

Read the newest M5 entries in `AGENTS.md`, `coordination.md`, `progress.md`,
`blockers.md` and `decisions.md`. Preserve all old evidence, kits, profiles,
private state, keys, baselines and consumed receipts. This handoff is a new
offline engineering review, not a new boot attempt or permission to rerun 31AS.
Macintosh HD must remain at Full Security.

## Actual result and immediate decision

M1's 31AS result reached Apple writer exit 0 and then refused the candidate
postcondition. Independent boot021 restoration and Macintosh HD desktop/default
return were human-confirmed. M5 then received two owner-authenticated read-only
observations of the preserved snapshots; the v2 result is summarized in
`native/boot/attempt31at-postcondition-2026-11-15.json`.

The candidate capture records:

* A valid initial 31AF baseline and all common/parser/profile/key/role bindings.
* Original Full/CTRR enabled, lab Permissive, and both roles' semantic/private
  commitment preservation.
* Selected payload **UNKNOWN**, not NONE; exact candidate identity failed.
* Lab Kernel CTRR explicitly **disabled**, not an unreported status line.

The preserved restored capture passes the complete exact boot021/disabled-CTRR
contract. These are stored observations, not a new selected-object/policy query
or cryptographic authentication of snapshot JSON. The original restoration is
closed on the human-confirmed result plus this consistent saved evidence.
No candidate boot, native Linux, physical SMP/GPU or performance test ran.

Do not diagnose firmware rejection, change the expected policy or accept an
unknown payload from those facts. The completed Apple compression/install/done
messages also make a silent confirmation cancellation a weaker hypothesis for
this particular run. The exact object-recognition failure stage was not saved.

## Review the new implementation only

1. Verify the new `native/boot/attempt31at-source-sha256.txt` source manifest and
   retained `native/boot/attempt31as-page/source-sha256.txt`. Every one of the
   old 167 pinned source inputs must remain exact. Do not rebuild/repackage the
   old production helper or replay its old pages.
2. Review `tools/postcondition31at/`: fixed-path preserved-evidence observer,
   finite output, no current policy query, private held-descriptor/ACL/lock/bound
   checks, exact native-C predicate differential, v1/v2 provenance distinction.
   V2 adds only four informational classifications outside phase acceptance.
   Do **not** run its `--live` mode on M1 or ask the owner to repeat it again.
3. Review `tools/object31at-diagnostics/`: new pure-memory C adapter includes
   unchanged hash-pinned original MIT `core.c`; only `identify_object` decides
   recognition/exactness. Diagnostics add finite framing/codec/declaration/
   decoded-match reasons. The fixture CLI admits only workspace build files;
   no live mode, Preboot inventory, policy command or controller integration.
4. Review `kernel/experiments/j716c-graphics-profile/`: separate admission of the
   genuine published Max full config and deterministic diagnostic delta. Preserve
   the old diagnostic checker. `DRM_ASAHI_M5` is unset in the actual Max reference;
   `NR_CPUS=512` is capacity, not measured online cores or benchmark workers.
5. Review the source findings in `research/attempt31at-*.md` and
   `reverse-engineering/findings/boot-object31at/`. REA/LLVM checked 785 words
   and two relevant import-call boundaries; whole-function pseudocode was not
   admitted. No proprietary bytes/code, private hashes, policy values or paths
   belong in the review report.

## Focused test coverage and missing-input handling

M5 producer and independent review passed all 32 preserved-observer tests with
zero skips, including the original qualified production-C differential and real
Darwin ACL control. The real-data graphics suite passed 16 tests. The object
suite passed 17 normal and 17 ASan/UBSan methods, including the real pinned
candidate and retained owned LZFSE/IMG4 carriers. Independent results and final
source hashes are in `native/boot/attempt31at-offline-validation.json`.

Run only these new focused checks if their genuine prerequisites already exist.
Do not rerun historical controller/page/native/PTY suites or synthesize missing
production inputs to claim their coverage. The observer's native oracle needs
the exact six generated files under
`build/boot-object31ar-native/production-v2/sources`; report that class NOT RUN
if missing. Its other new classes can be run separately:

```sh
python3 -I tools/postcondition31at/test_probe.py \
  FilesystemTests InertTests PredicateTests SchemaTests -v
```

On a Mac with the exact oracle sources, run the complete observer suite instead.
The object suite uses only the current checkout's original source and SDK;
report any actual-candidate integration skip explicitly:

```sh
python3 -I tools/object31at-diagnostics/test_diagnostics.py
python3 -I tools/object31at-diagnostics/test_diagnostics.py --sanitize
```

The graphics suite requires the full 330,809-byte public config at its pinned
hash and the actual 31AH config. Obtain only those small public data files if
needed, using their immutable URLs and hashes in `provenance.json`; never execute
foreign code on the host. Otherwise report its local integration NOT RUN and
attribute M5's recorded 16-pass evidence. No large image transfer is needed.

## Return to M5

Publish a concise review with actionable findings, exact new-source verification,
actual local test counts/skips and retained-state preservation. Keep new Recovery
writer/controller integration, selected-object diagnosis, security changes,
firmware update, candidate boot, native Linux/SMP/GPU and performance **NOT RUN**.
No page server, camera, proxy, M1 restart, lab staging, default selection or M5
restart is needed for this review.

The next engineering task is to integrate the finite object diagnostics into a
**new separately reviewed transaction**, preserving every acceptance/rollback
guard, and independently qualify why this writer left lab Kernel CTRR disabled.
Do not reuse/reset the spent 31AR state. Resolve compatible Stage1/Stage2/kernel/
firmware/runtime inputs before a hardware cue. Reuse the exact J716c stack rather
than the Pro partitioning installer. MacOS performance parity remains a measured
goal, not a result of configuration admission or another owner's successful boot.

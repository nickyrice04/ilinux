# M1 review of the complete 31AJ handoff

2026-11-13. Reviewed commit `d7a93a9` in the isolated checkout.
**Result: artifact integrity and focused tests PASS; page source closure BLOCKED.
Native HOLD.** One actionable delivery finding; no live action was performed.

## Finding: producer-only executable blocks source closure (P1)

`native/boot/attempt31aj-kit/source-sha256.txt:56` requires
`virtualization/jobs/097-direct31aj-readable/out/test-readable-host`.
That file is ignored, untracked and absent from this checkout. It is also not
one of the four specified transfer files. The other 56 inventory entries match.

The published review command stops with FileNotFoundError at this entry. The
actual page-preparation command independently returns REFUSED (exit 2), before
creating its output. `prepare.source_closure`, the fixed-page server and the
future lab stager all depend on this same closure. M5's successful local page
preparation is therefore not reproducible on the receiving M1 from Git plus
the documented four-file handoff.

Keep a producer-local executable hash in its build evidence rather than as a
required consumer source file. M5 should publish a corrected source inventory
and refresh the preparation receipt's inventory binding. Preserve the frozen
old inventory/evidence as history; do not copy or execute an extra producer
binary, silently skip the entry, or edit an old receipt to make the check pass.
The unchanged code and tests can reuse this review after the closure-only fix;
then repeat exact inventory verification, real page preparation and socket-free
page verification. No binary rebuild, camera retest or restart is requested
solely to fix this delivery issue.

## Folder and exact artifact verification

The user's `ilinux-31aj-review/` directory exists and contains all four expected
regular files. Every delivered size and SHA-256 matches Git before any parsing,
decompression or execution:

| File | Bytes | Result |
|---|---:|---|
| aura-31aj-inline.macho.gz | 15,985,266 | PASS |
| runtime-31aj.tar.gz | 16,031,216 | PASS |
| readback31aj | 89,312 | PASS |
| m1n1-boot021.bin | 3,932,160 | PASS |

Verified copies were placed in a new ignored workspace intake. The actual
package verifier passes all 15 archive-member bindings, the unchanged kernel,
new init/root, exact inline candidate, retained Aura prefix, padding, original
source relationships, helper identity and exact boot021. Archive content was
checked in memory, not extracted or executed. Candidate expansion is
153,190,400 bytes / SHA-256
`1ea24f0de4aa7d3e82c70a1b35f815791a48342db1a060100226b84dca7d7d01`.

Actual workspace materialization PASS: candidate, helper, exact boot021 and
canonical 822-byte profile are created in a new private build directory; its
receipt is a sibling sidecar. This is workspace preparation, not lab staging.
The delivered production helper was hash-inspected and never run.

## Independently run focused checks

| Suite | Methods | Result |
|---|---:|---|
| Recovery transaction | 64 | PASS |
| Lab stager with synthetic backend | 25 | PASS |
| Fixed-page server (synthetic loopback controls only) | 24 | PASS |
| Package intake | 25 | PASS |
| Workspace materializer | 15 | PASS |
| Collector source boundaries | 4 | PASS |
| Value-free metadata-shape probe | 26 | PASS |
| Native reader with ASan/UBSan, synthetic fixture build | 64 | PASS |
| **Total** | **247** | **PASS** |

Separately compiled and ran the original portable display test with ASan/UBSan:
9,263 assertions PASS, maximum 78 columns / 35 rows. These are assertions, not
9,263 test methods. No Linux executable from the delivered archive was run.

Rendered both complete blocks as inert review data from the verified source:
install 5,935 bytes, restore 6,691 bytes, HTML 17,306 bytes. All match M5's
published output hashes; both blocks pass `bash -n`. Neither block was executed,
pasted or served. This render-only equality does not bypass the failed source
closure or establish a production-prepared page. Actual page check-only is
NOT RUN because production page preparation failed.

## Source review and reused evidence

Reviewed the bounded native reader/codec, strict JSON/profile binding, synthetic
versus Recovery scopes, supported semantic fields and private comparison-key
commitments. Reviewed shell admission versus bound baseline, spent markers,
mutation/readback branches, and restore's independence from candidate presence.
No `bputil -n`, automatic restart or Startup Disk command is in the blocks.
Unknown object identity is admitted only in the intended recovery phases;
candidate/final identities remain exact. This review does not claim every
LocalPolicy byte is preserved or that arbitrary JSON assertions are attested.

The readable collector reuses workload/check/deadline logic and adds console
block text; no new framebuffer, backlight or brightness control is implemented.
Native legibility, rapid-scroll recovery and brightness persistence remain
unqualified. `Txx` is a loop tick, not the independent native wall clock.

M5's actual-artifact C/codec phase controls, public parser controls, Apple
read-only inspector, generic four-vCPU VM and REA/interface evidence were
reviewed as producer receipts, not independently rerun or raw-capture reproduced
on M1. The package check binds its embedded build/VM summaries to the actual
received artifacts. No producer-bound production-helper fixture mode was run.
Earlier 31AH/31AI/component reviews were reused; their 41/46/7 inventories
verify unchanged. All 57 kit entries were inspected: 56 match, one is absent.

## Preservation and next step

Original checkout's five unfinished notes, unrelated review file and all four
delivery files verify unchanged. No frozen inventory or member was edited.
Previous evidence and consumed receipts were not reset or re-armed. Media,
binary files, private paths, keys and policy values are excluded from this report.

M5 next fixes the portable source closure and republishes the corresponding
page-preparation evidence. **Lab staging, Recovery/helper admission, install,
native boot, live checks, restoration, default restoration and performance:
NOT RUN.** No production server, camera session, restart, USB/proxy, firmware,
volume, policy or default operation occurred. Physical readiness/authorization
does not follow from the passing software checks.

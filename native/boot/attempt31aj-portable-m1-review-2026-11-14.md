# M1: portable 31AJ correction verified; offline page ready

2026-11-14. Reviewed commit `4cddd22`.
**PASS: prior source-closure blocker resolved; exact offline page prepared.**
No actionable issue found in the correction. Physical steps remain NOT RUN.

## Independent verification

All **62 portable source pins** match and refer to Git-tracked files. The original
57-entry inventory remains unchanged. The new closure retains the other 56
original bindings exactly and excludes only the specifically identified ignored
producer executable. That executable is still absent on M1; none was copied,
rebuilt or fabricated to satisfy a pin. Old 31AH41/31AI46/component31AJ7 source
closures remain unchanged.

Read the new adapter and tests. Source admission pins the old inventory, all
retained original source bytes and the new adapter sources. Local dependency
loads use verified snapshots; only the frozen stager/server inventory selector
changes. Hardware targets, artifact bindings, transaction and no-overwrite
guards are unchanged. No new production stage target override is exposed.

`caffeinate -i python3 -I tools/recovery31aj_portable/test_adapter.py`:
**23 new methods PASS**, covering closure/pin refusal, missing inputs, symlinks,
verified dependency loading, fixed dispatch boundaries and socket-free page
verification. Previous **247 focused methods**, display sanitizer assertions,
artifact intake and complete source/procedure review are reused; unchanged
suites and binary materialization were not repeated.

Existing four prepared workspace files verify unchanged. Ran the original
`prepare.py` with the new portable inventory into a fresh output directory:
**PASS, 62 verified sources**. Ran the new adapter's actual `--check-only`:
**EXACT_PAGE_VERIFIED, server_started=false**.

| Prepared output | Bytes | Comparison with previous reviewed output |
|---|---:|---|
| profile.json | 822 | Exact SHA-256 match |
| install-paste.txt | 5,935 | Exact SHA-256 match; bash-n PASS |
| restore-paste.txt | 6,691 | Exact SHA-256 match; bash-n PASS |
| recovery.html | 17,306 | Exact SHA-256 match |

Portable inventory SHA-256:
`92b7612fe86ad7fc58dca09ac94b09160d00e1733365e139f077f1e37b5ec92f`.
HTML SHA-256:
`4ba56bf59e81de9e682e202e13fedea6c39de4644c3a976437736cb8eb01601b`.
No phase block was pasted, executed or served. A production serving window/URL
will be started only when the human is ready for the separately authorized
Recovery visit, using the portable adapter and an explicit private LAN address.
No LAN address is published or needed for these offline checks.

## M5 staging report and remaining boundary

Reviewed `staging-result.json`: it records **user-pasted stager JSON**, with all
four lab files matching the canonical profile and staged=true. It reports no
policy read, boot-object installation, boot-setting/default change or volume
creation. This is producer/user-reported evidence, not an independent live M1
verification. No stage was repeated; the no-overwrite lab kit must be preserved.
M5's clean-export reproduction was reviewed as producer evidence; M1 independently
reproduced the exact page preparation/check above in its existing clean checkout.

The existing camera plan is reused: fresh framing after movement, actual
RECORDING confirmation before the human native cue, independent maximum
90-second timer, and stop/cover capture before Recovery authentication. No new
quality clip is requested. Fine text and boot-time brightness remain limitations.

Current staging/preparation permission does not authorize the separate complete
physical transaction. Enrollment, temporary lab Startup Disk selection if needed,
one diagnostic window, exact boot021/disabled-CTRR restoration and original
Macintosh HD desktop/default return require that transaction's specific human
authorization. Do not restart M5 merely because this offline page is ready.
Macintosh HD remains Full Security; no firmware update or policy-reset operation
is added. Recovery admission is a runtime preflight, not a desktop test.

## Preservation and unrun actions

Original unfinished notes/unrelated review file, existing prepared artifacts,
frozen sources, prior receipts and consumed evidence preserved. No rebuild,
new binary transfer, camera session, proxy/USB, production server, helper live/
capability/private-group/RNG mode, host settings change or restart performed.
**M1 live staging, Recovery, enrollment, native/live tests, restoration, default
return and performance: NOT RUN.** Page readiness is PASS; native authorization
remains pending, and no physical result is inferred.

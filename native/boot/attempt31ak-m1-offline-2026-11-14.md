# M1 independent 31AK offline review — November 14, 2026

**OFFLINE_PASS_NATIVE_HOLD.** Reviewed main `b0ffccc`. No actionable finding in
this focused correction. The new procedure addresses the observed Recovery
system-alias failure without changing the diagnostic, helper or canonical profile.
This review does not start another physical session.

## Fresh verification

All **72** inventory members are tracked and hash-exact, before and after checks.
All **62** earlier portable bindings are retained byte-for-byte; the old inventory
is unchanged. New inventory SHA-256:
`f795b4329bfc8b75c0ec9dfa54ef5f1703ed67d3847bf2e061dc1c5067763115`.

Ran only the two new suites under `caffeinate -i`, Python 3.9.6, isolated mode:

| Suite | Fresh methods | Result | Seconds |
| --- | ---: | --- | ---: |
| `tools/recovery31ak/test_package.py` | 14 | PASS | 0.435 |
| `tools/recovery31ak/test_paths.py` | 16 | PASS | 68.704 |

The full-shell fixtures reproduce old 31AJ's refusal under a symlinked private
layout, then exercise corrected install/restore under alias and direct layouts.
They test ownership/mode refusal, directory replacement, foreign-content
preservation, phase-specific failure advice, post-command readback, independent
restoration and no repeated commands after restoration. Filesystem and shell
resolution are real; root, hardware, policy and mutation tools are synthetic.
Production blocks were not executed on M1.

The existing verified kit was copied within the workspace into this clean
checkout because the preparer requires checkout-contained artifact paths. All
candidate/helper/rollback/profile bytes matched the previous pins. This was no
rebuild, download, delivery resend or M5 restage. Actual corrected page preparation
PASS; socket-free `--check-only` PASS. Its receipt equals M5's preparation receipt
exactly. All four generated size/hash pairs match, and both `bash -n` checks PASS:

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| install-paste.txt | 7883 | 9c054a830d4d217ec694592201fd77a0412d8bf932d882d38979ae8232df107c |
| restore-paste.txt | 8593 | b890a63d309985f45e80533e0803dad38e51b8b16c9215db15f756d54f067a6c |
| recovery.html | 22362 | 2423277989ae30d75345e7de32d6eac602a86cdfa2ee36ac87bc6eef0e7f0af5 |
| profile.json | 822 | e42e85b94961b86f7c882bb937dd35456dd790d307740233a9065498468dd6ab |

The profile is still exact 31AJ. The three rendered outputs intentionally differ
from old 31AJ. The page contains the exact new readonly phase boxes. No production
page server or socket was started.

## Independent source review

Only the newly created owned work directory is physically resolved. The shell
binds device/inode/root ownership/mode0700, physical path and held working
directory, then checks those bindings before use. Copies and snapshot output use
relative writes in that held directory. Cleanup unlinks fixed work filenames and
removes the verified empty directory; it no longer recursively removes an
absolute work pathname. A changed binding stops without cleaning foreign data.
Persistent transaction state and consumed markers are not removed or re-armed.

Volume/kit/state symlink checks, native descriptor-based O_NOFOLLOW reads, pinned
file checks, comparison-key and baseline requirements remain. Candidate
`kmutil ... --compress` arguments and exact raw boot021 entry2048/lowestVA0
restoration arguments are unchanged. The reviewed lab CTRR operation remains
`bputil -c -v`, guarded by fresh target binding; no policy reset is added.
Restoration still does not require the candidate file. Pre-enrollment failure
advice no longer directs a baseline-free invocation blindly into restoration;
post-command failures retain conservative state/readback guidance.

The package controller verifies retained/new source snapshots and substitutes
only the renderer/inventory in the original preparer/server. Default invocation
is inert; there is no staging or boot mode. Its new inventory has no ignored
producer executable. Both native helper bytes and all old source pins are frozen.

## Reused evidence, current state and limits

The prior **247-method** reader/artifact/transaction review is reused, not rerun;
the earlier portable review is likewise retained. M5's two actual unchanged-helper
file controls (alias refusal and canonical-profile/exact-boot021 verification)
and Git-only-export receipt were reviewed as producer evidence, not repeated on
M1. No production helper, Recovery admission, policy query, Apple inspector, REA,
VM, native Linux or performance operation ran in this review. The research
supplement was read as the M5 handoff; public hardware/vendor claims were not
independently re-fetched in this software review.

All **36** snapshotted existing kit/page/receipt/session files remain hash-exact,
including retained ignored intake receipts and the prior session ledger. Earlier
unfinished notes were preserved. No source, frozen page, binary or consumed receipt
was edited by this review.

M5's supplied post-refusal object record says configured contained payload
EXACT_31AF; it does not establish wrapper authentication, bootability or boot021
restoration. M5's separate return record confirms current/default original macOS;
M1 has not repeated those target queries. Preserve Macintosh HD Full Security.
The intended later sequence remains actual 31AF baseline → unchanged 31AJ RAM
diagnostic → exact raw boot021/disabled lab CTRR → Macintosh HD/default return.
The 31AJ display marker is correct because this is a procedure-only correction.

**31AK Recovery/install/native/rollback/Linux/SMP/performance: NOT RUN.**
No server, camera retest, proxy, restart, security/volume/default action or physical
retry occurred. Ready for a later user-started corrected sequence after go-ahead;
this offline PASS supplies no automatic boot authorization or entry guarantee.
Use the new 31AK controller/page when that sequence is authorized. The existing
camera plan and independent maximum 90-second native deadline remain applicable.

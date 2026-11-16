# M1 independent 31AV offline review — November 15, 2026

**OFFLINE COMPONENT PASS; native remains on hold. No actionable source finding.**
Main `21b4cee` was fast-forwarded into the clean active review checkout. The closed
31AU result remains unchanged: candidate selection changed and its file was read,
but decoding and the separate enabled-CTRR requirement failed; exact boot021
restoration and Macintosh HD desktop/default return are human-confirmed. No
repeated security check, private-state read or Recovery action was performed.

All **10 new pins**, **190 frozen AU inputs** and **303 prior evidence/artifact/
review/closed-session files** verify unchanged. Both fresh builds' four compiled
source hashes match M5 exactly. No frozen source or delivered test was edited;
no local helper was staged or substituted.

| Local mode | Published methods passed | Published method NOT RUN | Retained-candidate equivalent passed | Failures/errors/skips | Seconds |
| --- | ---: | ---: | ---: | --- | ---: |
| Normal | 11 | 1 | 1 | 0 / 0 / 0 | 12.335 |
| ASan/UBSan | 11 | 1 | 1 | 0 / 0 / 0 | 14.001 |

The published `test_exact_owned_candidate_both_encoders` hardcodes the absent new
AU kit. Its method was not run. Instead, one review-only equivalent method per
mode exercised the same genuine-candidate assertions against the already-held,
exact **153190400-byte** candidate, SHA-256
`1ea24f0de4aa7d3e82c70a1b35f815791a48342db1a060100226b84dca7d7d01`.
This makes **12 selected checks per mode**, not 12 unchanged published methods.
No synthetic substitute, new kit, large transfer or repeated historical suite
was used. M5's 12 unchanged-method producer runs remain separately attributed.

Local environment: **macOS 26.0.1 / 25A362**, arm64, Apple clang **17.0.0
(clang-1700.3.19.1)**, SDK **26.0**, Python **3.9.6**, `-O2`, macOS 13.0 deployment
target. The sanitizer build adds ASan/UBSan. M5 used macOS 26.6.2/25G83,
clang21/SDK27.2. Local installed libcompression was exercised, but its concrete
shared-cache implementation was not separately qualified. No host install occurred.

Each mode reproduced the **77-control / 474-stream-trial** matrix and **two genuine
candidate encodings / 22 stream trials**, with zero proposal assertion failures.
The 1 MiB xorshift32 control produces two valid 1059159-byte Apple encodings:
strict framing passes, the original 64 KiB FINALIZE path errors on its first call
with **272727 input bytes remaining**, and the buffer proposal recovers the exact
bytes. All six tested output sizes show that expected error for both encoders
(**12 expected valid-stream failures**, not failed suite assertions). Five source
chunk sizes and the nonfinalized diagnostic comparison decode exactly; this does
not justify dropping finalization as a general admission strategy.

Both retained-candidate encodings decode exactly through the original **65536**
output path and through the proposal, which also matches the exact known size/SHA.
Their **65535** output traces reproduce two expected errors per mode. These are
generated own carriers. The historical selected Recovery carrier was not read,
and the specific cause of its 31AU failure remains **Unknown**.

Malformed/truncated/trailing/duplicate-EOS, declaration/frame/output-count, keybag,
gzip/DER, compressed/raw/file bounds, wrong-hash, CLI and path/alias controls pass.
The raw buffer API accepts the trailing-byte control; strict proposal framing
refuses it. Extra destination capacity detects saturation from forged output
counts. Decoder success alone never grants identity. Source review confirms the
inert default, held-descriptor confined fixture reads, frozen framing helpers,
exact known size/SHA and allocation-failure refusal. Temporary output can reach
**160 MiB plus one byte**, with additional library scratch; candidate output uses
153190401 bytes. Recovery memory behavior remains unqualified. Each run's 31
fresh temporary fixture files were deleted; finite matrix/build evidence remains
ignored and all previous receipts remain intact.

The CTRR record was reviewed as **attributed M5 static evidence**: 712 matched
words across five ranges trace a generic client request to BootPolicy. M1 did not
repeat REA/LLVM/cache extraction. Service-side SIP2 behavior and the actual
historical Recovery caller/library identity remain Unknown. A decoder repair
cannot satisfy the independently failed CTRR contract.

Next offline work: integrate the bounded proposal in a new reviewed component,
retain framing/extra-byte/exact-size-SHA and every existing policy/preservation/
rollback guard, and expose finite decoder subreasons. Qualify actual Recovery
codec/runtime and bounded synthetic positive/negative controls before any future
writer. Continue bounded offline research of the BootPolicy receiver rather than
repeat the unchanged install. No new boot package or restart is ready.

No server/proxy/staging, target controller, policy/installed-object/private-state
query, mount/writer, VM, device restart, or settings/security/firmware/volume
change was performed. **Native Linux/live target version/SMP/GPU/performance:
NOT RUN.** This review does not authorize a retry or another native experiment.

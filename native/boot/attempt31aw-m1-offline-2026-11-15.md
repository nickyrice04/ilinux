# M1 independent 31AW integration review — November 15, 2026

**OFFLINE INTEGRATION PASS; native remains on hold. No actionable source finding.**
Reviewed main `cc1a005` in the active checkout. All **14 new pins**, **10 prior AV
pins**, **190 frozen AU inputs** and **336 prior evidence/artifact/review/closed
receipts** verify unchanged. The accepted AV review keeps its exact 11 unchanged
methods plus retained-candidate equivalent accounting; that suite was not rerun.
The closed AU boot021 restoration and Macintosh HD desktop/default confirmations
stand, with their original evidence limits and no repeated policy query.

| Actual local run | Unchanged methods | Pass | Fail/error/skip | Unittest seconds |
| --- | ---: | ---: | --- | ---: |
| Normal | 52 | 52 | 0 / 0 / 0 | 35.794 |
| ASan/UBSan | 52 | 52 | 0 / 0 / 0 | 43.880 |

All genuine candidate/boot021 and optional legacy31AF inputs were already held;
no transfer, kit creation, test adapter or synthetic artifact substitution was
needed. Both actual builds' standalone **--codec-capability** commands report
positive_exact=true, negative_refused=true, passed=true, read_only=true,
host_queries=false and native_ready=false. Temporary fixture transactions and
the two freshly generated own carriers per mode were cleaned by the harness.
No old transaction or spent marker was reset, adopted or replayed.

Local runtime: macOS **26.0.1 / 25A362**, arm64; Python **3.9.6**, Apple clang
**17.0.0 (clang-1700.3.19.1)**, SDK **26.0**, `-O2`, macOS 13.0 deployment target.
Sanitizers add ASan/UBSan. Both builds match **all 11 generated source hashes**,
the exact candidate definition and state hash
`9181701efb1a7fc920b2804582d175c3ee9bafd2f758e9cbcf6044630c44d218` in M5 evidence.
The 143 retained qualified sources and 26 namespace-normalized safety bodies
match; removing the declared codec preflight restores the old transaction flow.
State/profile/parser and buffer-label transformations have exact reversals.
Local binaries differ under the older compiler; neither was staged or substituted
for any production helper. Installed libcompression was exercised without a
separate shared-cache implementation qualification.

Source and fixture review confirm the bounded decoder uses the same selected
read, strict complete framing/declarations and known size/SHA, with one extra
output byte to reject saturation/count mismatch. The former valid 1 MiB stream
counterexample now completes decoding while its unknown identity remains refused.
The genuine compressed candidate is recognized; its damaged carrier is refused.
An exact compressed candidate **still fails with disabled CTRR**.

Failed synthetic codec capability stops installation before target/mount/state/
writer work. A failed capability, missing candidate and unrecognized compressed
prior selection **do not prevent independently guarded raw boot021 restoration**.
Original/private/semantic/target/owner, one-shot durability, unknown CTRR and
mount-cleanup refusal controls pass. Finite failure reasons and result relations
pass. The parser extension accepts only canonical numeric **-1** for appropriate
no-writer results; malformed signed tokens and negative unsigned profile fields
still refuse. No production policy-reset writer was added.

Maximum decoded output remains **160 MiB plus one byte**, plus library scratch;
the candidate uses 153190401 output bytes. Synthetic capability alone does not
qualify Recovery peak memory, its actual codec library, firmware entry or the
historical carrier's cause.

M5's generic receiver evidence—**1226 words / ten ranges / three REA queries**—is
reviewed as attributed evidence. M1 checked range/count arithmetic, not original
kernel bytes, LLVM or REA. Its checked forwarding boundary ends at
**sep-endpoint,pnon**; matching Recovery/SEP identity and SIP2 policy semantics
remain unqualified. Public Aura/installer/exact-board summaries were reviewed as
M5's pinned-source findings; no per-unit DROM was copied or foreign code run.

The local generic Apple manual independently matches M5's SHA-256
`dacc771e3c49f0ec86feb582ba64e23b0e71c4ee49b1da647ec7f0f77d0a5a1b`.
It was read as data; bputil was not invoked. Its documented whole-policy
reconstruction is distinct from a CTRR-disable option. Whether that reconstruction
establishes enabled CTRR on this target remains a **Hypothesis**, not a tested
transition or an enable-only operation.

The proposed future policy phase correctly requires pre-reset Original private/
semantic/Full invariants, a closed lab-change/reissuance allowlist, and a fresh
post-transition lab baseline. **Rescue must work even if reset succeeds but the
first readback or new baseline admission fails.** Old AU restore cannot promise
that after lab metadata reissuance. Exact boot021 payload and declared lab
behavior restoration must be separated from recovery of old opaque policy bytes.
Implement and fault-test that state machine and its independent rescue before
another owner decision. Keep exact candidate, enabled CTRR and all Original
guards. AW neither implements nor authorizes policy reconstruction.

No restart, server/proxy, staging/kit/page, live controller, policy/selected-object/
private-state query, mount/writer, SEP call, VM or settings/security/OS/firmware/
volume/default change was performed. **Native Linux/live target version/SMP/GPU/
performance NOT RUN.** No new boot window is ready or authorized by this review.

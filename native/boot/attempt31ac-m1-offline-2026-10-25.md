# 31AC — independent M1 package, source and procedure review

**OFFLINE_PASS_NATIVE_HOLD, 2026-10-25 Eastern. Installation and native checks
NOT RUN; explicit approval for the new physical scope is still required.**
Pulled main cleanly with `git pull --ff-only` from `28ba410` through
`8c5b691210a1923d647412985c8bfa53a6c9feba`. Existing exact 31AB review was reused
by its two published report hashes; old suites and consumed experiments were not
repeated. [Reviewed metadata](attempt31ac-m1-offline-2026-10-25.json).

## Delivery verified against Git before extraction

The source manifest's **31 pins PASS**, exit 0 in 0.038 s; SHA-256:
`d1e017880ab416d2818e049f2a3391dfdc89097510b1453ee37ad8f8d7775476`.
The independently pulled artifact manifest SHA-256 is
`2d0978ddcc15a63a665917fe57d2fab3ed5784a2e92763dfcbd8e3595fcc5543`.

Downloaded only the published 31AC archive as data into a fresh ignored directory.
**249011 bytes**, SHA-256
`7cc585d69ebd023e2683b9842320b96ba30c9056e5082fa61aa18b74a0f60fdd`,
match Git **before extraction**. The repository verifier passed the real archive,
exit 0 in 0.077 s, with output byte-identical to the M5 delivery receipt. Independently
checked the exact seven-member namespace, all regular files, no duplicate,
absolute/traversal/link entries, then manually extracted only those files into
fresh private workspace storage with non-executable permissions. All six
manifest-listed files and the exact SHA256SUMS inventory match their tracked
sizes/digests. No downloaded binary or setup script was executed.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| ilinux-31ac.macho |180224|`261d44447442f32ba6c41bbf0f69179e8c9eb4c33507b60762f0ea8c2e54ab72`|
| m1n1-boot021.bin |3932160|`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`|

The spare rollback is byte-for-byte identical to the retained package's m1n1 image;
its boot021 marker and source metadata match pinned client
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`. This is file verification, not a live
M5 version query or reinstallation. The existing staged M5 rollback was not touched
or freshly verified remotely.

## Actual offline checks on M1

| Check | Actual result |
| --- | --- |
| Delivery verifier tests |3 methods PASS plus 6 namespace/content refusal subcases, exit 0 /0.076s|
| New packaging tests |8 methods PASS, exit 0 /0.077s|
| New visible-entry compile-only runner |5 AArch64 objects PASS, exit 0 /0.346s|
| Recovery guide shell blocks |6 blocks pass bash -n; no commands executed|
| Actual downloaded Mach-O data roundtrip |Byte-identical output from original source packager|

**11 unique Python methods.** Actual Python 3.13.5 and Apple clang 17.0.0
(clang-1700.3.19.1), on macOS 26.0.1 / build25A362. Delivery tests add `-B` only to
avoid bytecode caches. No source/test repair or repeat, tool install or skipped
executed-suite test. Compiler output status is **COMPILE_PASS_NOT_LINKED**.
All five objects independently have ELF64 little-endian AArch64 relocatable
headers; full object hashes are recorded in the JSON. The eleven source bindings
match published host and VM:
`e528ea024cf8fc987ca32e1e7c0dc7d8351e47735ef619868e505783be1cbd1b`.

Recovered the 147456-byte original payload from the downloaded Mach-O by restoring
only its known zero header canvas. Its SHA-256 equals the published linked/VM
payload `735fe28fb5148ff5c111ac0c9c1a3796957350325703c334ea9d2ca68a85ba96`.
The reviewed source packager reproduces the entire 180224-byte distributed image
exactly. This binds geometry and packaging of the actual artifact; it does not
independently reproduce linking, machine-instruction audit or firmware acceptance.

The M1 still lacks the existing ELF linker/QEMU toolchain needed for the full
link/audit and 26 runtime cases, so those are **NOT RUN on M1**. No shared VM was
started. Actual image-property inspection was not repeated; its M5 result is
reviewed separately. Existing 31AB observer/sanitizer evidence is reused rather
than counted again as new 31AC C tests.

## Independent source and evidence review

Read the new original C/assembly, image/audit/runners/tests, both 31AC research
notes, delivery metadata, final VM receipts and complete Recovery/rollback plan.
**No actionable blocker found within this offline review and bounded proposed
experiment.** Native acceptance and runtime display remain unknown.

The entry preserves full incoming state without argument/incoming-stack reads,
initializes its own record and uses owned stack/vectors before C. The bridge
accepts only its finite cold EL2 profile, without rewriting HCR/TCR/mappings to
force support. D128 capability is distinguished from an active format; optional
TCR2 access is feature-gated. Incoming producer state is never resumed, so low 64
PAR restoration is not advertised as preservation of an unknown 128-bit state.

Each external read interval is checked by AT at its first address and every 4 KiB
boundary before volatile copying. Only qualified Normal NC/WB sources are accepted.
Count 1..64 bounds the 24-byte record snapshot. Rechecking helper/count can detect
an observed change, but does not provide atomicity, authentication or stable
mapping/lifetime. Whole-record decoding is unnecessary for selected fields.
Payload/source physical pages are retained as protected pages with bounded refusal
rather than omitted on capacity overflow. The known protection extent excludes
appended metadata/link-edit pages; that limit remains explicit.

The frozen observer supplies geometry/interval validation. Every marker row then
passes write-translation, complete expected-PA, NC/WB-attribute and protected-page
checks before any pixel store. WB clean-line rounding/extent/alias checks and a
bounded unique line list precede painting. Volatile 32-bit stores, DSB and optional
DC CVAC remain actual runtime operations that can trap or leave partial output;
architectural AT success cannot rule out later Apple protections or unstable
mappings. No monitor call, secondary release, Linux launcher, page-table/control
write or display-controller configuration is present in the diagnostic.

Reviewed final M5 evidence separately: 26 complete payload cases = 8 paints,
16 no-paint refusals and 2 post-paint BRK/fatal captures, with actual profile and
complete framebuffer/cache-line checks. Coverage spans ordinary/VHE EL2,
4/16KiB pages,30/32-bit pixels and NC/WB paths; it is not a Cartesian-product proof.
Only vector slot4 is dynamically fault-tested. D128 optional paths and higher/
guarded exception routing are not execution-covered. Source-change harness repair,
previous 23/24-case receipts and initial read-only inspector setup failure remain
recorded. They are not hidden or added to the final 26 count. No private Apple/REA
or SDK measurement/source retrieval was reproduced on M1.

## Proposed operation and authorization boundary

31AC is a new resident-entry acceptance experiment. The prepared human sequence
is temporary lab Startup Disk selection (which may include a preparatory boot021
start), paired Recovery, exact candidate installation into the lab's custom-object
slot, one 30-second visual observation, exact raw boot021 rollback, return to
Macintosh HD and restoration of its default selection. These are separate from
the historical RAM/proxy authorizations. **No approval for that new scope has
been given in this handoff, and none of it was performed.**

Reviewed the new read-only guard and hash-bound frozen helper. It checks the
separate lab group, matching Data group, expected 25G83 build, rollback file,
Full/Permissive levels and lab-paired 1TR. It does not call the old Full/Full
`ilinux_preflight`. Candidate size/hash are checked separately. Syntax checks
parse, but never run, the six shell blocks. A later M5 check must establish its
actual state; this offline review cannot substitute a PASS for it.

The Mach-O configure command deliberately has no raw/entry override; rollback
uses the exact raw entry2048/lowestVA0 recipe. Rejection does not imply atomicity,
authorize changed options or an automatic retry. Rollback relies on the pre-existing
lab file, not an ephemeral Recovery download. Recovery is paired through the lab's
default selection; one-time desktop selection and restoring the default are
explicitly separate. LocalPolicy custom-object hashes can change even while the
original Full/lab Permissive levels are preserved; this is not a zero-policy-write
experiment. No new downgrade, volume creation, OS install or DFU action is proposed.

A visible 32x16 top-left marker proves reaching the store/display path only.
It cannot prove terminal cache/park completion, monitor readiness, Linux, SMP or
performance. A blank result stays ambiguous and must not produce an unchanged
second attempt or an Apple-only conclusion. Errors/rollback failures stop the
sequence; they do not authorize broader recovery or security changes.

## Preservation and publication

All **23 earlier manifests/5838 listed-file checks** pass unchanged. The manifests
cover 606 distinct files; adding the two already published M1 review files makes 608,
matching the upstream scope. An initial ad hoc M1 metadata assertion expected 607;
it stopped verification before publication. Corrected that count/scope assertion,
retained the note privately and changed no source, fixture or test. No test suite
was rerun for that bookkeeping correction.

All **539 prior intake evidence files** recursively hash unchanged, including
consumed receipts. Retained 13-file package and clean client pin are unchanged.
The archive, seven extracted members, logs and receipts remain ignored under
`build/native-intake/attempt31ac-offline/`; compiled objects remain under
`build/31ac-visible-m1-review/`. Compiler temp storage is empty and owned bounded
caffeinate has exited. Prior reports/source closures remain frozen.

**Lab installation, rollback installation, native entry/framebuffer, live version,
physical secondary, Linux/SMP/GPU/performance checks NOT RUN. Neither Mac restarted.**
No proxy/device open, target query, monitor call, server/transfer to M5, policy,
volume, installed-object or default-setting change. No outreach. Offline review
is ready for the user's concrete decision; it does not itself authorize a boot.

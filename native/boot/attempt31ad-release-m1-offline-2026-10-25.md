# 31AD release — independent M1 candidate review PASS; native hold

**Measured/reviewed, 2026-10-25 Eastern, commit
`150dc67f30b017369b6099d56ca9751ef4c19ca2`: OFFLINE_PASS_NATIVE_HOLD.**
The earlier [partial review](attempt31ad-m1-offline-2026-10-25.md) remains
unchanged. Its missing-suite finding is resolved by the corrected count, and
the real candidate/archive and separate M5 VM summary are now published.
This review verifies the delivered candidate without rerunning unchanged suites
or retrying the known incompatible M1 LLD link. No native operation occurred.

## New delivery and candidate evidence

All **37 current source pins PASS**. Compared with the initial 35-pin handoff,
31 old pinned files are byte-identical; only README, manifest, validation and
instructions changed, and the delivery verifier plus its tests were added.
The source-manifest SHA-256 is
`c0ffde5c41369dcf769b1209048ab8e0caa04fac0c067eeedd8ce350d3293e04`.

M1 downloaded the 251825-byte archive from the published release URL, checked
its size and SHA-256 against the pulled Git manifest **before extraction**, and
ran the new delivery verifier: **PASS, six manifest files plus exact checksum
inventory**. All seven members were verified regular files under the expected
namespace and extracted as non-executable data. Downloaded files were not run.

| Input | Bytes | SHA-256 |
|---|---:|---|
| Release archive | 251825 | `3f3eb70ea933d6e2aa3becb2aa08f721f5a8bbc48666bd496f0b18a7ebfcf61e` |
| Ordered candidate | 196608 | `406be900521795608073fa9f050f4e5f00b595793c95b0a155e510893cc16309` |
| Recovered original linked payload | 147456 | `6da621da67de37437300e7205e8c3919dcac997600f7eb6e8fedae29e6b0fc88` |
| Immutable boot021 rollback | 3932160 | `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664` |

M1 reconstructed the payload from the candidate by restoring its reserved zero
header page and retaining all subsequent payload bytes. Its digest equals the
Git-pinned M5 linked-payload digest. Running the independent validator with this
payload returns **STRUCTURAL_PROFILE_PASS**, payload comparison true. Both
headers have normal executable file offset **32768**, boot executable offset
**98304**, and checked difference **65536**. Repackaging that recovered payload
with the reviewed generator produces the downloaded candidate **byte for byte**.
The packaged rollback equals the retained boot042 package's boot021 exactly and
contains the expected boot021 marker. That is an offline byte check, not a live
target-version observation.

The standalone candidate, flat31AC control and boot021 control were separately
downloaded from their actual release URLs and verified against reviewed pins.
This binds the future Recovery-page URLs as well as the archive's members.

## Tests, reuse and VM evidence boundaries

**Three new delivery methods PASS**, including six namespace/content refusal
subcases. The previous 67 passing methods across four unchanged suites are
reused after confirming the unchanged implementation/test pins. Thus the
corrected five-suite coverage is **70 methods: 67 reused + 3 newly run**, not a
new full-suite run. The unrelated missing kconfig suite is no longer included.
The five earlier AArch64 compile-only objects and all eleven source bindings
are reused and reverified; binding digest remains
`ac5b7fcca628ff7fcec720dfcfefb537d0766ace161531cd47fed40c1ea8fcca`.

Actual new commands used `python3 -I`: `native/boot/attempt31ad/verify.py --archive`,
`native/boot/attempt31ad/test_verify.py`, and
`kernel/experiments/bootimage31ad/validate_ordered.py <candidate> --payload <recovered>`.
Python remains **3.13.5**; previous compiler environment was Apple clang
**17.0.0**, macOS **26.0.1 / 25A362**. No compiler/link or passed suite rerun.

The new M5 validation record reports the isolated GNU-ld two-base equality and
**26 QEMU cases PASS (8 paint, 16 refusal, 2 fatal-vector cases)** on the same
payload digest. M1 reviewed that published summary and unchanged harness/source
contract; it did **not** receive/reproduce the individual raw VM captures, rerun
QEMU, inspect a linked ELF or independently execute those 26 cases. M1's prior
LLD/script failure stays preserved. The delivery/parser result does not replace
an Apple installer or firmware test; the original exit-71 cause stays Unknown.

## Concrete Recovery tooling prepared, not executed

M1 generated pinned write and diagnosis profiles from the reviewed URLs and
rendered the install/rollback/diagnosis pages into a fresh ignored directory.
All three complete paste blocks pass **`bash -n`**, without execution:

| Phase | Bytes | SHA-256 |
|---|---:|---|
| Install | 6135 | `9676cfb413650048369a9be3e0134f2700d0ae864169108f2ff48c83ff15e308` |
| Rollback | 5872 | `349e31fc2bc8b1716aedf1aeabd6254a4b8f23e94aecc0acd79a7ba03e019ac2` |
| Read-only diagnosis | 3491 | `4c3f8998a0382827e81d76643c2f12d1f0d1dac55ae400a23c5ba423f1e721f3` |

Profiles/pages remain private; no HTTP server is running and no Recovery command
or clipboard smoke test ran. The source and earlier stub review still establish
the intended fresh guards, same-path hash checks, TTY input, output capture,
separate rollback and no automatic retry/reboot. They do not prove the M5's
clipboard retention or actual command acceptance.

**Nonblocking documentation finding:** section 1 of the current M1 instructions
still describes `PENDING_VM_LINK` and an unbuilt archive, despite section 2 and
the pinned manifest publishing them. Update that introductory historical text
in a future source-pin refresh; M1 used the concrete current pins and section 2.
No candidate-integrity or unchanged-tooling blocker was found.

## Preservation and remaining scope

M1 checked the 24 earlier frozen manifests unchanged plus the refreshed 31AD
manifest: **25 manifests / 5906 listed hash checks / 663 distinct files**.
All **622 prior ignored evidence files**, including consumed receipts, prior
partial review evidence and the failed-link outputs, remain byte-unchanged.
The previous public partial-review pair is also unchanged. Client remains clean
at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`; exact boot021 is preserved.
No source repairs, new tools, device/proxy/monitor operation, VM start, restart,
installed-object/security/volume/default change or outreach occurred.

This completes M1's released-candidate offline review for a concrete human
decision. It does **not** start or authorize a new physical sequence. Native
31AD installation, entry/marker observation, clipboard, rollback execution,
live target-version checks, Linux, SMP, GPU and performance remain **NOT RUN**.
Any later human-operated Recovery sequence must preserve Macintosh HD Full,
lab Permissive, exact rollback and original default restoration; no changed flags
or automatic retry follow from this review.

Machine-readable evidence: [release review receipt](attempt31ad-release-m1-offline-2026-10-25.json).

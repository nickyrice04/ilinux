# 31AD — independent M1 offline review; missing suite and native hold

**Measured, 2026-10-25 Eastern, commit
`f806f707e35562180ee83964e828dbd67b5dbcd5`: OFFLINE_PARTIAL_NATIVE_HOLD.**
All **35 source pins PASS**. The four available packaging/Recovery-renderer
suites pass **67 methods**, without skips or source repairs. The documented
eight-method kconfig command cannot run: its file is absent from this checkout
and Git's tracked files. Five freestanding AArch64 objects compile, with all
11 source bindings matching the published M5 compile-only record. No 31AD
candidate, release, Recovery action, clipboard test or native boot is qualified.

## Actual commands and results

| Command (from repository root) | Actual M1 outcome |
|---|---|
| `python3 -I kernel/experiments/bootimage31ad/test_ordered.py` | 32 methods PASS, exit 0, 0.434 s |
| `python3 -I kernel/experiments/bootimage31ad/test_image.py` | 23 methods PASS, exit 0, 0.075 s |
| `python3 -I tools/recovery31ad/test_render.py` | 5 methods PASS, exit 0, 3.326 s |
| `python3 -I tools/recovery31ad/test_write_render.py` | 7 methods PASS, exit 0, 8.546 s |
| `python3 -I kernel/experiments/omarchy-kconfig/test_kconfig_fragment.py` | Command exit 2: file missing; 8 advertised methods NOT RUN |
| `python3 -I kernel/experiments/visible31ad/run.py --output build/31ad-visible-m1-review --cc clang --target aarch64-none-elf --compile-only` | Exit 0; five ELF64 little-endian AArch64 relocatable objects, COMPILE_PASS_NOT_LINKED |

These are method executions across the four suites, not 75 passing methods or
eight skips. The missing suite is unrelated to the boot candidate, but the
published complete command list cannot currently be reproduced. The runner
retained the missing-file failure and then ran the independent compile command
once; no passed suite was rerun.

Tools: Python **3.13.5**, Apple clang **17.0.0 (clang-1700.3.19.1)**, macOS
**26.0.1 / 25A362**. Tests used workspace-local temporary storage and a bounded,
owned `caffeinate -i` assertion, now exited. Stub tests substitute private fixture
paths and fake configure/inspector tools; their exit-71/capture/postcheck results
are not Recovery or installer evidence. Neither generated production write block
was executed on a Mac target.

| Binding | SHA-256 |
|---|---|
| 35-file source manifest | `632bebcb607323235253ffee70915a333d3f32b79669fde5ff2396f6d217bb00` |
| Eleven compile source bindings | `ac5b7fcca628ff7fcec720dfcfefb537d0766ace161531cd47fed40c1ea8fcca` |
| Retained 31AC candidate used for read-only range check | `261d44447442f32ba6c41bbf0f69179e8c9eb4c33507b60762f0ea8c2e54ab72` |
| Exact retained boot021 | `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664` |

## Independent checks and qualifications

The seven reused visible31ac/observer31ab source files match their frozen pins;
the compiler's eleven-file binding matches the M5 record. The ordered synthetic
tests require each header's normal executable file offset to precede the boot
executable offset, reject both reversed flat root types and the old unordered
nested control, and compare the wrapper's preserved bytes to the supplied
synthetic payload. M1 additionally invoked the independent `range_check` API on
the actual retained hash-verified 31AC image: it refused specifically with
`split-protection executable file ordering would underflow`.

That is our finite parser's result, not Apple's Recovery result. The ordering
explanation for the original exit 71 remains **Hypothesis**, and the actual
installer cause **Unknown**. The full Recovery error and applicable profile
were never captured. Unchanged source files do not by themselves prove that a
newly relinked payload has byte-identical instructions or establishes acceptance.

The self-contained Recovery renderers were reviewed for fresh identity/pairing
guards, fixed rollback pins, resolved same-path size/hash binding, separate
install/rollback phases, `/dev/tty` input, combined output capture and immediate
`PIPESTATUS` handling. The available stub tests cover guard/transfer/hash/size
refusals, inspector rejection, configure exit 71, capture/postcheck failures,
and rollback in a fresh shell with no download or inherited variables. Future
production profiles must still be bound to an independently reviewed actual
candidate; syntactically valid fixture hashes are not production authorization.
Native browser clipboard retention remains **NOT RUN**.

## Link capability: present LLD, but this script did not link

Although no ELF linker was on PATH, the previously installed project-local
**LLD 23.1.3** exists and runs. Do not describe this M1 as having no ELF linker.
M1 attempted one additional offline build in fresh
`build/31ad-visible-m1-link-review`, selecting that existing `ld.lld` with the
unchanged runner and linker script. No source patch or alternate flags followed.

Compilation succeeded, then the canonical link exited **1**. LLD reported
`image.ld:9: unable to move location counter (0x4004) backward to 0x4000`
for `.late`, and a corresponding `.boot` counter error at line 14, with extent
assertions. Thus **canonical link attempted/FAILED; audit and slid link NOT RUN**.
This is a local linker/script compatibility result, not a demonstrated failure
of the intended GNU-ld VM build or the cause of 31AC's Recovery rejection.
The five compile-only objects remain a separate PASS. No linked payload or real
ordered image was produced here. QEMU is absent from PATH and the checked usual
installation locations, so all 26 execution cases remain **NOT RUN on M1**.

## Actionable handoff and preservation

1. **Publish the missing kconfig test or correct/qualify the advertised 75-method
   handoff.** Its documented pathname does not exist and is not among the pins.
   The M1 result is 67 PASS plus 8 NOT RUN, not complete reproduction.
2. **Complete and publish the intended GNU-link/26-case VM evidence and real
   candidate pin.** Record the LLD incompatibility rather than an absent-linker
   assumption. Candidate/archive hashes and URLs remain null in the frozen
   manifest; production candidate verification/install pages are not ready.

All **25 frozen manifests / 5904 listed hash checks / 661 distinct files** and
**570 prior ignored evidence files** verify unchanged, including consumed
receipts and the 31AC offline/recovery-result evidence. The clean client stays at
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`; all 13 retained package checksum
entries pass (14 regular files including the checksum inventory). One M1
preservation-count assertion initially counted 13 physical files instead of
13 entries plus the inventory; it was corrected before publication, with the
failure retained privately and no source change or suite rerun.

No download, new tool installation, VM start, physical device open, proxy request,
monitor call, Mac restart, installed-object write, security/volume/default change
or outreach occurred. The prior Macintosh HD return/default confirmation remains
the last human observation, not a fresh policy query. 31AD native installation,
entry/marker/live version/Linux/SMP/GPU/performance remain **NOT RUN**. Publish
the real candidate and complete review before proposing a concrete physical
sequence; this partial review does not authorize one.

Machine-readable evidence: [review receipt](attempt31ad-m1-offline-2026-10-25.json).
Raw outputs, object files and failed-link logs stay ignored.

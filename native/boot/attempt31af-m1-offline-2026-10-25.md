# 31AF — M1 independent offline review, 2026-10-25

**OFFLINE REVIEW PASS, with one nonblocking source-inventory completeness note.**
No blocker found for this exact candidate. Native installation, entry/marker,
rollback, live checks, Linux, SMP, GPU and performance remain **NOT RUN**.

Reviewed main `983cb842d938f7e8a0baaea0e8f591867d1d789d`, published source
`8d798ff`. The human requested pulling main and offline testing before native
restart. No source, settings, boot object or volume was changed by this review.
The consumed 31AE result is preserved; it is not reused as a new experiment.

## Delivery and exact candidate

All **34 primary Git source pins PASS**, inventory SHA-256
`c097def4b1a0497adf8ea3a31c1a8c6c8781a7d35f4ae039da524a51129decf0`.
Both exact GitHub release URLs were independently downloaded and size/hash
verified against Git before archive inspection/extraction:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Archive | 254936 | `52412ecf4a52cabd3cab23969ba3941572d691bd16efa7e6ff657c3746738eda` |
| Candidate | 442368 | `166bea74bf515473057dfd29dc89127d04768945a451e497cc80a9fc53d4951b` |
| Recovered payload | 393216 | `91d2ce73f79784b78c96e08c606d3622aa3246a7561fdbec4d1066ebe9bfaa7c` |
| Exact boot021 rollback | 3932160 | `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664` |

The repository verifier PASS: nine regular members plus exact checksum inventory,
with unsafe/link/duplicate/extra members refused. Members were read as data only.
The standalone and archived candidates are identical. Recovered payload is one
zero 16-KiB header page plus candidate bytes 0x8000..0x64000; its digest matches the
published GNU-link/QEMU payload. Independent strict validator returns
`STRUCTURAL_PROFILE_PASS` with both headers, both finite arithmetic profiles,
complete nonoverlapping extents and payload/metadata binding. The complete
source-packager roundtrip is byte-identical to the downloaded candidate.
Rollback equals the retained boot021 bytes and expected marker.

## Fresh local checks

All commands used `python3 -I`; fixture/compiler temporary files stayed under
ignored `build/`. **47 methods PASS; zero failures, errors or skips:**

| Suite | Methods |
| --- | ---: |
| `kernel/experiments/bootimage31af/test_image.py` | 21 |
| `kernel/experiments/bootimage31af/test_rejected31ae.py`, retained exact 31AE control | 5 |
| `tools/recovery31af/test_write_render.py` | 7 |
| `tools/recovery31af/test_prepare.py` | 11 |
| `native/boot/attempt31af/test_verify.py` | 3 |

The separate `immutable31af-test/run.py --self-test` PASS checks read-only 4/16-KiB
image/reservation mappings, populated reserved-state fixtures, alias geometry
and the centered 8192-pixel/32768-byte footprint. It runs no compiler or emulator.
The 40 new-image fixture cases it describes were not executed locally.

One fresh host compile-only invocation PASS:

```sh
python3 -I kernel/experiments/immutable31af/run.py --output build/native-intake/attempt31af-m1-offline/host-compile --cc clang --target aarch64-none-elf --compile-only
```

This produces one ELF relocatable object; it is not linked or executed. No
known-incompatible LLD invocation, compiler installation or VM start occurred.
The complete six-file source-binding digest equals the M5 published build
binding (`874ac4cd…ce1de4`). The local compiler differs from M5's; raw object
byte equality is not claimed. The locally recovered payload equals the GNU-link
payload digest regardless of the separate compile-only check.

Actual candidate/phase preparation commands:

```sh
python3 -I native/boot/attempt31af/verify.py --archive build/native-intake/attempt31af-m1-offline/ilinux-31af-entry-test.tar.gz
python3 -I kernel/experiments/bootimage31af/validate.py build/native-intake/attempt31af-m1-offline/ilinux-31af-immutable.macho --payload build/native-intake/attempt31af-m1-offline/recovered-payload.bin
python3 -I kernel/experiments/bootimage31af/image.py --payload build/native-intake/attempt31af-m1-offline/recovered-payload.bin --output build/native-intake/attempt31af-m1-offline/roundtrip
python3 -I tools/recovery31af/prepare.py --output build/native-intake/attempt31af-m1-offline/reviewed-pages
```

## Artifact/code review and evidence boundaries

The new assembly uses no SP, C, observer record, image-store instruction, monitor
service or physical secondary start. Entry/vectors/helpers stay in boot code.
The framebuffer range, source aliases, supplied table, translations, attributes
and rounded cache intervals are checked before pixel stores; unsupported cases
park. AT operations may still have architectural access-state effects under
incoming controls, as the implementation notes. This is not a universal
side-effect or formal address-validation proof.

M1 repeated the finite instruction-class walk over the **actual recovered
payload**, using the Git-pinned layout symbols. All 2052 boot-code bytes, including
vectors, are covered; every remaining boot word is zero. Counts match the pinned
layout: 267 ALU, 147 branches, 36 system, 20 loads, 7 returns, 3 addresses and **one pixel-store
instruction**. This confirms emitted operation classes; it is not a locally
rerun linked-ELF section/symbol audit or a proof of control/data-flow correctness.
The reservation is zero on disk; software never treats it as observer-owned RAM.

**Reviewed separate M5 evidence, not rerun:** isolated GNU two-base link, linked
ELF audit, 41 complete QEMU cases (14 paints, 26 refusals and the exact 31AE first
record-store permission-fault control), actual read-only Apple 14-property
result, and public/proprietary provenance summaries. No raw QEMU/ELF/Apple
captures were independently reproduced on M1 and no proprietary artifact or
decompiler output was opened. Standard QEMU does not establish Apple firmware
handoff, native panel scanout, monitor service readiness or physical CPU startup.
The old first-store fault is synthetic, not a diagnosis of the 31AE logo result.

**Nonblocking inventory note:** `kernel/experiments/immutable31af/layout.h` is
included by the assembly but absent from the 34-entry primary inventory. Its
current SHA-256 is
`3da9aba03614899241641fd80cf2c52067491de9c011f4aead66903babb2404b`.
M1 independently verified the header through the complete six-file build-binding
digest equal to M5's published GNU build, and every parsed constant equals the
Git-pinned layout. This supplemental pin closes the exact current review; the
frozen inventory was not silently rewritten. A future standalone source-closure
check should include the header. No current candidate-integrity mismatch found.

## Recovery pages and preservation

Regenerated HTML and both complete phases equal the archived versions. Both
production blocks pass `bash -n`. Install SHA:
`5dc9aa45f5469604155b750597772c414ca87b10157d18acc7d001df3f225b68`;
rollback SHA:
`7e363bf5cd4db770fb58635de213d7d79bfd06c7d94384a3685345454cfbe195`.
The base guard remains unchanged from the prior reviewed renderer. Candidate
geometry/pin/name change; the separate clipboard smoke phase is removed.

Each phase has a fresh lab identity/pairing/build/helper/boot021 and original
Full/lab Permissive guard. Install hashes the same readonly candidate pathname
immediately before one Mach-O configure; no raw candidate fallback. Independent
rollback uses exact staged boot021, raw entry 2048, lowest VA 0. TTY prompts,
separate configure/capture exits and policy-postcheck success gating remain.
No block was executed and no page server was started.

All **26 prior source inventories remain frozen**. Including 31AF, 27 manifests
verify: 5978 listed hash checks/722 distinct files. **732 prior ignored evidence
files and consumed receipts unchanged**. Client stays clean at
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`. No old receipt reset or re-arm.
New receipts/logs/prepared pages remain in ignored
`build/native-intake/attempt31af-m1-offline/`; no binaries, media or identifiers
are published. No production/test source was changed.

## Ready sequence

Offline review is complete for this exact candidate with the inventory note
qualified above. Keep both Macs in their existing state until the human starts
the native sequence. No restart, USB/proxy, native launcher, settings/default,
security/volume change or additional native attempt occurred in this handoff.

The next physical sequence is one guarded lab install; only after install and
postcheck success, **one timed 30-second observation for a centered 128x64 black/
white checkerboard**, then exact boot021 rollback and Macintosh HD/default
restoration. At 30 seconds power off even if only the Apple logo remains. No
clipboard smoke, repeated inspector matrix, unchanged retry or new security
reduction. A missing marker stays inconclusive; Linux/live version/monitor calls/
SMP/GPU/performance remain **NOT RUN**.

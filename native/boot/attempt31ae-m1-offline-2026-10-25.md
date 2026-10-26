# 31AE — M1 independent offline review, 2026-10-25

**OFFLINE REVIEW PASS. Native installation, entry and live checks NOT RUN.**
Reviewed main `f0847058eb6dff53e9f6543ebec07d83d3b50be4` (published source
`aa1747b`). No production or test source changed. The consumed 31AD session and
all its failure/rollback evidence remain intact.

## Actual delivery and source checks

All **38 Git source pins PASS**, inventory SHA-256
`aa27825f5082b1a5196b154e297002c62eee3677572062383b3b9d08b8a0229c`.
Both exact release URLs were independently downloaded; size/SHA verified against
Git before archive member inspection or extraction:

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| Archive | 256353 | `6b0c0ae6fdce31b69c72861c27297f0cb4d8873c586448fced41ed4e02910fa1` |
| Candidate | 196608 | `ccdc9c8c8ef78fda2d9e2a56550919d0c20030037486215d194e8762a85748aa` |
| Recovered payload | 147456 | `35bcecdff17ca1b927fccdffd057c9f149577df5698f250b7dbe93f5c71fe13b` |
| Exact boot021 rollback | 3932160 | `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664` |

The repository archive verifier PASS: nine pinned regular members plus exact
checksum inventory; no extra, duplicate or linked member. Extracted bytes were
read as data only. Standalone candidate equals the archived candidate. Rollback
equals the previously retained boot021 bytes and contains the expected marker.
Reconstructed payload is one zero header page followed by candidate bytes
`0x8000..0x28000`; it matches the M5 GNU-link/QEMU payload pin. New independent
validator returns `STRUCTURAL_PROFILE_PASS`; source-packager roundtrip equals
the entire delivered image.

## Fresh M1 tests

Every command used `python3 -I`; temporary fixtures remained under ignored
`build/`. **77 methods PASS, zero failures/errors/skips:**

| Suite | Methods |
| --- | ---: |
| `kernel/experiments/bootimage31ae/test_ordered.py` | 51 |
| `tools/recovery31ae/test_write_render.py` | 7 |
| `tools/recovery31ae/test_prepare.py` | 11 |
| `native/boot/attempt31ae/test_verify.py` | 3 |
| `kernel/experiments/bootimage31ae/test_rejected31ad.py` with retained exact released control | 5 |

The last suite verifies the old candidate's complete SHA before using it. It
confirms the frozen old validator accepts the rejected 31AD image, while the new
complete/range guards reject its data-to-text underflow; both headers and both
arithmetic profiles are covered. Synthetic mutations cover file/VA ordering,
complete extents, uint64 overflow, metadata placement and payload binding.
Renderer fixture tests substitute private stubs; no real Recovery tool ran.

Actual candidate validation and packaging commands:

```sh
python3 -I native/boot/attempt31ae/verify.py --archive build/native-intake/attempt31ae-m1-offline/ilinux-31ae-entry-test.tar.gz
python3 -I kernel/experiments/bootimage31ae/validate_ordered.py build/native-intake/attempt31ae-m1-offline/ilinux-31ae-ordered.macho --payload build/native-intake/attempt31ae-m1-offline/recovered-payload.bin
python3 -I kernel/experiments/bootimage31ae/ordered.py --payload build/native-intake/attempt31ae-m1-offline/recovered-payload.bin --output build/native-intake/attempt31ae-m1-offline/roundtrip
python3 -I tools/recovery31ae/prepare.py --output build/native-intake/attempt31ae-m1-offline/reviewed-pages
```

## Independent fix and source-reuse review

**Confirmed:** both headers now place DATA at 32768, normal executable at 81920,
boot executable at 98304, metadata at 163840 and linkedit at 180224. The actual
31AD failing subtraction is replaced by `81920 - 32768 = 49152`. The finite
parser checks adjacent complete extents in both file and virtual space, both
arithmetic profiles and intrinsic recovered-payload metadata binding. This is
our format model, not Apple's complete acceptance contract.

Seven original 31AC/31AB source files and the compile driver are byte-identical
to the previous M1 review. The exact five prior compile-only objects and their
recorded digests were verified and reused; no new compile or known-incompatible
host LLD invocation was needed. New linker/audit/packager code was reviewed.

Comparing the old and new actual payloads finds exactly three changed boot
instruction words (`0x14010`, `0x14068`, `0x15004`). Independent ADR decoding
confirms the two record references move from payload offset 0x8000 to 0x4000 and
the stack-top reference from 0x14000 to 0x10000, as the original source predicts.
All other boot bytes are identical; the normal self-branch moves with relinking.

**Reviewed M5 evidence only:** published two-base GNU-link equality, 26 full QEMU
cases, exact-old desktop inspector PROPERTY_ERROR despite exit 0, new complete
14-field derivation, and bounded REA/1127-word audit. The delivered payload
matches that evidence's digest. M1 did not inspect the raw linked ELF, raw QEMU
captures or proprietary artifacts, rerun QEMU/REA/Apple inspector, or emulate
firmware. Those separate results are not claimed as fresh M1 measurements.
The Recovery executable's equality and native acceptance remain **Unknown**.

## Recovery blocks and preservation

Source-verified page preparation PASS. Regenerated HTML and both independent
paste blocks equal the archived versions byte-for-byte. `bash -n` on each full
production block exits 0. Install SHA
`0bc65c87184e9071a4d031b4817bbd671f99fda1d8b96171964fef062d6d5c8a`;
rollback SHA
`7b09569a39417c45f2dbb08787efaa0145744b059ccbfec4064efb8ee56f755e`.

The base guard is unchanged from reviewed 31AD: exact helper/boot021, lab System
and Data identity, separate original, build 25G83, paired Recovery and original
Full/lab Permissive. Install checks the same candidate pathname immediately
before one Mach-O configure, without raw flags. Rollback is independent and
uses only exact staged boot021/raw entry 2048/lowest VA 0. Both preserve separate
configure/capture exits and require the policy postcheck before success. The
page adds the username-before-password clarification; no TTY/pipe fix is claimed.
Neither production block was executed and no server was started.

All **25 previous source manifests remain frozen**; with new 31AE,26 manifests,
5944 listed hash checks/691 distinct files PASS. **675 prior ignored evidence
files and consumed receipts are byte-unchanged.** Client remains clean at
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`. No reset/re-arm of receipts.
Private logs, download receipts and prepared pages remain under ignored
`build/native-intake/attempt31ae-m1-offline/`; no binaries/media/credentials or
hardware identifiers are published.

## Next gate

No offline package/review blocker found. Native 31AE install, entry/marker,
rollback execution, live target version, monitor calls, Linux, SMP, GPU and
performance remain **NOT RUN**. No restart, USB/proxy connection, VM start,
settings/default/volume/security change or physical test occurred.

A fresh human decision on the exact candidate and full install/one 30-second
observation/exact rollback/Macintosh HD default-restoration sequence is required.
Only an installation success permits the marker observation. Any nonzero
candidate result stops without retry, changed flags or diagnostic boot. Offline
PASS does not authorize or predict firmware acceptance.

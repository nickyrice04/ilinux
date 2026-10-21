# Attempt 31C — independent M1 offline readiness

**OFFLINE READY, 2026-10-21. Native 31C, hardware writes and CPU1 entry NOT RUN.**

M1 pulled M5 handoff **`61bbe52`** with `git pull --ff-only`, preserving the
completed 31B evidence. The human reports this Mac ready and M5 at Running
proxy. This is the corrected continuation **31C**, with separate confirmation
and receipts; it does not rerun consumed 31B. Publishing readiness precedes
the fresh human start required by the new checklist.

## Verified inputs

* All **46** entries in `attempt31c/source-sha256.txt` match. Reviewed the new
  controller, supervisor, synthetic fixture/tests, M5 review and VM validation;
  the shared 31B controller and 192-byte helper remain byte-identical.
  Source-manifest SHA-256:
  `b4021e4669e42732e4f1130f5a997451ecfdcbf94326a6bdd4bd63620cafe208`.
* Boot042's **13** retained files passed package verification, status
  `checksums_and_declared_revision_verified`. Manifest SHA-256:
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
  Existing boot021 image: **3,932,160 bytes**,
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
* Clean client remains pinned to
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* Controller SHA-256:
  `8b69e15e248b596ad1f51b7b013c2a0e72d8096d65afe8815166998e45fca567`.
  Supervisor:
  `0ca31f902c2ceb2d5bc94bd075a6d74a575fcee2060ddf0d10ec358574240f49`.
  Original helper:
  `dc046b303191b9a4fcb26a9e689fa4ec7b936dd1ae67dc5fd9b81c4edf4bf8aa`.
* Default controller output matched exactly:
  `OFFLINE PASS: 31C source/image/helper verified; no USB, allocation or CPU start`.
  No target connection, new download, VM run, host install or ARM64 helper
  execution on the M1 occurred.

## Tests and evidence protection

| M1 suite | Methods PASS | Skips |
|---|---:|---:|
| New RAM-bound/controller tests | 11 | 0 |
| Frozen 31B controller | 19 | 0 |
| 31B supervisor | 3 | 0 |
| New 31C supervisor | 3 | 0 |
| Census regression | 11 | 0 |
| Static layout audit | 5 | 0 |
| Renderer regression | 8 | 0 |

**60 methods PASS; all nine requested subprocesses exit 0.** No skips,
failures, source repairs or guessed pins. Host RAM tests use a parser model;
M5's separate job 060 real BootArgs/ADT/high-address client evidence was read
as VM evidence, not independently rerun or relabeled native. Supervisor tests
launched and terminated only their own dummy children. Test temporary files
and logs remain under ignored build; a bounded caffeine assertion is owned.

All five 31C live-use files were absent before and after testing:
`supervisor-once.json`, `consumed.jsonl`, `controller.json`, `controller.stderr`
and `supervisor-result.json`. Prior 31B evidence digests stayed unchanged; no
receipt was deleted or reset. No competing reader/proxy/controller was found.
No real attempt or window has been reserved: **live attempts = 0**.

## Correction and authorized boundary

M5's review identifies the old physical-address ceiling as incompatible with
this machine's observed DRAM aperture. 31C requires consistent supported
BootArgs, a nonempty usable interval within the exact machine aperture and
matching target ADT DRAM properties. It preserves firmware exclusions and
the inherited image/helper containment checks. Native rejected bounds were
not retained in 31B, so that run's exact numeric fields remain unknown.
This verifies the correction offline; native acceptance is still untested.

The unchanged CPU1 sequence allocates 16 KiB, uploads the original helper,
sets WFE before any alive secondary, prepares the existing dedicated stack,
and attempts exactly two CPU1 start writes followed by two bounded timer
requests. It is write-capable and initializes architectural state. No new
installed image, chainload, reset-vector/installed-code patch, frequency
operation, other core or Linux continuation is included.

Next: fresh human 31C start and restart/reseat/power/unlocked/open-lid readiness,
then the fixed supervisor once with a human **90 s** timer. Controller **60 s**,
independent supervisor **65 s** plus bounded child termination, serial **2 s**,
arrival **3 s** and each request **1 s** bounds remain. Immediately on any
outcome or time limit, power off and return to Macintosh HD. Preserve receipts;
no rollback, reconnect, automatic retry or target cleanup.

Existing boot021/client pin, macOS, security/default/volume settings unchanged.
Routine policy rechecks remain waived; original Full/lab Permissive/Macintosh HD
default are last reported, not freshly verified. **Native 31C, CPU1 entry,
Linux/native SMP, renderer, performance and energy tests NOT RUN.** A future
bootloader PASS alone would not establish Linux SMP, timer IRQ/IPI/coherence,
sustained stability or performance parity. Old copy31 and full-image SMP
candidate remain held. Instructions: `tools/m1n1-client/attempt31c-instructions.md`.

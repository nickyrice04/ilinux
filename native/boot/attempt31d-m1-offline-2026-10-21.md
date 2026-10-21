# Attempt 31D — independent M1 offline readiness

**OFFLINE READY, 2026-10-21. Native 31D, hardware writes and CPU1 starts NOT RUN.**

M1 pulled **`c331796`** with `git pull --ff-only`; the worktree was clean.
The human reports both computers ready and asks to run the new test. Publishing
this intake precedes the fresh human start required by the 31D checklist.
Consumed 31A/31B/31C are not replayed; their existing evidence is retained.

## Verification

* All **60** entries in `attempt31d/source-sha256.txt` match. Source-manifest
  SHA-256: `e41c9a29748007b08e06e077e45d63deb494eb0b3ec75e0142dc4aeb9f4e3ba5`.
  Reviewed the controller/supervisor, tests, image audit, binding, review and
  published REA behavioral findings/validation. No proprietary bytes or
  rejected pseudocode were used as implementation.
* Boot042's **13** retained files verify, status
  `checksums_and_declared_revision_verified`; package-manifest SHA-256
  `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`.
  Existing 3,932,160-byte boot021 image:
  `ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
  Clean client remains `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* New controller SHA-256:
  `1a37cd8e4e86dfd962240674a1714a4be0c2ac387efeead7efe459d5281ccc1c`;
  supervisor `ed2d4b2d0d794959fd75b6ed8e98285988917b916629038968177b2365b1e715`.
  Shared 31B/31C controllers and original 192-byte helper remain unchanged.
* Default controller output matches exactly:
  `OFFLINE PASS: 31D source/image/helper verified; no USB, allocation or CPU start`.
* **73 Python methods PASS**: 10 new controller, 11 previous RAM/controller,
  19 frozen controller, three supervisor suites of 3 each, 11 census,
  5 layout audit and 8 renderer. All **11 requested subprocesses exit 0**;
  zero skips, failures, repairs or guessed pins.
* An additional independent run of the original console image/source parser
  passes and its JSON is exactly equal to Git's `console-binding.json`.
  It reads the pinned public image/source without executing target code.
* All five 31D live-use files are absent before/after offline checks:
  `supervisor-once.json`, `consumed.jsonl`, `controller.json`, `controller.stderr`
  and `supervisor-result.json`. Prior 31B/31C live evidence digests are
  unchanged. No receipt was removed or reset; no competing proxy/reader found.

The host RAM tests use the reviewed parser model. M5's job 061 real pinned
client/BootArgs/ADT paths, nine actual-source UART harness cases in normal and
sanitized builds, and REA/LLVM cross-checks were read as separate offline
evidence, not rerun or represented as native. Supervisor tests terminate only
their own dummy children. Logs and test temporary data stay under ignored
build; a bounded caffeine assertion is owned. No USB was opened, no new image
downloaded, no VM launched and no ARM64 helper executed on M1.

## Next boundary

31D checks direct USB and expected diagnostic-UART RAM bases, then uses the
existing helper/CPU1 setup, zeros and cache-publishes the two RAM variables
before the same two CPU1 start writes, and records partial reset/spin stages.
The console hypothesis remains unproven; muting those outputs reduces fallback
diagnostics until power-off. USB/framebuffer settings are unchanged. No UART
MMIO probe/flush, installed-code/reset-vector patch or new power operation.
This is a write-capable native experiment, not a read-only diagnostic.

Await fresh human 31D start and restart/reseat/power/unlocked/open-lid/proxy/
90 s timer confirmation. One fixed supervisor run: controller 60 s, independent
parent 65 s plus bounded termination, serial 2 s, arrival 3 s, requests 1 s
each. Immediately on any result/deadline, power off and return to Macintosh HD.
No retry, reconnect, rollback, generic CPU stop or automatic Linux continuation.

Existing boot021/client, macOS, security/default/volume settings and firmware
are unchanged; routine policy rechecks remain waived. Original Full/lab
Permissive/Macintosh HD default remain last reported, not newly verified.
**Live attempts 0; native 31D, CPU1 entry, Linux/native SMP, renderer performance
and energy tests NOT RUN.** Any future bootloader PASS is not Linux SMP,
timer IRQ/IPI/coherence, sustained stability or performance parity. Old copy31
and full-image SMP candidate remain held. Procedure:
`tools/m1n1-client/attempt31d-instructions.md`.

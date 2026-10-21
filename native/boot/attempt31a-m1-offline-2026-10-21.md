# Attempt31A — M1 offline census readiness

**OFFLINE READY, 2026-10-21. Native/live/CPU starts/Linux NOT RUN.**

M1 pulled **`964aaac`** and independently verified all 31 SMP source pins,
boot042's 13 files/declared boot021 revision and clean client `57a9339`.
Boot021 image SHA-256 `ff75f4a9…72664`; census offline PASS, no USB opened.
**19 methods PASS** (11 census, 8 renderer), no skips/fixes. Native31A/live,
CPU starts, SMP, Linux and renderer tests **NOT RUN**; live attempts/MMIO reads 0.
Human has already reported M1 restart and M5 Running proxy and confirmed direct
cable/power/unlocked/lid/90s timer. Publish before executing the authorized one
census. No new image, startup candidate, CPU start, chainload or write operation.
Old copy31 remains HOLD; 31B requires separate review. Routine policy rechecks
waived; macOS/boot/security/default/volumes unchanged. Evidence:
`native/boot/attempt31a-m1-offline-2026-10-21.md`.

The source-pinned checklist, census implementation/tests, exact boot021 symbol
record and separate offline startup/renderer validation were read. New source
commit is 964aaac; only original read-only census source executes on this host.
No `m1n1-OFFLINE.bin`, startup function, renderer trial, old pair or Linux launcher
is rebuilt, executed, transferred or deployed by this intake.

| Check | M1 result |
|---|---|
|31 entries in `attempt31/smp-source-sha256.txt` |All digests equal Git |
|Boot042 SHA256SUMS |`60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`, 13 files PASS |
|Existing boot021 image, 3,932,160 bytes |`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664` |
|Clean client |`57a9339ffd1876e78297b17d34dece8cff8fa1ba` |
|Offline census |`OFFLINE PASS: boot021 verified; no USB opened; no CPU start` |
|Census unit tests |11 PASS |
|Renderer unit tests |8 PASS |

All four subprocesses exit 0; no failures, skips or source changes. Tests use
synthetic interfaces and prove refusals/read-count behavior, not actual native
reset targets. M5's 14 normal/14 sanitizer actual-function cases, real ADT parser
VM checks, 2,000-round two-CPU VM smoke, renderer timing and 53 verified REA
instruction words were read as separate evidence, not rerun or relabeled native.
Private receipts stay ignored under build/native-intake/attempt31a. A bounded
`caffeinate -i` assertion is owned only for this session.

One human-started census follows published readiness and the current explicit
start authorization. Start a visible 90-second human timer immediately before
the sole live command; tool 60s overall/5s serial-read bounds stay unchanged.
Chip/board/18 topology records, immutable startup/SMP text, boot-CPU/no-secondary
and installed RAM-state gates precede two guarded CPU0/CPU1 RVBAR reads. ADT
parsing stays transient, diagnostics suppressed. Only sanitized lock bits,
relative target class/offset and CPU IDs may be published after schema review.
The existing proxy diagnostic exception counter is read/cleared; no hardware
register, reset vector, code, CPU-start, security or policy write is authorized.

A success means `CENSUS_COMPLETE_REVIEW_REQUIRED`, two rows, mmio_reads=2 and
cpu_starts=0. It proves mirror values only, not actual reset execution. A fault
or refusal ends the session without retry/reconnect/gate edits. After either
outcome, human powers off and selects Macintosh HD; no proxy shutdown/CPU-stop
command. No Linux, CPU start, native renderer, 31B deployment or performance/
energy test is authorized by a census result. Keep original macOS/default/
Full and lab Permissive last reported; routine policy checks remain waived.

# 31L offline entry-contract analysis

2026-10-22. This is an original, dependency-free software checker for the
consumed 31K experiment. It does not prepare or authorize a native 31L attempt.
It sends no target commands, generates no boot image and changes no frozen
controller, firmware, macOS or boot setting.

## What the additional checks resolve

The earlier vector oracle starts at image offset zero; the cold oracle starts
inside its stub. Neither establishes CPU1's real entry or incoming memory
state. Their relative addressing had not been systematically checked over
high physical addresses and all m1n1 RAM aliases.

This checker binds the complete boot021 image and optional complete symbol
table. It independently decodes the first five words of each original
published recorder, through the first store and its barrier. It checks the
published branch destination and inventories the original sixteen vector
slots. It then evaluates seven synthetic bases spanning address carries at
4 GiB, 1 TiB and near the 41-bit limit, across four conventional aliases.
All bases obey the live controller's 16 KiB alignment gate; ADRP itself uses
4 KiB pages independently of translation granule.

**Confirmed offline:** both prefixes compute the intended record address in
all 56 address cases, without truncating high bits. Neither has a stack access
or system-register read before its first marker store. Their arithmetic keeps
the execution alias: it does not magically translate a virtual address to a
physical address. Another 112 cases distinguish an explicitly supplied alias
mapping from MMU-off identity, with 42 nonidentity/MMU-off cases reaching a
different physical address. These are arithmetic checks, not measured CPU1
mapping, permission, cache or instruction-fetch behavior.

The vector hook covers the first word of slot zero, not every exception slot.
The other fifteen original slots reach their own handlers. A vector marker
therefore does not by itself establish reset provenance, and a missing marker
does not exclude an earlier exception through another slot. There is no
evidence here to patch those other slots, change VBAR or redirect CPU1.

## What the observed negative pair cannot resolve

The checker accepts the actual sanitized 31K report only when the CPU0 control
passed, both channels have an explicit phase zero with uncommitted identity
and no channel error, and arrival/park remain unverified. Missing or malformed
fields are refused instead of being interpreted as zeros.

It evaluates explicit hypothetical premises for entry selection, instruction
fetch/publication, record mapping, store permission and publication. Eight
different premise combinations still yield zero while agreeing with the CPU0
positive control. Some execute no marker store; others execute one whose value
is not observable. The hardware result does not select among these causes.
Nor does phase zero say that every raw record word was zero.

One case injects a CPU1 Normal-cacheable, private-dirty first store while the
CPU0 observer reads Device memory. Its DSB is deliberately **not** treated as
a cache clean. This is an unresolved visibility hypothesis; the model does not
declare mixed memory attributes architecturally compatible or predict their
real behavior. A hypothetical clean comparison changes the result only after
separately assuming that maintenance is permitted, completes to the relevant
PoC and that the observer reaches that PoC. Adding a clean instruction alone
does not prove any of those conditions, recover a missing fetch or repair a
store fault. No native code change follows from this comparison alone.

Arm distinguishes data-cache maintenance, completion barriers, instruction-
cache invalidation and execution synchronization. CPU0's ISB does not itself
synchronize CPU1's pipeline. [Arm: cache maintenance](https://developer.arm.com/community/arm-community-blogs/b/architectures-and-processors-blog/posts/caches-self-modifying-code-implementing-clear-cache),
[Arm: multiple cores](https://developer.arm.com/community/arm-community-blogs/b/architectures-and-processors-blog/posts/caches-self-modifying-code-working-with-threads).

## Public-source publication audit

The pinned m1n1 source is commit
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
Its `memory.c` cache-range helpers issue maintenance instructions. Each opcode
used by the31K publication sequence ends in DSB SY and ISB in `proxy.c`.
Thus the absence of barriers
inside the range helper is not a demonstrated missing-barrier bug in the
31K sequence. The SMP-shared region is deliberately Device memory in all
CPU0 aliases; CPU0 AT probes and its returning control agree with that setup.
These CPU0 facts do not establish CPU1's incoming execution context.

Source locations: `src/start.S` vector table and cold/reset entries;
`src/memory.c` cache-range macro and `mmu_remap_smp_shared`;
`src/proxy.c` common operation epilogue. These are public m1n1 sources. No
Apple decompiler output or proprietary instruction bytes were used here.

## Reproduce

From the repository root, with the retained private build artifacts:

```sh
python3 -I kernel/experiments/smp31l-analysis/test_entry_contract.py \
  --image virtualization/jobs/069-smp31k/out/boot021.bin \
  --symbols virtualization/jobs/069-smp31k/out/m1n1-symbols.txt \
  --report native/boot/attempt31k-controller-2026-10-22.json

python3 -I kernel/experiments/smp31l-analysis/entry_contract.py \
  --image virtualization/jobs/069-smp31k/out/boot021.bin \
  --symbols virtualization/jobs/069-smp31k/out/m1n1-symbols.txt \
  --report native/boot/attempt31k-controller-2026-10-22.json
```

Omit `--symbols` only for explicitly image-only validation. Tests without
`--image` or `--report` skip the corresponding artifact/evidence checks and
must not be reported as complete. Mutants cover wrong registers, 32-bit stores,
shifted immediates, incorrect record offsets, changed branch type, moved stubs,
corrupt images/symbols and malformed evidence. This remains a bounded software
oracle, not a firmware emulator, native SMP test or performance benchmark.

The next physical session needs a separately supported discriminator for
entry, first fetch or first-store visibility. Repeating the same two start
writes with another equivalent negative marker would not answer those questions.

## Recorded validation

[Host validation](validation.json) records 24 methods PASS with the full
image/symbol/report and 24 methods PASS in image-only mode, with no skips.
The latter mode does not execute the symbol-corruption branch. Independent
review reran the full suite and rejected all 320 single-bit mutations across
the two five-instruction prefixes. Review identified malformed nested JSON
and missing acquisition-count checks; both were fixed and regressions passed
before this host result was recorded. No native hardware ran for this checker.

The subsequent [VM070 validation](../../../virtualization/jobs/070-smp31l-analysis/validation.json)
passed all 24 methods with the full image/symbol/report on Linux ARM64,
Python 3.14.8. Both full-symbol and image-only checker commands also passed;
the image-only test suite itself was not separately rerun in that VM. The
result objects agree with the host result, apart from the explicit symbol-mode
fields for image-only output. This verifies interpreter portability, not CPU1
execution or native cache behavior.

[Contract results](contract-results.json) bind the canonical report object;
the validation record also pins the exact original report file SHA-256,
image, symbols, checker, tests and this document. Generated summaries contain
only public code offsets, synthetic categories and sanitized evidence hashes.

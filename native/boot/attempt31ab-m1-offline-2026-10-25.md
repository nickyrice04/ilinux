# 31AB — independent M1 original entry and observer review

**OFFLINE_PASS_NATIVE_HOLD, 2026-10-25 Eastern. Native checks NOT RUN.**
Pulled main with `git pull --ff-only` from `c4a794f` through
`1354755a3ea4afc3ca084b1ec7ea47c99331d9c4`. The worktree was clean and previous
work was preserved. [Reviewed metadata](attempt31ab-m1-offline-2026-10-25.json).

## Actual M1 checks and tool limits

All **44 manifest entries PASS**, exit 0 in 0.041 s. Manifest SHA-256:
`f697bdd660f7030f7afd05c99a5078e00c2795192c22d8a9da7ad61635d456bd`.
The five documented commands ran once using fresh ignored output directories.
Actual tools: Python 3.13.5, Apple clang 17.0.0 (clang-1700.3.19.1),
macOS 26.0.1 / build25A362. No tool install, source repair or retry.

| M1 execution | Result | Exit / elapsed |
| --- | --- | --- |
| Packaging unittest discovery | 8 Python methods PASS | 0 / 0.078 s |
| Entry and transports | 2 AArch64 objects compiled; no link/execution | 0 / 0.128 s |
| Observer optimized | 12 C groups PASS | Combined runner below |
| Observer macOS ASan + UBSan | Same 12 groups PASS | Combined runner below |
| Observer freestanding compile/symbol inspection | PASS | Combined runner 0 / 1.256 s |
| Translation probe and fixture | 2 AArch64 objects compiled; no link/execution | 0 / 0.128 s |

**8 unique Python methods and 12 unique C groups.** Sanitizer variants do not
increase the unique count. The observer's 1200 translation-oracle queries pass in
each variant; both exact success markers and empty test stderr match VM086's
published variants. The packaging test log also matches M5's published log bytes.
All component bindings equal the M5 host and VM source-binding hashes:

| Component | Files bound | Source-binding SHA-256 |
| --- | ---: | --- |
| Entry | 9 | `f1cdd9d9dc957040a8774a3d7e5015e69a7cd84c1db58e0dfd0890efeba156ee` |
| Observer | 6, including frozen31Z reader | `92c956fcb3912c4b8d8a01091f13a0ca5a7763fa486dc10d082478e5df79a155` |
| Translation | 6 | `66619009f4c83158f8629d8ba90281f23e33a5f8778893167aeaf764dcc4057b` |

All five generated objects independently have ELF64 little-endian AArch64
relocatable headers and matching recorded hashes. Undefined symbols were inventoried
with the unchanged, hash-verified original31Z ELF reader: entry, transport and probe
have none; observer requires `memcpy`/`memset`; the synthetic translation fixture
requires linker-defined `fixture_l1/l2/l3` and `translation31ab_s1e2w`. Full object
hashes are in the JSON. No object was linked or executed as an AArch64 payload.

No suitable AArch64 ELF linker was found in PATH or the known Homebrew LLVM
prefixes; no QEMU system emulator was available in PATH. No tools were installed
and no shared VM was started. Therefore **M1 did not reproduce the linked ELF/
instruction audit, two-base payload equality, nine entry emulator cases or ten
translation emulator cases**. These optional checks are NOT RUN on M1, rather
than counted as passes or skips inside the completed suites. No actual linked
Mach-O was built or inspected here. Unit tests use synthetic original payloads.

## Independent code review

Read the four component READMEs, original sources, tests and runners; all six 31AB
research notes; VM086 validation and both CPU findings records. **No actionable
issue found within the documented offline contracts.** No pinned implementation
or test source was changed. The optional tool limits above remain explicit.

The entry captures full argument/state words without using incoming stack memory
or dereferencing incoming arguments. It masks DAIF, initializes its owned record,
handles EL1/EL2 explicitly, reads HCR only on EL2, selects owned stack/vector storage
and parks. The sixteen vector slots enter a stackless fatal recorder. Actual
mapping/permissions are caller/native prerequisites; fault capture is termination,
not a monitored exception-return implementation. EL0 and higher/guarded routing
are not promised. Three separate fixed-call transports remain uncalled; ordinary
AAPCS framing and their early/late placement do not prove a permitted runtime call.

Reviewed the bounded ELF parser, explicit instruction/operand whitelist, record
store bounds, vector destinations, ADR references and sixteen mutation refusals.
The audit inspects the linked artifact; compile-only does not run it. The packager
preserves input offsets, bounds aligned 64-bit image geometry, emits original
metadata and rejects writable/executable segment combinations in its tests.
Geometry/absence-of-fixup tests do not replace instruction auditing or acceptance.

Observer decoding bounds count and exact count-times24 extent, checks 16 KiB ranges,
overflow and physical/virtual overlap, preserves input order and refuses unmapped
or noncontiguous translations. The selected 88-byte revision2/version2 video prefix
preserves metadata while stripping only base low2 bits. Full framebuffer arithmetic
is validated before planning at most32x16 pixels. The RAM painter validates every
row, bound and overlap before its first ordinary byte store, so late invalid rows
leave RAM unchanged. All numeric PA/VA fields remain model labels; no physical
pointer conversion, MMIO, visibility/barrier or permission operation is supplied.
Live source identity/lifetime and valid disjoint serialized C objects remain caller
requirements. A translated range is not a writable scanout mapping.

The separate translation leaf checks EL, E2H/TGE, DAIF and MMU profile, returns
status/raw PAR distinctly, and restores 64-bit PAR on normal return. A completed AT
can still return PAR.F; a trap/nonreturn cannot guarantee restoration. It has no
candidate load/store or translation-control write. AT can affect caches/access
flags under other configurations; it is not a universally side-effect-free read.
EL0, D128, VHE and unqualified profiles remain outside its contract. The fixture's
page-table/control setup is ordinary-QEMU-only and must not enter a resident image.

## Reviewed M5 evidence, not reproduced on M1

VM086 reports six unique link/instruction audit groups and sixteen mutation refusals
per base, with identical 81920-byte payloads at bases0 and0x40000000. Nine ordinary
ARM execution cases cover EL1, EL2 and VHE; three actual BRKs exercise slot4 only.
Other vector slots are statically audited. Ten Cortex-A57 translation cases check
profile refusals, faults, NC/WB attributes, a deliberately different expected PA,
page offset, access-flag fault, PAR restoration and unchanged candidate/table bytes.
EL and E2H refusal branches are not execution-covered by that fixture. None executes
GENTER or Apple firmware. These counts do not multiply with platform/link base.

M5's original 114688-byte Mach-O and derived boot properties are parser evidence,
not firmware acceptance; M1 did not download or recreate that artifact. Its hash
and the payload hash remain in the pinned upstream validation and reviewed JSON.
The source and metadata review support the evidence separation, not independent
verification of private raw VM receipts. The recorded executable-bit, TCG/build,
network-preflight and DTB-placement failures remain retained, as does the inverted
translation audit predicate repaired before successful execution. No M1 repair or
repeat was needed; the current predicate accepts divisible-by-four extents.

The four REA requests/three batches and private instruction comparisons remain
M5-only evidence. Common-exit whole-function pseudocode stays refused; independent
checks of its complete 84-byte boundary do not admit the refused output. Entry 150
and observer 566 word counts contain three reverified call-order words, so their
sum is not wholly new unique evidence. Installed/running monitor identity is not
refreshed. The monitor's selected cold pointers do not establish table population,
normal-world readability or pre-service15 availability. Their count-initializer
ordering remains **UNKNOWN**. Neither a silent screen nor a raw-start failure can
establish an Apple-only restriction.

REA, private decoding, SDK measurements, fresh external-source retrieval, M5 VM/
Linux sanitizer execution, and actual image-property inspection were **NOT RUN on
M1**. Existing exact 31AA reviews were hash-verified and reused; older executable
suites, old inspector matrix and consumed receipts were not rerun or edited.

## Preservation and next work

All **22 prior frozen closures /5794 listed-file checks /563 distinct files PASS
unchanged**. All **522 prior intake evidence files** recursively hashed before/after,
including consumed receipts, remain unchanged. Retained 13-file boot042 package
sizes/hashes match its receipt; the client checkout is clean at
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`. Installed boot021 is unchanged by this
work. No new native-use receipt exists. Compiler temporary storage is empty; the
owned bounded caffeinate process exited. Logs and binaries remain ignored under
`build/native-intake/attempt31ab-offline/` and the three M1 review output directories.

Next integrate the observer with authenticated/bounded cold argument and count/
table reads, the actual translation profile, expected framebuffer pages and
visibility contract. An accepted observable entry comes before fixed-call/
exception lifecycle and a separately bounded physical-secondary observation.
The pieces are currently separate; no integrated native observation path or
meaningful physical test is ready. CPU software research remains active; a working
multicore workaround and Apple-only necessity are both unproved.

**Native 31AB, live target-version, physical-secondary, Linux SMP, GPU/framebuffer
and performance checks remain NOT RUN. Neither Mac restarted.** Device opens,
discovery queries, target requests, monitor calls and native invocations 0. No
installation, external contact, firmware/policy/security/volume/default change.
Original Full/lab Permissive/Macintosh HD default remain last reported, not rechecked.

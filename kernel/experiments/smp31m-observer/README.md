# 31M paired CPU0 cache observation

**Offline component; native execution NOT RUN.** This tests one observation
limitation from31L. It is not a CPU1 startup fix or evidence of native SMP.
The unchanged CPU1 prefixes write their phase and identity into Normal memory.
CPU0 first samples the record as before, then, only if that snapshot is zero,
issues one bounded clean/invalidate and samples it again.

## Why this changes the question

31L initializes and cleans the Normal records, but its freshness checks and
polls can leave clean zero lines in CPU0's cache. If CPU1 makes a store visible
to the point of coherency without updating that cached copy, ordinary CPU0
loads can continue to report zero. A successful local CPU0 store/read control
does not exclude that case. This is a hypothesis, not a diagnosed cause.

A committed expected identity in either31M snapshot establishes execution of
the original prefix. A positive maintained snapshot following a negative
cached snapshot does **not** establish a stale-cache cause: CPU1 could simply
have arrived between them. Two negative snapshots remain compatible with no
entry, an earlier exception, a private CPU1 dirty line, an inaccessible record
or an alternative route. No callback or extra core follows any positive.

## Operation and its scope

The new operation is **CPU0-issued `DC CIVAC` to PoC**, with the existing
proxy's `DSB SY; ISB` completion before loads. Its effects are not guaranteed
to remain in CPU0's cache. The records are Outer Shareable, and maintenance
can affect other PEs in that domain. `DC IVAC` was rejected because an
invalidate-only operation is insufficient protection for an unknown dirty
CPU1 record. Clean/invalidate preserves dirty data according to its cache
maintenance semantics; it is not a direct zero store to the record.

CPU0 must zero and clean the entire owned128-byte span for each record before
any CPU1 start, verify the readback and then perform **no CPU0 record stores**.
Thus a stale CPU0 zero line is clean: this observer must not generate dirty
CPU0 zeros that could overwrite a later CPU1 publication. These are enforced
controller premises, not facts established by the pure observer alone.

No MMIO, permission change, reset redirect, CPU1 cache instruction, set/way
operation or broad cache sweep is added. Only the already allocated helper's
fixed two record addresses are accepted by the observer.

## Qualification and layout

The new8-byte original leaf at helper+`0x220` reads `CTR_EL0` and returns. It
runs on CPU0 before starts, after code publication and permission checks.
Qualification requires currentEL2, the already observed VHE host regime
(E2H/TGE set, stage2 disabled), and explicitly reported geometry. `DMinLine`
is decoded separately from `CWG`; the minimum is never used as a maximum.

Accepted sizes are DMinLine64/128 bytes and CWG64/128 bytes with CWG at least
DMinLine. CWG0, larger bounds, unsupported encodings or another execution
regime refuse before starting CPU1. This intentionally restrictive experiment
does not claim those other geometries are invalid hardware.

| Owned helper range | Role |
|---|---|
| `0x220..0x228` | CPU0 CTR reader, outside existing control leaf |
| `0x1000..0x1080` | Vector record and exclusively owned padding |
| `0x1080..0x1100` | Cold record and exclusively owned padding |
| `0x1100..0x1180` | Separate CPU0 control and its owned padding |

Each record begins on a128-byte boundary. The record's phase and identity fit
inside its first16 bytes; the actual maintenance request spans64 bytes and
the known range helper issues one operation. Full128-byte ownership ensures
the supported maximum granule cannot overlap code, the other record or the
control. All spans remain inside the existing16KiB allocation.

Arm documents the architectural CWG and DMinLine field meanings in its
[CTR_EL0 description](https://documentation-service.arm.com/static/5e7e09f6a3736a0d2e862d2f).
Only those meanings are used; that Cortex implementation's values are not
assigned to Apple hardware. The [Arm system-register supplement](https://documentation-service.arm.com/static/649ae5b238511951cb799288)
also distinguishes EL1 cache-maintenance traps from the VHE host regime.
CPU0 qualification does not assign any of these states to CPU1.

## Pinned m1n1 path audit

`audit.py` requires the exact retained boot021 image, SHA256
`ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664`.
The corresponding source pin is `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
An independent Apple LLVM decode checked73 instruction words against the
original bytes with zero mismatches. See [validation.json](validation.json).

| Image location | Established behavior |
|---|---|
| `0x80fb4` | Signed16-bit dispatch entry for opcode`0x30a`, target`0x2d454` |
| `0x2d454..0x2d470` | Loads address/size, calls`0x277a0`, returns to common epilogue |
| `0x277a0..0x27820` | CIVAC range helper with64-byte stride; its legacy Cyclone workaround depends on selected feature flag+11 |
| GOT`0x108188` | Relative relocation to the `cpu_features` variable at`0x1012d0` |
| `0x2ce48..0x2ce64` | `DSB SY`, `ISB`, restoration of the saved guard, return |

The existing feature gate verifies selected features at`0x7fba8`, including
the false Cyclone flag. The new controller must additionally bind the live
GOT entry and dispatch-table entry before starts; the old text comparison
does not cover either location. With that flag false and size64, the helper
executes one CIVAC and skips its implementation-specific register writes.
The cache request does not temporarily change the shared exception guard;
the common epilogue restores its saved value, as it does for existing calls.

Relevant public source:
[`memory.c`](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/memory.c),
[`proxy.c`](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/proxy.c),
[`utils.h`](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/utils.h).

## Observer contract and tests

`PairedTracker` receives fixed read, maintenance and local-journal callbacks.
Its order is cached phase/identity/phase; if allzero, persist maintenance
intent, issue one request, verify acknowledgment, persist it, then acquire the
maintained phase/identity/phase. A snapshot can commit CPU1 identity only if
its first phase already establishes the commit. Any positive snapshot stops
the experiment; partial state is never promoted to identity evidence.

Every target or journal failure closes the observer immediately, retaining
completed-prefix counters. It performs no retry, extra sample, restoration
or cleanup callback. Foreign exception text is not copied into public state.
The caller must stop the entire campaign if either record tracker closes.

Initial macOS validation: **21 observer methods plus3 pinned-image audit
methods PASS**, including fault injection across all7 target operations,
both journal boundaries, wrong maintenance acknowledgments, geometry/refusal
cases and committed/partial observations. These tests validate software
contracts, not Apple cache coherency. Independent CTR assembly and complete
controller/client VM testing are tracked by the attempt release separately.

```sh
python3 -I kernel/experiments/smp31m-observer/test_observer.py
python3 -I kernel/experiments/smp31m-observer/test_audit.py --image PATH_TO_BOOT021
```

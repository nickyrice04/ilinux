# M1 handoff: 31Z local SPTM handoff and original adapter components

**Offline review only. Native31Z HOLD / NOT RUN. Do not restart either Mac.**
This follows the M1 review in commit `776b54f`. It prepares no boot package,
monitor call, CPU start, installation or security change. The user's no-outreach
instruction still applies; do not post or contact another project.

## What changed

Installed SDK headers supply useful SPTM interface documentation, but their
measured bootstrap layouts do not match this M5's retained/current kernel.
The local cold consumer copies **848 bytes**; the measured SDK profiles differ.
The original adapter therefore preserves that explicit local snapshot and
extracts only the independently corroborated physical first-available field
at offset24. It never guesses the rest of the record from another SDK version.

The original C code separates entry reasons and argument roles, rejects wrong
lengths and inconsistent profiles, and computes allocator extents above the
monitor boundary while preserving supplied reservations. It includes no native
entry assembly, monitor dispatch, MMIO or transport. Its source/profile selector
is a caller assertion, not proof that a future native handoff is valid.

The local kernel also corroborates boot-CPU registration through dispatch14.
Its input is the zero-extended32-bit ADT `reg` affinity, distinct from the
full diagnostic MPIDR with Aff2 bits. Registration is a prerequisite under an
already resident monitor, not a way to start one after raw boot. Nothing here
authorizes calling it or converting the earlier CPU2 plan into a live attempt.

## Review and run

Inspect `git status --short`, preserve local work and use `git pull --ff-only`.
Report divergence without discarding changes. Record the reviewed commit.
Read these files and their provenance/limits:

- `research/native31z-handoff.md`
- `research/native31z-public-contract.md`
- `reverse-engineering/findings/cpu-startup31z/validation.json`
- `kernel/experiments/sptm31z-adapter/README.md` and its C sources/tests/runner
- `native/boot/attempt31z/validation.json`
- `virtualization/jobs/084-offline31z/validation.json`

From the repository root:

```sh
shasum -a 256 -c native/boot/attempt31z/source-sha256.txt
python3 -I kernel/experiments/sptm31z-adapter/run.py \
  --output build/31z-adapter-m1-review --sanitize --freestanding
```

Use a fresh ignored output directory. The tests need only existing Python and
C/Clang tools; they do not need Apple SDK headers, binaries or a live monitor
record. Do not install tools or change security settings to satisfy the review.
If a compiler/runtime is unavailable, retain the error and report the unrun part.

Expected: **16 unique C groups** (eight entry, eight memory), passing optimized
and ASan/UBSan repetitions. Repetitions do not add to the unique count. The entry
suite includes854 rejected lengths and848 byte-position checks; the independent
memory oracle covers2304 page configurations. Require exact success markers and
source bindings; review the substantive bounds and failure behavior as well.

The freestanding check compiles two AArch64 ELF relocatable objects and inventories
undefined runtime symbols. Compiler-dependent object hashes/dependencies need not
match M5. Record them without implying the objects are linked or bootable. The
M5 host emitted no undefined entry symbols and `memcpy`/`memset` in the memory
object; those runtime dependencies would need implementation during integration.

## Report precisely

Write the usual dated pair:

- `native/boot/attempt31z-m1-offline-YYYY-MM-DD.md`
- `native/boot/attempt31z-m1-offline-YYYY-MM-DD.json`

Record commit, manifest result, actual tools, source-binding hash, suite outcomes,
sanitizer outcomes, freestanding object inspection and actionable findings.
Raw runner logs stay under ignored build because they contain local paths.
All public test inputs are synthetic. A future real monitor snapshot can contain
random seeds and other private state and must never be published as a fixture.

Keep REA, private kernel decoding, SDK conditional-layout compilation, external
source retrieval and M5 VM execution **NOT RUN on M1** unless independently
performed. They are not prerequisites for this focused code review. No repeat
of the31Y inspector matrix or older executable suites is required: their frozen
source identities are preserved separately.

Use `OFFLINE_PASS_NATIVE_HOLD` only when the stated review has no actionable
blocker; report missing or failed required checks explicitly. Update
progress/coordination and push the review under the established handoff workflow.
Preserve all earlier records, consumed receipts and unrelated work.

## Next native gates

The remaining work includes accepted host-image construction, actual entry
stack/translation state, argument-buffer lifetime and complete memory ownership,
helper/exception/fixups lifecycle, then correctly ordered CPU registration and
physical-secondary observation. These components implement a useful bounded part
of that path; they do not establish all of it. No native controller, installation,
proxy session, policy check or reboot follows from this review. A software route
remains under investigation; Apple-only necessity is not established.

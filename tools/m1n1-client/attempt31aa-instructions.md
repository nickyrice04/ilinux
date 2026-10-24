# M1 handoff: 31AA helper contract and CPU registration preparation

**Offline review only. Native 31AA HOLD / NOT RUN. Do not restart either Mac.**
This follows the M1 31Z review in commit `6106a6c`. No boot image, installation,
monitor invocation or live CPU experiment is included. The user's no-outreach
instruction remains in force.

## Review the change

Preserve local work, inspect `git status --short`, and use `git pull --ff-only`.
Report divergence without discarding changes. Record the exact reviewed commit.
Read:

- `research/native31aa-public-contract.md`
- `kernel/experiments/sptm31aa-adapter/README.md` and its implementation/tests
- `native/boot/attempt31aa/validation.json`
- `virtualization/jobs/085-offline31aa/validation.json`

This package contains the registration planner, its tests and the public-contract note only. The earlier local REA batch on the helper initializer and image fixups is retained in ignored build storage and is **not** part of this package; there is no handoff note or CPU findings file for 31AA to review.

The original registration planner builds ordered arguments for a future bridge.
It preserves CPU source IDs and class metadata, checks boot-first ordering and
uniqueness, and distinguishes predicted logical ordinals from observed monitor
results. The real registration service returns no success value. No monitor call,
mutable execution cursor, retry loop or hardware-ready state is implemented.

Check the important limitation: a diagnostic MPIDR can fit in 32 bits. Width
validation alone cannot authenticate it as an ADT affinity. The project fixture
must derive its values from the pinned sanitized ADT, without MPIDR fallback or
masking. The caller must independently bind the actual ordered CPU set and boot
identity. Core-class preservation is not scheduler or performance validation.

## Execute the focused offline checks

From the repository root, using a fresh ignored output directory:

```sh
shasum -a 256 -c native/boot/attempt31aa/source-sha256.txt
python3 -I kernel/experiments/sptm31aa-adapter/run.py \
  --output build/31aa-adapter-m1-review --sanitize --freestanding
```

Use existing Python/C/Clang tools only. Record any unavailable compiler/runtime
and the checks it prevents; do not install tools or modify security settings.
Require exact source bindings and success markers from the runner. Sanitizer
repetitions are not additional unique groups. Inspect failure behavior, preserved
input ordering, owned output, fixture provenance and composition with frozen 31Z.

Record freestanding AArch64 object formats and undefined runtime symbols.
Compiler-dependent object hashes need not match M5. Compiling a relocatable object
does not link a host image, satisfy its runtime dependencies or prove native entry.
Keep raw logs and generated artifacts in ignored build storage.

## Report and preserve scope

Write the usual dated Markdown/JSON pair:

- `native/boot/attempt31aa-m1-offline-YYYY-MM-DD.md`
- `native/boot/attempt31aa-m1-offline-YYYY-MM-DD.json`

Include the commit, manifest result, tools, actual group counts, sanitizer results,
source-binding hash, object inspection and actionable findings. Mark upstream
REA, private local-binary checks, SDK/public-source retrieval and M5 VM execution
**NOT RUN on M1** unless independently performed. No repeat of older executable
suites or the 31Y inspector matrix is needed for this focused review.

Use `OFFLINE_PASS_NATIVE_HOLD` only when the required checks pass and the review
has no actionable blocker. Update progress/coordination and push the review under
the established workflow. Preserve all frozen closures and earlier evidence.

The native gate is qualification of the fields/services our actual bridge needs,
not decoding every unused byte of the monitor record. A minimal original image
may require no chained pointer fixups, but still needs a qualified image contract,
mapped entry stack and vectors, exception/monitor continuation, and the correct
fixups-complete and registration lifecycle. Neither parser agreement nor this
argument planner supplies those guarantees. A physical test will be prepared only
when it can discriminate a new hypothesis; no reboot or policy check follows from
this review. A working workaround and an Apple-only necessity remain unproved.

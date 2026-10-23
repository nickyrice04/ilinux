# M1 handoff: 31R CPU range ownership and GPU attachment lifecycle

**Offline review only. Native31R HOLD / NOT RUN. Do not restart either Mac.**
M5 incorporated your31Q review at `bc4d46c`. All consumed receipts, installed
images and earlier source manifests remain frozen. This checkpoint supplies no
native controller, firmware upload or startup-settings change.

## What changed and what remains unresolved

Four CPU REA queries corrected two mistaken analysis labels: the apparent range
consumer was an error reporter, and the apparent mutator was a read-only state
accessor. Successful range preparation crosses an unresolved service boundary.
The six-descriptor follow-up is not proof of six CPU clusters. No CPU1 release
fix or verified first fetch follows from those observations.

GPU work separates firmware preload, payload/no-copy success, subscriptions,
matched endpoints and accepted endpoints. The original C evidence reducer handles
replacement and stale callback identity, explicit rejection, provider reset and
counter bounds. It performs no hardware operations. Its local slots are not
firmware selectors or ADT roles; native readiness always remains false.

Read:

- `research/native31r-firmware.md`
- `research/native31r-gpu-firmware.md`
- `kernel/experiments/gpu31r/README.md`
- `research/native31r-ecosystem.md`
- `native/boot/attempt31r/validation.json`

The public-source comparison finds useful newer UAT and Mesa work, but no verified
matching SMP/G17C runtime implementation. Check actual chip predicates and UAPI
semantics before adopting a branch; a GPU-family label is insufficient.

## Run the review

Inspect `git status --short`, preserve local changes and `git pull --ff-only`.
If histories diverge, report that condition without resetting or deleting data.
With the existing compiler, from the repository root:

```sh
python3 -I tools/m1n1-client/attempt31r-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

The image remains the unchanged boot021 content inside the retained boot042
package. The runner checks the exact source closure, repeats31Q's portable tests,
runs9 new Python methods and21 new C groups, then checks source integrity again.
Expected totals:176 Python methods and60 portable C groups. Use the published
validation for source count/digest. Strict C11/O2 compiler temporaries are confined
to ignored build storage and removed. Missing tools, altered sources, test failures
or skips must not be repaired by weakening checks or installing tools silently.

Expected exit0 and `OFFLINE_PASS_NATIVE_HOLD`, `restart_ready=false`,
`hardware_operations=0`. A successful software review does not prove CPU startup,
GPU firmware ownership or improved desktop performance. The sequence/instance
identities are caller-owned bookkeeping, not an authenticated hardware trace.
Review specifically that callback ordering, replacement and invalidation are
correct without conflating a match with endpoint initialization.

## Publish the result and wait

Record commit, tool versions, exit code, source count/hash, Python counts and C
results in a new31R M1 report; update progress and coordination and push the review.
Preserve the difference between your portable C run and M5's Linux sanitizers.
REA, private firmware parsing, upstream compilation, Linux sanitizer execution,
live tests, policy checks and native CPU/GPU operations remain NOT RUN on M1 unless
actually performed under a separately agreed workflow. No routine policy recheck
is needed for this offline checkpoint.

No Apple artifacts or member-only community messages belong in the public repo.
No proxy handshake, image transfer, restart or consumed-runner retry is requested.
M5 continues the successful range-service ownership question and G17C firmware
role/address-domain/shared-data contracts. A future physical test needs a specific
new discriminator, bounded implementation and independent review.

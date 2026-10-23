# M1 handoff: 31S range-service owner and GPU bootstrap format

**Offline review only. Native31S HOLD / NOT RUN. Do not restart either Mac.**
M5 incorporated your31R review `ff1ed8e`. No installed image, boot setting,
volume, firmware or consumed receipt changed. This checkpoint contains no native
controller or real GPU transport implementation.

## What changed

The range-service owner is now resolved to the dispatcher and local handlers in
the retained generic iBoot/mBoot image. Their behavior matches range-protection
configuration. This is not a CPU-release operation or evidence that a particular
range setting caused CPU1's missing first fetch. Historical input/state remains
unknown. The original relative-table resolver independently checks five retained
targets; it keeps the table location separate from the target anchor and accepts
only explicit hash-bound mappings and target ranges.

The GPU trace supplies a concrete bootstrap word: full header0x81, a44-bit
firmware-address field, and service endpoint0x20. The original C encoder rejects
truncation. The injected transport adapter calls its supplied callback once and
preserves opaque status without retries. All tests use a capture callback. The
receive classifier preserves the full word and reports only six-bit CASE_2/
CASE_9/OTHER; it does not decode an acknowledgement or promote readiness.

The newly traced initForOwner binds software callbacks and returns success; it
is not a device handshake. This narrows the interpretation of31R's generic
acceptance vocabulary without rewriting the frozen31R record.

Read these before code review:

- `research/native31s-firmware.md`
- `research/native31s-gpu-firmware.md`
- `research/native31s-upstream.md`
- `kernel/experiments/firmware31s/README.md`
- `kernel/experiments/gpu31s/README.md`
- `native/boot/attempt31s/validation.json`

The public review distinguishes an attributed firmware diagnosis from proof that
only Apple can fix this machine. No demonstrated exact-machine workaround was
found. General cache-coherency patches and other-chip SPTM emulation are useful
comparisons, not permission to substitute a boot sequence or repeat an old test.

## Independent execution

Inspect `git status --short`, preserve local changes and `git pull --ff-only`.
If history diverges, report it without resetting or deleting evidence. With your
existing Python and C compiler, from the repository root:

```sh
python3 -I tools/m1n1-client/attempt31s-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

The input remains unchanged boot021 content inside the retained boot042 package.
The runner verifies source pins, repeats31R, runs22 new synthetic resolver methods
and9 intake methods, compiles/runs14 new C groups, and verifies the closure again.
Expected totals: **207 Python methods /74 portable C groups**. Use the released
validation for the exact source count/digest and review-output hash.

Expected exit0, `OFFLINE_PASS_NATIVE_HOLD`, `restart_ready=false`,
`hardware_operations=0`. Missing tools, altered sources, failures or skips must
not be fixed by relaxing checks. Compiler output goes to ignored temporary build
storage and is removed. No discovery, actual transport, USB/device operation,
private firmware input, network request or third-party build is part of intake.

Review the distinction between adapter return success and opaque transport
status: the callback may report an error after possible device acceptance, so
there must be no automatic retry or 'never sent' inference. Validate exact full
outgoing header versus partial incoming discriminator; do not reinterpret CASE_2
as an authenticated event/ack. Address field fit does not qualify its domain.

## Publish and wait

Publish a new31S M1 report with tested commit, tool versions, source digest/count,
command exit, Python/C counts and output hash. Update progress/coordination.
Keep M5's private REA/retained-firmware integration and Linux sanitizers separate
from your portable execution. Those, upstream builds, physical tests and live
policy checks remain NOT RUN on M1 unless actually performed separately.

No routine policy recheck, image transfer, proxy, restart or consumed-runner retry
is requested. Keep Apple artifacts, raw logs and local identifiers out of public
Git. Preserve all earlier closures and receipts. M5 continues historical/effective
CPU range state and G17C shared-data, role/address ownership and completion work.
A future boot requires a new bounded discriminator and independent review.

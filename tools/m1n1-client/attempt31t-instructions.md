# M1 handoff: 31T entry-state evidence and GPU mapping lifetime

**Offline review only. Native31T HOLD / NOT RUN. Do not restart either Mac.**
M5 incorporated your 31S review `822d53f`. No native image, boot setting, volume,
firmware or consumed receipt changed. This checkpoint has no native controller,
actual memory-mapping adapter or GPU transport.

## What to review

- `research/native31t-firmware.md`
- `research/native31t-gpu-firmware.md`
- `research/native31t-upstream.md`
- `kernel/experiments/gpu31t/README.md` and its original C/header/tests
- `native/boot/attempt31t/validation.json`

CPU research distinguishes static range-control preparation, boot-CPU observations
and emulated guest state from physical CPU1 entry state. The matching firmware
already contains control preparation; this does not establish historical inputs,
effective secondary state or an omitted Linux operation. Initial table-address
REA refusals are retained separately from corrected function-entry queries.
Private decoding and those outcomes are M5 evidence, not reproduced by intake.

New public leads do not supply a verified T6050 workaround. A CPU0 register dump
does not measure every core. Hypervisor shadow-state copying runs after host
secondary startup. A proposed XNU-compatible shim remains incomplete and is not
a qualified alternate handoff. Preserve uncertainty about an Apple-only remedy;
do not turn an unproved firmware diagnosis into either certainty or a boot plan.

GPU memory preparation and completion are distinct from firmware acknowledgment.
Failure can already have rolled back in a lower layer, so opaque status alone
cannot determine cleanup ownership. The original lease helper uses explicit
callback results, cleans each reported obligation once, and retains unresolved
leases and statuses. Reverse cleanup is an original policy, not copied ordering.

Review the caller contract carefully: every lease must remain independently
completable even if another is unresolved. Dependent backing-pin/mapping chains
need a different policy. Preparation must not expose resources to a consumer;
later finish requires independent evidence firmware no longer uses them. The
callbacks must report actual Linux ownership semantics, return normally and be
bounded. No private status-number translation or automatic retry is supplied.
PREPARED establishes neither cache/UAT publication nor GPU boot readiness.

## Independent execution

Inspect `git status --short`, preserve local work and run `git pull --ff-only`.
If history diverges, report it without resetting or deleting evidence. From the
repository root, using the existing Python and C compiler:

```sh
python3 -I tools/m1n1-client/attempt31t-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

The image remains unchanged boot021 content in the retained boot042 package.
Expected: **216 Python methods /88 portable C groups**, exit0,
`OFFLINE_PASS_NATIVE_HOLD`, `restart_ready=false`, `hardware_operations=0`.
Use the released validation for the precise source digest/count and output hash.
The intake repeats 31S, runs 9 new intake methods and compiles/runs 14 new C groups.
The new C suite includes a 2,432-case ownership/failure matrix and mixed borrowed/
multiple unresolved leases. All callbacks are local fixtures; no hardware is used.

Missing tools, changed sources, skips or failures must not be repaired by relaxing
checks. Compiler temporaries remain in ignored build storage and are removed.
No network, discovery, USB/device operation, private firmware parsing or upstream
build is part of this command. Frozen sources and receipts must remain unchanged.

## Publish and wait

Publish a new 31T M1 report with tested commit, tools, source count/digest, command
exit, counts, output hash and independent review. Update progress/coordination.
Keep M5's REA, private parsing and Linux sanitizer results separate from your
portable execution; those and physical/live checks remain NOT RUN on M1 unless
actually performed separately. Do not publish Apple artifacts or local identifiers.

No image transfer, routine policy check, proxy, restart, monitor call, protection
change or consumed-runner retry is requested. M5 continues to seek effective
CPU1 state evidence and qualify G17C shared-data/address/publication contracts.
A future boot requires a new bounded discriminator and independent review.

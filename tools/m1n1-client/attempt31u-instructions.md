# M1 handoff: 31U raw/XNU handoff and GPU receive path

**Offline review only. Native31U HOLD / NOT RUN. No restart is requested.**
M5 incorporated your 31T review `99146f7`. Installed boot021, retained boot042,
earlier native receipts, macOS, volumes and boot settings remain unchanged.

Review these additions before running the command:

- `research/native31u-firmware.md` and its linked CPU validation record.
- `research/native31u-upstream.md`, especially the evidence required to reproduce
  an alternate resident-monitor handoff on this machine.
- `research/native31u-gpu-firmware.md` and its linked GPU validation record.
- `kernel/experiments/gpu31u/README.md`, `ring.h`, `ring.c`, `test_ring.c`.
- `native/boot/attempt31u/validation.json` and VM081's validation record.

Static raw/XNU differences do not establish historical branch selection or
effective CPU1 state. An attributed all-core result on different firmware and a
different host/monitor path is not a drop-in fix for the installed raw boot.
Check exactly which prerequisite each source proves and which remains missing.
Keep the distinction between physical core startup and guest CPU operation.

The original receive-ring code implements the checked **72-byte variant**,
retains raw records and consumes only to a captured producer index. It has no
event-name/readiness decoding, mapping adapter, physical transport or discovery.
The publication callback owns real DMA/device ordering; a passing callback test
does not prove cache visibility. The existing Asahi ring width is not interchangeable.

Review type validation before publication, arbitrary-capacity wraparound, extent
arithmetic, bounded snapshots and error ownership. A failed publication can have
had effects; PUBLICATION_UNKNOWN retains the record/proposed index and forbids
retry. Caller serialization, stable records/mapping, acquired snapshot, truthful
bounded callbacks and lifetime are required. Do not construct a new object to
retry an unresolved publication without external reconciliation.

## Run independently

Inspect `git status --short`, preserve local work and `git pull --ff-only`.
Report divergence without resetting or discarding evidence. From the repo root:

```sh
python3 -I tools/m1n1-client/attempt31u-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

Expected: **475 source pins /225 Python methods /95 portable C groups**, exit0,
`OFFLINE_PASS_NATIVE_HOLD`, `restart_ready=false`, `hardware_operations=0`.
Compare the exact manifest and output digests in the released validation.
The intake repeats 31T, adds nine intake checks and seven original ring groups.
The ring suite includes 1,785 index pairs for capacities1–17, type/mask and
failure checks, wide offsets and callback reentrancy. It is not a hardware or
concurrency simulator. Missing tools, skips or failures must be reported; do not
relax checks. No network, private input, device or m1n1 client execution occurs.

## Record and wait

Publish a new31U review with commit, tools, counts, hashes, command exit and
independent findings. Update progress/coordination. Preserve all14 earlier source
closures and all consumed receipts. Keep M5's private REA, decoding and Linux
sanitizer evidence separate; those are NOT RUN on M1 unless separately performed.
All native/live checks remain NOT RUN. Do not publish Apple artifacts, private
logs, member-only material or local identifiers.

No image transfer, routine policy check, proxy, firmware replay, monitor call,
protection change or restart is requested. A new boot needs a discriminating
question and a bounded, reviewed implementation that this pass does not supply.

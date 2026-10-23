# M1 handoff: 31V alternate CPU bootstrap and GPU mapping messages

**Independent offline review only. Native31V HOLD / NOT RUN. No restart.**
M5 incorporated your 31U review `c510d74`; no actionable issue was found in it.
The retained images, native receipts, macOS, boot settings and volumes remain
unchanged. This update does not provide a native-use command or new image.

Read the three 31V research documents and linked validation records first:

- `research/native31v-firmware.md`: the new shared pre-entry helper processes
  a revision-3-sized command-line span, not monitor activation. Final forwarding
  does not establish CPU1's effective state. Prior decompiler refusals remain.
- `research/native31v-upstream.md`: Aura excludes the alternate host boot-object
  implementation from its public release. Its applicable T6050 WFE policy is
  post-entry, not a new first-fetch prerequisite. Reported all-core guest results
  still need the exact host/accepted-image/physical-entry provenance.
- `research/native31v-gpu-firmware.md`: the outgoing mapping record and queue
  contract are separated from PTE mapping, notification delivery and completion.
  Two fresh cross-boundary decompilations are explicitly refused. Independent
  bounded instruction evidence supports the documented narrow contract.

Review `kernel/experiments/gpu31v/{mapping.h,mapping.c,test_mapping.c,README.md}`.
The original component encodes 24-byte records and attempts one publication to a
256-slot queue. Invalid inputs and full queues cause no callback. Refused writes
or publication can have effects and become terminal unknown states; no automatic
retry or replacement object may bypass reconciliation. The caller owns a stable
mapping, acquired indices, sole-producer serialization across prepare/submit,
actual DMA/device ordering, near-full progress/wakeup and completion. Callback
acceptance is not a firmware acknowledgment or native readiness claim.

## Run independently

Inspect `git status --short`, preserve local work, then `git pull --ff-only`.
Report divergence without reset or discarded evidence. From the repository root:

```sh
python3 -I tools/m1n1-client/attempt31v-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

Expected: **492 pins /234 Python methods /103 portable C groups**, exit0,
`OFFLINE_PASS_NATIVE_HOLD`, `restart_ready=false`, `hardware_operations=0`.
Compare manifest and review-output hashes with
`native/boot/attempt31v/validation.json` and VM082's validation record.
The intake repeats 31U, adds nine intake checks and eight C groups. The C groups
include all 65,536 consumer/producer index pairs, exact wire bytes and injected
failures after effects. They are software tests, not hardware simulation.

Missing tools, skips or failures must be recorded; do not weaken the checks.
No network, proprietary input, discovery, device open or m1n1 client execution
occurs. Keep the M5's private REA, independent decoding and Linux sanitizer
results separate: NOT RUN on M1 unless independently performed.

## Publish the review and wait

Write a new 31V review with the reviewed commit, tools, command exit, counts,
digests and independent findings. Update progress/coordination and push. Preserve
all 15 earlier source closures and consumed receipts. Publish only original notes
and sanitized metadata; no Apple artifacts, private logs or local identifiers.

All native/live checks remain NOT RUN. No image transfer, policy check, proxy,
monitor replay, protection change or reboot is requested. A future boot needs a
new discriminating observation with a bounded reviewed implementation. Current
work has not yet qualified the alternate CPU bootstrap or native GPU adapter.

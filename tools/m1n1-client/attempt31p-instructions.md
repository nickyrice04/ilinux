# M1 handoff: 31P CPU research and GPU foundation checks, offline only

**Native 31P is HOLD / NOT RUN. Do not restart either Mac.** No new native
controller, image installation, firmware replay or target operation is released.
Keep the existing consumed receipts and use files, including 31N, unchanged.

This checkpoint continues the CPU image-preparation investigation and starts
GPU foundation work. REA findings distinguish software object preparation from
hardware core release. GPU code validates this machine's dual firmware-controller
descriptors, preserving full-width addresses and uncertain address domains.
Neither workstream has established native secondary execution or GPU acceleration.

Read the current records:

- `research/native31p-firmware.md`
- `research/native31p-gpu-contract.md`
- `research/native31p-gpu-build.md`
- `research/native31p-environment.md`
- `native/boot/attempt31p/validation.json`

## Independent offline review

Preserve local changes. Inspect `git status --short`, then `git pull --ff-only`.
Stop on divergence instead of resetting or clearing receipts. From repo root:

```sh
python3 -I tools/m1n1-client/attempt31p-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

The retained boot021 image is unchanged. This command verifies pinned sources,
runs the previous 31O image-only review, executes the new original Python tests,
compiles and runs the original portable C codec tests with the existing `cc`,
and validates the retained sanitized ADT. Temporary compiler output stays under
the ignored project build directory and is removed after the test. No third-party
build code is executed by this intake. It has no live mode, device discovery,
USB open, m1n1 client import or target request.

Expected exit 0 and `OFFLINE_PASS_NATIVE_HOLD`, with `restart_ready=false` and
`hardware_operations=0`. The final validation record contains actual counts and
the source digest. A missing C compiler is a refusal; report it rather than
installing host tools or skipping compilation. This review uses neither full
image symbols nor private Apple firmware. Those checks remain separate evidence.
Do not transfer firmware to M1 to fill a missing optional result.

## Record the result and wait

Publish the tested commit, source count/digest, command exit, Python test counts,
C codec result and ADT classification in a new offline result document, with
progress/coordination updates. Keep upstream Mesa/kernel builds marked NOT RUN
on M1 unless separately reproduced in an isolated Linux VM. Distinguish the
portable C test from M5's Linux sanitizer validation. Do not copy build binaries,
private research, compiler diagnostics containing local paths, or raw firmware.

Mark native CPU/GPU work NOT RUN, with zero target operations and no readiness
grant. M5 owns the next CPU prerequisite investigation and G17C integration
work. A physical handoff must first identify a new distinguishing question,
review its exact operations and pass its own offline tests. This checkpoint
does not authorize reusing any earlier runner or changing macOS settings.

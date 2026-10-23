# M1 handoff: 31Q CPU preparation and GPU memory contracts

**Offline review only. Native31Q HOLD / NOT RUN. Do not restart either Mac.**
This release has no native controller, image installation or target operation.
Keep all earlier consumed receipts and installed boot images unchanged.

M5 incorporated the independent31P review at `5058916`. The next checkpoint
continues the actual raw-image preparation trace and G17C firmware interface
analysis. It adds original portable GPU VA planning and a separately typed
page-number conversion. Neither establishes CPU1 entry, usable GPU firmware,
native page-table configuration or performance parity.

Read these records before reviewing the code:

- `research/native31q-firmware.md`
- `research/native31q-gpu-firmware.md`
- `research/native31q-gpu-planner.md`
- `native/boot/attempt31q/validation.json`

## Review with retained local inputs

Inspect `git status --short`, preserve local changes, and use `git pull --ff-only`.
If branches diverge, stop and report the state; do not reset or clear receipts.
From the repository root, using the existing C compiler:

```sh
python3 -I tools/m1n1-client/attempt31q-offline.py \
  --image build/native-boot042-download/ilinux-j716c-boot042/m1n1.bin
```

The input remains the unchanged boot021 image in the retained boot042 package.
The runner verifies its source closure, repeats the prior31P portable checks,
runs the new original tests, compiles the two original C components and checks
the closure again. Compiler temporaries are confined to ignored build storage
and removed. No third-party code, installer, client discovery, USB access or
hardware API is run. A missing compiler or failed test is a refusal; do not
install tools, skip tests or weaken checks to obtain a pass.

Expected: exit0, `OFFLINE_PASS_NATIVE_HOLD`, `restart_ready=false`,
`hardware_operations=0`. Use the release validation for exact source/test counts
and manifest digest. Compilation and synthetic models do not emulate CPU reset,
GPU firmware, hardware mapping lifetime or synchronization. The planner's local
output transaction does not make a later kernel mapping ioctl atomic.

## Publish reviewed results, then wait

Record the tested commit, tool versions, source count/digest, command exit,
Python counts and each C result. Publish a new M1 offline result document and
update progress/coordination. Preserve distinctions between portable C tests
and M5's Linux sanitizer runs. Keep REA, private artifact checks, Linux sanitizer
execution, upstream rebuilds and native CPU/GPU tests marked NOT RUN on M1 unless
actually performed through a separately agreed workflow.

Do not transfer Apple binaries, decompiler output or personalized boot objects;
no such material is needed for the intake. Do not publish local filesystem
paths, credentials or raw compiler diagnostics. Record zero new target operations
and no reboot. This pass supplies no native readiness grant.

M5 owns the unresolved first-secondary startup and G17C handoff/mapping work.
A later physical test must distinguish a specific remaining hypothesis and have
its own implementation, bounds, failure handling and offline validation. Nothing
here authorizes a consumed-runner retry or changes to macOS or boot policy.

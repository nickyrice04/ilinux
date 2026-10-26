# 31AF immutable complete-payload emulator fixture

This original fixture supplies synthetic resident-cold inputs to the complete
`immutable31af` image. It loads no Apple firmware and performs no native hardware
operation. The native payload's entire identity mapping is read-only, including
the reserved `__DATA_SPTM` range. Incoming SP is zero. A successful paint therefore
cannot depend on writable image data or a usable incoming stack.

For each new-image case, the RAM loader model fills reserved offsets
`0x4000..0x58000` with byte `0xa5` before execution. This represents initialized
monitor-owned storage and is compared byte-for-byte afterward. The linked input,
its original hash and the native packaged image remain unchanged; each case
records a separate loaded-model hash. The exact old 31AE negative control is
loaded without any sentinel substitution.

The marker is the centered 128×64 rectangle in a synthetic 256×128 framebuffer:
8192 four-byte pixels, 32768 bytes of actual pixel stores. The harness checks the
exact footprint and verifies the complete payload, descriptor/helper/table inputs
and translation tables remain byte-identical. It reads terminal phase/status from
CPU registers through QMP's HMP register view, never from a payload-owned record.

The 40 new-image cases include ordinary/VHE EL2, Normal NC/WB, 30/32-bit pixels
and incoming fully unmasked or partially masked DAIF. There are 14 positive
paints and 26 refusals. Refusal cases cover nonzero full-width reasons, MMU off,
mixed HCR, inaccessible inputs, helper/count/video/range errors and framebuffer
permission, mapping, attribute and protected-alias errors. All refusals must leave
the framebuffer and other supplied storage unchanged. These are synthetic code
checks, not evidence of native entry or panel scanout.

Four positive cases use the 16 KiB VHE translation profile with
`TCR_EL2=0x28099b519`. Its L1 points to an L2 with separate L3 tables for the
read-only image, the identity range containing inputs with a physical-framebuffer
hole, and the framebuffer aperture. The 4 KiB profiles retain their separate
read-only image and aperture tables. The generator self-test verifies both
granules' image permissions, absence of a physical framebuffer identity alias
and the 16 KiB aperture's expected physical pages.

Check the fixture generators without a compiler or emulator:

```sh
python3 -I kernel/experiments/immutable31af-test/run.py --self-test
```

Root owns execution in the isolated Linux build environment:

```sh
python3 -I kernel/experiments/immutable31af-test/run.py --payload build/immutable31af-link/payload.bin --layout build/immutable31af-link/layout.json --output build/immutable31af-runtime --qemu /usr/bin/qemu-system-aarch64
```

Omitting `--qemu` prepares and compiles the synthetic fixtures without running
them. The fixture bootstrap is separate code and is never packaged in the native
payload. The QMP transport is reused by reference from `translation31ab/run.py`;
The fixture sources, this description and transport hashes are recorded before
execution and rechecked afterward.

An optional `--old-payload` accepts only the frozen 31AE complete-payload SHA-256
`35bcecdff17ca1b927fccdffd057c9f149577df5698f250b7dbe93f5c71fe13b`.
The separate fixture installs its own vectors before handoff. That negative
control must capture a current-EL write-permission data abort at the old first
record-clear instruction, with FAR pointing to the old record, while the old
payload and framebuffer remain unchanged. The capture occupies only64 bytes of
fixture-owned synthetic scratch, outside the tested image. It demonstrates the
old code's dependency under this model; it does not diagnose the native 31AE boot.

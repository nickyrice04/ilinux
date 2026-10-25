# Complete 31AD instruction experiment

This original MIT fixture derives from the frozen 31AC harness and executes the
complete newly linked ordered payload with synthetic cold inputs in QEMU RAM.
Its new bootstrap enters at `0x40414000`; record, owned stack top and vector
checks use payload offsets `0x8000`, `0x14000` and `0x14800`. Argument and
translation-table fixtures retain their original independent addresses. The
payload must match its linked layout and expected geometry before execution.

All 26 meaningful 31AC cases are retained: eight paints, sixteen refusals and
two actual post-paint BRK faults. The harness verifies the full 64 KiB framebuffer,
exact marker pixels and complete write footprint, cache-clean coverage, argument
preservation, unchanged input/table bytes, actual captured execution profile,
stack/vector placement and fatal-vector return address. Only the two fault cases
replace the terminal park instruction with a test-only BRK. That mutation and
the bootstrap never belong in the native image. See `../visible31ac-test/README.md`
for the retained coverage and limits.

Root alone runs this with shared VM/quiet locks, existing GNU tools and QEMU/TCG
inside the isolated ARM64 Linux VM:

```sh
python3 -I kernel/experiments/visible31ad/run.py \
  --output build/31ad-linked --cc cc --ld ld
python3 -I kernel/experiments/visible31ad-test/run.py \
  --payload build/31ad-linked/payload.bin --layout build/31ad-linked/layout.json \
  --output build/31ad-execution --qemu /usr/bin/qemu-system-aarch64
```

Use a fresh, short absolute output path for the QMP socket. Each process has a
bounded deadline and closes on success or error. The runner binds its own two
sources and the original 31AB QMP helper, rechecking them at completion. No Apple
firmware, monitor service, disk, network or physical device is attached. This
tests original instructions under the documented model; native acceptance,
mapping permissions, guarded fault routing and scanout remain unestablished.

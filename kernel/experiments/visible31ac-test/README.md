# Complete 31AC instruction experiment

This original fixture executes the **same payload** packaged for the native
entry experiment. It supplies synthetic cold boot records, range tables and a
framebuffer in QEMU RAM. No Apple firmware, monitor service, disk, network or
physical device is attached. Its bootstrap configures only its own emulated
translation tables. Never include that bootstrap or those tables in a native
image.

The final 26 cases comprise eight successful paints, sixteen refusals and two
deliberate post-paint BRK exceptions. Successful cases cover ordinary EL2 and
VHE, 4 KiB and 16 KiB page tables, Normal-NC and Normal-WB framebuffer aliases,
and 30/32-bit pixels. The combinations are specified in `run.py`; this is not
an exhaustive Cartesian product. Optional D128-capability branches are not
execution-covered by this machine model.

The observer independently reads the owned record and full 64 KiB framebuffer.
It checks the actual captured execution profile, arguments, stack/vector address,
exact 32×16 pixel pattern and its complete write footprint. Cache coverage uses
an independently constructed set of touched line addresses. Every WB case must
complete all planned cleans; NC cases execute none. Refusals include unmapped
arguments/tables, invalid counts, wrong versions, wrapping ranges, a read-only or
missing later row, wrong PA, Device attributes and an alias of the image itself.
They must perform no paint or cache clean. Inputs and fixture tables stay
unchanged. Two test-only park-to-BRK mutations exercise new vector slot4 and
check its captured exception and return address after painting; other slots are
statically audited. Visible pixels alone therefore do not prove a terminal phase.

Inside the isolated ARM64 Linux VM, with existing GNU tools and QEMU/TCG:

```sh
python3 -I kernel/experiments/visible31ac/run.py \
  --output build/31ac-linked --cc cc --ld ld
python3 -I kernel/experiments/visible31ac-test/run.py \
  --payload build/31ac-linked/payload.bin --layout build/31ac-linked/layout.json \
  --output build/31ac-execution --qemu /usr/bin/qemu-system-aarch64
```

Use a short absolute output path for the Unix QMP socket. Root owns the shared
VM/quiet locks. The runner binds its two sources and the frozen original31AB QMP
helper, checks final source hashes and returns failure if that closure changes.
Each QEMU process has a bounded deadline and is closed on success or error.

This validates original instructions and behavior under the documented model.
Firmware acceptance, native mapping permissions, guarded fault routing and actual
scanout remain the specific questions for the reviewed physical experiment.

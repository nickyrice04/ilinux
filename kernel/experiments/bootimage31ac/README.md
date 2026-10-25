# 31AC native entry acceptance image

`image.py` packages the audited 147456-byte original payload into a 180224-byte
Mach-O. Data, stack, all initial executable code and the sixteen vectors remain
at their audited payload offsets. There are no pointer-fixup commands or Apple
implementation bytes. Its eight geometry tests and read-only `kmutil inspect`
result establish format behavior; actual firmware acceptance is the experiment.

```sh
python3 -I kernel/experiments/bootimage31ac/test_image.py
python3 -I kernel/experiments/bootimage31ac/image.py \
  --payload build/31ac-linked/payload.bin --output build/31ac-package
```

The actual payload is linked at two bases with identical bytes and executes in
the [complete original instruction fixture](../visible31ac-test/README.md).
The native image contains no synthetic page tables, bootstrap or BRK mutations.
It performs no monitor call or CPU release. It paints a small signature only
after bounded cold-record, range, permission, physical-address, cache and alias
checks; it then parks. A positive signature establishes entry into that store/
display path. An absent signature leaves several distinct causes unresolved.

Follow the [M1 handoff](../../../tools/m1n1-client/attempt31ac-instructions.md)
and the Git-pinned manifest in `native/boot/attempt31ac/`. The candidate must
temporarily replace the lab custom boot object to test the resident-monitor
handoff. That action and its Startup Disk/rollback sequence require the user's
explicit approval. No installation or boot selection is performed by this code.

# 31AE complete-payload emulator checks

The original 31AD 26-case suite is preserved, changing only record, stack and
late-park symbol offsets for 31AE. `bootstrap.S` is byte-identical to the 31AD
standard-QEMU fixture and is never included in the native payload. The complete
relinked payload executes with synthetic boot arguments, translations and
framebuffer storage. There are eight successful paints, sixteen complete
no-paint refusals, and two actual fatal-vector captures, across EL2 non-VHE/VHE,
4/16 KiB pages, 30/32-bit pixels and NC/WB cache paths. Entry, vector and body
placement and all case expectations remain unchanged.

Run only in an isolated Linux build environment with the existing GNU toolchain
and QEMU; this script starts one bounded emulator per case:

```
python3 -I kernel/experiments/visible31ae-test/run.py --payload build/visible31ae-link/payload.bin --layout build/visible31ae-link/layout.json --qemu /usr/bin/qemu-system-aarch64 --output build/visible31ae-runtime
```

The harness binds its own sources and the reused `translation31ab/run.py` QMP
transport, verifies payload/layout identity and exact symbols before execution,
compares immutable inputs and page tables, validates exact pixel footprints,
checks cache-clean coverage and captures actual exception records. Native
acceptance, native entry, Linux, SMP, GPU and performance remain NOT RUN.

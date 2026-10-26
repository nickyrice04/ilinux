# Offline entry-profile controls and evidence classification

These tools are original offline infrastructure. They generate no native image,
call no monitor service, access no host state and load no Apple firmware.
Frozen 31AF files remain unchanged. No new restart is authorized or recommended.

The existing diagnostic distinguishes outcomes in its terminal registers, but
the native screen-only test cannot retrieve those registers. This experiment
adds actual EL1 execution and a raw-argument ABI control to the unchanged
released instruction stream:

| Case | Context | Expected result |
| --- | --- | --- |
| EL2 resident cold | Existing full-mapping fixture | Complete 8192-pixel paint |
| EL1 resident cold | EL1h, translation disabled, SP=0 | Refusal status2, no pixel |
| EL2 raw argument | x0 holds BootArgs, x1/x2 zero | Refusal status1, no pixel |

The EL1 bootstrap deliberately uses no EL1 page tables. Frozen31AF should refuse
on CurrentEL before reading HCR_EL2, translating inputs or painting. PSTATE's
observed execution level is checked after parking; SP must remain zero. The
existing harness independently reads back all modeled payload/input/table/scratch
bytes and framebuffer contents. A5-populated reservation bytes model existing
monitor state; original instruction bytes and the on-disk payload remain unchanged.

These controls do not assert that native firmware supplies EL1 or the raw ABI.
They demonstrate finite silent outcomes if those assumptions differ. Register
visibility comes from QEMU's debugger; no equivalent native reader is qualified.
The task still needs an independently observable native loader/entry channel or
a working control for the same resident contract before another physical test.

Run host-safe classifier tests:

```sh
python3 -I kernel/experiments/entry31ag/test_classify.py
python3 -I kernel/experiments/entry31ag/classify.py native/boot/attempt31af-human-2026-10-26-result.json
```

Compile/emulate only inside the existing isolated Linux guest:

```sh
python3 -I kernel/experiments/entry31ag/run.py --payload /mnt/ilinux/build/research31af/job/out/link/payload.bin --layout /mnt/ilinux/native/boot/attempt31af/layout.json --output /mnt/job/out/entry --qemu /usr/bin/qemu-system-aarch64
```

The runner pins the exact payload and four frozen import/include/layout files,
then binds and rechecks all its own sources. The classifier consumes either the
direct-human31AF result or this exact emulator schema. It never promotes an
emulated paint or a human blank screen into native entry, pre-entry failure or
an Apple-only requirement. A human marker remains explicitly human-reported.
The classifier validates fields, **not report authenticity**; it is not a new
capture mechanism. Unknown or contradictory terminal states are refused.

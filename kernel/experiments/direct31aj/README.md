# 31AJ readable console collector

This is a new presentation variant of the original RAM-only collector, not an
edit to frozen 31AH/31AI/31AJ artifacts. `diag_init.c` derives from original
`direct31ah/linux/diag_init.c`, SHA-256
`53b75d25c01b03a1c92832df91c51b875f03616847cbc674cce1c539cc729761`.
The added header and helpers are original MIT code.

The change adds hand-drawn 3x5 glyphs rendered as ordinary ASCII `#`, space and
newline. Each horizontal pixel uses two console characters. There is no font
file/engine, escape sequence, cursor ioctl, framebuffer mapping, MMIO or backlight
access. Output uses the existing standard console stream. The existing kernel
font/display path determines the final size and contrast; neither is changed.

Six block-text lines show:

```text
31AJ
NATIVE T00
CPU18/18
CPU OK
RAM OK
TMR OK
```

The actual renderer enlarges those labels into at most **78 console columns and
35 rows** per panel, within a fixed 4 KiB buffer. `T00` is the existing loop's
**tick counter**, not measured wall-clock seconds. Status words are `WAIT`, `OK`,
`FAIL` and `TIME`. CPU count and CPU/RAM/timer status remain distinct. Partial
native execution can show `CPU01/18` and `CPU FAIL`; timer success on that one
created worker does not imply eighteen working cores. Generic controls are
labelled `VM`, with the actual worker target (for example `CPU04/04`). Synthetic
display samples are labelled `DEMO` and make no physical claim.

Rendering occurs only after the worker/RAM tests, through the existing
`camera_summary` calls at ticks 0, 5, ... 60. No worker/check calculation, deadline,
test buffer, sleep or loop timing policy changes. The panel is written directly
to stdout; the existing JSON/kmsg records and USB JSON-filter behavior remain
unchanged. Presentation failure emits an additional fixed `UNAVAILABLE` record
without converting a failed workload into a success. A complete panel is built
in memory before output, and inconsistent success/count inputs are refused.

The panel may scroll, interleave with kernel messages or be cropped by a small
terminal. Console writes add bounded output work; a loop tick is not a timing
measurement. No persistent screen placement, native legibility, camera exposure,
brightness control or performance parity is claimed. Existing camera evidence
qualifies moderate synthetic text only; fine kernel text remains a limitation.
An external native stop clock remains separate from this display counter.

## Offline tests and build

`test_collector.py` has four host-safe source-boundary methods. They verify the
immutable source hash and exact preservation of the workload/check/deadline
prefix and JSON/guard/liveness suffix after removing only the new presentation
hooks. They also check that display mode precedes PID-1/hardware handling and
that the renderer introduces no device/terminal-control access.

`test_readable.c` is original portable C. It tests dimensions, permitted bytes,
buffer sentinels, deterministic output, short-buffer refusal, invalid/partial
states, scope distinctions and status cases. Its assertion total includes each
output byte; that total is **not** a count of distinct test methods.

```sh
python3 -I kernel/experiments/direct31aj/test_collector.py
```

Job097 builds the Linux executable, relink object and new root in the existing
isolated VM. `--selftest` and `--selftest-timeout` retain their original semantics.
New `--display-test` prints four fixed synthetic panels from a normal process;
it performs no mounts, PID-1 operation, sleep, USB setup or native hardware work.
The parent owns VM lifecycle and the separate diskless/no-network control.

The kernel Image/config/DT remain the exact 31AH inputs. The executable, object,
initramfs and assembled candidate require **new** digests and delivery bindings.
Do not change old literal pins or claim the old generic VM result tests this new
binary. Full public glibc source/attribution closure remains incomplete; compiled
root/object delivery stays a same-user local handoff, not a public Release.

No native boot, camera session, security/default/volume change, firmware update
or installation is implemented or authorized by these files.

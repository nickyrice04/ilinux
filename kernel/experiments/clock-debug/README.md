# Attempt 7: isolate optional clock debug initialization

2026-10-14. **Offline validated; native attempt 7 NOT RUN.** Reuse the exact
boot025 payload. This change adds one fixed Linux argument:
`initcall_blacklist=clk_debug_init`. It is a temporary diagnostic workaround,
not an established root-cause fix or a change to hardware clock operation.

## Observation and analysis

[M1 attempt 6](../../../native/boot/stage-b-2026-10-14-attempt6-result.md)
reached native late initialization. The last visible call was
`clk_debug_init+0x0/0x120 @ 1` at 1.360189 s; the human reports an unchanged
screen until shutdown. No panic, diagnostic userspace or heartbeat was observed.
The last log line locates an observation boundary, not the blocking instruction.
Console visibility, scheduler/timer progress, debugfs allocation/locking and
clock debug registration remain possible causes.

The exact retained boot025 ELF reproduces its Image byte-for-byte. Its linked
`clk_debug_init` is 0x120 bytes and calls debugfs creation, takes the clock-debug
mutex, walks the debug list and sets the debug-ready flag. It does not initialize
the clock framework or directly change frequencies. Its helper creates per-clock
files and may invoke the provider's `debug_init` callback. The shipped Stage-B DT
declares one `fixed-clock` provider; that provider has no debug callback. Apple
NCO is a module and is absent from this diagnostic initramfs. These are static
configuration facts, not a reconstructed live clock list.

`clk_debug_register()` adds clocks to its list independently of this initcall;
with the debug-ready flag unset it does not create their debugfs files. Normal
clock registration, timer interrupts and consumer APIs remain available.
Clock diagnostic files will be unavailable for this test. We are not disabling
all debugfs, changing a clock driver, writing a frequency or removing a lock.

REA 6.4.0 / Ghidra 12.1.4 queried the exact `clk.o` in the isolated lab:
`clk_debug_init` and compiler helper `clk_debug_create_one.part.0` (Ghidra labels
the latter `clk_debug_create_one`). Both complete bodies and all high-pcode PCs
fit the ELF ranges. [audit.py](audit.py) checks **195 instruction words** with
independent LLVM and compares every nonrelocated word with the linked Image.
Relocation words are reviewed through linked disassembly and source. Ghidra's
incomplete call signatures are not accepted as verified prototypes.
[evidence.json](evidence.json) records hashes and limits. No macOS decompilation
is needed to investigate this generic Linux routine; no Apple code is copied.

The retained Linux `init/main.c` implements the exact-name blacklist before
the initcall-start trace and call. This Image has `CONFIG_KALLSYMS=y` and
`CONFIG_DEBUG_FS=y`; its init debug messages are compiled in. Therefore
`initcall clk_debug_init blacklisted` is the positive checkpoint. Do not expect
a `calling clk_debug_init` or matching `returned` line in attempt 7.

## Implementation and tests

The only live-behavior change is the extra fixed argument in
[launch.py](../../../native/boot/launch.py). Final prepared-DT validation still
requires the exact argument list. Four new regressions verify exact upload and
reject omission, a broader comma-separated list and an appended second skip.
There is no user-selectable arbitrary blacklist or argument override.

* **69 controller cases PASS:** launcher 35, descriptor 6, DAPF 16, framebuffer
  5, pinned parser 2, root ADT 4 and real pinned proxy serializer 1.
* **13 package files PASS**, unchanged archive/Image/config/DT/initramfs/m1n1.
* Exact boot025 Image and unchanged initramfs, diskless/networkless generic
  ARM64 VZ, one vCPU/4 GiB: precisely one blacklisted initcall, no execution of
  `clk_debug_init`, subsequent initialization, diagnostic PID 1, one CPU and
  **60.089095-second** liveness checkpoint PASS. Only console differs from
  native arguments (`hvc0` for VZ, `tty0` for the physical test).
* Prior no-blacklist VM baseline completed `clk_debug_init` normally. This
  test validates bypass behavior, not reproduction or resolution of the native
  hang. No new kernel compilation was needed because the Image is unchanged.

[validation.json](validation.json) records exact software and test boundaries.
[Job 026](../../../virtualization/jobs/026-clk-debug-skip/README.md) reproduces
the checks. Generic VZ has different interrupt/display/clock devices and does
not validate native M5 efficiency or clock behavior.

## Next physical evidence

Follow the [M1 checklist](../../../tools/m1n1-client/stage-b-instructions.md)
for one filmed human-started attempt 7. Keep the AIC workaround, one-core,
NVMe-off, cpufreq-off, DAPF and framebuffer safeguards. Collect the blacklist
checkpoint, subsequent last completed/called initializer, userspace/one CPU/
60-second liveness or first failure, then Macintosh HD return.

If the kernel advances but stalls elsewhere, do not keep blacklisting unrelated
initializers. A second debugfs-related stop would motivate shared allocator/
locking/timer analysis; absent screen output would require console evidence.
If userspace succeeds, prioritize a Linux-side control/input channel and usable
RAM userspace next. Restore clock debug support during focused diagnosis before
relying on its files for performance work. Native Omarchy, SMP, efficient idle,
GPU and peripheral support remain separate milestones.

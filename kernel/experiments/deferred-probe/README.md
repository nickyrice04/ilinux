# Attempt 8: identify the deferred-probe blocker without skipping driver work

2026-10-14. Boot027 is an original diagnostic change on top of boot025.
**Native attempt 8 NOT RUN. Root cause remains unknown.** The installed boot021
m1n1, lab entry, Stage-B DT, initramfs and boot policies stay unchanged.

## Evidence and decision

M1's [attempt-7 report](../../../native/boot/stage-b-2026-10-14-attempt7-result.md)
(`a2239f9`, result originally `e5f25a8`) establishes later native initcalls:
`boot_wait_for_devices` and `sync_state_resume_initcall` return 0, then
`deferred_probe_initcall` is last visible at 1.371769 seconds. No panic or
userspace heartbeat was observed. The exact blacklist message is not visible
in the photo; the controller verified the fixed argument. Do not infer a
precise blocking PC from the final printed call.

REA 6.4.0 / Ghidra 12.1.4 analyzed the exact boot025 `dd.o`, querying
`deferred_probe_initcall` and `deferred_probe_work_func`. Both full bodies and
all high-pcode PCs fit their ELF ranges. [audit.py](audit.py) checks **94 ARM64
instruction words** using Apple LLVM, and all 66 nonrelocated words match the
linked Image. The 28 relocation-bearing words were reviewed against linked
GNU disassembly and retained source. [evidence.json](evidence.json) pins the
object/Image and records limitations. No proprietary decompilation was needed.

The source/REA identify distinct boundaries: debugfs file creation, the first
trigger/flush of deferred work, and a second trigger/flush after optional
probe dependencies are relaxed. The worker takes a mutex, moves device PM
ordering, then invokes `bus_probe_device`. Debugfs creation is also present
at attempt 6's clock boundary. A driver, mutex/allocator, scheduling/interrupt
progress, or console visibility could explain the evidence. Advancing printk
timestamps only prove counter reads, not timer interrupt delivery.

Do not add another blacklist or claim an unobserved driver/timer fault.
Instead, make the next boot distinguish those cases. A root-cause repair
requires the resulting native observations. Public-source timer selection uses
the hyp physical timer under VHE; no evidence here supports rewriting that
route. The hardware check verifies its DT description, not physical delivery.

## Implementation

[apply.py](apply.py) applies only to the reviewed dd.c digest. It includes the
original [diagnostic helper](ilinux_probe_diag.h) and inserts checkpoints while
retaining both triggers, both flushes, locks, device lifetimes and probe calls.
The helper is inert unless the fixed `ilinux_probe_diag=1` argument is set.

* Reports J716c/t6050 compatibility separately from `generic-test`, EL1/EL2 and
  online CPU count. The native controller independently rejects other hardware.
* Requires one CPU and enabled interrupts. Samples the architectural counter
  for 100 ms with preemption disabled but interrupts enabled; checks jiffies
  advanced. A 100-million-iteration ceiling also bounds a frozen counter.
  It reports before re-enabling preemption, so a scheduling stop is distinguishable.
  The low three architectural physical/virtual timer control bits and IRQ/FIQ
  mask booleans are also reported, without implementation-defined registers.
  The pending bit is meaningful only for an enabled timer.
  Missing counter/ticks fails with an explicit diagnostic panic; no fallback
  timer, frequency write, security change or automatic reboot is attempted.
* A timer-softirq heartbeat reports main phase, worker subphase and retry count
  every five seconds, at most six times. It does not depend on the potentially
  blocked workqueue. It cannot report if interrupt/softirq/console delivery stops.
* The first 32 retries report bounded DT compatible strings before/after the
  probe. No raw DT, device name, addresses, registers or identifiers are logged.
  Later retries keep a numeric count. Normal completion shuts down the timer
  synchronously; later deferred work is not instrumented.
* Keeps the sole existing `clk_debug_init` skip. No new device is disabled.
* `native/boot/fdt.py` now validates t6050 root compatibility, observed CPU
  MPIDR/family sets, AIC3 core/event geometry and address translation, unique
  interrupt-controller phandle, and named host/guest timer routes, both offline
  and after m1n1 fixups. Existing board/chip/pin/secondary/DAPF/descriptor guards
  remain. This is a stricter description check, not proof of all driver support.
* Corrects the intake receipt's stale `next` text: it directs agents to the
  current Stage-B checklist instead of repeating entry provisioning/Stage A.

| Main phase | Meaning of the last entered boundary |
|---|---|
| 1 | Counter/tick check; inspect its following PASS/ticks or explicit panic |
| 2 | Tick check passed and watchdog armed |
| 3 | Entering `debugfs_create_file` |
| 4 | Debugfs returned; enabling/triggering deferred work |
| 5 | First `flush_work` entered |
| 6 | First flush returned |
| 7 | Second `flush_work` entered |
| 8 | Second flush returned; delayed retry setup follows |
| 9 | Deferred initializer complete; watchdog shut down |

Worker subphases in heartbeat: **0** not entered; **1** before initial mutex;
**2** holding mutex/list processing; **3** device PM move; **4** bus probe;
**5** bus probe returned; **6** reacquiring mutex; **7** worker returned.
A counter PASS with zero ticks is a timer-progress **failure**, not a pass.
A heartbeat establishes timer/softirq progress during the wait, not that the
blocked worker or display path is fully correct. A completed phase 9 without
visible userspace moves diagnosis beyond this initializer.

## Validation and reproduction

[Job 027](../../../virtualization/jobs/027-deferred-probe/README.md) copies the
retained boot025 tree inside the existing build VM; the earlier tree is not
modified. It runs **11 actual-helper scenarios with ASan/UBSan**, compiles the
full Linux 7.1.9 Image with GCC 16.1.1/binutils 2.46.0, confirms unchanged
16-KiB config, and compares ELF-to-Image bytes. Two local candidates were superseded to add worker subphase reporting and
architectural timer status; their outputs are retained.

The controller suite has **90 cases**: launcher 37, entry descriptor 6,
DAPF 16, framebuffer 5, hardware binding 19, real pinned ADT/DAPF 2,
root ADT 4 and real proxy serialization 1. Test receipt/VM results and hashes
are in [validation.json](validation.json). Only **Image** differs from boot025;
13-file intake is checked. No m1n1 replacement is built or installed.

Generic diskless/networkless VZ uses one CPU/4 GiB and the exact packaged Image
and initramfs (only console changes to hvc0). Require timer PASS/nonzero ticks,
phases 1–9, PID 1, online_cpus=1 and the 60-second heartbeat. It has no M5 AIC
and does not reproduce the native stop. Synthetic timer tests establish failure
handling/log bounds, not physical interrupt delivery. Timing changes may alter
the native symptom. No performance or efficiency claim is made.

Two preliminary local VM launches used an incorrect root subvolume/old kernel;
no native attempt occurred. They were stopped, and the established @ subvolume
and virtiofs-enabled kernel were used for successful source export and builds.

## Next

Follow the [current M1 checklist](../../../tools/m1n1-client/stage-b-instructions.md)
for one filmed RAM attempt. Fresh post-attempt-7 policies are already PASS:
original Full, lab Permissive. Preserve the installed setup and all prior
packages/results. If stable userspace is observed, next develop a Linux-side
USB/input/control channel and usable RAM userspace; the configuration agent
can then work toward Omarchy. GPU, storage, SMP and efficient idle/DVFS require
separate measured enablement. Do not restart installation from the beginning.

# Attempt 10: independent diagnostic framebuffer and context-switch checkpoints

2026-10-14. Boot029 is based on boot028. **Native attempt 10 NOT RUN; the
native hang is unresolved.** The implemented fix is to our diagnostic display
initialization, not a demonstrated scheduling/hardware fix or Omarchy boot.

## Evidence → decision

[M1 attempt 9](../../../native/boot/stage-b-2026-10-14-attempt9-result.md),
reviewed commit `29f0f8e`, contains paused-video observations: native J716c/t6050
EL2, one CPU, counter PASS/25 ticks, phases 1/10/11/12 and final
`reschedule pending=1 strip=0`. Phase 13, watchdog/stack and diagnostic userspace
are unobserved. The 21.598-second recording was sampled through 21.45 seconds,
not every frame or the whole 120-second window. Human return is confirmed.

Exact boot028 source and REA/Ghidra identify a **confirmed lifecycle defect**:
`fb_remap` returns without mapping when `fb_console` is absent or unregistered,
even when the independent status-strip diagnostic is enabled. Job 029 compiles
the actual previous function and reproduces the retired-console case. The
actual new mapper succeeds with absent, retired and active console fixtures.
This does **not** establish which prerequisite caused native `strip=0`; font,
DT or mapping failures were previously indistinguishable. New state reporting
separates them. No speculative idle, timer, register or security change.

REA 6.4.0/Ghidra 12.1.4 also analyzes exact `__switch_to`. Its result covers
296 of the ELF symbol's 420 bytes, omitting 31 instruction words associated
with alternatives/WARN control flow. Its pseudocode is not complete source.
[audit.py](audit.py) verifies full ELF/LLVM coverage for **152 instruction words**,
**126 nonrelocated words** against the deployed Image and bounded REA PCs.
The other 26 relocation-bearing words are reviewed against linked GNU
disassembly. LLVM decodes all words. [evidence.json](evidence.json) pins inputs,
coverage and limits. CPU alternatives can patch static NOPs at boot; neither
static result establishes the native feature selection or a faulty register.

The original context-switch checkpoints below follow the actual public kernel
source, including branches absent from the decompiler output. No Apple binary
extraction or proprietary code was needed to answer these questions.

## Implementation

[apply.py](apply.py) checks five exact boot028 source digests and unique anchors
before editing a new isolated VM copy. Earlier source/packages remain intact.

* [fb-map.h](fb-map.h) initializes from the existing strict flat-DT parser and
  font checks independently of early-console registration. With diagnostics
  enabled it never takes the console-list lock to decide whether it may map.
  Only the already validated framebuffer range is mapped, using the existing
  WC attributes. No guessed address, raw probe or GPU/firmware command.
* The same P/S/W/H strip uses **4× glyphs** for easier capture. Bounds account
  for the scale and reserve four font rows in our own console renderer. Another
  console owner may still overwrite it; a mapping PASS is not proof of scanout.
  `ilinux-display: state=N console_setup=N` reports preparation/mapping status.
  `console_setup` means our early-console setup ran, not that it is registered.
  The reschedule line repeats `display=N` if the earlier log has scrolled away.
* S adds subphases through generic `context_switch` and ARM64 `__switch_to`.
  Hooks store bounded scalars/render fixed cells, without printk, allocation,
  locks, new register accesses or scheduling-policy changes. They are inactive
  before/after the same single-CPU deferred-probe diagnostic interval.
* The pre-armed six-report watchdog, single stack, normal scheduler operations,
  driver probes, both flushes and sole `clk_debug_init` skip remain. Only the
  RAM **Image** changes; installed boot021, DT, config, initramfs, launcher
  arguments and every existing hardware/USB/DAPF/descriptor guard are unchanged.

## Decode the next native observations

Record literal hex strip values and the last printed decimal phase separately.
Do not report inferred zeros or equate a last boundary with an exact blocking PC.
The original P sequence remains `01 → 0A → 0B → 0C → 0D → 02 ... 09`.
P=0C precedes preempt_enable, P=0D follows its return. W/H are unchanged.

| Display state (decimal) | Meaning |
|---|---|
| 0 | No preparation outcome recorded |
| 1 | Eligible target/active framebuffer absent |
| 2 | DT/framebuffer properties rejected |
| 3 | Font missing or invalid |
| 4 | Display too narrow for enlarged strip |
| 5 | Permanent WC mapping failed |
| 6 | Mapping exists; visibility still requires the screen |

S=01–09 retain scheduler entry/lock/selection/context/finish/exit meanings from
[boot028](../schedule-boundary/README.md). New values are **hex**:

| S | Next source operation at this boundary |
|---|---|
| 10 | prepare_task_switch |
| 11 | arch_start_context_switch |
| 12 | Kernel/user MM handling |
| 13 | mm_cid_switch_to |
| 14 | rseq_sched_switch_event |
| 15 | prepare_lock_switch |
| 16 | switch_to |
| 17 | finish_task_switch after switch_to returned |
| 20 | debug_switch_state (DAIF validation) |
| 21 | fpsimd_thread_switch |
| 22 | tls_thread_switch |
| 23 | hw_breakpoint_thread_switch |
| 24 | contextidr_thread_switch |
| 25 | entry_task_switch |
| 26 | ssbs_thread_switch |
| 27 | cntkctl_thread_switch |
| 28 | ptrauth_thread_switch_user |
| 29 | permission_overlay_switch |
| 2A | gcs_thread_switch |
| 2B | actlr_thread_switch |
| 2C | DSB ISH |
| 2D | mte_thread_switch |
| 2E | Conditional SCTLR update |
| 2F | mpam_thread_switch |
| 30 | cpu_switch_to |
| 31 | cpu_switch_to returned to this thread |

Some capability-conditional operations are no-ops on a given CPU. S=07 is a
normal finish path for a new thread; S=31 is not required on its first start.
P/S values can update faster than the camera. A frozen mark brackets subsequent
work only if the display is still updating; it does not prove a register fault.
Combine it with the last main phase, changing H and any watchdog stack.

## Tests and boundaries

[Job 029](../../../virtualization/jobs/029-context-display/README.md) uses the
retained Linux 7.1.9/16 KiB config, GCC 16.1.1/binutils 2.46.0, `make -j2`.
Full Image link and ELF-to-Image comparison pass. ASan/UBSan run the actual
diagnostic helper and enlarged renderer, three font geometries/all four lanes,
padding/edge guards and rejected inputs. The actual parser/mapper uses retained
kernel libfdt with controlled I/O: **15 scenarios** cover console lifecycle,
generic/null DT, disabled framebuffer, invalid stride/format/font/size and
mapping failure. The previous mapper's defect is separately reproduced.

Linked mark functions call no printk/allocator/lock/sleep function (the renderer
retains its compiler stack-canary failure path). All normal switch operations
remain in source order. The physical mapping and video readability require
native validation. Marking adds overhead; no scheduling-speed or energy claim.

Exact packaged Image/initramfs pass a one-CPU/4 GiB diskless/networkless VZ boot,
phases including pending reschedule/phase 13, diagnostic PID 1 and 60-second
liveness. Generic `strip=0 display=1` is expected because VZ has no J716c DT or
scanout. The watchdog does not fire in that quick successful initialization;
its callback is shim-tested. [validation.json](validation.json) pins results.

Fresh post-attempt-9 user JSON: original Full/lab Permissive, exit 0 each.
Independent original root/build 25G83/FileVault/SIP/staged m1n1 checksum pass.
Default selection/installed boot object/authenticated-root were not re-queried.
No boot/security/volume/default changes or replacement of installed m1n1.

## Next

M1 follows the [attempt-10 checklist](../../../tools/m1n1-client/stage-b-instructions.md):
verify private boot029, publish readiness, then one filmed human-started RAM
boot. Capture display state and an enlarged strip frame, review the recording,
and return within the existing bound. If the kernel still stops, the next
repair must use that specific boundary, not another guessed driver skip.
Stable native PID 1/liveness precedes a Linux control/input channel and usable
RAM root for the configuration agent. GPU, SMP and efficient idle remain open.

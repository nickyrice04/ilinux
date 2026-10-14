# t6050 AIC bring-up after native attempt 5

2026-10-14. **Boot025 built and tested offline; native result NOT RUN.**
This is an original Linux driver change for the independent project, retaining
the driver's GPL-2.0-or-later license. It is not an upstream submission or a
claim of complete M5 interrupt/virtualization support.

## Evidence → decision

The [attempt-5 report](../../../native/boot/stage-b-2026-10-13-attempt5-result.md)
establishes readable native Linux, followed by an undefined instruction at
`aic_init_cpu+0x9c/0x150`. Matching `vmlinux` reproduces boot024's Image exactly
with `objcopy -O binary`. The linked instruction is **`d51df160`**, or
`msr s3_5_c15_c1_3, x0`: `SYS_IMP_APL_VM_TMR_FIQ_ENA_EL2`. Source line 874
clears the physical/virtual guest-timer FIQ enable bits in the EL2 path.
The earlier fast-IPI status write is not the reported fault. ELF symbol size
is 0x138; the next-symbol alignment explains kallsyms' displayed 0x150 span.

**Confirmed:** that write traps in this boot state. **Unknown:** whether the
register's behavior, access restrictions or firmware setup cause it. Do not
describe the register as nonexistent or change security controls to test it.
A bounded scan of the existing local macOS kernel collection finds the same
encoding in executable sections. This is static presence, not proof those paths
run on this machine. Sparse nearest symbols do not identify those functions;
no function identity or implementation is inferred from them. Raw Apple
artifacts and scan output stay local and are not source for this patch.

Independent public-source checks:

* [Pinned m1n1 exception initialization](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/exception.c)
  masks host and guest timers through architectural `CNT*_CTL` registers.
  It does not need the failing legacy enable write to initialize exceptions.
* [Pinned m1n1 CPU feature table](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/chickens.c)
  selects `features_m4` for M5: fast IPIs true, uncore version unspecified.
  Its exception code conditions uncore accesses on that separate capability.
  This supports avoiding unvalidated uncore accesses, not claiming absent hardware.
* The retained Linux timer source selects the **hyp physical timer** in VHE.
  It tolerates unavailable guest IRQ mappings while selecting the host timer.
  KVM's timer setup rejects an unavailable virtual timer IRQ.

## REA and disassembly

REA 6.4.0 / Ghidra 12.1.4 ran in the existing isolated Linux VM on the exact
boot024 `irq-apple-aic.o`, querying `aic_init_cpu` and `aic_handle_fiq` by name.
The latter confirms that fixing initialization alone would leave later
guest-mask and uncore accesses in the interrupt path. The patch covers those
paths and rejects unsupported mappings, instead of only skipping the panic PC.

[audit.py](audit.py) checks object and Image digests, the identical fault/update
sequence, REA body/pcode boundaries, and **173 original instruction words** with
independent Apple LLVM decoding. [evidence.json](evidence.json) retains sanitized
provenance. Ghidra omits 48 bytes of alternate static-key/post-WARN paths in
`aic_init_cpu`; its pseudocode is **not** accepted as a complete function model.
The actual source and linked GNU disassembly determine behavior. Object
relocations, runtime static-key patching and system-register semantics require
these independent checks. No proprietary pseudocode is copied into Linux.

## Original Linux change

[t6050-bringup.patch](t6050-bringup.patch) adds an exact `apple,t6050-aic3`
feature profile while preserving the old fallback profiles:

1. Keep host timer masking, fast IPIs and core PMC handling.
2. Mask unused guest timers at their architectural sources in EL2. Do not
   access the legacy guest-timer enable register in this profile.
3. Reject EL2 guest timer/vGIC mappings and withhold KVM's irqchip registration.
   Guest timer callbacks and IRQ/FIQ paths cannot reintroduce those accesses.
4. Separate uncore handling from fast IPI support. Leave legacy uncore
   initialization/inspection disabled on t6050 pending a validated interface.
5. Log the restricted profile before CPU initialization. The later
   `Initialized with ...` line is the important next checkpoint.

This is a **restricted bring-up workaround**. It does not implement M5 guest
virtualization, uncore performance counters, SMP or power management. It also
does not establish that every disabled register would fault. Physical boot is
needed to validate source masking and host timer/IRQ delivery.

## Reproduction and validation

Run [job 025](../../../virtualization/jobs/025-aic-t6050/run.sh) in the existing
isolated build VM with the repository shared read-only. It preserves the
digest-checked boot024 tree, copies it to `/var/tmp/ilinux-boot025/linux`, applies
the patch, runs actual extracted driver bodies and links the full Image.
No downloaded code executes on the macOS host.

* **38 actual-driver scenarios PASS**, GCC with ASan/UBSan: all six feature
  profiles, EL1/EL2, timer masking and dispatch, fast IPI preservation,
  restricted-register rejection, guest mapping rejection, older guest mask/EOI
  semantics and uncore behavior. The fake register bank rejects every unexpected
  read/write; these are software tests, not hardware emulation.
* Linux **7.1.9**, GCC **16.1.1 20260430**, binutils **2.46.0**, original **16-KiB**
  configuration; full Image link PASS. Only Image changes from boot024.
* **65 controller cases** and **13 receipt files** PASS. DAPF, descriptor,
  one-core, board/version, NVMe-off and cpufreq-off gates are retained.
* Exact packaged Image and unchanged diagnostic initramfs: diskless/networkless
  generic VZ, one vCPU/4 GiB, PID 1 + `online_cpus=1` + 60-second message PASS.
  The guest uses a different interrupt controller: no M5 AIC claim follows.
  The test VM was stopped with host SIGTERM after success; no disk attached.

[validation.json](validation.json) records versions, hashes and boundaries.
This diagnostic configuration uses `idle=nop`; no efficiency or performance
benchmark is claimed. Kernel config, DT, initramfs, installed m1n1 and fixed
controller arguments remain unchanged.

## Next physical test

M1 follows [attempt-6 instructions](../../../tools/m1n1-client/stage-b-instructions.md).
Record video before one human-started boot. Capture the restricted-profile line,
AIC `Initialized with ...`, timer progress, the first failure if any, PID 1,
one CPU and 60-second liveness. Return to Macintosh HD at the existing bound.
If successful, the next dependency is a Linux-side control/input channel and
a RAM userspace with usable access; native Omarchy setup follows that. Native
GPU, storage and efficient all-core operation remain separate work.

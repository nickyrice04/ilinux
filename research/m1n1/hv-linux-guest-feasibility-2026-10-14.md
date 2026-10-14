# m1n1 hypervisor as a Linux bring-up channel on J716c / t6050

2026-10-14 · M1 agent (Claude), offline and read-only. **No target connection,
no m1n1 code executed, nothing installed, built or committed.** Native and
hypervisor behavior on this machine: **NOT RUN.**

**Scope and conditions.** `third_party/m1n1/AGENTS.md` states that m1n1's
maintainers forbid any use of AI/LLM tools with the project. The user was shown
that notice and authorized reading the pinned source for this private study
only (2026-10-14). This document is LLM-produced: do not contribute it, or
anything derived from it, upstream or to Asahi channels (see also
`research/asahi/asahi-status-m5-2026-10.md`). m1n1 is GPL-2.0-or-later since
2.0.0 (`README.md:85-90`, earlier code also MIT). A privately modified build is
fine for private use; distributing one carries GPL obligations.

Source pin: `third_party/m1n1` at `57a9339ffd1876e78297b17d34dece8cff8fa1ba`,
the same revision as installed boot021. Paths below are relative to that clone
unless they start with a project directory.

## Verdict

* **Not usable off the shelf on this machine.** Unmodified m1n1 would stop
  before Linux prints anything, for two independent reasons:
  1. Hypervisor init starts every secondary core. The project forbids that,
     and m1n1 cannot start t6050 secondaries (B-001).
  2. Every return to the guest writes the guest-timer FIQ enable register,
     the exact instruction that trapped as undefined at EL2 in native attempt 5.
* **Feasible with a small private m1n1 change set**, loaded into RAM by
  chainload, with no boot-policy, security, volume or installed-m1n1 change.
  Several register behaviors are unknown and could each cost a session.
* **Payoff if it works:** the full kernel log streamed to the M1 over the
  existing cable, an interactive serial console, Ctrl-C into a debugger shell
  with symbolized backtraces, a GDB stub, and MMIO tracing of chosen devices
  such as the GPIO controllers. That is roadmap order 3 (an observable control
  channel) without any Linux USB driver.
* **Recommendation:** not the next step. Boot034's cheap diagnostics come
  first (built-in stall detectors, panic log drawn directly on screen, GPIO
  driver loaded after userspace). If the hang is still opaque, or when bring-up
  moves to new drivers, run one read-only register census session (§5, H1) to
  price the hypervisor work before writing it.

## 1. What a Linux guest needs, and what breaks on t6050

| Hypervisor step | Code | t6050 status | Label |
|---|---|---|---|
| Host init starts all secondaries | `src/hv/hv.c:136` calls `smp_start_secondaries()` unconditionally. With locked sysregs, `src/smp.c:165-169` prints that RVBAR is locked and differs, then still writes CPU_START (`src/smp.c:189-196`), releasing cores at the locked RVBAR. | **Blocker.** Violates the launcher's no-secondaries gate; t6050 secondaries do not start (B-001). | Confirmed (code, project rule) |
| Guest timer FIQ gating | `hv_update_fiq()` (`src/hv/hv_exc.c:152-180`) does read-modify-write of `SYS_IMP_APL_VM_TMR_FIQ_ENA_EL2` = `sys_reg(3,5,15,1,3)` (`src/cpu_regs.h:749`). Called on every exit to the guest (`hv_exc.c:452`, also `:538`, `:614`). | **Blocker.** Attempt 5 trapped on `msr s3_5_c15_c1_3, x0` (`d51df160`) at EL2 (`kernel/experiments/aic-t6050/README.md:10-19`). m1n1 runs at EL2 in the same boot. | Likely (strong) |
| Guest CPU-start interception | `proxyclient/m1n1/hv/__init__.py:1560-1572` hooks CPU_START only for chip IDs up to 0x6041; t6050 logs `CPUSTART unknown for this SoC!` (`:1571`), so guest writes reach PMGR. A guest m1n1 calls `smp_start_secondaries()` before kboot (`src/payload.c:316-318`). | **Blocker** for upstream's `run_guest_kernel.sh` flow. | Confirmed (code) |
| SPRR/GXF emulation | Enabled whenever `apple_sysregs_unlocked` is false (`hv/__init__.py:1365-1368`), which is true for M4 and M5 parts (`src/chickens.c:111-116`, `:164-167`). `run_guest.py:49-52` also raises the m1n1 heap to 1 GiB. It traps guest TLB maintenance (`hv_exc.c:209-214`). Built for XNU with SPTM. | Not needed for Linux; disable with the Python attribute. | Likely |
| Apple registers read at start | `hv_start()` reads AMX_CTL_EL2, APVMKEYLO/HI_EL2, APSTS_EL12, ACTLR_EL12, CNTHCTL_EL2, SPRR_CONFIG_EL1, GXF_CONFIG_EL1 (`hv.c:213-234`) without an exception guard. | Unknown in raw boot mode (`research/asahi/asahi-status-m5-2026-10.md:157`, `:161`). | Unknown |
| Apple registers written at init | HACR_EL2 trap setup (`hv/__init__.py:1419-1431`), ACTLR_EL12 (`:1457-1461`). These go through guarded proxy calls (`proxyclient/m1n1/proxyutils.py:228-236`), so a synchronous trap aborts init cleanly before guest start. | Unknown | Unknown |
| Per-exception PMU and IPI registers | PMCR0 save/restore (`hv_exc.c:443-446`, `:454`), fast-IPI registers (`hv_exc.c:312-317`, `:379-400`). Linux's t6050 AIC profile uses both at EL2 and attempts 6-13 passed AIC init. | Probably fine | Likely |
| Timer virtualization (ECV) | ECV traps used if `ID_AA64MMFR0_EL1` bits 63:60 are nonzero (`hv.c:158-171`). | Not recorded in the hardware inventory | Unknown |
| Hypervisor watchdog | Runs on a second live core (`src/hv/hv_wdt.c:150-161`); started only when `wdt_cpu` is set (`hv/__init__.py:1998`). | Unavailable on one core; not a blocker | Confirmed (code) |

**Guest-timer fix direction (Hypothesis).** Read the register first; reads
succeeded in attempt 5. The value shows whether guest-timer FIQs are enabled by
default. Then either mask the guest timer at its architectural source
(`CNTV_CTL_EL02`/`CNTP_CTL_EL02` IMASK) while a virtual FIQ (HCR_VF) is
pending, keeping the guest-visible value shadowed through the existing ECV
traps (`hv_exc.c:220-226`), or poll guest timer status from the 1 kHz
hypervisor tick (`hv.c:18`, `:492-503`). This mirrors the project's own Linux
AIC profile, which masks guest timers at their architectural sources.

## 2. Virtual UART on J716c

* The ADT has `/arm-io/uart0` (`uart-1,samsung`, `0x305200000+0x4000`,
  IRQ 1359) with a `debug-console` child (`hardware/adt/adt-nodes.tsv:367-368`).
  The Stage-B DT has `/soc/serial@505200000`, `apple,s5l-uart`, IRQ 0x54f
  (1359), status okay, alias `serial0`. **Confirmed.**
* `map_vuart()` (`hv/__init__.py:1465-1472`) hooks that MMIO page.
  `hv_map_vuart()` (`src/hv/hv_vuart.c:144-150`) routes it to
  `IODEV_USB_VUART`, the second CDC-ACM function of the same m1n1 USB device
  (`src/usb.c:231-232`, `:254`, `:396-401`). The project already records it as
  data interface 3, next to the primary data interface 1
  (`tools/m1n1-client/usb_identity.py:31-32`). **Confirmed.**
* It is bidirectional. Guest UART writes go to the M1 (`hv_vuart.c:95-99`);
  bytes from the M1 are readable by the guest (`hv_vuart.c:111-118`). With a
  shell in the initramfs this is an interactive console. **Confirmed (code).**
* Interrupt-driven RX/TX uses AIC software-set (`hv_vuart.c:44-51`). m1n1
  supports AIC3 (`src/aic.c:38-40`, `:163`), but this path is untested on
  t6050. **Likely**; polled earlycon output does not depend on it.
* The physical UART is not externally reachable on laptops
  (`kernel/native-enablement/plan.md:234`). That does not matter here, because
  the hypervisor intercepts the page.
* Host side: today's launcher deliberately opens only the primary port. A
  session would add a read-only logger for interface 3, using pyserial from
  the existing client venv (`tools/m1n1-client/README.md:24-27`).

## 3. Kernel, DT and command line for an EL1 guest

There are two ways to start Linux under the hypervisor:

* **A. Upstream flow** (`proxyclient/tools/run_guest_kernel.sh:59-92`). It
  chainloads a fresh m1n1 host, then runs a guest m1n1 with the DTB, Image and
  initramfs appended. The guest m1n1 runs `payload_run()`, which starts
  secondaries (blocker above), then kboot at EL1. It also bypasses the
  launcher's guarded DAPF and framebuffer preparation. The attempt-3 DAPF
  handoff fault would need the same correction applied to the guest's ADT copy.
* **B. Host-prepared kernel (project style).** Reuse the launcher's validated
  kboot DT preparation. Then start the kernel through `P_HV_START`
  (`src/proxy.c:499`) with x0 = FDT, as `kboot_boot()` does for EL2
  (`src/kboot.c:2949-2954`), instead of jumping. This keeps every existing DAPF,
  framebuffer and GPIO gate and needs no guest m1n1. It needs custom host
  scripting, because `HV.load_raw()` is XNU-shaped (boot args, SEPFW,
  TrustCache; `hv/__init__.py:1707-1760`). **Hypothesis; preferred if pursued.**

Guest specifics:

* **AIC.** The project's t6050 profile rejects guest-timer mappings only in hyp
  mode (`kernel/experiments/aic-t6050/t6050-bringup.patch:138-145`). At EL1 the
  virtual timer should map normally. **Likely, untested.**
* **Console.** Add `earlycon=s5l,mmio32,0x505200000 console=ttySAC0,115200`
  and keep the framebuffer console and panel.
* **Keep** `maxcpus=1 nr_cpus=1 idle=nop arm64.nowfxt`. This configuration
  does not trap guest WFI: HCR from `hv.c:144-150` and
  `hv/__init__.py:1405-1416` has no TWI/TWE. On M4 and later, WFI can lose
  state (`research/asahi/asahi-status-m5-2026-10.md:162`).
* **Not identical to native.** EL1 under the hypervisor has a different timer
  source, injected FIQs, trapped registers and adjusted time (CNTVOFF,
  `hv_exc.c:455`). Driver-logic hangs such as the GPIO probe or a workqueue
  stall should reproduce; EL2/VHE-specific behavior will not. Never benchmark
  under the hypervisor.

## 4. Extra code that would run on the M1

* **Today:** `native/boot/launch.py` uses only m1n1's proxy and serializer, a
  narrow surface.
* **A hypervisor session would add** `proxyclient/m1n1/hv/__init__.py` (2,009
  lines) and its imports (`trace`, `gdbserver`, `virtio`, `sprr`, `impdef`),
  `proxyutils` (assembles helpers with the project's LLVM), `run_guest.py` or a
  custom equivalent, and `chainload.py` to load a modified m1n1 into RAM. All of
  it is GPL Python from the pinned clone, run in the existing venv. The
  hypervisor imports already pass offline (`tools/m1n1-client/README.md:26`).
* **A modified m1n1 binary** built from source: C changes in
  `src/hv/hv.c` and `src/hv/hv_exc.c`, Python changes in
  `proxyclient/m1n1/hv/__init__.py`.
* **Needs explicit user approval** under AGENTS.md (third-party code outside a
  VM, new live procedure). No new host install is expected.

## 5. Bounded test plan

### H1: register census (one short session, no Linux, no hypervisor start)

* **Preconditions:** as for Stage A/B. The human starts the iLinux Boot Lab and
  the proxy is running. Macintosh HD stays default at Full Security, installed
  boot021 is unchanged, and no secondaries are started.
* **Reads only**, each through `ProxyUtils.mrs` under the exception guard
  (`proxyutils.py:178-188`, `:228-236`; a synchronous trap is skipped and
  reported):
  * `ID_AA64MMFR0_EL1` (ECV)
  * `VM_TMR_FIQ_ENA_EL2`
  * `HACR_EL2`
  * `AMX_CTL_EL2`, `APVMKEYLO_EL2`, `APVMKEYHI_EL2`, `APSTS_EL12`
  * `ACTLR_EL12` and the IMPDEF variant
  * `SPRR_CONFIG_EL1`, `GXF_CONFIG_EL1`
  * `CNTHCTL_EL2`, `CNTV_CTL_EL02`, `CNTP_CTL_EL02`
* **No writes at all.** Attempt 5 already answers the timer write. HACR and
  ACTLR writability surfaces in H2's guarded init, where a synchronous trap
  aborts cleanly; an SError would not.
* **Stop** after the list, or on any SError or hang: power off and return to
  Macintosh HD.
* **Output:** a sanitized table of register, readable or trapped, and a value
  class only (no identifiers or raw dumps). It decides whether the change set
  is §1's three blockers plus SPRR-off, or larger.
* **Risk:** an asynchronous SError from a read hangs m1n1; recovery is a power
  off, as with current RAM-only attempts. The research notes report SErrors
  from locked-register writes on M4 and later, not reads (`:161`).

### H2: hypervisor bring-up (only after H1 and separate user approval)

1. Build a private m1n1 variant with:
   * a single-CPU hypervisor (no secondary start on t6050);
   * guest-timer delivery without `VM_TMR_FIQ_ENA_EL2`;
   * SPRR emulation off for Linux guests;
   * a no-op CPU_START hook for chip 0x6050 (offset as `src/smp.c:336-338`).
   Chainload it into RAM over the proxy; installed boot021 stays untouched.
2. Start the current package's Image, DT and initramfs by path B with the
   vUART console arguments. Log interface 3 on the M1 and film the screen as
   usual.
3. Pass signals, in order:
   1. "Jumping to entrypoint";
   2. the first kernel line on the vUART;
   3. advancing printk timestamps;
   4. Ctrl-C reaches the hypervisor shell, and `bt` is symbolized with
      `System.map` (`hv/__init__.py:1269`, `:625`);
   5. Ctrl-D resumes the guest.
4. Stop on any EL2 exception, guest panic, 120 seconds or the first failed
   signal. Return to Macintosh HD.
5. Then trace the main GPIO controller with `trace_device`
   (`hv/__init__.py:273`) to see the exact MMIO access where the probe stalls.
   The GDB stub (`:426-437`) allows source-level kernel debugging.

## 6. Compared with the cheaper boot034 changes

| Option | Cost | What it gives | New risk |
|---|---|---|---|
| Built-in stall detectors plus panic log drawn directly on screen | Kernel config and command line | Stuck task's symbolized stack and workqueue state in one photo | None new |
| GPIO driver as a module, loaded by diagnostic init after PID 1 | Small init and config change | Userspace milestone plus the exact GPIO hang stack | Low |
| H1 register census | One ~5-minute proxy session | Prices the hypervisor work | Low |
| H2 hypervisor | m1n1 C/Python changes, chainload procedure, likely 1-3 sessions | Live log, shell, debugger and MMIO tracing for all later bring-up | Moderate: unknown traps, EL1 differs from native EL2 |

## Sources

* Pinned m1n1 (`57a9339`): `src/hv/hv.c`, `src/hv/hv_exc.c`,
  `src/hv/hv_vuart.c`, `src/hv/hv_wdt.c`, `src/smp.c`, `src/payload.c`,
  `src/kboot.c`, `src/proxy.c`, `src/usb.c`, `src/chickens.c`,
  `src/cpu_regs.h`, `proxyclient/m1n1/hv/__init__.py`,
  `proxyclient/m1n1/proxyutils.py`, `proxyclient/tools/run_guest.py`,
  `proxyclient/tools/run_guest_kernel.sh`, `README.md`, `AGENTS.md`.
* Project: `kernel/experiments/aic-t6050/`, `kernel/native-enablement/plan.md`,
  `hardware/adt/adt-nodes.tsv`, `tools/m1n1-client/usb_identity.py`,
  `tools/m1n1-client/README.md`, `native/boot/launch.py`,
  `research/asahi/asahi-status-m5-2026-10.md`, Stage-B DT in the boot032 package.
* Public: https://asahilinux.org/docs/sw/m1n1-hypervisor/ (cited from
  `tools/m1n1-client/README.md`; not re-fetched for this study).

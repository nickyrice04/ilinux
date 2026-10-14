# hv002: boot033 under a private m1n1 hypervisor

2026-10-14, M5 agent. **Private iLinux tooling. Never contribute it or anything
derived from it to m1n1/Asahi.** m1n1's AGENTS.md/CLAUDE.md forbid LLM use; the
user authorized private use. **Native/hypervisor behavior: NOT RUN.**
hv002 replaces hv001 (release `native-j716c-hv001`, kept for the record).

## Why hv001 could not work

* **Timer interrupts.** The H1 census (`census-2026-10-14-result.md`) found
  `VM_TMR_FIQ_ENA_EL2` = **ENA_V=1 ENA_P=1**, and attempt 5 showed writes to it
  trap at EL2.
  * hv001 assumed those bits would be clear and only polled guest timers.
  * With them set, a guest timer that fires unmasked raises a physical FIQ the
    HV cannot gate. The guest would re-trap forever.
  * hv001's gate correctly refused to start, so nothing unsafe ran.
* **Uncore registers.** A later M5 review found a second defect the census did
  not cover: the HV FIQ handler read the uncore PMU registers `UPMCR0`/`UPMSR`
  unconditionally on every tick.
  * m1n1's own `exception.c` only touches them when
    `cpu_features->uncore_version` is set; `features_m4`, which M5 uses, leaves
    it unset.
  * The project's Linux t6050 AIC profile avoids them too.

## hv002 m1n1 change set

`0001-ilinux-hv-t6050-hv002.patch` against pinned `57a9339`: 155 lines added,
7 removed, 7 files.

| Area | Change |
|---|---|
| CPUs | `hv_init()` starts no secondaries when `chip_id == T6050`. |
| Guest timers | `VM_TMR_FIQ_ENA_EL2` is only read (logged). When a guest timer is expired, enabled and unmasked, `hv_update_fiq()` sets its `IMASK` (masking the FIQ at its source), records that in a per-CPU flag, and injects `HCR_VF`. Timer FIQs now arrive immediately instead of within 1 ms. |
| Guest view | With ECV, guest `CNTV_*`/`CNTP_*` accesses trap (`EL1TVT`, `EL1PTEN` clear). Reads of `CTL` hide the HV's mask. Any guest write to `CTL` ends it, and `CVAL`/`TVAL` re-arms restore the guest's `IMASK`. If the counter steps back, the mask is also lifted. Every handled trap re-runs `hv_update_fiq()`. |
| Gate | `hv_init()` sets `hv_ilinux_init_failed` (`hv_start` refuses) only when **ECV is missing**, because the shadow needs the traps. The census found ECV=1. |
| Handoff | `hv_start()` turns both guest timers off (`CTL` = 0) and clears the flags before entry; the census found them left expired (`ctl=7`). |
| Uncore | The FIQ handler's `UPMCR0`/`UPMSR` block runs only when `cpu_features->uncore_version` is set, as in `exception.c`. |
| Private op `0x7f0` | Unchanged: `kboot_prepare_hv_guest` runs `mcc_enable_cache`, `tunables_apply_static`, `clk_init`, `dapf_init_all`; no USB/PCIe init. |

**Build** (job 035, VM): `m1n1-hv.bin` SHA-256 `f3ed8705…758b`.

* Patch: the build used the repo patch, SHA-256 `ecde6b2b…b11e`
  (`toolchain.txt`).
* Offsets: marker `ilinux-57a9339-hv002` at 527024, `dt` pointer at
  `0x116538`, `hv_ilinux_init_failed`/`single_cpu` at `0x35a558`/`0x35a559`.
* Warnings: no C warnings. The one Rust notice also appears in the stock
  build.
* DAPF: the table, paths and functions sit at the same offsets as boot021, so
  the reviewed guard verifies hv002 with only its image-hash pin swapped.

## How hv002 was verified (offline)

* **Machine code, `hv_exc.o` disassembly** (job 035):
  * The enable-register writes are reachable only on the non-t6050 branch.
  * The t6050 path masks and restores `cntv/cntp_ctl_el02` and computes
    pending exactly as designed.
  * The trap handlers shadow `CTL` and clear the mask on `CTL`/`CVAL`/`TVAL`
    writes.
  * `UPMCR0`/`UPMSR` are reached only after `cpu_features->uncore_version`
    tests nonzero.
* **Machine code, final binary** (`hv_init`/`hv_start`, via an ELF wrapper):
  * `hv_init`: `chip_id == 0x6050` skips `smp_start_secondaries`, and
    single-CPU without ECV sets the failure flag.
  * `hv_start`: the failure check runs before `hv_ilinux_timers_reset`.
* **Timer model test** (`test_timer_model.c`):
  * Setup: the exact timer block is extracted from the patch, compiled with
    ASan/UBSan, and run against simulated timers whose FIQ enables are stuck
    on. Each HV exit must leave the physical FIQ line low, and the guest must
    see its own `CTL`.
  * Scenarios: arm/expire/deliver/ack/re-arm; re-arm through `CVAL` and through
    `TVAL`; `CVAL` into the past; disable while masked; guest-masked expiry;
    both timers at once; counter stepping back.
  * Mutation check: removing the source mask, the guest-view shadow or the
    re-arm restore each makes it fail.

## Host launcher (`hv_launch.py`, study path B)

1. Same gates as `native/boot/launch.py` on the installed boot021: chip,
   marker, no secondaries. **New:** the guarded register census (`hv_regs.py`)
   runs in the same boot before anything is chainloaded, and any blocker stops
   it.
2. Chainload of hv002 into RAM. It mirrors upstream `chainload.py -r`, never
   writes RVBARs, and uses a pre-assembled stub checked against clang. The port
   is reopened, NOP-verified, and the hv002 marker and no-secondaries state
   re-checked.
3. `HV.init()` runs with SPRR emulation off. The launcher then reads the
   `hv_ilinux_*` flags and **stops** unless single-CPU mode is on and ECV was
   found.
4. The same DT gates as boot033 apply. Differences from native:
   * `console=ttySAC0,115200` before `console=tty0`, and
     `earlycon=s5l,0x505200000`. `/dev/console` stays the framebuffer; printk,
     including diag init's kmsg copies, also reaches the vUART (polled).
   * No `stdout-path`.
   * Linux RAM starts above the HV heap. The payloads must not overlap
     reserved memory or the framebuffer.
5. RAM outside m1n1 is identity-mapped as `HV.load_raw()` does, minus the TZ
   carveouts. `CPU_START` (`0x280688000`) writes are dropped, behind a RESERVED
   tracer.
6. Upstream `map_essential()` keeps the HV link's PMGR domains on. For a USB0
   link: UART0, UART_P, SIO, FAB8_SOC, FAB0_PIOGW, ATC0_USB, ATC0_COMMON,
   FAB3_SOC and ATC0_USB_AON, at addresses decoded from the M5 ADT. Guest
   writes to them are held on and logged as "Dangerous write".
7. `hv_start(kernel, x0=DT)`.

Same payloads as attempt 14 (boot033 Image/DT/initramfs, unchanged). Never
benchmark under the HV.

## Validation

* `python3 -I native/hv/test_hv_launch.py`: **34 PASS** (also via
  `python3 -m unittest`). Covers:
  * the timer model above;
  * census v2 rules: set FIQ enables pass; missing ECV or a trapped
    `PMCR0`/`IPI_SR` block; unused registers are informational;
  * launcher preflight;
  * rejection of a non-hv002 symbol table;
  * all hv001-era launcher checks: layout, memory rewrite, overlap,
    `System.map`, flags, CPU_START tracer, reconnect, chainload, gate order,
    package tamper/offsets, vUART.
* Pure `native/boot` suites PASS; reviewed boot files unchanged.
* After boot034, `native/boot/package-manifest.json` describes the newest
  package, so the launcher now selects the repository manifest that matches
  the guest package's own name and contents (`boot033-package-manifest.json`
  for the boot033 guest). `launch.py` and its reviewed digest are unchanged.
* Chainload analysis and the planned hardening (hv003):
  `hv002-chainload-analysis-2026-10-14.md`.
* **Not verified on M5:** M1 client-venv imports (M1 readiness).

## Known risks / unknowns

* **ECV trap behavior.** If Apple's ECV does not trap EL1 timer accesses as the
  architecture specifies, the guest would read the HV's `IMASK` after its first
  timer expiry and loop in its FIQ handler. The HV stays responsive: stop with
  Ctrl-C, run `bt`, power off and report.
* **Untested on t6050 (upstream code):**
  * vUART interrupt delivery through AIC3;
  * USB re-enumeration after the chainload;
  * `hv_init`'s `pcie_shutdown`/`usb_hpm_restore_irqs`;
  * guest PMU/IPI register emulation.
* An asynchronous SError hangs m1n1; recovery is a power off.
* EL1 under the HV is not native EL2: different timer path, injected FIQs,
  1 kHz tick. VHE-specific or timing-sensitive faults may not reproduce.
* Job 034 (hv001) is history; its script refers to the removed hv001 patch.

## Files

| File | SHA-256 |
|---|---|
| `0001-ilinux-hv-t6050-hv002.patch` | `ecde6b2b9342c91d55b0254217bd940adde234837d23927dee381eea3ad9b11e` |
| `hv-manifest.json` | `89e7112da29c89e36c104761d27d8825dffbfad80803284ee96dcddeba6c8cdd` |
| `hv_launch.py` | `b4b3656e7a6bbd88f20fc00a22632ec66e5778054c320ad2514d76bd405d7584` |
| `hv_regs.py` | `3545bfcaa17b8187be65a2051c36afadcdc384906174f425884a4f8330bc1456` |
| `census.py` | `3a7f9f7dd320ecb12f19fca804a641e82bfdbfb3334660290ebf571978f8a6bf` |
| `vuart_log.py` | `08d4d6510f960a0b1d653ec80160ffa6ced359a7cea056b4f3c7d635cc4c9d6a` |
| `test_hv_launch.py` | `fa5c1360ae1535f58f88fafa006b02b962a16e1293010480d385a680c21d33f2` |
| `test_timer_model.c` | `ad3bad419aef1ef2929ffadd74ef7f55390122ffcbb141f0cbd0356f2d5e4f3d` |
| Release `native-j716c-hv002`, `ilinux-j716c-hv002.tar.gz` | `c79ffded48bebc580734918c1540fd589937d5440e2a385a65186c801f2c4254` |

M1 procedure: `tools/m1n1-client/hv-instructions.md`.

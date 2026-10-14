# hv001: boot033 under a private m1n1 hypervisor

2026-10-14, M5 agent. **Private iLinux tooling. Never contribute it or anything
derived from it to m1n1/Asahi.** m1n1's AGENTS.md/CLAUDE.md forbid LLM use; the
user authorized private use. **Native/hypervisor behavior: NOT RUN.**
Reviewed a second time before handoff. Fixes from that pass are listed under
"Review pass".

## Why

Attempt 14 reached PID 1 and then the SoC reset silently ~5.6 s into
userspace, with no message. Photos of a panel cannot show what happened last.
Under the hypervisor the M1 gets:

* the kernel log live on the virtual UART (USB interface 3);
* Ctrl-C into the HV shell, with backtraces symbolized from `System.map`;
* optional MMIO tracing from that shell, e.g. `trace_device("/arm-io/pmgr")`.
  That tracing records PMGR writes, which bears on attempt 14's top hypothesis
  (domains switched off at `sync_state`).

The vUART is bidirectional. A later initramfs with a getty on `ttySAC0` would
give an interactive console; boot033's diagnostic init has no shell.

## m1n1 change set

`0001-ilinux-hv-t6050-single-cpu.patch` against pinned `57a9339`: 53 lines
added, 1 removed, 7 files.

| Study blocker | Change |
|---|---|
| `hv_init()` starts all secondaries | Skipped when `chip_id == T6050`. The live gates read chip ID 0x6050 on this machine. |
| `hv_update_fiq()` writes `VM_TMR_FIQ_ENA_EL2`, which trapped at EL2 in attempt 5 | On t6050 the register is only **read**. If either enable bit is already set, `hv_ilinux_init_failed` is set and `hv_start` returns without starting. Guest timers are level-evaluated on every exit and on the 1 kHz HV tick, then delivered as a virtual FIQ. Timer latency is ≤ 1 ms. |
| Path B needs kboot's hardware steps without a jump | New private proxy op `0x7f0` (`kboot_prepare_hv_guest`): `mcc_enable_cache`, `tunables_apply_static`, `clk_init`, `dapf_init_all`. `usb_init` and `pcie_init` are skipped. The boot033 DT has **no USB, PCIe or SPMI nodes**, so Linux uses neither. |

**Build** (job 034, VM): `m1n1-hv.bin` SHA-256 `6d031661…85ac`.

* Offsets: marker `ilinux-57a9339-hv001` at 527000, `dt` pointer at `0x116538`,
  `hv_ilinux_init_failed`/`hv_ilinux_single_cpu` at `0x35a558`/`0x35a559`.
* Warnings: no C compiler warnings. The one Rust future-compatibility notice
  also appears in the stock boot021 build log (job 021).
* DAPF: the table, its paths and its function offsets are identical to
  boot021; only the image hash differs.

## Host launcher (`hv_launch.py`, study path B)

1. Same gates as `native/boot/launch.py` on the installed boot021: chip,
   marker, no secondaries.
2. Chainload of hv001 into RAM. It mirrors upstream `chainload.py -r` and never
   writes RVBARs; upstream also skips them for a raw image at the same base.
   The stub is pre-assembled and checked against clang. `reload()` waits for
   the new m1n1. The launcher then reopens the descriptor-checked port, proves
   it with a NOP, and re-checks the hv001 marker and that no secondaries run.
3. `HV.init()` runs with SPRR emulation **off**. The launcher then reads the
   two `hv_ilinux_*` flags from RAM and **stops** unless single-CPU mode is on
   and the timer gate passed. This happens before anything is written for the
   guest.
4. The same DT gates as boot033 apply: J716c, framebuffer, GPIO ADT, prepared
   DT with one CPU, fixed bootargs, DAPF correction, framebuffer descriptor.
   Differences from native:
   * Bootargs add `console=ttySAC0,115200` **before** `console=tty0` and
     replace `earlycon=ilinuxfb` with `earlycon=s5l,0x505200000`.
     * `/dev/console` stays the framebuffer, as in native boots.
     * All kernel printk lines reach the vUART, including diag init's
       `/dev/kmsg` copies (PID 1 and heartbeats).
     * Serial console writes are polled, so they don't depend on vUART
       interrupts, which are untested on t6050.
     * Diag init's direct console writes (`/proc` dumps) stay on screen only.
   * No `stdout-path`, matching the native DT.
   * Linux, the initramfs and the DT are placed **above the HV heap**. The
     prepared DT's first `/memory` range is rewritten to start there, and the
     payloads must not overlap any reserved-memory node or the framebuffer.
5. RAM outside m1n1 and its heaps is identity-mapped as `HV.load_raw()` does,
   minus the TZ carveouts. The heap layout was checked: m1n1's own heap is
   capped below ProxyUtils' heap by `heapblock_set_limit`. Guest `CPU_START`
   writes at `0x280688000` (the address m1n1's `smp.c` uses for t6050) are
   dropped and logged. A RESERVED tracer keeps `pt_update()` from replacing
   that hook.
6. Upstream `map_essential()` hooks the PS registers of the HV's own link and
   keeps them powered. Names and addresses were decoded offline from the M5's
   sanitized ADT; the pinned C and Python 48-byte records agree, giving 661
   devices. For a USB0 link:
   * `UART0` `0x280900360`
   * `UART_P` `0x280900310`
   * `SIO` `0x280900290`
   * `FAB8_SOC` `0x280900288`
   * `FAB0_PIOGW` `0x2806001d8`
   * `ATC0_USB` `0x288300150`
   * `ATC0_COMMON` `0x280600208`
   * `FAB3_SOC` `0x2806001e0`
   * `ATC0_USB_AON` `0x288300148`

   Ports 1–3 use the matching `ATCn` names. Guest writes to these are forced
   on and logged as "Dangerous write". Upstream's two hardcoded M1-era
   overrides (`0x23d29c044/05c`) hit no t6050 device range.
7. `hv_start(kernel, x0=DT)`. No ADT upload, SPRR, SEPFW or TrustCache copy.

Same payloads as attempt 14 (boot033 Image/DT/initramfs, unchanged). Never
benchmark under the HV.

## Review pass (before the M1 handoff)

* **Console order:** `ttySAC0` was last, which would have made the vUART
  `/dev/console`. Diag init's direct writes could then block on vUART TX
  interrupts. `tty0` is last again.
* **`stdout-path`:** no longer set; it was redundant with `console=` and
  differed from the native DT.
* **Flag gate:** the HV flags are now checked right after `HV.init()`.
  Before, a refused start only showed up when `hv_start` returned.
* **CPU_START hook:** gained its RESERVED tracer; `pt_update()` would have
  replaced it.
* **Reconnect:** NOP-verified with retries, and it no longer swallows the
  global timeout.
* **Overlap check:** payloads checked against reserved memory and the
  framebuffer.
* **Package check:** the symbol table is now a hashed package file, and the
  flag/DT offsets are checked against it.
* **Census:** reads `ACTLR_EL2`. The pre-spec Apple `ACTLR_EL12` is
  informational only (t6050 uses the architectural one). Target console text
  is not echoed.
* **vUART logger:** reconnects after USB re-enumeration. Interface 3 already
  exists under boot021, before the chainload.
* **Tests:** `unittest.main()` now runs every test class in script mode.
  Before, script mode skipped the census and vUART classes.
* **Wording:** RVBAR and warning claims corrected.

## Validation (offline, M5)

* `python3 -I native/hv/test_hv_launch.py`: **28 PASS** (also via
  `python3 -m unittest`). Covers:
  * bootargs and console order;
  * stub vs clang;
  * layout bounds;
  * the in-place `/memory` rewrite;
  * reserved/framebuffer overlap;
  * `System.map` ↔ Image (descriptor offset 35,133,328 and image size);
  * scoped DAPF pin;
  * the HV flag gate;
  * RESERVED CPU_START hook;
  * reconnect retry/timeout;
  * chainload addresses and no RVBAR writes;
  * gate ordering (DAPF → op 0x7f0 → framebuffer descriptor);
  * overlap stop before hardware prep;
  * real-package verification, tamper and symbol-offset rejection;
  * census classes and informational ACTLR;
  * vUART selection and reconnect.
* `native/boot/test_launcher.py` and the other pure `native/boot` suites PASS.
  The m1n1-dependent `native/boot` suites run on the M1 as before.
  Reviewed boot files unchanged.
* **Not verified on M5:** imports in the M1 client venv (no
  pyserial/construct here, and no download made for it). This is M1 readiness
  step 3.

## Known risks / unknowns

* `hv_start` (C) reads AMX/APVMKEY/APSTS/ACTLR/SPRR/GXF registers **without**
  a guard. An undefined trap there hangs m1n1, and recovery is a power off.
  `census.py` reads exactly these first, guarded.
* `hv_init` also runs `pcie_shutdown()` and `usb_hpm_restore_irqs(0)`, and the
  Python init writes HACR/HCR/MDCR/ACTLR. All are upstream code, untested on
  t6050. A Python-side trap aborts cleanly; a C-side one hangs.
* An asynchronous SError from any step hangs m1n1; recovery is a power off.
* USB re-enumeration after chainload and vUART interrupt delivery through AIC3
  are untested on this unit.
* EL1 under the HV is not native EL2: different timer path, injected FIQs,
  trapped registers, 1 kHz HV tick. Driver-logic faults should reproduce;
  VHE/EL2-specific or timing-sensitive ones may not. Domains of the HV link
  (above) cannot be powered off by the guest.

## Files

| File | SHA-256 |
|---|---|
| `0001-ilinux-hv-t6050-single-cpu.patch` | `35e3cbe974d442b7f9af90bc6584167a61d437a2844159419371c3a4aa10ae82` |
| `hv-manifest.json` | `e54877b78cc2b207ba14170952206a1d4aa9e9c7c9eef65caf6a65a58b28183c` |
| `hv_launch.py` | `f9beaf2f4da6b3df7010d754d4d76babf6bd9016718427618f960b03888e0367` |
| `census.py` | `6a488722f415a063c216aeca79bfe57a7f9824f769877ca49fc408771491dbd2` |
| `vuart_log.py` | `25d3d4ee8db52a3c65201f35eace84b77ee3c0b6d280dde0be8c39c30aaac856` |
| `test_hv_launch.py` | `d007c151fc5375bb36ffbfa7162f6651e237fff65f5bb4da20cecee6fa67f52b` |
| Release `native-j716c-hv001`, `ilinux-j716c-hv001.tar.gz` (unchanged by the review pass) | `c659462c77df8a56979aff5f5f5596cbbdb49a6bbe0eaef5d2ecfd9bd6f4ebb1` |

M1 procedure: `tools/m1n1-client/hv-instructions.md`.

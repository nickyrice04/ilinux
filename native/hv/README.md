# hv001: boot033 under a private m1n1 hypervisor

2026-10-14, M5 agent. **Private iLinux tooling. Never contribute it or anything
derived from it to m1n1/Asahi** (their AGENTS.md/CLAUDE.md forbid LLM use; the
user authorized private use). Native/hypervisor behavior: **NOT RUN.**

## Why

Attempt 14 reached PID 1 and then the SoC reset silently ~5.6 s into userspace,
with no message. Photos of a panel cannot show what happened last. Under the
hypervisor the M1 gets:

* every kernel line live on the virtual UART (USB interface 3);
* Ctrl-C into the HV shell with `System.map`-symbolized backtraces;
* an MMIO trace of chosen devices. Tracing `/arm-io/pmgr` directly tests
  attempt 14's top hypothesis: domains switched off at `sync_state`.

It also serves as the first control channel into native Linux, since the vUART
is bidirectional: a shell in the initramfs works as a console.

## What changed (on top of the study `research/m1n1/hv-linux-guest-feasibility-2026-10-14.md`)

**m1n1 patch** `0001-ilinux-hv-t6050-single-cpu.patch` (52 lines, pinned `57a9339`):

| Study blocker | Change |
|---|---|
| `hv_init()` starts all secondaries | Skipped when `chip_id == T6050`. |
| `hv_update_fiq()` writes `VM_TMR_FIQ_ENA_EL2` (trapped in attempt 5) | On t6050 the register is only **read**. If it is already enabled, the HV refuses to start (`hv_start` returns). Guest timers are level-evaluated on every exit and on the 1 kHz HV tick, then delivered as a virtual FIQ. Timer latency is ≤ 1 ms. |
| Path B needs kboot's hardware steps without a jump | New private proxy op `0x7f0` (`kboot_prepare_hv_guest`): `mcc_enable_cache`, `tunables_apply_static`, `clk_init`, `dapf_init_all`. No `usb_init` or `pcie_init`, which would break the HV link. |

The build is job 034 (VM): `m1n1-hv.bin`, SHA-256 `6d031661…85ac`. It has the
`ilinux-57a9339-hv001` marker at 527000, the DT pointer at `0x116538`, and no
compiler warnings. The DAPF table, its paths and its function offsets are
identical to boot021; only the image hash differs.

**Host launcher** `hv_launch.py` (study path B, project style):

1. Same gates as `native/boot/launch.py` on the installed boot021: chip, marker,
   no secondaries.
2. Its own chainload of hv001 into RAM. It is upstream `chainload.py` minus the
   secondary **RVBAR writes** (locked on t6050), with a pre-assembled stub
   checked against clang. It then reconnects and re-checks the hv001 marker and
   that no secondaries are started.
3. `HV.init()` with SPRR emulation **off**, vUART on `/arm-io/uart0`, PMGR
   hooks protecting the HV's own USB/UART domains (upstream `map_essential`).
4. The same gates as boot033 apply: J716c, framebuffer, GPIO ADT, prepared DT
   with one CPU, fixed bootargs, DAPF correction, framebuffer descriptor. The
   only differences:
   * The console moves to `console=ttySAC0,115200 earlycon=s5l,0x505200000`,
     plus `chosen/stdout-path=serial0`. `console=tty0` and the panel stay.
   * Linux, the initramfs and the DT are placed **above the HV heap**. The
     prepared DT's first `/memory` range is rewritten to start there, so Linux
     cannot touch m1n1.
5. RAM outside m1n1 is identity-mapped as `HV.load_raw()` does, minus the TZ
   carveouts. Guest `CPU_START` writes are dropped and logged.
6. `hv_start(kernel, x0=DT)`. No ADT upload, no SPRR, no SEPFW/TrustCache copy.

Same payloads as attempt 14 (boot033 Image/DT/initramfs, unchanged). Only EL
and console differ, so a reset that does reproduce is attributable to those
payloads. Never benchmark under the HV.

## Validation (offline, M5)

* `python3 -m unittest native/hv/test_hv_launch.py`: **18 PASS**.
  Covers:
  * bootargs delta;
  * stub vs clang;
  * guest layout bounds;
  * the in-place `/memory` rewrite;
  * `System.map` ↔ Image consistency (descriptor offset 35,133,328 and image
    size both match);
  * scoped DAPF pin;
  * gates and ordering (DAPF → op 0x7f0 → framebuffer descriptor);
  * chainload without RVBAR writes;
  * real-package verification and tamper rejection;
  * census classification and sanitization;
  * vUART interface selection.
* `native/boot/test_launcher.py` still PASS; reviewed boot files unchanged.
* **Not verified here:** imports in the M1 client venv (no pyserial/construct on
  M5, and no download was made for it). This is M1 readiness step 3.

## Known risks / unknowns

* `hv_start` (C) reads AMX/APVMKEY/APSTS/ACTLR/SPRR/GXF registers **without**
  a guard. An undefined trap there hangs m1n1, and recovery is a power off.
  `census.py` (H1) reads exactly these, guarded, first.
* An asynchronous SError from any step hangs m1n1; recovery is a power off.
* The USB re-enumeration after chainload is untested on this unit.
* EL1 under the HV is not native EL2: different timer path, injected FIQs,
  trapped registers. Driver-logic faults should reproduce; VHE/EL2-specific
  ones will not.
* The HV's 1 kHz tick and MMIO traps slow the guest. Timing-sensitive
  failures may shift.

## Files

| File | SHA-256 |
|---|---|
| `0001-ilinux-hv-t6050-single-cpu.patch` | `35e3cbe974d442b7f9af90bc6584167a61d437a2844159419371c3a4aa10ae82` |
| `hv-manifest.json` | `85a5b16f5f8d2701cb7abd18c826666e802d7851e5a6e2ce2d80713e6966ab59` |
| `hv_launch.py` | `066534a48c7ff28fae7b8df67b1513997c4a4c6222e68308f0ab4bce29267e10` |
| `census.py` | `66f809616bed4ca682f58b0fac646a0a8ab3668eabbbecd02002a91dd28a80df` |
| `vuart_log.py` | `4485e08f260e2811c360435192f53776338502b6b51d3760977d9dbc4d37ca00` |
| Archive `ilinux-j716c-hv001.tar.gz` (local, not yet released) | `c659462c77df8a56979aff5f5f5596cbbdb49a6bbe0eaef5d2ecfd9bd6f4ebb1` |

M1 procedure: `tools/m1n1-client/hv-instructions.md`.

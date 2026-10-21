# CPU1 timeout after 31C: console dependency and PMGR cross-check

2026-10-21. Native report `beaadb1`; 31C execution `c48464d`.
**Observed:** the actual RAM/ADT gate passed; both CPU1 startup writes were
acknowledged; arrival did not complete within three seconds. Usual macOS
return was confirmed within the human timer. No Linux boot or timer request
ran. The saved output does not distinguish a core held in reset from a core
stalled before its arrival flag. It did not retain partial reset-table state.

## Fresh REA and independent checks

REA 6.4.0 / Ghidra 12.1.4 ran in the existing diskless ARM64 analysis VM,
using this machine's retained macOS 26.6.2 / 25G83 ApplePMGR member. Two
90-second-bounded queries exited 0 in 41.982 and 41.340 seconds. Guest setup
and job both exited 0. Original-carrier byte checks and Apple LLVM independently
verified all 214 instruction words. The provenance-only record is
[validation.json](validation.json); raw output stays in ignored local build.

| Function | Entry | What the bounded evidence supports |
|---|---|---|
| `ApplePMGR::enableCPUCores` | `0xfffffe000949606c` | 664-byte body / 166 words. The request passes through indirect dispatch at function +0xD4 and surrounding software bookkeeping. The body alone does not establish all prior hardware/power initialization. |
| `ApplePMGR::getClusterPowerState` | `0xfffffe000949e3bc` | 192-byte body / 48 words. A resolved cluster index contributes four-byte register spacing at +0x78; the returned state is masked to the low nibble at +0xA0. This is not proof that an offline core can safely be probed or that startup completed. |

The first pseudocode gate remains **manual review required**. The second
is **rejected cross boundary**: 153 p-code operations referenced addresses
outside the function, including the neighboring enable path. Its full
pseudocode was not used. Only bounded, byte-checked instructions inform the
behavioral statement. Indirect calls and collection fixups remain limits.

Earlier verified `configMiscCores` and T6050 register-group findings still
support the two selected CPU1 register addresses and masks. There is no new
evidence here to justify a speculative power-register write, longer timeout,
security-register replay or reset-vector change. CPU1 shares CPU0's cluster;
the known six-core/four-bit-stride issue affects later clusters, not CPU1.

## A concrete pre-arrival dependency in public bootloader code

**Confirmed source and compiled image:** pinned m1n1 `57a9339` / boot021 calls
`uart_puts` and several `printf` paths before publishing CPU1's arrival flag.
Both `uart_putbyte` and `dockchannel_uart_putbyte` poll transmit availability
without a bound. The MMU-off secondary console path writes through
`_iodev_console_write_helper`, bypassing the normal `can_write` check.
Thus primary USB responsiveness does not exclude secondary console blockage.

**Hypothesis, not diagnosed hardware cause:** a diagnostic UART with no
transmit space could keep a correctly started CPU1 from reaching its flag.
31C did not record these transmitters or earlier progress, so it cannot prove
this explanation. CPU1's actual reset entry and early register state remain
unknown if no shared record appears.

The exact compiled UART entry paths load their respective RAM base variables
and return immediately when zero, before touching UART MMIO. The original
parser in `kernel/experiments/smp31/audit_console31d.py` resolves those loads
and zero-return branches from the pinned image, and GNU objdump independently
confirms them. Bindings are recorded in `native/boot/attempt31d/console-binding.json`.

| Diagnostic output | RAM variable offset in boot021 | Expected peripheral base from translated ADT |
|---|---:|---:|
| Dockchannel UART | `0x110030` | `0x288e28000` |
| Serial UART | `0x35a4a0` | `0x505200000` |

These offsets designate mutable **RAM variables**, not hardware registers.
Zeroing them suppresses diagnostic output for this RAM session. It does not
reset a UART, alter a boot volume, patch instructions or alter USB transport.
The active proxy's separate enum must indicate direct USB before allocation.
Both values are cache-cleaned to PoC before any CPU1 start request. Cache-line
neighbors may also be written back; this is not an atomic multicore snapshot.

## Engineering decision and experiment interpretation

31D keeps installed boot021, the same CPU1 start sequence, helper, requests,
three-second arrival bound and independent human return timer. It adds the
two RAM zeroes and two cache publications, then records partial CPU1 reset
and spin identity with the existing guard-free reads of uncached SMP RAM.
It makes no new MMIO read and no new MMIO write beyond the two existing starts.

A source-based VM harness compiles the actual pinned UART functions and
console helper with simulated MMIO. Full transmitters keep polling in all
three routes; a bounded mock ends observation after 32 reads. Zero bases
return without MMIO; ready transmitters still write. Nine cases pass both
normal and ASan/UBSan builds. This proves a code-path dependency, **not** that
the real UARTs were full or that 31D will start CPU1.

* **Arrival plus two completed timer requests:** supports a diagnostic-console
  dependency; next prepare two-core Linux and test timers, bidirectional IPIs,
  coherency, scheduler work and threaded renderer. It does not identify the
  exact transmitter or prove macOS performance/efficiency.
* **Reset identity but no flag:** the secondary entry function reached its RAM
  publication; focus on the remaining interval before spin publication.
* **Spin identity but no flag:** focus on flag publication, ordering or observation.
* **No reset record:** earlier CPU execution is still unknown. Do not simply
  retry; prepare early entry instrumentation and review its deployment, then
  revisit raw reset state/power with evidence. No guessed power/firmware writes.
* **Unexpected identity, fault or lost transport:** stop and retain partial
  evidence. No cleanup, reconnect, retry or Linux continuation.

Public m1n1 sources:
[secondary startup](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/startup.c),
[console dispatch](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/iodev.c),
[UART](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/uart.c),
[dock UART](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/dockchannel_uart.c).
These exact files were read locally and pinned; no proprietary implementation
is included in the controller or source-based test harness.

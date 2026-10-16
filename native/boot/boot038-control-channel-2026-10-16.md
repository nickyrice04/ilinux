# boot038: the USB control channel with CDC-ACM + CDC-ECM, prepared offline

2026-10-16, M5 agent. **Native boot038 / attempt 18 NOT RUN. Not published, not
committed.** Builds on `boot036-control-channel-2026-10-15.md` and the
attempt-17 result (`stage-b-2026-10-16-attempt17-result.md`). Labels:
Confirmed / Likely / Hypothesis / Unknown.

## What attempt 17 settled (Confirmed, hardware)

* The Linux side of boot036's link works on the M5: all three `snps,dwc3`
  cores probe in 26–31 ms with no `-110` and no DART fault, three gadgets bind,
  and the M1 enumerates the cabled port 8 s after the handoff (`1d6b:0104`,
  high speed, configuration set by macOS). The port stays `configured`.
* The baseline holds with the ATC domains excluded: ladder complete at 45.0 s
  (50 domains, none from `atc0`–`atc2`), alive past 98 s, no reset.
* macOS 26.0.1 on the M1 never claims a CDC-EEM interface: the kext on disk is
  a stub and is not in the kernel collection. `cdc.acm` and `cdc.ecm` are
  loaded; `cdc.ncm` is available on demand.

## What boot038 changes

Only the gadget's functions, in `/init` (`kernel/experiments/usb-gadget/init.c`):

| | boot036 | boot038 |
|---|---|---|
| Functions per gadget | CDC-EEM | **CDC-ACM** (interfaces 0–1) + **CDC-ECM** (2–3), one configuration |
| ACM port | — | `/dev/ttyGSn` on the M5; a child of `/init` copies `/dev/kmsg` to it as `[sec.usec] text` lines, pacing itself when the 8 KiB serial FIFO is full, so nothing the kernel still holds is dropped. Nothing is read from the port. macOS creates `/dev/cu.usbmodem*`. |
| Network | EEM, `usb0`, `fe80::69:6cff:fe69:6e0N` | ECM, same interface, MACs and address |
| `bcdDevice` | 0x0036 | 0x0038 |
| Image, config, DT, m1n1, launcher | | byte-identical to boot036 (packager-enforced) |

Why both functions: ACM and ECM each use an interrupt-IN notification endpoint
(EEM did not). The ADT flags `ncm-interrupt-ep-disabled` on these ports for
Apple's own NCM, and m1n1's ACM never transmits on its notification endpoint,
so whether that endpoint transmits on this hardware is Hypothesis until
attempt 18. The serial port's silence or output answers it independently of
the network.

## Results

| Check | Result |
|---|---|
| VM job 041 (rebuilt initramfs; Image `e0e53113…`, DT `a676087b…` unchanged) | PASS; `init.c` compiles with the one known harmless warning |
| Initramfs contract (static init, root-only, no self-test, exactly the M1's key) | PASS |
| Package `ilinux-j716c-boot038.tar.gz`: 18,904,584 bytes, SHA-256 `09f5a5d723461bccfba3c29aacb084c3318203d074e522c1527d650186e05f70`, SHA256SUMS digest `efba5795…a186` | PASS; only `initramfs-stage-b.cpio.gz` (2,392,929 bytes, `30800bdd…`) and `diag-init.c` differ from boot036 |
| Committed launcher `4d55f0c9…` offline verification | `Package PASS` |
| Generic VM, shipped Image + initramfs, 95 s | PASS: PID 1, one CPU, no UDC (expected), dropbear, 60 s heartbeat |
| Generic VM, test Image (dummy_hcd + cdc_ether + cdc-acm host drivers) | PASS, all 16 checks: `ACM+ECM 1d6b:0104` bound, host `cdc_ether` interface, **1,796 kernel-log lines over `/dev/ttyACM0`**, ping, SSH with the key, refusal without it, 8 MiB intact |
| `native/boot` suites | all PASS |

The VM cannot show whether the real dwc3 cores complete an interrupt-IN
transfer, or which drivers macOS binds; those are attempt 18's questions.

## Attempt 18 reads

| M5 screen | M1 | Meaning |
|---|---|---|
| port `configured`, `rx`/`tx` rise | new `cu.usbmodem*` streams the log; `enX` with `inet6`; ping and SSH | the control channel works both ways |
| port `configured` | log arrives on serial, no `enX` or no `inet6` | ACM works; report ECM's driver state from `ioreg` |
| port `configured` | serial port exists but silent, no `enX` | the notification or data endpoint stalls: the interrupt-endpoint hypothesis fails; next is a bulk-only design the M1 can bind |
| port `configured` | device in `ioreg`, neither driver | report `ioreg`'s per-interface drivers |

## Also fixed today

The E1 MTP probe (and the PMGR probe) stopped on a Python scoping error before
any device contact: a class body assigned `M1N1Proxy = staticmethod(M1N1Proxy)`
and could not see the function-local import. Both now alias the import first,
and each test suite builds the live API through `connect_and_run` with stub
m1n1 modules (the new tests fail with the original `NameError` when the fix is
reverted). The E1 plan is unchanged (66 reads). A rerun needs the M1's
re-verification and the human's go.

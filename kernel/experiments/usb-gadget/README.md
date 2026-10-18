# USB control channel (boot036, revised as boot038, boot039 and boot040)

Roadmap Phase 3, step 2: a network link into native Linux over the same USB
cable the M1 uses for the m1n1 proxy, so the M1 can run commands, read logs and
later send the Arch RAM root. Private research code: never send it upstream.
**Prepared offline 2026-10-15. Native boot036 NOT RUN. It must not run before
attempt 16 (boot035) reports a stable baseline.**

## What boot036 changes from boot035

| Part | Change | Checked by |
|---|---|---|
| Kernel config | `USB_LIBCOMPOSITE` and `USB_CONFIGFS` from m to y; Kconfig turns the 12 gadget functions and helpers they select (EEM, NCM, ECM, u_ether, ...) from m to y. Nothing else. The Stage-B initramfs carries no modules. | `native/boot/control_channel.py` `check_config` |
| Stage-B DT | One `snps,dwc3` node per usb-drd port, peripheral, high speed, four PHY-keepalive quirks, DMA through that port's second USB DART with stream 1. Those three DARTs enabled without `power-domains`. All 39 PMGR domains of ATC ports 0–2 disabled. | `native/boot/usb_dt.py` `check_delta` |
| Initramfs | `/init` from `init.c` (static): everything the old diag-init did, plus one configfs gadget per UDC (boot036: CDC-EEM; boot038: CDC-ACM kernel-log port + CDC-ECM in one configuration; boot039: one bulk-only `gser` kernel-log port, no network), the interface up (IPv6 link-local only; not in boot039), dropbear (root, key only, no forwarding, host keys made in RAM), a status line per heartbeat (boot039: with the dwc3 state from debugfs). dropbear and busybox with their libraries from signed Arch Linux ARM packages. | `control_channel.check_initramfs`; boot039: `check_bulk_only_init`, `check_init_only_delta` |
| Image | Rebuilt from the boot034 tree with the config above. The genpd release ladder and every earlier patch are unchanged. | job 041 symbol and roundtrip checks |

m1n1, the generic `initramfs.cpio.gz`, the full DT and the launcher's fixed
arguments are unchanged. The launcher's checks (`fdt.check_stage_b`) pass on the
new DT; no reviewed controller digest changes.

## Why these choices

| Claim | Label | Source |
|---|---|---|
| m1n1 powers each port's ATC, DART and DRD domains, starts the USB2 PHY and parks the PIPE mux on the dummy PHY; at handoff it only stops and soft-resets the dwc3 device side | Confirmed (source) | `third_party/m1n1/src/usb.c:145-177`, `usb_dwc3.c` shutdown |
| m1n1's own gadget DMAs through DART instance 1 with stream = `mapper-usbN` `reg` = 1 on this Mac | Confirmed (source + ADT) | `usb.c` `usb_dart_init`; `hardware/adt/adt-sanitized.json` |
| Linux's pwrstate probe arms AUTO_ENABLE on every domain that is on, and the boot034 ladder releases unclaimed ones; a disabled node is never probed or registered | Confirmed (source, attempt 15) | `drivers/pmdomain/apple/pmgr-pwrstate.c:295-298`; attempt-15 report |
| With the ATC domains described but unclaimed, omarchy-m5's DWC3 soft resets timed out (-110) | Likely (their commit text) | `research/asahi/omarchy-m5-review-2026-10-15.md` §1 |
| dwc3 core = usb-drdN `reg[0]`, IRQ = `interrupts[0]` (DART IRQ + 4, as on M3) | Likely | ADT; Asahi `t6030.dtsi:1374-1405` |
| Core window 0xcd00; the Apple glue registers follow it | Likely | Asahi `t6030.dtsi:1376` |
| CDC-EEM uses bulk endpoints only, so no interrupt-IN notification | Confirmed (class spec) | USB CDC EEM 1.0 |
| **Attempt 17 (boot036):** all three dwc3 cores probe, the EEM gadget binds, the M1 enumerates it in 8 s, no DART fault; but macOS 26.0.1 on the M1 has no loadable EEM driver (stub kext), so no interface appears | Confirmed (hardware) | `native/boot/stage-b-2026-10-16-attempt17-result.md` |
| **boot038:** CDC-ACM (kernel log, written only by the M5) + CDC-ECM (network) in one configuration; both macOS drivers are loaded on the M1. Both use an interrupt-IN notification endpoint, which attempt 18 therefore tests too | Likely (drivers loaded); endpoint: Hypothesis | attempt-17 report; attempt 18 |
| NCM stalled on omarchy-m5's J714s after its first interrupt-IN notification | Likely (their commit text) | review §1 |
| All three usb-drd ports carry `ncm-interrupt-ep-disabled` in our ADT | Confirmed (ADT) | `hardware/adt/adt-sanitized.json` |
| macOS 26.6.2 (this M5) has `AppleUSBEEM.kext`, `com.apple.driver.usb.cdc.eem` 5.0.0, matching interface 2/12/7 | Confirmed (this Mac) | `/System/Library/Extensions/AppleUSBEEM.kext` Info.plist |
| The M1's macOS has the same driver | Unknown | check on the M1 first (draft steps) |
| The USB DARTs translate without `apple,dma-range` (macOS's ADT window starts at 0x100_0000_4000) | Hypothesis | Asahi M3 dwc3 DARTs carry none |
| The gadget enumerates and carries traffic on a macOS host | Hypothesis | attempt 17 |

## boot039: one bulk-only function and the dwc3 state on screen

Attempt 18: right after macOS selected configuration 1, boot038's device stopped
answering control transfers. Both of its functions have an interrupt-IN notification
endpoint, and the ADT marks these ports `ncm-interrupt-ep-disabled`. boot039 keeps
everything but the gadget and the status line:

* **Function:** the in-kernel generic serial function `gser` (`f_serial.c`). It has one
  vendor-class (`0xff`) interface, one bulk-IN and one bulk-OUT endpoint, no interrupt
  endpoint and no setup handler. No macOS driver binds it; the M1 reads the bulk-IN
  endpoint with a read-only user-space tool (`tools/m1n1-client/bulk-log-reader-brief.md`).
  The kmsg streamer is unchanged except that the port is raw (no echo, exact CR LF)
  and it counts what it writes, in memory shared with `/init`.
* **bcdDevice `0x0139`:** configfs accepts only BCD (`is_valid_bcd`). `0x003a` was
  refused with `EINVAL` in the VM, and the gadget fell back to the kernel default
  `0x0701`; the self-test caught it. `0x0039` is the RAM root's.
* **Status line:** per port, `log <records>L <bytes>B q<queued>`. Then, per dwc3
  controller, `dwc3 <link> f<SOF frame> ev<pending event bytes> [STOPPED HALTED BUSERR
  CSR-TIMEOUT EVBUSY] irq<count> ep0 o:<cmd> i:<cmd> <ep> <type> h<HW-owned TRBs>
  d<dequeue>`. Here `<cmd>` is the last command in that endpoint's DEPCMD register, `*`
  means still active and `!N` a nonzero status. Once per controller, `core <id>, <n>
  endpoints (<m> IN), MDWIDTH <w>; TX FIFO words ...`. Only `link_state`, `regdump`
  and the endpoints' `transfer_type` and `trb_ring` are read. Reading the FIFO and queue
  files, `GDBGEPINFO` or `lsp_dump` writes a debug select register, so those are not
  read. A child process does the reading, so a stuck read costs one line, not the
  heartbeat. This tree has no `ep0state` file: the driver's EP0 state machine is not
  visible, only its commands, events and interrupts.
* **No network:** dropbear still runs, on loopback only. The initramfs differs from
  boot036's in `/init` only (packager-enforced).

## boot040: the first fault on the screen (after attempt 21)

Attempt 21 read 36,909 bytes over the bulk-IN endpoint, then port 1's dwc3 flagged a bus
error, its interrupts stopped and the DART fault interrupt stormed until Linux disabled
it, without one fault report. boot040 keeps boot039's gadget, DT and config and adds
only diagnostics, so the next film shows the first fault instead of the storm:

* **Image:** `dart-diag/` patches the apple-dart driver twice. Part 1 makes the t8110
  fault handler print the raw ERROR, ERROR_MASK, ERROR_STREAMS, ERROR_ADDR and TLB_CMD
  when the interrupt arrives without the error flag (count-limited), acknowledge a pending
  ERROR or stream bit and otherwise return IRQ_NONE, and name each t8110 instance at probe
  (version, PARAMS, Linux fault IRQ). Part 2, written after the REA of this Mac's macOS DART
  driver (`dart-diag/rea-dart-2026-10-18.md`: the fault-register layout switches at DART
  version 2.2, which Linux does not know), reports and acknowledges faults in that layout
  when, and only when, PARAMS3 reports version 2.2 or later, with a bound of 256
  acknowledged interrupts per instance. Nothing in translation, protection or the TLB-flush
  path changes (`dart-diag/test_dart_diag.py`, W=1 build, digest-gated two-stage `apply.py`).
* **`/init`:** `BUSERR@<GBUSERRADDR1:0>` in the status line; at bind an identity line per
  port (dwc3 IRQ, DART instance, stream, fault IRQ, the sibling instance the DT leaves
  out, all from sysfs) and a read-only register snapshot of both DART instances through
  `/dev/mem` (both fault layouts, chosen by the version the DART reports), repeated at the
  first bus error; a short `[usbN]` line per port each heartbeat (about 100 columns: state,
  link, frame, dwc3 and DART interrupt counts, bytes, queue, ring state, flags, bus-error
  address); the log streamer of a port stops for good at its first bus error.
* **Audit** of the Linux DART driver against the ADT, Asahi's wiring and m1n1
  (`dart-diag/README.md`, findings D1-D7 with evidence and confidence) and the fix
  candidates A-D it leaves, each tied to the evidence boot040 would show.

Report: `native/boot/boot040-dart-fault-2026-10-18.md`. Packaging: `make-package.py
--name ilinux-j716c-boot040` (Image, `/init` and its source may differ from boot039;
`test_boot040_package.py`).

## Address plan

Gadget N (N = 1..3 for `2a2280000.usb`, `2aa280000.usb`, `382280000.usb`, the
ADT's ports 1..3; any other UDC, such as the VM's `dummy_udc.0`, gets 4+):
VID:PID `1d6b:0104`, product "iLinux J716c control channel, port N", serial
`ilinux-portN` (not a hardware serial), device MAC `02:69:6c:69:6e:0N`
(locally administered, fixed), so the Linux end is
`fe80::69:6cff:fe69:6e0N%<M1 interface>`. No IPv4, no routes, no DHCP: nothing
on the M1 has to be configured, and no traffic is routed.

## Tests (job 041 and `selftest/run-vz.sh`)

* Offline: `native/boot/test_usb_dt.py` (exact DT delta, 19 mutations, the real
  build with dtc) and `native/boot/test_control_channel.py` (config delta,
  16 initramfs and 12 config deviations, including toolchain drift).
* Job 041 builds the Image, a test Image (adds `dummy_hcd`, usbnet and the host
  `cdc_ether` and `cdc-acm` drivers; never shipped), the DT (schema-checked), the initramfs and a
  self-test overlay, and checks every ELF for 16 KiB pages.
* `selftest/run-vz.sh` boots both on the Mac (Virtualization.framework, one
  CPU, no disk or network): the shipped pair must reach PID 1 and the 60 s
  heartbeat with "no UDC"; the test pair must bind the gadget to `dummy_udc.0`,
  enumerate it through `dummy_hcd`, and pass ping, SSH with the key, refusal
  without it, and an 8 MiB copy, across a network namespace.

Results (2026-10-15, boot036): job 041 and both boots PASS; (2026-10-16, boot038): rebuilt with the ACM + ECM init, job 041 and both boots rerun; see
`native/boot/boot036-control-channel-2026-10-15.md`. (2026-10-16, boot039): the test
kernel adds the host's generic usb-serial driver, the self-test reads the log over
the bulk-IN endpoint, and job 041 checks the kernel facts the status line relies on
(`selftest/check_kernel_facts.py`) and runs the status line on fixture trees
(`selftest/status_fixture.c`, also under ASan/UBSan); see
`native/boot/boot039-bulk-log-2026-10-16.md`. What the VM cannot show:
the dwc3 cores, the DARTs, the PHY state m1n1 leaves, the AIC routing and the
macOS host. Those are attempt 17's questions.

## Files

`init.c` (packaged as `diag-init.c`), `make_stage_b_dt.py`,
`stage_initramfs.py`, `elf_pages.py`, `selftest/`, `dart-diag/` (boot040),
`virtualization/jobs/041-usb-gadget/`, `native/boot/usb_dt.py`,
`native/boot/control_channel.py`.

`authorized_keys` here is the M1's own public key (commit `a6717b0`,
`SHA256:o7wtpNY0…`); job 041 builds the shipped initramfs with it, and without
the file it falls back to its own test key and says so. The VM self-test
overlay replaces root's `authorized_keys` with the job's test key for test
boots only. Job 041 pins the kernel's build time, user and host, so rebuilds
give the same Image.

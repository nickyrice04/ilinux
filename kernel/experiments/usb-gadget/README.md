# USB control channel (boot036)

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
| Initramfs | `/init` from `init.c` (static): everything the old diag-init did, plus one CDC-EEM configfs gadget per UDC, the interface up (IPv6 link-local only), dropbear (root, key only, no forwarding, host keys made in RAM), a status line per heartbeat. dropbear and busybox with their libraries from signed Arch Linux ARM packages. | `control_channel.check_initramfs` |
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
| NCM stalled on omarchy-m5's J714s after its first interrupt-IN notification | Likely (their commit text) | review §1 |
| All three usb-drd ports carry `ncm-interrupt-ep-disabled` in our ADT | Confirmed (ADT) | `hardware/adt/adt-sanitized.json` |
| macOS 26.6.2 (this M5) has `AppleUSBEEM.kext`, `com.apple.driver.usb.cdc.eem` 5.0.0, matching interface 2/12/7 | Confirmed (this Mac) | `/System/Library/Extensions/AppleUSBEEM.kext` Info.plist |
| The M1's macOS has the same driver | Unknown | check on the M1 first (draft steps) |
| The USB DARTs translate without `apple,dma-range` (macOS's ADT window starts at 0x100_0000_4000) | Hypothesis | Asahi M3 dwc3 DARTs carry none |
| The gadget enumerates and carries traffic on a macOS host | Hypothesis | attempt 17 |

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
  `cdc_eem` driver; never shipped), the DT (schema-checked), the initramfs and a
  self-test overlay, and checks every ELF for 16 KiB pages.
* `selftest/run-vz.sh` boots both on the Mac (Virtualization.framework, one
  CPU, no disk or network): the shipped pair must reach PID 1 and the 60 s
  heartbeat with "no UDC"; the test pair must bind the gadget to `dummy_udc.0`,
  enumerate it through `dummy_hcd`, and pass ping, SSH with the key, refusal
  without it, and an 8 MiB copy, across a network namespace.

Results (2026-10-15): job 041 and both boots PASS; see
`native/boot/boot036-control-channel-2026-10-15.md`. What the VM cannot show:
the dwc3 cores, the DARTs, the PHY state m1n1 leaves, the AIC routing and the
macOS host. Those are attempt 17's questions.

## Files

`init.c` (packaged as `diag-init.c`), `make_stage_b_dt.py`,
`stage_initramfs.py`, `elf_pages.py`, `selftest/`, `virtualization/jobs/041-usb-gadget/`,
`native/boot/usb_dt.py`, `native/boot/control_channel.py`.

`authorized_keys` here is the M1's own public key (commit `a6717b0`,
`SHA256:o7wtpNY0…`); job 041 builds the shipped initramfs with it, and without
the file it falls back to its own test key and says so. The VM self-test
overlay replaces root's `authorized_keys` with the job's test key for test
boots only. Job 041 pins the kernel's build time, user and host, so rebuilds
give the same Image.

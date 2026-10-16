# Stage B attempt 17: the Linux USB gadget enumerates on the M1; macOS has no EEM driver

2026-10-16. **One RAM attempt consumed** (the first controller invocation stopped
at the USB identity gate before any device contact and is recorded separately).

* **First Linux USB on this M5 Max, on real hardware.** All three `snps,dwc3`
  device-mode controllers probed (26-31 ms each), three CDC-EEM gadgets bound,
  and the M1 enumerated the cabled port **8 s after the handoff**
  (`1d6b:0104`, `bcdDevice 0x0036`, USB 2.0 high speed, configuration 1 set by
  macOS). The M5 reports that port `configured`, `usb0 up`, with its link-local
  address, and stays that way to the end of the clip.
* **The control channel did not come up: macOS has no EEM driver.** The EEM
  interface has no driver attached on the M1, no `enX` interface appears, and
  SSH was not possible. **`com.apple.driver.usb.cdc.eem` is not in this Mac's
  kernel collection in any state** (macOS 26.0.1, build 25A362).
* **Native baseline held:** PID 1, one CPU, the 60 s milestone (63.60 s),
  heartbeats 000-019 to 98.68 s, the release ladder complete at 45.02 s (50
  domains, none from `atc0`-`atc2` or `smc_i2cm`), no reset, no M1 panic.
* **Correction to M1's earlier report:** the `AppleUSBEEM.kext` check on
  2026-10-15 proved only that a stub bundle exists on the sealed volume. The
  loaded or loadable state of the kext should have been checked too.
* Fresh policy/default checks: **NOT CHECKED.** No retry or settings change.

## Reviewed inputs and controller executions

* M5 handoff `0363bd5`; readiness `9a3e002`, re-stamped to `ea76f60` (docs-only
  commit; no pinned file changed).
* Release `native-j716c-boot036`: archive 18,902,541 bytes, SHA-256
  `f09a00000925aea64a6ea7ab6dace05958d779d2367fc6aec233becc58ca71a3`, verified
  against Git before extraction. Image `e0e53113…f3f7`, Stage-B DT
  `a676087b…efa5`, initramfs `5f4b478b…b248`. M1 independent review recorded in
  the readiness entry (DT delta, key-only dropbear, packaged key equals the M1
  key).
* **Launch 1, 2026-10-16T18:26:32Z: stopped at the USB identity gate** (0.11 s):
  the freshly restarted M1's USB registry query returned nothing parseable (no
  USB device attached on its ports, `InvalidFileException` from the plist
  parse). No port was opened and no request was sent. The human then
  moved the cable to another USB port; the read-only gate passed (two m1n1
  serial interfaces). The human asked for the rerun; it was not automatic.
* **Launch 2, started 18:29:03Z, handoff 2026-10-16T18:29:14.150473Z: exit 0 in
  10.975 s.** Target, marker, no secondaries, GPIO ADT, board/framebuffer, DAPF
  layout and correction, final hardware DT and framebuffer descriptor all PASS;
  kboot reply PASS. Interface list recorded before the handoff (23 names).
* **M1 host:** freshly restarted (uptime 3 min at pre-flight), `caffeinate -i`
  running, no panic during or after the run.

## Media and method

`Attempt17.MOV`: **100.727 s, 1080×1920, 30 fps, original file** (200 MB),
user-supplied into the ignored inbox. It begins at kernel ≈ 1.5 s and ends at
≈ 100.3 s. Reviewed locally with AVFoundation: a 2 s brightness trace, overview
frames and upscaled crops. The text is fully legible. Review images deleted;
media stays local. Time mapping: `kernel ≈ video + 0.56 s`.

## M5 screen, literal observations

| Kernel s | Observation |
|---:|---|
| ≈ 1.55 | panel `P:05 S:00 / W:04 H:00 / D:0059 … B:91 C:0059` (main GPIO probe); `/proc/interrupts` later shows three `apple-dart fault handler` lines at 0 |
| 3.385 | `[ctl] USB control channel: CDC-EEM gadget per UDC, IPv6 link-local, SSH key only` |
| 3.386-3.418 | `configfs-gadget.g1`; `probe of gadget.0 returned 0 after 31286 usecs` |
| 3.419 | `[ctl] port 1: UDC 2a2280000.usb bound, EEM 1d6b:0104, interface usb0 up; Linux end fe80::69:6cff:fe69:6e01%<if>` |
| 3.451 | `[ctl] port 2: UDC 2aa280000.usb bound … usb1` (gadget.1 probe returned 0 after 25907 usecs) |
| 3.483 | `[ctl] port 3: UDC 382280000.usb bound … usb2` (gadget.2 probe returned 0 after 25910 usecs) |
| 3.489 | `[ctl] dropbear start 1: pid 55, port 22, key-only root` |
| 3.491 | `[diag] heartbeat 000 online_cpus=1`; `[ctl] port1 not attached usb0 down rx=0 tx=0 | port2 not attached usb1 unknown | port3 not attached usb2 unknown` |
| **8.503** | **heartbeat 001: `[ctl] port1 configured usb0 up rx=0 tx=0 fe80::0069:6cff:fe69:6e01(tentative)`**; ports 2 and 3 `not attached`, `usb1`/`usb2` down |
| 13.505+ | heartbeat 002 onward: port1 `configured`, address no longer tentative, `rx=0 tx=0`; ports 2-3 `not attached` |
| 13.535 | two `apple-pmgr-pwrstate … sync_state() pending due to …` notices (driver core, not power-offs) |
| 19.42-44.51 | ladder steps 1-50: first `atc3_usb_aon`, then `isp_sys`, `uart6`…`uart0`, `uart_n`, `qspi`, `spi5`…`spi0`, `aes`, `i2c6`…`i2c0`, `aphy_gp_aus5`, …; last `dispext0_sys` |
| **45.024** | **`ladder complete: 50 domains released`** |
| 63.595 | `[diag] 60s elapsed; still alive. Observe the M5 framebuffer and the M1's new USB network interface.` |
| 98.68 | heartbeat 019 (last in the clip): port1 `configured usb0 up rx=0 tx=0`; ports 2-3 `not attached` |

* No `dwc3` error, `-110`, `apple-dart … fault` or other error line was seen on
  screen at any point; the DART fault counters were 0 at 3.5 s. No `smc_i2cm`,
  `atc0`, `atc1` or `atc2` name appears among the ladder lines read (steps 1-26
  and the last steps were read; the middle steps were not each transcribed).
* `rx=0 tx=0` never changes over 95 s. Not a failure of the gadget: with no
  host driver, the host never opens the endpoints, so no frame completes in
  either direction (**Likely**).
* The panel rows after the early probe were scrolled off; GPIO caches and other
  attempt-16 lines were not re-read.

## M1-side observations (read-only; no network setting changed)

* `ioreg`: **`iLinux J716c control channel, port 1`** at the cabled port, seen
  8 s after the handoff: `idVendor 0x1d6b`, `idProduct 0x0104`, `bcdDevice
  0x0036`, `bcdUSB 0x0200`, speed high, one configuration, `bMaxPacketSize0 64`.
  Interface 0: class/subclass/protocol 2/12/7, **2 endpoints**,
  `bConfigurationValue 1`.
* macOS attached **`AppleUSBCDCCompositeDevice`** at device level. **Nothing
  attached to the EEM interface**, and no `IOEthernetInterface` was created;
  `ifconfig -l` was identical before and after (23 names).
* `AppleUSBEEM.kext` on the sealed volume is a **stub** (`Info.plist`,
  `version.plist`, `_CodeSignature`; no executable), bundle id
  `com.apple.driver.usb.cdc.eem`, with one personality `AppleUSBEEMData` that
  matches class 2 / subclass 12 / protocol 7. `kmutil showloaded --show all`
  for that bundle id returns **nothing**, and no registered class contains
  "EEM". By contrast **`cdc.ecm` is loaded**, **`cdc.ncm` is present but
  unloaded**, `AppleUSBDeviceNCM` is loaded, and `cdc.acm` is loaded (m1n1 uses
  it); a DriverKit `AppleUserECM` is also available.
* `kernelmanagerd` logged load notifications for `cdc`, `serial`, `cdc.acm`,
  `cdc.ecm` when m1n1 was re-plugged (14:28:04 EDT) and for `AppleUSBAudio`
  when the iLinux device appeared (14:29:22 EDT). **It never requested an EEM
  kext.** (`AppleUSBAudio` is generic probing, not a match for this device.)
* SSH was not attempted: the capture script found no new `en` interface
  (its first run waited only 3 s; two later manual checks, 30 s and over a
  minute after, confirmed none) and stops before any network action.

## Interpretation (bounded)

**Confirmed:**

* Linux device-mode USB works on the M5's dwc3 cores on the PHY state m1n1
  leaves, with DMA through the second USB DART: no probe timeout, no DART
  fault, three UDCs, a host-visible enumerated device within 8 s.
* The control-channel design is sound on the Linux side (gadget, netdev,
  link-local address, key-only dropbear all start).
* macOS 26.0.1 on this M1 Pro has **no usable EEM driver**: the kernel
  collection does not contain the kext, so the EEM interface is never claimed.

**Likely, not tested:** with an ECM, NCM or ACM function instead of EEM, macOS
would bind a loaded or available driver. ECM and the serial driver are already
loaded here; NCM is available on demand.

**Unknown:** whether the t6050 dwc3 supports the interrupt endpoint that ECM,
NCM and ACM notification need. m1n1's own CDC-ACM gadget uses interrupt
endpoints on the same controllers and works, which suggests yes in device mode,
but the ADT flag `ncm-interrupt-ep-disabled` that M5 noted is unexplained.

## Return and next handoff

* The human stopped filming at the time given, shut the M5 down and returned to
  Macintosh HD (reported). Fresh policy/default/installed-object checks: **NOT
  CHECKED.** Attempt 17 is consumed.
* **For M5 (proposals, not authorization):**
  * choose a gadget function macOS can bind: **ECM** (kext already loaded here),
    **NCM**, or **CDC-ACM serial** with a getty/login on `ttyGS0` (macOS binds it
    and creates `/dev/cu.usbmodem*`; m1n1 proves it works);
  * if ECM or NCM is chosen, resolve the interrupt-endpoint question first
    (the `ncm-interrupt-ep-disabled` flag), ideally offline with the VM
    self-test;
  * a gadget with several functions would let one boot try more than one host
    path, at the cost of descriptor complexity;
  * add a check to the intake: confirm the loaded or available kext state with
    `kmutil showloaded --bundle-identifier … --show all`, not only the stub
    plist on disk.
* Everything else in boot036 (the three controllers, key-only dropbear, the
  SMC-less DT, the ATC-domain exclusion) can be kept as the baseline.

No media, raw target output or identifiers beyond the fixed gadget ones are
committed. Earlier reports are unchanged.

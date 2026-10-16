# Stage B attempt 18: macOS configures boot038's ACM + ECM gadget, then control transfers time out; no serial port, no network

2026-10-16. **One RAM attempt consumed. Controller PASS, no host panic.** The control
channel did **not** come up.

* **Controller:** exit 0 in 10.958 s, handoff 2026-10-16T20:22:28.529Z, every gate PASS.
  Launched once, after the read-only USB gate had failed for about six minutes (see
  "Before the launch"); nothing was opened or sent before the launch.
* **The Linux side matches attempt 17:** PID 1, one CPU, `online_cpus=1`; the release
  ladder ran (first step `atc3_usb_aon` at 19.42 s, no `atc0`-`atc2` or `smc_i2cm` name among
  the steps read, **`ladder complete: 50 domains released` at 45.024 s**); the 60 s milestone at
  **63.60 s**; heartbeats 000-022 to **113.70 s**; no reset. The human reports the screen was still
  updating minutes after the clip.
* **Host side:** the M1 enumerated the gadget **3.95 s** after the handoff (`1d6b:0104`,
  `bcdDevice 0x0038`, high speed) and macOS selected configuration 1 at **+8.45 s**, the same
  sequence as attempt 17. Then **control-endpoint transfers began timing out** (four timeouts from
  +9.57 s to +14.34 s, then a transaction error); attempt 17's host log (same filter, first two
  minutes) has none.
  **No interface node was ever published, no ACM or ECM driver attached, no `cu.usbmodem*` and no
  new `enX` appeared** in 60 s of polling. So: no serial log, no SSH.
* **M5 side:** port 1 reads `configured` from heartbeat 001 (8.51 s) to the end, but **`usb0 down
  rx=0 tx=0 no-ll`** the whole time (attempt 17: `usb0 up` with a link-local address at the same
  point). CDC-ECM raises its link only when the host selects the data interface's alternate setting 1,
  which never came.
* No `dwc3`, `apple-dart` fault or other error line was seen on the screen in the frames read.
* Fresh policy/default checks: **NOT CHECKED.** No retry or settings change.

## Reviewed inputs and controller execution

* M5 handoff `bd814ad` (published `5105c58`); M1 readiness `897fac7` (the launch ran on that commit,
  clean tree).
* Release `native-j716c-boot038`: archive 18,904,584 bytes, SHA-256
  `09f5a5d723461bccfba3c29aacb084c3318203d074e522c1527d650186e05f70`, verified against Git before
  extraction (GitHub's asset digest equal). Image `e0e53113…f3f7`, Stage-B DT `a676087b…efa5`
  (both byte-identical to boot036), initramfs `30800bdd…`. M1 independent review is in the readiness
  entry: the Stage-B initramfs differs from boot036's only in `/init`.
* One invocation through `build/native-intake/run-attempt18.py` (fsync per checkpoint; printed
  deadline 600 s):

| Item | Result |
|---|---|
| Invocation count | 1 |
| Start / handoff UTC | 2026-10-16T20:22:17.797 / 20:22:28.529 |
| Elapsed / exit | **10.958 s / 0** |
| Target, marker, secondaries | PASS: t6050, boot021 marker, none started |
| GPIO ADT | PASS: 221 pins / 7 groups, exclusions 5,6,7,112,141 |
| Board/framebuffer, DAPF layout and correction | PASS |
| Final hardware DT, framebuffer descriptor | PASS |
| kboot reply / USB close | PASS |

* **M1 host:** freshly restarted (uptime 10 min at the launch), `caffeinate -i` running, no panic
  report during or after the run (the newest report on file is attempt 15's).

## Before the launch (read-only gate)

After the human's fresh M1 restart, with the cable in the port used for attempt 17 and the M5 at
Running proxy, the M1's USB gate failed continuously from 20:13Z to 20:19Z (`InvalidFileException`:
the registry listed three USB controllers and no device; the port controller showed one connection,
at times with only the power-negotiation channel active). It passed at 20:21:58Z after the human
re-seated the cable. No port was opened and no launcher invocation was made before 20:22:17Z.
**Observation (Hypothesis):** this is the second fresh M1 restart in a row after which the M5's
proxy device was invisible until the cable was moved or re-seated (attempt 17's first launch was the
other). Suggest: re-seat the cable after the restart, then run the gate.

## Media and method

`Attempt18.MOV`: **120.558 s, 1080×1920 (portrait, oriented), 30 fps, original file** (240 MB),
user-supplied. It was first saved in the repository root (untracked) and moved into the ignored
inbox before any commit. Reviewed locally with AVFoundation: a 2 s and a 0.2 s brightness trace,
overview frames and upscaled crops; the text is fully legible. Review images deleted; media stays
local. Brightness is steady (48-55) from 10 s to the end: no blackout, no restart.

Time mapping: the single-frame brightness dip at video 5.2 s is the handoff, so
**kernel ≈ video − 5.2 s** (checked against heartbeats 000, 001, 002, 021 and 022 appearing where
that offset predicts, within 0.5 s). The clip ends at kernel ≈ 115.3 s.

## M5 screen, literal observations

| Kernel s | Observation |
|---:|---|
| 3.386 | `[ctl] USB control channel: CDC-ACM log port + CDC-ECM per UDC, IPv6 link-local, SSH key only` |
| 3.392-3.418 | `configfs-gadget.g1 gadget.0`: host MAC `02:69:6c:69:6f:01`, MAC `02:69:6c:69:6e:01`; `probe of gadget.0 returned 0 after 25958 usecs` |
| 3.425 | `[ctl] port 1: UDC 2a2280000.usb bound, ACM+ECM 1d6b:0104, interface usb0 up, log on ttyGS0; Linux end fe80::69:6cff:fe69:6e01<if>` |
| 3.450-3.453 | gadget.1 probe returned 0 after 24212 usecs; port 2: UDC `2aa280000.usb` bound, `usb1`, `ttyGS1` |
| 3.486-3.493 | gadget.2 probe returned 0 after 29974 usecs; port 3: UDC `382280000.usb` bound, `usb2`, `ttyGS2` |
| 3.495 | `[ctl] dropbear start 1: pid 58, port 22, key-only root` |
| 3.502 / 3.505 | heartbeat 000, `online_cpus=1`; `port1 not attached usb0 down rx=0 tx=0 no-ll | port2 not attached usb1 unknown … | port3 not attached usb2 unknown …` |
| **8.508 / 8.513** | **heartbeat 001: `port1 configured usb0 down rx=0 tx=0 no-ll`**; ports 2-3 `not attached`, `usb1`/`usb2` down |
| 13.516 | heartbeat 002, same states; two `apple-pmgr-pwrstate … sync_state() pending` notices at 13.546 (driver core, not power-offs) |
| 18.53, 23.54, … | heartbeats 003 onward, identical: port1 `configured usb0 down rx=0 tx=0 no-ll` |
| 19.424-44.513 | ladder steps 1-50: `atc3_usb_aon`, `isp_sys`, `uart6`…`uart0`, `uart_n`, `qspi`, `spi5`…`spi0`, `aes`, `i2c6`(digit read as 8)…`i2c0`, `aphy_gp_aus5`…, `apcie_*`, `ispsens0`, `dispext*_fe`, `ap_tmm`, `msg`, `gpio`, `dispext*_sys` (steps 1-30 and 34-50 read) |
| **45.024** | **`ladder complete: 50 domains released`** |
| 63.601 | `[diag] 60s elapsed; still alive. Observe the M5 framebuffer and the M1's new USB network interface.` |
| 108.694-113.713 | heartbeats 021 and 022 (the last in the clip): `port1 configured usb0 down rx=0 tx=0 no-ll`; ports 2-3 `not attached … down` |

* The status fields are: UDC state, interface, operstate, `rx_packets`, `tx_packets`, link-local
  address or `no-ll` (`init.c`, `status_line`). `usb0 down` and `no-ll` are therefore a link without
  carrier and no address, not a failed bind.
* No `[ctl] log streamer for port N exited` line, `dwc3` error, `-110` or `apple-dart … fault` line
  was seen; the DART fault counters were 0 in the early `/proc/interrupts` dump (3.5 s). The
  middle part of the ladder (steps 31-33) and the panel rows scrolled off were not read.

## M1-side observations (read-only; nothing written to the device, no network setting changed)

Host kernel log, times relative to the handoff (`T0 = 20:22:28.529Z`):

| T0 + | Event |
|---:|---|
| 0.27 s | m1n1's device destroyed (`hardware connection lost`) |
| **3.95 s** | `enumerated 0x1d6b/0104/0038 (iLinux J716c control channel, port 1)` at 480 Mbps; `device functionality blocked by transport restrictions`; `device will not be registered for matching` (the same two lines appear in attempt 17's log) |
| 8.44 s | macOS's accessory manager reports the accessory authorized (`GENERIC UNLOCKED`) |
| **8.45 s** | `AppleUSBCDCCompositeDevice selected configuration 1` (attempt 17: +8.17 s) |
| ~8.45 s | two user applications try to open the device and are refused (exclusive access held by the composite driver); also in attempt 17 |
| **9.57 / 10.77 / 11.99 / 14.34 s** | `AppleUSBIORequest … endpoint 0x00: status 0xe00002d6 (timeout): 0 bytes transferred` |
| 14.34 s | the same endpoint: status `0xe00002ed` (transaction error). No later USB line. |

* `ioreg` (USB plane at +4 s and +51 s, service plane at +8.5 s, +23 s and +105 s): the device is
  present (`1d6b:0104`, `bcdDevice 0x0038`, speed high, one configuration) with
  `AppleUSBCDCCompositeDevice` and user-client nodes below it, and **no `IOUSBHostInterface`
  child at any time**, so no driver could match an interface. For comparison, m1n1's own device
  shows four interface nodes with `AppleUSBACMControl`, `AppleUSBACMData` and `IOSerialBSDClient`
  below them.
* No `/dev/cu.usbmodem*` after the handoff; `ifconfig -l` unchanged (21 names). The capture script
  waited 30 s for an ACM callout and 60 s for a new `en` interface, found neither, and so sent
  nothing and ran no SSH. The device was still listed minutes later.
* Loaded-driver check before the launch (after the fresh restart): `com.apple.driver.usb.cdc.acm`,
  `…cdc.ecm` and `…cdc` loaded (1 line each).

## Interpretation (bounded)

**Confirmed:**

* boot038 reached the same Linux baseline as attempt 17 with the two-function gadget on all three
  controllers (probe 24-30 ms each, three `ttyGS` ports, dropbear): 50-domain ladder at 45.024 s,
  60 s milestone, heartbeats to 113.7 s, no reset.
* macOS enumerated and configured the device, but attached neither an ACM nor an ECM driver and
  never selected ECM's data alternate setting (`usb0` stayed down, `no-ll`).
* After the configuration the device stopped answering control transfers (host view: four timeouts,
  then a transaction error), while the M5 kept `configured`. Attempt 17's EEM gadget did not do this.

**Likely, not tested:** the change that matters is the interrupt-IN notification endpoint that
ACM and ECM each add (EEM used bulk endpoints only), which the ADT flags on these ports
(`ncm-interrupt-ep-disabled`). Enabling those endpoints happens when the host sets the
configuration, which is where the device went silent. This points at the dwc3 or PHY side of the
M5 and not at macOS; the M5 agent's hypothesis from the handoff is neither confirmed nor refuted.

**Alternatives not excluded:** a request from the macOS composite driver that this two-IAD device
does not answer; a Linux function's setup handler that never completes a control request.

**Unknown:** which function or request; whether the dwc3 core is wedged or only EP0 stopped; the
M5's kernel log after 3.5 s (no serial, no SSH; no dwc3 line reached the screen); whether the log
streamers ran, since no host opened a port.

**Host note:** the `blocked by transport restrictions` line is macOS's accessory authorization. It
lifted by itself 4.5 s after enumeration (the Mac was unlocked) and appeared the same way in attempt
17, so it is not what stopped this attempt; a locked or asleep M1 could hold it longer.

## Return and next handoff

* The human stopped filming (clip ends at kernel ≈ 115 s), reported the M5 screen still updating
  before shutting it down, powered the M5 off and returned to Macintosh HD (reported). Fresh
  policy/default/installed-object checks: **NOT CHECKED.** Attempt 18 is consumed; no retry or
  settings change. The E1 probe (fixed, re-verified offline) is still **NOT RUN**.
* **For M5 (proposals, not authorization):**
  * keep everything else (three controllers, DART mapping, ATC exclusion, key-only dropbear) and
    separate the variables: the next gadget should have **no interrupt endpoint**, for example a
    bulk-only vendor-specific function (`gser` or FunctionFS) that macOS leaves unbound and the M1
    reads from user space (libusb or IOUSBHost, no kext, no network settings). If the host then
    configures it without timeouts and bytes flow, interrupt endpoints are the problem; if the
    timeouts return, look elsewhere. The M1 can build and offline-test that reader once the
    function is chosen;
  * add controller state to the heartbeat so the screen alone names it: mount debugfs
    (`CONFIG_DEBUG_FS=y` in the shipped config; `init.c` mounts none) and print the dwc3 per-port
    `ep0state`, `link_state` and endpoint states next to the `[ctl]` status line;
  * in the next lab session, re-seat the cable after the M1's restart and run the read-only gate
    before the launch.

No media, raw target output or identifiers beyond the fixed gadget ones are committed. Earlier
reports are unchanged.

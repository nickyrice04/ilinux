# Our MTP transport: design

Status 2026-10-15: designed and drafted; the draft is `patches/0002-…patch`, compiled and linked in
the exact boot036 tree and exercised offline (README section 6); never booted. Facts and their evidence labels are in `README.md`; this file says
what we build from them and why.

## 1. Goal and non-goals

Goal: keyboard input on the M5 Max under native Linux (then the trackpad), through the pinned Asahi
`dockchannel-hid` driver, with the smallest change that handles the M4/M5 transport.

Non-goals: upstreamability (this work is private and derived from macOS analysis), the STM firmware
update, SMC GPIO support for t6050, multi-touch calibration, power management of the MTP.

## 2. Layering

```
 HID core  <-  hid-apple / hid-magicmouse / hidraw          (config delta)
    ^
 dockchannel-hid.c  (pinned 77cb8f24 + 0001 bounds patch + 0002 ring patch)
    |  dchid-ring.h : framing, checksum, ring consumer, command encoders  (portable, tested in userspace)
    |  dockchannel API : dockchannel_send / recv / await
    v
 apple,dockchannel (t6050 node, DT delta)      apple-dart (MTP stream, apple,dma-range)
    v                                              ^
 DockChannel FIFO  <---------- MTP firmware ---------+  writes the ring through the DART
```

One driver, two transports. `apple,t6050-dockchannel-hid` selects ring mode; `apple,dockchannel-hid`
(or `mtp_ring=0`) keeps the FIFO-era behaviour, which the harness checks stays byte-for-byte equivalent.

## 3. The ring transport

Device → host reports travel through a 2 MiB byte ring in coherent, DART-mapped memory
(`dmam_alloc_coherent`, the same mechanism the existing firmware upload uses). Host → device
messages are unchanged: framed commands through `dockchannel_send`.

* **Ownership.** The device is the only producer, the driver the only consumer. The driver writes
  nothing but the read index (and zeroes both indices once, before registration, and on a detected
  corruption). Barriers: `dma_rmb` between the index load and the data loads, `dma_mb` before the
  index store.
* **Trigger.** The RX thread of the DockChannel (`dockchannel_await` callback) drains the ring after
  every DockChannel message, exactly as macOS does; no timer in normal operation. `mtp_poll_ms`
  adds a debug timer so that a missing or unrecognised doorbell is observable instead of fatal.
* **One assembler, two sources.** `dchid_asm` reads 12 bytes, then the remainder, validates the
  checksum, and hands the message to the same `dchid_dispatch()` the FIFO path uses. A bad checksum
  drops that message only; a header or length error discards what is queued (the stream is out of
  step), counted in `ring_drops`.
* **Bounded work.** A drain performs at most 16384 reads; a corrupted index is reset instead of
  trusted; an oversized body waits for its bytes like macOS does and is then rejected by the
  checksum.
* **Serialisation.** `ring_lock` makes the RX thread, the poll timer and the handshake the same
  logical consumer (a mutex: all three may sleep, `dchid_dispatch()` allocates with GFP_KERNEL).
  `id_lock` guards `id_ready` and the deferred-interface list against the STM fallback timer.

## 4. Startup sequence in the driver

1. `probe`: helper RTKit device bound, ring allocated and zeroed, assembler buffer allocated, then
   `dockchannel_await` armed (as before).
2. First DockChannel message (any kind): schedule the handshake 100 ms later, once
   (`atomic_xchg`). The message itself is processed normally.
3. Handshake work: `{0xC1, 2}`, then `{0x91, 0, 0, IOVA, 0x200000}`, each as FEATURE SET_REPORT on
   interface 0 and each acknowledged (a failed acknowledgement is logged, the ring is drained
   anyway). Then one drain, because the acknowledgement or early input may already be in the ring.
4. Descriptors (`0xF0`) arrive, are parsed to the end of the payload, interfaces are created. An
   interface without a HID descriptor is not created yet (an inactive interface announces itself
   first and re-announces after its image download). Creation order: STM first.
5. `{0xB4, iface}` enable, HID device registration, ready event completes `iface->ready`.
6. If the STM has not reported ready 3 s after the first deferral, the deferred interfaces are created
   with a synthesised device id so the keyboard cannot be held back by the STM (ring mode only).
7. HID core opens the keyboard; reports flow `ring → assembler → dispatch → work → hid_input_report`.

Every management event is logged at info level in ring mode (id and the first 32 bytes) so the first
hardware run is a complete record of what the firmware says.

## 5. Behaviour differences guarded by `ring_mode`

| Area | FIFO mode (unchanged) | Ring mode |
|---|---|---|
| Init payload | stops after the transport block | runs to the end of the payload, handles blocks 3–6 |
| Ready event | always completes `ready` | status ≠ 0 → `inactive`, not completed |
| Acks | echoed report id, payload, flags all checked | transfer id (seq) and status byte only |
| Empty descriptor | n/a | not created until a descriptor exists |
| STM gating | wait forever | 3 s fallback |
| Type-0 empty frames | rejected as bad body length | ignored |

Module parameters (all 0444): `mtp_ring` (-1 follow the compatible, 0, 1), `mtp_enable_cmd`
(skip `0xB4`), `mtp_poll_ms`, `mtp_ring_size` (clamped 16 KiB..16 MiB, 16 KiB multiples).

## 6. Firmware path (trackpad)

`fw/mtfw_convert.py` runs on the Mac that owns the image and writes
`apple/tpmtfw-j716c.bin` (HIDF container: magic, version 1, header length 20, data length, interface
offset 0, then the CBOR). The existing `dchid_get_firmware` / `dchid_send_firmware` path loads it on
device open and sends `{0x95, 2, 0, iface, IOVA, size}`. The file is delivered to the boot
environment outside Git (initramfs staging); the DT node names it with `firmware-name`.

What is still missing for the trackpad and deliberately not drafted: the reset (macOS runs
`function-afe-reset` through SMC on the host; the driver still sends the FIFO-era `0x40` commands),
SMC function execution for `0xA0` actions, and calibration bytes (actions 6–9). They are
Unknowns 9 and 10 in the README; the 0xA0 handler already answers every request with a failure ack
so the firmware is never left waiting.

## 7. Failure handling

| Event | Behaviour |
|---|---|
| ring allocation fails | probe fails (`-ENOMEM`); no half-initialised state |
| no DockChannel traffic | nothing is registered, nothing is sent; `mtp_poll_ms` does not start before the handshake |
| handshake acknowledgement lost | error logged, drain still runs, `ring_registered` stays false |
| index out of range | error, both indices reset, assembler reset |
| checksum error | message dropped, queued messages kept |
| framing error / bad header length | queued data discarded (bounded), counted |
| unknown interface / unknown event | logged, ignored |
| STM never ready | 3 s fallback, keyboard created without STM identity |
| work allocation fails | message dropped (as the pinned driver) |

## 8. Alternatives considered

* **Poll the ring on a timer by default.** Rejected: macOS never does, it adds latency and wakeups;
  kept as a debug aid only.
* **Create a host→device ring as well.** Rejected: macOS creates none (`WriteSize 0`).
* **Separate driver for the M4/M5 transport.** Rejected for now: 90 % of the HID plumbing is shared,
  and keeping one file keeps the FIFO-era regression tests meaningful. Revisit if the behaviours keep
  diverging.
* **Handle the multi-touch image in the kernel (parse the XML plist).** Rejected: policy and
  complexity belong in userspace/initramfs tooling; the kernel only moves bytes.
* **Run the converter at first boot on the target.** Not possible: the Preboot volume of the M5 is not
  reachable from the Linux that is booting (and must not be touched).

## 9. How the draft is tested, and what that proves

| Layer | Test | Proves | Does not prove |
|---|---|---|---|
| framing/ring core | `ring/test_ring.c` (54871 checks), 12 mutants | arithmetic, wrap, corruption handling, encoders against hand-written bytes | the device's real data |
| driver | `driver-test/test_driver.c` runs the real file against a firmware model, 28 mutants | handshake order and fields, descriptor/ready/ack handling, ring drain incl. wrap and 1.7 KiB reports, error recovery, FIFO mode unchanged | that real firmware speaks the model; that the file builds in a kernel |
| syntax | `kshim.h` compile | no undeclared names, wrong members, arity | API prototype mismatches the shim itself hides |
| kernel build | job 042: 0001+0002 in the boot036 tree, `W=1`, Image link | the file compiles against the real kernel headers with no warning and links; symbols present | that it binds or runs |
| converter | `fw/test_mtfw_convert.py`, 19 mutants, real image structurally | encoding rules as read from macOS | byte equality with macOS |
| probe | `probe/test_mtp_probe.py`, 16 mutants | read-only by construction, plan addresses from ADT facts | the register semantics on real silicon |

## 10. Staging

1. **Keyboard first-light (E2).** boot036 + delta; success = `Ring registered`, `New interface
   keyboard`, key events on `/dev/hidraw*` over the existing SSH channel. Failure branches:
   * no `Initialized`/ring line → probe/DT problem (SID, `dma-range`, helper not bound) → E1 numbers;
   * handshake ack timeout → framing/handshake mismatch; the logged management events show what the
     firmware does say;
   * ack fine, no descriptors → doorbell/transport-of-descriptors question (Unknowns 1, 2): needs the
     poll timer, which the launcher's fixed arguments do not allow today (boot037 document, options A/B);
   * descriptors, no key events → report path or enable/ready gating (Unknown 8): try
     `mtp_enable_cmd=0`.
2. **Trackpad (E3)** after the SMC-function and calibration questions have an answer.
3. **Never needed:** STM update.

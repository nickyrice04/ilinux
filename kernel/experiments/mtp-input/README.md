# MTP input path (keyboard and trackpad) on the M5 Max, from this Mac's own macOS

**Status, 2026-10-15: analysis and offline preparation complete. Nothing in this directory
has run on the M5, nothing is committed. The patched driver compiles and links in the exact
boot036 kernel tree (VM job 042, offline); it has never been booted.**
Every claim below carries a label and a citation; the claims that decide whether the first
hardware run works are listed as Unknown in [section 9](#9-open-questions-unknown).

| | |
|---|---|
| Machine | MacBook Pro M5 Max (t6050, J716c), macOS 26.6.2 (25G83) |
| Why | Native Linux boots (boot035) but has no input: the keyboard and trackpad sit behind the MTP coprocessor, and M4/M5 firmware moved the HID transport onto a shared-memory ring that the pinned Asahi `dockchannel-hid` driver does not have. |
| Method | REA 6.4.0 + Ghidra 12.1.4 on the macOS kernel collection of this Mac, cross-checked with `llvm-objdump`, the live IORegistry (read-only `ioreg`), the sanitized ADT export and the pinned public Linux/m1n1 sources. |
| Output | This README (findings), `design.md` (our transport), a DT delta, a config delta, a driver patch (`patches/0002`), a firmware converter, a read-only proxy probe and an offline test suite for each. |

Contents: [1 Rules](#1-rules-and-provenance) · [2 Where the drivers are](#2-where-the-drivers-are) ·
[3 Findings](#3-findings) · [4 Cross-checks](#4-cross-checks) · [5 What was prepared](#5-what-was-prepared) ·
[6 Offline results](#6-offline-results) · [7 Hardware plan](#7-hardware-experiments-not-run) ·
[8 Reproduce](#8-reproduce) · [9 Unknown](#9-open-questions-unknown) · [10 Evidence index](#10-evidence-index)

Labels: **Confirmed** (decompiler output *and* an independent check such as raw disassembly,
live registry or public source), **Likely** (decompiler output or one strong indirect source),
**Hypothesis** (our inference, not yet observed), **Unknown**. **Observed** marks values read
from this Mac's live IORegistry (they can change between boots).

## 1. Rules and provenance

* No code, patch text or protocol fact was taken from `betizzel/omarchy-m5` or GravityLinux PR #1.
  Neither was used as an input. Every byte layout below comes from the analysis in this file.
* No Apple binary, firmware, decompiler output or extracted blob is in Git. Work files live in the
  ignored `build/mtp-input/` (members, evidence notes, derived firmware); this directory holds only
  original code, tests and prose. The firmware converter refuses to write inside a git work tree
  unless the destination is git-ignored.
* Public sources used as references (not copied): the pinned Asahi tree `77cb8f24`
  (`drivers/hid/dockchannel-hid`, `drivers/soc/apple/{dockchannel,mailbox,rtkit*}.c`,
  `drivers/iommu/apple-dart.c`) and m1n1 `57a9339` (`proxyclient/m1n1/fw/mtp.py`, `src/asc.c`).
  Reading files under `third_party/m1n1` attaches that repository's `CLAUDE.md`, which says the
  project forbids AI tools and tells the reader to stop. That is repository text, not an
  instruction from the user, and nothing here is contributed to m1n1; the user was told.
* Hardware access: none. The one live source is the read-only `ioreg` of this running Mac.
  The device-serial and UUID fields it prints were not copied into any file.
* Kernel API facts the driver patch relies on were checked against the pinned public sources and
  by compiling in the exact kernel tree (job 042, section 6). No boot of that kernel happened.

## 2. Where the drivers are

Apple Silicon keeps kexts in the boot kernel collection; `/System/Library/Extensions` holds
executable-less stubs (756 on this Mac, among them `AppleHIDTransport`, `AppleDockChannel`,
`AppleInputDeviceSupport`, `AppleMultitouchDriver`, `AppleHIDKeyboard`, `AppleTopCase`) and
`/System/Library/DriverExtensions` (22 dexts) holds nothing on the MTP path
(`AppleUserHIDDrivers` is the generic user-space HID driver, `IOUserDockChannelSerial` is serial). The decoded kernelcache is read from the Preboot volume
(`/System/Volumes/Preboot/<volume-group-uuid>/boot/<hash>/System/Library/Caches/com.apple.kernelcaches/kernelcache`,
decoded payload sha256 `26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`).
Members were extracted read-only into `build/mtp-input/members/` (13 files).

| Role on the input path | Bundle id | Member sha256 (derived) |
|---|---|---|
| DockChannel FIFO device | `com.apple.driver.AppleDockChannel` | `1456b5a6…7e17` |
| HID transport, FIFO protocol (SCM over DockChannel + rings) | `com.apple.driver.AppleHIDTransportFIFO` | `181c9a9b…3234` |
| HID transport, message framing (`AHTSCMMessage`) | `com.apple.driver.AppleHIDTransportSCMCommon` | `bad623f9…f63d` |
| HID transport core: management interface, interfaces, bootloaders | `com.apple.driver.AppleHIDTransport` | `889d5378…f3b7` |
| Shared memory manager, rings, image downloader, CBOR helpers | `com.apple.driver.AppleInputDeviceSupport` | `ec52c1b7…1492` |
| MTP coprocessor (ASC wrapper, RTKit) | `AppleA7IOP-ASCWrap-v6`, `com.apple.driver.RTBuddy` | `df3a175b…764b`, `e41f5311…48c1` |
| IOMMU | `com.apple.driver.AppleT8110DART`, `IODARTFamily` | `c57e7bea…e199`, `3fbde46a…7c12` |
| Consumers (not needed for Linux) | `AppleMultitouchDriver`, `AppleHIDKeyboard`, `AppleTopCaseHIDEventDriver` | |

Class chain for one keyboard report (macOS): `AppleDockChannel` → `AppleDockChannelDevice`
(`dcRead`/`dcWrite`/`dcReadAsync`, vtable +0x890/+0x898/+0x8a0) → `AppleHIDTransportDeviceFIFO`
→ `AppleHIDTransportProtocolSCMFIFO` (parses with `AHTSCMMessage`, drains `AIDCircularReadBufferShared`)
→ `AppleHIDTransportInterface` (`keyboard`, iface 2) → `AppleHIDTransportHIDDevice` → HID event drivers.

## 3. Findings

### 3.1 Topology (ADT `J716c`, live registry)

| Fact | Value | Label | Source |
|---|---|---|---|
| MTP ASC | `/arm-io/mtp`, `iop,ascwrap-v6`, role MTP, reg `0x294600000`+0x88000 (mailbox at +0x8000), irqs 676–679 (send-empty, send-not-empty, recv-empty, recv-not-empty), `iommu-parent` → mapper-mtp | Confirmed | ADT; m1n1 `src/asc.c` (`base + 0x8000` mailbox, `0x44` CPU control) |
| MTP firmware | RTKit image `J716_MtpFirmware.im4p` (`mtpf`), SRAM TEXT `0x294c00000`+0x54000 / DATA +0x6c000; already running when macOS starts (`AHTBootloadLoadImageResult 0, 0 ms` on the RTBuddy bootloader object) | Likely | ADT segments; live registry |
| DockChannel | `/arm-io/dockchannel-mtp` `dockchannel,t8002`, irq 660, six 0x1000 regs `0x294b00000/…14000/…30000/…34000/…28000/…2c000` = (unused)/irq/config/data/rmt-config/rmt-data, `fifo-size` 0x800, `channel-number` 0 | Confirmed (regs, irq); Observed (`fifo-size`, stripped from the sanitized ADT) | ADT; live registry |
| DART | `/arm-io/dart-mtp` `dart,t8110`, reg `0x294800000`+0xc000, page 16 KiB, `vm-base 0x10000004000`, `vm-size 0xffff0000`, `sid {0}`, `sid-count 16`, `remap` bytes (1→0)(2→0)(3→0)(4→0) | Confirmed | ADT |
| Interfaces | 0 `comm` (Management), 1 `multi-touch`, 2 `keyboard`, 3 `stm`, 4 `actuator`, 5 `tp-accel` | Observed | `bInterfaceNumber` in live registry; ADT children |
| Transport object | `AppleHIDTransportDeviceFIFO`, protocol `AppleHIDTransportProtocolSCMFIFO`, `hid-transport-mux "mtp-aop-mux"` | Confirmed | live registry; kext class symbols |

### 3.2 Message framing (host ↔ device, same on DockChannel and on the ring)

`AHTSCMMessage::init` `0x…185f9c`, `parseNewBytes` `0x…1861a8`, `calculateChecksum` `0x…186abc`,
`createMessage` `0x…186684`, `createControlMessage` `0x…186824`, `getRemainingSize` `0x…186104`.

```
byte 0      hdr_len        8 normally; parser accepts 6..8
byte 1      type           0x11 host->device command / device->host acknowledgement
                           0x12 device->host input report or event
                           0x00 parsed and ignored
byte 2..3   length         u16 LE = round_up(8 + payload_len, 4)         (body, excludes checksum)
byte 4      transfer id    matched against the pending command by the host
byte 5      interface      0 = management
byte 6..7   pad / status   byte 7 is a status on responses (0 = use the retcode below)
--- app header at hdr_len (8 bytes)
byte 0      flags          bits 7:6 report type (0 input, 1 output, 2 feature) | bits 5:0 request (0 SET, 1 GET)
byte 1      unused
byte 2..3   payload_len    u16 LE
byte 4..7   retcode        u32 LE
--- payload at hdr_len + 8, zero padded to 4
--- checksum u32 LE at hdr_len + length = ~(sum of the u32 LE words of header+body)
total = hdr_len + length + 4;  smallest message = 12 bytes (empty body)
```

| Claim | Label | Evidence |
|---|---|---|
| Layout and checksum above | **Confirmed** | `parseNewBytes`/`createMessage` pseudocode and raw `llvm-objdump` of `createMessage` (`length = (len + 0xb) & ~3`) and the checksum (word sum, `mvn`); independent public corroboration for the FIFO era: m1n1 `mtp.py` `MTPProtocol.send/read_pkt` builds `<BBHBBH` = (8, 0x11, len, seq, iface, 0) and `0xffffffff - sum(words)` |
| Read 12 bytes first, then the remainder | Confirmed | `getRemainingSize`: `cur < 12 ? 12 - cur : length + hdr_len + 4 - cur` |
| Parser error states 0xfc (header too long), 0xfd (too big for buffer), 0xfe (overrun), 0xff (checksum) | Confirmed | `parseNewBytes` |
| Acknowledgements are matched by transfer id only; status comes from byte 7 / retcode | Likely | `handleControlReport` `0x…176bec` pseudocode (no flags comparison seen) |

Differences from the pinned Linux driver: Linux additionally requires the echoed report id and
at least one payload byte in every acknowledgement and compares the acknowledgement's flags with
the command's. Neither check exists in `handleControlReport` (Likely), so the patch relaxes both
in ring mode only.

### 3.3 The shared-memory ring

`AIDCircularBufferShared::init` `0x…22d6b4`, `AIDCircularReadBufferShared::read` `0x…22dd58`,
`AIDCircularWriteBufferShared::write` `0x…22e54c`, `AIDSharedMemoryManager::createSharedMemoryFifo`
`0x…22c5d4`, `readSharedMemoryFifo` `0x…22cb00`.

```
offset 0   u32 write index   (producer; byte offset into the data area)
offset 4   u32 read index    (consumer)
offset 8   data[size - 8]    byte stream of consecutive framed messages, no per-entry header
```

* Consumer (host): `avail = W >= R ? W - R : cap + W - R`; copy in at most two segments;
  `R = (R + n) % cap`; full barrier; store read index. Producer leaves one byte free.
  **Confirmed** (pseudocode + raw disassembly of init/read/write).
* macOS creates exactly one such FIFO, device→host, 2 MiB: live `MemoryFifos = [{ReadSize 2097152,
  WriteSize 0}]`, published `MemoryFIFOs = [{Address 0x100_0002_8000, Size 0x200000}]`.
  **Observed**; the address is one boot's IOVA and lies inside the DART window.
* There is no host→device ring: every host report goes through `AppleDockChannelDevice::dcWrite`
  (`SCMFIFO::setReportGated` `0x…1744f0`). Reports longer than `MaxDockFIFOReportLength` would use a
  typed shared buffer (below); **Confirmed** for the absence of write-FIFO creation, Unknown for the limit.
* Live protocol config (Observed): `MaxReadSize 16384`, `MaxWriteSize 16384`, `AllowReportTimeout Yes`.

### 3.4 Startup (what the host does, in order)

`SCMFIFO::handleStart` `0x…16f2a0` (DeviceFIFO) → `cacheProtocolConfig` `0x…17b8e4` → first DockChannel
bytes → `readCompletionAction` `0x…17114c` → 100 ms → `handshakeGated` `0x…17c9fc`.

| Step | Report (all FEATURE SET_REPORT on interface 0, flags 0x80) | Label |
|---|---|---|
| 1. First bytes on the DockChannel FIFO arm a one-shot 100 ms timer; interfaces are created from the personality list | | Confirmed |
| 2. System awake | `{0xC1, 0x02}` (2 bytes; `0x01` = asleep) via `setSystemAwakeReport` `0x…1720ec` | Confirmed (raw `strh 0xc1`, `strb 1 + (awake != 0)`) |
| 3. Register each memory FIFO | `{0x91, 0x00, 0x00, u64 IOVA @3, u32 total_size @11}` (15 bytes, total size includes the 8-byte index header) via `registerSharedMemory`/`handshakeGated` | Confirmed |
| 4. Per interface needing an image | `performBootload` `0x…1788e4` (section 3.8) | Confirmed |
| 5. Per interface after its descriptor is complete | `{0xB4, iface}` (enable) via `descriptorComplete` `0x…128304` | Confirmed |
| Per-interface typed buffers | `{0x95, type, 0x00, iface, u64 IOVA @4, u32 size @12}` (16 bytes); type 2 firmware, type 3 large report | Confirmed |

Public cross-check: m1n1 `mtp.py` defines the same three shapes for the M1/M2 FIFO era
(`InitBufMsg` 0x91, `InitAFEMsg` 0x95 with `unk1 = 2`, `UnkMsgC1` 0xC1, `DeviceEnableMsg` 0xB4), so
the command set is the same family; what is new on M4/M5 is that 0x91 is the *only* way device→host
reports flow, and the ring replaces the FIFO for them (Likely).

**Doorbell.** The ring has no interrupt. After every DockChannel read completion and after every
power-state change the host drains all registered rings (`drainSharedMemoryFifos` `0x…176288`,
`…FromThread` `0x…172e8c`, called from `powerHasChanged` `0x…172228`); there is no timer
(**Confirmed**, xrefs). Therefore the firmware must put something on the DockChannel FIFO after writing
to the ring. What it puts there is **Unknown**: the host reads and parses it with the normal framing
(≥ 12 bytes), so the first hypothesis is "any well-formed message, possibly type 0 with an empty
body". The driver patch accepts exactly that and drains afterwards whatever it was.

### 3.5 Management interface (interface 0), device → host

`AppleHIDTransportManagement::handleReport` `0x…1219b8`.

| Report id | Meaning | Layout | Label |
|---|---|---|---|
| `0xF0` | interface descriptor | 22-byte header `{0xF0, u16 version (<2), iface, name[16], u16 more_packets}` then TLV blocks `{u16 type, u16 len ≤ 0x7ff}` | Confirmed (`parseDescriptor` `0x…1261dc`) |
| | block 0 | HID report descriptor | Confirmed |
| | block 1 | config entries: `{u16 unk, u16 id, char name[32]}` (Linux calls it a GPIO request); builds the interface's `ExternalResources` {name → id} | Confirmed (block), Likely (property use) |
| | block 2 | transport (6 bytes; version byte 0 required, type 0 HID / 2 mux) | Confirmed |
| | block 3, 4, 5, 6, 7 | serial number; ready status (u16: 0 HID, 1 inactive); available interfaces; location id; product name | Confirmed |
| `0xF1` | ready | `{0xF1, iface, u16 status}` (4 bytes); status ≠ 0: macOS sets the interface type to *invalid* (error string "Cannot set interface type to invalid") and still runs `ready()` | Confirmed (`handleReady` `0x…121cb0`) |
| `0xF2` | wake | `{id, iface, u64 timestamp @2}`, ≥ 10 bytes | Confirmed |
| `0xA0` | config / resource request | 20 bytes: `[1] iface, [2..3] resource id u16, [4..7] action u32, [8..11] reason u32, [12..19] timestamp u64`; actions 6..9 carry `u32 length @0x14` + data after a 0x18-byte header | Confirmed (`handleConfigRequest` `0x…1225c8`; log string "interface %u, resource %u, action %u, reason %u, timestamp %llu") |
| `0xA2` | reset request | `{id, iface}`; refused after repeated bootload failures | Confirmed (`handleResetRequest` `0x…122bd8`) |
| `0xA3`/`0xA4` | memory dump request / response | | Confirmed |
| `0xB5` | AHT function request | ≥ 0x1c bytes: iface @2, length u32 @0x18, payload @0x1c; run by `AHTFunctionExecutor` | Confirmed (`handleAHTFunctionRequest` `0x…123ef4`); semantics Unknown |
| `0x96/0x97/0x43/0x9A` as input-report ids on iface 0 | release shared memory / memory dump / toggle power request / FlatPack bootloader message | | Confirmed (`handleInputReport`) |

**Config request actions** (`externalResourceActionGated` `0x…12b6b0`). The resource id is looked up in the
interface's `ExternalResources`; the name selects an ADT `function-<name>` property, executed as an
"AHT function" (an SMC pin or key on this hardware):

| Action | Effect | Host replies |
|---|---|---|
| 0 | pulse: set 1, sleep 50 ms, set 0 | no |
| 3 | same pulse | yes |
| 1 / 4 | set 0 | no / yes |
| 2 / 5 | set 1 | no / yes |
| 6 / 7 | call the function with the bytes supplied in the request | no / yes |
| 8 / 9 | call the function with the bytes of the interface (or `DefaultProperties`) property whose name is supplied | no / yes |

Reply (`handleConfigResponse` `0x…12c278`, sent by `sendConfigReport` `0x…12872c` as FEATURE SET_REPORT on
iface 0): 25 bytes `{id, u32 status, the 20 request bytes}`; id is a per-object field (Likely 0xA1).
**This is exactly the layout of the pinned Linux driver's 0xA0/0xA1 exchange** (`dchid_gpio_cmd` /
`dchid_gpio_ack`, command 3 = pulse), widened: Linux's `cmd` byte is the low byte of macOS's u32 action
and its `gpio` byte the low byte of the u16 resource id. Public cross-check: m1n1 `GPIORequestMsg` /
`GPIOAckMsg` (`cmd == 3` pulses the SMC key twice).

### 3.6 Keyboard path

| Claim | Label | Evidence |
|---|---|---|
| The keyboard is interface 2, a plain HID device; its report descriptor arrives in descriptor block 0; reports arrive as type 0x12 messages on iface 2 (`handleInputReport` → `iface->vfn(+0xa08)`) | Confirmed | `handleInputReport` `0x…1767ec`; live registry (`HIDDescriptor` present on `keyboard`) |
| It needs **no firmware**: no `image-tag`/`bootloader-type`, no `AHTBootloadLoadImage*` properties; base `AppleHIDTransportBootloader::needsFirmwareAtBoot` returns 1 (`0x…107f0c`) but no bootloader is attached to `keyboard` | Confirmed | live registry; `performBootload` |
| Layout id and country code come from the ADT (`kblang-calibration` etc.), as the Linux driver reads `hid-country-code` / `apple,keyboard-layout-id` from DT; m1n1 `dt_set_ipd()` already resolves the `keyboard` alias | Likely | live registry; m1n1 |
| The `stm` interface (3) gives the device id/serial in macOS; the pinned Linux driver defers every other interface until it is ready | Likely | `dchid_handle_ready` (Linux) |
| STM is an ST microcontroller: image `J716C_InputDevice.im4p` (`ipdf`), bootloader type `HIDDevice`; its bootloader class overrides `needsFirmwareAtBoot` to return **0** (`0x…13d8ec`) and `loadFirmware` returns `kIOReturnUnsupported` (`0x…13d8dc`); it only runs `doFirmwareUpdate` (`0x…137868`) through chunked HID writes when a version/signature check says so | Confirmed | decompiler |
| So the keyboard should work without any image and without STM firmware work; the driver patch carries a 3 s fallback so a not-ready STM cannot hold the keyboard back | Hypothesis | |

### 3.7 Trackpad

| Claim | Label | Evidence |
|---|---|---|
| The multi-touch interface (1) has `image-tag "wftm"`, `bootloader-type "CBOR"`, `PowerMethod 2`, `function-afe-reset`, `reset-sequence`/`power-sequence`, `hid-merge-personality "C1FD2,3"`; its HID descriptor (0x6d7 bytes, report ids 2/0x3f/0x44) and `MaxInputReportSize 1752` | Observed | live registry |
| It needs a firmware download: base class `needsFirmwareAtBoot` = 1 and `AppleHIDTransportBootloaderCBOR` does not override it | Confirmed | `0x…107f0c`; symbol search |
| Source on this Mac: `/System/Volumes/Preboot/<volume-group-uuid>/restore/Firmware/J716c_Multitouch.im4p` (112731 bytes, sha256 `98bf7a99…a55c`; identical copy in each restore bundle; also in the IPSW). Name pattern `<BOARD>_Multitouch.im4p`. Not under `/System` | Confirmed | file system |
| Container: DER `SEQUENCE{IA5 "IM4P", IA5 "mtfw", IA5 "1", OCTET STRING}`, no KBAG, no compression element, payload 112706 bytes | Confirmed | parsed |
| Payload: a NUL-terminated **XML-serialised OSObject graph** (not binary, not an ftab; the `rkosftab` path of `extractFromFtab` is for the MTP RTKit image `mtpf`). Top level `{"C1FD2,3": [14 steps]}`; elements `dict/array/key/string/integer/data/true/false` with `ID`/`IDREF` sharing; the key equals the interface's `hid-merge-personality` | Confirmed | parsed; `beginFirmwareDownload` `0x…2378f8` ("Unserializing payload with %u bytes") |
| The 14 steps are a script for the MTP's CBOR bootloader: 7× `ReadModifyWrite` on ASIC registers (`Address`, `Mask`, `Value`), 4× `Binary`/tagged data (65248 B and 10908 B code at `0x0` / `0x400a00`; `TCAL` 2492 B and `FCAL` 392 B marked "dummy" calibration), `RequestCalibration`, one more `ReadModifyWrite` (`SkipCheck`), and a final `Config` dictionary | Confirmed | parsed (structure only; values are not reproduced here) |
| macOS passes the whole dictionary to `encodeObject` (`handleLoadImage` `0x…118294`; no sub-selection) and sends the CBOR through a type-2 typed buffer (`0x95`) | Confirmed | decompiler |
| CBOR rules (`encodeObject` `0x…1191dc`, helpers `_cbor_get_varuint_size` `0x…22aeb4`, `_cbor_write_varuint_unsafe` `0x…22aef4`, `_cbor_insert_alignment_tags` `0x…22b008`): number → major 0 with the **low 32 bits**; bool → `0xf4`/`0xf5`; string → major 3, length **strlen + 1**, NUL included; data → major 2 preceded by `0xd3` filler tags so the content starts 4-byte aligned; array → major 4; dictionary → major 5, keys as strings, in insertion order; heads are standard CBOR big-endian (1/2/3/5/9 bytes) | Confirmed | decompiler + raw disassembly of the number path (`mov w21, w0`) |
| `mtfw_convert.py` reproduces that encoding and wraps it in the HIDF container the Linux driver loads (`apple/tpmtfw-j716c.bin`); the real image converts to 81396 CBOR bytes, no truncated integers | Likely (byte-for-byte match with macOS untested: needs a macOS-side capture or a hardware run) | `fw/` |
| After the download macOS calls `resetDevice(0)` then `resetDevice(2)` and waits for the ready report; for `PowerMethod 2` these run the ADT sequences on the **host** through SMC functions, not a `0x40` command | Confirmed (sequence, absence of 0x40) / Hypothesis (that the device ignores 0x40) | `performCBORBootload` `0x…178fc4`; `setPowerGated` `0x…10c1a4` |
| `function-afe-reset` is `<phandle 0x281 (smc-pmu), 'pKW8', 'pcIO', 0x00010000, 0x011c0000>`; `reset-sequence` = `"function-afe-reset\0" 32 00 01 00`, `power-sequence` = `… 00 32 00 01`: per entry `{enable delay ms, disable delay ms, enable type, disable type}`, delay ×1000 → µs (`AHTFunctionInfo::init` `0x…142fd4`); types name None/High/Low/AltFunc/Input/Config0/Config1/Read (`call` `0x…1430a0`) | Confirmed (layout, delay unit) / Unknown (legacy type byte → name map, SMC key semantics) | decompiler |
| The calibration data the image calls "dummy" is supplied by the host on request (config actions 6–9) | Hypothesis | `RequestCalibration` step + `externalResourceActionGated` |

**What the trackpad therefore needs from Linux**: (1) the CBOR image through a type-2 buffer, (2) a way
to run SMC functions (AFE reset pulse; SMC GPIO is not supported for t6050 in the pinned tree),
(3) answers to 0xA0 requests, (4) probably calibration bytes. (1) and the 0xA0 plumbing exist after patch 0002;
(2) and (4) are future work and are **not needed for the keyboard**.

### 3.8 Image loading and the other two images on this Mac

| Image | Type | Used for | Boot-time? |
|---|---|---|---|
| `J716_MtpFirmware.im4p` (856656 B, sha256 `274762ac…bc28`) | `mtpf`, payload starts `00000000 ffffffff` (rkosftab) | MTP RTKit firmware (`AppleHIDTransportBootloaderRTBuddy`, tag `fptm`) | loaded by iBoot before the OS (Likely) |
| `J716c_Multitouch.im4p` (112731 B) | `mtfw` | trackpad AFE script, CBOR bootloader | yes |
| `J716C_InputDevice.im4p` (101460 B, sha256 `cd2adacf…27c9`) | `ipdf` | STM update program: `DeviceMatching`, report-id variable definitions (0x10 DeviceInfo, 0xb8 ChunkSize, 0xbb Versions, 0x13 IsProdSigned, 0xb4 ST Version, 0x17 Payload Digest), version/signature `Branch` checks, `SetReport 0xb0`, `ChunkedWrite 0xb1` (71284 B), `SetReport 0xb2`, `GetReport 0xb2`, `SetReport 0xb3`, 10 s `Delay` | no (update only) |

### 3.9 DART and the MTP's address space

| Claim | Label | Evidence |
|---|---|---|
| macOS maps the FIFO inside `vm-base 0x10000004000` / `vm-size 0xffff0000`; the one live IOVA is `0x100_0002_8000` | Observed | live registry |
| SIDs 1–4 are aliased to 0 by the `remap` bytes; `AppleT8110DART::_dartSetup` `0x…98a744` sets up the t8110 stream tables | Confirmed (ADT) | ADT; decompiler |
| Linux needs `apple,dma-range <0x100 0x4000 0x0 0xffff0000>` on the DART node (pinned `apple-dart.c` parses `apple,dma-range` as `u64[2]`) and has no software SID remap, so the MTP devices use one SID | Confirmed (code) | pinned `apple-dart.c` |
| Which SID: `iommus = <&mtp_dart 1>` (Asahi M2/M3 convention) with 0 as the fallback | Likely | `make_mtp_dt.py --sids` |
| The DART register block starts at +0 of the 0xc000 ADT region (m1n1 `dart_init_adt`), not +0x8000 | Likely (m1n1), open for the probe | m1n1 |
| m1n1 applies DAPF index 1 of `/arm-io/dart-mtp` (`dapf.c:174`) and does not apply DART tunables | Confirmed | m1n1 source |

## 4. Cross-checks

**ADT versus macOS** (`hardware/adt/adt-sanitized.json`, `mtp_adt.py` asserts every value):

| Item | ADT | macOS runtime |
|---|---|---|
| Interfaces and numbers | children of `mtp-transport` | `bInterfaceNumber` 1..5 (live) |
| FIFO IOVA window | `vm-base`/`vm-size` | `MemoryFIFOs` Address inside the window (live) |
| DockChannel registers | six regs | `AppleDockChannel` maps six windows (class symbols) |
| Resource functions | `function-afe-reset`, `function-stm-reset` | `externalResourceActionGated` looks up `function-<name>` |

**Pinned Linux `dockchannel-hid` versus macOS (ring era)**:

| Aspect | Linux (FIFO era) | macOS on this Mac | Patch 0002 |
|---|---|---|---|
| Device → host input | DockChannel FIFO only | one 2 MiB ring, drained after DockChannel traffic | ring consumer in the RX thread |
| Handshake | none | 0xC1 then 0x91, 100 ms after first traffic | same, in a delayed work |
| Init blocks | stops at the transport block | continues (serial, ready status, interfaces, location, product) | parses to the end in ring mode only |
| Ready event | always "ready" | status ≠ 0 marks the type invalid | not completed in ring mode (interface flagged unusable) |
| Acks | echo of report id + flags required | transfer id and status | relaxed in ring mode |
| Interface reset | `0x40` command | host-side SMC sequence | `0x40` still sent (harmless if ignored; Hypothesis) |
| Config request | cmd 3 = pulse, GPIO required | actions 0–9, function via SMC | unchanged: only 3, replies failure when no GPIO |

## 5. What was prepared

| Item | File | Purpose |
|---|---|---|
| ADT facts | `mtp_adt.py` | extracts and asserts every MTP value from the sanitized ADT |
| DT delta | `make_mtp_dt.py`, `test_mtp_dt.py` | adds `mtp`, `mbox`, `fifo` (DockChannel) + `input` + interface nodes, fixes the DART node, adds the `keyboard` alias; proves nothing else changed |
| Config delta | `check_config.py` | `APPLE_RTKIT_HELPER=y`, `HID_APPLE=y`, `HID_MAGICMOUSE=y`, `HIDRAW=y` (+ recommended `FW_LOADER_USER_HELPER=n`) against a kernel `.config`, with preconditions |
| Ring/framing core | `ring/dchid_ring.h` (+ `test_ring.c`, `mutate_ring.py`) | portable framing, checksum, ring consumer/producer, command encoders, TLV walker |
| Driver patch | `patches/0002-dockchannel-hid-mtp-ring-transport.patch` | the ring transport inside the pinned driver (on top of `driver-contracts/…/0001`) |
| Driver checks | `driver-test/` (`check_driver.py`, `kshim.h`, `test_driver.c`, `mutate_driver.py`) | applies 0001+0002 to the pinned source, syntax-checks, runs the real driver code against a firmware model |
| Firmware converter | `fw/mtfw_convert.py` (+ tests, `mutate_fw.py`) | IM4P → HIDF; refuses non-ignored output paths |
| Read-only probe | `probe/mtp_probe.py` (+ tests, `mutate_probe.py`) | DART / ASC / DockChannel register reads through the m1n1 proxy; prepared for the M1 agent |
| Kernel-side VM job | `virtualization/jobs/042-mtp-input/{run.sh,host-run.sh}` | applies 0001/0002 to a private copy of the boot036 tree, config delta, `W=1` build of the driver, Image link, symbol check, gcc/glibc harness, checkpatch, DT candidate through dtc/dt-validate (offline, takes the `vm` lock, about 45 s) |
| One command | `check_all.py` | runs everything above except the VM job offline |
| Design | `design.md` | the transport design and the staged plan |
| M1 hand-over | `m1-instructions.md` | what the M1 agent runs after approval, and what it reports |

`make_mtp_dt.py` imports `../usb-gadget-dt/fdtedit.py`, a sibling experiment that is still
uncommitted at the time of writing; the two directories have to be committed together.

## 6. Offline results

Run with `python3 -I check_all.py --repo <asahi-linux clone>` (2026-10-15, macOS 26.6.2, Apple clang 21):

| Step | Result |
|---|---|
| DT delta unit tests | 21 tests OK (13 deliberate mistakes rejected) |
| DT build on the boot035 Stage-B DTB (sha256 `b1105bbf…86db`) | structural check PASS; only the listed nodes added, DART node edited, alias added |
| Config delta against boot035's `kernel.config` | 4 changes + 1 recommended; 13 preconditions met; 0 unmet |
| Ring/framing core tests (ASan + UBSan) | 54871 checks, 0 failures; 12/12 mutants caught |
| Driver patch | base `15c1186c…b2f` → 0001 `e888ddae…5605c` → 0002 applies cleanly; patched driver `01c56449…23e4`; `dchid-ring.h` byte-identical to `ring/dchid_ring.h` |
| Driver syntax check against `kshim.h` | no errors (implicit declarations and pointer mismatches are errors) |
| Driver behaviour harness (real driver code, firmware model, ASan + UBSan) | 39483 checks, 0 failures; 28/28 mutants caught |
| Firmware converter | 27 tests OK (incl. the real image structurally); 19/19 mutants caught |
| Probe | 26 tests OK; 16/16 mutants caught |

VM job 042 (2026-10-15 22:40Z, `vm` lock taken and released, host untouched otherwise; the boot036
tree `/var/tmp/ilinux-boot036/linux` whose Image is the packaged one, sha256 `e0e53113…ef3f7`):

| Step | Result |
|---|---|
| Tree driver | pinned `15c1186c…b2f`; 0001 applied by the job; 0002 applies; result `01c56449…23e4`; `dchid-ring.h` identical to `ring/dchid_ring.h` |
| Config delta | `.config` differs by exactly `HIDRAW`, `HID_APPLE`, `HID_MAGICMOUSE`, `APPLE_RTKIT_HELPER` = y (plus two new "is not set" lines the dependencies reveal); `HID_DOCKCHANNEL` and `APPLE_DOCKCHANNEL` already y; `check_config.py` 13/13 preconditions |
| Driver compile, gcc, `W=1`, arm64 | **0 warnings** in `dockchannel-hid.c` / `dchid-ring.h` |
| Image link | succeeds; `dchid_ring_drain`, `dchid_handshake_work`, `dchid_dispatch`, `dchid_stm_fallback_work`, `dockchannel_hid_driver`, `dchid_cfg_ring` present; Image sha256 `6fb8c371…6ed9`, identical across two runs (build time/user/host pinned) |
| Harness rebuilt with gcc + glibc (ASan/UBSan) | 39483 checks, 0 failures |
| checkpatch (informational) | `dchid-ring.h`: 0 errors, 4 warnings, 5 checks (volatile in the userspace branch, `uint8_t` typedefs, one 102-column line); `dockchannel-hid.c`: 5 errors, 11 warnings, 17 checks over the whole file, a mix of the pinned file's own style and our additions |
| DT candidate (boot036 Stage-B + delta) | dtc: no new warnings; dt diff +61/−1 lines; `dt-validate`: 0 findings before, 6 after, all "no schema": the pinned tree has no binding for `dockchannel-hid` (`apple,fifo-size`, `apple,helper-cpu`, `hid-country-code`, `apple,keyboard-layout-id`) and `apple,dart.yaml` does not list `apple,dma-range` although `apple-dart.c` parses it |

What these do **not** show: that the firmware behaves like the model (that is the hardware
experiment), that the kernel boots or the driver binds on the M5, or that the converter's output
matches macOS byte for byte.

## 7. Hardware experiments (NOT RUN)

**2026-10-19, attempt 26 (prepared, NOT RUN): E2 now runs as boot042 over SSH, and E1 is no longer needed
first.** boot042 (`native/boot/boot042-keyboard-modules-2026-10-19.md`, VM job 050) builds this driver and
its helpers as modules on boot041's tree, so they load one at a time from the Omarchy root's SSH session
(`ilinux-keyboard`, job 045's link overlay) after the USB link is up; module parameters such as
`mtp_poll_ms=100` are passed to `modprobe` there, so the launcher's fixed arguments no longer matter. The
DT gives the MTP DART streams 0-4 instead of 1 (the ADT remaps 1-4 to 0, and apple-dart's reset clears a
t8110 remap), and `ilinux-keyboard` checks the DART's probe line (16 KiB pages, not locked) before loading
anything, which answers E1's register-base and lock questions in the attempt itself. The table below is
the original plan.

All need the user's approval; the M1 agent runs them with the existing lab procedure
(`m1-instructions.md`). Order and what each result decides:

| # | Experiment | Touches | Decides |
|---|---|---|---|
| E0 | `check_all.py` on the M1 host | nothing | the checkout is intact |
| E1 | `probe/mtp_probe.py read` in one human-started RAM session | proxy, 32-bit reads only | DART register base (+0 vs +0x8000), SID(s) iBoot left translating, ASC running, mailbox layout, DockChannel FIFO depth; fixes `--sids` and the DART `reg` |
| E2 | boot037 candidate = boot036 + config delta + patches 0001/0002 + DT delta, built offline and checked by `native/boot/mtp_input.py` (`build/native-boot037/`, archive sha256 `3900924b…`, not committed; details in `native/boot/boot037-mtp-input-2026-10-15.md`). The launcher's fixed-argument rules do not allow `dockchannel_hid.mtp_poll_ms=100`, so the first run has no poll timer | native boot, over the existing USB control channel | do `Ring registered` and `management event 0xf0 … keyboard` appear; does `hid-recorder`/`evtest` on the keyboard hidraw show key events; does the ring ever hold data without a doorbell (poll counter) |
| E3 | trackpad: firmware file in the initramfs, an SMC-function provider, answers to 0xA0 | native boot | whether the AFE comes up (needs the Unknowns in section 9) |

## 8. Reproduce

```sh
# kernel-side checks in the job VM (offline; takes the vm lock; ~45 s)
WAIT=1 virtualization/jobs/042-mtp-input/host-run.sh mtp-input

# offline suite (nothing touches hardware; the clone only supplies the pinned driver source)
python3 -I kernel/experiments/mtp-input/check_all.py \
  --repo ../apple-silicon-linux-research/third_party/asahi-linux

# derive the firmware file on the Mac that owns the image; never commit the output
python3 -I kernel/experiments/mtp-input/fw/mtfw_convert.py \
  "/System/Volumes/Preboot/<volume-group-uuid>/restore/Firmware/J716c_Multitouch.im4p" \
  build/mtp-input/fw-out/tpmtfw-j716c.bin
MTFW_REAL_IM4P=<that .im4p> python3 -I kernel/experiments/mtp-input/fw/test_mtfw_convert.py

# candidate DTB (DT only)
python3 -I kernel/experiments/mtp-input/make_mtp_dt.py \
  build/native-boot035/verified/t6050-j716c-stage-b.dtb hardware/adt/adt-sanitized.json \
  build/mtp-input/dt/out.dtb build/mtp-input/dt/delta.json --sids 1 --dts build/mtp-input/dt/new.dts
```

REA reproduction: open the derived member (`build/mtp-input/members/<name>.macho`, derivation script
`list_members.py`/`derive_all.py` kept in the ignored work area) and decompile the addresses in
section 10; the helper `disasm.py` gives the independent `llvm-objdump` view. Decompiler output has
cold-block and function-merge artefacts (`parseNewBytes` merges the following drain function);
every layout marked Confirmed was re-read in raw disassembly.

## 9. Open questions (Unknown)

1. **Doorbell content.** What the firmware writes to the DockChannel FIFO after filling the ring.
   Handled defensively (any framed message triggers a drain, type-0 empty frames are ignored,
   `mtp_poll_ms` drains on a timer for diagnosis).
2. **Where the descriptors travel.** Whether `0xF0` interface descriptors arrive through the ring
   or the DockChannel FIFO on M5. Both paths dispatch identically.
3. **Which SID** the MTP ASC and the DockChannel DMA use (Likely 1 in Asahi style; macOS aliases
   1–4 to 0). E1 answers it.
4. **DART register base** (+0 vs +0x8000 of the ADT region). E1 answers it.
5. **SRAM window size** for `reg` of the RTKit helper node (1 MiB assumed from the first firmware
   segment).
6. **RTKit compatibility**: whether the pinned `rtkit-helper` driver can handle `iop-version 1`
   (`rtbuddy-v2`) MTP firmware on ASC v6 without changes.
7. **Ack flags and status byte**: the real firmware's acknowledgement header (the patch accepts a
   bare acknowledgement and a zero or echoed flags byte).
8. **Whether the firmware gates input on the 0xB4 enable and the ready event** the way FIFO-era
   firmware did; `mtp_enable_cmd=0` exists to test without it.
9. **Trackpad reset**: the legacy function-type byte → name mapping, what `pKW8`/`pcIO` mean, and
   whether the AFE needs a pulse after a cold iBoot start. SMC GPIO for t6050 does not exist.
10. **Calibration**: where macOS gets the bytes for the "dummy" calibration blobs
    (`RequestCalibration`, actions 6–9) and whether the trackpad runs without them.
11. **Converter fidelity**: byte-for-byte equality with what macOS sends (the number truncation and
    filler placement come from the decompiler; a capture would settle it).
12. **`MaxDockFIFOReportLength`** and the exact threshold for typed report buffers (not in the live
    registry).
13. **hid-magicmouse** handling of report 0x44 (the multi-touch descriptor uses ids 2/0x3f/0x44).
14. **Tp-accel node name** (`tp_accel` vs `tp-accel`): the ADT says `tp-accel`, the Linux driver
    looks for `tp_accel`; the DT carries both.

## 10. Evidence index

Addresses are kernelcache virtual addresses of macOS 26.6.2 (25G83), prefix `0xfffffe0009` unless
shown; `member` is the derived file in `build/mtp-input/members/`.

| Function | Address | Member |
|---|---|---|
| `AppleHIDTransportProtocolSCMFIFO::handshakeGated` | `0xfffffe000917c9fc` | FIFO |
| `…::handshake` | `0x…175d1c` | FIFO |
| `…::registerSharedMemory` | `0x…1756ac` | FIFO |
| `…::drainSharedMemoryFifos` / `…FromThread` | `0x…176288` / `0x…172e8c` | FIFO |
| `…::powerHasChanged` (calls the drain) | `0x…172228` | FIFO |
| `…::parseNewBytes` / `readNext` / `addReadMessage` | `0x…175e04` / `0x…175b9c` / `0x…17c8bc` | FIFO |
| `…::handleInputReport` / `handleControlReport` | `0x…1767ec` / `0x…176bec` | FIFO |
| `…::readCompletionAction` | `0x…17114c` | FIFO |
| `…::setReportGated` / `setReportWithInterface` / `setSystemAwakeReport` | `0x…1744f0` / `0x…178cc0` / `0x…1720ec` | FIFO |
| `…::cacheProtocolConfig` / `generateFifoProperty` | `0x…17b8e4` / `0x…17b778` | FIFO |
| `…::performBootload` / `performCBORBootload` / `performFlatPackBootload` | `0x…1788e4` / `0x…178fc4` / `0x…17952c` | FIFO |
| `AppleHIDTransportDeviceFIFO::handleStart` / `read` / `write` | `0x…16f2a0` / `0x…16fe14` / `0x…16fe50` | FIFO |
| `AHTSCMMessage::init` / `parseNewBytes` / `calculateChecksum` | `0x…185f9c` / `0x…1861a8` / `0x…186abc` | SCMCommon |
| `AHTSCMMessage::createMessage` / `createControlMessage` / `getRemainingSize` | `0x…186684` / `0x…186824` / `0x…186104` | SCMCommon |
| `AIDCircularBufferShared::init` / `ReadBuffer::read` / `WriteBuffer::write` | `0x…22d6b4` / `0x…22dd58` / `0x…22e54c` | AID |
| `AIDSharedMemoryManager::createSharedMemoryFifo` / `createSharedMemory` / `readSharedMemoryFifo` | `0x…22c5d4` / `0x…22c43c` / `0x…22cb00` | AID |
| `_cbor_get_varuint_size` / `_cbor_write_varuint_unsafe` / `_cbor_insert_alignment_tags` / `_buffer_write` | `0x…22aeb4` / `0x…22aef4` / `0x…22b008` / `0x…228948` | AID |
| `AIDImageDownloader::readImageTag` / `beginFirmwareDownload` / `extractFromFtab` | `0x…236be4` / `0x…2378f8` / `0x…238040` | AID |
| `AppleHIDTransportManagement::handleReport` / `handleDescriptor` / `handleReady` / `handleWake` | `0x…1219b8` / `0x…121c1c` / `0x…121cb0` / `0x…122210` | HIDTransport |
| `…::handleConfigRequest` / `…FromThread` block / `handleConfigResponse` / `sendConfigReport` | `0x…1225c8` / `0x…12c614` / `0x…12c278` / `0x…12872c` | HIDTransport |
| `…::externalResourceAction` / `…Gated` | `0x…12b4fc` / `0x…12b6b0` | HIDTransport |
| `…::handleResetRequest` / `handleAHTFunctionRequest` | `0x…122bd8` / `0x…123ef4` | HIDTransport |
| `…::parseDescriptor` / `descriptorComplete` | `0x…1261dc` / `0x…128304` | HIDTransport |
| `AppleHIDTransportBootloaderCBOR::handleLoadImage` / `encodeObject` | `0x…118294` / `0x…1191dc` | HIDTransport |
| `AppleHIDTransportBootloader::needsFirmwareAtBoot` | `0x…107f0c` | HIDTransport |
| `AppleHIDTransportBootloaderHIDDevice::needsFirmwareAtBoot` / `loadFirmware` / `handleLoadImage` / `doFirmwareUpdate` | `0x…13d8ec` / `0x…13d8dc` / `0x…13766c` / `0x…137868` | HIDTransport |
| `AppleHIDTransportInterface::setReport` / `handleReport` / `ready` / `setPowerGated` | `0x…10b58c` / `0x…10b99c` / `0x…112a58` / `0x…10c1a4` | HIDTransport |
| `AHTFunctionInfo::init(const void*, unsigned long long*)` / `call` | `0x…142fd4` / `0x…1430a0` | HIDTransport |
| `AHTFunctionSequence::init(…, const void*, unsigned long long)` / `runSequence` | `0x…145130` / `0x…1459e0` | HIDTransport |
| `AppleT8110DART::_dartSetup` | `0xfffffe000988a744` | AppleT8110DART |
| `AppleFirmwareUpdateKext::initWithData` | `0xfffffe0008f4af7c` | (kernel collection) |

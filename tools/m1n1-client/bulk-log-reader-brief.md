# Bulk log reader for boot039: brief for the M1 agent

2026-10-16, M5 agent. **A brief, not code: nothing here has been built or run on the
M1.** The M5 side it reads from (boot039) is prepared offline and **NOT RUN natively**.
Labels: Confirmed / Likely / Hypothesis / Unknown.

boot039 replaces boot038's CDC-ACM + CDC-ECM gadget with one bulk-only function, so
that the next attempt tests attempt 18's interrupt-endpoint hypothesis with no
interrupt endpoint at all (`native/boot/boot039-bulk-log-2026-10-16.md`). No macOS
driver binds this function. The M1 reads the M5's kernel log from user space with a
small read-only tool that it builds itself from the macOS SDK. This file specifies
that tool.

## What the M5 presents (Confirmed in the VM; the native device is NOT RUN)

| Field | Value |
|---|---|
| VID:PID | `0x1d6b:0x0104` (the same as boot036/038; m1n1 is `0x1209:0x316d`) |
| `bcdDevice` | **`0x0139`**. configfs accepts only BCD, so `0x003a` was impossible. boot036 used `0x0036`, boot038 `0x0038`, and the RAM root uses `0x0039`. |
| `bcdUSB`, speed | `0x0200`, high speed (the DT caps the cores at high speed) |
| Device class | `0x00` (defined per interface), one configuration, `bConfigurationValue` 1, string "Bulk-only kernel log port" |
| Strings | manufacturer "iLinux", product "iLinux J716c control channel, port N", serial "ilinux-portN" (not a hardware serial). N = 1, 2, 3 for the M5's usb-drd0..2. |
| Interface | number 0, alternate setting 0 only, class `0xff`, subclass 0, protocol 0, string "Generic Serial" (Linux `f_serial.c`) |
| Endpoints | **one bulk IN, one bulk OUT**, `wMaxPacketSize` 512. **No interrupt endpoint.** Read the addresses from the descriptors; do not hard-code them. In the VM (`dummy_udc`) they were `0x81` and `0x02`; on the dwc3 cores expect `0x81` and `0x01` (Likely). |
| Class requests | none: the function has no setup handler |
| Data | The M5's kernel log, starting at the oldest record still in its buffer. One record per line, `[sssss.uuuuuu] text\r\n`. The port is raw, so each line ends in exactly one CR LF. The M5 never reads from the port and never echoes. |
| Flow | The M5 queues about 16 KiB, then waits until the host reads. Nothing is lost while the M5 kernel's log buffer still holds the records. |

On its own screen, the M5 prints `log <records>L <bytes>B q<queued>` per port. Bytes
rising and `q` falling mean that the reader is draining the port.

## What macOS is expected to do (Likely, not yet seen with this device)

* Configure the device itself: a class-0 device gets a composite driver, which selects
  configuration 1. In attempts 17 and 18 this was `AppleUSBCDCCompositeDevice`. The
  driver publishes one `IOUSBHostInterface` (class `0xff`).
* Bind nothing to that interface: no Apple driver matches a vendor-class interface of
  `1d6b:0104`. A user client can then open the interface without an entitlement.
  **Check this first** (read-only): `ioreg -p IOService -l -w0 -r -c IOUSBHostInterface`
  should show no driver child under the iLinux interface.
* The composite driver holds the *device* open exclusively. In attempts 17 and 18, two
  applications were refused when they tried to open it. So the reader must open
  **only the interface**, never the `IOUSBHostDevice`.
* Accessory security: in attempts 17 and 18, the "transport restrictions" block lifted
  about 4.5 s after enumeration with the M1 unlocked. A locked or asleep M1 can hold it
  longer. The interface appears only after the block lifts.

## The tool

**Build:** only the macOS SDK. Use Objective-C with `clang -fobjc-arc -framework
Foundation -framework IOKit -framework IOUSBHost` (Swift with `swiftc` is fine too).
The calls below are the SDK's IOUSBHost selectors (checked in the SDK headers,
`IOUSBHost.framework/Headers`, on this Mac; confirm them in the M1's own SDK). The
following are out of scope and each needs the user's approval: third-party packages,
libusb, a kext, a DriverKit or system extension, any entitlement, sudo, and any network
or system setting. Suggested paths: source in `tools/m1n1-client/bulk-log-reader.m`,
binary in `build/control/bulk-log-reader` (ignored).

**Usage:** `bulk-log-reader --out FILE [--port N] [--wait 120] [--seconds 600] [--dry-run]`.
There is no option for VID, PID, bcdDevice or endpoint. The identity is fixed in the
code, so the tool cannot be pointed at m1n1 or at any other device.

### Steps

1. **Refuse to start** if `--out` exists (never truncate or append to a capture), if
   another instance holds its lock file (`build/native-intake/bulk-log-reader.lock`,
   `O_EXCL`), or if `--seconds` is above 3600.
2. **Match**:
   `+[IOUSBHostInterface createMatchingDictionaryWithVendorID:@0x1d6b productID:@0x0104
   bcdDevice:@0x0139 interfaceNumber:@0 configurationValue:@1 interfaceClass:@0xff
   interfaceSubclass:@0 interfaceProtocol:@0 speed:nil productIDArray:nil]`. Poll
   `IOServiceGetMatchingServices` every 0.5 s for at most `--wait` seconds. A matching
   notification also works.
3. **Check the identity before opening anything.** Read the matched service's
   registry properties (`IORegistryEntryCreateCFProperty`, plus the parent device's
   product string) and require all of the above. The product string must be "iLinux
   J716c control channel, port N". With several matches, take the one named by
   `--port`; otherwise list them and exit. Print the registry path, `locationID` and
   speed. `--dry-run` stops here.
4. **Open the interface:** `-[IOUSBHostInterface initWithIOService:options:queue:error:interestHandler:]`
   with **`IOUSBHostObjectInitOptionsNone`**. Never use `DeviceCapture`: it needs the
   `com.apple.vm.device-access` entitlement and takes the device away from macOS.
   Never use `DeviceSeize`: it asks the current owner to close. The interest handler
   records `kIOMessageServiceIsTerminated` (`0xe0000010`) and ends the loop.
5. **Check the descriptors:** in `interfaceDescriptor`, `bInterfaceClass` must be
   `0xff` and `bNumEndpoints` 2. Walk the endpoints with `IOUSBGetNextEndpointDescriptor`.
   Exactly one must be bulk IN, the other must be bulk OUT, and nothing may be an
   interrupt endpoint. Anything else means a different device: close and exit.
6. **Copy only the bulk-IN pipe:** `-[IOUSBHostInterface copyPipeWithAddress:error:]`
   with the IN address from step 5. Do not copy the OUT pipe at all.
7. **Read loop:** take a buffer from `-[IOUSBHostObject ioDataWithCapacity:error:]`,
   16384 bytes (a multiple of 512). Call `-[IOUSBHostPipe
   sendIORequestWithData:bytesTransferred:completionTimeout:error:]` with a 5 s
   timeout, one request at a time. After every return, append the reported
   `bytesTransferred` to the capture, even when the status is a timeout, then go
   round again. Gaps between requests lose nothing: the device NAKs until the next IN
   token, and the M5 keeps the data.
8. **Sidecar log** (`FILE.txt`): UTC start time and the M1's uptime; the identity from
   step 3; the endpoint addresses; a line per second with bytes received (cumulative);
   every non-success status with its hex `IOReturn`, UTC time and seconds since start;
   and the reason the tool stopped. `fsync` both files once per second and at exit.
9. **Stop and close:** at `--seconds`, on SIGINT or SIGTERM, on termination of the
   service, or on an error from the table below. Then `-[IOUSBHostObject destroy]` on
   the pipe and the interface, so pending IO is aborted on the host side, then close the
   files. No other teardown.

### Never (the read-only contract)

The M1 must not send the M5 anything beyond the IN tokens of step 7. macOS's own
enumeration and `SET_CONFIGURATION` are macOS's, not the tool's. So the source must not
call any of the following:

* any OUT transfer, and any use of the OUT pipe;
* `sendDeviceRequest` / `enqueueDeviceRequest` / `sendControlRequest` /
  `enqueueControlRequest`, i.e. any control request, including GET_DESCRIPTOR. The
  descriptors are already cached in `configurationDescriptor` / `interfaceDescriptor`;
* `selectAlternateSetting` (it sends SET_INTERFACE) and any configuration change;
* `clearStallWithError` (it resets the data toggle and sends requests);
* `abortWithOption` / `abortWithError` (`destroy` covers teardown);
* `setIdleTimeout` (power policy), and any reset, re-enumeration or port power change;
* opening the `IOUSBHostDevice`, and the `DeviceCapture` / `DeviceSeize` options.

Add a static check next to the source (for example a `test_bulk_log_reader.py` that
greps the source for these names and for `kIOUSBEndpointDirectionOut`). It should fail
if any appear.

## How it fails safely

| Event | Tool's action | Exit |
|---|---|---|
| `--out` exists, a second instance, `--seconds` above 3600 | refuse before any IOKit call | 6 |
| No matching interface within `--wait` (default 120 s) | log what `ioreg` shows for `1d6b:0104` (read-only) and exit. **Do not set a configuration**: if macOS never published the interface, that is a result | 2 |
| Identity or descriptor mismatch, several matches without `--port` | exit before opening, or close right after step 5 | 4 |
| `kIOReturnExclusiveAccess` (`0xe00002c5`) or another open failure | something else owns the interface: report its driver from `ioreg`, do not seize | 3 |
| `kIOReturnTimeout` (`0xe00002d6`) on a read | normal while the M5 has nothing new: record it and read again. A timeout does not halt a bulk endpoint (SDK header) | continues |
| `kUSBHostReturnPipeStalled` (`0xe0005000`) | **do not clear the stall** (that is a control request): record and stop | 5 |
| `kIOReturnNotResponding` (`0xe00002ed`), `kIOReturnNoDevice` (`0xe00002c0`), `kIOReturnOffline` (`0xe00002d7`), `kIOReturnAborted` (`0xe00002eb`), service terminated | the device went away or is wedged: record the time, stop | 0 if data arrived, else 5 |
| Three other errors in a row, or a capture above 64 MiB | stop | 5 |
| Disk full or a write error on the capture | stop reading at once | 6 |

The tool never retries an open and never re-opens after a stop. A new run is the agent's
or the human's decision. It runs as the user. On a privilege error it stops and reports;
it does not escalate.

## Offline checks for the M1 agent (before the attempt)

* Build it, run the static check, and run `--dry-run` with no M5 attached: it must
  print that nothing matched and exit 2 after `--wait`, writing only the sidecar.
* With m1n1 connected (`1209:316d`), `--dry-run` must still find nothing. The matching
  dictionary never sees m1n1's device.
* Confirm the interest handler and the stop paths with a short `--seconds`.
* Without a boot039 device the M1 cannot test a read; the VM self-test covers the M5
  side (see below). The first real read is the attempt itself.

## During the attempt

* Keep everything from the attempt-18 method: a fresh M1 restart, then re-seat the
  cable and run the read-only USB gate; film the M5 screen; capture the host USB log
  read-only with the same filter as attempt 18 (it showed attempt 18's EP0 timeouts).
* Start the reader right after the launcher reports the handoff (it waits up to
  120 s): `build/control/bulk-log-reader --out build/native-intake/attemptNN-bulk-log.bin`.
* Record `ioreg` for the device and interface at about +5 s and +60 s (as in attempt 18).
* Keep the capture and the sidecar local, as for the attempt-18 media. Commit only
  excerpts, after checking them for serial numbers, MAC addresses and other identifiers
  (`AGENTS.md`). This is a full native kernel log, and it has not been reviewed for them.

## What the VM self-test shows about the M5 side (job 041, `selftest/run-vz.sh`)

In the test kernel, Linux's generic usb-serial driver plays the M1's part. It is
given `1d6b:0104` through `new_id`, opens the bulk-IN endpoint and reads the log. The
test checks that:

* the descriptors are as in the table above;
* the log is complete from before the host opened the port;
* lines end in one CR LF;
* bytes a host writes are not echoed and do not stop the stream.

It cannot show what macOS binds, or how the M5's real dwc3 cores and the M1's host
controller behave; those are the attempt's questions.

## Attempt 22: the RAM root's two-interface device (added 2026-10-16)

The RAM root (`omarchy-arm64/ram-root`, `usb-gadget.sh` with `FUNCTION=gser`) presents the
same `1d6b:0104` device with **`bcdDevice 0x0039`** and **two** `gser` interfaces in
configuration 1 ("Bulk-only kernel log port + SSH byte pipe"): interface 0 is the journal,
written only by the M5, exactly as boot039's interface 0; interface 1 is a raw byte pipe with
`sshd` on it, which the M1's `usb-pipe` opens (`usb-ssh-link.md`). For the reader this means:

* **Accept `bcdDevice 0x0039` as well as `0x0139`**, from a fixed two-entry table in the code
  (still no option), and keep matching `interfaceNumber:@0`. Print which stage answered.
* **`bNumInterfaces`** in the configuration descriptor is 1 for boot039 and 2 for the RAM root;
  both are fine. The per-interface checks of step 5 are unchanged: interface 0, class `0xff`,
  exactly one bulk IN and one bulk OUT, no interrupt endpoint.
* **Never open interface 1.** Two user clients on two interfaces of one device are expected
  to coexist (Likely); the device nub stays with macOS's composite driver as before. Add
  `bInterfaceNumber` other than 0 and `interfaceNumber:@1` to the static check's forbidden
  list.
* The data is the systemd journal (`journalctl -b -f -o short-monotonic --no-hostname`),
  one record per line ending in CR LF, from the boot's start; the stream restarts from the
  boot's start after a hang-up. On the M5's status screen there is no `log … B q…` field for
  the RAM root; `systemctl status ilinux-usb-gadget@<udc>` over SSH shows the streamer.
* Everything else in this brief (read-only contract, fail-safe table, offline checks) applies
  unchanged.

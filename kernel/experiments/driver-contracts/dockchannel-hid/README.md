# DockChannel HID parser regression experiment

2026-10-13. Original local patch and synthetic regression harness; neither
native t6050 input support nor a performance claim.

The pinned Asahi implementation provides the existing Linux transport for
MTP keyboard/trackpad HID. Review found malformed-input paths that either
read outside a declared object, misinterpret an adjacent block, leak packet
work, or leave reception disarmed after allocation failure. These are concrete
Linux fixes that can be tested before native boot is available.

## Provenance

* Public base: `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` in
  `third_party/asahi-linux`.
* File: `drivers/hid/dockchannel-hid/dockchannel-hid.c`.
* Git blob: `9cab638b30c328da05b52158e11bf9e00bc61660`.
* Source SHA-256:
  `15c1186c3bbb87dddb75c1f1053ab3a2c3a2a1128bba6718bd88977f4b7beb2f`.
* Source license: `GPL-2.0 OR MIT`; original harness/preparation code: MIT.
* No proprietary implementation or decompiled pseudocode is in this patch.
  The source defects and the packet layouts are independently visible in
  the public Linux code. m1n1's `proxyclient/m1n1/fw/mtp.py` corroborates
  the eight-byte envelope, four-byte padding and additive checksum.
  In the pinned Linux source, `dchid_send` pads `hdr.length` with
  `round_up(size, 4)` and `dchid_checksum` consumes 32-bit words, warning
  on leftover bytes. The receive word-alignment check enforces that existing
  contract; it is not inferred from rejected proprietary pseudocode.

`0001-dockchannel-hid-validate-input-bounds.patch` adds:

1. A full firmware-header size check before any header field is accessed.
2. A terminator check for the fixed-width interface name before C-string use.
3. GPIO init-block validation against that block's own declared size.
4. A nonzero-length check before indexing the last product-name byte.
5. An empty-event check before reading its type byte.
6. Rejection of transport bodies shorter than the subheader or not word padded.
   The body is drained first, preserving the next packet boundary.
7. A return to the receive-rearm path before an invalid interface array index.
8. Release of queued work when its declared subheader length is invalid.
9. Receive callback rearming when allocation of packet work fails.

The last change is also consistent with the bounded REA investigation of
`AppleDockChannel::_readBytesAsyncGated`: a pending-read lifecycle matters to
continued reception. It is justified directly by the Linux callback control
flow; it does not require importing Apple's implementation. The parent
research record owns the binary evidence and its limitations.

## Reproduce

From the project root, this preparation step only reads source as data and
writes generated source in an unused workspace output directory:

```sh
python3 -I kernel/experiments/driver-contracts/dockchannel-hid/prepare.py \
  --repo third_party/asahi-linux \
  --output build/rea-lab/dockchannel-tests
```

The preparation script verifies both source digests, applies the patch with
the system `patch` utility, and extracts seven actual driver functions plus
their original protocol types. It does not execute third-party code. If the
output directory exists, choose a fresh directory or inspect it before removal.

Run **only inside the isolated Linux analysis VM**, with the normal project
`quiet` lock held:

```sh
apk --cache-dir /mnt/lab/apk-cache update
apk --cache-dir /mnt/lab/apk-cache add clang compiler-rt
CC=clang sh /mnt/lab/dockchannel-tests/run-linux.sh
```

Pass `--benchmark` for six bounded runs (three per variant, alternating
order) of 10,000,000 identical synthetic valid packets. These use `-O2` without
sanitizers and time the extracted receive/checksum/dispatch path, including
its allocation/free and synthetic callback hooks. The output records the
compiler, iterations, elapsed time, per-packet time, OS and build flags.
This measures VM parser overhead only; it excludes physical I/O, firmware,
interrupt scheduling, real HID consumers and latency/power at the keyboard.

The harness compiles the exact baseline and patched functions with ASan and
UBSan. Hardware, allocation and HID hooks are synthetic. Ten independent
baseline cases must fail; the patched cases and three valid-input cases must
pass. The results directory records compiler version/flags and individual
baseline diagnostics. There is no hardware access or captured keyboard data.
The Alpine ARM64 GCC package does not supply the sanitizer runtimes used by
this test. The validated sanitizer build uses guest-only Clang 21.1.2 and
compiler-rt 21.1.2; the ordinary portable ring tests also compile with GCC.

Tests execute the original parser bodies, not a separate reimplementation.
The transport builder independently encodes synthetic packet bytes, and the
hooks expose dispatch, allocation/release and receive-rearm side effects.

To apply in a disposable native-kernel checkout based on that commit:

```sh
git apply --check /path/to/0001-dockchannel-hid-validate-input-bounds.patch
git apply /path/to/0001-dockchannel-hid-validate-input-bounds.patch
```

No full kernel object is built by this experiment. When the native-kernel
build job is available, build the actual object there using its existing
configuration with `CONFIG_APPLE_DOCKCHANNEL` and `CONFIG_HID_DOCKCHANNEL`:

```sh
make ARCH=arm64 O=/path/to/output drivers/hid/dockchannel-hid/dockchannel-hid.o
```

The userspace harness does not establish a complete kernel build, interrupt
concurrency correctness, firmware compatibility, or functional native input.
Do not install this experimental patch in the live Omarchy VM: its virtio
input path does not exercise Apple DockChannel.

## Remaining t6050 work

The draft native DT only contains a disabled MTP DART node. MTP/ASC firmware
startup, DockChannel DT resources, interrupt routing, firmware packaging,
reset GPIO/SMC mapping, and native event delivery remain unvalidated. Test
those after an authorized RAM-only boot, with a second-machine console.
First validate keyboard events, then multitouch and haptics; preserve working
USB/serial access while input initialization is experimental.

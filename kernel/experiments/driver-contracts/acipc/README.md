# N1 ACIPC operational contract experiment

This is original, portable offline code for a future N1 transport driver.
It does not register a Linux device, perform MMIO, map DMA, transmit packets,
or claim working Wi-Fi/Bluetooth. It was added on 2026-10-13 in agent B's
cross-subsystem REA investigation.

## What the artifacts establish

**Observed static configuration:** the shipped `AirshipDK.framework`
`t2026-CentauriAlpha.plist` and `t2026-CentauriBeta.plist` both name `acipc`
and operational protocol version 768 (`0x300`). These are software
configuration values; the running device's negotiated ABI is not observed.
`observed-operational-facts.json` records only selected operational scalar
facts, their source paths and complete-file SHA-256 digests. No proprietary
executable, decompiled implementation, boot-stage data, device identifier,
network traffic or log content is included.

The paired DriverKit `Info.plist` files identify Alpha as the WLAN provider
(PCI match `106b:1902`, 10 MSI) and Beta as the Bluetooth-side provider
(`106b:1903` / `106b:1181`, 2 MSI). Those match values are bundle metadata,
not an independent observation of enumeration on this particular unit.

| Selected operational configuration | Alpha | Beta |
|---|---|---|
| Declared transfer/completion index counts | 192 / 234 | 16 / 1 |
| Completion topology | Separate completion rings; RX marked out of order | HCI/ACL/SCO rings marked in-place |
| Doorbell mode | Shared constant | Index |
| Examples of declared ring sizes | Events 96; commands 64/192; data 2048 | HCI TX 5 / RX 17; ACL and SCO 9 |
| Examples of footer-size values | Data 16 | HCI 260; ACL 2592; SCO 724 |

**Engineering decision:** do not bake a power-of-two assumption into a
prospective transport's software bookkeeping. The values 5, 9, 17, 96 and
192 are observable counterexamples to that assumption at the configuration
layer. They do **not** establish that a hardware producer register wraps at
those values: the relationship between configured size, allocated slots,
usable slots, reserved slots and encoded phase bits remains unknown.

`ring_math.c` therefore takes explicit software geometry. It advances an
ordinary index with overflow-safe modulo and rejects invalid buffer spans,
truncated slot arrays, out-of-range indices and multiplication overflow.
Its buffer-span structure is not an ACIPC wire descriptor. Stride is always
caller supplied; it is never inferred from `footer_size` or
`transfer_footer_size`, which are not established descriptor strides.

The added `acipc_software_queue` API explicitly adopts the ordinary circular
buffer policy of reserving one empty slot. `push(count)` and `pop(count)`
check available/occupied space before changing an index; rejection leaves
the state unchanged. The implementation is original general software queue
code, not a translation of the target routine or a hardware structure. It
has no concurrency, DMA ownership, fences or device accesses. A one-slot
allocation has zero usable capacity by this explicit model policy.

The parent REA investigation corroborated the selected class's normal-path
modulo arithmetic, three 16-bit fields, one-empty-slot head check, and
bounded tail advancement. All 131 selected instruction words matched LLVM
and the original cache; no out-of-body pcode was reported. This supports
testing this software policy. External failure handlers, the class's actual
use by each configured ring, firmware index representation and capacity
interpretation remain unresolved. These findings do not turn plist footer
sizes into strides or the software queue into an ACIPC wire implementation.

`extract_config.py` accepts only Alpha/Beta `t2026` ACIPC configurations. It
field-allowlists operational stage/ring/register/doorbell facts; retains
source hashes; validates scalar types, explicit index bounds and doorbell
references; and excludes Control, boot stages, unlisted fields and diagnostic
rings. It does not infer whether vectors in a `multi` group are contiguous.

## Reproduce

From the repository root, using the existing compiler and Python:

```sh
cc -std=c11 -Wall -Wextra -Werror -O2 \
  kernel/experiments/driver-contracts/acipc/ring_math.c \
  kernel/experiments/driver-contracts/acipc/test_ring_math.c \
  -o build/rea-lab/test_acipc_ring_math
build/rea-lab/test_acipc_ring_math
python3 -I kernel/experiments/driver-contracts/acipc/test_extract_config.py
python3 -I kernel/experiments/driver-contracts/acipc/test_ring_analysis.py
python3 -I kernel/experiments/driver-contracts/acipc/extract_config.py \
  --output build/rea-lab/acipc-facts-new.json
```

The extractor exclusively creates its output; it refuses to overwrite prior
evidence. The last command needs the readable macOS Alpha/Beta static plist
files. The C and Python tests themselves run on ordinary Linux without those
files. Use only this workspace or an isolated Linux lab; do not start a
driver, configure hardware, or inject these observations into a native DT.

**Host validation:** macOS 26.6.2 / 25G83, Apple M5 Max, Apple clang 21.0.0
(`clang-2100.3.34.2`), `-std=c11 -Wall -Wextra -Werror -O1 -g
-fsanitize=address,undefined`: 8,525,654 wrap cases plus boundary/overflow
tests pass. Python 3.9.6: ten configuration tests and eight analysis-carrier
tests pass, including field omission and malformed input rejection. This
measures test coverage, not transport performance.
The queue extension adds 49,840 exhaustive state/count combinations for
slot counts 1–20 (including 5, 9 and 17), with independent small-state walks,
plus `UINT64_MAX`, invalid-state and unchanged-on-rejection cases; these
also pass the host sanitizer build.
The parent analysis task records isolated ARM64 Linux validation separately.

## Next REA questions and Linux mapping

The visible `AppleCentauriAlpha`, `AppleCentauriBeta` and
`AppleCentauriControl` dext executables are only four-byte `_DummySymbol`
text stubs, confirmed with Apple LLVM headers/symbols. Importing them into
REA cannot reveal the driver. Their load commands name the real DriverKit
private frameworks. Those frameworks' code is in the separate, roughly
24 MB DriverKit dyld cache:

`/System/Volumes/Preboot/Cryptexes/OS/System/DriverKit/System/Library/dyld/dyld_shared_cache_arm64e`

The matching `.symbols` file is about 3.6 MB. Scope the next REA import to
`AirshipDK`, `CentauriAlpha`, `CentauriBeta`, and their non-boot transport
helpers. Seek ring construction, submit, completion, index encoding, buffer
ownership and doorbell ordering functions. Validate every inferred layout
against independently decoded instructions and this static configuration;
do not treat generated pseudocode as source. Only the selected ring-index
class's normal paths have since received the narrow corroboration above;
descriptor submission, DMA ownership and doorbell semantics remain open.

**Observed cached code:** an original bounded reader of Apple's published
[dyld format](https://raw.githubusercontent.com/apple-oss-distributions/dyld/main/include/mach-o/dyld_cache_format.h)
confirms intact text in the three selected images. `AirshipDK` has 586,216
text bytes at `0x18022a000`; `CentauriAlpha` has 165,872 at `0x1803d6000`;
`CentauriBeta` has 159,900 at `0x180412000`. The cache SHA-256 is
`c0cb9e3f489efe860ec67122bd51b93c816eac5ff4f48884375f0c908fea536d`.
The matching local-symbol companion was checked in memory; no cache identity
fields were recorded. Selected AirshipDK targets below are named by local
symbols and bounded by its `LC_FUNCTION_STARTS` table, not by a guessed next
symbol.

| REA target (demangled description) | Static address | Function-start interval bytes |
|---|---|---:|
| `ring_index_pair<uint16_t>` constructor | `0x18023000c` | 136 |
| `ring_index_pair<uint16_t>::advance_head_index` | `0x180237ef8` | 196 |
| `ring_index_pair<uint16_t>::advance_tail_index` | `0x180237fbc` | 192 |
| `acipc::cr_ring::copy_descriptor` | `0x180230094` | 312 |
| `acipc::direct_doorbell::get_offset` | `0x1802395d8` | 64 |

These addresses and labels select analysis work; they do not establish
semantics. The cached images share `__LINKEDIT`, and data rebases/authenticated
fixups remain an extraction concern. Do not create an apparently standalone
driver by copying arbitrary contiguous cache ranges.

`extract_ring_analysis.py` solves only the narrower analysis problem: after
verifying the pinned cache hash, image identity, section mapping and exact
function-start intervals, it copies the constructor/head/tail instruction
bytes into a synthetic ELF64/AArch64 carrier with three function symbols.
The output is 1,344 bytes, of which 524 are original instructions. It retains
the static virtual addresses, but has no program headers or entry point and
is not loadable code or a recovered library. No strings, data pages, Control
functions or other images are copied. Original target functions are never
executed. External branches and data references remain unresolved and may
prevent a useful decompilation; the evidence gate still applies.

```sh
python3 -I kernel/experiments/driver-contracts/acipc/extract_ring_analysis.py \
  --output build/rea-lab/artifacts/Airship-ring-analysis.elf
```

The generated ELF and its `.elf.json` provenance manifest stay under ignored
`build/`; outputs are created exclusively. The manifest provides original to
derived byte mappings compatible with `reverse-engineering/rea-lab/check_evidence.py`.
Apple LLVM independently recognizes its three section addresses/sizes and
symbols. The eight tests construct original synthetic cache/ELF data and
exercise hash mismatches, ambiguous mappings, invalid architecture,
truncated function starts, changed intervals and exact section/symbol layout.

The common Linux prerequisite is a working t6050 PCIe host and DART stream
configuration. The sanitized driver map associates `apcie0` with
`AppleT6050PCIe` / `AppleCentauriManager` and its DART with `AppleT8110DART`.
The existing Asahi `apple-dart.c` supplies T8110 foundations; matching class
names alone do not prove t6050 stream mappings or DMA correctness. N1's
ACIPC transport must not be equated with Linux `apple-rtkit`'s distinct
management protocol, whose checked source supports versions 11–12.

For Wi-Fi, a future driver needs cfg80211 capability/configuration support,
packet transport and orderly netdev queue completion. Linux documents
[cfg80211's interface](https://docs.kernel.org/driver-api/80211/cfg80211.html)
and [netdev queue lifetime rules](https://docs.kernel.org/networking/driver.html).
Whether firmware provides full-MAC behavior still requires command evidence.
For Bluetooth, HCI-labelled rings make a Linux HCI transport a plausible
design; [Linux HCI device registration](https://linux.googlesource.com/linux/kernel/git/torvalds/linux/+/335c9017e333894c39853f6fc27db9f0ce44f48b/net/bluetooth/hci_core.c)
is the public implementation reference. The labels alone do not establish
H4 framing, event ordering, credits, SCO/ISO framing or reset sequencing.

Remaining blockers are PCIe/DART enablement, descriptor ABI and ordering,
normal firmware availability and lifecycle, command/event formats,
completion/cancellation behavior, and physical measurements. A VM cannot
validate any of these native N1 interfaces. Asahi's [current M5 support
table](https://asahilinux.org/docs/platform/feature-support/m5/) still marks
PCIe, DART, Wi-Fi and Bluetooth TBA (checked 2026-10-13).

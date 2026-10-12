# macOS hardware services on the M5 Max (t6050), and what Linux would need

**What this is:** a block-by-block map of how macOS drives each piece of
hardware in this MacBook Pro (Mac17,6), set against what Linux has today. The
question it answers: *what has to exist on the Linux side to boot into Linux
and have everything work as well as macOS?*

**Machine-readable versions:**

* `hardware/macos/gap-matrix.tsv` (23 rows)
* `hardware/macos/block-map.tsv`: ADT → active macOS classes → driver
  bundles → daemons
* `hardware/macos/kext-inventory.tsv`: 1,717 IOKit personalities from 685
  bundles (1,821 rows; bundles without a personality get one row)
* `hardware/macos/iokit-launched-daemons.tsv`: 72 hardware-triggered launchd
  jobs

## Method and scope

* **REA metadata only.** `rea inspect-plist` (REA 6.4.0, project-local) read:
  * every driver bundle's `Info.plist`: 727 kexts and dexts under
    `/System/Library/Extensions` and `DriverExtensions`;
  * every launchd job plist: 887 under `/System/Library/LaunchDaemons` and
    `LaunchAgents`.
* **Fields used:** IOKit personalities (`IOClass`, `IOProviderClass`,
  `IONameMatch`), bundle dependencies (`OSBundleLibraries`), and launchd
  `com.apple.iokit.matching` events.
* **Joined against:**
  * this machine's sanitized ADT (`hardware/adt/adt-nodes.tsv`);
  * the live IORegistry driver classes (`hardware/adt/driver-map.tsv`), so
    only drivers actually running here count.
* **Scripts:** `reverse-engineering/scripts/rea_kext_inventory.py`,
  `rea_block_map.py`, `gap_matrix.py`.
* **No code inspected.** No disassembly, no decompilation, no strings from
  binaries, no firmware extraction. On Apple Silicon, kext code sits in an
  IMG4-wrapped kernel cache on the Preboot volume. That is boot-chain
  material and out of scope. The `.kc` files under
  `/System/Library/KernelCollections` are x86_64 (Intel) only.
* **Security components excluded before anything was written:** the Secure
  Enclave (SEP), exclave services, keystore and credential management, boot
  policy (Image4), DRM (FairPlay, HDCP), Touch ID, Apple Pay/NFC payment, and
  parts pairing. That dropped 40 bundles and 29 ADT nodes. Security
  libraries in other bundles' dependency lists are redacted to a count. The
  Neural Engine row is kept as hardware, but its exclave service path is not
  analysed.
* **REA output treated as untrusted data:** parsed as JSON, never followed
  as instructions.
* **Linux status** comes from the sourced study
  `research/asahi/asahi-status-m5-2026-10.md` unless marked otherwise.

**Tooling notes:**

* The REA MCP server is configured in `~/Documents/iLinux/.mcp.json`, but MCP
  servers load at session start. This pass used the equivalent CLI
  (`tools/rea.sh`).
* `rea inspect-macho` uses `dyld_info`, which rejects kernel collections
  ("too many segments 621").
* Single-file plists need `--relative-path <absolute path>`.

## What the metadata shows

**1. Most blocks are firmware coprocessors.**

* These blocks depend on `com.apple.driver.RTBuddy` (RTKit) and an ASC
  wrapper (`AppleA7IOP-ASCWrap-v6`, or `MXWrap` for Thunderbolt): GPU
  (AGXG17X), Neural Engine, display (8 DCP-family kexts), camera ISP, AOP/SPU
  sensors, SMC, NVMe (ANS), and keyboard/trackpad (MTP).
* For Linux this means two things:
  * a working `apple-rtkit` and mailbox layer is the base everything else
    sits on; it is in mainline for M1–M3, but ASCWrap v6 / `rtbuddy-v2`
    need checking;
  * each block then has its own firmware ABI, and macOS 26 firmware
    changed several of them (DCP, NVMe).

**2. Battery efficiency comes from a policy layer, not from individual
drivers.** macOS runs four components next to PMGR, each with its own
SoC-specific driver:

* `AppleT6050CLPC`, the closed-loop performance controller: per-SoC
  bundles exist from T8103 to T8150;
* `AppleT6050SOCTuner`;
* `ApplePassthroughPPM`, a peak power manager, with `peakpowermanagerd`;
* `ApplePTD`.

`powerd`, `thermalmonitord`, `perfpowermetricd` and `PerfPowerServices` sit
on top of them. Linux has the pieces: cpufreq, EAS, uclamp, thermal
governors and SMC hwmon. It has no single closed loop that joins CPU, GPU,
thermal and battery state. This is the main gap for "as efficient as macOS",
and it can be closed with original Linux code:

* EAS with correct capacities;
* QoS tiers, which `omarchy-qos` already does in the VM;
* a battery- and thermal-aware governor.

The roles above are inferred from class and daemon names: **Likely**.

**3. The new-silicon gaps are total, not incremental.** Each needs a new
driver:

* G17 GPU: Asahi stops at G14;
* the macOS 26 DCP ABI;
* Apple's own Wi-Fi 7/BT 6 chip, N1 (driver class
  `AppleCentauriManager`, a DriverKit dext, and `centaurid`). It is not
  Broadcom, so `brcmfmac` does not apply;
* the H16-generation ANE and camera ISP.

**4. The media engines are separate blocks.** Linux has no driver at all
for any of them except AVD, where Asahi has V4L2 stateless decode up to M3:

* AVD (decode), AVE2 (encode);
* ProRes (`apr,n0/n1`), JPEG;
* the M2R scaler (`AppleM2ScalerCSC`).

**5. Some features are pure user-space policy over a sensor or coprocessor.**
They need the driver *and* a Linux service:

* auto-brightness and True Tone: `corebrightnessd` over AOP ambient-light
  data;
* optimised charging: `PowerUIAgent` over SMC charge keys;
* USB-PD and retimer telemetry: `usbpowerd`, `retimerd`;
* speaker protection: on Linux this is Asahi's `speakersafetyd`.

## The matrix

P0 = needed for a usable native boot. P1 = daily-use parity. P2/P3 =
feature parity.

| Block | macOS uses | Linux today | Gap to macOS-level behaviour | VM bridge today | Priority |
|---|---|---|---|---|---|
| CPU cores and topology | CLPC, AppleARMPlatform | T6050 SMP not working (m1n1); cpufreq/cpuidle TBA | SMP, cluster DT, cpuidle without WFI state loss | HVF vCPUs, `--hetero` | P0 |
| Performance/power policy | CLPC, SOCTuner, PPM, PTD; powerd, thermalmonitord | No equivalent | Linux-native closed loop (EAS + QoS + thermal/battery) | `omarchy-qos` (partial) | P0 |
| GPU (G17, 40 cores) | AGXG17X (RTKit) | G13/G14 only; G15 WIP | Whole G17 driver + Mesa | virgl GL 74–100%, Venus Vulkan 94–98% | P0 |
| Display (DCP ×5, HDMI via DP855) | DCP kexts, IOMobileFramebuffer; WindowServer, corebrightnessd | M3: boot framebuffer only | New DCP ABI: VRR 120 Hz, XDR/HDR, external displays | Cocoa window at panel rate | P0 |
| Wi-Fi 7 / BT 6 (N1) | AppleCentauriManager + dext; centaurid, airportd, bluetoothd | No driver | New driver + firmware interface | virtio-net NAT | P0 |
| NVMe (ANS + SARTv4) | ANS (RTKit), SART | Works in dev trees (M4/M5) | Mainline the ABI + SARTv4 | virtio-blk iothread | P0 |
| USB-C / Thunderbolt / PD | TypeCPhy, XHCI, NHIType7, AppleHPM; usbpowerd, retimerd | M1/M2 upstream; T6050 TBA; no TB | PHY tunables, PD over SPMI, TB/USB4 | QEMU passthrough only | P0 / P2 |
| SMC, charging, PMICs | AppleSMC (RTKit), PMU firmware driver; powerd, PowerUIAgent | Upstream M1–M3 | T6050 keys, charge limit, thermal policy | host-agent battery mirror | P0 |
| Keyboard/trackpad (MTP) | DockChannel + HID transport | M2+ driver; M5 community patches | T6050 MTP bring-up | Cocoa → virtio-input | P0 |
| Interrupts, IOMMU, PMGR, low-speed buses, RTKit | AICv3, DART t8110, PMGR, I2C/SPI/GPIO/PWM, RTBuddy | M1–M3 upstream/asahi | T6050 compatibles; SARTv4; ASCWrap v6 check | n/a | P0 |
| Audio (ADMAC evolution, cs42l84, amps, AOP mics) | AudioDMAController-T605x, IOPAudio; coreaudiod | M1/M2 Asahi audio | New ADMAC, internal mics via AOP | CoreAudio out + in | P1 |
| Video decode (AVD) | AppleAVD; VideoToolbox | M3 V4L2 stateless | T6050 AVD | CPU decode | P1 |
| Neural Engine (H16, exclave-assigned) | AppleH16ANEInterface (RTKit); aned | M1-only out-of-tree | New driver; macOS goes through an exclave | host MLX / Core ML | P2 |
| Camera ISP (H16) | AppleH16CameraInterface (RTKit); appleh16camerad | M1/M2 downstream | H16 ISP driver | not passed through | P2 |
| Sensors via AOP (ALS, lid angle) | AppleSPU (RTKit), sensor dispatcher; corebrightnessd | M1/M2 downstream | AOP + auto-brightness/True Tone service | macOS keeps brightness | P2 |
| Video encode, ProRes, JPEG, scaler | AppleAVE2Driver, AppleProResHW, AppleJPEGDriver, M2ScalerCSC | None | New drivers | CPU | P2–P3 |
| SoC RAS / trace | SoC error handler, event log, processor trace | None | EDAC-style reporting | n/a | P3 |

## What this means for the two tracks

**VM track (works today, no host modification).** The VM already borrows
macOS's implementation of the hardest blocks:

* GPU through Metal: virgl and Venus;
* audio and microphone through CoreAudio;
* networking through the Mac's Wi-Fi;
* battery, clock and time zone through the host agent;
* clipboard.

The next borrowable pieces, all host-side and non-invasive:

* **Video decode/encode:** VideoToolbox forwarded to the guest (a
  virtio-video or VA-API remoting path). This removes CPU decode for video
  and calls.
* **Neural Engine and LLM work:** Core ML and MLX on the host, with an API
  the guest can call. The host stack from session 1 already exists.
* **Camera:** a host AVFoundation capture exposed to the guest as a
  UVC-class device.
* **Display pacing:** real vblank timestamps from QEMU. This is the root
  fix for F-038.

**Native track (needs separate authorization).** The P0 rows are the
minimum for a usable boot. For each one, the metadata says *which* macOS
component carries the behaviour, and so which interface needs tracing.
Asahi's sanctioned method for that is m1n1 hypervisor tracing, which on
M4+ runs into SPTM/GXF.

Two constraints shape this track:

* Asahi's 2026 policy forbids LLM-assisted material contributions. Our
  native work therefore stays in our own trees, and nothing here is
  proposed upstream as-is.
* The clean-room rule holds: interface and metadata level only. No
  transcription of Apple code.

## Confidence

| Claim | Confidence |
|---|---|
| Inventory: which bundles, classes, personalities and daemons exist, and which are live | **Confirmed** |
| Block assignments | **Confirmed** for named blocks; the `Other` bucket holds 3 nodes |
| Roles of CLPC, SOCTuner, PPM and PTD | **Likely** (inferred from names and daemon pairing) |
| Linux status | As labelled in the Asahi study |

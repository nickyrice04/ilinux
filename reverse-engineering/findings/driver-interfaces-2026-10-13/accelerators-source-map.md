# Accelerator source and target map

2026-10-13. Agent B source scout. Read-only source, bundle metadata and symbol
inspection; no decompilation, VM operation, sensor activation or host changes
performed for this map. No protected exclave/SEP implementation was inspected.

## Evidence and pins

* **Observed:** sanitized `hardware/adt/adt-nodes.tsv` and
  `hardware/macos/block-map.tsv`; installed bundle `Contents/Info.plist` metadata.
* **Observed:** selected member symbols in ignored
  `build/rea-lab/artifacts/{AGXG17X,AppleH16ANEInterface,AppleH16CameraInterface,AppleDCP}.symbols.json`.
  The `.macho.json` sidecars identify carrier SHA256
  `26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`.
  These are ARM64e fileset members; the corresponding bundle executables are
  absent from `/System/Library/Extensions/*/Contents/MacOS/`. Running boot
  identity remains unverified. Collection fixups remain unapplied.
* **Pinned local Linux:** `third_party/asahi-linux` at
  `d55aa8982990ecbc6cfccfe047458944e76fde7e`. The GPU, DCP and ISP paths below
  have no changes against public base
  `77cb8f24c2381a8abb7272d7bbdec548d6426a8a`.
* **Pinned m1n1:** `third_party/m1n1` at
  `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* **Pinned external ANE source:** `eiln/ane` main resolved through GitHub on
  this date to `0dcea9976fae0b500a236a62fca69cd4d39f0809`; source read directly,
  not executed or installed.

The selector lists below describe those exact sources, not every development
branch or a general prediction of hardware feasibility. The current
[M5 feature table](https://asahilinux.org/docs/platform/feature-support/m5/)
lists GPU, ANE and webcam as TBA. Its generic status does not override concrete
source changes. In particular, the
[August progress report](https://asahilinux.org/2026/08/progress-report-7-2/)
reports full M3 webcam support and M3 DCP firmware 14.8.3 nearing parity; the
local DCP snapshot is narrower than that report.

## Confirmed bindings and precise Linux gaps

| Area | Sanitized macOS evidence | Pinned open-source support and remaining gap |
|---|---|---|
| GPU | ADT line 541: `/arm-io/sgx`, `gpu,t6050`; class `AGXAcceleratorG17X`, bundle `com.apple.AGXG17X` version 353.14. Its plist explicitly matches `gpu,t6050`. Transport inventory includes ASCWrap v6/RTBuddy. | [Linux driver.rs](https://github.com/AsahiLinux/linux/blob/77cb8f24c2381a8abb7272d7bbdec548d6426a8a/drivers/gpu/drm/asahi/driver.rs): IDs t8103, t8112, t6000/1/2, t6020/1/2; firmware cases G13/12.3, G14G/12.4, G13/13.5, G14G/13.5, other G14/13.5. No t6050 selector or G17 firmware specialization here. Boot/init data, queues, address translation and shader/command generation all need evidence; adding one compatible string cannot supply them. |
| ANE | ADT line 525: `/arm-io/ane0`, `ane,t8132exclave`; ordinary host class `H11ANEIn`. `com.apple.driver.AppleH16ANEInterface` version 9.512.0 explicitly matches this name. AppleH11ANEInterface shares older host-class names but its plist does not match this variant. | [ane_drv.c](https://github.com/eiln/ane/blob/0dcea9976fae0b500a236a62fca69cd4d39f0809/ane/src/ane_drv.c#L649): only `apple,t8103-ane` and `apple,t6000-ane`, both selecting `ane_hw_t8020`. No ANE driver source was found under local Linux `drivers/`. Old request/DMA machinery is research input, not evidence of t8132 host ownership, firmware compatibility or a usable Linux model compiler. The ADT suffix alone proves none of those. |
| Camera | ADT line 108: `/arm-io/isp0`, `isp,isp-generic-ex;isp,s5l8960x`; class `AppleH16CamIn`, user client `AppleH16CamInUserClient`; `com.apple.driver.AppleH16CameraInterface` version 5.605 matches `isp,isp-generic-ex`. A separate exclave-proxy personality exists but is outside this research. | [isp-drv.c](https://github.com/AsahiLinux/linux/blob/77cb8f24c2381a8abb7272d7bbdec548d6426a8a/drivers/media/platform/apple/isp/isp-drv.c): t8103, t8112, t8122, t6000, t6020, t6030, t6031. Thus M3 support already exists. No t6050 entry here. Reuse V4L2/vb2, ISP IPC, firmware-surface and format handling; verify the new firmware command ABI, platform register/IRQ data, metadata sizes and sensor setup before creating a hardware config. |
| Display/DCP | ADT lines 420, 426–428: `disp0,t605x`, `dcp-expert-v1`, DCP `iop,ascwrap-v6` with `iop-nub,rtbuddy-v2`. Inventory associates AppleDCP and AppleMobileDispT605X-DCP; broad display inventory includes other families and is not proof each one drives this panel. | [dcp.c](https://github.com/AsahiLinux/linux/blob/77cb8f24c2381a8abb7272d7bbdec548d6426a8a/drivers/gpu/drm/apple/dcp.c): selectors `apple,t6020-dcp`, `apple,t8112-dcp`, `apple,dcp`, `apple,dcpext`; firmware gate 12.3.0 or 13.5.0, plus compat13.3.0 only when actual FW13.5.0. No 26.x ABI is selected. Reuse DRM/KMS, AFK/EPIC, buffer/fence and panel code; a generic DCP selector does not establish compatibility with this carrier's firmware. |

## Finite REA questions and bounded targets

All addresses are static unslid VAs. Byte counts are the gap to the next
distinct symbol, **not verified function sizes**. GPU, ANE and camera
follow-ups below were checked against the derivative's `__text` section.
Names identify candidate functions; they do not establish runtime dispatch.

| Area | Current target and proposed follow-up | Finite question and useful outcome |
|---|---|---|
| GPU | Parent target `AGX·PI_300·X·A0·KSMKickQueue::addKicks(unsigned, unsigned long long)`, `0xfffffe0008986470`, 340 B symbol gap. Follow-up `AGXArmFirmware::kickFirmware(unsigned,bool,bool)`, `0xfffffe000896bff0`, 300 B; optionally `prepareFirmwareForBoot()`, `0xfffffe000896d13c`, 164 B. | Does an ordinary queue kick retain the old channel/doorbell framing, or introduce a new queue token/role? Compare with pinned [m1n1 fw/agx](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/proxyclient/m1n1/fw/agx/__init__.py): endpoint 0x21, type 0x83, channel bits 15:0; firmware endpoint 0x20. A validated difference can inform a small original packet validator. It cannot validate G17 rendering or shader ISA. |
| ANE host boundary | Parent target `ANEHWDevice::aneCmdSend(ANEFirmwareCommand const&)`, `0xfffffe0008fb6fb4`, 324 B. Follow-ups `ANEClientDevice::getVersion(ANEVersion*)`, `0xfffffe000903259c`, 256 B, or `H11ANEInUserClient::externalMethod(unsigned, IOExternalMethodArgumentsOpaque*)`, `0xfffffe00090353a0`, 256 B. | What version/length/selector contract is checked at the ordinary host API, and what transport boundary does `aneCmdSend` reach? Stop at any protected-service dispatch. Version/selector observations support an original host ABI validator and clarify which facts remain inaccessible; they do not authorize protected-code analysis or demonstrate native ANE availability. |
| Camera | Parent target `AppleH16CamIn::doorBellRing0(void*)`, `0xfffffe00090c581c`, 68 B. Better protocol follow-ups: `AppleH16CamInFrameReceiver::SetBufferPoolConfiguration(unsigned,unsigned short,unsigned short,unsigned,unsigned)`, `0xfffffe00090e2174`, 132 B; `SetPrimaryScalerOutput(unsigned,unsigned,unsigned,unsigned,eCIspOutputFormats,eCIspVOutputColorRangeModes)`, `0xfffffe00090e2668`, 148 B. | Do buffer-pool and scaler commands retain the existing opcodes, wire lengths and field widths? Pinned [isp-cmd.h](https://github.com/AsahiLinux/linux/blob/77cb8f24c2381a8abb7272d7bbdec548d6426a8a/drivers/media/platform/apple/isp/isp-cmd.h) defines pool0x0117/0x9c bytes with u16 type/count, output0x0b01 or0x0b09/0x38 bytes. Validate differences against [isp-cmd.c](https://github.com/AsahiLinux/linux/blob/77cb8f24c2381a8abb7272d7bbdec548d6426a8a/drivers/media/platform/apple/isp/isp-cmd.c), not assumptions from names. This is the closest of these targets to a finite, testable protocol-layout change. |
| DCP | Parent target `AFKEPKextBaseV2::handleSendMessage(MessageInfo const*,span<AFKEPMessage>,AFKEPSendOptions const*)`, `0xfffffe0008da2a34`, 32 B. | Is this only a forwarding adapter? If so, identify the next ordinary-host callee and its symbol/body before expanding analysis. Compare transport length, alignment, ring wrap and acknowledgement rules with pinned [afk.c](https://github.com/AsahiLinux/linux/blob/77cb8f24c2381a8abb7272d7bbdec548d6426a8a/drivers/gpu/drm/apple/afk.c). A transport match says nothing yet about IOMFB RPC IDs or panel modes. |

The camera follow-ups are preferable if the selected doorbell is merely a
wrapper: they have direct public Linux command counterparts. GPU doorbell
work also has a precise comparison. ANE should first establish the permitted
host boundary and report unknown ownership explicitly.

## Implementation and validation gates

**Possible now:** original portable serializers/parsers and rejection tests
for public-source GPU doorbells, ISP command layouts or AFK ring bounds.
Keep versions explicit; reject unknown lengths/opcodes and overflow. Tests can
exercise boundary values and malformed packets in ordinary ARM64 Linux. A
resulting helper becomes useful native code only after the t6050 contract is
independently established. ANE can support a host capability/selector schema;
do not manufacture a hardware backend from an older command format.

**Before using REA findings:** pass the existing original-byte/LLVM check and
numeric function-body gate; do not trust REA's `member` label. Recover direct
callees independently. Unapplied fixups, pointer authentication, unresolved
virtual calls and cold/no-return boundaries can invalidate reconstructed
behavior. Keep private pseudocode/raw binary output in ignored lab files;
record only the observed contract and its evidence in project documents.

**Still requires native validation:** firmware startup, IRQ delivery, IOMMU
ownership/mapping, queue completion and reset; then one bounded GPU submit,
ISP format/stream initialization or display commit on the authorized firmware.
Camera validation should begin with metadata and a synthetic/test pattern
where available, not personal recordings. Protected service access is not a
fallback. Existing native boot gates and machine readiness remain prerequisites.
VM compilation or [Mesa drm-shim](https://docs.mesa3d.org/drivers/asahi.html#drm-shim-linux-only)
can validate software/compiler behavior but cannot prove G17/ANE/ISP/DCP
hardware functionality or performance.

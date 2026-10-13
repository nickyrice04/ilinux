# Input, audio and USB source map

2026-10-13. Local static evidence, no native boot or device capture.

The public Linux base is `77cb8f24c2381a8abb7272d7bbdec548d6426a8a`.
The inspected checkout's later draft-DT commits do not change the
DockChannel HID source blob. m1n1 is pinned at
`57a9339ffd1876e78297b17d34dece8cff8fa1ba`.

| Area | Existing Linux/public implementation | Local observed target and useful REA question | Remaining native blocker |
|---|---|---|---|
| Keyboard/trackpad | `drivers/hid/dockchannel-hid/dockchannel-hid.c`, `drivers/soc/apple/dockchannel.c`, `include/linux/soc/apple/dockchannel.h`; m1n1 `proxyclient/m1n1/fw/mtp.py` | ADT `dockchannel-mtp`, `mtp`/ASC v6, `dart-mtp`; AppleHIDTransportFIFO and AppleDockChannel. Does receive framing remain an 8-byte header plus padded body/checksum? | DT/firmware startup, DART mapping, reset controls and actual packet delivery. Parser robustness can be improved now. |
| Internal microphones | `drivers/soc/apple/aop.rs`, `rust/kernel/soc/apple/aop.rs`, `sound/soc/apple/aop_audio.rs`; m1n1 `proxyclient/m1n1/fw/aop/ipc.py` | `IOPAudioLPMicDevice`, `IOPAudioDriverFamily`; determine public IOP command envelope and separate normal low-power mic paths from the isolated high-performance path. | ADMAC evolution, AOP service negotiation, hardware routing and isolated/exclave boundary. Existing t6030 support is not evidence of t6050 compatibility. |
| Speaker/headphone audio | `sound/soc/apple/macaudio.c`, `sound/soc/apple/mca.c`, `drivers/dma/apple-admac.c`, `sound/soc/codecs/cs42l84.c`, TAS-family codecs | `AudioDMAController-T605x`, `AppleCS42L84Audio`. Recover descriptor object sizes, channel constraints, register-aperture selection; independently validate before any MMIO patch. | New ADMAC generation, AOP-managed routing, amplifier identity and speaker protection/calibration. Codec availability alone does not establish a complete route. |
| External keyboard/mouse/webcam/mic | Ordinary `usbhid`, `uvcvideo`, `snd-usb-audio` once USB host works | `AppleT6050TypeCPhy`, AppleT8142 USB controller classes, AppleHPM. Start with USB2 PHY/tunable entry points. | ATC PHY compatibility, SPMI generation 4 IRQ/flush semantics and USB-PD transport, DART, host controller DT. A guest USB model does not test these. |
| Shared coprocessor transport | `drivers/soc/apple/mailbox.c`, `rtkit.c`, `rtkit-helper.c`, `drivers/iommu/apple-dart.c`; m1n1 RTKit/ASC code | AppleASCWrapV6, RTBuddy, AOP AFK/EPIC framing. Check negotiated version, endpoints and buffer descriptors. | Per-device firmware/boot contract, new mailbox/ASC variants, coherent DMA and DART setup; not all devices share one interchangeable protocol. |

The existing AOP audio driver defines attach-device `0xc3000002`,
set-property `0xc3000005`, device identifiers `pdm0`, `lpai`, `hpai`,
and idle/power settings. It supports the generic `apple,aop-audio` path and
`apple,t6030-aop-audio`; the latter uses three bytes per sample and a high
frequency decimator. AOP AFK endpoints start at `0x20`, count `0xf`, with
ring alignment `0x40`. These are documented *existing Linux* contracts,
not newly validated t6050 contracts.

The current Linux ADMAC match table includes `apple,t8122-admac`,
`apple,t8103-admac`, and the generic fallback. The local hardware mapping
instead observes `admac-evolution,t6050`, with non-secure base/leap nodes
and separate isolated audio proxies. Do not select a generic fallback just
because the older driver compiles.

Selected static function identities from the copied arm64e carrier:

| Bundle / symbol | Address | Useful bounded question |
|---|---|---|
| AppleDockChannel `_readBytesAsyncGated` | `0xfffffe0008e484b4` | How is one pending read registered and armed? |
| AppleHIDTransportFIFO `parseNewBytes` | `0xfffffe0009175e04` | Envelope/checksum boundaries; whole-function decompilation is rejected by the parent evidence gate. |
| AudioDMAController-T605x `AudioDMAChannel::readInterruptStatusAndEnables` | `0xfffffe0009b5a6e4` | What status/enable objects are read before interrupt dispatch? |
| AudioDMAController-T605x `AudioDMAChannel::_buildTransferDescriptors` | `0xfffffe0009b5b3d0` | Descriptor object construction; not yet a verified hardware descriptor format. |
| IOPAudioLPMicDevice `startIO` | `0xfffffe000a721c28` | Which normal IOP command starts low-power capture? |
| IOPAudioLPMicDevice `handleIOPMessage` | `0xfffffe000a72189c` | Message type/length checks on the normal proxy boundary. |
| AppleT6050TypeCPhy `applyTunables` | `0xfffffe0009a746c4` | Tunable record layout and aperture bounds. |
| AppleT6050TypeCPhy `initUSB2` | `0xfffffe0009a76e98` | Wrapper parameters and dispatch into USB2 initialization. |

Symbol addresses alone establish function identity, not behavior. Do not
translate a decompiler's output into a driver without original-byte checks,
control-flow boundaries and independent source or runtime corroboration.

The most useful next peripheral milestone is functional input on a RAM-only
native boot. A microphone or webcam command cannot compensate for an absent
DMA/IOMMU/firmware path. External class-compliant USB devices remain a useful
fallback after native USB bring-up, while internal audio needs its own tests.

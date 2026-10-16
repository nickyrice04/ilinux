# Audio on t6050: IOP (AOP) + exclaves, not an AP-driven MCA (first pass)

2026-10-16, M5 REA session. Offline; nothing ran on the M5; macOS read-only. Inputs: `build/macos-drivers/members/
{AudioDMAController-T605x,IOPAudioDriverFamily,AppleEmbeddedAudio,AppleSN012776Amp,AppleCS42L84Audio,ExclavesAudioKext}.macho`
(symbols and strings), kext personalities from the carrier, the sanitized ADT. Labels: Confirmed / Likely / Hypothesis /
Unknown. The Linux audio stack (`apple-admac`, `mca`, `macaudio`, `tas2764`, `cs42l84`) is not in the pinned clone; comparisons
are from memory and labelled.

## 1. The answer to "IOP or exclave?"

* **There is no AP-visible MCA/I2S block in this ADT** (Confirmed: none of the 254 `/arm-io` children is an `mca*`/`i2s*`
  node; `AppleMCKAudio` matches the `audio-data,*` stream nubs published by IOPAudio, not a register block). The I2S/
  serial-audio engine ("LEAP") lives behind the AOP: the audio **control plane and the I2S are an IOP service**
  (`/arm-io/aop/iop-aop-nub/aop-audio`, `iop-audio,aop-service`; AP side `IOPAudioDriverFamily`: `IOPAudioController`
  matches `iop-audio,controller`, `RTKitAudioFramework`, `IOPAudioMessageDispatcher`, `iop-domain-id`,
  `iop-audio-service-name`).
* **The DMA engines are AP-driven but sit in the AOP's bus domain** (Confirmed): `admac-base-ns` and `admac-leap-ns`
  (`admac-evolution,t6050`, CPU `0x293800000`/`0x293300000`, 0x34000 each, channels `audio-dma-channel,v4p0`) have
  `iommu-parent` = `dart-aop` mappers; the AP kext `AudioDMAController-T605x` matches them (also `admac,t6050/t605x` for the
  display-audio ADMACs `admac-disp0`, `admac-dispext0..3` behind the `*-isoc` DARTs).
* **Microphone input is exclave-isolated** (Confirmed): `admac-leap-s` (secure, no AP IOMMU parent), `admac-hp-mic-ec-proxy`
  and `admac-sllb-ec-proxy` (`admac-ec-proxy`, `exclave-assigned`, `0x2d3200000`), `audio-hp-mic-proxy`/`audio-sllb-proxy`
  (`iisaudio,isolated-stream-proxy`), `audio-shared-dart-proxy` (`usecase-dart-map`), `iop-voicetrigger-controller/
  audio-vt-device` (`exclave-assigned`), `lp-mic-*` devices with `isolated-audio-service-input`; `ExclavesAudioKext` is a
  Tightbeam proxy (`ExclavesAudioProxyInputStreamDriverTightbeam`: `readInput`, `setupClientIO`, `mapDMABuffer`,
  `selectPhysicalStreamDescription`; output: `writeMixOutput`).
* **Codecs/amps are plain I2C devices configured by the AP** (Confirmed): six `audio-control,sn012776` amps
  (`i2c1` `0x38` with `interrupts [0x6a]`, `function-reset`, speaker-id functions, `iboot-audio-volume`; `0x39`, `0x3a`;
  `i2c3` `0x3b`, `0x3c`, `0x3d` = left woofer 1/2 + tweeter, right woofer 1/2 + tweeter) and one `audio-control,cs42l84`
  headphone codec (`i2c2` `0x4b`, `interrupts [0x86]`, `enable-ringsense`, `mic-config`; `AppleCS42L84Mikey` = headset
  buttons). DisplayPort audio goes through the DCP (`dp-audio0..4`).

So: speakers = AP ADMAC transfer + AOP-owned I2S + AP-configured amps, orchestrated by the IOP audio service; headphone
jack = same with the CS42L84; internal/headset microphones = exclave streams the AP never touches directly.

## 2. ADT topology (Confirmed)

| Node | compatible | Facts |
|---|---|---|
| `/arm-io/aop` | `iop,ascwrap-v6` | `reg` `0x290600000+0x88000` (ASC), `0x290650000+0x4000`, `0x290c00000+0x2f0000` (AOP peripheral window), `0x288328000+0x24`, `0x29062c000+0x3c008`; interrupts `0x243 0x242 0x245 0x244`; `iommu-parent` `dart-aop/mapper-aop`; nub `iop-nub,rtbuddy-v2` with services `aop-audio`, `aop-voicetrigger`, `accel`, `gyro`, `als`, `aop-gpio0`, `aop-spmi0` |
| `/arm-io/iop-audio-controller` | `iop-audio,controller` | streams: `audio-speaker` (`iop-adma-stream,mca` → `audio-data,sn012776`), `audio-codec-output/-input` (`audio-data,cs42l84[-input]`), `audio-hp-mic` (`iop-adma-stream,leap` → `audio-data,external`), `audio-speaker-tap`, `audio-mca-loopback`, `audio-leap-internal-loopback`, `audio-secure-leap-loopback`, `lp-mic-device`, `lp-mic-io-buffer-device` (`isolated-io-buffer-device`), `lp-mic-injection-device`, `siri-listening-device` (`client-manager-device`) |
| `/arm-io/iop-voicetrigger-controller` | `iop-audio,controller` | `audio-vt-device` `iop-audio,isolated-vt-device`, `exclave-assigned` |
| `/arm-io/admac-base-ns`, `admac-leap-ns`, `admac-leap-s` | `admac-evolution,t6050` | `0x293800000`, `0x293300000`, `0x293200000` (+0x34000), each with a second `0x288328000+0x8` window; interrupts 637/639/638; `ced-ssw-service` → `admac-aop-ced-ssw` (`admacled,t6050`, `0x293c80000`/`0x293c84000`, irq 652); `channel-buffer-alloc-base-*`, `channels-offset`, `function-vote_crit_llt_mode` |
| `/arm-io/admac-disp0`, `admac-dispextN` | `admac,t6050`, `admac,t605x` | `0x28a140000+0x24000` etc., DP audio DMA behind the display isoc DARTs |
| `/arm-io/i2c1/audio-speaker*`, `/arm-io/i2c3/audio-speaker*` | `audio-control,sn012776` | six amps, addresses above |
| `/arm-io/i2c2/audio-codec-output` | `audio-control,cs42l84` | `0x4b`, `PowerOffAtSleep`, `internal-mclk-src`, `function-codecinput_master` |
| `/product/audio` | — | `speaker-thiele-small`, `supports-always-listening`, `supports-barge-in`, `acoustic-id` (speaker protection parameters consumed by the IOP/AP) |

## 3. Kernel driver facts (Confirmed, symbols/strings)

* `AudioDMAController-T605x`: `AudioDMAController` (102 fn), `AudioDMAChannel` (147), `ADMATransfer`, `AudioDMAChannelStateMachine`,
  `AudioDMAChannelSharedResourceManager`; logs "ADMAC revision being driven: 0x%08x. Assigned DART SID", three FIFO
  apertures ("TD FIFO", "CS FIFO", "PCT FIFO"), "SRAM carveout overrun", "evolved DMA command pool", clock-scaler/timebase
  alignment (LTB/GTB/MCT), and "EC proxy has already been registered" (exclave proxy channels). Register offsets were not
  extracted in this pass (next step: decompile `AudioDMAChannel` register accessors and compare with Linux `apple-admac`'s
  `REG_*` map from memory: TX/RX start/stop, per-channel control at `0x8000 + ch·0x200`, descriptor/report FIFOs).
* `IOPAudioDriverFamily`: `IOPAudio`, `IOPAudioController`, `IOPAudioDevice`, `IOPAudioNode(Manager)`, `IOPAudioService`,
  `IOPAudioMessageDispatcher`, `RTKitAudioFramework` — an RTKit message protocol to the IOP audio service (format not
  extracted).
* `AppleEmbeddedAudio`: `AppleI2CAudio`, `AppleTII2CAudio`, `AppleI2C{Paged,Ranged,Multiple}Audio`, `AppleMCKAudio`
  (`audio-data,audio-loopback`, `maggie-debug`, `mck-only`), `iBootAudioVolumeManager`, runtime register patches.
* `ExclavesAudioKext`: 179 functions, all Tightbeam proxy plumbing (`ExclavesAudioProxyEndpoint`, input/output stream
  driver interfaces, debug injection).

## 4. Linux delta

| # | Item | Label |
|---|---|---|
| 1 | The M1/M2 path (`mca` + `apple-admac` + `macaudio` programming the I2S directly) does not apply: no MCA block is exposed to the AP. Speaker output on Linux needs (a) an RTKit client for the AOP audio service (`aop-audio`), (b) `apple-admac` support for the `admac-evolution` revision behind `dart-aop`, (c) the existing `tas2764`-class amp driver for `sn012776` (six instances) and `cs42l84` | Likely (a, b) / Confirmed (c exists for the parts, from memory) |
| 2 | Internal microphones: exclave-owned ADMAC/DART/stream proxies; without exclaves the AP has no documented path. Expect no internal-mic support on Linux unless the AOP service can be driven without the exclave proxies | Hypothesis |
| 3 | Headphone-jack mic (`audio-hp-mic`, `leap` stream with an exclave ADMAC proxy) shares the same limitation | Hypothesis |
| 4 | DisplayPort audio: `admac-disp0`/`dispextN` + `dp-audio0..4` via the DCP; depends on the DCP work | Likely |
| 5 | DT: `aop` node (`apple,t6050-aop`? — the Linux AOP driver status is Unknown here), `dart-aop`, the three `admac-evolution` nodes with `iommus = dart_aop`, six amp nodes under `i2c1`/`i2c3`, the codec under `i2c2`; no `mca` node | Likely |

## 5. Open questions

1. `admac-evolution` register map vs Linux `apple-admac` (next step: `AudioDMAChannel` accessors).
2. The IOP audio message format (`IOPAudioMessageDispatcher`) and the AOP endpoint number for `aop-audio`.
3. Whether the AOP firmware (pre-loaded by iBoot, `segment-names __SHARED;__OS_LOG`) accepts an AP client without the
   exclave-side services present.
4. Speaker-protection ("safety-offset", Thiele-Small) requirements before driving the amps on Linux.

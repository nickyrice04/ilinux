# SMC on t6050 from this Mac's macOS 26.6.2 drivers: transport, keys, events and the Linux delta

2026-10-16, M5 REA session. **Offline analysis; nothing ran on the M5; macOS read-only** (one read-only `ioreg` query for
a live ADT property). Proprietary inputs stay in the ignored `build/macos-drivers/` (`members/AppleSMC.macho` …,
`evidence/AppleSMC-*.txt`, `evidence/smc-keys-*.txt`, `scripts/smc_keys.py`). Labels: Confirmed / Likely / Hypothesis /
Unknown. The Linux side is compared **from memory** (the pinned asahi-linux clone is a `blob:none` partial clone without
`drivers/platform/apple`, `drivers/power/supply/macsmc_power.c`, `drivers/hwmon/macsmc-hwmon.c`, `drivers/gpio/gpio-macsmc.c`
or `drivers/input/misc/macsmc-hid.c`; nothing was fetched); every such comparison is labelled "(Linux, from memory)".

| Binary (kernel-collection member) | sha256 | Role |
|---|---|---|
| `com.apple.driver.AppleSMC` | `a3904e16…837d` | RTKit key endpoint, notifications, PMU buttons/GPIO/lid, charger port logic, sensor dispatcher |
| `com.apple.driver.AppleSmartBatteryManager` | `b78dc555…a306` | battery/gas-gauge keys |
| `com.apple.driver.AppleHighVoltageCharger` | `07c080e4…30ce` | adapter firmware/PD VDM helper; **uses no SMC keys itself** |

## 1. Summary

1. **The message ABI is the one Linux `macsmc` already speaks** (Confirmed, §3): 64-bit RTKit messages on the first user
   endpoint (`SMCEndpoint1` = 0x20), command byte 0 (`0x10` read, `0x11` write, `0x12` key-by-index, `0x13` key-info,
   `0x17` get shared SRAM address, `0x18` notification, `0x20` read-with-payload), 4-bit tag in bits 15:12, size byte 2,
   payload size byte 3, key in bits 63:32; data ≤ 4 bytes inline, otherwise through the shared SRAM; result codes
   `0x84` key not found, `0x87` size mismatch, `0x89` bad argument.
2. **Notifications are `type<<24 | subtype<<16 | arg1<<8 | arg0` in the upper 32 bits** (Confirmed): families `0x70`
   system state, `0x71` power/charger, `0x72` HID (subtype 1 button, 2 GPIO, 3 lid), `0x73` battery auth, `0x75` system
   control (thermal emergency). This is the event layout Linux's `macsmc-hid`/`gpio-macsmc` match (from memory).
3. **The thermal path on this Mac is one key**: the AP's sensor dispatcher reads `mTPL` (live ADT `smctempsensor0/sensor`)
   every 1000 ms; all fan/thermal control lives in the SMC firmware. GPU die temperatures are *written* to the SMC
   (`tGA0`–`tGA2`, `tGAM`) only when the ADT asks for it (not here) (Confirmed).
4. **Battery and charger keys are the M1-era names** (`B0AV`, `B0AC`, `B0RM`, `B0FC`, `B0DC`, `B0CT`, `B0TE`, `B0TF`, `B0AT`,
   `BRSC`, `CHCE`, `CHCC`, `CHLS`, `CH0C`, `CH0I`, `AC-W`, …) plus a 33-entry SBS-command→key table (§5). Nothing in the
   kexts suggests a renamed or re-typed key on M5; types/sizes are queried at runtime with key-info, as Linux does.
5. **Power-state protocol** (Confirmed): sleep writes `MBSE` = `slpa` (or `hiba` for hibernation) and `WKTP` = 2; wake
   reads `MBSE` and the wake-reason bitmap `MBSW` (8 bytes), writes `MBSE` = `waka`; shutdown/restart write
   `MBSE` = `offw` / `rest`; notifications are enabled with `NTAP` = 1. Linux's reboot driver uses `offw`/`rest`
   (from memory); `slpa`/`waka`/`WKTP`/`NTAP` are the parts to check in `smc_core` (§7).
6. **DT**: the node is the standard `apple,smc` shape with t6050 addresses (§6); nothing M5-specific is required beyond
   compatibles, addresses and the four mailbox interrupts (Likely).

## 2. ADT and registry facts (Confirmed; sanitized ADT, one read-only `ioreg` query)

`/arm-io/smc`: `compatible iop,ascwrap-v6`, `role SMC`, `iop-version 1`, `reg[0] 0x8c600000+0x88000` (ASC), `reg[1]
0x8c050000+0x4000` (shared SRAM), `reg[2] 0x8c810000+0x100` (purpose Unknown; no macOS driver maps it by index in the
analysed kexts), `interrupts 0x384 0x383 0x386 0x385`, `power-gates` empty (always-on). The `/arm-io` `ranges` map child
`0x0…0x3c0000000` to `+0x200000000`, so the CPU addresses are **`0x28c600000`, `0x28c050000`, `0x28c810000`**
(the same translation the ANS node uses: ADT `0x219600000` → draft-DT `0x419600000`).

Children of `/arm-io/smc/iop-smc-nub` (`iop-nub,rtbuddy-v2`): `smc-pmu` (`AppleSMCInterface`, `device_type
interrupt-controller`, `function-pmu_button`, `has_lid_open_sensor`, `event_name-bit{0,8,9,11,13,35,40..45,48}`),
`smc-charger-util-0/1/2` (`port-number 1/2/3`, `port-type 2`), `smc-charger-util` (`port-number 1`, `port-type 17`,
`magsafe-auth`). `/arm-io/smctempsensor0`: `compatible smc-tempsensor`, live properties `sensor = "mTPL"`,
`timerInterval = 1000` (ms); `readGPUDieTemp`, `gpu-temperature-offset-value`, `gpu-maxTemperature-offset-value` absent.
Kext personality: `AppleSMCKeysEndpoint` matches `IONameMatch = SMCEndpoint1`; RTBuddy names user endpoints
`<role>Endpoint<n>` with n = 1 for 0x20 (the carrier shows `AOPEndpoint1…32`, `DCP0Endpoint1…`), so the key endpoint is
**0x20** (Likely: naming convention; Confirmed that it is the first user endpoint).

## 3. Transport (`AppleSMCKeysEndpoint`, Confirmed; pseudocode in `evidence/AppleSMC-KeysEndpoint-batch1.txt`)

Message (`ApcKeyMsg`, 8 bytes, built as a u64; `_sendKeyMsgAndWaitForResponse` `0xfffffe0009690148`):

| Bits | Field | Notes |
|---|---|---|
| 7:0 | command | `0x10` read, `0x11` write, `0x12` key by index, `0x13` key info, `0x17` get SRAM address, `0x18` notification (SMC→AP only), `0x20` read with payload (`_readPKeyGated` `0xfffffe0009690da0`) |
| 11:8 | 0 | must be < 0xf before the tag is or-ed in |
| 15:12 | tag | `this+0x61a`, incremented mod 16 per message; the reply's byte 1 must match the request's byte 1 ("Tag/ID of response doesn't match") |
| 23:16 | size | bytes to read/write (`_readKeyGated` `0xfffffe0009690478`: `0x10 | size<<16`) |
| 31:24 | payload size | only for `0x20`: payload copied to SRAM first |
| 63:32 | key / index | the 4CC as a u32 (`'M'<<24|'B'<<16|'S'<<8|'E'`); for `0x12` the index |

Reply (`_pollForKeyFinished` `0xfffffe0009692164`, `_keyEndpointHandler` `0xfffffe000968f664`): byte 0 = result,
byte 1 = tag, byte 2 = actual size, bytes 4..7 = inline data when the size is < 5, otherwise the data is in the shared
SRAM (`this+0x600`, obtained once with command `0x17`: "Unable to obtain shared SRAM Addr"); cache maintenance around
SRAM accesses (`vtable+0x148(1|2, 0, len)`). Key info (`_getKeyInfoGated` `0xfffffe0009691c38`): 6 bytes from SRAM —
`size` (u8), `type` (u32, **byte-swapped**), `flags` (u8). Key-by-index (`0xfffffe0009691968`): the key comes back
byte-swapped in the inline data. Result codes seen: `0` ok, `0x84` key not found (`_sendNotify` maps it to
`kIOReturnNotFound`), `0x87` reply larger than the buffer, `0x89` bad argument (size > 0x78 or NULL buffer), `0x10`/`0x11`
local busy/send failure, `0xb7` poll timeout (3 s, `_pollForKeyFinished`). The endpoint allows one outstanding command
(`_activeKeyCommand` `this+0x608`, `_waitForIdle`).

Notification (`0x18`): `AppleSMC::_processUpstreamNotification` `0xfffffe0009696f8c` decodes `byte7 = type`, `byte6 =
subtype`, `byte5 = arg1`, `byte4 = arg0` and dispatches by type: `0x70` `system-state-notify`, `0x71`
`power-state-notify`, `0x72` `hid-event-notify`, `0x73` `battauth-event-notify`, `0x75` system control (subtype 3 =
thermal: reason 1 → `kIOPMOverTemp`, 2 → `kIOPMDWOverTemp`, else sleep now; subtypes 1/2 "not implemented"); during
panic polling `0x70` with subtype `0x22` = "SMC panic progress", `0x0a` = "panic done"; a `0x70`/subtype 7 message is the
wake-event claim. HID (`AppleSMCPMU::_smcNotifyCallout` `0xfffffe000968cf54`): subtype 1 button (`arg1` = button index:
1 power, 2 vol+, 3 vol−, 4/13 play-pause, 5 …, 7/11 wake-SEP, 8/9/10/12/14/0xfe vendor usages; `arg0` = state),
subtype 2 GPIO (`arg1` = PMU GPIO number → vector 7+n, or 8+n when `+0xd4` is set; acknowledged by writing the vector's
key with `0x05000000 | state`), subtype 3 lid (`arg1` = state → root domain). Charger (`AppleSMCChargerUtil::handleSMCEvent`
`0xfffffe0009683c7c`, family `0x71`): subtype `0x13` port status change (`arg1` = port, `arg0` = 2 detach / 3 attach /
4 winner update), `0x0f` over-current (`arg1` = port).

## 4. Power-state protocol (Confirmed)

| When | Key | Value / size | Function |
|---|---|---|---|
| start | `NTAP` | u8 = 1 (enable notifications) | `AppleSMC::_smcInitNotifications` `0xfffffe0009695d8c` |
| start | `LGPE` | key-info probe (SOC debug/log capability) | `AppleSMC::start` `0xfffffe0009694bb0` |
| start | `aDC#`, `aDC?`… | u32 count, per-channel ADC sensor keys | `start`, `_createSensor` `0xfffffe0009695e48` |
| start | `MBSW` | 8-byte wake-reason bitmap, then `MESS` (u8 shutdown cause: 1 thermal critical, 2 dark-wake thermal, 3 remote mgmt, 0x28 ap_shutdown, 0x29 ap_panic, 0x2a ap_restart, 0x2b wdt, 0x2c sys_reset, 0x2d hibernate, 0x2e virtual slp) and `MEST` (8-byte shutdown time) | `AppleSMCPMU::_claimSystemBootEvents` `0xfffffe000968ad90`, `_claimSystemShutdownEvents` `0xfffffe000968afa4` |
| sleep | `WKTP` | u8 = 2 | `AppleSMC::setPowerState` `0xfffffe0009698084` |
| sleep | `MBSE` | u32 `slpa` (`0x736c7061`) or `hiba` (hibernating) | `AppleSMCKeysEndpoint::_powerStateActionGated` `0xfffffe0009692410` |
| sleep (capability change) | `MBSE` | `slpw` | `AppleSMCPMU::handleSystemPowerStateChange` `0xfffffe000968a960` |
| wake | `MBSE` read (4), `MBSW` read (8), then `MBSE` = `waka`; `NTAP` = 1 again after un-hibernating | `_powerStateActionGated`, `AppleSMCPMU::callPlatformFunction` `0xfffffe000968bf00` |
| shutdown / restart | `MBSE` = `offw` / `rest` | `handleSystemPowerStateChange` |
| time set | `CLKH` (8 bytes, after key-info) | `AppleSMC::smcSetTimeCallback` `0xfffffe0009698dc0` |
| AP→SMC notify | `NESN` (4 bytes) | `AppleSMCKeysEndpoint::_sendNotify` `0xfffffe0009692b64` |

## 5. Key table (keys are `mov/movk` immediates; `scripts/smc_keys.py` + Ghidra; sizes = the byte count the caller passes)

Core, PMU and sensors (AppleSMC):

| Key | Size | Direction | Used by | Label |
|---|---|---|---|---|
| `#KEY`, `$Num`, `REV `, `RGEN` | 4 / 1 / 6 / 1 | read | key count, version, generation (`AppleSMCFamily`) | Confirmed |
| `MBSE`, `MBSW`, `MESS`, `MEST`, `WKTP`, `NTAP`, `NESN`, `CLKH`, `LGPE`, `LGDD`, `LGDE`, `TINI`, `SCRD`, `UFLG`, `sEEC`, `panb` | see §4; SOCD/log keys | — | §4, `_executeSOCDCommand`, `callPlatformFunction` | Confirmed |
| `btn0`–`btn7` | 4 | write `0x04000001`/`0x04000000` (IENA) and `0x05000000\|state` (ICLR) | `AppleSMCPMU::enableVector`/`disableVectorHard` `0xfffffe000968ca8c`/`…c94c`, `mapVectorToKey` `0xfffffe000968c764` | Confirmed |
| `gPxx` (two hex digits) | 4 | same encoding for PMU GPIO vectors ≥ 8 | same | Confirmed |
| `MSLD` | 1 | read lid state | `_sendCurrentLidStateToRootDomainGated` | Confirmed |
| `mTPL` | 8-byte read | temperature published by the AP | `AppleSMCSensorDispatcher::readTemperatureKeysFromSMC` `0xfffffe0009688d8c`, key from ADT `sensor` | Confirmed (live ADT) |
| `TG0B` | 8-byte read | battery temperature special case (`battery-state` boot-arg) | same | Confirmed |
| `tGA0`–`tGA2`, `tGAM` | 4 (float) | **write** GPU die temperatures | `readGPUAverageDieTemp` `0xfffffe0009688f94` (only with `readGPUDieTemp`) | Confirmed, inactive here |
| `tGMD` | — | sensor dispatcher timer | `_timeoutOccurredGated` | Confirmed |
| `MGNT`, `NFCP`, `NFCS` | 4 | magnet / NFC power-pause / NFC state | `getMagnetKey`… | Confirmed |
| `PwrB`, `DPBW` | 4 | power budget to/from SMC | `AppleSMCPowerOut` | Confirmed |
| `AOPc` (64), `AOPe` (1) | — | AOP↔SMC link config | `AppleAOPSMCLink` | Confirmed |
| `keyR/keyW/keyV/mkyR/pKR3..8/pKW3..8/btnR/ramU` | — | not SMC keys: `AppleSMCEmbeddedFunction` platform-function selectors | — | Confirmed |

Charger port logic (AppleSMC `AppleSMCCharger*`, `AppleSMCChargerUtil`, `AppleSMCAdapterSrcOption*`; `D%d` = port digit):

| Key | Size | Meaning (from the code/logs) | Function |
|---|---|---|---|
| `CHSC` | 1 | charger state (bool) | `AppleSMCChargerFunction::getChargerState` `0xfffffe00096a039c` |
| `CHBI`, `CHBV` | 4 | charge current / voltage configuration | `getChargeCurrentConfiguration`/`getChargeVoltageConfiguration` |
| `CHHV` (8), `CHI1` (4) | — | USB input high-voltage enable, input current limit (write) | `setUSBInputHighVoltage`, `setUSBInputCurrentLimit` |
| `B0AT` | 4 | battery temperature | `measureBatteryTemperature` `0xfffffe00096a0834` |
| `VQ0B` (4/8), `VQ0u` (8), `VBUS` (4) | — | system/battery voltage, VBUS voltage, detect status | `measure*`, `copyDetectStatus` |
| `D%dAP` | 4 | port attached (bit 0) | `AppleSMCCharger::_checkConnection` `0xfffffe000969e424` |
| `D%dST` (1), `AC-W` (1), `ANWP` (1), `D%dPt` (1), `D%dPI` (1) | — | port status bits, winner port, number of… , winner type/index | `handleSMCPortStatusChangeEventPwrInUpdate` `0xfffffe00096833c4`, `…WinUpdate` `0xfffffe0009683040` |
| `D%dID`(1) `D%dIG`(1) `D%dSM`(4) `D%dAR`(4) `D%dAI`(1) `D%dSC`(0x1c) `D%dIR`(4) `D%dVR`(4) `D%dFC`(4) `D%dDE`(0x20) `D%dBD`(4) `D%dos`(0xc) `D%dDB`(1) `D%dNO`(1) | — | **AP → SMC** accessory/PD contract description (writes gated by key-info attributes) | `AppleSMCChargerPS::handlePowerSourceDetect` `0xfffffe000969f6b0` |
| `D0NF`, `D1L1`, `D0Au`, `D0BI`, `D0Rp`, `ATP0`, `BNOC`, `MSSC`, `D1St`, `adcV`, `chrg` | — | charger start/notify/adapter-source helpers | `AppleSMCCharger::start`, `AppleSMCDockUSB_UFP`, … |

Battery (AppleSmartBatteryManager; `getSmcKeyForCommand::keyTable` at `0xfffffe00075f80b8` = `{SBS command, key}` pairs,
Confirmed):

| SBS cmd | Key | SBS cmd | Key | SBS cmd | Key |
|---|---|---|---|---|---|
| 0x01 | `CHSC` | 0x08 Temperature | `B0AT` | 0x09 Voltage | `B0AV` |
| 0x0a Current | `B0AC` | 0x0b AverageCurrent | `B0IV` | 0x0f RemainingCapacity | `B0UC` |
| 0x10 FullChargeCapacity | `B0CM` | 0x12 AvgTimeToEmpty | `B0TE` | 0x13 AvgTimeToFull | `B0TF` |
| 0x17 CycleCount | `B0CT` | 0x18 DesignCapacity | `B0DC` | 0x21 ManufacturerName | `BMDN` |
| 0x23 ManufacturerData | `BMDA` | 0x53 | `B0PS` | 0x76 | `BMSN` |
| 0x8b | `B0RC` | 0x9c | `B0CU` | 0x100 | `CHCE` |
| 0x200 | `CHCC` | 0x300 | `BSFC` | 0x400 | `BCF0` |
| 0x500 | `B0RM` | 0x600 | `B0FC` | 0x700 | `B0NC` |
| 0x900 | `B0CA` | 0xe00 | `CH0V` | 0x1000 | `CHAS` |
| 0x1500 | `B0BL` | 0x1600 | `CHNC` | 0x1700 | `CHCR` |
| 0x1800 | `BCDC` | 0x1b00 | `TG0V` | 0x120a | `BCFW` |

Battery immediates (size the kext passes): `B0FV` (4), `BNCB` (8), `BFS0` (1), `BDVT`, `BC4V`, `CHTL` (4) in
`smcNotifierHandler`; `CH0C` (1, write: charge inhibit) `modifyChargeState`; `CH0I` (1, write: external-connected inhibit)
`modifyConnectedState`; `CHCC` (1) `externalConnectedTimeout`; `CHTE`, `WAFC` (4, writes) `setPropertiesGated`; `B0LP`,
`SBCK` `handleLpemPropsGated`; `BDBI` (17) dead-battery boot data; `BDFU` (8, write) date of first use; `BFUE` (1), `BFUC`
(1/32) gas-gauge firmware update; `UB0C` (1), `UBNC` (2), `UPOF` (2) shutdown data; `UB0T` (8); `AC-N`, `AP-N`, `AY-N`,
`ANWP`, `U1S0` (1) adapter/power-out/accessory counts; `ATC0` (96/53) port controller info; `D1IQ`, `D1JQ`, `D0IG`; `I2CL`,
`BPEX` logs; `zSPp` (112) energy telemetry; `GCCM` (2), `BATC`/`BATD` (64) battery auth. Key tables in `__TEXT` (polled
sets and lifetime statistics; `evidence/smc-keys-AppleSmartBatteryManager.txt` and the data-segment scan):
`BRSC BUIC CHPS CHQi TG0B CHQv CHQw WAFS WAIR WARP WAVR WARI WARV WARF WAPS WASS BDD1 BQX1 BISS B0AV B0SS B0RS B0FG B0AC
B0IV TG0A B0CH TG0V` (`0xfffffe00075f7fd8`), the per-cell set `BQX1..4 BMW1..4 BC1A.. BQD1.. BDD1.. BC1V.. B0R1.. BR1W..`
plus `WA**` wireless-adapter keys (`0xfffffe00075f7aa0`), the `UB**`/`UPO*`/`CHT*`/`CHK*`/`SBO*`/`OBO*`/`BR00..14`/`B0**`
set (`0xfffffe00075f71d0`) and the `BL**` lifetime set (`0xfffffe00075f6ed0`). Types are not hardcoded: `_smcKeyInfo`
(`0xfffffe0009727ba0`) classifies each key at runtime (`flt `, `ioft`, integer widths).

`AppleHighVoltageCharger` contains no SMC key: its immediates (`DMC!`, `sMDV`, `2GCC`, `CQRI`) are PD vendor-message codes
for the adapter firmware path (`AdapterLPC11U37`, `AdapterCCG2`) (Confirmed).

## 6. DT node proposal (t6050; addresses Confirmed from the ADT, interrupt order Likely)

```dts
	smc_mbox: mbox@28c608000 {
		compatible = "apple,t6050-asc-mailbox", "apple,asc-mailbox-v4";
		reg = <0x2 0x8c608000 0x0 0x4000>;
		interrupt-parent = <&aic>;
		/* ADT smc interrupts [0x384 0x383 0x386 0x385]; sorted like the draft DT's ans_mbox */
		interrupts = <AIC_IRQ 899 IRQ_TYPE_LEVEL_HIGH>,
			     <AIC_IRQ 900 IRQ_TYPE_LEVEL_HIGH>,
			     <AIC_IRQ 901 IRQ_TYPE_LEVEL_HIGH>,
			     <AIC_IRQ 902 IRQ_TYPE_LEVEL_HIGH>;
		interrupt-names = "send-empty", "send-not-empty",
				  "recv-empty", "recv-not-empty";
		#mbox-cells = <0>;
	};

	smc: smc@28c600000 {
		compatible = "apple,t6050-smc", "apple,t8103-smc";
		reg = <0x2 0x8c600000 0x0 0x4000>,
		      <0x2 0x8e000000 0x0 0x100000>;	/* ASC + 0x1a00000, 1 MiB: the pattern of t8103/t8122/t6031 — see §8 */
		reg-names = "smc", "sram";
		mboxes = <&smc_mbox>;

		smc_gpio: gpio {
			compatible = "apple,smc-gpio";
			gpio-controller;
			#gpio-cells = <2>;
		};

		smc_hwmon: hwmon {
			compatible = "apple,smc-hwmon";
		};

		smc_reboot: reboot {
			compatible = "apple,smc-reboot";
			nvmem-cells = <&shutdown_flag>, <&boot_stage>,
				      <&boot_error_count>, <&panic_count>;
			nvmem-cell-names = "shutdown_flag", "boot_stage",
					   "boot_error_count", "panic_count";
		};
	};
```

No `power-domains` (ADT `power-gates` is empty). The mailbox base is ASC + 0x8000 as on t8103/t8122/t6031. The Linux
`sram` window is not the ADT's `reg[1]` (`0x28c050000+0x4000`): on t8103, t8122 and t6031 the DTs place it at ASC +
0x1a00000 with a 1 MiB size (`0x23fe00000`, `0x2ede00000`, `0x2a5e00000`), so t6050 gets `0x28e000000+0x100000` (Likely;
the SMC's `0x17` reply names the real shared-memory address and the driver checks it against this window). The
`reboot`/`rtc` subnodes are left out until the draft DT has the SPMI PMU node that provides their nvmem cells.
**Status (2026-10-16):** these two nodes are now generated by `kernel/experiments/t6050-dt/gen_t6050_dt.py` and carried by
patch 0007 (`smc` left `status = "disabled"` until a native session verifies the transport).

## 7. Linux delta (what to check or change; Linux facts from memory, labelled)

| # | Item | Label |
|---|---|---|
| 1 | Transport: `smc_rtkit` already uses endpoint 0x20 and this exact message layout (`SMC_MSG`/`SMC_ID`/`SMC_SIZE`/`SMC_WSIZE`/`SMC_DATA`, INITIALIZE = 0x17 returning the shmem address, ≤ 4-byte inline data, key-info size/type/flags with the type byte-swapped). No change expected | Confirmed (macOS) / Likely (Linux match from memory) |
| 2 | Events: `macsmc-hid` (`0x7201` button, `0x7203` lid) and `gpio-macsmc` (`0x7202`) match the `type<<24\|subtype<<16` layout decoded here; the GPIO key commands `0x04 << 24` (IRQ enable, bit 0) and `0x05 << 24` (ack) match macOS's IENA/ICLR writes to `gPxx`/`btnN` | Likely |
| 3 | Power-state keys: Linux's `macsmc-reboot` writes `MBSE` = `offw`/`rest` (matches); the macOS suspend path additionally writes `WKTP` = 2 and `MBSE` = `slpa`, reads `MBSE`/`MBSW` on wake and writes `MBSE` = `waka`; `NTAP` = 1 is written at start (Linux does this in `smc_core`, from memory). For S2idle on t6050 the `slpa`/`waka` pair is the thing to add if the SMC otherwise misses the sleep | Likely |
| 4 | Battery keys: the names `macsmc_power` uses (`B0AV`, `B0AC`, `B0RM`, `B0FC`, `B0DC`, `B0CT`, `B0TE`, `B0TF`, `B0AT`, `BRSC`, `CHCE`, `CHCC`, `CHLS`, `CH0C`/`CH0I`) are all present in this firmware's kext tables; `CH0B` was not seen (only `CH0C`, `CH0I`, `CH0J`) — if Linux writes `CH0B` for charge control, verify it exists on M5 with key-info first | Likely / Unknown (`CH0B`) |
| 5 | Thermal/hwmon: `macsmc-hwmon` enumerates keys by index and filters by prefix; macOS only reads `mTPL` here, so no key name is prescribed for Linux. The SMC runs the fans/thermal loop itself; no AP input is needed unless `readGPUDieTemp` is set (it is not) | Likely |
| 6 | Charger: the AP → SMC port/contract writes (`D%d**` family) come from `IOAccessoryManager` behaviours; Linux has no equivalent and M1/M2 charge without it; expected unnecessary on M5 too | Hypothesis |
| 7 | DT: the two nodes of §6 are in `kernel/patches/t6050/0007` (2026-10-16). `apple,t6050-asc-mailbox` and, since job 044 (2026-10-16), `apple,t6050-smc` (`bindings/mfd/apple,smc.yaml`, `apple,t8103-smc` fallback as t6020/t8122) are in the binding patch 0006; `dtbs_check` of the DTB reports 0 findings (`virtualization/jobs/044-t6050-dtbs-check/`). The `apple,t8103-smc` fallback is what the driver matches | Confirmed (node, schema) / Likely (fallback suffices) |
| 8 | ADT `reg[2]` (`0x28c810000`, 0x100) is not used by the analysed kexts; leave it out of the DT | Unknown purpose |

## 8. Open questions

1. Shared-SRAM window: the DT uses the t8103/t8122/t6031 pattern (ASC + 0x1a00000, 1 MiB); the ADT's `reg[1]` (16 KiB at `0x28c050000`) is a different window. Only the `0x17` reply tells.
2. `CH0B` on M5 (not referenced by the kexts; Linux may use it for charge limiting).
3. Whether the SMC needs `MBSE` = `slpa` before a Linux suspend to keep the lid/power-button wake sources armed.
4. `reg[2]` purpose; the `smc-pmu` `event_name-bitN` map (sanitized away) → wake-reason names.
5. Key types of the charger/battery keys on this firmware: only sizes are visible statically (key-info at runtime).

## 9. Reproduce

```
python3 -I build/macos-drivers/scripts/smc_keys.py AppleSMC                       # 4CC immediates + size hints
python3 -I build/macos-drivers/scripts/smc_keys.py AppleSmartBatteryManager 0xfffffe00075f80b8:66
# REA (Ghidra) on build/macos-drivers/members/AppleSMC.macho: addresses above; pseudocode in build/macos-drivers/evidence/
ioreg -p IODeviceTree -n smctempsensor0 -r -w0                                     # live "sensor" property (read-only)
```

# USB-C on t6050: Type-C PHY (ATC) and the USB-PD controller, from this Mac's macOS 26.6.2 drivers

2026-10-15, M5 REA session. **Offline analysis; nothing ran on the M5.** Proprietary inputs stay in
the ignored `build/macos-drivers/` (members, pseudocode, `evidence/notes-usb.md`,
`TypeCPhy-batch1.txt`, `AppleT6050TypeCPhy.strings.txt`). Labels as in
`kernel/experiments/cpu-power-smp/README.md`. Public references (not copied): AsahiLinux
`77cb8f24` (`t8122.dtsi`, `t8122-usbpd-spmi.dtsi`), m1n1 `57a9339` (SPMI gen-4 FIFO layout,
`tps6598x`-over-SPMI).

| Binary | Member sha256 | Role |
|---|---|---|
| `com.apple.driver.AppleT6050TypeCPhy` | `907632ec…a45e` | the t6050 ATC PHY (USB2 eUSB2 PHY, USB3/DP/CIO "ACIO" PHY, DP crossbar, PHY microcontroller client) |
| `com.apple.driver.AppleTypeCPhy` | derived (`AppleTypeCPhy.macho`) | generic lane/orientation/power-level logic (not decompiled; symbols only) |
| `com.apple.driver.AppleHPM` | `cf8935c2…3088` | USB-PD controller ("HPM") over I2C or SPMI |

## 1. Summary

1. **USB-PD is already a Linux problem that is solved.** The controllers are `usbc,sn201202x,spmi`
   on `nub-spmi-a0/a1`, exactly the M3 MacBook Air configuration the pinned Linux tree drives with
   `apple,sn201202x` over SPMI. macOS's SPMI transaction shape (select register, poll status byte,
   read the data window) is the same as the public m1n1/Linux backends. Work left is a DT delta
   (USIDs 0xc/0xa/0x8 + hpm2 on spmi-a1, interrupt mapping) — §3.
2. **The Type-C PHY is new.** t6050 has 44 register spaces instead of M3's five, an **eUSB2** USB2
   PHY block, and a PHY **microcontroller** (`acio-phy-cpu0`, RTKit, firmware pre-loaded and running
   under mBoot) whose completion bits macOS polls during PHY init. The pinned Linux `atcphy` driver
   (`apple,t8122-atcphy`) cannot drive it unchanged. For the USB-device-mode control channel
   (boot036) none of this matters: dwc3 runs on the PHY state m1n1 leaves. For host-mode USB2/USB3
   a new PHY driver is needed; the recovered sequences and block map are the starting point — §2.

## 2. Type-C PHY (`AppleT6050TypeCPhy`)

### 2.1 Register spaces (Confirmed, `start()` `09a37bf8` + ADT)

`start()` matches a static 44-entry table (`_sRegisters`, per-instance physical ranges) against
the provider's memory ranges and stores each as object range *i* (`this+0x210+0x20*i`), reporting
"found register range %d at …"; the ADT `atc-phy0` `reg` list has the same 44 entries in the same
order. Ranges used by the decompiled code:

| ADT `reg[i]` (atc-phy0) | Object field | Block name from the kext's log strings |
|---|---|---|
| `[0]` `0x2_a2a90000 +0x4000` | `this[0x42]` | `AUSBC_CFG_USB2PHY_BLK` — the eUSB2 USB2 PHY (Linux t8122 "usb2phy" sits at the same +0x2a90000 offset) |
| `[1]` `0x2_a2800000 +0x4000` | `this[0x46]` | `AUSBC_CORE_EVT_BLK` (`C0_UTMI_CLK_ACTIVE.EVT_CNT`, `C0_USB2_CTL`); also `usb-drd0 reg[4]` |
| `[2]` `0x2_a3000000 +0x4000` | `this[0x4a]` | `ACIOPHY_TOP_BLK` (`CFG0_TOP`, `CFG1_TOP`, `CFG_SLP_CTRL`, `UC_CTRL_REG`, `UC_STATUS` +0x16c, `SWITCH_CLK_BY_UC`) |
| `[3]..[35]` `0x2_a3000400 …` | `this[0x4e]..` | lane/PLL/AUX/BIST sub-blocks (`ACIOPHY_PLL_TOP_BLK`, `ACIOPHY_AUX_*`, `ACIOPHY_BIST_BLK`, `LANE%d_AUS40PMA_*`, `AUS40CMN_DIG_BLK`, `ACIO80PHY_UC_REGS_BLK`) — which index is which is not yet resolved (**Unknown**, resolvable from the per-function base indices in `TypeCPhy-batch1.txt`) |
| `[36]` `0x2_a3040000 +0x20000`, `[37]` `0x2_a30c0000 +0x10000` | | the PHY microcontroller's `__TEXT`/`__DATA` windows (ADT `acio-phy-cpu0 segment-ranges`) |
| `[38]` `0x2_a3140000 +0x1c000` | | contains the uC mailbox/ASC at `0x2_a3148000` (`acio-phy-cpu0` reg) |
| `[39]` `0x2_a3200000 +0x4000` | `this[0xde]` | `ATCPHY_CFG_BLK` (power-down control, spare registers, DP clock switch) |
| `[41]` `0x2_a0000000 +0x8000` | | Likely the AXI2AF block (Linux t8122 "axi2af" is at +0 of the ATC window) |

### 2.2 Recovered bit fields (Confirmed: each write is followed by a log of the field name)

`ATCPHY_CFG_BLK` (range 39): `POWER_DOWN_CONTROL_0` (+0x0): bit 0 `ACIOPHY_SLEEP_B_SML_IN`,
bit 1 `ACIOPHY_SLEEP_B_BIG_IN`, bit 2 `ACIOPHY_CLAMP_EN`, bit 3 `ACIOPHY_AHB_RESET_N`,
bit 4 `ACIOPHY_RESET_N`; `POWER_DOWN_CONTROL_1` (+0x4): bit 0 `SLEEP_B_SML_OUT`, bit 1
`SLEEP_B_BIG_OUT`, `ACIO80PHY_AHB_CLK_ACK`; `SPARE_REGISTERS_0` (+0x8): bit 0 `CFG_S2R_FSM_EN`,
bit 1 `CFG_S2R_USB_LN_SWAP`; `ACIO80PHY_AHB_CLK_REQ` (+0x2c) bit 0. De-asserting a sleep input
waits ≤ 1 ms for the matching `_OUT` bit (`09a7313c`, `09a737ec`).

`AUSBC_CFG_USB2PHY_BLK` (range 0, eUSB2): `USB_CTL` (+0x0) `USB_MODE` [2:0]; `USB2PHY_CTL` (+0x4):
bit 0 `USB2PHY_RESET`, bit 1 `USB2PHY_PORT_RESET`, bit 2 `USB2PHY_APB_RESETN`, bit 3
`USB2PHY_SIDDQ`; `USB2PHY_SIG` (+0x8): bit 2 `VBUS_VALID_EXT_FORCE_VAL`, bit 3
`VBUS_VALID_EXT_FORCE_EN`; `USB2PHY_MISC_TUNE` (+0x1c): bit 29 `USB2PHY_APBCLK_GATEOFF`, bit 30
`USB2PHY_REFCLK_GATEOFF`.

`ACIOPHY_TOP_BLK` (range 2): `CFG0_TOP` (+0xc): bit 2 `CMN_SLEEP_B_SML_IN`, bit 3
`CMN_SLEEP_B_SML_IN_OV`; `UC_STATUS` (+0x16c) bit 0 `CSR_UC_IDLE`; `UC_CTRL_REG.UC_TNBL_DONE`.

### 2.3 Sequences (Confirmed order of the named steps; unnamed writes omitted)

* `eusb2phy_init(bool, bool)` (`09a3b744`): `USB2PHY_SIG |= FORCE_VAL`, `|= FORCE_EN`; 10 µs;
  `USB2PHY_CTL &= ~SIDDQ`; 10 µs; `&= ~USB2PHY_RESET`; `&= ~PORT_RESET`; `|= APB_RESETN`;
  `MISC_TUNE &= ~APBCLK_GATEOFF`, `&= ~REFCLK_GATEOFF`; 5 µs; `USB_CTL.USB_MODE = mode`.
  Shutdown (`09a3ce54`) is the reverse with `USB_MODE = 4`. The delays are `IODelay` calls with the
  literal arguments shown (unit µs, Likely).
* `aciophy_phy_powerup_rst` (`09a569b4`, 8 waits): `AHB_CLK_REQ &= ~1` → `AHB_RESET_N` set → wait
  `AHB_CLK_ACK` → wait `ACIOPHY_BIST_BLK_USBPHY_MAC_STATUS2.USBPHY_MAC_LN0_PHY_STATUS_2` →
  `AHB_CLK_REQ |= 1` → `RESET_N` cleared → `AHB_RESET_N` cleared → … → `CFG_S2R_FSM_EN` cleared →
  wait `AHB_CLK_ACK`. (The unnamed writes between the named steps are in the evidence file.)
* `aciophy_phy_init_partC` (`09a58ca4`): `CFG_S2R_USB_LN_SWAP` per orientation; 5 ms; **wait
  `UC_CTRL_REG.UC_TNBL_DONE`** (the uC has applied its tunables); 100 µs; wait
  `USBPHY_MAC_LN0_PHY_STATUS_2`. `aciophy_uc_idle` (`09a71af8`) polls `UC_STATUS.CSR_UC_IDLE` ≤ 1 s.
* Tunables: `applyTunables(range, OSData)` (`09a746c4`) applies 12-byte records
  `{u32 offset (27-bit), u32 mask, u32 value}` as `reg = (reg & ~mask) | value`, bounds-checked
  against the range — the same encoding as the ADT `tunable_*` properties and the Linux `atcphy`
  tunable applier. ADT atc-phy0 carries `tunable_USB2PHY_{DEV,DFLT,HOST}`, `tunable_ATC_COMMON_CFG`,
  `tunable_ATC_FABRIC`, `tunable_AUS40CMN_SHM`, `tunable_AUSPLL_CORE`, `tunable_CIO4PLL_CORE`,
  `tunable_LN{0,1}_RX_*`, `tunable_UC_REGS_CIO_DFLT`, `tunable_ATC0AXI2AF(_LIOA)`.

### 2.4 The PHY microcontroller (Confirmed data, Linux impact Likely)

`start()` resolves the `acio-phy-cpu` phandle to an `IOSlaveProcessor` ("couldn't set up embedded
CPU" otherwise). ADT `acio-phy-cpu0` = `iop,mxwrap`, child `iop-aciophy0-nub` = `iop-nub,rtbuddy-v2`
with (live registry) `pre-loaded = 1`, `running = 1`, `dont-power-on`, `no-firmware-service`,
`reconfig-firmware`, `user-power-managed = 1`. So mBoot loads and starts the PHY firmware before
the OS; the kernel driver only waits on its status bits and talks to it through
`AppleTypeCPhyCIO80PhyMBI` (USB4 v2 / CIO80 only). **Linux should leave the uC alone** (not power
its domain off, not reset it) and poll `UC_TNBL_DONE`/`CSR_UC_IDLE` where macOS does.

### 2.5 What a Linux driver needs (scope, not done)

| Item | Status |
|---|---|
| DT: `apple,t6050-atcphy` node with the 44 `reg` ranges (names from §2.1), `#phy-cells`, power domains `ps_atc0_{common,usb_aon,usb,phymxwrap}` (the boot036 DT disables them for device mode) | design only |
| eUSB2 PHY init for host/device mode (§2.3) | sequence recovered; untested |
| ACIO (USB3) lane bring-up: `aciophy_phy_init` partA/B/C, `cmn_init`, `xbar_config`, `slpctrl_init`, `apply_usb_tunables` (`09a5c8ac`), `usbClientSetACIO` (`09a763dc`); ~200 unnamed writes | evidence saved, not reconstructed |
| DP alt mode (`aciophy_dptx_*`, DP 1.4 / DP 2 presets, `function-atc_dp_clock_source`) and CIO/Thunderbolt (`AppleTypeCPhyCIO80PhyMBI`, `tunable_*CIO*`) | out of scope |

## 3. USB-PD controller (`AppleHPM`, `usbc,sn201202x,spmi`)

| Fact | Evidence | Label |
|---|---|---|
| ADT: `hpm0`/`hpm1`/`hpm5` on `nub-spmi-a0` (`0x2_8a188000`), `hpm2` on `nub-spmi-a1` (`0x2_8a1a8000`); `reg[0].size` high word = SPMI USID: hpm0 0xc, hpm1 0xa, hpm5 0x8 (`port-type 17`, charge-only port: Hypothesis); interrupts hpm0 {11,17,19}, hpm1 {37,43,45}, hpm5 {63,69,71} | sanitized ADT | Confirmed |
| Pinned Linux `t8122-usbpd-spmi.dtsi`: `compatible = "apple,sn201202x"`, `reg = <0xc SPMI_USID>`, interrupts `11 "irq", 13 "select", 17 "sleep", 19 "wake"` — same USIDs and three of the four interrupts | source | Confirmed |
| macOS `publishHPMDevices` (`091b6214`) matches `usbc,sn201202x,spmi` (HAL type 3/5), reads the TPS6598x-style registers 0x0f, 0x00, 0x01, 0x05, 0x2c, 0x2d at start; `sendHPMReset` sends `GAID` to leave DFU (`hpm-exit-dfu`) | pseudocode | Confirmed |
| SPMI transaction (`readRegs` `091b5654`, `writeRegs` `091b526c`): select register (controller vfn `+0x8e0`, 2 or 0x12 bytes), poll ≤ 1000 × 1 µs until the 2-byte status at SPMI offset 0 echoes the register in bits [6:0] with bit 7 clear (byte 1 = actual length), read the length at 0x1f and the data at offset 0x20; writes put the payload at 0xa0 then select the register and poll offset 0 | pseudocode | Confirmed; equivalence with the public m1n1/Linux SPMI backends Likely |
| `interrupt-type` array parallel to `interrupts`; live hpm0 has {0, 2, 3} for interrupts {11, 17, 19}: 0 = the HPM interrupt (Linux "irq"), 2 = SPMI sleep, 3 = SPMI wake (`AppleHPMARMSPMI::start` `091b4838`); type 1 takes its own path in `initSingleHPM` (`091a0624`) and does not occur in our ADT: Likely the Linux "select" line (irq 13 on t8122) | pseudocode + live registry | Confirmed (0/2/3); Likely (1 = select) |

**Linux delta (prepared, not applied):** a `t6050-usbpd-spmi.dtsi` after the t8122 file with our
USIDs and interrupt numbers (read `interrupt-type` live to assign irq/sleep/wake; the "select"
interrupt is absent in our ADT), connectors wired to `dwc3_{0,1,2}_hs` and the (future)
`atcphy{0,1,2}_typec_lanes`. No driver change expected. Not needed for boot036 (device mode).

## 4. Open questions

1. Which ADT `reg` index holds each named ACIOPHY sub-block (lane, PLL, AUX, BIST) — derivable from
   the base indices in the saved pseudocode.
2. The unnamed register writes in `aciophy_phy_init*`/`cmn_init`/`xbar_config` (values and order).
3. Whether the uC needs a "reconfig" after a Linux-side PHY reset (`reconfig-firmware` flag).
4. hpm5's role (`port-type 17`) and the missing "select" interrupt.

## 5. Evidence index

| Function | Address | Member |
|---|---|---|
| `AppleT6050TypeCPhy::start` / `eusb2phy_init` / `eusb2phy_shutdown` | `09a37bf8` / `09a3b744` / `09a3ce54` | AppleT6050TypeCPhy |
| `aciophy_phy_init` / `_partA` / `_partB` / `_partC` / `aciophy_cmn_init` / `aciophy_xbar_config` / `aciophy_slpctrl_init` | `09a5b48c` / `09a5b458` / `09a5b368` / `09a58ca4` / `09a4155c` / `09a554bc` / `09a5660c` | AppleT6050TypeCPhy |
| `aciophy_phy_powerup_rst` / `aciophy_phy_deassert_aciophy_reset` / `assert_aciophy_reset` / `de_assert_aciophy_{reset,clamp,apb_reset,sleep_big,sleep_sml}` / `aciophy_uc_idle` | `09a569b4` / `09a56810` / `09a7277c` / `09a72918`,`09a72abc`,`09a72dfc`,`09a7313c`,`09a737ec` / `09a71af8` | AppleT6050TypeCPhy |
| `applyTunables` / `aciophy_apply_usb_tunables` / `usbClientSetACIO` / `initUSB2` / `initACIO` / `setDevicePowerState` / `setPhyMxwrapPowerState` | `09a746c4` / `09a5c8ac` / `09a763dc` / `09a76e98` / `09a76ecc` / `09a75534` / `09a74d04` | AppleT6050TypeCPhy |
| `AppleHPMARMSPMI::readRegs` / `writeRegs` / `start` / `publishHPMDevices` / `sendHPMReset` / `readIECSReg`; `AppleHPMInterface::initSingleHPM` | `091b5654` / `091b526c` / `091b4838` / `091b6214` / `091b6e14` / `091b513c`; `091a0624` | AppleHPM |

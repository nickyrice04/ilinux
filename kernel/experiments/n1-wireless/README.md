# N1 Wi-Fi/Bluetooth on t6050: what the macOS 26.6.2 kernel side shows (first pass)

2026-10-16, M5 REA session. Offline; nothing ran on the M5; macOS read-only. Inputs: `build/macos-drivers/members/
AppleCentauriManager.macho` (strings), `IOBluetoothFamily.macho` (symbols), the sanitized ADT, and the earlier project pass
`reverse-engineering/findings/driver-interfaces-2026-10-13/` (ACIPC ring facts from the DriverKit plists; not redone here).
Labels: Confirmed / Likely / Hypothesis / Unknown.

## 1. Summary

1. **The N1 ("Centauri") is a PCIe endpoint on `apcie0` port 0** (Confirmed): `/arm-io/apcie0/pci-bridge0` carries
   `centauri-builtin`, `built-in`, `function-pcie_port_control`, `function-perst`, `function-warm_reset`, `enable-ptm`,
   `keep-root-port-on`, `pci-l1ss-enable` and Gen3/4/5 shadow tunables; port 1 is the SD reader (`pci17a0,9755`).
2. **The kernel-resident driver is lifecycle glue only** (Confirmed from `AppleCentauriManager` strings): chip power
   on/off ("chip is already powered on/off", "LPM entered, skip power off"), "sim-sleep", apcie error handler and
   link-training-timeout handling, `IOPCIDevice` power states, and launching three DriverKit dexts (`CentauriAlpha` =
   WLAN, `CentauriBeta` = Bluetooth, `CentauriControl`); an FTDI USB "wire" exists for debug. The packet protocol
   (ACIPC) lives in user space and is not in the kernel collection.
3. **Bluetooth**: `/arm-io/bluetooth` (`transport-encoding`, `local-mac-address`, both sanitized) and the kernel
   `IOBluetoothFamily` (generic HCI/L2CAP/HID stack, 1069 functions; its HCI controller personality matches
   `IOUSBHostDevice` only). No N1 transport class exists in the kernel stack, so N1 HCI framing is in the Beta dext
   (Confirmed by absence; the earlier pass measured HCI/ACL/SCO ring sizes from the plists).
4. **Linux delta**: a t6050 `apcie` compatible and `dart-apcie0` for enumeration, then a new WLAN driver (Apple's own
   silicon; `brcmfmac` does not apply) and an HCI transport over ACIPC. First milestone: enumerate `106b:1902` (WLAN,
   10 MSI) and `106b:1903`/`106b:1181` (BT, 2 MSI) (IDs from the DriverKit plists in the earlier pass; Likely).

## 2. ADT facts (Confirmed)

| Node | Facts |
|---|---|
| `/arm-io/centauri` | `device_type centauri`; `function-sac` (slow adaptive clocking via SMC, matches the kext's `kAppleCentauriManagerSACFunctionProperty`), `function-error_detect`; `interrupts [0x12, 0x6000004]` with parent **`aop-gpio0`** (a wake/error GPIO on the AOP GPIO block); `wifi-antenna-sku-info`, `ChipID`, `ChipRevision`, `ModuleVendor`, `WiFiHardwareHealthy`, `BTHardwareHealthy` (values sanitized) |
| `/arm-io/apcie0` | `apcie,t6050`; `reg[0] 0x1cb0000000+0x10000000` (config/ECAM window), `reg[1] 0x214000000+0x4000` (+ more); interrupts `0x5f3 0x5fb 0x603 0x60b`; `apcie0-piodma` (`pcie-apiodma,t6020`) |
| `/arm-io/apcie0/pci-bridge0` | `apcie-bridge`, N1 port (above); `pci-bridge1` = SD reader |
| `/arm-io/apciec0..2` | `apciec,t6050` (Thunderbolt/USB4 PCIe tunnels, not the N1) |
| `/arm-io/bluetooth` | `transport-encoding` (sanitized), `local-mac-address` (sanitized) |

## 3. Kernel driver facts (Confirmed, strings; `AppleCentauriManager` has only 9 functions)

Classes: `AppleCentauriManager`, `AppleCentauriManagerHelper`, `AppleCentauriManagerLogger`,
`AppleCentauriManagerUSBController`, `AppleCentauriManagerUserClient`. Boot-args/properties seen: `centauri-builtin-disable`,
`centauri-driverkit`, `centauri-module-factory-env`, `centauri-driver-sim-sleep-enable`, `centauri-panic-link-down`,
`centauri-panic-link-training-timeout`, `kCentauriManagerChipPowerStateKey`, dext relaunch bookkeeping
("Dext crashed for pci device %s"), "firmware boot timestamps". The manager owns the PCIe error handler
("failed to set apcie error handler", "PCIe error: type %u") and tx/rx "pipes" to the dexts.

## 4. Linux delta

| # | Item | Label |
|---|---|---|
| 1 | PCIe: add `apple,t6050-pcie` (or the t602x fallback) for `apcie0` with its DART and the port-0 PERST/clkreq GPIO functions (`function-perst`, `function-clkreq` on the bridge node); the SD reader on port 1 is a cheap first test of the link | Likely |
| 2 | WLAN: no existing Linux driver; needs an ACIPC transport (rings/doorbells per the earlier pass) plus a cfg80211 driver speaking the N1 firmware's own protocol (Unknown, user-space dext only) | Confirmed (scope) |
| 3 | Bluetooth: HCI over the Beta dext's ACIPC rings; the kernel `IOBluetoothFamily` gives no framing details | Confirmed (scope) |
| 4 | Power: the chip's power/wake go through the manager's platform functions (`function-sac` → SMC, GPIO on `aop-gpio0`); Linux needs the AOP GPIO block for the wake line | Likely |

## 5. Open questions

1. Which `apcie0` lane/clock configuration the N1 uses (`lane-cfg`, `link-state-power` sanitized).
2. Whether the N1 firmware is pre-loaded by iBoot or downloaded by the dexts (no firmware file name in the kernel strings).
3. The `transport-encoding` value of `/arm-io/bluetooth`.

# Review of `betizzel/omarchy-m5`: what it offers a native Omarchy boot on our M5 Max

2026-10-15, side session for the M5 agent. **Offline review. Nothing from the
reviewed repository was built, run, sourced or imported, and none of its code
was copied.** Labels: **Confirmed / Likely / Hypothesis / Unknown**. Where a
row says Confirmed about the other repository, it means "the repository
contains this", not "this works".

## Scope, sources and citation format

| Item | Value |
|---|---|
| Reviewed repository | `github.com/betizzel/omarchy-m5`, HEAD **`15cd70c1fad65322b85be4de4362cbed816a11c1`** (2026-10-11). 74 commits since 2026-09-21, listed through the GitHub API. |
| Local copy | Shallow clone (depth 1) in `~/Documents/iLinux/apple-silicon-linux-research/third_party/betizzel-omarchy-m5/`, ignored there by `.gitignore:20` (`third_party/`). Treated as untrusted data. |
| Extra data read | All commit messages (API). `docs/HANDOFF.md` as of `45ecc1f`, removed from tracking in `8e7afbf`, read as text through the API and not stored in this repository. |
| Our comparison set | `build/native-boot035/verified/t6050-j716c-stage-b.dtb` (sha256 `b1105bbf…`) and `kernel.config` (`4f7f4590…`); both match `build/native-boot035/verified/SHA256SUMS`. Also `build/native-boot035/verified/initramfs-stage-b.cpio.gz`, `kernel/patches/t6050/`, `native/boot/attempt15-review-2026-10-15.md` and `hardware/adt/adt-sanitized.json`. |
| Pinned clones (research workspace) | `third_party/m1n1` at `57a9339`. `third_party/asahi-linux`: branch `t6050-local` on `asahi` `77cb8f24`; a sparse checkout without `drivers/usb` or `drivers/hid`. |
| How the DTB was read | Decompiled with the workspace's `third_party/dtc/dtc`, the binary `kernel/experiments/t6050-dt/validate.sh` uses. |

How paths are cited:

* `omarchy-m5:path:line` is a file in the reviewed snapshot.
* `omarchy-m5@sha` is one of its commits.
* A bare path is a file in this repository (`ilinux-publish`).
* `third_party/…` is a pinned clone in the research workspace.
* One host path outside both repositories is marked as such where it appears.

## Summary

| Question | Short answer | Label |
|---|---|---|
| 1. USB gadget | Plain `snps,dwc3` in peripheral mode, high speed only, with two DARTs per core and **no PHY, power domain or reset**. It relies entirely on the PHY and PMGR state m1n1 leaves behind, and it disables the 12 ATC port domains so Linux never touches them. The gadget is CDC-EEM only (bulk endpoints). There is no ATC PHY, no SPMI/ACE3 USB-PD node and no Linux USB patch (`omarchy-m5:dt/t6050-storage-net.dtsi:50-180`, `omarchy-m5:scripts/usb-gadget-net.sh`). | Confirmed (content). Works on J714s: Likely |
| 2. Keyboard and trackpad | The MTP RTKit coprocessor, pre-loaded by iBoot, plus DockChannel HID with a new **ring transport** for M4/M5 firmware. The transport is rebased from the unmerged GravityLinux/linux PR #1 (`omarchy-m5:patches/linux/0005-…`). The trackpad needs `tpmtfw-<board>.bin` converted from the restore bundle (`omarchy-m5:scripts/extract-tpmtfw.py`). | Confirmed (content). Works on J714s: Likely |
| 3. PMGR | No `smc_i2cm` domains (dropped 2026-10-02). `pd_ignore_unused` is on the command line, plus the same sync_state fix as our boot034. Always-on means ADT-critical *and* on at handover (69 of 273). The framebuffer claims **no** display domain (`omarchy-m5:scripts/adt2pmgr.py`, `omarchy-m5:patches/linux/0004-…`, `omarchy-m5:dt/t6050-jxxx.dtsi:27`). | Confirmed |
| 4. Display and desktop | m1n1's simple-framebuffer feeds simpledrm and fbcon, all built in, plus an efifb earlycon patch for early logs. **No desktop**: Hyprland and Wayland appear nowhere. Userspace is an Arch Linux ARM rootfs on an NVMe partition (`omarchy-m5:configs/omarchy-bringup.config`, `omarchy-m5:README.md:29`). | Confirmed |
| 5. Evidence | m1n1-proxy captures from a J714s are committed. **No Linux log, trace, photo or video** exists at HEAD or in the history. The Linux results exist only in commit messages and in a handoff note that was later removed (`omarchy-m5:docs/research/probe-logs/`, `omarchy-m5@b46c57d`). | Confirmed for what exists. Claims: Likely, not reproduced |

Two of their PMGR fixes predate ours:

* genpd sync_state honouring `pd_ignore_unused`: `omarchy-m5:patches/linux/0004-…` in `omarchy-m5@79a0261` (2026-10-02). Ours is boot034 (`kernel/experiments/genpd-sync-state/README.md:3`, 2026-10-14).
* Dropping the SMC I2C-master domains: `omarchy-m5:scripts/adt2pmgr.py:59-68` in `omarchy-m5@24858b0` (2026-10-02). Ours is boot035 (`native/boot/attempt15-review-2026-10-15.md`, 2026-10-15).

The two projects reached each fix independently, which supports both of our decisions (Likely). Their stated mechanism for the SMC domains differs from ours (section 3, point 1).

## Licence, provenance and privacy

* **No licence at HEAD (Confirmed).** `omarchy-m5@f595f7a` added an MIT `LICENSE` (2026-10-10 19:21Z) and `omarchy-m5@9b3eee7` set its holder. `omarchy-m5@45ecc1f` removed it at 19:25Z with the message "licensing is premature at this stage". Without a repository-level grant, the default is all rights reserved.
* **Per-file tags.** Some files carry SPDX tags:
  * device trees: `GPL-2.0+ OR MIT` (`omarchy-m5:dt/t6050.dtsi:1`);
  * most scripts: `MIT` (`omarchy-m5:scripts/adt2pmgr.py:2`);
  * the host shims: `GPL-2.0`;
  * the new files in `omarchy-m5:patches/linux/0001-…`: `GPL-2.0-only`.

  These carry no tag: Linux patches 0002–0009, all m1n1 patches, `scripts/usb-gadget-net.sh`, `scripts/host-usbnet.sh`, `scripts/extract-tpmtfw.py`, the configs and all docs. We copy nothing either way.
* **AI-written (Confirmed).** Every commit carries `Co-authored-by: Claude`, and the first also names Devin (`omarchy-m5@fdb320c`). Like our own drafts (`kernel/patches/t6050/README.md:5-8`), nothing derived from this repository can go to Asahi.
* **SMP work based on disassembly (Confirmed).** The SPTM and iBoot conclusions come from running Ghidra or objdump on Apple binaries (`omarchy-m5@0b0c215`, `@6e8c887`, `@23e4058`). That work is out of scope for this review and is not used here.
* **Early DT provenance.** The first DT skeleton took its MMIO addresses from "the J716c ioreg dump" (`omarchy-m5@1600383`). That is plausibly the dump in m1n1 PR #631, which `kernel/patches/t6050/README.md:74` excludes (Hypothesis). The current DTs were regenerated from the author's own J714s runtime ADT (`omarchy-m5@ff6204e`, `@23a922f`).
* **Their machine identifiers.** Volume-group IDs and disk/partition GUIDs appear in `omarchy-m5:docs/research/probe-logs/nvme-gpt-j714s-2026-10-01.log` and in the removed handoff note. None are reproduced here.

## 1. USB device-mode link

### What the repository has (all Confirmed as content)

* **Device tree.** `omarchy-m5:dt/t6050-storage-net.dtsi:50-165`, generated by `omarchy-m5:scripts/gen-storage-net-dt.py:75-118`.
  * Three cores: `usb@2a2280000`, `usb@2aa280000`, `usb@382280000`.
  * Each has `compatible = "snps,dwc3"` only (no Apple glue), the core window `0xcd00`, `dr_mode = "peripheral"` and `maximum-speed = "high-speed"`.
  * Quirks (`:64-67`): `snps,usb2-gadget-lpm-disable`, `snps,dis_u2_susphy_quirk`, `snps,dis_u3_susphy_quirk` and `snps,dis_enblslpm_quirk`.
  * Each core has `iommus` on two `apple,t8110-dart` DARTs that carry **no** `power-domains`.
  * The cores have **no `phys`, `power-domains` or `resets`** (`:68-69`).
* **ATC port domains disabled.** `&ps_atc{0,1,2}_{common,usb_aon,usb,phymxwrap} { status = "disabled"; }` (`:168-180`). The reason given (`omarchy-m5:scripts/gen-storage-net-dt.py:120-125`): when the domains were described and unclaimed, the pwrstate probe armed AUTO_ENABLE and every DWC3 soft reset timed out (-110). Disabled nodes are never probed, so the hardware stays as m1n1 left it.
* **No PHY or USB-PD description.** `omarchy-m5:dt/` has no ATC PHY node, USB-PD controller, typec connector or role switch. The only SPMI node is `nub_spmi0`, for the PMIC's NVMEM cells (`omarchy-m5:dt/t6050-smc.dtsi:37-111`), driven by a polled gen-4 SPMI patch (`omarchy-m5:patches/linux/0008-…`).
* **Kernel config** (`omarchy-m5:configs/omarchy-storage-net.config:19-35`):
  * `USB_DWC3=y` and `USB_DWC3_DUAL_ROLE=y`; `USB_DWC3_APPLE` unset;
  * `USB_LIBCOMPOSITE=y` and `USB_CONFIGFS=y` with NCM/ECM/ACM;
  * `FTRACE=y`, for the dwc3 tracepoints.

  Everything is built in because their initramfs carries no modules. The fragment does not list `USB_CONFIGFS_EEM`. It probably comes from the arm64 defconfig their build merges first (`omarchy-m5:scripts/build-kernel.sh:22`), as it does in our config (Likely).
* **Gadget.** `omarchy-m5:scripts/usb-gadget-net.sh:50-79` builds one configfs gadget per UDC (VID:PID 1d6b:0104, serial `m5pro-<n>`). Each gadget has a single **CDC-EEM** function and the address 10.55.<n>.2/24.
  * Why EEM (`:5-12`, `omarchy-m5@d5abf0c`): with NCM+ACM, SET_CONFIGURATION completed, but the controller raised no further event after NCM queued its first interrupt-IN notification.
  * m1n1's own gadget never transmits on an interrupt endpoint, and the ADT has `ncm-interrupt-ep-disabled` on this port.
  * An earlier -110 timeout was fixed by the LPM and SUSPHY quirks (`omarchy-m5@057dc0b`).
* **Host side.** A Linux ThinkPad with `cdc_eem`, NAT and udev rules (`omarchy-m5:scripts/host-usbnet.sh`).
* **Patches.** There is no Linux driver patch for USB. `omarchy-m5:patches/m1n1/0005-…` skips m1n1's USB-PD scan on T6050, because that scan hung their m1n1 before the proxy came up.

### Reliance on m1n1's state: total (Confirmed, by design)

The DT comments say so, and our pinned m1n1 (`third_party/m1n1` @ `57a9339`) shows what m1n1 leaves behind:

* `usb_phy_bringup()` powers the ATC, DART and DRD domains, starts the USB2 PHY and parks the PIPE mux on the dummy PHY (`third_party/m1n1/src/usb.c:145-177`). It runs for every port (`third_party/m1n1/src/usb.c:315`).
* At handoff, `usb_iodev_shutdown()` (`third_party/m1n1/src/main.c:203`, `third_party/m1n1/src/usb.c:383`) only stops the dwc3 device side, soft-resets it and unmaps its buffers (`third_party/m1n1/src/usb_dwc3.c:1269-1293`).
* The power domains and the PHY stay up.

So Linux gets USB 2.0 only (`maximum-speed = "high-speed"`, PIPE mux on the dummy PHY at `third_party/m1n1/src/usb.c:175`), on whichever port the cable is in. Nothing can bring the PHY back after a suspend (`omarchy-m5:dt/t6050-storage-net.dtsi:59-63`).

### Against ours

| | omarchy-m5 | boot035 (`build/native-boot035/verified/`: decompiled `t6050-j716c-stage-b.dtb`, `kernel.config`, `initramfs-stage-b.cpio.gz`) |
|---|---|---|
| dwc3 nodes | 3, `snps,dwc3`, peripheral mode | none |
| USB DARTs | 6, enabled, no `power-domains` | 6 (`iommu@2a2f00000` …), `status = "disabled"`, `power-domains = <atcN_usb>` |
| ATC port domains | 12 disabled | All registered and unclaimed. Attempt 15's ladder released `atc?_usb_aon`, `atc?_phymxwrap` and `atc?_usb` for three ports, then `atc?_common_dp_3` (`native/boot/stage-b-2026-10-15-attempt15-result.md:136-142`) |
| Gadget stack | `LIBCOMPOSITE=y`, `CONFIGFS=y` | `USB_LIBCOMPOSITE=m`, `USB_CONFIGFS=m`, `USB_F_EEM/NCM/ECM=m`. The Stage-B initramfs contains only `/init`, so no gadget can load |
| PHY | none (m1n1's state) | `PHY_APPLE_ATC` not set; `USB_DWC3_APPLE=y` (unused without a node) |
| Tracing | `FTRACE=y` | not set |

**The hardware matches as far as our ADT shows (Confirmed for these properties).** In `hardware/adt/adt-sanitized.json`:

* `usb-drd0/1/2` have port numbers 1/2/3 and compatible `usb-drd,t6050`.
* drd0 uses interrupt 0x58b (1419) and `dart-usb0` uses 1423, the same as their DT.
* All three DRDs carry an `ncm-interrupt-ep-disabled` property. The name is present but its value is not exported. They report the same property for J714s.
* Our USB-PD controllers are the same part. `hpm0`, `hpm1` and `hpm5` sit on `nub-spmi-a0` and `hpm2` on `nub-spmi-a1`, all `usbc,sn201202x,spmi`.

**Their m1n1 0005 is not needed here (Confirmed).**

* Our installed boot021 m1n1 is `57a9339` with no local patches (`native/boot/boot021-package-manifest.json`).
* That build includes gen-4 SPMI (`a09a5e2`, 2026-07-23) and still runs the PD scan (`src/usb.c:312`).
* It answered the M1 in Stage A (`AGENTS.md:249`) and booted attempt 14 with the boot021 marker (`native/boot/stage-b-2026-10-14-attempt14-result.md:31`).

Their premise that m1n1 cannot speak gen-4 SPMI is wrong for any tree after `a09a5e2`, including their stated base (v2.0.0-2-g2460b, `omarchy-m5@98ae39c`). Why their m1n1 hung is Unknown.

### Implication

Our roadmap lists reusing the PHY state m1n1 leaves behind as an option for milestone 2 (`roadmap.md:63`). That is exactly what they ran, and it takes the ATC PHY driver off the critical path. The cost is high speed only and a fragile PHY.

Our M1 runs macOS (`native/boot/attempt15-review-2026-10-15.md:95`), so the choice of USB function matters. A read-only listing on this M5 (macOS 26.6.2; a host path outside both repositories) shows that `/System/Library/Extensions/AppleUSBEEM.kext` matches interface class 2/12/7 (CDC-EEM), next to `AppleUSBECM.kext` and `AppleUSBNCM.kext`. EEM's bulk-only gadget should therefore bind on a macOS host too (Likely; the M1's macOS has not been checked).

## 2. Keyboard and trackpad

### What the repository has (Confirmed as content)

* **SoC device tree** (`omarchy-m5:dt/t6050.dtsi:404-514`):
  * `mtp@294600000` (`apple,t6050-mtp`, `apple,rtk-helper-asc4`), with an `asc` register window and a 1 MiB `sram` window;
  * `mtp_mbox` (ASC mailbox v4, IRQs 676–679);
  * `mtp_dart` (t8110, IRQ 659, `apple,dma-range = <0x100 0x4000 0x0 0xffff0000>`, SIDs 0–4 through the multi-SID remap);
  * `mtp_dockchannel` (IRQ 660, FIFO pairs from `0x294b28000`) with the HID child `mtp_hid`:
    * compatibles `apple,t6050-dockchannel-hid`, `apple,t8132-dockchannel-hid` and `apple,dockchannel-hid`;
    * FIFO size 0x800;
    * `apple,helper-cpu = <&mtp>`.

  No PMGR domain is listed, because the T6050 ADT has no MTP_* domain (`:436-437`). iBoot pre-loads and starts the RTKit firmware (`pre-loaded = 1`); Linux only wakes it (`:423-424`).
* **Board device tree** (`omarchy-m5:dt/t6050-j714s.dts:19-79`):
  * enables the four nodes;
  * adds a `keyboard` alias so m1n1's `dt_set_ipd()` fills in the layout from `kblang-calibration`;
  * defines the child nodes `multi-touch` (`firmware-name = "apple/tpmtfw-j714s.bin"`), `keyboard`, `stm`, `actuator`, `tp-accel`, `tp_accel` and `mtp`.
* **Driver.** `omarchy-m5:patches/linux/0005-hid-dockchannel-mtp-ring-transport-for-m4-m5.patch` changes `dockchannel-hid.c`, `dockchannel.c` and `rtkit-helper.c`.
  * The `apple,t8132-dockchannel-hid` compatible selects the new transport (`:1245`).
  * It allocates a **2 MiB DMA ring** and registers it with the firmware over the comm interface (`:440-470`). A preparatory command precedes the registration; the patch notes that this command was observed in both macOS and standalone T8132 bring-up (`:452`).
  * DockChannel channel 0x00 becomes a notification doorbell (`:42`, `:1012`).
  * M2/M3 keep the FIFO path.
  * The HID driver now depends on `APPLE_RTKIT_HELPER` (`:9`), and clean stop/remove paths are added.

  Provenance (`omarchy-m5@beb66c4`): rebased from GravityLinux/linux PR #1, which is unmerged and "LLM-assisted per the PR". That PR is reported working on an M4 Air and an M5 MacBook Pro. A pass of review fixes followed (`omarchy-m5@ee06488`).
* **Kernel config** (`omarchy-m5:configs/omarchy-bringup.config:68-83`):
  * built in: DART, mailbox, RTKit, **RTKIT_HELPER**, DockChannel, HID_DOCKCHANNEL, HID_APPLE, HID_MAGICMOUSE, HID_GENERIC and HIDRAW;
  * `FW_LOADER_USER_HELPER` off, so a missing trackpad blob cannot stall `open()` for 60 s.
* **Firmware.** The keyboard needs none. The trackpad needs `tpmtfw-<board>.bin`, which `omarchy-m5:scripts/extract-tpmtfw.py` builds from the restore bundle's `Multitouch.im4p` using asahi-installer's `MultitouchFWCollection`.
  * It reads either the local Preboot `restore` directory or an IPSW, fetched with HTTP range requests.
  * The firmware must match the macOS that iBoot boots.
  * The script's own header still says "UNTESTED against Apple data" (`:5`). Yet `omarchy-m5@b46c57d` and the removed handoff note report trackpad events with that firmware (13.7k multi-touch events in 90 s). Which statement is current is Unknown.
* **Live state, read-only from m1n1** (`omarchy-m5:docs/research/probe-logs/mtp-probe-j714s.log`): ASC `RUN=0`, the I2A mailbox already non-empty, the DART not locked, iBoot's TCR/TTBR values present, and `pre-loaded: 1`.

### Against ours

* **DT.** Boot035's Stage-B DT (`build/native-boot035/verified/t6050-j716c-stage-b.dtb`, decompiled) has only the MTP DART (`iommu@294800000`), disabled and without `apple,dma-range`. It has no MTP, mailbox, DockChannel or HID node.
* **Config.** `build/native-boot035/verified/kernel.config` has `APPLE_DOCKCHANNEL=y`, `HID_DOCKCHANNEL=y`, and mailbox, RTKit and DART built in. However:
  * **`APPLE_RTKIT_HELPER` is not set.** The unchanged context of their patch shows that `dockchannel-hid` defers until its helper is bound (`omarchy-m5:patches/linux/0005-…:1299`). With no helper driver it would wait forever (Likely).
  * `HID_APPLE`, `HID_MAGICMOUSE` and `HIDRAW` are off.
* **Hardware match (Confirmed).** Our ADT agrees with theirs on every MTP value we can compare (`hardware/adt/adt-sanitized.json`):
  * `mtp` at `0x94600000`, interrupts 0x2a4–0x2a7 (676–679);
  * `dart-mtp`: IRQ 659, `remap` 1–4, `sid-count` 16, `vm-base` 0x10000004000, `vm-size` 0xffff0000;
  * `dockchannel-mtp`: IRQ 660;
  * `mtp-transport` children: `multi-touch`, `stm`, `keyboard`, `tp-accel` and `actuator`;
  * the `keyboard` node has `kblang-calibration`.

  The J714s MTP description should therefore fit our J716c with only the board file and the firmware name changed (Likely).
* **Our driver has no ring transport (Confirmed).** Their patch's pre-image blob for `dockchannel-hid.c` is `9cab638b3` (`omarchy-m5:patches/linux/0005-…:14`). That is exactly our pinned file: `77cb8f24:drivers/hid/dockchannel-hid/dockchannel-hid.c` = `9cab638b30c3…` in `third_party/asahi-linux`, present in the object store though not checked out. The same blob is recorded in `kernel/experiments/driver-contracts/dockchannel-hid/README.md:17`. The ring code exists only on the patch's added side.
  * The pre-images of their `dockchannel.c`, `rtkit-helper.c`, `pmgr-pwrstate.c`, `irq-apple-aic.c` and `sart.c` changes also match our pinned blobs; their `pmdomain/core.c` and `spmi-apple-controller.c` pre-images do not.
  * Our own bounds/rearm patch (`kernel/experiments/driver-contracts/dockchannel-hid/0001-dockchannel-hid-validate-input-bounds.patch`) edits the same file.
  * Their patch also gives a provisional answer to our open framing question (`kernel/experiments/driver-contracts/dockchannel-hid/scout.md:12`). On M4/M5 the 8-byte header, a 4-aligned body and the checksum stay (`omarchy-m5:patches/linux/0005-…:976`). Only the carrier changes, from the FIFO to the DMA ring (Likely; untested by us).
* **Hypervisor versus native.** Their keyboard was first verified with Linux running as a guest of the m1n1 hypervisor (`omarchy-m5@beb66c4`). Native use is reported only in the later, removed handoff note. Our hypervisor path stopped at the chainload (`native/hv/hv002-session2-2026-10-14-result.md`), so only the native route applies to us.

## 3. PMGR power domains

| | omarchy-m5 (J714s) | boot035 Stage-B (J716c; decompiled `build/native-boot035/verified/t6050-j716c-stage-b.dtb`) |
|---|---|---|
| Domains / always-on | 273 / 69 (`omarchy-m5:dt/t6050-pmgr.dtsi`) | 181 / 34 |
| `smc_i2cm*` | Absent: `omarchy-m5:scripts/adt2pmgr.py:59-68` skips them (`@24858b0`, 2026-10-02) | Absent since boot035 (`native/boot/attempt15-review-2026-10-15.md`). The full `build/native-boot035/verified/t6050-j716c.dtb` still has seven (`0x8028`–`0x8058`) |
| CPU-complex domains | Not described (`omarchy-m5:scripts/adt2pmgr.py:50-57`) | Not described |
| `pd_ignore_unused` | On the command line (`omarchy-m5:scripts/mktether.sh:57-61`, `omarchy-m5:scripts/mkpayload.sh:37-40`) plus `omarchy-m5:patches/linux/0004-…`, so sync_state honours it | The same flag and the same sync_state fix in boot034 (`kernel/experiments/genpd-sync-state/README.md`), plus our release ladder |
| Always-on rule | ADT-critical **and** on at handover (`omarchy-m5:scripts/adt2pmgr.py:18-24`, `:134-139`; snapshot `omarchy-m5:dt/t6050-j714s-pmgr-boot-state.json`) | ADT-critical, plus hand-picked domains |
| Extra write guard | `omarchy-m5:patches/linux/0003-…`: skip the probe write when AUTO_ENABLE is already set. Their example: a store to `dispext0_cpu` "never completes" | None. `disp_cpu` and `dispext*_cpu` are `status = "disabled"` (`kernel/experiments/t6050-dt/gen_t6050_dt.py:184`), so that write never happens |
| ATC port domains | 12 disabled | All live |
| Framebuffer domain | None (`omarchy-m5:dt/t6050-jxxx.dtsi:27-28`, a TODO) | None |

Points that matter:

1. **SMC domains: same fix, different mechanism.**
   * Their reason is the probe's AUTO_ENABLE write on active domains (`omarchy-m5:scripts/adt2pmgr.py:59-62`). The write itself is at `third_party/asahi-linux/drivers/pmdomain/apple/pmgr-pwrstate.c:295-298`.
   * Our reason is an explicit power-off about 5.6 s before the reset (`native/boot/attempt15-review-2026-10-15.md`, "Conclusion").
   * On J716c, the probe-time write happened during attempt 15, because the probe runs for every registered domain. The reset came only 5.70–5.88 s after the sixth ladder release, about 17 s later (same review, point 3). Our data therefore favour the power-off (Likely).
   * Boot035 removes both writes, so attempt 16 cannot tell the two mechanisms apart. Whether the difference ever matters: Hypothesis.
   * In their J714s snapshot, `smc_i2cm0`–`5` are on at handover and `smc_i2cm6` is off. That matches the **six** releases attempt 15 logged (`native/boot/stage-b-2026-10-15-attempt15-result.md:136`), so J716c probably matches (Likely).
2. **Two of our always-on domains were off at their handover.**
   * On J714s, `afr` (`0x0f040300`) and `nub_spmi_a2` (`0x0f000200`) are off at handover. Their generator withholds always-on from both for that reason.
   * Linux force-powers any always-on domain it finds off (`third_party/asahi-linux/drivers/pmdomain/apple/pmgr-pwrstate.c:284-290`). They say that ends in an asynchronous SError on T6050 (`omarchy-m5:scripts/adt2pmgr.py:18-24`).
   * Boot035 marks both domains always-on. Attempts 14 and 15 reached PID 1, so either J716c differs or the forced power-on is harmless here (Unknown).
   * Their table also lists 98 domains that our DT does not describe. Most are fabric, memory-controller and die-link domains (`amcc*`, `fab*`, `b2b*`); the rest are `fppt*` and `pmgr_soc_ocla*`. We have six `venc1_*` domains they lack.
3. **Display domains, and a correction to the attempt-15 review.**
   * The review says `disp_cpu` and `disp_adma` "will be released by the ladder" (`native/boot/attempt15-review-2026-10-15.md:91`). In the boot035 Stage-B DT, `disp_cpu` is `status = "disabled"`, so Linux never registers or releases it (Confirmed).
   * Only `disp_adma` can be released. On J714s it is **off** at handover (`0x00000300`), so there may be nothing to release (Likely, if J716c matches).
   * On J714s, `disp_cpu` is on, with AUTO_ENABLE already set by iBoot (`0x1f0000ff`). That is exactly the case their 0003 patch guards.
   * The review also suggests claiming `ps_disp_cpu` from the framebuffer node, "as Asahi does". That conflicts with our generator disabling that node. In the pinned Asahi tree:
     * M4 claims `ps_disp_cpu` (with `apple,min-state = <4>`) and `ps_dptx_phy` (`third_party/asahi-linux/arch/arm64/boot/dts/apple/t8132-jxxx.dtsi:24-30`, `t8132-pmgr.dtsi:956-964`);
     * M3 Pro/Max claims `ps_disp_fe` (`t603x-j514-j516.dtsi:39-44`).

     Claiming `ps_disp_fe`, which is already always-on in ours, is the lower-risk option (Hypothesis).
   * Our generator's comment "Locked on M4 (Asahi t8132), don't touch" no longer matches the pinned t8132 tree (Confirmed; harmless).

## 4. Framebuffer, simpledrm and the desktop

* **Framebuffer (Confirmed).** `/chosen/framebuffer@0`, `apple,simple-framebuffer`, filled in by m1n1, with no power domain (`omarchy-m5:dt/t6050-jxxx.dtsi:24-31`). Same shape as ours.
* **Kernel (Confirmed)** (`omarchy-m5:configs/omarchy-bringup.config:11-66`):
  * built in: `DRM`, `DRM_SIMPLEDRM`, `DRM_FBDEV_EMULATION`, `FB`, `FRAMEBUFFER_CONSOLE` and `VT`;
  * a Terminus 16×32 font;
  * `CONFIG_RUST` off.

  Its comment at `:5-9` records that their first boot was silent because DRM was built as a module. Ours already has `DRM_SIMPLEDRM=y`, `FB=y`, `FRAMEBUFFER_CONSOLE=y`, `SYSFB_SIMPLEFB=y` and `EFI_EARLYCON=y`.
* **Early log on the panel.** `omarchy-m5:patches/linux/0001-t6050-early-fb-markers.patch` does two things:
  * It paints checkpoint bands into the framebuffer.
  * It fills `sysfb_primary_display` from compiled-in geometry before `parse_early_param()`, so `earlycon=efifb` works on a DT boot. The defaults are J714s-specific: `CONFIG_OMARCHY_FB_MARKER_BASE` = `0x10bd3110000`, 3024×1964 (`:24-40`). It withdraws the EFI type at `arch_initcall`, so simpledrm stays the only driver (`:238-268`).

  This addresses the gap described in `kernel/experiments/early-framebuffer/README.md:24-27`: an m1n1 boot provides no EFI screen information. It needs the address for each machine. Our launcher already fills in the marker base and stride in RAM (`kernel/experiments/early-framebuffer/README.md:48`) and could do the same here (Hypothesis).
* **Desktop: none (Confirmed).**
  * No script or config mentions Hyprland, Wayland, a compositor, Mesa or a session manager.
  * The README marks Wayland "not started" (`omarchy-m5:README.md:29`), and the removed handoff note lists "Hyprland on simpledrm" as the next step.
* **Userspace.** An Arch Linux ARM rootfs built on the host (`omarchy-m5:scripts/mkrootfs-image.py`):
  * The base tarball is fetched over plain HTTP (`:19`). There is no signature check, only a hint to check the `.md5` (`:89`).
  * The image is written to a 20 GB NVMe partition carved out of macOS's container (`omarchy-m5:scripts/prep-stub.sh`).
  * An Alpine busybox initramfs enters it with `switch_root` (`omarchy-m5:scripts/mkinitramfs.py`).

  Partitioning and boot-policy changes are off limits for us (`AGENTS.md:21-22`), and our milestone 3 is a RAM root, so this part does not transfer.

## 5. Evidence of real hardware runs

| Evidence | Where | Level |
|---|---|---|
| PMGR power state of 301 domains at m1n1 handover | `omarchy-m5:dt/t6050-j714s-pmgr-boot-state.json` | m1n1 proxy, J714s |
| MTP, DockChannel and DART registers | `omarchy-m5:docs/research/probe-logs/mtp-probe-j714s.log` | m1n1 proxy |
| NVMe initialisation and the GPT, read by m1n1 | `omarchy-m5:docs/research/probe-logs/nvme-gpt-j714s-2026-10-01.log` | m1n1 proxy |
| SMP tables, a start attempt and a dump of the SMP-RO window | `omarchy-m5:docs/research/probe-logs/t6050-smp-*` | m1n1 proxy |
| SMC key catalogue (3485 keys) | `omarchy-m5:docs/research/smc-keys-j714s.json` | m1n1 proxy |
| Linux boot, NVMe, USB-EEM and SSH, keyboard, trackpad, SMC, cpufreq | Commit messages `omarchy-m5@4dff297`, `@beb66c4`, `@b46c57d`, `@c8c4b5a` and `@87de8a2`; the removed `docs/HANDOFF.md` (`@45ecc1f`) | Prose only |

* **No Linux-side artifact exists (Confirmed).** There is no dmesg, journal, dwc3 trace, host-side `lsusb` or `ip` output, photo or video, either at HEAD or in the tree at `45ecc1f`. That tree's only extra files are four `HANDOFF*.md` notes (checked through the GitHub tree API).
* **The captures look genuine (Likely).** They agree with our J716c ADT on every USB and MTP address and IRQ compared (sections 1 and 2).
* **The prose is specific and records failures**, which makes fabrication less likely:
  * a 159 MB/s rootfs write;
  * 13.7k multi-touch events in 90 s;
  * cpufreq scaling from 1.344 to 4.308 GHz;
  * a failure: the battery driver panicked the M5 (`omarchy-m5@af76051`).
* **Contradictions:**
  * The "UNTESTED" header of `omarchy-m5:scripts/extract-tpmtfw.py` versus the trackpad claim.
  * The premise of their m1n1 0005 patch versus m1n1's history (section 1).
  * "405 power domains" in `omarchy-m5:FOR-AURORA.md:21` versus 273 in the shipped `t6050-pmgr.dtsi`. The 405 came from the on-disk ADT, which the 301-entry runtime ADT superseded (`omarchy-m5@23a922f`).
* **Sources are unpinned.** `omarchy-m5:scripts/fetch-sources.sh:8-11` uses m1n1 `main` and the tip of linux `asahi-wip-7.2`, so a build today would not reproduce their kernel.
* **Board.** Everything is J714s (M5 Pro, 15 cores). `omarchy-m5:dt/t6050-j716s.dts` is an 18-line stub, and there is no J716c board file.

**Verdict.**

* It is Likely that single-core Linux reached a userspace reachable over SSH on a J714s, with NVMe, USB-EEM and the internal keyboard working.
* No artifact we can inspect verifies this, and it is untested on J716c (Unknown).
* The device-tree and config choices are the useful part, because each one can be checked on our side without trusting the prose.

## Other cross-checks

* **AIC.** Their AIC patch (`omarchy-m5:patches/linux/0002-…`, an `apple,t6050-aic3` variant that skips the locked `VM_TMR_FIQ_ENA_EL2` write) addresses the same register our attempt 5 trapped on at `aic_init_cpu+0x9c` (`kernel/experiments/aic-t6050/README.md:10-17`). Confirmed: same register.
* **DAPF.** Their m1n1 skips the `/arm-io/dart-aop` DAPF on T6050 (`omarchy-m5:patches/m1n1/0001-t6050-kboot-bringup.patch:144-155`). Our `native/boot/dapf_guard.py:1-5,15` omits the same entry. Confirmed: same entry; the stated reasons differ.
* **J716c notes.** Their docs point to `qspqww/m1n1 t6050-j716c-bringup` (`omarchy-m5:docs/bringup.md`, References). `kernel/patches/t6050/README.md:74` already excludes that work for provenance. Not reviewed here.

## Testable ideas for the USB control channel and input

USB control channel (roadmap milestone 2):

Ideas 1–3 are now prepared offline as a DT-only candidate. They are not packaged
or run; job 040 passed. See `kernel/experiments/usb-gadget-dt/README.md`. That
work refines idea 1: all 39 `atc0-2` domains must be disabled, not just four per
port.

1. **Device tree only, no driver work.** Write the approach fresh rather than copying it:
   * one `snps,dwc3` peripheral node per USB-DRD, with `maximum-speed = "high-speed"` and the four `snps,*` quirks;
   * its two DARTs enabled **without** `power-domains`;
   * `status = "disabled"` on `ps_atc{0,1,2}_{common,usb_aon,usb,phymxwrap}`.

   Pitfall: a DART that keeps `power-domains = <atcN_usb>` while that domain is disabled defers, and the dwc3 core with it, forever.
   * Offline pass: `kernel/experiments/t6050-dt/validate.sh` is clean, and no ATC domain is left for the boot034/035 release ladder (`kernel/experiments/genpd-sync-state/README.md`, "What boot034 changes").
   * Native pass: the M1 sees a new USB device after the handoff. Once a userspace exists, `/sys/class/udc` lists the cores and dwc3 reports no -110.
   * Also record which `usb-drdN` (ports 1/2/3 in `hardware/adt/adt-sanitized.json`) the M1 cable uses, so a single-port DT remains an option.
2. **Built-in gadget stack.** Set `USB_LIBCOMPOSITE=y`, `USB_CONFIGFS=y` and `USB_CONFIGFS_EEM=y`, so that `USB_F_EEM` and `USB_U_ETHER` are built in; the Stage-B initramfs carries no modules (`build/native-boot035/verified/kernel.config`). Add `FTRACE` with the dwc3 events to diagnose a SET_CONFIGURATION that never completes.
   * A configfs gadget needs userspace writes that our diagnostic `/init` does not make.
   * For a first link test without userspace (Hypothesis, to check in a full kernel tree, since our sparse clone lacks `drivers/usb`), try the legacy Ethernet gadget (`USB_ETH=y`, currently unset) with its EEM option and RNDIS off.
   * Combine it with `ip=` from `IP_PNP` (already `=y`) and a short `carrier_timeout=`, so the kernel itself answers the M1's ping.
   * It binds to the first UDC, so pair it with a single-port DT.
3. **CDC-EEM with its own identity.** Use EEM first: bulk endpoints only, which avoids the interrupt-IN stall they hit and the `ncm-interrupt-ep-disabled` property our ADT also carries.
   * Before booting, confirm on the M1 that `AppleUSBEEM.kext` exists and matches 2/12/7, as it does on this M5 (section 1, "Implication").
   * Give the gadget a VID:PID different from m1n1's `1209:316d` (`third_party/m1n1/src/usb_dwc3.c:38-39`). The M1 then binds the EEM driver instead of the CDC-ACM path that panicked in attempt 15 (`native/boot/attempt15-review-2026-10-15.md:95`).
   * Pass: a new `en*` interface on the M1, then ping, then SSH.
   * Fallback, as a separate single-variable test: NCM, which is expected to show their stall.
4. **A PMGR snapshot before any Linux change.** Run Stage 1 of the PMGR probe once (`tools/m1n1-client/pmgr-probe-instructions.md:25`). Diff the handover state of the `atc*`, `smc_i2cm*` and `disp_*` domains, `afr` and `nub_spmi_a2` against their `dt/t6050-j714s-pmgr-boot-state.json`. This shows whether idea 1, and the always-on question in section 3, transfer to J716c.

Input (roadmap milestone 6):

5. **Config.** Set `APPLE_RTKIT_HELPER=y`, `HID_APPLE=y` and `HID_MAGICMOUSE=y`, and optionally `HIDRAW=y`, as in `omarchy-m5:configs/omarchy-bringup.config:68-83`. All four are off in `build/native-boot035/verified/kernel.config`. Without the helper the HID driver cannot bind (section 2).
6. **Device tree from our own ADT values, plus a read-only comparison.**
   * Add the `mtp`, `mtp_mbox`, `mtp_dart`, DockChannel and HID nodes from the values listed in section 2, with `vm-base`/`vm-size` as `apple,dma-range`, and the `keyboard` alias.
   * Beforehand, repeat their read-only register reads from the m1n1 proxy and compare with `omarchy-m5:docs/research/probe-logs/mtp-probe-j714s.log`: ASC `CPU_CONTROL`, mailbox `I2A_CONTROL`, DART `PROTECT`/TCR/TTBR, and the DockChannel counts.
   * Pass: the helper starts the MTP and the HID driver logs its interface list.
7. **Ring transport.** Our pinned `dockchannel-hid.c` has none (section 2), so expect the stock FIFO path to see no reports from M5 firmware.
   * An original implementation needs the protocol from a source we may use. Their diff has no licence and the task rules forbid copying it, and its basis, GravityLinux PR #1, is unmerged and LLM-assisted.
   * Build it on top of our bounds/rearm patch, which changes the same file.
   * Cheap first test, before writing any code: boot the stock driver and record on the panel whether the comm interface lists its interfaces and whether any key event arrives. Their patch registers the ring only when an interface starts, and skips the GPIO requests on ring hardware (`omarchy-m5:patches/linux/0005-…:604-618`). So the expected stock result is interfaces listed but no input (Hypothesis).
8. **Keyboard first, then the trackpad.** The keyboard needs no firmware (`omarchy-m5:dt/t6050-j714s.dts:31-35`).
   * For the trackpad, convert `tpmtfw-j716c.bin` the way `omarchy-m5:scripts/extract-tpmtfw.py` describes: from this machine's local Preboot restore bundle (no download), matched to the installed macOS.
   * It is a proprietary blob: extract it only with the user's approval and never commit it (`AGENTS.md`, host protection and Git conventions).

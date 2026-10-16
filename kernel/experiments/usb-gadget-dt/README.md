# USB device-mode link: Stage-B DT candidate (offline, NOT RUN)

2026-10-15, M5 side session. **A candidate only: not packaged and not booted.
boot035 / attempt 16 are untouched.** It prepares roadmap Phase 3 milestone 2,
the control channel into Linux (`roadmap.md:63`), from the review in
`research/asahi/omarchy-m5-review-2026-10-15.md`. Labels: **Confirmed / Likely /
Hypothesis / Unknown**. No code or text from the reviewed `betizzel/omarchy-m5`
repository is used; everything here is written fresh from our ADT, our pinned
m1n1 and the pinned Asahi tree.

**Relation to boot036 (main M5 session, 2026-10-15, also uncommitted).**
`native/boot/usb_dt.py`, built by job 041, uses the same delta with one DART per
port, `<dart1 1>`: this README's fallback, chosen because it is m1n1's own DMA
path and schema-clean. boot036 also builds the gadget stack into the Image and
adds an init that sets up an EEM gadget per UDC. `audit_domains.py` gives the same
result on that DT (0 `atc0-2` releasable, none deferring, 101 releasable). This
directory keeps the two-DART variant and the check and audit tools. The EEM
modules from job 040 suit the RAM-root path, which keeps the boot035 Image.

## Question

boot035's Stage-B DT has no dwc3 node, so Linux on the M5 has no USB device
controller (UDC) at all. What is the smallest change that gives Linux a UDC on
the PHY state m1n1 leaves behind, with no Type-C PHY driver?

## The candidate: one variable, the Stage-B DT

`make_dt.py` turns the boot035 Stage-B DT (sha256 `b1105bbf…`) into
`build/usb-gadget-dt/t6050-j716c-stage-b.dtb` (sha256 `d257843b1246ba49…`,
62,007 bytes) and writes `dt-delta.json`. Image, initramfs, m1n1, kernel config,
fixed arguments and the launcher stay as in boot035.

| Change | Count | Why |
|---|---|---|
| Add a `snps,dwc3` node per USB-C port: `usb@2a2280000`, `usb@2aa280000`, `usb@382280000` | 3 | The dwc3 core driver alone (no Apple glue, no PHY). Peripheral mode, high speed. Core window `0xcd00`, as Asahi's M3 DT uses (`third_party/asahi-linux/arch/arm64/boot/dts/apple/t8122.dtsi:1261-1276`). |
| Enable the port's two DARTs and drop their `power-domains` | 6 | `iommus = <dart0 0>, <dart1 1>`, as on M3 (same file, `:1270-1271`). A DART that kept `power-domains = <atcN_usb>` would defer forever once that domain is disabled. |
| `status = "disabled"` on every `atc0_*`, `atc1_*`, `atc2_*` PMGR domain | 39 | Linux must not touch the PHY power state m1n1 set up (see below). |

Properties of each dwc3 node: `compatible = "snps,dwc3"`, `reg`, the AIC
`interrupt-parent`, `interrupts`, `dr_mode = "peripheral"`,
`maximum-speed = "high-speed"`, `iommus`, and four quirks:
`snps,usb2-gadget-lpm-disable`, `snps,dis_u2_susphy_quirk`,
`snps,dis_u3_susphy_quirk` and `snps,dis_enblslpm_quirk`. These keep USB 2.0
link power management and PHY suspend off, because no PHY driver could wake the
link again. There is deliberately no `phys`, `power-domains`, `resets` or
`status`.

### Facts behind the values

| Fact | Source | Label |
|---|---|---|
| Port 1 = `usb-drd0`, `atc-phy0`, `hpm0`, **left-back**; port 2 = `usb-drd1`, `hpm1`, **left-front**; port 3 = `usb-drd2`, `hpm2`, **right** | `port-number` in `hardware/adt/adt-sanitized.json`. The physical locations come from this M5's IORegistry (`ioreg -a -l -p IODeviceTree`, read-only, 2026-10-15): the export keeps `port-location` names but not their values. | Confirmed (ports); Observed (locations) |
| Core and DART addresses: ADT `reg` translated through `/arm-io` ranges (`0x0` → `0x2_0000_0000`). `make_dt.py` cross-checks every DART against the node already in the base DT: address, `0xc000` window, interrupt (1423/1455/1487), and its domain being that port's `atcN_usb`. | ADT; base DT | Confirmed |
| dwc3 interrupt = the first `usb-drd` interrupt: 1419, 1451, 1483 | ADT `interrupts`; the same choice is made independently in the reviewed repo | Likely |
| At handoff, m1n1 leaves each port's ATC, DART and DRD domains on and the USB2 PHY running, with the PIPE mux on the dummy PHY (so USB 2.0 only) | `usb_phy_bringup()`, `third_party/m1n1/src/usb.c:145-177`, run for every port (`:315`), at our pin `57a9339` | Confirmed (source) |
| m1n1 only stops and soft-resets the device side of each dwc3 before Linux | `usb_iodev_shutdown()` (`src/main.c:203`, `src/usb.c:383`), `usb_dwc3_shutdown()` (`src/usb_dwc3.c:1269-1293`) | Confirmed (source) |
| m1n1's kboot leaves these nodes alone: ATC tunables need `atcphyN` aliases, which we don't have, and `dt_set_pmgr()` acts only on T8012 | `src/kboot_atc.c:568-580`, `src/kboot.c:2630-2660` | Confirmed (source) |
| **Why all 39 ATC domains, not just four per port:** the pwrstate probe writes AUTO_ENABLE to an active domain *before* it looks up the domain's parents. A missing parent becomes `-EPROBE_DEFER`. So a child of a disabled domain is written on every probe attempt and never registers. | `third_party/asahi-linux/drivers/pmdomain/apple/pmgr-pwrstate.c:295-298` then `:312-350`; `drivers/pmdomain/core.c:3036` | Confirmed (source) |
| With AUTO_ENABLE armed on unclaimed port domains, every DWC3 soft reset timed out (-110) on an M5 Pro | the reviewed repo (review section 1) | Hypothesis for J716c |

## Offline validation (all PASS)

| Check | Result |
|---|---|
| `fdtedit.py` round trip (`encode(parse(x)) == x`) | Byte-identical for the boot034 and boot035 Stage-B DTBs and the full boot035 DTB. Libfdt's stale padding bytes are preserved. |
| `make_dt.py` | Base digest enforced. Built twice: identical output. |
| `check()` (inside `make_dt.py`) | The node set grows by exactly the three `usb@` nodes. The six DARTs change only by losing `status` and `power-domains` and gaining `phandle`. Exactly the 39 `atc0-2` domains gain `status = "disabled"`, and nothing else changes. Phandles are unique, `iommus` resolve to the right DARTs and stream IDs, and no available node points at a disabled domain. |
| `test_usb_dt.py` | **22 tests PASS**, including 13 deliberate mistakes, each rejected for its own reason (for example: a DART keeping its domain, a re-enabled child domain, swapped stream IDs, a missing quirk, super-speed). |
| `native/boot/fdt.py` `check_stage_b()` (the launcher's Stage-B rules) | PASS |
| `dtc -I dtb -O dts` | 0 warnings, the same as boot035. The decompiled diff is **+84 / −12** lines and contains exactly the planned changes. |
| `audit_domains.py` (model of the pwrstate probe and genpd) | See the next table. |

| PMGR domains | boot034 | boot035 | candidate |
|---|---|---|---|
| pwrstate nodes / disabled / always-on | 188 / 5 / 34 | 181 / 5 / 34 | 181 / **44** / 34 |
| "unclaimed", the way the boot034/035 notes count (disabled nodes included) | **152** | **145** | 145 |
| Actually registered by Linux | 183 | 176 | 137 |
| Releasable by sync_state or the ladder (registered, not always-on, unclaimed) | 147 | **140** | **101** |
| `atc0-2` domains releasable | 39 | 39 | **0** |
| Domains that defer forever | 0 | 0 | 0 |

The model reproduces the project's earlier 152 and 145, which supports it. It also
shows a small correction: those counts include the five disabled `disp*_cpu`
nodes. The boot035 ladder can release at most **140** domains, not 145.

VM job 040 (`virtualization/jobs/040-usb-gadget-dt/run.sh`; outputs in its
gitignored `out/`) ran on 2026-10-15T17:24Z under the `vm` lock. Toolchain:
Linux 7.1.6, Python 3.14.8, DTC 1.8.1, GCC 16.1.1. Result: **PASS**.

| Check in the VM | Result |
|---|---|
| Generation on Linux | Byte-identical to the host build (`cmp`). 22 tests OK. Domain audit identical. |
| dtc | No new warnings. Decompiled diff +84 / −12. |
| `dt-validate` against the boot034 tree's `processed-schema.json` (bindings `apple,dart`, `apple,pmgr-pwrstate`, full tree) | boot035: 0 findings. Candidate: 3 findings, all `iommus: [[…], […]] is too long` from `snps,dwc3.yaml`. See below. |
| Probe audit (`kernel/experiments/t6050-dt/probe-audit.sh`) | `snps,dwc3` matches `drivers/usb/dwc3/core.c`. `apple,t6050-dart` matches through its `apple,t8110-dart` fallback. |
| EEM gadget modules for the exact Image | `libcomposite.ko`, `u_ether.ko` and `usb_f_eem.ko` built against the read-only tree. Vermagic `7.1.9-g863199d8b4a3-dirty SMP preempt mod_unload aarch64` appears verbatim in the boot035 Image. `usb_f_eem` depends on `libcomposite,u_ether`, alias `usbfunc:eem`. |

**The schema finding is deliberate.** The generic `snps,dwc3` binding allows one
`iommus` entry. Every Asahi generation describes this USB block with two DART
streams, `<dart0 0>, <dart1 1>`, under the Apple glue binding:
`third_party/asahi-linux/arch/arm64/boot/dts/apple/t8103.dtsi:1557`,
`t8112.dtsi:1822`, `t8122.dtsi:1270` and `t6030.dtsi:1383`. The IOMMU core and
apple-dart take up to three DARTs per device (`MAX_DARTS_PER_DEVICE`,
`drivers/iommu/apple-dart.c:41`, from job 040's facts). The candidate keeps the
hardware description and accepts the warning.

The fallback, if U1 shows DART faults or the schema matters more, is a single
`iommus = <dart1 1>`. That is the one stream m1n1's own gadget maps
(`usb_dart_init()`, `third_party/m1n1/src/usb.c:84-104`: DART instance 1, stream
from `mapper-usbN`), with `dart0` left disabled.

### Kernel facts from the exact tree (job 040, `out/kernel-facts.txt`)

Release `7.1.9-g863199d8b4a3-dirty`, the tree that built the boot034 = boot035 Image.

| Fact | Where |
|---|---|
| Built in: `USB_DWC3=y` (dual role), `USB_GADGET=y`, `APPLE_DART=y`. Modules: `USB_LIBCOMPOSITE`, `USB_U_ETHER`, `USB_CONFIGFS`, `USB_F_EEM`, `USB_F_NCM`. `USB_ETH` and `PHY_APPLE_ATC` not set. | `.config` |
| `snps,dwc3` is matched by the core driver (`core.c:2832`), which reads `dr_mode` (`:1763`), `maximum-speed` (`:1761`) and all four quirks (`:1790`, `:1836`, `:1838`, `:1840`) | `drivers/usb/dwc3/core.c` |
| The Apple glue matches only `apple,t8103-dwc3`, so it ignores these nodes | `drivers/usb/dwc3/dwc3-apple.c:505` |
| A failed core soft reset returns `-ETIMEDOUT` (`core.c:361`) and ends in "failed to initialize core" (`:2342`). This is the U1 failure signature. | `drivers/usb/dwc3/core.c` |
| EEM descriptors are all bulk endpoints; NCM adds interrupt endpoints (`:248`, `:293`, `:340`) | `function/f_eem.c:67-130`, `function/f_ncm.c` |
| The legacy Ethernet gadget has an EEM option (`USB_ETH_EEM`, default n). RNDIS defaults to y and is registered as the first configuration. EEM IDs are `0x1d6b:0x0102`. | `gadget/legacy/Kconfig`; `legacy/ether.c:141-142`, `:416-423` |
| A gadget driver without `udc_name` binds to the first free UDC | `gadget/udc/core.c:1623-1625` |
| `initcall_debug` prints `probe of %s returned %d after %lld usecs` at KERN_DEBUG, the U1 pass line | `drivers/base/dd.c:832` |
| DART fault IRQs are requested shared, so two DARTs can share one line | `drivers/iommu/apple-dart.c:1425` |

## What the boot035 kernel provides

The candidate needs no kernel change for the controller. In
`build/native-boot035/verified/kernel.config`, `USB_DWC3=y` (dual role) and
`USB_GADGET=y` are built in. With this DT, three UDCs should register:
`2a2280000.usb`, `2aa280000.usb` and `382280000.usb`.

The gadget *functions* are modules: `USB_LIBCOMPOSITE=m`, `USB_CONFIGFS=m`,
`USB_F_EEM=m`, `USB_F_NCM=m`. The diagnostic `/init` loads none, so in rung U1
below no function binds and the M1 sees nothing new. That is expected. The RAM
root (`omarchy-arm64/ram-root/`, job 039) already builds gadget modules for this
exact Image and sets the gadget up from userspace, so the Image can stay
byte-identical through rung U2.

## Gadget function: EEM, not NCM (recommendation)

| Evidence | Source | Label |
|---|---|---|
| NCM has an interrupt notification endpoint; EEM uses bulk endpoints only | exact tree, `f_ncm.c:248/293/340`, `f_eem.c:67-130` (job 040) | Confirmed (source) |
| `usb_f_eem.ko`, `u_ether.ko` and `libcomposite.ko` build for the exact boot035 Image, with matching vermagic | job 040 `out/eem-modules/` (sha256 in `out/eem-modules-sha256.txt`) | Confirmed (build) |
| On a T6050 M5 Pro, an NCM+ACM gadget stalled after its first interrupt-IN notification; EEM worked | review section 1 | Likely (unreproduced) |
| All three of our DRDs carry `ncm-interrupt-ep-disabled` | `hardware/adt/adt-sanitized.json` (property name; value not exported) | Confirmed (name) |
| macOS binds CDC-EEM natively: `AppleUSBEEM.kext` matches class 2/12/7 | read-only listing on this M5 (macOS 26.6.2, host path outside the repo) | Confirmed on the M5; **M1 unchecked** |

So the RAM root's gadget should use `functions/eem.usb0` (module `usb_f_eem`)
instead of `ncm.usb0`. It should also bind one gadget per UDC, or pick the UDC of
the cabled port, rather than `ls /sys/class/udc | head -n 1`. That command returns
`2a2280000.usb` (left-back), which is right only if the M1 cable is in the
left-back port. The RAM-root session was told this on 2026-10-15; the choice is theirs.

**Not recommended now: a built-in legacy Ethernet gadget** (`USB_ETH=y` with its
EEM option, RNDIS off). It would give a link with no userspace, but:

* it changes the Image;
* it binds only the first UDC;
* it then occupies that UDC, which a configfs gadget could otherwise use;
* `usb0` would still need bringing up. The launcher's fixed arguments forbid an
  appended `ip=` (`native/boot/launch.py:25-29`, `:125-129`), so that means a
  reviewed-controller change or userspace anyway.

## Native test plan (M1), one variable per rung

Run these only after attempt 16 (boot035) has given a stable baseline.

### Rung U1: this DT alone (boot035 + candidate Stage-B DT)

* **Packaging (M5).** `native/boot/make-package.py` needs an exact DT-delta rule
  for this release, as the boot035 rule does at `:74-89`. Compare
  `fdt.properties()` before and after against `dt-delta.json`: three added nodes,
  six DART edits and 39 status additions, nothing else. Every other file must
  stay byte-identical to boot035.
* **Pass, on the panel.** `initcall_debug` is already in the fixed arguments.
  * The panel prints `probe of 2a2280000.usb returned 0 after …` and the same line
    for `2aa280000.usb` and `382280000.usb`.
  * No dwc3 error appears (soft-reset timeout / -110).
  * The diagnostic init's `/proc/interrupts` dump shows dwc3 on 1419, 1451 and 1483.
  * Heartbeats and the release ladder run as in attempt 16, now with at most 101
    releases and none of them `atc0-2`.
* **Expected on the M1.** The m1n1 CDC device disappears at handoff as usual, and
  nothing new appears, because no gadget function is bound.
* **Failure meanings.**
  * `-110` / soft-reset timeout: the PHY clock or reset state is not as m1n1 left
    it. Next step: a single-port DT for the cabled port.
  * An SError or silent reset shortly after the dwc3 probes: stop, and report the
    last lines and timing, as for attempt 16.
* **Record the M1 cable's M5 port** (left-back / left-front / right) in the report.

### Rung U2: plus the RAM root with an EEM gadget (milestone 3 image)

* **M1 pre-checks, read-only:**
  `ls /System/Library/Extensions/AppleUSBEEM.kext` and
  `plutil -p /System/Library/Extensions/AppleUSBEEM.kext/Contents/Info.plist | grep bInterface`.
* **Pass:**
  * `ioreg -p IOUSB -l` shows the gadget with a VID:PID that is not m1n1's
    `1209:316d` (`third_party/m1n1/src/usb_dwc3.c:38-39`);
  * `AppleUSBEEMData` attaches;
  * a new `en*` interface appears;
  * ping, then SSH.
* **Host addressing.** The RAM root now runs one EEM gadget per UDC and gives
  the cabled interface `10.66.0.2/24` plus a DHCP server
  (`omarchy-arm64/ram-root/overlay/etc/systemd/network/20-usb.network:11-16`,
  RAM-root session, uncommitted). If macOS brings the new `en*` interface up with
  DHCP as usual (unchecked), the M1 needs no manual address. Setting one by hand is
  a host network change and needs the user's OK. IPv6 link-local needs neither,
  for example `ping6 ff02::1%enX`.

## Risks and unknowns

* The interrupt choice (first `usb-drd` interrupt) is Likely, not proven.
* USB 2.0 only. With no PHY driver, a suspended link cannot recover; the quirks
  are meant to keep it from suspending.
* The USB DARTs get no `apple,dma-range`, although the ADT lists `vm-base`
  0x10000004000 for `dart-usb*`. The pinned Asahi DTs set it only on display,
  DCP, MTP and ISP DARTs, never on a USB DART (`t8103.dtsi:610-627`,
  `t8122.dtsi:592-621`, `t6031-die0.dtsi:206-364`). Likely not needed; the MTP
  DART will need one at the input milestone.
* Disabling the 39 ATC domains leaves port power exactly as m1n1 set it,
  including DP/CIO/PCIe sub-domains. This costs some idle power on unused ports,
  which is acceptable for a link test.
* Independent of this candidate: the M1 host's CDC panic at handoff
  (`native/boot/attempt15-review-2026-10-15.md:95`).

## Files

| File | Purpose |
|---|---|
| `fdtedit.py` | Ordered FDT reader/writer (stdlib only), byte-identical round trip |
| `make_dt.py` | Builds and checks the candidate; writes `dt-delta.json` |
| `audit_domains.py` | Which PMGR domains register and which genpd could release |
| `test_usb_dt.py` | 22 unit and mutation tests |
| `dt-delta.json` | The exact delta, with input/output digests and per-port facts |
| `../../../virtualization/jobs/040-usb-gadget-dt/run.sh` | VM checks: reproduction, schema, probe audit, kernel facts, EEM modules |

```sh
python3 -I kernel/experiments/usb-gadget-dt/make_dt.py \
    build/native-boot035/verified/t6050-j716c-stage-b.dtb hardware/adt/adt-sanitized.json \
    build/usb-gadget-dt/t6050-j716c-stage-b.dtb kernel/experiments/usb-gadget-dt/dt-delta.json
python3 -I kernel/experiments/usb-gadget-dt/test_usb_dt.py -v
python3 -I kernel/experiments/usb-gadget-dt/audit_domains.py \
    build/native-boot035/verified/t6050-j716c-stage-b.dtb build/usb-gadget-dt/t6050-j716c-stage-b.dtb
```

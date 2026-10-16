# macOS 26.6.2 driver analysis for t6050 (2026-10-15) — index

Offline REA/Ghidra analysis of this Mac's own kernel collection (`kernelcache.macho` sha256 `26ddfbe9…b093`), run
from `build/macos-drivers/` (ignored; members, pseudocode, notes, extracted SPTM firmware). Nothing ran on the M5;
nothing committed. Every claim in the area READMEs is labelled Confirmed / Likely / Hypothesis / Unknown and cited to
binary + function + offset. Input devices (MTP keyboard/trackpad) were skipped on the user's instruction (another agent
covers them).

| Area (priority order) | Status | Deliverable |
|---|---|---|
| 1. CPU cluster power, idle, DVFS, SMP start (PMGR, PMP/PTD) | done | `kernel/experiments/cpu-power-smp/README.md`; m1n1 patches `0001`/`0002` + `apply_and_check.py` (PASS), `test_start_bits.py` (PASS); DT patch for the +2 p-state offset; native test plan for the M1 agent (needs approval) |
| 2. USB-C: Type-C PHY (ATC) + USB-PD (`sn201202x` over SPMI) | done (PHY lane bring-up left as evidence only) | `kernel/experiments/usb-typec/README.md` |
| 3. NVMe/ANS3 register split, SPTM mediation | done (SPTM `nvme.c` decompiled 2026-10-16: NVMMU = `reg[3]+0x28000`, controller = `reg[9]`, per-cid TCB status array at `0x28000`, `0x28100` fixed at `0x3f`) | `kernel/experiments/nvme-ans3/README.md` §4.1/§5; evidence `build/macos-drivers/evidence/sptm/` |
| 4. SMC keys (battery, charger, thermal) | done (2026-10-16): message ABI = Linux macsmc, endpoint 0x20, event layout, MBSE/MBSW/WKTP/NTAP protocol, key tables incl. the 33-entry SBS→key map, DT node | `kernel/experiments/smc/README.md`; evidence `build/macos-drivers/evidence/smc-keys-*.txt`, `AppleSMC-*.txt` |
| 5. DCP ABI/version on M5 | done (2026-10-16): firmware 26.6.2 (`mBoot-18000.161.10`), link version 195, IOMFB endpoint 0x37, 227 `A` calls + 136 `D` callbacks with names, topology; not driver-ready (struct layouts need the DCP firmware image) | `kernel/experiments/dcp/README.md`; evidence `build/macos-drivers/evidence/dcp-method-table.json`, `DCP-*.txt` |
| 6. N1 Wi-Fi/BT transport, audio | first pass done (2026-10-16): N1 = PCIe endpoint on `apcie0` port 0, protocol in DriverKit dexts; audio = AOP IOP service + AP ADMAC (`admac-evolution` behind `dart-aop`) + I2C amps, mics exclave-isolated, no AP-visible MCA | `kernel/experiments/n1-wireless/README.md`, `kernel/experiments/audio/README.md` |
| 7. G17 GPU firmware/ABI | scope done (2026-10-16): G17X + macOS 26.6.2 firmware, two firmware ASCs, Fender/KSM/GPTBAT new vs G13/G14; asahi-mirrored code knows G13/G14 and ≤ 13.5 only; not a near-term target | `kernel/experiments/gpu-g17/README.md` |

Driver-ready now: USB-PD DT delta (`apple,sn201202x`, USIDs 0xc/0xa/0x8, irqs 11/17/19 = irq/sleep/wake); NVMe patch
`0005` confirmed in its register offsets and the `0x1200/0x1208` queue-base writes, plus the SPTM-confirmed NVMMU facts
(status array at `0x28000`, `0x28100` = `0x3f`); SMC: the Linux `macsmc` transport applies unchanged (endpoint 0x20, same
message layout), DT nodes now in patch 0007 (2026-10-16, with the NVMMU status check in patch 0005); m1n1 SMP start-bit packing fix (compile-checked, needs the native
test). Not driver-ready: Type-C PHY host mode (new eUSB2 block, PHY microcontroller), cpuidle (WFI is a power-down with
reset-vector resume; needs the SMP entry path first), DCP (needs 26.x firmware struct layouts), N1 Wi-Fi/BT (protocol in
user-space dexts), audio (AOP IOP service, exclave mics), G17 GPU (new generation and firmware ABI).

Rules kept: no native boot, no commit, no push; no proprietary bytes in Git; no code taken from omarchy-m5 or
GravityLinux; macOS read-only (Preboot firmware copied, never modified).

# NVMe/ANS3 on t6050 from this Mac's macOS 26.6.2 driver: the register split, SPTM mediation and the Linux delta

2026-10-15/16, M5 REA sessions. **Offline analysis; nothing ran on the M5.** Proprietary inputs stay in the
ignored `build/macos-drivers/` (`members/IONVMeFamily.macho`, `evidence/NVMe-batch{1,2,3}*.txt`,
`evidence/notes-nvme.md`, `firmware/sptm.t6050.*`). Labels: Confirmed / Likely / Hypothesis / Unknown.
Public references (not copied): m1n1 `57a9339` `src/nvme.c`, pinned asahi-linux `drivers/nvme/host/apple.c`
with our `kernel/patches/t6050/0004`–`0005` applied.

| Binary | sha256 | Role |
|---|---|---|
| `com.apple.iokit.IONVMeFamily` (kernel-collection member) | `5eb0c57b…8a45a` | NVMe core + the embedded ANS controllers |
| SPTM firmware `sptm.t6050.release.im4p` (Preboot `restore/Firmware`, read-only copy) | im4p `27541fb8…d2cb`, LZFSE payload → Mach-O `da2ad8d4…0666` | programs the NVMMU and the controller's queue registers on M4+/M5 |

## 1. Summary

1. **The active driver on this Mac is `AppleANS3CGv2Controller`** (registry; probe score 500000 when the ADT
   has `nvme-linear-sq` and SPTM is present). "CG v2" = CoastGuard v2: every NVMMU/TCB operation and every
   queue-base register write is an **SPTM call**, not an MMIO write. The kernel keeps writing only the linear
   doorbells, the boot/mode/status registers and a few control bits (§3).
2. **Register offsets are the M1 layout.** The alternative `+0x4000` layout exists in the driver but is keyed to an
   ADT property (`nvme-secure-reg-layout`) that t6050 does not have. m1n1's offsets (`0x1200/0x1208` queue bases,
   `0x1210`, `0x1300`, `0x24908`, `0x2490c/0x24910`, `0x28100…`) are all confirmed in the kernel (§3).
3. **The `nvme-secure-bar` window (`reg[9]`, `0x25dcc0000` = `reg[3]` | bit 30) is never mapped by the active
   driver**; `start()` maps it only for the older CoastGuard type-1 (PPL) driver. It is the aperture the SPTM uses,
   which is why m1n1 (running without SPTM) drives the controller through it. Patch 0005's "nvme = reg[9], nvmmu =
   reg[3]" split stays (§5).
4. **The SPTM is the only macOS agent that touches the NVMMU, and its `nvme.c` is now decompiled (§4.1):** NVMMU
   window = `reg[3]+0x28000` (one 16 KiB page), controller window = `reg[9]` (four pages, `0x10000`), exactly the split
   patch 0005 assumes. `0x28100` ("NUM_TCBS") is written as `0x3f` even with 253-entry queues. The TCB invalidation
   status is **not** a single register at `0x28120` (Linux) or `0x29120` (m1n1): the SPTM reads a per-cid status array
   at `0x28000 + 4·(cid>>2)` (5-bit slot per cid) and requires the low 4 bits to be 0.
5. macOS runs **253-deep queues** here (ADT `nvme-queue-entries`, driver max 256); Linux keeps 64 (§5).

## 2. ADT and registry facts (Confirmed, sanitized ADT + read-only `ioreg`)

`/arm-io/ans` (`iop,ascwrap-v6`, role ANS2): `reg[0] 0x219600000+0x88000` (ASC), `reg[1] 0x219050000+0x4000`,
`reg[2] 0`, `reg[3] 0x21dcc0000+0x60010` (controller + NVMMU), `reg[4] 0x21b000000+0x18000` (AXI2AF dual),
`reg[5] 0x21db90000+0xc000` (SL common), `reg[6] 0x21dd47c00+0x4000` (CCU security INT), `reg[7] 0`, `reg[8] 0`,
`reg[9] 0x25dcc0000+0x10000` (**secure bar**). Properties: `nvme-secure-bar`, `nvme-linear-sq`, `ignore-gating`
(all empty = flags), `nvme-queue-entries = 253`, `nvme-interrupt-idx = 4` → `interrupts[4] = 0x922`.
`/defaults` has `nvme-iboot-sptm-security` and `dual-spi-nand`. `/arm-io/sart-ans`: `sart,coastguard`,
`sart-version 4`. The `reg[4..8]` names come from `start()` mapping index *n* into the field that
`Read/WriteANS2{AXI2AFDual,SLCommon,CCUSecurityINT,ECCWidgetLLT,ECCWidgetBulk}Register32` use; the matching
tunable properties are applied by context (`ApplyTunables`): `command-accelerator-tunables` → `reg[3]+0x20000+off`,
`afc-aiu-ans-dual-tunables` → `reg[4]`, `storage-lane-common-tunables` → `reg[5]`,
`ccu-security-interrupt-tunables` → `reg[6]`; records are 24 bytes `{u32 off, u32 size=4, u64 mask, u64 value}`.

Driver flags set from the ADT (`AppleANS2NVMeController::CheckEDTProperties` `0a629a80`): `nvme-iboot-sptm-security`
→ `+0x8f8`, `nvme-secure-bar` → `+0x910`, `nvme-tl-wa` → `+0x911` (absent), `nvme-secure-reg-layout` → `+0x912`
(absent), `ignore-gating` → `+0x9f8`, `nvme-queue-entries` → `+0x9c0`.

SPTM-side ADT use (`nvme_bootstrap` `0xfffffff0270c8bd8`, Confirmed): `/defaults/nvme-iboot-sptm-security` together with
`ans/nvme-secure-bar` selects the `reg[9]` controller window; `nvme-secure-reg-layout` (absent) would select
`reg[3]+0x4000` instead; `nvme-linear-sq` sets queueing-protocol version 2 and one TCB array per queue (two per queue
without it); `nvme-queue-entries` (253; 1…257 accepted, "Too many TCB entries per queue") sizes the TCB arrays and the
per-cid state; `nvme-prp-flush-wa`, `nvme-tl-wa` (+ `nvme-num-sl`, `reg[10..12]`), `nvme-vdma-wa` (`reg[13]`) and
`nvme-ans-sha-present` (`reg[14]`) are workaround/extra-window flags, all absent on t6050 (sanitized ADT has only
`nvme-iboot-sptm-security`, `nvme-interrupt-idx`, `nvme-linear-sq`, `nvme-queue-entries`, `nvme-secure-bar`);
`chosen/carveout-memory-map` region 55 is the physical range queue and PRP pages must fall in (or the XNU-managed range).

## 3. What the kernel still writes itself (Confirmed; base = `reg[3]` mapping, `WriteRegister32/64` = vtable `0x990/0x980`)

| Offset | Meaning | Function | Notes for Linux |
|---|---|---|---|
| `0x14` | CC: clear SHN on abrupt shutdown, then poll CSTS.SHST==2 ≤ 500 ms | `HandleAbruptShutdown` `0a629378` | standard |
| `0x24/0x28/0x30` | AQA/ASQ/ACQ (direct only on non-SPTM-security systems) | `IONVMeController::SetupAdminQueue` `0a64201c` | standard; via SPTM type 1 here |
| `0x1000 + (2q)·(4<<DSTRD)`, `+ (2q+1)·…` | classic SQ tail / CQ head doorbells | `IONVMeController::RingSQTailDoorbell/RingCQHeadDoorbell` | CQ head doorbell still used |
| `0x1200` (w64) / `0x1208` (w64) | **IOSQ base / IOCQ base** after the I/O queues exist | `AppleANS2NVMeController::EnableSubmissionQueue` `0a65f674`, `EnableCompletionQueue` `0a65f7c0` (asm: `mov w9,#0x1200` / `#0x1208`); SPTM types 4/3 on t6050 | m1n1/patch 0005 do this: Confirmed |
| `0x1210` | max pending commands = `n \| n<<16`, `n = GetMaxPendingCommands()` = **256** for ANS3CGv2 (64 for the base class); SPTM type 2 carries `entries-1` | `AppleANS2NVMeController::SetupIOQARegister` `0a629978`, `GetMaxPendingCommands` `0a621904` | Linux writes `64 \| 64<<16` |
| `0x1300` | boot status, wait for `0xde71ce55` (100 000 × 1 µs polls) | `WaitDeviceActive` `0a623f20` | same constant in Linux |
| `0x1304` | "modesel": 0, or 4 when the restore-environment flag is set, written before CC.EN | `PreCCEnableHook` `0a626aa0` → `SetModeselRegister` `0a6260cc` | not in Linux/m1n1; purpose Unknown |
| `0x1308` | base command ID (u16, read) | `GetBaseCommandID` `0a627174` | Linux uses 0-based tags; Unknown relevance |
| `0x13c8` | `= 1` "auto queue manage" on SPTM-security systems (others: `0x24004 \|= 0x1000`) | `AppleANS2CGv2Controller::EnableAutoQueueManage` `0a64a050` / `0a6261c8` | not in Linux/m1n1; optional candidate |
| `0x24008` bit 11 | PRP null check: cleared on non-CoastGuard systems only; **untouched on t6050** | `DisablePRPNullCheck` `0a62627c`, CGv2 override `0a64a0b0` | matches the asahi fwabi series (no `0x24008` access) |
| `0x24100+4i`, `0x24400+4i`, `0x24500+4i` | command permissions (`0x102` / `0x10002`); **not written on CoastGuard systems** (CGv2 override is empty) | `SetupCommandPermissions` `0a626330` / `0a64a048` | nothing to do |
| `0x24908` bit 0 | linear SQ enable; **skipped when `nvme-iboot-sptm-security`** (iBoot already set it) | `AppleANS3CGv2Controller::EnableLinearSQ` `0a621708` | m1n1/Linux set it themselves: fine |
| `0x2490c` / `0x24910` | linear admin / I/O SQ doorbell: write the command id after `dmb` | `AppleANS3CGv2Controller::RingSQTailDoorbell` `0a6217a0` | identical to Linux |
| `0x28000` | NVMMU block base passed to the PPL (type-1 driver) | `AppleANS2CGNVMeController::InitializePCI` `0a62ae58` | offsets inside: §4 |
| `0x2812c`, `0x28130`, `0x2813c`, `+0x4000` aliases | only with `nvme-secure-reg-layout` | — | not used on t6050 |

Power/sleep: `PowerStateAction` `0a627dbc` (off→on: `ConfigSpiGpios`, `ConfigPcieSTGLanes`; on→off: `EnableANS2Clocks`
unless `ignore-gating`, then `ApplyTunables`); sleep goes through vendor "tunnel" admin commands
(`SendSleepNotificationToANS` `0a62a29c`: type `0x309` asks "ok to sleep" (returns a byte), `0x30a` announces sleep).

## 4. SPTM-mediated operations (kext side Confirmed; SPTM side in §4.1)

Handle at `this+0xa00`; calls are `sptm_call(handle, selector, buf, len, 0, 0)` (`func_0xfffffe000b5eda8c`),
registration `func_0xfffffe000b5ed804(pmap id, provider id, desc, 0x18, &this[0x140])` with
`desc = {0x8000000100020003, u32 queue_entries, u32 x}` (`AppleANS2CGv2Controller::InitializePCI` `0a648f68`).

| Selector | Payload | Meaning | Linux (no SPTM) equivalent |
|---|---|---|---|
| `0x8022` | none | enable CoastGuard ("Successfully enabled NVMe CoastGuard") | — |
| `0x8027` type 1 | `{1, asq_entries-1, acq_entries-1, asq_phys, acq_phys}` (0x20 B) | admin queue registers | AQA/ASQ/ACQ writes |
| `0x8027` type 2 | `{2, n-1, n-1}` | max pending commands | `0x1210` |
| `0x8027` type 3 / 4 | `{3, iocq_phys}` / `{4, iosq_phys}`, CQ first | I/O queue bases | `0x1208` / `0x1200` |
| `0x8024` | `{u32 cid, u32 qid, u8 tcb[128], u64 *pages, u64 npages}` (0x98 B) | set TCB + pin pages | write the TCB entry |
| `0x8025` / `0x8026` | 0x18 B / `{cid, qid, flag}` 0xc B | retire / clear a pending request ("SL failed to idle after %llu us", 1 s) | NVMMU TCB invalidate |
| `0x8023` (type-1 PPL driver) | six page addresses (0x30 B) | TCB arrays (`entries << 7` bytes each) | TCB arrays |

TCB entry (`NVMeCoastGuardSetTCBEntry` `0a649128`, `NVMeCoastGuardSetTCB` `0a64921c`): 128 bytes; dword 0 = SQE DW0
(opcode | flags | cid) with bits 8/9 = DMA direction (`0x100` for direction 1, `0x200` for direction 2 from
`isOpCodeDir(opcode, dir, qid)`), u16 at +4 = NLB (firmware-download opcodes `0x11`/`0xd1`: pages-1 computed from the
length), dwords 14/15 = request `+0x160/+0x164`. Linux's `apple_nvmmu_tcb` is also 128 bytes with opcode/dma_flags/
command_id in the first dword — same shape (Likely same field meaning).

### 4.1 The SPTM side (`sptm.t6050.bin`, `nvme.c`; Confirmed unless labelled; evidence in `build/macos-drivers/evidence/sptm/`)

The firmware has no symbols; the functions are identified by the `nvme.c` function-name strings they pass to the
violation reporter (xrefs from `0xfffffff027008535`, `…8597`, `…8675`, `…8703`, `…878b`, `…87f4`, `…8829`, `…887b`,
`…88af`), their position in the XNU-facing table, and their register writes. Addresses are the Ghidra `FUN_` entries.

| Slot / bit | Function (string name) | Address | What it does |
|---|---|---|---|
| bootstrap | `nvme_bootstrap` | `0xfffffff0270c8bd8` | reads the ADT (§2), maps the two windows, allocates TCB arrays and per-cid PRP lists, initialises the cached register values to −1 |
| 0 | enable (no string; `allowed_functions` bit 0) | `0xfffffff0270c898c` | writes NVMMU `0x108/0x10c` = PA of TCB array 0 (admin), `0x110/0x114` = PA of TCB array 1 (I/O), `0x100` = `0x3f`; then allows slot 4 (secure-bar systems) or slots 1/2 |
| 1 | `sptm_nvme_map_pages` | `0xfffffff0270c822c` | validates and installs one TCB (below) |
| 2 | `sptm_nvme_unmap_pages` | `0xfffffff0270c7a24` | clears the TCB, writes NVMMU `0x118` = cid, checks the status array, unpins the pages |
| 3 | registration check (`validate_nvme_queue_entries` / `_protocol_version`) | `0xfffffff0270c7904` | `entries == nvme-queue-entries` else `ILLEGAL_NVMe_QUEUE_ENTRIES_MISMATCH`; `version == 2` (linear SQ; 1 otherwise) else `ILLEGAL_NVMe_QUEUEING_PROTOCOL_VERSION` — this is what the kext's registration descriptor `{…, entries, version=2}` hits |
| 4 | `sptm_nvme_bar_admin_queue_regs` | `0xfffffff0270c743c` | controller `0x24` = `(asq_n−1) \| (acq_n−1)<<16` (each ≤ `0xffe`), `0x28/0x2c` = ASQ, `0x30/0x34` = ACQ; then allows slots 1, 2, 5 |
| 5 | `sptm_nvme_bar_ioqa_reg` | `0xfffffff0270c720c` | controller `0x1210` = `a \| b<<16`, each ≤ entries; then allows slot 7 |
| 6 | `sptm_nvme_bar_iosq_reg` | `0xfffffff0270c6eec` | controller `0x1200/0x1204` = IOSQ base |
| 7 | `sptm_nvme_bar_iocq_reg` | `0xfffffff0270c6bb8` | controller `0x1208/0x120c` = IOCQ base; then allows slot 6 |
| 8 | `sptm_nvme_ans_sha_reg` | `0xfffffff0270c6760` | `reg[14]+0` = addr>>14, `+4` = config&3; only with `nvme-ans-sha-present` (absent here) |

**Windows (nvme_bootstrap).** `reg` needs ≥ 4 entries and `reg[3].size ≥ 0x2c000`; the NVMMU window is
`iommu_bootstrap_register_io_range(reg[3].addr + 0x28000, 1 page)` (state `+0x748`). The controller window (state
`+0x778`) is `reg[9].addr, 4 pages` when `nvme-secure-bar` and `nvme-iboot-sptm-security` are present and
`nvme-secure-reg-layout` is not (t6050), `reg[3].addr + 0x4000, 1 page` with `nvme-secure-reg-layout`, and not mapped at
all otherwise. ADT addresses go through the `/arm-io` `ranges` translation first (`0xfffffff0270ec77c`). The SPTM never
touches `0x24908`–`0x24910`, `0x1300`, `0x13c8`, `0x24008` or the doorbells: those stay with the kernel through `reg[3]`
(§3). Every MMIO store is a 32-bit `str` followed by `dsb sy` and a "Nonrecoverable PIO error" check.

**Call gating.** `allowed_functions` (state `+0x14`) starts as `0x109` (slots 0, 3, 8). Enable sets `0x10` on secure-bar
systems (else `0x06`); admin regs sets `0x26`; IOQA sets `0x80`; IOCQ sets `0x40` (secure-bar only). So on t6050 the
only legal order is enable → admin regs → IOQA → IOCQ → IOSQ, with TCB map/unmap allowed from the admin step on; an
out-of-order call is `ILLEGAL_CALL` (`0x3000005`). Slots 4–8 have reentrancy guards (`func_state[4..8]`) and cache their
value: a second call with a different ASQ/ACQ/IOSQ/IOCQ address is `ILLEGAL_QUEUE_ADDRESS` (`0x3000008`), a different
AQA/IOQA panics ("doesnt match the previously cached value"). Queue addresses must be 4 KiB aligned and inside carveout
region 55 or the XNU-managed physical range (globals `0xfffffff02709a058/60`).

**Dispatch.** IOMMU class table at `0xfffffff027099660` (32-byte entries by IOMMU id; the name list gives SHART=0, SART=1,
**NVMe=2**, UAT=3, …). The NVMe descriptor at `0xfffffff027019eb0` holds the name, `nvme_bootstrap`, dispatch domain 6,
the XNU-facing table `0xfffffff027018878` (9 × `{fnptr, flags=0}`, slot order as above = `allowed_functions` bit order),
instance size `0xa08` and the 16 violation names (`0x3000000`…`0x300000f` in that order). `iommu_init_driver`
(`0xfffffff0270ec5a4`) registers the table through `register_sptm_iommu_dispatch_table` (`0xfffffff0270ed5a0`); the
handler `0xfffffff0270ed6a8` takes `(domain<<32 | slot)`, requires `slot < 0x32` and a non-null entry, and the entry flags
gate callers from domains `0x16`/`0x14` (all zero for NVMe = XNU only). The kext's `0x8022`/`0x8024`–`0x8027` are XNU
`pmap_iommu_ioctl` command codes; the XNU shim that turns them into slots was not decompiled. By argument shape
(Likely): `0x8022` → slot 0, `0x8024` → slot 1, `0x8025`/`0x8026` → slot 2 (flag 0 = invalidate, flag 1 = finish a
retry), `0x8027` type 1 → slot 4, type 2 → slot 5, type 3 (IOCQ) → slot 7, type 4 (IOSQ) → slot 6, and the registration
descriptor → slot 3.

**TCB handling (`sptm_nvme_map_pages(qid, cid, tcb*, pages*, npages)`).** `qid ≤ 1`, `cid < entries`, `npages ≤ 0x101`;
the kernel's 128-byte TCB and the page list are copied in from XNU memory. The SPTM-owned entry (`TCB_array[qid] +
cid·128`, arrays at state `+0x120/+0x128`) must have halfword 0 == 0 ("TCB entry %d is not invalidated in DRAM") and
NLB (u16 at `+4`) == 0. The SPTM then: keeps only bits 8–12 of the kernel's first halfword (the DMA-direction flags →
state `+0x140[cid]`, 0x100 = write to memory), zeroes bytes `0x18–0x27` and writes PRP1 (`+0x18`) = page 0, PRP2
(`+0x20`) = page 1 (npages == 2) or the PA of its own per-cid 0x800-byte PRP list (npages > 2, pages 1… copied there);
requires NLB == npages−1 (page 0 4 KiB aligned) or npages−2 (unaligned page 0; npages == 1 → `ILLEGAL_SEG_COUNT`);
pins every page as read (1) or write (2); copies the 128 bytes, sets u16 `+2` = cid and, in linear-SQ mode, halfword 0 =
the saved DMA flags (byte 0 = opcode stays 0). cid state (`+0x19[cid]`): 0 → 1 → `qid<<4 | 3` (`CID_FILLED`; `| 2`
without linear SQ). Unmap expects `CID_FILLED`, clears halfword 0, `dmb st`, writes `0x118` = cid, `dsb`, then reads
`NVMMU + 4·(cid>>2)` and panics "ANS invalidation failed with state: %u" if `(word >> 5·(cid&3)) & 0xf != 0`
(assembly `0xfffffff0270c7b74`–`…7b94`: `and w9,w1,#3; ubfx w13,w1,#2,#0xe; ldr w12,[x12,w13,uxtw #2]; orr w9,w9,w9,lsl #2;
lsr w9,w12,w9; ands w9,w9,#0xf`), unpins, zeroes TCB and PRP list, returns the cid to 0. The `nvme-tl-wa` "SL idle" wait
(`+0x7c0..+0x7d0` windows, `CID_FILLED_RETRY` = `qid<<4 | 4`, the kext's 1 s "SL failed to idle") is compiled in but
inactive on t6050.

## 5. Linux delta (what this changes for `kernel/patches/t6050/0004`–`0005` and the draft DT)

**Applied 2026-10-16:** items 8 (per-TCB status array), 10 (32-bit lo/hi stores on M4+) and the `0x28100` comment of item 3 are
in the revised patch 0005 (`apple_nvmmu_inval`, `apple_nvme_write_base`); offline compile check: `virtualization/jobs/043-nvme-smc-patches`.

| # | Item | Label |
|---|---|---|
| 1 | Keep `nvme = reg[9]` and `nvmmu = reg[3]`: the SPTM maps the controller through `reg[9]` (4 pages) and the NVMMU through `reg[3]+0x28000` (1 page), and the kernel reaches `0x24908`–`0x24910` and the doorbells through `reg[3]`. No macOS agent maps more than `0x10000` of `reg[9]`; whether `reg[9]+0x24908` decodes is Unknown (m1n1's M4 path relies on it). Safe option: route the linear-SQ control/doorbell writes through the `reg[3]` window and keep the `reg[9]` window at `0x10000` | Confirmed (split) / Unknown (`reg[9]` size) |
| 2 | `0x1200/0x1208` I/O queue base writes after queue creation, CQ first | Confirmed |
| 3 | Queue depth: the SPTM runs 253-entry queues and still writes `0x28100` = `0x3f`, so that register does not encode the depth (Hypothesis: it is the last index of the 64 status words = 256 cids). Raising Linux's 64 needs TCB arrays of entries×128 bytes (4 KiB-rounded) per queue, status-array reads up to `0x28000+4·(entries>>2)`, and CAP.MQES ≥ entries−1 (the kext derives its depth from CAP.MQES; Likely 253) | Likely |
| 4 | Do not touch `0x24008` (PRP null check) or the command-permission table on this SoC | Confirmed |
| 5 | Optional writes macOS does and Linux does not: `0x1304` modesel (0) before CC.EN, `0x13c8 = 1` | Unknown need |
| 6 | Interrupt `0x922` (`nvme-interrupt-idx 4`); the draft DT already derives it this way | Confirmed |
| 7 | Suspend: the firmware is told about sleep with vendor tunnel commands `0x309/0x30a`; whether CC.SHN alone is enough for Linux S2idle is untested | Unknown |
| 8 | `TCB_STAT`: resolved — the SPTM uses neither `0x28120` nor `0x29120`. After the invalidate write it reads `nvmmu + 4·(tag>>2)` and requires `(val >> 5·(tag&3)) & 0xf == 0`. Linux on t6050 should do the same and drop the `0x28120` read (Unknown register on this SoC). The invalidate write at `0x28118` is Confirmed | Confirmed (SPTM check) / Likely (sufficient without SPTM) |
| 9 | TCB layout Confirmed for M5: byte 0 opcode = 0 (the SPTM clears it; matches the asahi fwabi series' `tcb->opcode = 0`), byte 1 = DMA flags (bits 0–4 passed through), u16 `+2` = command id, u16 `+4` = NLB, PRP1/PRP2 at `+0x18/+0x20` — `struct apple_nvmmu_tcb` needs no change | Confirmed |
| 10 | The SPTM writes the TCB bases, ASQ/ACQ and the I/O queue bases as 32-bit lo/hi pairs; the pinned `apple.c` uses `writeq` for ASQ/ACQ and the TCB bases. Whether the M5 windows accept 64-bit stores is Unknown; `lo_hi_writeq` everywhere is the no-risk choice (m1n1 does this) | Unknown need |
| 11 | SPTM policy facts that Linux does not need but must not violate if it ever runs under an SPTM: NLB == pages−1 with 4 KiB pages, queue memory 4 KiB aligned, ≤ 257 pages per command, strict call order enable → admin → IOQA → IOCQ → IOSQ | Confirmed |

## 6. Open questions

1. Exact decode size of the `reg[9]` aperture: ADT and SPTM say `0x10000`; m1n1's M4 path accesses up to `0x24914`
   through it. Unknown until a native read; routing those registers through `reg[3]` avoids the question.
2. Whether `0x1304`/`0x13c8` matter for the ANS firmware on Linux.
3. `0x1308` base command id: does the firmware require tags to start there?
4. Whether the firmware needs the `0x30a` sleep notification before a power-domain off (relates to the attempt-14/15 resets if ANS was involved).
5. What `0x28120` and `0x29120` read on this SoC: neither macOS nor the SPTM references them.
6. Whether the ANS firmware requires `0x28100` = `0x3f` or ignores the value (the SPTM writes `0x3f` unconditionally).

## 7. Reproduce

```
python3 -I build/macos-drivers/scripts/derive.py com.apple.iokit.IONVMeFamily      # member + symbols
# REA (Ghidra) on build/macos-drivers/members/IONVMeFamily.macho: addresses in §3/§4 (0xfffffe00 prefix)
python3 -I build/macos-drivers/scripts/vtab.py com.apple.iokit.IONVMeFamily AppleANS3CGv2Controller 480
# SPTM: Preboot restore/Firmware/sptm.t6050.release.im4p -> DER OCTET STRING -> compression_tool -decode (LZFSE)
# REA (Ghidra) on build/macos-drivers/firmware/sptm.t6050.bin: xrefs from the nvme.c name strings (§4.1), batch_decompile;
#   pseudocode + unmap assembly saved in build/macos-drivers/evidence/sptm/
```

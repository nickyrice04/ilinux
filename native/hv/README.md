# hv003: boot033/boot034 under a private m1n1 hypervisor, with a hardened chainload

2026-10-14, M5 agent. **Private iLinux tooling. Never contribute it or anything
derived from it to m1n1/Asahi.** m1n1's AGENTS.md/CLAUDE.md forbid LLM use; the
user authorized private use. **Native/hypervisor behavior: NOT RUN.**
hv003 replaces hv002 (release `native-j716c-hv002`) and hv001
(`native-j716c-hv001`); both are kept for the record. Do not run them.

## Where this stands

* hv002's hypervisor change set (patch 0001, below) **has still never executed.**
  Its session stopped at the m1n1→m1n1 chainload: no USB device returned, the
  vUART stayed empty, and the M5 stayed on the restored Apple logo
  (`hv002-session2-2026-10-14-result.md`).
* hv003 keeps patch 0001 unchanged. It changes **how the hypervisor build is
  started** and makes a failure show itself on the screen. Analysis and ranked
  hypotheses: `hv002-chainload-analysis-2026-10-14.md`.
* The leading explanation, a misaligned literal in our copy stub, is **Likely,
  not hardware-confirmed**. The other candidates (the Python ADT rebuild,
  overlapping regions, early re-initialization on t6050, the hv002 build itself)
  stay open until a rung of the ladder names one.

## What hv003 changes

| Area | hv002 | hv003 |
|---|---|---|
| Copy stub | 36 bytes of code, then the 64-bit entry literal at offset 36 (4 mod 8) | literal pool padded to 8 bytes; clang-assembled, and run through an instruction emulator that faults on an unaligned literal load |
| Moved blobs | six staged (SEPFW, SEPPatches, uStuff, preoslog, RTBuddySeg, TrustCache) | SEPFW only, as the in-tree stage-1→2 chainload |
| ADT | rebuilt in Python and pushed back (755,924 bytes) | one 16-byte property patched in place, **last**, after everything else is staged and read back; the whole ADT is read back; any failure reverts and says whether it was restored |
| `boot_args` | rebuilt | raw copy with only `top_of_kernel_data` changed, never below the live value |
| Gates | none on layout | read-only layout gate before the first write: ADT, `boot_args`, framebuffer, staging block, RAM bounds |
| Visibility | none | breadcrumb strip on the screen: host marks, a stub entry mark and bar, 16 m1n1 steps |
| Sessions | census, then the full run | ladder: `--layout-only`, `--chainload-only`, `--control stock`, then the full run |
| Proof of a new m1n1 | marker and no secondaries | also: the new instance's `boot_args` pointer is the copy the launcher staged |
| Reload | `UartTimeout` ended the session | a port that does not return by itself prints one sanitized line, then the descriptor-checked reconnect runs |
| Terminal echo | every non-protocol byte the target printed (including the device serial) reached the terminal and `--log` | `tty_enable` off on every open; only the launcher's sanitized lines |
| Errors | USB open errors carried the `/dev/cu.*` path (it embeds the serial) | class name only; the final `STOP:` line is scrubbed |

## The ladder

Each rung is human-started and RAM-only. Rungs 2–4 are **followed by a power
off**: only one chainload can happen per boot of the installed m1n1. Rung 1
writes nothing, so rung 2 may follow it in the same boot. Procedure for M1:
`tools/m1n1-client/hv-instructions.md`.

| Rung | Flags | Target writes | Question it answers | Exit |
|---|---|---|---|---|
| 1 | `--layout-only` | none (two m1n1 heap-bookkeeping requests) | Does the planned region fit the live layout? Does the raw ADT parse? | 0 `LAYOUT PASS`, 3 `LAYOUT FAIL` |
| 2 | `--chainload-only` | RAM | Does a new m1n1 start, and do all 16 steps show on the screen? | 0 `CHAINLOAD PASS` |
| 3 | `--chainload-only --control stock` | RAM | Same through boot021's own `m1n1.bin`: is the mechanism or the hv build at fault? | 0 `CHAINLOAD PASS` |
| 4 | *(none)* | RAM | Hypervisor start and the EL1 guest (boot033 or boot034). | 1 when it ends |

Any `STOP:` line exits 1 (Ctrl-C exits 130; argparse errors exit 2). Without
`--launch` the launcher only verifies packages.

## Breadcrumb strip (shared contract)

Top-left of the boot framebuffer. 21 slots, left to right; each a white 24×24
block (4 bytes per pixel), pitch 28 px, origin (8, 4). The strip is painted only
when the framebuffer geometry passes the same guards in the host, the stub and
m1n1: nonzero 4-aligned base, 30/32-bit depth, width ≥ 596, height ≥ 28, stride ≥
2384 and a multiple of 4 (m1n1 also bounds stride ≤ 0x10000 and height ≤ 0x4000).

| Slot | Painter | Meaning |
|---|---|---|
| 0 | host | layout gate passed; nothing written yet |
| 1 | host | image, SEPFW, `boot_args` copy and stub staged, read back and cache-cleaned |
| 2 | host | everything staged; about to patch the live ADT and hand off |
| 3 | stub | stub entered, before its copy loop |
| 0–4 | stub | **bar**: copy loop finished, strip cleared, one solid bar painted; the jump follows |
| 5–20 | new m1n1 | steps `c0`…`c15` (below) |

Success is the bar **plus** all of slots 5–20. boot021's own redraw can erase the
host marks (slots 0–2) before the stub runs, so after a handoff only the stub's
slot 3 and bar and the m1n1 steps are authoritative. The stock control build
paints no `c`-blocks: for it, success is the bar and the USB port returning.

| Step | Slot | Painted after |
|---|---|---|
| c0 | 5 | `_start_c` entered (raw `boot_args` pointer; before the `.bss` clear) |
| c1 | 6 | `.bss` clear, `boot_args` copy, first ADT walk (`/cpus`) |
| c2 | 7 | `uart_init`, `dockchannel_uart_init` |
| c3 | 8 | `get_device_info`, `init_cpu` |
| c4 | 9 | `dump_boot_args` |
| c5 | 10 | `exception_initialize` (end of `_start_c`) |
| c6 | 11 | `firmware_init` |
| c7 | 12 | `heapblock_init` |
| c8 | 13 | boot-policy print, `usb_enable_debugusb` when the policy asks (waits 1 s), `gxf_init`, `mcc_init` |
| c9 | 14 | `mmu_init`, framebuffer mapped Normal-NC as `fb_init` does (needs a 16K-aligned base; without one only c0–c8 paint) |
| c10 | 15 | `aic_init` |
| c11 | 16 | `smp_init` (ADT bookkeeping only; starts no CPU) |
| c12 | 17 | `wdt_disable` |
| c13 | 18 | `pmgr_init` |
| c14 | 19 | `display_init`, `display_shutdown` |
| c15 | 20 | `fb_init`, `fb_display_logo` (also stored into the console's shadow framebuffer) |

## Chainload procedure (`--chainload-mode intree`, the default)

1. Gates on the installed boot021: chip is t6050, version marker, no secondaries,
   then the register preflight (census v2 rules).
2. Read the live facts: raw `boot_args` and ADT (cross-checked against the
   controller's own parse), memory map, framebuffer, m1n1 base, the staging
   block (a `malloc` from the ProxyUtils heap, which starts at least 128 MiB
   above the heap base, so normally it never meets the destination). Raw ADT
   walk and layout gate (`adt_patch.py`, `hv_chainload.py`): `LAYOUT PASS` or
   `LAYOUT FAIL`. Nothing has been written. Every pure check (stub size, copy
   length, the 16-byte ADT patch plan) also runs before the first write.
3. Stage in the staging block: hv003 image, a copy of the SEPFW blob, the new
   `boot_args` (raw bytes, `top_of_kernel_data` only), and the stub. Read every
   piece back and clean the data cache; slot 1.
4. Slot 2 and **all** host text first. Then, under ONE guard: patch the live
   ADT's SEPFW property in place (16 bytes), read the **whole** ADT back, clean
   the cache, print one short line and call `proxy.reload()`. Any failure or
   interruption (Ctrl-C, the 300 s alarm, an interrupted print) before `reload()`
   is entered writes the original 16 bytes back and verifies the whole ADT; the
   launcher prints `live ADT patch failed and was restored and verified` or
   `live ADT SEPFW patched and NOT restored: POWER OFF completely before any
   further run` (also if the restore itself is interrupted). Once `reload()` is
   entered the handoff may have happened and nothing is restored.
5. `proxy.reload()` hands off to the stub: entry mark, copy, clean, clear and
   paint the bar, jump to `new_base + 0x800`. If the port does not come back by
   itself the launcher prints one sanitized line and runs its own
   descriptor-checked reconnect; a final failure says to power off and read the
   strip.
6. Reconnect by USB descriptor, then require the hv003 marker, no secondaries
   and `get_bootargs() == new_base + bootargs_off` (a new instance, not boot021).

`--chainload-mode python` keeps hv002's six-blob flow for comparison. It is not
the default and is not part of the ladder; it shares the gates, the stub, the
new `top_of_kernel_data` and the ADT-last order, and refuses a rebuilt ADT that
does not fit the live one before any write.

### Layout rules

* Destination: `[m1n1 base, base + image_size)`, `image_size` = image + 4 zero
  bytes (16K aligned) + SEPFW (16K aligned) + 16K for `boot_args`; the stub
  follows in the staging block. `image_size` must be a positive multiple of 16.
* Problems (stop before any write): outside RAM; overlaps the ADT or the
  framebuffer; the live `boot_args` sits exactly at the planned `boot_args`
  address (a second chainload in one power cycle); staging overlaps the ADT,
  `boot_args` or framebuffer; staging lies below `top_of_kernel_data` (inside
  live kernel data); staging overlaps the **source** of a blob that is being
  moved (the in-tree flow moves SEPFW only); the staging block cannot be
  allocated.
* Staging overlap: the destination may overlap the **start** of the staging block
  only when it starts below it, ends below the stub, and the block is at or above
  the current `top_of_kernel_data`. The copy is ascending, so it only overwrites
  bytes it has already read (a NOTE). Otherwise it is a problem.
* Notes (information only): memory-map blobs the destination overwrites; other
  memory-map blobs the staging block overlaps; the live `boot_args` lies inside
  the destination (m1n1 already copied it);
  SEPFW already points at the planned relocation address (a previous chainload
  patched this ADT: power off completely).
* New `top_of_kernel_data` = `align_up(max(current, destination end), 16K)`.
  The in-tree flow uses the destination end alone, which can lower the value
  below live iBoot structures; the new m1n1's non-freeing heap starts at that
  value and `fb_init()` takes a framebuffer-sized shadow from it.

## hv002 m1n1 change set (patch 0001, unchanged)

`0001-ilinux-hv-t6050-hv002.patch` against pinned `57a9339`: 155 lines added,
7 removed, 7 files.

| Area | Change |
|---|---|
| CPUs | `hv_init()` starts no secondaries when `chip_id == T6050`. |
| Guest timers | `VM_TMR_FIQ_ENA_EL2` is only read (logged). When a guest timer is expired, enabled and unmasked, `hv_update_fiq()` sets its `IMASK` (masking the FIQ at its source), records that in a per-CPU flag, and injects `HCR_VF`. Timer FIQs now arrive immediately instead of within 1 ms. |
| Guest view | With ECV, guest `CNTV_*`/`CNTP_*` accesses trap (`EL1TVT`, `EL1PTEN` clear). Reads of `CTL` hide the HV's mask. Any guest write to `CTL` ends it, and `CVAL`/`TVAL` re-arms restore the guest's `IMASK`. If the counter steps back, the mask is also lifted. Every handled trap re-runs `hv_update_fiq()`. |
| Gate | `hv_init()` sets `hv_ilinux_init_failed` (`hv_start` refuses) only when **ECV is missing**, because the shadow needs the traps. The census found ECV=1. |
| Handoff | `hv_start()` turns both guest timers off (`CTL` = 0) and clears the flags before entry; the census found them left expired (`ctl=7`). |
| Uncore | The FIQ handler's `UPMCR0`/`UPMSR` block runs only when `cpu_features->uncore_version` is set, as in `exception.c`. |
| Private op `0x7f0` | `kboot_prepare_hv_guest` runs `mcc_enable_cache`, `tunables_apply_static`, `clk_init`, `dapf_init_all`; no USB/PCIe init. |

## hv003 m1n1 change set (patch 0002)

`0002-ilinux-hv-t6050-hv003-crumbs.patch`, applied after 0001: additions only, in
`src/startup.c` and `src/main.c` (the code sits between
`/* ILINUX-CRUMB-BEGIN */` and `/* ILINUX-CRUMB-END */`).

* `ilinux_crumb(video, slot)` stores one white block straight into the boot
  framebuffer with 4-byte stores. It first checks the geometry (the guards
  above, no address-space wrap, 4-byte aligned rows because the MMU is off for
  c0–c8).
* Before `mmu_init` the MMU is off and the framebuffer is stored to directly. A
  state word in `.data` (so the `.bss` clear cannot touch it) records "saw the
  MMU off"; only then, once the MMU is on, the framebuffer is mapped Normal-NC
  with the same call `fb_init` uses. A boot whose first call already saw the MMU
  on never maps anything.
* `c15` is also written into the console's shadow framebuffer, because
  `fb_update()` overwrites the hardware framebuffer from that copy.
* Nothing else in m1n1 changes.

## Build

* VM job `virtualization/jobs/037-m1n1-hv003`: pinned m1n1 + patches 0001 and
  0002, `M1N1_VERSION_TAG=ilinux-57a9339-hv003`; exports `System.map` for both
  guests (boot033 Image `250d9ff5…`, boot034 Image `1131a1af…`).
* `m1n1-hv.bin` (3,932,160 bytes) SHA-256 `369b104a…42c8`; marker at 527024, `dt`
  pointer at `0x116538`, `hv_ilinux_init_failed`/`single_cpu` at
  `0x35a558`/`0x35a559`.
* Warnings: no C warnings; the one Rust notice also appears in the stock build.
* The reviewed DAPF guard verifies the image with only its image-hash pin
  swapped (table, paths and functions sit at the same offsets as boot021).
* Call order checked in the final binary: `ilinux_crumb` before `memset64` in
  `_start_c`; `c1`…`c5` in `_start_c`; `c6`…`c15` in `m1n1_main` in the
  contract's order (c1 after the ADT walk, on both paths); `ilinux_crumb_state`
  in `.data`; compiled with `-mgeneral-regs-only -mstrict-align`.

## Package

`ilinux-j716c-hv003.tar.gz`: `m1n1-hv.bin`, `m1n1-hv-symbols.txt`, two
`System.map` files (one per guest), `toolchain.txt`, `hv-manifest.json` (schema
2: both patches with SHA-256, required symbols, the guest-Image-digest → package
→ map table, offsets) and `SHA256SUMS`. Built by `make_hv_package.py`, which
refuses patches the job did not record. The launcher still reads the schema-1
manifest of hv002.

## Host launcher (`hv_launch.py`)

Live modes sit behind `--launch --device auto --confirm HV-J716C-RAM-DIAGNOSTIC`
(without them the launcher only verifies the packages offline):
`--layout-only`, `--chainload-only`, `--control stock` (with `--chainload-only`),
`--chainload-mode intree|python`, `--log` (full run only). The log path is
checked at argument time (exit 2): an existing entry (a dangling symlink
included), a missing, non-directory or unwritable parent, or a name longer than
the filesystem allows. The file is created exclusively **before the first target
write** of a full run, so a failure there stops the session while nothing has
happened to the target.

The target's console text is never shown (it carries the device serial number),
so the launcher's own lines and the screen strip are the evidence; `hv.log`
events still reach `--log`.

The full run, after the chainload:

1. `HV.init()` runs with SPRR emulation off. The launcher reads the
   `hv_ilinux_*` flags and **stops** unless single-CPU mode is on and ECV was
   found.
2. The same DT gates as the native launcher apply. Differences from native:
   `console=ttySAC0,115200` before `console=tty0` and `earlycon=s5l,0x505200000`;
   no `stdout-path`; Linux RAM starts above the HV heap.
3. RAM outside m1n1 is identity-mapped as `HV.load_raw()` does, minus the TZ
   carveouts. `CPU_START` (`0x280688000`) writes are dropped.
4. Upstream `map_essential()` keeps the HV link's PMGR domains on (UART0,
   UART_P, SIO, FAB8_SOC, FAB0_PIOGW, ATC0_USB, ATC0_COMMON, FAB3_SOC,
   ATC0_USB_AON); guest writes to them are held on and logged.
5. `hv_start(kernel, x0=DT)`.

Guests: boot033 or boot034, selected by the Image digest in the manifest (the
repository's retained per-package manifest is used for the guest's own checks;
`native/boot/launch.py` and its reviewed digest are unchanged). Never benchmark
under the HV.

## Validation (offline, on the M5)

All with `python3 -I`:

| Suite | Tests |
|---|---|
| `test_hv_chainload.py` | 204 |
| `test_hv_launch.py` | 93 |
| `test_adt_patch.py` | 10 |
| `test_crumb.py` | 15 |
| `native/boot/test_launcher.py` | 37 |
| `unittest discover -s native/hv` | 322 |
| `kernel/experiments/genpd-sync-state/test_genpd.py` | 5 |

* **Stub:** the 48-word painting stub (192 bytes of code, 32-byte aligned pool,
  224 bytes of 0x100) and the 12-word plain stub are re-assembled with clang and
  compared byte for byte, and run through an instruction emulator that faults on
  an unaligned literal load. Tests assert: the slot-3 mark's 576 stores and one
  `dsb sy` precede the first copied byte; a fault in the copy loop leaves slot 3
  lit and no bar; clang-built mutants (mark after the loop, no mark) are
  caught.
* **Launcher:** every gate fails with zero target writes (loop over every
  `boot_args` and video field); the real `chainload_intree` and
  `chainload_python` run through `run_live` against a recording target; the
  ADT window (restored, not restored, global alarm, Ctrl-C), reload failure,
  new-instance proof, stock control digest, manifest schema 1 and 2 round trip
  through `make_hv_package.py`, sanitized errors and the `STOP:` scrub.
* **Mutation sweeps** (fix agent, scratch only): four sets of textual mutants of
  the launcher and chainload modules (71 from round 1, 42 for the review fixes, 22
  for the restructured ADT window, 11 re-crafted), run against both test files;
  0 survivors in the final state. Round 1's two survivors got tests.
* **Review fixes** (independent read-only review, then a second pass): Ctrl-C and
  every other `BaseException` end as one scrubbed line (exit 130 or 1), never a
  traceback; the `--log` path checks; the single guarded ADT-to-reload region;
  staging gates independent of the destination; toolchain record check for
  schema 2; operator text that says the new m1n1 will not paint when its own
  guards refuse (stride > 0x10000, height > 0x4000, or a framebuffer base that
  is not 16K aligned, in which case only c0–c8 paint); `census.py` now ends the
  same way.
* **m1n1 side:** `test_crumb.py` extracts the patch's crumb block, compiles it
  with ASan/UBSan and drives it with simulated framebuffers and MMU states, with
  mutations; the final-binary call order and `.data` placement were read from
  the linked image.
* **Not run on the M5 (need the M1 client venv):** `test_dapf_guard_adt.py`,
  `test_launcher_adt.py`, `test_protocol.py`, `test_usb_check.py`,
  `test_framebuffer_fixup.py`. `native/boot` is unchanged.

## Not verified / risks

* **Everything above is offline.** No rung has run.
* The misaligned-literal explanation is Likely, not confirmed. If rung 3 (stock
  boot021 through the same code) also fails, the fault is in the mechanism or in
  early re-init on t6050, not in the hv003 build.
* The first parse of a real t6050 ADT by `adt_patch.py` happens in rung 1. It is
  strict: an unexpected layout stops the launcher before any write.
* The in-tree flow overwrites five memory-map blobs that the Python flow moved
  (SEPPatches, uStuff, preoslog, RTBuddySeg, TrustCache). The layout table lists
  them as NOTES; whether any is live on t6050 is Unknown.
* The stub's framebuffer stores run with the MMU off (Device memory, 4-byte
  aligned); that is expected from the architecture, not observed.
* A staging block that overlapped the original SEPFW source would not be caught
  by the gate; the proxy heap starts at least 128 MiB above `top_of_kernel_data`,
  so this is theoretical.
* **ECV trap behavior** (hv002): if Apple's ECV does not trap EL1 timer accesses
  as specified, the guest would read the HV's `IMASK` after its first timer
  expiry and loop in its FIQ handler. The HV stays responsive: Ctrl-C, `bt`,
  power off and report.
* **Untested on t6050 (upstream code):** vUART interrupt delivery through AIC3;
  USB re-enumeration after the chainload; `hv_init`'s
  `pcie_shutdown`/`usb_hpm_restore_irqs`; guest PMU/IPI register emulation.
* An asynchronous SError hangs m1n1; recovery is a power off.
* EL1 under the HV is not native EL2: different timer path, injected FIQs, 1 kHz
  tick. VHE-specific or timing-sensitive faults may not reproduce.

## Files

| File | SHA-256 |
|---|---|
| `0001-ilinux-hv-t6050-hv002.patch` | `ecde6b2b9342c91d55b0254217bd940adde234837d23927dee381eea3ad9b11e` |
| `0002-ilinux-hv-t6050-hv003-crumbs.patch` | `457480e01e85f68499314d6797701c7f9dfb7c36e628b9a00fb4c3f4feb1c590` |
| `hv-manifest.json` | `1192ff97148fe91023f5c62af3226b1d9be8aa88afd35d0513a5b8d7275216d0` |
| `hv_launch.py` | `e4894a16c4243b797b960b4cd704032cf9ccc96f181db107468641df553f517d` |
| `hv_chainload.py` | `03e0977155cd68677f6f7e1c0976748b0bc59824088881b2ff1c0c14631a87f0` |
| `adt_patch.py` | `baa020fa6344912c45af6905283a8851635cdd2e82574d29c8d372b6fab76f6b` |
| `make_hv_package.py` | `68eb15e9578f597dd3dddb58b2b880914813bf386a32941473f9231dcf3332dd` |
| `hv_regs.py` | `3545bfcaa17b8187be65a2051c36afadcdc384906174f425884a4f8330bc1456` |
| `census.py` | `22829e037da9e0f615d76914c62c052e3e3de6705af986f670e7587c9f598620` |
| `vuart_log.py` | `08d4d6510f960a0b1d653ec80160ffa6ced359a7cea056b4f3c7d635cc4c9d6a` |
| `test_hv_launch.py` | `99cbbe94b077f099f462af0e29f87fcb09d93f90ee7be91fa14478a9ed483f17` |
| `test_hv_chainload.py` | `47f0df89b80faf0a19f956beb8501cfd689ca917f82d83c5b928818dcff0bd1d` |
| `test_adt_patch.py` | `496fcdcb2c2101881da74701c8fecf8268d9d616ef3d86e16b5f9a55feed984d` |
| `test_crumb.py` | `eae628969ed9406e024c6bb1b8cf5cbd98c4397ac86d991cdf2bfe104c6652fb` |
| `test_crumb_model.c` | `2e574e60194a67ac4dd89b4768ed85b20dcf16988f1a284f95e25bc66f4de599` |
| `test_timer_model.c` | `ad3bad419aef1ef2929ffadd74ef7f55390122ffcbb141f0cbd0356f2d5e4f3d` |
| `tools/m1n1-client/hv-instructions.md` | `f7d0d63281d064732a7f5d7496b9889a477f0638d36d2c3cc2d8d5f92814e0ef` |
| Release `native-j716c-hv003`, `ilinux-j716c-hv003.tar.gz` | `392433747cb23dbd44df92b7b24279fb559f243ece30ba6e29efc0b842722c05` |

M1 procedure: `tools/m1n1-client/hv-instructions.md`.

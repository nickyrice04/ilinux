# boot041: boot040 with both DART instances per dwc3 core in the Stage-B DT, prepared offline

2026-10-18 (UTC 2026-10-19), M5 side session. **Native boot041 NOT RUN. Not committed, not
released.** It builds on `boot040-dart-fault-2026-10-18.md` and the attempt-23 result
(`stage-b-2026-10-18-attempt23-result.md`). Labels: Confirmed / Likely / Hypothesis / Unknown;
"Confirmed" means by source, VM or package check, never on the M5's hardware.

## Summary

* **Attempt 23** showed the USB DART is version 2.4 (boot040's part 2 was active), instance 1's
  handler found nothing pending through the whole interrupt storm, and at the first bus error
  **instance 0**, which the boot036-040 Stage-B DT leaves out, held the fault (`pend 1`, a stream-0
  block at `0x3ffff35800`). Linux had never reset or programmed instance 0 and had no handler for it
  on the shared fault interrupt. That is fix candidate A of `kernel/experiments/usb-gadget/dart-diag/README.md`.
* **boot041 is boot040 with one change, in the Stage-B DT:** each of the three dwc3 cores gets both
  DART instances of its port, `iommus = <dart0 0>, <dart1 1>`, the way every Asahi device tree wires
  this block. Instance 0 is enabled exactly as boot036 enabled instance 1: `status` and
  `power-domains` removed (its domain is the port's disabled `atcN_usb`), a new phandle. Nothing else
  in the DT changes.
* **The Image is boot040's, byte for byte** (`a53d1d47…`): job 041's reproducible build gave it
  again, and the packager refuses any other. So the attempt-24 Omarchy root pinned to that Image stays
  valid: the committed launcher's `omarchy` profile accepts boot041's package with it (offline).
* **`/init` keeps boot040's diagnostics** and adds what item 3 of the task asked for: an identity line
  naming both instances (and how many fault handlers share the line), a line at bind saying whether
  the kernel set up both instances (`: both set up`), and both instances' pending-fault words in the
  short per-port line (`pend <instance 0>/<instance 1>`). These lines can only live in `/init`, so
  the initramfs and `diag-init.c` change too. The packager enforces that the DT is the only change
  outside `/init`: the DT must be boot040's plus the exact two-DART delta, the initramfs boot040's apart
  from `/init`, `diag-init.c` pinned by digest, and every other file byte-identical to boot040.
  boot040's `/init` cannot just be kept: on the new DT the kernel's `<dwc3>/iommu` link names instance 0
  (`apple_dart_probe_device` returns the first `iommus` entry's DART), so boot040's `/init` would
  mislabel it and skip the register snapshot.
* **Package** `ilinux-j716c-boot041.tar.gz`: 18,926,067 bytes, SHA-256
  `ab49e307239a600f0652ea180ee15aa2b153ddf3c28e910bf8b5f97317944d28`; SHA256SUMS digest
  `593c449265c2cbd930f0c57db95939af59f37191c0d8934b4ff1146e34f280a1`. Records in
  `build/native-boot041/records/` (`native/boot/package-manifest.json`, `archive-sha256.txt` and
  `intake-manifest-sha256.txt` are untouched: still attempt 23's).
* **Checks:** job 041 PASS (kernel facts incl. the boot041 ones, the status fixture 53 checks plain and
  under ASan+UBSan, the DT with exactly its three expected schema findings, the Image equal to
  boot040's); `selftest/run-vz.sh both` PASS (liveness; dummy_hcd self-test 27 present + 16 absent);
  `test_boot041_package.py` 11 PASS; the committed launcher `b14ec7a1…` offline: `Package PASS`.

## What boot041 changes

| File | boot040 | **boot041** | Enforced by |
|---|---|---|---|
| `t6050-j716c-stage-b.dtb` | `a676087b…`, 62,043 bytes (= boot036-039) | **`b053f248…`, 61,995 bytes**: boot040's plus the two-DART delta below | `make-package.py` boot041: `usb_dt.check_both_darts_delta` against boot040's DT (`--previous-package`) |
| `initramfs-stage-b.cpio.gz` | `59bc2afc…`, 2,402,470 | **`27314880…`, 2,403,156**: boot040's apart from `/init` (857,112 → 857,152 bytes) | `check_init_only_delta` against boot040's; `check_bulk_only_init`, `check_dart_diag_init`, `check_dart_both_init` on the packed `/init` |
| `diag-init.c` | `58c68268…`, 45,907 | **`2e2e9923…`, 56,086** | `INIT_SOURCE` pin |
| `Image` | `a53d1d47…`, 44,681,728 | **byte-identical** | baseline comparison (`boot040-package-manifest.json`), `IMAGE_SOURCE`; job 041 asserts its rebuild equals it |
| `kernel.config`, `t6050-j716c.dtb`, `initramfs.cpio.gz`, m1n1 (4), `toolchain.txt` | | **byte-identical** | baseline comparison |

### The DT change (`native/boot/usb_dt.py`, `make_stage_b_dt.py --both-darts`)

| Node | boot040 | boot041 |
|---|---|---|
| `/soc/iommu@2a2f00000`, `@2aaf00000`, `@382f00000` (instance 0, ADT `dart-usbN` `reg[0]`) | `status = "disabled"`, `power-domains = <atcN_usb>` | both removed; `phandle = <0x6b>`, `<0x6c>`, `<0x6d>` (dtc's next free ones) |
| `/soc/usb@2a2280000`, `@2aa280000`, `@382280000` | `iommus = <0x68 1>` (instance 1, stream 1) | `iommus = <0x6b 0 0x68 1>` (instance 0 stream 0, instance 1 stream 1); likewise `0x6c`/`0x69`, `0x6d`/`0x6a` |

The decompiled diff is **+6 / −9 lines**, exactly those. Both instances of a port keep their
compatible, `0xc000` windows `0x80000` apart and the one shared fault interrupt (`0x58f`, `0x5af`,
`0x5cf`); `check_both_darts_delta` requires all of it, refuses 19 deliberate deviations
(`test_usb_dt.py`) and the packager six more on real DT bytes (`test_boot041_package.py`). The DT is
built from boot040's (= boot036's) decompiled DT, so instance 1 keeps its phandle; built on the Mac
(dtc 1.8.1-gf3451d12) and in the VM (dtc 1.8.1) it is the same file, and the launcher's
`check_stage_b` passes.

**What the kernel does with it (Confirmed, source of the exact tree; `check_kernel_facts.py`):**
apple-dart probes instance 0 like instance 1 (prints `t8110-class DART v…`, resets it unless locked,
which attempt 23's `prot 0` says it is not, and registers a second `apple-dart fault handler` on the
shared line); `apple_dart_of_xlate` keeps one stream map per instance, in `iommus` order (refusing
instances whose page size or VA width differ: attempt 23 read identical PARAMS on both);
`apple_dart_attach_dev_paging` sets the core's DMA domain up on every stream map (all streams enabled,
TTBR with the valid bit, TCR translate), with one page table, and every TLB flush goes to both
instances; `<dwc3>/iommu` now links to instance 0.

### The `/init` change (`kernel/experiments/usb-gadget/init.c`)

| Line | When | Source |
|---|---|---|
| `[usb1] 2a2280000.usb irq 58b(<a>) dart0 2a2f00000 sid 0 + dart1 2a2f80000 sid 1 fault irq 58f(<n>) x2` | at bind | the core's `of_node/iommus`; each phandle found among `/sys/bus/platform/devices/*.iommu/of_node/phandle` (`reg` gives the base, `interrupts` the line, the `driver` link whether apple-dart is bound); `x2` = how many `apple-dart fault handler` actions `/sys/kernel/irq/<n>/actions` lists. The bases count as confirmed only if the kernel's iommu link names the DT's first DART and every DT DART is instance 0 or 1 of the port's ADT pair on the same line; only then is anything read. On a boot036-040 DT the line is boot040's (`dart1 … sid 1 …; dart0 … not in DT`) |
| `[ctl] port 1: reading DART registers …` and the four to six `[usb1] dartN …` register lines | at bind, and at the first bus error | unchanged from boot040 (`/dev/mem`, 32-bit loads, never a write) |
| `[usb1] dart0 sid 0 bound tcr 9 ttbr <t> + dart1 sid 1 bound tcr 9 ttbr <t>: both set up` | at bind, after the snapshot | the snapshot's values: per DT instance its stream enabled, TCR translate without bypass, TTBR valid, apple-dart bound; both on one table. Otherwise `: dart0 NOT set up`, `: both translating, NOT one table`, `: not checked` |
| `[usb1] configured On f<n> irq<n> dart<n> pend <a>/<b> <B>B q<n> 1o h<n> d<n> 1i h<n> d<n> [BUSERR@<hex>]` | each heartbeat | `pend` = the per-stream pending bitmap (0x4000) of instance 0 / instance 1 on a version ≥ 2.2 DART, ERROR_STREAMS (0x1c0) below; read by the status child (two loads per instance); `pend ?` if the read fails; absent if the bases are not confirmed |

Widths: every realistic short line is ≤ 100 columns except a bus error with a long address and the
pending words (107 in the fixture), and the wedge case (111). The fixture now also gets a fake
`/dev/mem` (a sparse file in its own root) so `dart_peek`'s and `dart_pending`'s offsets and version
gates run on known register values; boot040's fixture could not exercise the reads at all.

## What it would test on the M5, and the risks

* **The question:** with instance 0 reset, programmed and handled by Linux, does port 1's bulk-IN path
  keep flowing past the first second (no `BUSERR`, no storm, the reader receiving the whole log for ten
  minutes)? If yes, attempt 21's and 23's stall was the unprogrammed sibling instance (candidate A
  confirmed), and the attempt-24 Omarchy root can then use boot041's package unchanged.
* **New on hardware (Likely safe, not tested):** Linux now writes instance 0: the reset at probe (TCR 0
  and TTBR 0 on all 16 streams, all streams enabled, ERROR and the v2.2 pending words and protection
  status cleared, both masks 0, a TLB invalidate), the TTBR and TCR of stream 0 when the dwc3 attaches,
  and a TLB flush on every map and unmap. Instance 0 shares instance 1's clock gate and power, answered
  `/dev/mem` reads twice in attempt 23 and reported `prot 0` (unlocked). If the M5 stops right around
  the DART probe lines (≈ 2-3 s, before the first UDC binds), instance 0's reset is the suspect.
* **Which stream instance 0 carries is the one open wiring question.** Asahi gives instance 0 stream 0,
  and attempt 23's pending bit on instance 0 was stream 0's. The REA (`rea-dart-2026-10-18.md`, A7/A8)
  found macOS programming stream 1 on both instances and remapping stream 0 to 1; instance 0's
  stream-1 block also read `0x3ffff35800` at the bus error (its pending bit was clear). If boot041 then
  shows a fault on instance 0's stream 1 (or instance 1's stream 0), the next DT gives both instances
  both streams, `<dart0 0>, <dart0 1>, <dart1 0>, <dart1 1>`, which the REA calls an exact mirror of
  macOS. boot041 keeps Asahi's wiring, as the task asked.
* The generic `snps,dwc3` schema allows one `iommus` entry: three deliberate findings, as job 040 found
  for the same wiring (Asahi describes the block with its Apple glue binding).
* Unchanged on purpose: no `apple,dma-range` (candidate C), no TLB-policy or remap change, the gadget,
  the reader, the fixed arguments.

## Results

| Check | Result |
|---|---|
| VM job 041 (`WAIT=1 host-run.sh boot041`, 2026-10-19 03:05:59-03:07:25Z; an earlier run at 03:05:12-03:05:20Z stopped at the new kernel-facts check, which looked for `of_device_make_bus_id` in `drivers/of/platform.c` while this tree defines it in `drivers/of/device.c`; `vm` lock taken and released each time) | **PASS.** apple-dart patches digest-gated as for boot040; `test_dart_diag.py` PASS; **Image `a53d1d47…` = boot040's, test Image = boot040's**; config delta PASS; boot036 DT rebuilt `a676087b…` (= boot040's), then boot041's `b053f248…`; `dt-validate`: exactly the three `usb@… (snps,dwc3): iommus: [[107, 0], [104, 1]] is too long` findings, `apple,dart` clean; `init.c` and the fixture build with `-Wall -Wextra` and no warning; initramfs contract PASS; same nine signed packages as boot040 |
| Kernel facts (`check_kernel_facts.py`, the exact tree) | **PASS**, now also the boot041 facts: one stream map per DART in `iommus` order, the iommu link to the first, a paging domain set up on every one and every TLB flush on every one, TCR/TTBR bits, the driver name `apple-dart`, comma-separated `actions`, `phandle`/`reg`/`interrupts` as `of_node` files (`drivers/of/fdt.c`, `kobj.c`), the `of_node` and `driver` links (`drivers/base/core.c`, `dd.c`), DT platform devices named `<address>.<node>` (`drivers/of/device.c`), `dart_pending` reads only |
| Status fixture (`status_fixture.c`, 53 checks; boot040 had 31) | **PASS** plain `-O2` and under ASan+UBSan (also on the Mac with clang during development): boot040's cases on a boot036-040 DT (identity line unchanged, `pend ?` without `/dev/mem`); the two-DART identity line and dartinfo; the snapshot read from the fake `/dev/mem` (v2.4); `: both set up`; `pend 0/0`, `pend 1/0` with attempt 23's fault on instance 0 and a bus error, `pend 0/2` on a version 2.1 pair (ERROR_STREAMS); the verdicts `dart0 NOT set up` (instance 0 as attempt 23 found it, or without its driver) and `NOT one table`; a DT naming another port's DART (nothing confirmed, nothing read, no `pend`); the VM-style ports unchanged |
| Generic VM, shipped Image + initramfs, 95 s | **PASS**: PID 1, one CPU, debugfs, the boot041 banner, `no UDC`, dropbear, heartbeats 000-016, the 60 s milestone; no `[usb` line, no DART read |
| Generic VM, test Image + overlay, 120 s (dummy_hcd) | **PASS**: 27 expected patterns, 16 rejected ones absent (two new: no setup line, no `pend` for the unknown UDC); gadget `1d6b:0104 bcdDevice 0139`, one vendor interface, two bulk endpoints; **1,928 log lines over bulk IN**, no echo; `[usb4] dummy_udc.0 irq 0(-1) no iommu link in sysfs`, `[usb4] dart regs not read …`; SSH with the key `uid=0`, refused without |
| Packager (`test_boot041_package.py`, 11) | **PASS**: rebuilds byte-identically, also after `init.c` moves on; exactly the DT, the Stage-B initramfs and `diag-init.c` differ from boot040; refuses boot039's Image and a one-byte-flipped Image (`unexpected payload change: Image`), boot040's DT and six DT deviations, boot040's or a changed `diag-init.c`, boot040's initramfs (`/init lacks the boot041 two-DART lines`), an initramfs changed beyond `/init`, changed `toolchain.txt`, `m1n1.bin`, `kernel.config`, `t6050-j716c.dtb`, `initramfs.cpio.gz`, boot039 as the baseline, missing flags, another key |
| `test_usb_dt.py` (12, 6 new), `test_control_channel.py` (16, 3 new incl. the real boot041 package), `test_boot040_package.py` (10: boot040 still rebuilds byte-identically), `test_boot039_package.py` (8), `test_kconfig_guard.py` (7), `test_mtp_input.py` (33), `test_ramroot.py` (45), controller suites `test_launcher` (37), `test_gpio_guard` (10), `test_entry_guard` (6), `test_dapf_guard` (16), `test_framebuffer` (5), `test_hardware` (19) | PASS. Not run here: the three controller suites that need the M1's client venv (`test_dapf_guard_adt`, `test_launcher_adt`, `test_protocol`); the launcher and its modules are unchanged |
| Committed launcher `b14ec7a1…0740` from a scratch copy (HEAD's modules) with boot041's records | `Package PASS: all files match the repository manifest. Mode: OFFLINE ONLY; USB not opened`, the fixed arguments unchanged. With `--profile omarchy` and the attempt-24 root pinned in the working tree's `omarchy-root-manifest.json` (`b8eae454…`, not committed, another session's): `RAM root PASS: 2,434,354,327 bytes match`, upload estimate 2,479,098,050 bytes (495.8 s at 5 MB/s, deadline 900 s) |

Evidence (ignored): `virtualization/jobs/041-usb-gadget/out/runs/boot041-2026-10-18/` (run logs incl.
the stopped one, digests, kernel facts and the sources they read, fixture output, DT checks, both
console logs). Job 041's `out/export` and `out/build` now hold boot041's files; boot040's export and
test artifacts were copied to `out/runs/boot040-2026-10-18/` first (`export/`, `build-snapshot/`). The
test Image and the job-041 kernel tree that jobs 045 and 046 read are byte-identical to boot040's.

## NOT RUN / Unknown

* **NOT RUN:** native boot041, its release, its handoff and the M1's readiness for it. Nothing committed
  or pushed.
* **Unknown:** whether programming instance 0 stops the stall; which stream instance 0 carries in device
  mode (stream 0 by attempt 23's pending bit and Asahi; stream 1 by macOS's programming); whether
  instance 0's reset and writes are safe on this chip (Likely); what raised attempt 23's storm on
  instance 1's handler beyond instance 0's pending fault (the two GAPF units share the line: Unknown).

## Reproduce

```sh
WAIT=1 virtualization/jobs/041-usb-gadget/host-run.sh boot041                 # the vm lock, ~90 s
kernel/experiments/usb-gadget/selftest/run-vz.sh both                         # Mac, ~4 min
python3 -I native/boot/make-package.py --out virtualization/jobs/041-usb-gadget/out \
    --destination build/native-boot041 --name ilinux-j716c-boot041 \
    --previous-package build/native-boot040/verified \
    --authorized-key kernel/experiments/usb-gadget/authorized_keys \
    --record-dir build/native-boot041/records
python3 -I native/boot/test_boot041_package.py
```

## Files

* New: `native/boot/test_boot041_package.py`, `native/boot/boot040-package-manifest.json` (the boot040
  manifest as the boot041 baseline, equal to `native/boot/package-manifest.json`, `71cecb07…`), this
  report, `tools/m1n1-client/stage-b-boot041-draft.md` (draft checklist; the attempt number is left to
  the handoff).
* Changed: `native/boot/usb_dt.py` (`both_darts_amendment`, `check_both_darts_delta`),
  `native/boot/test_usb_dt.py`, `native/boot/make-package.py` (boot041 entry), `native/boot/control_channel.py`
  (`check_dart_both_init`), `native/boot/test_control_channel.py`; `kernel/experiments/usb-gadget/init.c`,
  `make_stage_b_dt.py` (`--both-darts`), `selftest/status_fixture.c`, `selftest/check_kernel_facts.py`,
  `selftest/run-vz.sh`, `README.md`, `dart-diag/README.md`; `virtualization/jobs/041-usb-gadget/run.sh`.
* Untouched: `native/boot/launch.py`, `omarchy-root-manifest.json`, `test_ramroot.py`,
  `package-manifest.json`, `archive-sha256.txt`, `intake-manifest-sha256.txt`,
  `tools/m1n1-client/stage-b-instructions.md`, the apple-dart patches, job 045, job 039 and the link
  files other sessions are changing.

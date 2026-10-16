# t6050 (M5 Max) kernel patches: local drafts

**Status: driver objects and all DTBs compiled in job 018; DT schema
validation clean in job 044 (2026-10-16); never booted.**
Full kernel linking of this revision remains pending. These are local
research drafts. They were written by an AI agent, so under Asahi Linux's
generative-AI policy they **must not be submitted** to Asahi, to mainline or to
any mailing list (decision D-007). For that reason they carry no
`Signed-off-by` (DCO) line.

* **Base:** `AsahiLinux/linux` branch `asahi` at
  `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` (2026-08-20). The first patch
  carries a `base-commit:` trailer.
* **How they were made:** commits on a local branch `t6050-local` in the
  sparse clone `third_party/asahi-linux`, exported with
  `git format-patch --base=77cb8f24`. The 2026-10-16 revision of 0005 and
  0007 lives on branch `t6050-local-v2` (worktree `ilinux-publish/build/
  asahi-wt-t6050-v2`, ignored). The current export comes from branch
  `t6050-local-v3` in the same clone (`git format-patch --base=77cb8f24 -7
  t6050-local-v3`, run from that worktree, which keeps `t6050-local-v2`
  checked out): v2 plus the schema fix of 0006 found by job 044. v3 was
  built from v2 offline with git plumbing because the clone is `blob:none`
  and sparse (`git write-tree --missing-ok` under `GIT_NO_LAZY_FETCH=1`,
  `git commit-tree`, then a new branch; `mfd/apple,smc.yaml` is outside the
  sparse cone). 0001–0005 are byte-identical to the v2 export; 0006 adds the
  `mfd/apple,smc.yaml` hunk and updates its message; 0007 changes only its
  message.
* **Apply:** in a full checkout of that commit, run
  `git am kernel/patches/t6050/*.patch`.

## Series

| # | Patch | What | Provenance / evidence | Confidence |
|---|---|---|---|---|
| 0001 | `dt-bindings: iommu: apple,sart: Add t6050 (SARTv4) compatible` | `apple,t6050-sart`, standalone (no SARTv3 fallback) | ADT `sart-ans`: `sart,coastguard`, `sart-version = 4`. m1n1 `src/sart.c` @ `9bfdf8aeca30` (MIT at tag v1.9.9) | Likely |
| 0002 | `soc: apple: sart: Shift paddr and size by their own shift` | Latent bug fix: `sart_set_entry()` used `size_shift` for paddr and vice versa. No effect today because both shifts are 12 | Code reading | Confirmed (bug); no functional effect |
| 0003 | `soc: apple: sart: Add SARTv4 support for t6050` | `sart_ops_v4`: CONFIG at 0x00, PADDR at 0x60, SIZE at 0xc0, shift 12, 30-bit size, allow flags 0xff | m1n1 `9bfdf8aeca30` (PR #661: "makes nvme_init()/nvme_read() work on T6050") | Likely |
| 0004 | `dt-bindings: nvme: apple,nvme-ans: Add M4+ (t8132) and t6050 compatibles` | Optional third reg `nvmmu`, required for `apple,t8132-nvme-ans2`. t6050 falls back to t8132 and has 3 power domains | m1n1 `53f8ee9b54ba` (PR #652). ADT `ans`: `nvme-secure-bar`, 10 reg entries, `nvme-interrupt-idx = 4` | Likely |
| 0005 | `nvme-apple: Support the M4+ NVMMU/NVMe register split` | `mmio_nvmmu` window for all `APPLE_NVMMU_*` registers. Mirrors the I/O CQ/SQ base to nvme+0x1208/0x1200 after IOSQ creation. **2026-10-16:** on M4+ the TCB invalidation status is read from the per-TCB state array at NVMMU+0x28000 (word per 4 TCBs, 5-bit slot, low 4 bits), the 64-bit base registers are written as lo/hi 32-bit pairs, `NUM_TCBS` stays 63 | m1n1 `53f8ee9b54ba` (MIT at v1.9.9); SPTM facts from `../../experiments/nvme-ans3/README.md` §4.1 (REA of this Mac's SPTM) | Likely; status array Confirmed (SPTM) |
| 0006 | `dt-bindings: apple: Document t6050 (M5 Max) compatibles used by the draft DT` | Board, CPU (`apple,sotra-m/-p` placeholders), PMGR, pwrstate, AIC3, pinctrl, I2C, WDT, DART, ASC mailbox, cluster-cpufreq. **2026-10-16:** SMC (`apple,t6050-smc` with the `apple,t8103-smc` fallback in `mfd/apple,smc.yaml`, the one real `dtbs_check` finding of job 044) | ADT. m1n1 PR #610 naming. SMC compatible pattern as Asahi t6020/t8122 | Placeholder names (CPU); schema-clean (job 044) |
| 0007 | `arm64: dts: apple: Add draft t6050 (M5 Max) J716c device tree` | The generated `t6050.dtsi`, `t6050-pmgr.dtsi`, `t6050-j716c.dts` (from `kernel/experiments/t6050-dt/`). **2026-10-16:** adds `smc@28c600000` (disabled) and `smc_mbox@28c608000`; `dtbs_check` 0 findings (job 044) | See `kernel/experiments/t6050-dt/README.md`; SMC facts from `../../experiments/smc/README.md` | Draft |

## Task 4b: NVMe firmware-ABI series (already exists; apply, don't rewrite)

The macOS-15+ ANS firmware ABI fixes are Sven Peter's series "Apple NVMe fixes
for macOS 15+ firmware / M4 support". M4 and M5 need them; so do M1–M3 machines
running macOS 15+ firmware.

| Change | `b4/nvme-fwabi` (on v7.2-rc1 `dc59e4fea9d8`) | Same patch in `asahi` branch |
|---|---|---|
| (cover letter, empty b4 commit) | `761a96cb8095` | — |
| nvme-apple: Destroy the admin queue on removal | `7d5e1d1d85fb` | `9c02d723ef80` |
| nvme-apple: Don't set a DMA direction for commands without a data transfer | `d2bdc9edf220` | `07133e8a2fb8` |
| nvme-apple: Never set the opcode in the NVMMU TCB | `c64e4895d112` | `835cbc4205ac` |
| nvme: Add a quirk for page aligned admin queue buffers | `04fa7c4f1bfa` | `055df6031321` |
| nvme-apple: Require page aligned buffers on the admin queue | `1e8c7bbc5069` | `c3d4bb4f1cab` |
| nvme-apple: Drop the PRP null check chicken bit | `2d2b34f0d85c` | `a4f6716c6a69` |

* **Based on `asahi` (`77cb8f24`):** nothing to do. The six patches are
  already in. This was verified by reading `drivers/nvme/host/apple.c`,
  `core.c` and `nvme.h` at that commit, and by listing the branch history with
  the GitHub API.
* **Based on mainline ≥ v7.2-rc1:** cherry-pick
  `7d5e1d1d85fb^..2d2b34f0d85c` from `b4/nvme-fwabi`, then apply 0004 and 0005.
  0005 touches the same functions, so expect trivial context fuzz.
* The equivalent m1n1 changes are `b0cdce107543`, `0e77db5bf051` and
  `1aead9e78af0`.

**What the series does *not* contain** (checked branches: `asahi`, `asahi-wip`,
`apple-soc/drivers-7.4`, `b4/nvme-fwabi`, `bits/050-nvme`):

* the M4+ NVMMU/NVMe register split and the I/O-queue base registers. Patch
  0005 adds these;
* SARTv4. Patches 0001–0003 add it.

## Licensing and clean-room notes

* m1n1 was MIT-licensed up to v1.9.9 (`809541515659`, 2026-09-30). From v2.0.0
  it is GPL-2.0-or-later; see m1n1 commits `ce2b8a43cea4` and `2460b604c6f0`.
  The m1n1 code these drafts derive from (`9bfdf8aeca30`, `53f8ee9b54ba`) is
  present at v1.9.9 with `SPDX-License-Identifier: MIT`.
* The Linux files keep their licenses: `sart.c` is GPL-2.0-only OR MIT, and
  `nvme/host/apple.c` is GPL-2.0.
* Patches 0001–0004 and 0006 use no decompiled material: their hardware
  facts come from this machine's ADT (`hardware/scripts/adt_extract.py`) and
  from m1n1. **Since 2026-10-16, 0005 and 0007 also use register and
  transport facts recovered by offline REA/Ghidra analysis of this Mac's own
  SPTM firmware and AppleSMC kext** (`kernel/experiments/nvme-ans3/README.md`
  §4.1, `kernel/experiments/smc/README.md`). The code is original, written
  from those facts, but this makes the two patches unsuitable for Asahi's
  clean-room policy in addition to its generative-AI policy.
* m1n1 PR #631 ("T6050 j716c bringup", qspqww, closed unmerged) was **not**
  used as a source. Its notes describe the internals of Apple's
  `AppleT6050PMGR` kext, which implies binary analysis, and it adds a full
  ioreg dump file. Its notes and its `smp.c` diff were read only to judge
  provenance (the ioreg dump was not opened). Nothing from it is used here.
  The `function-enable_core` facts in this workspace come from this machine's
  own ADT.

## Test plan

**Can be done without native boot (in the project VM):**

Steps 1–3 already passed in `virtualization/jobs/018-asahi-compile-test/`.
The saved build logs contain no warning/error matches. This verifies build
compatibility only; it does not validate the hardware assumptions below.
The 2026-10-16 revision is checked offline by
`virtualization/jobs/043-nvme-smc-patches/` (clean worktree of the pinned
base inside the VM, `git am`, `apple.o`/`sart.o` with `W=1`, the t6050 DTB,
`checkpatch`, probe audit); see its `README.md`. **Result 2026-10-16: 7/7 apply, `apple.o`/`sart.o`
`W=1` clean, t6050 DTB built with 0 dtc warnings, probe audit binds the SMC nodes to `macsmc`.**
Step 4 ran offline in `virtualization/jobs/044-t6050-dtbs-check/` (dtschema
2026.9 from the venv job 020 left in the VM; nothing installed). **Result
2026-10-16: `dt_binding_check DT_SCHEMA_FILES=apple` reports only two findings
that pre-exist in `asahi@77cb8f24` in files this series does not touch (a
yamllint blank-line warning in `hwmon/apple,smc-hwmon.yaml`, a missing
`additionalProperties` note in `pci/apple,pcie.yaml`); `CHECK_DTBS=y
apple/t6050-j716c.dtb` reports 0 findings once 0006 lists `apple,t6050-smc` in
`mfd/apple,smc.yaml` (the only real finding of the first run); the Asahi
`t8132-j715` reference board also reports 0.** A clean schema check validates
property shapes against the bindings, not the hardware facts; those keep their
evidence labels in `kernel/experiments/t6050-dt/README.md`.

1. Full checkout of `asahi@77cb8f24`, then `git am` this series.
2. `make ARCH=arm64 defconfig` plus `CONFIG_APPLE_SART=y`,
   `CONFIG_NVME_APPLE=y`, `CONFIG_ARCH_APPLE=y`.
3. Build `drivers/soc/apple/sart.o` and `drivers/nvme/host/apple.o`, then
   `make dtbs`. Expected: no warnings with `W=1`.
4. `make dt_binding_check DT_SCHEMA_FILES=apple` and
   `make CHECK_DTBS=y apple/t6050-j716c.dtb`. dtschema is already in the VM:
   the venv job 020 created at `/var/tmp/t6050-build/dtvenv`
   (`export PATH=/var/tmp/t6050-build/dtvenv/bin:$PATH`). Done by job 044.
5. Static review: `scripts/checkpatch.pl --strict` on each patch.

**Needs native hardware and explicit user authorization:**

* SARTv4 programming and NVMe bring-up on t6050, verified by reading back the
  SART entries.
* The `nvme` window size of 0x40000 against the ADT's 0x10000.
* The per-TCB NVMMU status array check (replaces the 0x28120/0x29120
  question: the SPTM reads neither; see `nvme-ans3/README.md` §5 item 8).
* The SMC transport on the `smc@28c600000` node (left disabled in the DT).
* Whether the ANS still reboots the machine after a few minutes when its power
  domain is gated. This was seen on M4, which is why the draft DT keeps the
  domain always-on.

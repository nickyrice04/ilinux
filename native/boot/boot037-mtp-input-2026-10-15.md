# boot037: the MTP keyboard/trackpad input path, prepared offline

2026-10-15, M5 agent. **Native boot037 NOT RUN. Not published, not committed, no
release; the handoff records in `native/boot/` are still boot036's.** It should
not boot before the E1 read-only probe reports (stream id and DART register base
are still Likely). Evidence for the input path itself: `kernel/experiments/mtp-input/README.md` (labelled
findings), `design.md`, `m1-instructions.md`. Labels: Confirmed / Likely /
Hypothesis / Unknown.

## What it is

boot036 plus the keyboard/trackpad path of the M5's MTP coprocessor, so that the
first input experiment (E2, keyboard first light) can run over the existing USB
control channel.

| Part | boot037 |
|---|---|
| Kernel | boot036's tree (job 041) plus `dockchannel-hid` patches 0001 (input bounds) and 0002 (shared-memory ring transport), and `HIDRAW`, `HID_APPLE`, `HID_MAGICMOUSE`, `APPLE_RTKIT_HELPER` built in (VM job 042). boot036's Image carries the *pinned* driver, so 0001 is new in this Image too. |
| Stage-B DT | boot036's plus ten nodes under `/soc` (RTKit helper `mtp`, ASC mailbox, DockChannel `fifo` with its HID child `input@8000` and six interface nodes), the MTP DART enabled with its IOVA window, and the `keyboard` alias. Stream id 1 (`--sids 1`). No `power-domains`, no GPIO references. |
| Initramfs, m1n1, full DT, launcher | unchanged: the control channel (M1's key only), dropbear and the diagnostic `/init` are how E2 is observed |
| Not in the package | any Apple blob, the converted trackpad firmware (`apple/tpmtfw-j716c.bin`; the keyboard needs none), any code or protocol fact from betizzel/omarchy-m5 or GravityLinux PR #1 |

## The package

Built in ignored `build/native-boot037/` (`ilinux-j716c-boot037.tar.gz`,
`SHA256SUMS`, `verified/` = the extracted archive, `records/`).

| | |
|---|---|
| Archive | 18,924,863 bytes, SHA-256 `3900924b24f3fae2ba426911d8e8ffec628b28b59c9586d47cf189bba4008394` |
| SHA256SUMS digest (the M1's `--manifest-sha256`) | `8c817c1a97e55beb86eac15bec614ad0ec050dcaccca8c9e881f5cad2c4459c0` |
| Records (not installed in `native/boot/`) | `build/native-boot037/records/{package-manifest.json, archive-sha256.txt, intake-manifest-sha256.txt}`; manifest SHA-256 `60cce7b09af953cb708cfff120a9446139e252ede888cb252569c48dfef1250e` |
| m1n1 | unchanged pin `57a9339…`, marker `##m1n1_ver##ilinux-57a9339-boot021`, offsets as boot036 |

| File | boot036 | boot037 |
|---|---|---|
| `Image` | 44,681,728 B `e0e53113…ef3f7` | **44,812,800 B `6fb8c371baa280fe3003b02c226229f6cce784341b751593fa09e58bb6686ed9`** |
| `kernel.config` | 321,820 B `caa8e71a…3887` | **321,837 B `31596ed108a44a11fd03b0d818f164a20be312fff09865b18b5413739cbe5ee9`** |
| `t6050-j716c-stage-b.dtb` | 62,043 B `a676087b…cefa5` | **63,523 B `334301817c19e9eda5b0c49231f88bc538139dfb5071e4675f2e668d76aa6496`** |
| `initramfs-stage-b.cpio.gz` | `5f4b478b…b248` | byte-identical |
| `t6050-j716c.dtb`, `initramfs.cpio.gz`, `m1n1.bin`, `m1n1-build-config.h`, `m1n1-LICENSE`, `m1n1-revision.txt`, `diag-init.c`, `toolchain.txt` | | byte-identical |

The manifest's `early_framebuffer_descriptor_offset` moves from 35,297,168 to
35,411,856 (the Image grew by 131,072 bytes); `entry_guard` finds it.

## What changed against boot036

* **Stage-B DT, exactly:** 361 to 371 nodes. Existing nodes that differ:
  `/soc/iommu@294800000` (the MTP DART: `status = "disabled"` removed,
  `phandle` 110 and `apple,dma-range = <0x100 0x4000 0x0 0xffff0000>` added) and
  `/aliases` (`keyboard = "/soc/fifo@294b14000/input@8000/keyboard"`). New nodes:
  `/soc/mtp@294600000` (phandle 107, `iommus = <&dart 1>`, `mboxes`),
  `/soc/mbox@294608000` (phandle 108, interrupts 676-679), `/soc/fifo@294b14000`
  (phandle 109, interrupt 660, `ranges` to `0x294b28000`),
  `…/input@8000` (compatible `apple,t6050-dockchannel-hid`, `apple,fifo-size`
  0x800, `apple,helper-cpu`), and its children `multi-touch` (`firmware-name`
  only), `keyboard` (`hid-country-code` 0, `apple,keyboard-layout-id` 0, both
  overwritten by m1n1), `stm`, `actuator`, `tp_accel`, `tp-accel`.
* **Kernel config, exactly:** `HIDRAW`, `HID_APPLE`, `HID_MAGICMOUSE`,
  `APPLE_RTKIT_HELPER` from not set to `y`, plus two `# … is not set` lines that
  `HIDRAW` makes visible (`HID_CP2112`, `HID_FT260`). `kernel.config` is the
  config embedded in the Image and equals the VM tree's `.config`
  (boot036's config plus job 042's `config.diff`, checked).
* **Image:** the ring-transport driver is linked in. The Image carries
  `dockchannel_hid.mtp_{ring,enable_cmd,poll_ms,ring_size}`,
  `apple,t6050-dockchannel-hid` and `Ring registered: iova ` (all absent from
  boot036's Image; `apple,dockchannel-hid` was there already).
* **Default behaviour:** `apple,t6050-dockchannel-hid` selects ring mode; the
  driver registers the ring 100 ms after the first DockChannel traffic and
  drains it after every DockChannel message. `apple,dockchannel-hid` alone still
  selects the FIFO-era path.

## Rules the packager now enforces

`native/boot/mtp_input.py` (DT, config, Image) and `make-package.py --name
ilinux-j716c-boot037`:

| Rule | Fails closed when |
|---|---|
| Every file but `Image`, `kernel.config`, `t6050-j716c-stage-b.dtb` equals boot036's (`boot036-package-manifest.json`) | any other file differs |
| DT = boot036's Stage-B DT (digest pinned) + the delta above, compared property by property against an expected tree built from literal ADT values | one added, removed or changed property, node or alias; stream id other than 1; any `status`, `power-domains` or `*-gpios`; a duplicate or invalid phandle; wrong addresses, interrupts or window |
| Config delta = the four symbols n to y + the two revealed lines; the 13 driver-stack symbols stay `y`; no toolchain drift accepted | anything else, including a module (`m`) |
| `kernel.config` is byte-identical to the config embedded in the Image (`kconfig_guard`, boot037 is not in `DRIFTED`) | any difference |
| Image carries the ring-transport markers (provenance only) | a marker is missing |
| Control channel still enforced: `diag-init.c` equals `kernel/experiments/usb-gadget/init.c`; initramfs contract and the M1's key | either differs |

Tests: `native/boot/test_mtp_input.py` (33 tests: the exact delta on a synthetic
and on the real boot036 DT, 58 DT mutations each required to fail for its own
reason, 7 input deviations, 11 config deviations, image markers, the ADT
cross-check, the DT tool's real output, and `make-package.py` itself run on the
staged export: one accepted, 12 tampered variants refused with the right error).
`native/boot/mutate_mtp_input.py` mutates the rule and its wiring in the
packager: 36 mutants (31 + 5), all caught (its first run left 4 alive; the tests
were tightened until none survived).

## Inputs

Built on HEAD `a584322` (the MTP analysis, committed 2026-10-15 19:01). Files
that are not in that commit are marked.

| Input | SHA-256 |
|---|---|
| `kernel/experiments/mtp-input/patches/0002-dockchannel-hid-mtp-ring-transport.patch` | `1a631861c49127e9a0e85b5fd793d1a533acf18120ede98b600bce37df1fb038` |
| `kernel/experiments/driver-contracts/dockchannel-hid/0001-dockchannel-hid-validate-input-bounds.patch` | `d6abf91a052b115671ab4e9710699cf31b6cfecf44a7589ea99ddc5e03215cf5` |
| `kernel/experiments/mtp-input/make_mtp_dt.py` | `fed2ac42c201f3b90a61d415f567d1fa4bb8a988624194dac2ac1301ba9aff31` |
| `kernel/experiments/usb-gadget-dt/fdtedit.py` (**untracked**) | `f4f2c602a6a67a3e8f63f82abcefe6781d41848ed64e41480354285edbfb8f73` |
| `hardware/adt/adt-sanitized.json` | `6f143434d2f05310067559f8fa3836ae564dd9934ebc5912660f2a9f5a8a73af` |
| `kernel/experiments/usb-gadget/authorized_keys` (the M1's key, `SHA256:o7wtpNY0…`) | `394dfd501a64e7d855fe2c7779ae5a864431e858ed1d32bc130f3f859d37bc50` |
| `native/boot/boot036-package-manifest.json` (**new**, a copy of the current `package-manifest.json`; boot036 archive `f09a0000…71a3`) | `db2f25afe3d4b4778b90af08bc168941dc1a7b8728778e9c78203b8f7564090c` |
| patched `dockchannel-hid.c` / `dchid-ring.h` in job 042's tree | `01c56449…23e4` / `40aedde3…b9d2` |

## Results (Confirmed offline, nothing touched hardware)

| Check | Result |
|---|---|
| Image reproducibility (VM job 042, boot036 tree, build time/user/host pinned) | three builds, same bytes `6fb8c371…6ed9`; the third was this session's `WAIT=1 …/host-run.sh mtp-input` (vm lock taken and released, 43 s); the job's other outputs equal the first run's (DT, config diff, symbols, `W=1` warnings 0, gcc harness 39,483 checks) |
| Stage-B DT | built on this Mac by `make_mtp_dt.py` and byte-identical to the DT the VM built (`33430181…6496`); `dtc` no new warnings; `dt-validate` 0 findings before, 6 after, all "property not in a schema" (no binding for dockchannel-hid / `apple,dma-range`) |
| Packager | two builds give the same archive; the edited packager rebuilds boot036 byte-identically (`f09a0000…71a3`, manifest and both digests equal the published records) |
| Offline launcher verification | `launch.py --package` prints `Package PASS` for the committed launcher (`65ece253…`, unchanged since attempt 16) and for the working-tree launcher (`4d55f0c9…`, foreign uncommitted edits); with boot036's manifest it refuses (`missing file or size mismatch: Image`). Run in a scratch copy of `native/boot/` holding boot037's manifest, so no handoff record was touched |
| Package integrity | `shasum -c SHA256SUMS` in `verified/`: 13 files OK; no `tpmtfw`/firmware path in the Image or the initramfs (422 entries) |
| Existing `native/boot` tests | 11 of 15 run and pass: control_channel 6, dapf_guard 16, entry_guard 6, framebuffer 5, gpio_guard 10, hardware 19, installer_verifier 11, kconfig_guard 7 (now also surveys boot037), launcher 37, usb_dt 6, ramroot 30 (another session's untracked file), plus the new mtp_input 33. The same four did not run before any change and need the M1 client venv or the VM: `test_dapf_guard_adt`, `test_launcher_adt` (no `m1n1` module), `test_protocol` (`M1N1_SOURCE`), `test_framebuffer_fixup` (VM integration tool with arguments). Nothing changed here is something they exercise |

## Kernel command line: `dockchannel_hid.mtp_poll_ms=100` is NOT in this package

The launcher's fixed-argument rules do not allow it, so it is a follow-up
(Confirmed with the launcher's own fixtures, in a scratch copy, not committed):

* The launcher sets one fixed string for every package (`BOOTARGS`) and, after
  m1n1's DT preparation, accepts only that string followed by m1n1's own
  `idle=nop arm64.nowfxt`; anything else stops with `unexpected appended
  bootargs`. The prepared DT with `… dockchannel_hid.mtp_poll_ms=100` appended
  is rejected; the launcher never sets it; with the argument inside `BOOTARGS`
  every check passes.
* Editing `launch.py` is not mine to do: the working tree carries another
  session's uncommitted edits (profiles, RAM root) and the controller digest
  `65ece253…` is pinned in earlier intake records. On a kernel without the
  driver the argument should be inert (Likely: `init/main.c` drops an unmatched
  `module.parameter` as an unused module parameter; not tried here).

| Option | Cost |
|---|---|
| A. A launcher profile or fixed-argument change (`BOOTARGS + " dockchannel_hid.mtp_poll_ms=100"`) with the three scratch cases above added to `test_launcher.py` | user approval; touches the file another session is editing; changes the controller digest |
| B. Bake the default into the driver patch (`mtp_poll_ms` default 100) | new job-042 build, new Image hash, new package (a built-in `CONFIG_CMDLINE` would bypass the launcher's argument check and was not examined) |
| C. Run E2 without the poll | no code change; E2 shows the handshake and every management event that arrives with a DockChannel doorbell; a ring that fills without a doorbell is never drained and the log cannot say so |

Recommendation: C for the first light, A afterwards if the log shows the
handshake but no input.

## Findings from this review that matter for E2

* **Gate:** the MTP DART `reg` stays at `0x294800000` (offset +0 of the ADT
  region) and the stream id at 1. Both are Likely; E1 decides. A different value
  is a new DT delta and a new rule constant (`DART_REG`, `SIDS` in
  `mtp_input.py`), not a flag.
* **The genpd release ladder has nothing to release for MTP (Likely):** the
  sanitized ADT, which keeps `clock-gates` for 124 other nodes, has empty
  `clock-gates`/`power-gates` for `/arm-io/mtp` and none for `dart-mtp` or
  `dockchannel-mtp`; the Stage-B DT has no MTP power domain, and
  `nub_dock_channel` is `apple,always-on`. That matches the new nodes carrying no
  `power-domains`. That iBoot leaves the MTP blocks on is Hypothesis until E1's
  "MTP CPU started" line.
* **The trackpad interface will ask for a file that is not there:**
  `firmware-name = "apple/tpmtfw-j716c.bin"` is in the DT and the initramfs holds
  no firmware, so opening the trackpad fails with `-ENOENT` (Likely immediate:
  `FW_LOADER_USER_HELPER_FALLBACK` is not set). That is E3's blocker, not the
  keyboard's.
* **The DT tool is committed (`a584322`), its editor is not:**
  `make_mtp_dt.py` imports `kernel/experiments/usb-gadget-dt/fdtedit.py`, still
  untracked. `stage-boot037.py` needs it; the package itself does not.
* **Larger kernel delta than "MTP only":** 0001 (bounds checks) is also new in the
  Image, and `HID_APPLE`/`HID_MAGICMOUSE` add input drivers that initialize at
  boot on every run. The generic-VM liveness check below is what would show a
  regression from those.

## NOT RUN

* **Native boot037 / E2 / any live step:** NOT RUN; needs E1's result and the
  user's approval. Whether the driver binds, the firmware speaks the model,
  descriptors arrive, or a key event appears: unknown.
* **E1 (the read-only register probe):** NOT RUN; no result in the repository
  (HEAD `a584322`).
* **Generic-VM liveness of boot037's Image with the shipped initramfs
  (Virtualization.framework, one CPU, no disk or network, 95 s):** NOT RUN. A run
  was attempted and the permission check blocked it (it is not part of the
  requested work). It is the same check boot036 passed:
  ```sh
  tools/lock.sh acquire vm boot037 "boot037 liveness" 20
  ../apple-silicon-linux-research/virtualization/bin/vzrun --cpus 1 --mem 4 --no-net \
    --kernel build/native-boot037/verified/Image \
    --initrd build/native-boot037/verified/initramfs-stage-b.cpio.gz \
    --cmdline 'console=hvc0 fbcon=nodefer rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 idle=nop arm64.nowfxt pd_ignore_unused clk_ignore_unused loglevel=8 ignore_loglevel printk.time=1 panic=0 earlycon=ilinuxfb initcall_debug initcall_blacklist=clk_debug_init ilinux_probe_diag=1'
  # stop after 95 s; expect: PID 1 reached, online_cpus=1, [ctl] no UDC yet, [ctl] dropbear start 1, 60s elapsed; still alive
  tools/lock.sh release vm boot037
  ```
* **dummy_hcd USB self-test on boot037:** NOT RUN (the USB DT, initramfs and gadget
  config are byte-/delta-identical to boot036's, which passed; the test Image is
  boot036-specific).
* **Effective DT after m1n1's fixups** (`check_stage_b(prepared=True)`): only at a
  live launch; m1n1's handling of the new nodes was never observed.
* **M1 intake receipt** (`verify-package.py`), publication of
  `native-j716c-boot037`, `tools/m1n1-client` checklist for boot037: not done.

## Reproduce

```sh
# kernel-side (offline; takes the vm lock; about 45 s); the Image must be 6fb8c371…6ed9
WAIT=1 virtualization/jobs/042-mtp-input/host-run.sh mtp-input
# stage (refuses a wrong baseline, a failed job, another Image or a DT that differs from the VM's)
python3 -I native/boot/stage-boot037.py --previous build/native-boot036/verified \
  --job-out virtualization/jobs/042-mtp-input/out --destination build/native-boot037/stage \
  --expect-image-sha256 6fb8c371baa280fe3003b02c226229f6cce784341b751593fa09e58bb6686ed9
# package (records go to a private directory, not to the current handoff)
mkdir -p build/native-boot037/records
python3 -I native/boot/make-package.py --out build/native-boot037/stage --destination build/native-boot037 \
  --name ilinux-j716c-boot037 --previous-package build/native-boot036/verified \
  --authorized-key kernel/experiments/usb-gadget/authorized_keys --record-dir build/native-boot037/records
# checks
for t in test_mtp_input test_usb_dt test_control_channel test_kconfig_guard test_launcher; do
  python3 -I native/boot/$t.py; done
python3 -I native/boot/mutate_mtp_input.py
```

## To promote it (each step needs the user's go-ahead)

1. Commit `native/boot/{mtp_input.py, test_mtp_input.py, mutate_mtp_input.py,
   stage-boot037.py, boot036-package-manifest.json, make-package.py (edited),
   test_kconfig_guard.py (edited)}` and this file, together with
   `kernel/experiments/usb-gadget-dt/` (the DT tool's editor).
2. Copy the three `records/` files over `native/boot/`
   (`package-manifest.json`, `archive-sha256.txt`, `intake-manifest-sha256.txt`);
   only then does `launch.py --package build/native-boot037/verified` verify it.
3. Decide the kernel-argument question above; publish `native-j716c-boot037`;
   write the M1 checklist (E1 first, then E2 from `m1-instructions.md`).

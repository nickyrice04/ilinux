# boot042: boot041 with the MTP keyboard path and the storage drivers as modules, prepared offline (attempt 26)

2026-10-19, M5 side session. **Native boot042 / attempt 26 NOT RUN. Nothing committed, pushed or released.**
It builds on attempt 25 (`stage-b-2026-10-19-attempt25-result.md`), boot041 (`boot041-two-darts-2026-10-18.md`)
and boot037's MTP work (`boot037-mtp-input-2026-10-15.md`, `kernel/experiments/mtp-input/`). Labels: Confirmed /
Likely / Hypothesis / Unknown; "Confirmed" means in source, offline or in a VM, never on the M5's hardware.

## Summary

* **Attempt 26 = the keyboard, switched on from the SSH session one module at a time after the USB link is
  up.** Storage is prepared in full as attempt 27's separate set (`kernel/experiments/nvme-ans3/storage-ro/`)
  and kept out of the attempt-26 package, image and checklist: the committed launcher refuses any Stage-B DT
  whose NVMe node is enabled (`fdt.check_stage_b`), and that guard stays; attempt 27 needs a separate launcher
  change the user reviews (the user's decision, 2026-10-19).
* **Kernel (VM job 050):** boot041's tree plus dockchannel-hid 0001 (input bounds) and 0002 (the M4/M5 ring
  transport), with the keyboard path (`APPLE_DOCKCHANNEL`, `HID_DOCKCHANNEL`, `APPLE_RTKIT_HELPER`,
  `HID_APPLE`, and `HID_MAGICMOUSE` for later) and the storage drivers (`NVME_APPLE`, `NVME_CORE`,
  `APPLE_SART`) as modules, and `HIDRAW` (a bool of the built-in HID core) on. Nothing else in the config
  (two `is not set` lines appear because `HIDRAW` makes them visible).
  Image `0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c` (44,616,192 bytes), identical
  over two builds.
* **Stage-B DT:** boot041's plus boot037's MTP nodes (the RTKit helper, its mailbox, the DockChannel FIFO
  and its HID child with six interface nodes, the MTP DART enabled with its IOVA window, the keyboard
  alias), with the MTP on DART streams 0-4. USB untouched, NVMe still disabled. `17c55af9…0405`, 63,539
  bytes, the same bytes from the Mac and the VM.
* **The one change at boot:** the built-in apple-dart driver (needed for the USB DARTs) now probes the MTP's
  DART too and resets it. The MTP's mailbox binds to the built-in mailbox driver without touching a register.
  Every keyboard and storage driver waits as a module.
* **Omarchy root (job 045):** attempt 25's build for boot042's Image, plus the keyboard modules (blacklisted
  from automatic loading), `ilinux-keyboard` and attempt 25's four fixes (deviations 25-31).
* **Storage set:** the same tree's storage modules, with an nvme-core patch that makes every namespace
  read-only and refuses every media-changing command before any controller sees it, a mode that cannot be
  turned off (a load that asks for it off fails); VM-tested against a writable virtual NVMe disk (guarded:
  nothing written; control, a VM-only build with the mode off: the same attempts write).
* **Package:** boot041's twelve files with `Image`, `kernel.config` and the Stage-B DT replaced, staged in
  `build/boot042/package/`, packaged by `make-package.py`'s new boot042 entry into `build/native-boot042/`
  (`a2e57c0c…a781`); the committed launcher's offline run accepts that package with the pinned root.

## Kernel: what changed and why (Confirmed: job 050, the exact tree)

| Symbol | boot041 | boot042 | Why |
|---|---|---|---|
| `APPLE_DOCKCHANNEL` | y | **m** | the MTP's FIFO driver; it would bind `fifo@294b14000` at boot (it masks and acknowledges the FIFO's interrupts and creates `input@8000`) |
| `HID_DOCKCHANNEL` | y | **m** | the HID transport, with 0001 and 0002; binds `input@8000` |
| `APPLE_RTKIT_HELPER` | n | **m** | binds `mtp@294600000`: sets the MTP CPU's run bit and wakes or boots its RTKit |
| `HID_APPLE` | n | **m** | Apple's key mapping; its table matches host-bus Apple keyboards (`HID_DEVICE(BUS_HOST, …, HOST_VENDOR_ID_APPLE, …)`) |
| `HID_MAGICMOUSE` | n | **m** | for later trackpad work; not in the attempt-26 root |
| `HIDRAW` | n | **y** | raw report captures; a bool of the built-in HID core (it registers a character device class, no hardware) |
| `NVME_APPLE`, `NVME_CORE`, `APPLE_SART` | y | **m** | the storage set; not in the attempt-26 root, so the Image has no storage code (boot041's SART node was bound at boot; boot042's is not) |

**Kept built in, and why:** `APPLE_DART` (the USB DARTs need it at boot; it is boot041's patched driver);
`APPLE_MAILBOX` (it already binds the ANS mailbox at boot in boot041, and making it a module would force
RTKit to one and change boot041's boot; its probe maps the registers and requests both interrupts with
`IRQF_NO_AUTOEN`, so the new MTP mailbox node binds with no register access: Confirmed, `check_facts.py`);
`APPLE_RTKIT` (a library with no device of its own; it acts only when a module calls it); `HID`, `INPUT`,
`EVDEV` (boot041's). The exact delta is enforced by `kernel/experiments/boot042-modules/check_config_delta.py`
(job 050) and `native/boot/boot042_modules.py` (the packager's rule). The file also gains
`# CONFIG_HID_CP2112 is not set` and `# CONFIG_HID_FT260 is not set`: two USB bridge drivers that depend on
`HIDRAW` and only become visible with it; both stay off.

The tree is a copy of job 041's (its Image is boot041's, its `.config` boot041's, its `apple-dart.c` job
041's patched file: checked). A rebuild of that copy at another path does not reproduce boot041's bytes: the
build ID in the Image's notes hashes the debug information, which names the tree's directory (job 047 found
the same). boot042 is reproducible at job 050's own tree path (`/var/tmp/ilinux-boot042/linux`): two builds give
the same Image, config, DT, modules and storage-set files (only the test disk, random by design, differs). The
Image names its build `ilinux@boot042` in `/proc/version` (`KBUILD_BUILD_HOST`), which `ilinux-keyboard` and
`ilinux-storage-ro` check; the job was first numbered 049 and renamed to 050 because another session's job
had taken 049, and the build identity was moved from the job number to the boot name at the same time.

**What vmlinux no longer has, and still has** (Confirmed, job 050's symbol check and liveness log): no
`apple_nvme_probe`, `apple_sart_probe`, `dockchannel_probe`, dockchannel-hid or RTKit-helper code, no
`nvme_setup_cmd`; still the gadget stack, the DART diagnostics, the genpd ladder, the HID core with hidraw,
the mailbox and RTKit. In the 95 s generic-VM boot, `nvme_core_init`, `apple_nvme_driver_init` and
`dockchannel_hid_driver_init`, which boot041's own log shows at 0.043-0.071 s, do not run.

**Kernel facts the checklist relies on** (`kernel/experiments/boot042-modules/check_facts.py`, 20 facts, all
found in the exact tree): apple-dart's probe validates PARAMS before any write, resets the DART unless locked,
then requests its fault interrupt shared and enabled; its reset disables every stream (which also clears a
t8110 stream remap); several `iommus` entries on one DART merge into one stream map; a device's IOMMU set-up
runs only when a driver probes it, so `mtp@294600000` gets no DART set-up at boot; the module probes write
what the table above says; dockchannel-hid's patched messages (`Initialized, awaiting packets`, `Ring
registered`, `New interface keyboard`, `Interface keyboard is now ready`).

## Stage-B DT

`kernel/experiments/mtp-input/make_mtp_dt.py` on boot041's DT, `--sids 0,1,2,3,4`; `native/boot/boot042_modules.py`
checks the result property by property against an expected tree built from literal ADT values (boot037's
`mtp_input.check_delta`, now with the stream list as an argument; boot037's own rule unchanged: 33 tests, 36
of 36 mutants caught).

* **Ten new nodes, two changed** (`/soc/iommu@294800000`: `status` removed, `phandle` and `apple,dma-range`
  added; `/aliases`: `keyboard`), as boot037. Phandles 0x6e-0x71.
* **Streams 0-4, not boot037's 1:** the ADT's `dart-mtp` remaps streams 1-4 to 0 for macOS (Confirmed, ADT),
  and Linux's reset of a t8110 DART clears that remap (Confirmed, source), so the MTP's traffic arrives on
  whichever stream it uses; giving the helper and the HID node streams 0-4 puts all five on one table (one
  stream map, one domain). The E1 probe was to decide between 0 and 1 before any boot; this covers both in
  the attempt itself (Likely sufficient; which stream the MTP uses stays Unknown and shows in the DART's
  fault lines if none of these).
* **Checks:** `fdt.check_stage_b` passes (NVMe and the three cpufreq nodes disabled); dt-validate: boot041's
  three `snps,dwc3 iommus … too long` findings plus the same six "no schema" findings boot037's nodes had.

## Omarchy root (job 045, `LINK=1 CLAUDE=1 NOPASSWD=1 MODULES=…`)

Attempt 25's root (Omarchy's own installer, the link, Claude Code signed out, Omarchy's permanent
passwordless sudo for `omarchy`; Claude Code is the release current at build time, 2.1.304 here, 2.1.303 in
attempt 25's) for boot042's Image, with deviations 25-31 of job 045's report
(`omarchy-arm64/omarchy-root-report-2026-10-17.md`):

| # | What | Why |
|---|---|---|
| 25 | SSH login shells get `BROWSER=/usr/local/lib/ilinux/ssh-browser`, which prints the address and opens nothing (`/etc/profile.d/ilinux-ssh-browser.sh`, only with `SSH_CONNECTION`) | attempt 25: `claude` over SSH opened Chromium on the M5's screen through the `BROWSER` Omarchy's interactive shell sets (`omarchy-launch-browser`), which keeps one that is already set |
| 26 | `archlinux-keyring-wkd-sync` timer and service masked | 75 % of attempt 25's journal |
| 27 | sshd on a USB port starts only once a host has configured that port (`wait-usb-host`, silent; `TimeoutStartSec=infinity`), and the login grace exit (status 3) is a clean end | the uncabled ports restarted sshd every 47 s |
| 28 | Chromium's component updates off (managed policy) | about 31 MB through the M1's relay |
| 29 | boot042's four keyboard modules under `/usr/lib/modules/<release>`, indexed by the root's `depmod` | the keyboard path is modules |
| 30 | `/etc/modprobe.d/ilinux-boot042.conf` blacklists them | udev's coldplug loads by alias at every boot (checked at build: each MTP node's alias resolves to its module without the blacklist and to nothing with it; by name they still load) |
| 31 | `/usr/local/bin/ilinux-keyboard` | the attempt's procedure |

No storage module is in the root (the stage refuses one). Omarchy's `linux-modules-cleanup` keeps the module
directory (it is the running kernel's) and no longer fails.

**VM boot test** (job 045 stage 4, QEMU TCG, one vCPU, boot042's Image): the image is 2,435,320,732 bytes, SHA-256
`565644bed5aa2d2c7ab594868447c74a33fd9317c6269c3c52570eef86d3bf6f` (built 2026-10-19T22:08:01Z; 8,815,328,206 bytes
unpacked in 215,508 files; zstd `--ultra -22 --long=27`, 635 s), 966,405 bytes more than attempt 25's. Desktop ready
208.5 s and first run done 211.0 s after kernel start (attempt 25's build: 224.4 s and 221.7 s), 13,971 MiB in use
at the settled desktop (14,126 MiB), the menu, Chromium and Obsidian rendered with no new core dump, Claude Code
2.1.304 (the release current at build time). Pin record: `build/boot042/records/omarchy-root-manifest.json`
(`2ac6658a…9383`), for the handoff. The link test passes
end to end and now also checks the fixes and the modules: an SSH login shell's `BROWSER` is the stand-in, it
printed the address and nothing launched (no process, no `uwsm-app` line), the desktop session keeps
Omarchy's; wkd-sync masked and silent through two clock steps; the sshd unit has the `wait-usb-host`
`ExecStartPre`, no start timeout, status 3 a success, and its login-grace ends count as clean (the 18 ordinary
session ends exit 255 as before); the Chromium policy; the keyboard modules are present with their digests,
not loaded at boot, load and unload by name with no kernel complaint, and `sudo ilinux-keyboard` over SSH stops
at its first check (`no /soc/mtp@294600000 in the device tree`, the VM has no MTP) with nothing loaded.
`virtualization/jobs/045-omarchy-installer-root/test-wait-usb-host.sh` (Mac, a fake configfs and UDC class)
covers what the VM cannot show, a port no host has configured: 11 cases PASS (waits silently while not
attached, powered, default or addressed; returns within a second once configured or suspended; fails for a tty
no gadget owns or a UDC that goes away).

Not shown in any VM: `ilinux-keyboard`'s steps 1-6 (they need the MTP), m1n1's handling of the new nodes,
Chromium reading the policy (its path is in the binary; checked at build).

## Storage set (kept apart)

See `kernel/experiments/nvme-ans3/storage-ro/README.md`: how read-only is enforced, the VM test and its
results, what is unknown on the M5, and what a launcher change would have to do. In short: the guarded VM
run refused every write path (block device, mapping, discard, zero-out, passthrough I/O and admin commands,
mounts) and left the virtual disk's SHA-256 unchanged; the control run, with nvme-core's VM-only control
build loaded with the mode off, wrote through the same paths and changed it. The shipped `nvme-core.ko`
(`6c7f3a8f53959c0245b763840abaf06999e8e5905eee65c9f1b0e65515facb0e`; the set's `SHA256SUMS` `f57ad4fe…4e18`)
cannot be loaded with the mode off: `ilinux_read_only=0` fails with EPERM, so `sudo modprobe nvme-core
ilinux_read_only=0` on a root with passwordless sudo is no way to write. A sibling session's launcher review
found the earlier switchable parameter; job 050 was rebuilt for it, and the Image, DT, config and every
keyboard module came out byte-identical (26 of the export's 35 files; the 9 that differ are the storage
set's files, `modules/manifest.json`, which lists them, and the test disk, random at every run).

| Storage test (Mac, `virtualization/jobs/050-boot042-keyboard/run-vz.sh storage` and `script`, 2026-10-19, Virtualization.framework, boot042's Image, a writable virtual NVMe disk) | Result |
|---|---|
| guarded (the storage set's nvme-core) | **PASS, the disk's SHA-256 unchanged.** Loading with `ilinux_read_only=0` first: EPERM, nothing loaded; then as built, `Y`; ro flags 1 on the disk and its three partitions; reads work (O_DIRECT, passthrough Read, Identify, Get Log Page); `write(2)` EPERM (also after root's `BLKROSET 0`), writable `mmap` EINVAL, `BLKDISCARD`/`BLKZEROOUT` EPERM, `BLKSECDISCARD` EOPNOTSUPP; passthrough Write, Flush, Write Zeroes, Dataset Management, Write Uncorrectable, Format NVM, Sanitize, firmware download and commit, namespace management and attachment, Set Features (cache; queues with Save), Security Send and a vendor command all refused (EOPNOTSUPP, one kernel line each); ext4 refused its journal replay, FAT mounted read-only |
| control (the VM-only control build with `ilinux_read_only=0`, another copy) | the same data paths wrote and **the copy's SHA-256 changed**: the guarded refusals are the guard's |
| the load script, `ilinux-storage-ro --transport pci`, in a small userland (another copy) | **every step PASS**, a second run stopped at its first check (`nvme-core is loaded already`), no UUID or serial printed, **the copy's SHA-256 unchanged** |

**What a launcher change would have to do to run the storage set** (described, not written; details in the
storage README): the check is `fdt.check_stage_b`; a new profile (for example `omarchy-storage-ro`, with its
own confirmation string) would have to accept exactly one enabled NVMe node, `/soc/nvme@45dcc0000`
(`apple,t6050-nvme-ans2`), only in that profile, keep the cpufreq nodes disabled and every other profile
unchanged, require the storage stack as modules and no NVMe or SART driver in the Image, rely on a pin record
that says the root carries no storage module, bind the set by its `SHA256SUMS` digest (`f57ad4fe…`, covering
`nvme-core.ko` `6c7f3a8f…`), and pass the M1's
controller-digest review and the user's approval; the packager's own `check_stage_b` call would need the same
profile-scoped exception. **The M1's intake for attempt 27 would have to verify** (storage README): the launcher
diff and its new controller digests, with the user's approval; the package against Git, its Image boot042's
byte for byte; by its own property-level diff, that the DT differs from boot042's only in the NVMe node's
`status`, and that the other profiles still refuse that DT; the storage set's `SHA256SUMS`, `nvme-core.ko`'s
attested digest and its always-on parameter description; the root read from the image (no storage module
under `/usr/lib/modules`, the set, script and rule equal to Git's, nothing that mounts an NVMe device); and
the go/no-go text with identity-only recording. Another session's design for this change, for the user's
review, pins the set that way and reads its own root pin. Attempt 26 is the keyboard alone; storage is attempt 27 (the
user's decision, 2026-10-19).

## Package

**Packaged (2026-10-19) in the ignored `build/native-boot042/` and published as the prerelease `native-j716c-boot042`.** The boot042 entry in
`native/boot/make-package.py` went in with the user's approval, additive only, as boot036 to boot041 each
added theirs: the name joins the `--name` choices and the 14 cumulative lists boot041 is in, and the baseline
map gets boot042 → boot041 (16 lines extended); 9 lines are new: the allowed changes (`Image`, the Stage-B DT,
`kernel.config`), one call to `boot042_modules.check_package`, and the record's history line and fields from
`boot042_modules`. `check_stage_b`, every other entry, the help strings, `launch.py` (`b14ec7a1…`), `fdt.py`
(`ee577a08…`) and the four places the attempt-27 launcher patch changes are untouched; that patch and this
entry apply together in either order with the same result (checked on copies). The package carries no
storage: no module or script, and an Image with no NVMe, SART or nvme-core code.

| Package | |
|---|---|
| `ilinux-j716c-boot042.tar.gz` | 18,877,362 bytes, SHA-256 `a2e57c0ccddcd7c8e60affac0ffa033deb9db1639119a7aa93faaedea276a781` |
| SHA-256 of its `SHA256SUMS` (the intake digest) | `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd` |
| exactly these differ from boot041 | `Image` `0b6df395…b69c`, `kernel.config` `4f137b37…`, `t6050-j716c-stage-b.dtb` `17c55af9…0405` |
| records | `build/native-boot042/records/`; the root's pin `build/boot042/records/omarchy-root-manifest.json` |

| Check (2026-10-19) | Result |
|---|---|
| `test_boot042_package.py` (after `test_boot041_package.py`) | 9 of 9: byte-identical rebuild with the same record, the record's fields, only the three files differ from boot041, boot041's Image or a changed one, a config that is not the Image's, seven DT changes (the NVMe node enabled, streams 1, 1-4 or 0-5, the MTP DART disabled, an unrelated property, boot041's DT), every other file, the baseline and flags, another key |
| `test_boot042_rule.py` | 10 of 10 |
| `mutate_boot042.py` (after `mutate_mtp_input.py`) | 25 mutants, 25 caught: 20 in `boot042_modules.py` (the DT rule and its streams, the config delta, the revealed lines and kept drivers, the Image digest and its markers, each check of `check_package`) and 5 in the packager entry (the call, wider allowed changes, another baseline, the record's fields and history) |
| `mutate_mtp_input.py` with the entry | 36 mutants, 36 caught, as without it (the entry repeats none of its targets) |
| every other `native/boot` suite (the repository, boot042's records and pin in place) | all pass: 265 tests in 17 suites; four files do not run on this Mac, as before: `test_dapf_guard_adt.py`, `test_launcher_adt.py` and `test_protocol.py` need m1n1's Python client, and `test_framebuffer_fixup.py` is a command-line tool that needs an m1n1 build and its arguments |
| the committed launcher's offline run (`b14ec7a1…`) from the repository, `--profile omarchy`, the job 045 image, with boot042's records and pin in `native/boot/` | **exit 0**, the seven lines of the checklist; upload 2,480,000,463 bytes, 496.0 s at 5 MB/s (475.1 s at attempt 22's measured 5.22 MB/s), deadline 900 s |

Not run here: the M1's `verify-package` receipt (it needs the M1's m1n1 client pin) and the launcher's
prepared-DT check (`Hardware DT`, at launch). At the handoff (2026-10-19) the coordinating session copied the
records and the root's pin into `native/boot/`, applied the pin-bound `test_ramroot.py` change, published the
prerelease (target `a1cc21a`; GitHub's digest and a fresh download both match `a2e57c0c…a781`) and made the
draft the attempt-26 checklist, `tools/m1n1-client/stage-b-instructions.md`.

## NOT RUN / Unknown

* **NOT RUN:** native boot042 / attempt 26, every hardware step, the M1's readiness, m1n1's handling of the
  MTP nodes (the launcher checks its prepared DT at launch), and the E1 probe (no longer needed first).
* **Unknown:** whether the MTP DART's reset at boot disturbs the MTP firmware iBoot started (it runs with no
  host DMA until the helper wakes it: Hypothesis); whether the MTP answers RTKit's wake; the DockChannel
  doorbell and where the descriptors travel (README §9, Unknowns 1-2; `--poll 100` is the retry); the
  stream the MTP uses (0-4 covered); the trackpad (firmware, the SMC reset: not attempted).

## Reproduce

```sh
WAIT=1 virtualization/jobs/050-boot042-keyboard/host-run.sh          # the vm lock: kernel, DT, modules, storage set
virtualization/jobs/050-boot042-keyboard/run-vz.sh both              # Mac: liveness, storage guard and control, load script
python3 -I native/boot/test_boot042_rule.py
python3 -I native/boot/test_mtp_input.py
# job 045's out/job.env: LINK=1 CLAUDE=1 NOPASSWD=1 KERNEL_NAME=boot042 KTREE=/var/tmp/ilinux-boot042/linux
#   KERNEL and MODULES = /mnt/ilinux/virtualization/jobs/050-boot042-keyboard/out/export/{Image,modules}
#   IMAGE_SHA=0b6df395…b69c (in full), ZSTD_FINAL="--ultra -22 --long=27" VARIANTS=0
WAIT=1 virtualization/jobs/045-omarchy-installer-root/host-run.sh omarchy-045   # about 27 min
virtualization/jobs/045-omarchy-installer-root/test-wait-usb-host.sh          # Mac, 11 cases
python3 -I native/boot/make-package.py --out build/boot042/package/out --destination build/native-boot042 \
    --name ilinux-j716c-boot042 --previous-package build/native-boot041/verified \
    --authorized-key kernel/experiments/usb-gadget/authorized_keys --record-dir build/native-boot042/records
python3 -I native/boot/test_boot042_package.py
python3 -I native/boot/mutate_boot042.py
```

The packaged files are extracted to `build/native-boot042/verified/` for the package test, as for boot041.

## Files

* New: this report; `kernel/experiments/boot042-modules/` (`check_config_delta.py`, `check_facts.py`,
  `module_sets.py`, `handoff/`: how it was packaged); `kernel/experiments/nvme-ans3/storage-ro/`;
  `native/boot/boot042_modules.py`, `test_boot042_rule.py`, `test_boot042_package.py`, `mutate_boot042.py`,
  `boot041-package-manifest.json` (boot041's record, the packager's baseline for boot042);
  `virtualization/jobs/050-boot042-keyboard/`; job 045's `test-wait-usb-host.sh` and its new link-overlay
  files; the checklist, `tools/m1n1-client/stage-b-instructions.md` (first the draft `stage-b-attempt26-draft.md`).
* Changed: `native/boot/make-package.py` (the boot042 entry, with the user's approval: 16 lines extended with
  the name, 9 added); `native/boot/mtp_input.py` (an optional `sids` argument; boot037's behaviour unchanged);
  job 045's `link.sh`, `run.sh` and link test; `omarchy-arm64/omarchy-root-report-2026-10-17.md` (deviations
  22 and 25-31); `kernel/experiments/mtp-input/README.md`.
* Changed at the handoff: `native/boot/package-manifest.json`, `archive-sha256.txt` and
  `intake-manifest-sha256.txt` (boot042's), `omarchy-root-manifest.json` (the pin for boot042's Image),
  `test_ramroot.py` (its one pin-bound assertion) and `tools/m1n1-client/stage-b-instructions.md` (the
  attempt-26 checklist).
* Untouched: `native/boot/launch.py` (`b14ec7a1…`), `fdt.py` (`ee577a08…`) and the other controller files.

# Storage set for attempt 27: the internal SSD, read-only by construction (prepared offline)

2026-10-19, M5 side session (attempt-26 preparation). **Never run on the M5. Not part of the attempt-26
package, image or checklist: nothing there can load or bind storage.** The user's decision (2026-10-19):
attempt 26 is the keyboard alone; storage follows as attempt 27, with a separate launcher change the user
reviews. This directory and VM job 050 (`virtualization/jobs/050-boot042-keyboard/`) hold attempt 27's
ready-to-package set, built from the same boot042 tree, so attempt 27 can reuse boot042's Image. Labels: Confirmed / Likely / Hypothesis /
Unknown; "Confirmed" means in source, offline or in a VM, never on the M5.

## Why it is separate

The committed launcher (`native/boot/launch.py` `b14ec7a1…`) refuses any Stage-B DT whose NVMe node is
not `status = "disabled"`: `fdt.check_stage_b()` (`native/boot/fdt.py:102-114`), which it runs on the
package's DT (`launch.py:81`) and on m1n1's prepared DT (`launch.py:233`), and which
`make-package.py:63` runs too. A disabled node never binds, module or not, so the storage step cannot run
in a boot that uses this launcher unchanged. That guard stays (parent session, 2026-10-19); loosening it
needs the user's approval and its own review. What such a change would have to do is at the end.

## The set

| File | What |
|---|---|
| `0001-nvme-core-ilinux-read-only.patch` | nvme-core's iLinux read-only mode, always on (`ilinux_read_only` reports it, 0444; a load that asks for it off fails): every namespace read-only, every command that could change the media refused before it reaches a controller |
| `ilinux-storage-ro` | the load script, run over SSH as root: one module at a time, read-only checks before and after, the controller's identity, the partition table, a short read |
| `60-ilinux-nvme-readonly.rules` | for the root of such an attempt: NVMe block devices read-only, ignored by udisks, not ready for systemd's mounts |
| `ro_test.c`, `make_test_disk.sh` | the VM test: PID 1 that tries every write path, and its 64 MiB test disk |
| job 050 `out/export/storage-set/` | `modules/` (apple-sart, nvme-core with the patch, nvme-apple with the current `kernel/patches/t6050/0005`, nvme for the VM test; `SHA256SUMS`), both test initramfs, the test disk, the script and the rule (all ignored build output) |

Built by job 050 from the boot042 tree (boot041's plus the MTP transport). The tree's `apple.c` was an
older 0005; job 050 replaces it with the series' current file (the M4+ per-TCB status array instead of a
`0x28120` read, 32-bit lo/hi base writes; diff kept in job 050's `out/build/`); `sart.c` already was the
current one. boot042's Image contains none of these drivers (`CONFIG_NVME_APPLE`, `NVME_CORE`,
`APPLE_SART` are `m`; job 050's symbol check), so storage code runs only when this set is loaded.

## How read-only is enforced, exactly

1. **No storage driver at boot.** boot042's Image has no NVMe, SART or NVMe-core code (Confirmed: symbols,
   initcalls absent from its 95 s liveness log while boot041's log shows `nvme_core_init` and
   `apple_nvme_driver_init`). The storage modules are not in the attempt-26 root at all, so neither udev's
   coldplug nor anything else can load them. In a later root they would sit outside `/usr/lib/modules`
   (no alias index) and be loaded by path with `insmod` by `ilinux-storage-ro` only.
2. **nvme-core makes every namespace read-only** before userspace sees it: `nvme_ns_is_readonly()` (the one
   place all three `set_disk_ro()` calls ask) returns true (in this build, always). So `write(2)`
   on the block device fails (EPERM), a shared writable mapping is refused at `mmap` (EINVAL), discard and
   zero-out fail (EPERM), and file systems mount read-only or not at all. Root's `BLKROSET 0` clears only the
   per-device flag, not the disk's, so writes stay refused (all Confirmed in the VM test below).
3. **nvme-core refuses every media-changing command before any controller sees it**, in
   `nvme_setup_cmd()`, the call nvme-apple's and nvme-pci's `queue_rq` make for every request before they
   map data or submit anything: block-layer requests other than reads, and passthrough commands outside
   an allowlist (on a namespace Read alone; on the admin queue queue creation and deletion, Identify, Get
   Log Page, Get Features, Abort, Asynchronous Event Request, Keep Alive, Doorbell Buffer Config, and Set
   Features for the features the driver itself sets, never with Save). The request ends with
   `BLK_STS_NOTSUPP` (the ioctl returns EOPNOTSUPP) and the kernel logs `iLinux read-only: refused …`.
   This layer matters because the block layer's own flag is not enough: in this kernel `bio_check_ro()`
   only warns (Confirmed in the pinned `block/blk-core.c`), so a write that reached the driver would go
   through; and passthrough ioctls ignore the flag for root (Confirmed: the control run below writes
   through them).
4. **The mode cannot be turned off.** `ilinux_read_only` only reports it. It is 0444, so it cannot be
   written once the module is loaded (the kernel gives a parameter without write bits no store method,
   root included), and a load that asks for it off fails with EPERM before the module initialises, so no
   NVMe driver binds at all: `insmod … ilinux_read_only=0`, `modprobe`, a `modprobe.d` option and the kernel
   command line alike (Confirmed in the VM: the guarded run's first check). This matters because a root
   that carries the set has passwordless sudo: were the parameter a switch, `sudo modprobe nvme-core
   ilinux_read_only=0` would be enough to write. Only nvme-core's VM control build, compiled with
   `ILINUX_RO_CONTROL` into the test initramfs and never into the storage set, accepts 0; job 050,
   `module_sets.py` and `ilinux-storage-ro` each refuse a storage set whose nvme-core is not the always-on
   build (by its parameter description). `ilinux-storage-ro` also loads with `insmod` and no parameters,
   refuses to start if the kernel command line names the parameter, and unloads nvme-core again, before
   any controller exists, if the parameter does not read `Y`. (A sibling session's review of the launcher
   change found the earlier switchable parameter, 2026-10-19.)
5. **Nothing mounts, checks, repairs or writes it.** The script never opens a block device for writing;
   it refuses to start if `/etc/fstab` or `/etc/crypttab` could name a device it brings up, if anything is
   mounted from an NVMe device, or (with udev running) if the rule is missing; the rule keeps udisks and
   the desktop's volume monitor away and systemd from considering the devices ready.

The ANS firmware's own housekeeping (wear levelling, its metadata) is outside the host's control, as at
every boot of macOS or iBoot; the host itself issues no write.

## VM test (Confirmed in the VM, 2026-10-19; `virtualization/jobs/050-boot042-keyboard/run-vz.sh storage`)

Virtualization.framework on this Mac (`vzrun --nvme`): boot042's Image, a **writable** virtual NVMe disk
(the PCI transport, `nvme.ko`, and this set's `nvme-core.ko`), `ro_test` as PID 1, twice:

| Run | Disk | Result |
|---|---|---|
| guarded (the storage set's `nvme-core.ko`, `6c7f3a8f…`) | a copy of the 64 MiB test disk: GPT, 16 MiB of random bytes in an APFS-typed partition, ext4 marked `needs_recovery`, FAT | **all checks PASS; the copy's SHA-256 unchanged**. First, loading the module with `ilinux_read_only=0` fails with EPERM and nothing is loaded (the kernel: `iLinux read-only mode cannot be turned off in this build`, `` `0' invalid for parameter `ilinux_read_only' ``); then it loads as built and reads `Y`. ro flags 1 on the disk and its three partitions, `BLKROGET 1`; reads work (O_DIRECT, passthrough Read, Identify, Get Log Page); `write(2)` EPERM, also after root's `BLKROSET 0`; writable `mmap` EINVAL; `BLKDISCARD`/`BLKZEROOUT` EPERM, `BLKSECDISCARD` EOPNOTSUPP; passthrough Write, Flush, Write Zeroes, Dataset Management, Write Uncorrectable, Format NVM, Sanitize, Firmware Commit and Image Download, Namespace Management and Attachment, Set Features (volatile write cache; number of queues with Save), Security Send and a vendor command all EOPNOTSUPP, each with its `iLinux read-only: refused … opcode 0x..` line; ext4 refused (`write access unavailable, cannot proceed`, journal not replayed), FAT mounted read-only, file creation EROFS. The controller set itself up normally under the allowlist (`1/0/0 default/read/poll queues`, partitions scanned) |
| control (nvme-core's VM control build, `ILINUX_RO_CONTROL`, test initramfs only, loaded with `ilinux_read_only=0`, reads `N`) | another copy | the same data-path attempts **write** (pwrite, mmap, discard, zero-out, passthrough Write; ext4 mounts read-write and replays its journal) and **the copy's SHA-256 changes**: the guarded run's refusals are the guard's, not a disk that could not be written. The admin commands that change a controller are never sent in this mode |

The load script itself (`run-vz.sh script`, 2026-10-19): boot042's Image, a small userland (this job VM's
bash, coreutils, util-linux, kmod, procps, gawk, sed and grep with their libraries) and `ilinux-storage-ro
--transport pci`, against another copy of the test disk: **every step PASS** (nvme-core, the always-on
build, announced its read-only mode and read `Y` before the controller existed; the disk and its three partitions `ro=1`;
identity `Apple Virtual NVMe Controller`, firmware `1.0`, no serial read; the GPT printed with its types and
names and no UUID; two 16 MiB O_DIRECT reads, 0.012-0.015 s, equal; zero refusals, since the script never
tries to write), **a second run stopped at its first check** (`nvme-core is loaded already`), and **the
copy's SHA-256 did not change**.

Not shown by any test: the block-layer branch of the refusal (`refused <op> request`), which the
read-only flag keeps every user path from reaching (it is a backstop); Chromium-, udisks- or
gvfs-specific behaviour (the VM userland has none; the rule covers them on a full root); anything about
the ANS.

## On the M5 (NOT RUN; what the script would do and what is unknown)

`sudo ilinux-storage-ro` (apple transport): step 0 checks boot042, the digests, the read-only default, no
NVMe device or mount yet, the rule, and that the controller's DT node is enabled (with the current
launcher it is not, so it stops there); then apple-sart (binds the SART; the driver reads its existing
entries at probe), nvme-core (`Y` checked), nvme-apple (resets and boots the ANS coprocessor through
RTKit, waits for boot status `0xde71ce55`, programs the SART, the NVMMU and the queues, enables the
controller), the read-only checks, identity, table and a 16 MiB read.

* **Unknown:** whether the ANS boots under Linux without the SPTM on t6050 (m1n1's driver does it through
  the `reg[9]` aperture; `../README.md` §5); whether `reg[9]`'s decode covers `0x24908`-`0x24914`; whether
  the firmware needs `0x1304`/`0x13c8`; what the genpd release ladder has done to the NVMe's `apcie0`/`apcie1`
  domains by then (unclaimed until the driver binds, so released at about 45 s; the driver powers them on
  again; the `ans` domain itself is always-on).
* **Seen on M4 by others:** the ANS rebooting the machine some minutes after its domain was gated; here
  `ans` stays on.
* **Risk to the data:** none from the host (above). The worst plausible outcomes are a coprocessor that
  does not boot, a hang or a reset; a power cycle returns the M5 to Macintosh HD.

## What a launcher change would have to do (described, not written)

The check is `fdt.check_stage_b()`: every node whose compatible contains `nvme` or `cluster-cpufreq` must be
`status = "disabled"`, and there must be exactly four such nodes. A change that lets this set run would
have to:

1. **Be a new profile** (for example `omarchy-storage-ro`, with its own confirmation string), so that
   `stage-b`, `ramroot` and `omarchy` keep refusing an enabled NVMe node exactly as now.
2. In that profile only, accept **exactly one** enabled NVMe node, `/soc/nvme@45dcc0000` with
   `apple,t6050-nvme-ans2`, and still require the three cpufreq controllers disabled, on the package's DT
   and on m1n1's prepared DT alike.
3. Require that the package's `kernel.config` builds the storage stack as modules (`NVME_APPLE`, `NVME_CORE`,
   `APPLE_SART` `=m`) and that the Image carries no NVMe or SART driver, so nothing binds the node at boot.
4. Require a RAM-root pin record that says the root carries no storage module in `/usr/lib/modules` and has
   the read-only rule (the launcher can check only the record and the digest, not the image's content),
   and bind the exact modules the M5 can load: the storage set by the SHA-256 of its `SHA256SUMS`, which
   covers this set's always-on `nvme-core.ko` (`f57ad4fe…4e18` for job 050's set).
5. Keep every other check, the fixed arguments and the m1n1 pin as they are; extend `test_launcher.py` with
   the accepting and refusing cases; and go through the M1's controller-digest review and the user's
   approval like any launcher change.

Packaging such an attempt also needs a DT whose NVMe node is enabled, which `make-package.py` refuses for
the same reason (it calls `check_stage_b`), so the packager's check would need the same profile-scoped
exception. Another session is developing such a change for the user's review, outside Git and not applied
(profile `omarchy-storage-ro`, its own confirmation, a `storage_guard.py`; the package attests the set by
its `SHA256SUMS` digest, `module_sums_sha256`, and the profile reads its own root pin with the same field;
it also requires `NVME_CORE=m` and `NVME_APPLE=m` in the Image's embedded config, which boot042's passes).
That session reports its dry run with job 050's files passing and the omarchy and stage-b profiles refusing
the same package.

### What the M1's intake must verify for attempt 27 (described, not written)

1. **The launcher change itself:** the diff read in full; the new controller digests (`launch.py`,
   `fdt.py`, any new guard module) reviewed and recorded as for every launcher change; the user's approval
   recorded; the offline suites, with the new profile's accepting and refusing cases, passing.
2. **The package, before extraction:** the archive's digest against Git's record, then the `verify-package`
   receipt, as for boot042. Its Image must be boot042's byte for byte (`0b6df395…b69c`), so attempt 27 adds no
   kernel code that runs at boot.
3. **The DT, by the M1's own property-level diff** of attempt 27's Stage-B DT against boot042's: exactly one
   property differs, `status` of `/soc/nvme@45dcc0000`; the three cpufreq controllers still disabled; every
   other node, the MTP's included, unchanged. And the negative case offline: the stage-b, ramroot and omarchy
   profiles still refuse that DT.
4. **The storage set:** its `SHA256SUMS` digest equal to the one the package attests (`f57ad4fe…4e18` for
   job 050's set) and every file equal to it; `nvme-core.ko` (`6c7f3a8f…facb0e`) shows the always-on
   parameter description, not the control build's; every module's vermagic is the Image's.
5. **The root image, by size and digest against its pin, and read from the image itself** (as attempt 25's
   intake did with `tar`): no storage module under `/usr/lib/modules` (no `nvme*`, no `apple-sart`); the set
   at its path with its `SHA256SUMS`; `ilinux-storage-ro` and `60-ilinux-nvme-readonly.rules` equal to Git's;
   no `fstab` or `crypttab` line and no mount unit that could name an NVMe device.
6. **The go/no-go text before the human starts:** the load order (apple-sart, then nvme-core with its
   refused-off check, then nvme-apple), the stop rules, the power-cycle recovery, and the recording rules:
   identity fields only (model, firmware revision, capacity), never a serial number or a partition UUID.

## Reproduce

```sh
WAIT=1 virtualization/jobs/050-boot042-keyboard/host-run.sh boot042          # the vm lock, about 1 min
virtualization/jobs/050-boot042-keyboard/run-vz.sh storage                    # Mac, about 1 min, no lock
virtualization/jobs/050-boot042-keyboard/run-vz.sh script
```

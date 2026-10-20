# The two-stage boot: a small stage one through m1n1, the Omarchy root over the USB link (VM-tested, NOT RUN natively)

**Historical design and tests for the preceding roots.** The current attempt-27
pair and its results are in [the current validation record](attempt27-two-stage-validation.md).
Use [the current M1 checklist](../../tools/m1n1-client/stage-b-instructions.md);
the older pins and timing estimates below do not certify the new pair.

2026-10-19, M5 side sessions (VM job 049). **Proven in a VM on this Mac; nothing has run on the M5's
hardware.** Labels: Confirmed / Likely / Hypothesis / Unknown; "Confirmed" means in code, offline or
in the VM, never on the M5. Nothing is committed, pushed or released. Built and tested first for
attempt 25's root on boot041 (stage one `4e2ea2a3…`); **rebuilt and re-tested the same evening for
attempt 26's root on boot042 (stage one `44acacfc…`)**, which was the pair at the time of this report.

## Summary

* **Why.** Attempt 25 spent 473.0 s uploading the 2.43 GB Omarchy root (job 045, `b8eae454…66c1`)
  through m1n1's USB proxy at 5.24 MB/s, then measured the Linux USB byte pipe at about 25 to 27 MB/s
  each way over SSH. The two-stage boot moves the big image to that link.
* **Stage one** (`omarchy-arm64/two-stage`): job 039's RAM root without its desktop (115 Arch Linux
  ARM packages, job 039's RAM-root layer unchanged, the operator keys root-owned 0644 as job 039 now
  installs them) plus a receiver, a panel status screen and the pin of stage two. **For attempt 26's
  root (`565644be…6bf6f`, boot042's Image `0b6df395…b69c`): 59,636,857 bytes
  (`44acacfccc811beee4893b6f45e01991ce81ae4db15c3e7b141733bb1e3f6872`), 337,524,038 unpacked**; the
  first build, `4e2ea2a3…` (59,627,338 bytes), was for attempt 25's root on boot041. No private key,
  host key, password or keyring. **The launcher's existing `ramroot` profile carries it unchanged**
  (`launch.py` stays `b14ec7a1…`): only `native/boot/ramroot-manifest.json` is re-pinned. With the
  boot042 package m1n1 uploads 104,316,588 bytes: **about 20 s** at attempt 25's rate, against 473.0 s.
* **Stage two:** the M1 runs `tools/m1n1-client/m5-stage2.py`, which checks the image against
  `native/boot/omarchy-root-manifest.json`, offers its size and SHA-256 over SSH on the byte pipe
  (`m5s`, root, its own known_hosts) and streams it once stage one accepts the offer. Stage one reads
  at most `size + 1` bytes into a tmpfs, hashing on the way in, checks size and SHA-256 against its
  pin, unpacks with `bsdtar` into a tmpfs at `/run/nextroot`, checks the entry count and the entry
  points, and **soft-reboots into it**. Whatever fails, stage one stays up and says why on the panel
  (red), in the journal (`ilinux-stage2`, which interface 0 carries to the M1) and in the M1's session.
* **VM proof (job 049, QEMU with Hypervisor.framework on this Mac, one vCPU, job 041's test Image =
  boot041's Image plus `dummy_hcd`, boot042's kernel release): the full run and the timing run PASS on
  the rebuilt stage one with attempt 26's root**, as both did on the first build with attempt 25's.
  Full run: stage one's link up 3.7 s after the kernel started; a login as `omarchy` through the 0644
  key file; an image it is not pinned to refused before a byte (6.0 s); a session that ended after
  64 MiB refused; **the pinned size with one byte changed refused by the SHA-256 check after the whole
  2,435,320,732 bytes**; each time stage one stayed up, the panel showed the reason in red and the
  journal had it; then the real image: received in 307.7 s (7.9 MB/s: both computers on one vCPU),
  verified, unpacked in 10.3 s (215,508 entries, 10.3 GiB), soft-reboot; **the Omarchy root's systemd
  started 2.2 s after the unpack, its gadget 2.1 s later, the desktop (job 045's definition of ready)
  11.3 s after its systemd** (20.4 s in the timing run: Omarchy's own first-boot pacman-keyring
  creation, which SDDM waits for, took 12.0 s there and 3.1 s here), and **stage two's own link
  worked**: the journal on interface 0, this boot's host key equal to ssh's record, SSH as `omarchy`
  with passwordless sudo. **Stage two's failed units: `omarchy-provision-hardware` and `ufw` only**, as
  job 045's VM test of this root found (`linux-modules-cleanup` keeps the root's boot042 modules and no
  longer fails). **Timing run (the image sent as soon as the link was up): desktop ready 348.5 s after
  the kernel started**, of which the VM's transfer was 307.6 s and everything else 40.9 s (the first
  build with attempt 25's root: 344.5 s and 35.3 s).
* **Native estimate (Inferred): handoff to the Omarchy desktop about 125 to 155 s, launch to desktop
  about 150 to 180 s** (attempt 25: 476.5 s to the handoff plus about 30 s). The transfer at attempt
  25's measured rate dominates (about 97 s); it has never run at this size on the M5.
* **Found in the VM and fixed:** across a soft-reboot systemd keeps device units plugged with the
  `SYSTEMD_WANTS` they had, so stage two's gadget (wanted by the same udev rule in both roots) was never
  started; stage one now clears its udev database after udevd stops, as an initrd does before
  switch-root. A switch unit that called `systemctl soft-reboot` itself was killed by it and its failed
  state was carried into stage two: the soft-reboot is now the unit's `SuccessAction`. Job 039's
  gadget unit always stops "failed" (its `KillSignal=SIGKILL`); a stage-one drop-in counts that as
  clean.

## Design

### Stage one

Built by VM job 049 (`virtualization/jobs/049-two-stage-boot/run.sh`, the `vm` lock, about 2 minutes)
for boot042's Image (`0b6df395…b69c`: job 050's, packaged as `ilinux-j716c-boot042`; named in the job's
`out/job.env`). The first build, `4e2ea2a3…`, was for boot040's Image (`a53d1d47…`), which boot041
carries byte for byte. The rebuild has the same 115 package versions and the same 10,326 paths; a
file-by-file comparison of the two images finds only the pin, the three script edits below, boot042's
built-in module lists (`apple-dockchannel`, `apple-sart`, `dockchannel-hid`, `nvme-core` and
`nvme-apple` are modules in boot042, none of them in stage one) and build stamps (build-info, the
`.updated` stamps, pacman's log, ldconfig's cache, the regenerated Java CA store):

| Layer | What |
|---|---|
| Packages | job 039's "init, login and base tools" and `openssh`, plus `zstd`, `libarchive` (bsdtar) and `kbd` (console fonts): 115 packages from the official mirror with signature checks (`omarchy-arm64/two-stage/packages.txt`) |
| Job 039's RAM-root layer, unchanged | `/init` (bind-mounts rootfs onto itself, execs systemd), `usb-gadget.sh` (one gadget per controller: the journal on interface 0, `sshd -i` on interface 1, `bcdDevice 0x0039`), its units and udev rule, sshd's drop-ins (key-only, `LoginGraceTime 45`, keepalives), `/etc/environment`. Its desktop files are present, not enabled: stage one boots to `multi-user.target` |
| Keys | the operator's public keys (the M1's, `kernel/experiments/usb-gadget/authorized_keys`) in `/etc/ssh/authorized_keys.d/{root,omarchy}`, **root-owned 0644**: job 039's working-tree fix (sshd opens the file as the user who logs in; at 0600 omarchy was refused, VM job 046). The VM logged in as omarchy on stage one through that layout |
| Two-stage layer | `ilinux-stage2` (receive, switch, status), `stage1-screen` (the panel; a red line when the state still says switching a minute later, which means the soft-reboot fell back to stage one), `ilinux-stage2-switch.service` (`SuccessAction=soft-reboot`), `ilinux-stage2-udev-cleanup.service` (wanted by `soft-reboot.target`), `ilinux-ssh-hostkey.service` (a host key per boot; its fingerprint line tagged `ilinux-ssh-hostkey` in the journal, where the first build's showed `sh`) and its `sshd-tty` drop-in, a drop-in for job 039's gadget unit (`SuccessExitStatus=SIGKILL`) |
| The pin | `/etc/ilinux/stage2-pin`: `omarchy-root-manifest.json`'s size, sha256 and image_sha256 (which must equal stage one's own Image, or the build stops), plus `entries=215508` and `unpacked_bytes_16k=11012407296` for attempt 26's root (attempt 25's: 215,472 and 11,007,361,024), measured by unpacking stage two in the build VM exactly as `switch` does (10.6 s there) |
| Checks | job 039's prune and 16 KiB ELF check (no pruned library missing; 3 pre-existing optional ones: `ssh-sk-helper`, `arpd`, `memusagestat`), a private-key scan of the whole root, no host key, no `id_*`, locked passwords, an empty machine-id |

### The receive, the checks, the switch

| Step | Check | On failure (stage one stays up) |
|---|---|---|
| Offer (`ilinux-stage2 receive SIZE SHA256`) | equal to the pin | refused before a byte is read, exit 3 |
| Admission | a lock (one transfer or switch at a time); no verified image waiting; MemAvailable ≥ image + unpacked root + 1 GiB | refused, exit 3 |
| Transfer | `dd` reads at most `size + 1` bytes into a tmpfs of its own (sized to the image), `tee` into `sha256sum` | short or long stream: failed, exit 4 |
| Image | size and SHA-256 equal the pin; zstd magic | failed, exit 4 |
| Unpack (`ilinux-stage2-switch.service`, so it finishes if the session goes) | `bsdtar -x -p --numeric-owner` into a tmpfs at `/run/nextroot` (no size option: half of RAM, rootfs's own limit); entry count equals the pin; `/init` and `/usr/lib/systemd/systemd` executable; an os-release | failed, exit 5; both tmpfs unmounted |
| Switch | the unit ends; its `SuccessAction=soft-reboot` stops stage one's units (the gadget is unbound and removed cleanly), the udev database is cleared after udevd stops, systemd moves `/dev`, `/proc`, `/sys` and `/run` into `/run/nextroot` and execs the Omarchy root's systemd | systemd stays in stage one if `/run/nextroot` holds no OS tree |

**Why a soft-reboot (Confirmed in code and in the VM):** systemd 262's `SwitchRoot` refuses outside an
initrd (`Not in initrd, refusing switch-root operation`, in `libsystemd-core-262-1.so`); its
soft-reboot switches a running system into `/run/nextroot` when that holds an OS tree. Making stage
one a systemd initrd would have meant rewiring job 039's units around `initrd.target`, and an initrd
whose switch fails drops to the emergency shell, which the M5 cannot answer.

**How the result differs from a one-stage boot of the same image (attempts 25 and 26; Confirmed in the
VM):** the same image runs as the
root, from a tmpfs (`ilinux-stage2-root`, half of RAM, as rootfs). Its PID 1 is the image's systemd
started by the soft-reboot (`--switched-root --deserialize`), not by the image's `/init`, whose only
job is to make the kernel's rootfs an ordinary mount (a tmpfs already is one). systemd counts one
soft-reboot (`SoftRebootsCount=1`; "Soft-reboot finished in …" instead of "Startup finished in …").
`/run` is carried over, so `journalctl -b` and the journal on interface 0 begin with stage one's
records. The udev database is cleared before the switch, so device handling is a fresh boot's. Stage
one's files stay in the kernel's rootfs, unreachable (about 0.34 GB). The hostname changes from
`ilinux-m5-stage1` to `omarchy` at the switch.

### The M1 side

* `tools/m1n1-client/m5-stage2.py` (standard library): checks the image's size, then SHA-256, against
  the manifest (nothing is sent on a mismatch: exit 3); opens `m5s`; waits for stage one's `ready`
  (a refusal comes back at once: exit 1); streams 1 MiB pieces with a progress line every 5 s (MB, %,
  the rate now and on average, the time left); then prints stage one's report (its own rate, the
  verdict, the unpack, the switch). Exit 0 switching, 1 refused or check failed, 2 session failed,
  3 image does not match the manifest, 4 unpack or switch failed. `--dry-run` checks the image only.
  `test_m5_stage2.py`: 18 tests (a stand-in for stage one: success, the offer refused, busy, the
  SHA-256 failure, an unpack failure, a dropped session, silence, the local checks, the dry run, and
  `m5-ssh-config`'s `m5s` entries through `ssh -G`).
* `m5-ssh-config` gains `m5s` and `m5s-port1..3`: root, `HostKeyAlias m5-stage1`,
  `build/control/known_hosts-stage1` (clear it before each boot: the host key is made per boot),
  `ClearAllForwardings yes`, the same usb-pipe ProxyCommand. After the switch the M1 uses `m5o` as in
  attempt 25.

## VM test (job 049)

`run-qemu.sh` on this Mac, no lock: the workspace QEMU 11.1.1 with Hypervisor.framework
(`kernel-irqchip=on`), one vCPU, 32 GiB, `virt` with GICv3; the launcher's RAM-root arguments plus
m1n1's append plus `console=hvc0`; a device tree with the M5's root compatible and a `/chosen`
simple-framebuffer 3456x2234 x2r10g10b10 (`fdt-fb.py`, since the Mac has no `dtc`); job 041's
`Image-test` (`a1ecd7f8…`: boot041's Image with `dummy_hcd` and the generic usb-serial driver built
in, so the kernel is the host of its own gadget, job 046's approach); stage one exactly as built, then
the VM-built test base (python3, the Linux `usb-pipe`, a VM key pair) and an overlay from the working
tree (the test scripts, `m5-stage2.py`, `m5-ssh-config`, the manifest); stage two on a read-only
virtio disk. A test hook in the overlay adds the stage-two probe to the unpacked root before the
switch, as job 045's boot test appended its probe to the same image; the delivered stage one has no
hook (the switch logs any use). The test Image's release, `7.1.9-g863199d8b4a3-dirty`, is boot042's
too (job 050 builds boot041's tree plus the MTP transport), so stage two's boot042 modules belong to
the running release, as on the M5; boot042's own Image cannot be the VM's kernel (no `dummy_hcd`).
What the judge expects of stage two (size, SHA-256, entry count, build-info) comes from stage one's
pin and the build's unpack record since the rebuild; it refuses to boot a stage one whose pin names
another image than `omarchy-root-manifest.json`.

### Rebuilt stage one with attempt 26's root: full run (2026-10-19 19:39 to 19:51 EDT), `run-qemu.sh: PASS`

Stage one `44acacfc…` (as pinned), stage two `565644be…6bf6f` (as pinned). Times are seconds since the
kernel started. Evidence: `virtualization/jobs/049-two-stage-boot/out/runs/full-boot042-2026-10-19/`
(ignored by Git).

| s | Event |
|---:|---|
| 2.57 | this boot's host key in the journal, **now tagged `ilinux-ssh-hostkey`** (the first build's line showed `sh`) |
| 2.65 / 2.66 | stage one's gadget bound (`bcdDevice 0x0039`) / "Startup finished in 431ms (kernel) + 2.231s (userspace)" |
| 3.67 | link up: `ilinux-sshd-tty@ttyGS1` active |
| 6.09 | a login as `omarchy` on stage one through the root-owned 0644 key file |
| 12.15 | **an image stage one is not pinned to**: `stage one refused: the M1 offers 1,048,576 bytes … pinned to 2,435,320,732 bytes`, exit 1 in 6.0 s, nothing sent |
| 26.13 | **a session that ended after 64 MiB**: `failed: the transfer ended after 67,108,864 of 2,435,320,732 bytes (8.5 s; the M1's session closed early)`, exit 4 |
| 340.00 | **the pinned size with one byte changed**: 2,435,320,732 bytes in 308.1 s, then `SHA-256 054bb592… of the received image differs from the pin 565644be…`, exit 4 |
| 341.29 | the real image: `m5-stage2.py` hashed it (0.8 s), stage one accepted the offer |
| 648.94 | received in 307.7 s (7.9 MB/s); verified at once (hashed on the way in) |
| 659.37 | unpacked: 215,508 entries, 10.3 GiB, in 10.3 s; `switching` |
| 661.53 | the Omarchy root's systemd (`UserspaceTimestampMonotonic`), hostname `omarchy`; `linux-modules-cleanup` ends cleanly at 663.00 |
| 663.59 | stage two's gadget bound (the same descriptors) |
| 667.15 / 667.17 / 668.22 | "Soft-reboot finished in 5.770s, counter is now at 1" / SDDM / Hyprland |
| **672.80** | **desktop ready**, 11.3 s after stage two's systemd (layers omarchy-background, -bar, -dock, -notifications) |
| 699.30 | stage two's link as the M1 uses it: the journal on interface 0 up to this boot's host key (1,983 lines, 16 of them stage one's `ilinux-stage2`), SSH `m5o` in 0.4 s: `omarchy@omarchy`, `sudo -n id -u` 0, root `ilinux-stage2-root tmpfs`, `SoftRebootsCount 1`, build-info `built 2026-10-19T22:08:01Z`, `options LINK=1 CLAUDE=1 NOPASSWD=1` |

As before, after each failed attempt stage one was waiting again with nothing left mounted, the reason
in the journal and as the panel's last outcome (captures `shot-neg1-other-image`, `shot-neg2-short`,
`shot-neg3-corrupt`; `shot-receiving`; `shot-desktop`). Stage two's failed units:
`omarchy-provision-hardware` and `ufw`. Memory at the end: 15,430 MiB used of 32,438 (shared 11,204).
Wall time 702.6 s. The panel's new red line for a soft-reboot that fell back to stage one does not
show on this path (the switch succeeded); the script was run once against a fake `/proc` and
`/run/ilinux-stage2`: no red line 59 s after the switching state, the line at 61 s.

### Rebuilt stage one with attempt 26's root: timing run (2026-10-19 19:51 to 19:57 EDT), `run-qemu.sh: PASS`

`NEGATIVES=0 run-qemu.sh`, evidence in `out/runs/timing-boot042-2026-10-19/`: the real image goes as
soon as the link is up (this time after the stage-one login check, which the first build's timing run
lacked).

| s | Event |
|---:|---|
| 2.50 / 2.59 / 2.60 | host key (`ilinux-ssh-hostkey`) / gadget bound / "Startup finished in 366ms (kernel) + 2.228s (userspace)" |
| 3.60 | link up |
| 7.66 | stage one accepts the offer and receives (the M1 stand-in first copied the image from its virtio disk, 2.0 s, logged in as `omarchy`, then `m5-stage2.py` hashed it, 0.9 s) |
| 315.24 | received in 307.6 s (7.9 MB/s), verified |
| 325.91 | unpacked in 10.6 s; `switching` |
| 328.09 | the Omarchy root's systemd |
| 329.92 | stage two's gadget bound |
| 329.60 to 341.55 | Omarchy's first boot creates the machine's pacman keyring (12.0 s; 3.1 s in the full run) |
| 342.62 | "Soft-reboot finished in 14.708s, counter is now at 1" |
| 342.80 / 343.83 | SDDM / Hyprland |
| **348.48** | **desktop ready: 348.5 s after the kernel started**, 20.4 s after stage two's systemd |
| 374.98 | SSH `m5o` in 0.5 s: `omarchy@omarchy`, `sudo -n id -u` 0, root `ilinux-stage2-root tmpfs`, `SoftRebootsCount 1`, the pinned image's build-info; failed units `omarchy-provision-hardware`, `ufw`; 15,126 MiB used |

Everything but the transfer took 40.9 s of the 348.5 (the link 3.6, the M1 side's start 4.1, the
unpack 10.7, the switch 2.2, stage two to the desktop 20.4, of which 12.0 the keyring). With the
transfer at attempt 25's measured rate instead, the same run would take about 348.5 − 307.6 + 97 ≈
138 s (Inferred).

### First build (`4e2ea2a3…`) with attempt 25's root: full run, final (2026-10-19 17:13 to 17:25 EDT): `run-qemu.sh: PASS`

Stage one `4e2ea2a3…` (as then pinned), stage two `b8eae454…66c1`, the final test scripts. Times are
seconds since the kernel started (both stages share one kernel). Evidence:
`virtualization/jobs/049-two-stage-boot/out/runs/full-2026-10-19b/` (ignored by Git; the run before it,
`full-2026-10-19/`, is the same image and passed the same checks, two of its verdict patterns needed
fixing first).

| s | Event |
|---:|---|
| 2.58 | stage one: "Startup finished in 371ms (kernel) + 2.2s (userspace)"; gadget bound (`bcdDevice 0x0039`) |
| 3.74 | link up: `ilinux-sshd-tty@ttyGS1` active, this boot's host key in the journal |
| 6.37 | **a login as `omarchy` on stage one** through `/etc/ssh/authorized_keys.d/omarchy`, root-owned 0644 (job 039's fix) |
| 12.46 | **an image stage one is not pinned to** (the tool with a 1 MiB image and its own manifest): `stage one refused: the M1 offers 1,048,576 bytes … pinned to 2,434,354,327 bytes`, exit 1, nothing sent |
| 26.50 | **a session that ended after 64 MiB**: `failed: the transfer ended after 67,108,864 of 2,434,354,327 bytes (8.6 s; the M1's session closed early)`, exit 4 |
| 342.67 | **the pinned size with one byte changed**: 2,434,354,327 bytes in 310.4 s, then `SHA-256 … of the received image differs from the pin b8eae454…`, exit 4 |
| 342.67 | the real image: `m5-stage2.py` hashed it (1.0 s), stage one accepted the offer |
| 652.32 | received in 308.3 s (7.9 MB/s); verified at once (hashed on the way in) |
| 662.74 | unpacked: 215,472 entries, 10.3 GiB, in 10.3 s; `switching` |
| 664.90 | stage one's units stopped, its udev database cleared after udevd; the Omarchy root's systemd 262 (`UserspaceTimestampMonotonic`), hostname `omarchy` |
| 666.95 | stage two's gadget bound (the same descriptors) |
| 670.42 / 670.56 / 671.59 | "Soft-reboot finished in 5.670s, counter is now at 1" / SDDM / Hyprland |
| **675.25** | **desktop ready**, 10.4 s after stage two's systemd (the shell answers its IPC ping; layers omarchy-background, -bar, -dock) |
| 701.74 | stage two's link as the M1 uses it: the journal on interface 0 up to this boot's host key (it starts with stage one's records), SSH `m5o` in 0.4 s: `omarchy@omarchy`, `sudo -n id -u` 0, root `ilinux-stage2-root tmpfs`, `SoftRebootsCount 1`, the pinned image's build-info |

After each failed attempt the test checked that stage one was waiting again, nothing was left mounted,
the journal had the reason and the panel's last outcome named it (captures `shot-neg1-other-image`,
`shot-neg2-short`, `shot-neg3-corrupt`; `shot-receiving` shows the progress bar and rate; `shot-desktop`
the Omarchy desktop). Stage two's failed units: `linux-modules-cleanup`, `omarchy-provision-hardware`,
`ufw`, as in attempt 25 and job 045's VM test. Memory at the end: 15,137 MiB used of 32,438 (shared
11,197: the root, `/run`, stage one's leftovers).

### First build with attempt 25's root: timing run (no refusal tests first)

`NEGATIVES=0 run-qemu.sh` (2026-10-19 17:06 to 17:12 EDT; evidence in `out/runs/timing-2026-10-19/`): the
real image goes as soon as the link is up. PASS, apart from the stage-one omarchy login check, which
was added after this run started (the first build's final full run above has it).

| s | Event |
|---:|---|
| 2.58 | stage one: "Startup finished in 371ms (kernel) + 2.204s (userspace)" |
| 3.59 | link up |
| 7.17 | stage one accepts the offer and receives (the M1 stand-in first copied the image from its virtio disk, 2.0 s; `m5-stage2.py` hashed it, 1.0 s) |
| 316.37 | received in 309.2 s (7.9 MB/s), verified |
| 328.09 | unpacked in 11.6 s; `switching` |
| 330.25 | the Omarchy root's systemd |
| 332.43 | stage two's gadget bound |
| 336.75 | "Soft-reboot finished in 6.645s, counter is now at 1" |
| 337.02 / 338.07 | SDDM / Hyprland |
| **344.54** | **desktop ready: 344.5 s after the kernel started**, 14.3 s after stage two's systemd |
| 371.05 | SSH `m5o` in 0.5 s: `omarchy@omarchy`, `sudo -n id -u` 0, root `ilinux-stage2-root tmpfs`, `SoftRebootsCount 1`, the pinned image's build-info; failed units attempt 25's three; 15,128 MiB used |

Everything but the transfer took 35.3 s of the 344.5 (the link 3.6, the M1 side's start 3.6, the
unpack 11.6, the switch 2.2, stage two to the desktop 14.3). The VM's pipe is slow because both
computers share its one vCPU (the M1's ssh and usb-pipe, the host side of `dummy_hcd`, the gadget,
the M5's sshd and receiver): job 046 measured the same 7.5 to 8 MB/s. With the transfer at attempt
25's measured rate instead, the same run would take about 344.5 − 309.2 + 97 ≈ 133 s (Inferred).

### Earlier runs and what they found

These are the first build's, except the last item.

1. The Mac's `/bin/bash` is 3.2 (no `mapfile`): the harness died after starting QEMU. Fixed.
2. The generic usb-serial driver binds only IDs it is given: `new_id` (job 046 does the same; the kernel
   keeps it across the soft-reboot). The panel's sshd line read cgroupfs file sizes, which are 0. Fixed.
3. First complete transfer and switch (the stage one image `97cae968…`): the desktop came up 11.7 s
   after stage two's systemd, but **stage two's gadget never started**: systemd deserialized the
   controller's device unit as plugged with the same `SYSTEMD_WANTS`, and its hook only starts wants
   that are new after a switch. Also the switch unit (killed by its own `systemctl soft-reboot`) and the
   gadget unit (SIGKILL) were carried into stage two as failed, and the panel script stopped on the
   hook's unprefixed log line. Fixed in `4e2ea2a3…`: the udev cleanup unit, `SuccessAction`, the drop-in,
   the log format; the first build's full run above is that image.
4. The rebuild for attempt 26's root: `run-qemu.sh` had attempt 25's root written into its verdict (its
   size, digest, entry count, build-info and three failed units). It now reads them from stage one's
   pin and the build's unpack record, and stage two's failed units from `FAILED_UNITS` (default: this
   root's two). Re-judging the first build's final run with these rules still gives PASS (given attempt
   25's three failed units). Nothing else in the test changed: job 045's new `sshd-tty` drop-in, which
   starts sshd only once a host has configured the port (`wait-usb-host`), passes stage two's link
   check as it is. **In stage two that wait returned at once**: sshd started 20 ms after systemd began
   starting it, 0.2 s before the host side enumerated the new gadget (both runs), where on a fresh boot
   (job 045's own test) it waited the 1.2 s until the host had configured the port. Likely the UDC's
   `state` still read `configured` from stage one when stage two's gadget was bound (dummy_udc; Unknown
   for the M5's dwc3). Harmless here: on the cabled port sshd waits for the M1 either way; at worst, as
   before the fix, its 45 s grace time runs out (status 3, a clean end under the drop-in) and it starts
   again.

## Native estimate (Inferred)

| Phase | VM | Basis for the M5 | M5 estimate |
|---|---:|---|---:|
| m1n1 upload (boot042's Image, stage one, DT: 104,316,588 bytes) | (QEMU loads) | attempt 25: 5.24 MB/s, plus about 3.5 s of the launcher's checks | about 23 s before the handoff |
| handoff to stage one's link | 3.6 to 3.7 s | attempt 20: systemd 2.3 s after the kernel with a 182 MB root; attempt 25: gadget 2.6 s after systemd | 4 to 6 s (Likely) |
| macOS accessory approval, the M1's tool connects | — | attempt 25: 3.2 s from enumeration to configuration with the human's click; SSH 0.5 s | a few s, the human's |
| transfer, 2,435,320,732 bytes (attempt 25's root: 2,434,354,327) | 307.6 to 310.4 s at 7.8 to 7.9 MB/s over eight whole transfers (five with the first build, three with the rebuild; both computers on one vCPU) | attempt 25: 16.8 MB in 0.63 s each way (26.7 MB/s), one sample, a desktop running | **90 to 100 s at 24 to 27 MB/s** (Inferred; the M5 also hashes and writes to tmpfs, a few % of a CPU) |
| SHA-256 check | 0 s (on the way in) | sha256sum of the image in 1.2 s in the build VM | 0 s extra |
| unpack | 10.2 to 11.6 s | the kernel unpacked the same image in about 14 s in attempt 25 | 12 to 20 s (Likely) |
| switch | about 2.2 s (2 s for the M1 to read `switching`) | — | about 2.5 s |
| stage two's systemd to the desktop | 10.4 to 20.6 s (the spread is mostly Omarchy's first-boot pacman-keyring creation, which SDDM waits for: 3.1 and 12.0 s in the rebuild's two runs) | attempt 25: userspace 9.6 s, desktop 27 to 31 s after the handoff with a 14 s unpack | 11 to 20 s |
| **handoff to desktop** | **344.5 and 348.5 s** (the two builds' timing runs; 35.3 and 40.9 s without the transfer) | the VM's 35.3 to 40.9 s plus the transfer at 24 to 27 MB/s, plus the M5's slower unpack and the human's click | **about 125 to 155 s** |
| **launch to desktop** | | attempt 25: about 507 s | **about 150 to 180 s** |

The time spent moving bytes falls from 473 s to about 20 s through m1n1 plus about 97 s over the link.

## Risks and unknowns for the native run

* **Unknown:** the pipe's sustained rate for 2.43 GB, and the M5's single CPU doing sshd's decryption,
  `u_serial` and the receiver's copies at once (attempt 25 measured one 16.8 MB transfer each way).
* **Unknown:** bulk OUT through the dwc3 core and its two DARTs for about 100 s at full rate (attempt 25
  moved 72 MB to the M5 over 12 minutes with no fault line).
* **Unknown:** the gadget unbound in stage one and bound again in stage two on the same dwc3 core (the
  VM's `dummy_hcd` exercises neither dwc3 nor the DARTs). If stage two's link fails, the desktop still
  comes up (the switch does not depend on it).
* **Unknown:** whether macOS asks again to allow the accessory when stage two's gadget appears with the
  same descriptors.
* **Likely:** the panel's 16x32 font (`latarcyrheb-sun32`, set from user space; the kernel has only 8x16)
  reads on the real panel as in the VM's capture (the same simple-framebuffer format and size).
* Memory is not a constraint on the M5 (126 GiB usable): peak about 14 GB during the unpack.

## Follow-ups (not done)

* A smaller stage one: `libarchive` pulls `libxml2` and ICU (about 40 MB unpacked); GNU `cpio` behind
  `zstd -d` would unpack the same newc archive. About 2 s less upload; the unpack path would need the
  same VM test.
* Measure the receive path's CPU on the M5 (sshd, `u_serial`, `dd`/`tee`/`sha256sum`) during the first
  native run; if the pipe is CPU-bound there, an AES-GCM cipher for `m5s` (both CPUs have AES
  instructions) is the first thing to try.

## Sequencing

* **Stage one `44acacfc…` is pinned to stage two `565644be…6bf6f`** (attempt 26's root, which
  `native/boot/omarchy-root-manifest.json` names since the attempt-26 handoff) **and built for boot042's
  Image `0b6df395…b69c`.** Any new job 045 image needs a stage-one rebuild. Every job 045 rebuild gets the
  Claude Code release current at build time, so its digest changes. A new Image needs one too. Rebuild
  with `rm -f virtualization/jobs/049-two-stage-boot/out/stage2/ramroot.cpio.zst; WAIT=1
  virtualization/jobs/049-two-stage-boot/host-run.sh` (it clones job 045's current image; for another
  Image, `KTREE`, `KERNEL` and `IMAGE_SHA` in `out/job.env`), then re-pin `ramroot-manifest.json` and
  rerun both `run-qemu.sh` runs. `run-qemu.sh` now refuses to boot a stage one whose pin names another
  image than the manifest, and takes what it expects of stage two from that pin.
* The first build (`4e2ea2a3…`, for attempt 25's root `b8eae454…66c1` on boot041) and its VM runs stay
  in job 049's `out/runs/` (`stage1-4e2ea2a3/`, `full-2026-10-19/`, `full-2026-10-19b/`,
  `timing-2026-10-19/`).
* Before the two-stage boot, `ramroot-manifest.json` pinned job 039 run 33 for boot035 (`67f25732…`),
  which the current packages refuse anyway (Image mismatch). The re-pin keeps the record's shape
  (`test_ramroot.py` 45 PASS). The launcher's `--profile` help still describes the ramroot profile as
  "job 039's RAM root"; stage one is built from that layer, and `launch.py` is unchanged by rule.
* Draft checklist: `tools/m1n1-client/stage-b-two-stage-draft.md`, now on boot042 and attempt 26's root
  (the attempt number with the handoff, after attempt 26).
* Job number: the attempt-26 session had also created a `049-…` job directory, later the same afternoon;
  it renames its own to `050-boot042-keyboard` (agreed between the sessions on 2026-10-19), and this job
  keeps 049.

## Files

* New: `omarchy-arm64/two-stage/` (README, packages, overlay), `virtualization/jobs/049-two-stage-boot/`
  (README, `host-run.sh`, `run.sh`, `run-qemu.sh`, `make-test-overlay.py`, `fdt-fb.py`, `test-overlay/`),
  `tools/m1n1-client/m5-stage2.py`, `test_m5_stage2.py`, `stage-b-two-stage-draft.md`, this report.
* Changed: `tools/m1n1-client/m5-ssh-config` (the `m5s` entries), `native/boot/ramroot-manifest.json`
  (the re-pin, now to `44acacfc…`). The rebuild's `out/job.env` (boot042's Image and tree) is under the
  job's ignored `out/`.
* Not changed: `native/boot/launch.py`, job 045, job 039 (its working-tree key fix is not mine; stage
  one's build installs the keys the same way).

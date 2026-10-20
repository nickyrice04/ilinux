# Job 049: the two-stage boot (stage one, and the switch to the Omarchy root), in a VM

Builds stage one of the two-stage boot (`omarchy-arm64/two-stage`) and tests the whole path in a VM:
stage one boots, the M1's `tools/m1n1-client/m5-stage2.py` sends the Omarchy root (job 045's image)
over the USB byte pipe, stage one checks it against its pin, unpacks it and soft-reboots into it, and
the Omarchy desktop comes up. Current pair and evidence:
`native/boot/attempt27-two-stage-validation.md`. Earlier design and tests:
`native/boot/two-stage-boot-2026-10-19.md`.

| Step | Where | Needs | Command |
|---|---|---|---|
| Build stage one and the test base | workspace Arch VM | the `vm` lock, about 2 minutes with warm caches | `WAIT=1 POLL=10 host-run.sh` |
| Boot test | Mac, QEMU with Hypervisor.framework, one vCPU, 32 GiB | the build's outputs and job 041's test Image, **no lock** | `run-qemu.sh` (about 12 minutes: three refusals, two of them whole transfers, then the switch); `NEGATIVES=0 run-qemu.sh` (about 6 minutes: the timing run, the image sent as soon as the link is up) |
| Offline tests | Mac | nothing | `python3 -I tools/m1n1-client/test_m5_stage2.py` |
| The launcher offline with a stage-one pin that waits in `build/` | Mac, a scratch copy of `native/boot/` (the repository's files are not written) | the record, the package, stage one | `launcher-check.sh RECORD PACKAGE STAGE1` |

* `host-run.sh` first makes `out/stage2/ramroot.cpio.zst` an APFS clone (no copy) of job 045's image;
  `run.sh` checks it against `native/boot/omarchy-root-manifest.json`, unpacks it once into a tmpfs
  the way stage one does (the entry count and the RAM it takes go into stage one's pin), builds the
  root, prunes and checks it (job 039's `prune.sh` and `elf_page_check.py`, a private-key scan) and
  packs `out/stage1.cpio.zst` (zstd `--ultra -22 --long=27`). Then, test only, a second root gets
  python3, the Linux `usb-pipe` and a VM key pair: `out/build/test-base.cpio.zst`. Optional
  `out/job.env`: `KTREE`, `KERNEL`, `IMAGE_SHA` (another Image), `MANIFEST` (stage two's pin record as
  `/mnt/ilinux/…`, when it waits in `build/` for its handoff; `host-run.sh` and `run-qemu.sh` read the same
  line, and the M1's copy in the test overlay is that record), `FAST=1` (zstd -3). `run.sh`'s
  defaults are boot041's Image; the current stage one is for boot042's, so its `out/job.env` names the
  packaged Image (`/mnt/ilinux/build/native-boot042/verified/Image`, `0b6df395…b69c`) and job 050's
  tree (`/var/tmp/ilinux-boot042/linux`), as job 045's does.
* `run-qemu.sh` boots `out/stage1.cpio.zst` exactly as built, followed by the test base and an
  overlay built from the working tree (`make-test-overlay.py`: `test-overlay/` plus the M1's
  `m5-stage2.py`, `m5-ssh-config` and the manifest), on job 041's `Image-test` (boot041's Image with
  `dummy_hcd` and the generic usb-serial driver built in; its release, `7.1.9-g863199d8b4a3-dirty`, is
  boot042's too, so stage two's boot042 modules are the running release's), with the launcher's
  RAM-root arguments plus m1n1's append, and a device tree (`fdt-fb.py`: the Mac has no `dtc`) with the
  M5's root compatible and a `/chosen` simple-framebuffer that simpledrm drives. Stage two is on a
  read-only virtio disk.
* The test, in the guest (dummy_hcd makes the kernel the host of its own gadget, job 046's approach):
  `m1-stage1.sh` plays the M1 against stage one: the link, then three attempts stage one must refuse
  and survive (an image it is not pinned to, a session that ends after 64 MiB, the pinned size with
  one byte changed), each checked in the session, the journal and the panel's state, with a capture;
  then `m5-stage2.py` with the real image. Stage one verifies, unpacks, runs the test hook (it adds
  `stage2-probe.sh` to the unpacked root, as job 045's boot test appended its probe to the same image)
  and soft-reboots. The probe follows Omarchy to the desktop (job 045's definition of ready: the
  shell answers its IPC ping and Hyprland has mapped layer surfaces), asks for a capture, then checks
  stage two's own link as attempt 25's M1 used it (the journal on interface 0 up to this boot's host
  key, SSH as `omarchy` with the `m5o` entry).
* Markers `ILINUX049-<NAME> <seconds since kernel start>` on the virtio console; captures, the markers,
  both stages' journal, the logs and a timeline (`timeline-summary.txt`) in `out/vm/` (`out/` is ignored
  by Git; earlier runs in `out/runs/`). The verdict is `run-qemu.sh: PASS`; `run-qemu.sh check` judges
  the last run again. What the verdict expects of stage two (size, SHA-256, entry count, build-info)
  comes from stage one's own pin (`out/stage2-pin.txt`) and the build's unpack record
  (`out/build/stage2-unpacked.txt`), copied into `out/vm/` at each boot; the run refuses to start when
  stage one's pin and `native/boot/omarchy-root-manifest.json` name different images. Stage two's
  failed units: `FAILED_UNITS` (default: attempt 26's root, `omarchy-provision-hardware` and `ufw`, as
  job 045's VM test found). Do not edit `run-qemu.sh` while it runs (bash reads it as it goes).
* After the switch, the test queries Hyprland's effective repeat delay (1000 ms),
  parses the shell's runtime layout to require weather absent, and checks that
  the keyboard unit is enabled but skips the VM's absent MTP controller. It also
  requires one online CPU. `IMAGE-FIXES` is a required verdict marker; these
  checks do not establish native keyboard initialization or hardware frequency.
* The test also logs in to stage one as `omarchy` (the VM key's public half in a root-owned 0644
  `/etc/ssh/authorized_keys.d/omarchy`, job 039's layout) before the refusals.
* Timing: both stages share one kernel, so the markers are one time line from the kernel's start (the
  VM's "handoff"). In the VM the M1's half of the transfer (ssh, usb-pipe, the host side of
  `dummy_hcd`) runs on the same single vCPU as the M5's half, so the VM's pipe is several times slower
  than the M5's measured 25 MB/s; the report keeps VM and native numbers apart.

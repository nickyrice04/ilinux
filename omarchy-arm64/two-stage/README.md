# Two-stage boot: stage one

The Omarchy root (VM job 045, 2.43 GB compressed) takes about 8 minutes to upload through m1n1's
USB proxy at 5.2 MB/s. Attempt 25 measured the Linux USB link at about 25 MB/s each way over SSH
on the byte pipe. The two-stage boot uses that link for the big image:

1. **Stage one**, this layer: a small RAM root (59.6 MB compressed, about 20 s of upload) that the
   launcher's existing `ramroot` profile uploads through m1n1. It brings up job 039's USB link
   (one gadget per controller: the journal on interface 0, `sshd -i` on the byte pipe of
   interface 1) and shows its state on the panel.
2. **Stage two**: the M1 sends the Omarchy root over SSH on that pipe
   (`tools/m1n1-client/m5-stage2.py`). Stage one checks its size and SHA-256 against the pin it
   was built with, unpacks it into a tmpfs at `/run/nextroot` and soft-reboots into it. systemd
   stops stage one's services (the gadget goes away cleanly) and starts the Omarchy root's own
   systemd. If anything fails, stage one stays up, says why on the panel, in the journal and in
   the M1's session, and waits for the next attempt.

VM job [`049-two-stage-boot`](../../virtualization/jobs/049-two-stage-boot/README.md) builds and
tests it.

| Path | What |
|---|---|
| `packages.txt` | Job 039's base and link packages without its desktop group, plus `libarchive` (bsdtar unpacks stage two) and `kbd` (console fonts) |
| `overlay/usr/local/lib/ilinux/ilinux-stage2` | `receive SIZE SHA256` (the M1's SSH command: offer check, transfer, SHA-256), `switch` (unpack, checks, soft-reboot), `status` |
| `overlay/usr/local/lib/ilinux/stage1-screen` | The panel: kernel time, USB link per controller, this boot's SSH host key, the pin, the transfer's progress and rate, the last attempt's outcome (red with the reason when it failed), the recent events; a red line when the state still says switching a minute later (the soft-reboot fell back to stage one) |
| `overlay/etc/systemd/system/` | `ilinux-stage2-switch.service` (the unpack, started by `receive` so it finishes even if the session ends; its `SuccessAction=soft-reboot` is the switch), `ilinux-stage2-udev-cleanup.service` (clears the udev database during the soft-reboot, after udevd stops, as an initrd does before switch-root: otherwise the Omarchy root never starts its gadget), `ilinux-stage1-screen.service` (tty1), `ilinux-ssh-hostkey.service` and its `sshd-tty` drop-in (the host key is made at every boot; its fingerprint goes to the journal tagged `ilinux-ssh-hostkey`), a drop-in for job 039's gadget unit (`SuccessExitStatus=SIGKILL`: its stream ends with SIGKILL by design, and a "failed" state would be carried into stage two) |

Job 039's RAM-root layer (`../ram-root/overlay`: `/init`, `usb-gadget.sh`, its units and udev rule,
sshd's drop-ins, `/etc/environment`) is copied unchanged under this one; its desktop files are
present but not enabled (stage one boots to `multi-user.target`). The build adds:

* `/etc/ilinux/stage2-pin`: `size`, `sha256` and `image_sha256` from
  `native/boot/omarchy-root-manifest.json`, plus `entries` and `unpacked_bytes_16k`, measured by
  unpacking stage two in the build VM exactly as `switch` does;
* `/etc/ssh/authorized_keys.d/{root,omarchy}`: the operator's public keys, root-owned 0644 (job 039's
  fix: sshd opens the file as the user who logs in).

Nothing in the image is private: no SSH host key (made at boot), no private key, no password
(root and omarchy are locked), an empty machine-id (made at boot).

## The checks, in order

| Step | Check | On failure |
|---|---|---|
| Offer | The M1's `SIZE SHA256` equal the pin | refused before a byte is read (exit 3) |
| Admission | no other transfer or switch (a lock); memory available ≥ image + unpacked root + 1 GiB | refused (exit 3) |
| Transfer | at most `size + 1` bytes are read into a tmpfs of its own, hashed on the way in | a short or long stream: failed (exit 4) |
| Image | byte count and SHA-256 equal the pin; zstd magic | failed (exit 4) |
| Unpack | `bsdtar -x -p --numeric-owner` into a tmpfs at `/run/nextroot` (the size limit rootfs would have had); entry count equals the pin; `/init`, `/usr/lib/systemd/systemd` and an os-release exist | failed (exit 5); the tmpfs is unmounted |
| Switch | the switch unit ends; its `SuccessAction=soft-reboot` stops stage one's units (the gadget goes cleanly), the udev database is cleared, and systemd switches into `/run/nextroot`. systemd 262 refuses `switch-root` outside an initrd; soft-reboot switches a running system into `/run/nextroot` when it holds an OS tree (and stays in stage one when it does not) | still in stage one a minute later: a red line on the panel |

## How the result differs from a one-stage boot of the same image (attempts 25 and 26)

The same image runs; how it starts differs:

* PID 1 is the Omarchy root's systemd, started by stage one's systemd through the soft-reboot
  (`--switched-root --deserialize`), not by the image's `/init`. That `/init` only bind-mounts the
  kernel's rootfs onto itself so the root is an ordinary mount (bubblewrap needs `pivot_root`); a
  tmpfs at `/run/nextroot` already is one.
* `/run` is carried over (by soft-reboot's design), so `journalctl -b` shows both stages, and the
  journal on interface 0 starts with stage one's records. The udev database in it is cleared before
  the switch, so devices are found anew, as at a fresh boot.
* systemd counts one soft-reboot (`SoftRebootsCount=1`) and logs "Soft-reboot finished" instead of
  "Startup finished".
* Stage one's own files stay in the kernel's rootfs, unreachable (about 340 MB).

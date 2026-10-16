# Omarchy-style RAM root (roadmap Phase 3, steps 3–4)

A zstd-compressed initramfs that is the whole system. It holds:

* an Arch Linux ARM userspace with systemd and seatd;
* Hyprland on `simpledrm` with Mesa llvmpipe;
* waybar and foot;
* Omarchy's configuration;
* SSH on the USB network link.

VM job [`039-omarchy-ram-root`](../../virtualization/jobs/039-omarchy-ram-root/run.sh) builds
and boot-tests it. Results are in
[`../ram-root-report-2026-10-15.md`](../ram-root-report-2026-10-15.md).

| Path | What |
|---|---|
| `packages.txt` | The 27 packages asked for; pacman resolves the rest (304 in all) from the official Arch Linux ARM repositories |
| `prune.sh` | Removes what a RAM root never reads (documentation, translations, headers, Python, Perl and others) |
| `overlay/init` | PID 1: bind-mounts the initramfs root onto itself, so `pivot_root` and bubblewrap work, then execs systemd |
| `overlay/etc/systemd/system/` | `ilinux-desktop.service` (Hyprland on tty1 with seatd, started without the ambient `CAP_WAKE_ALARM` pam_systemd gives local sessions, which stops bubblewrap and so glycin's image loaders), `ilinux-sshd.socket` (10.66.0.2:22 only), `ilinux-usb-gadget@.service` |
| `overlay/etc/systemd/network/`, `overlay/etc/udev/rules.d/` | USB links keep the names `usb<N>`; the cabled one gets 10.66.0.2/24 and a DHCP server; udev starts one gadget per device-mode controller |
| `overlay/usr/local/` | Gadget script (CDC-EEM by default), desktop-ready probe, status screen |
| `home/.config/` | RAM-root edition of Omarchy's `hypr/hyprland.lua`, plus `hypr/ramroot.lua` (session programs, scale 2) and a waybar configuration |

USB ports, the same as boot036's Stage-B init (`kernel/experiments/usb-gadget/init.c`), so one
M1 command reaches both stages. Any other UDC (VM tests) is port 4 onwards, in sorted order.

| UDC | Port | M5 MAC (`dev_addr`) | M1 MAC (`host_addr`) | M5 link-local |
|---|---|---|---|---|
| `2a2280000.usb` (`usb-drd0`) | 1 | `02:69:6c:69:6e:01` | `02:69:6c:69:6f:01` | `fe80::69:6cff:fe69:6e01` |
| `2aa280000.usb` (`usb-drd1`) | 2 | `02:69:6c:69:6e:02` | `02:69:6c:69:6f:02` | `fe80::69:6cff:fe69:6e02` |
| `382280000.usb` (`usb-drd2`) | 3 | `02:69:6c:69:6e:03` | `02:69:6c:69:6f:03` | `fe80::69:6cff:fe69:6e03` |

The cabled port also has 10.66.0.2/24 and serves 10.66.0.10–13 by DHCP. `bcdDevice` is
0x0039 here and 0x0036 in Stage-B.

Build (on the host; this takes the `vm` lock):

```bash
virtualization/jobs/039-omarchy-ram-root/host-run.sh
```

Output: `virtualization/jobs/039-omarchy-ram-root/out/ramroot.cpio.zst` (gitignored). It holds
the image's SSH host key, so do not publish it.

Before building, put operator public keys in
`virtualization/jobs/039-omarchy-ram-root/out/authorized_keys` (gitignored). Alternatively,
append a small cpio with `/etc/ssh/authorized_keys.d/root` to the image at delivery time,
zero-padded to a 4-byte boundary.

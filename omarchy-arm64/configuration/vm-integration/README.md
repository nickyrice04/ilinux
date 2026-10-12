# Omarchy VM integration (guest side)

These files make Omarchy-in-a-VM behave like Omarchy on the metal. Each one
uses a host channel that the launcher provides
(`virtualization/qemu/run-omarchy-gpu.sh`). Install paths match the tree
below.

| File (install path) | What it does |
|---|---|
| `bin/ilinux-host-bridge` → `/usr/local/bin/` | Reads key=value lines from virtio-serial port `org.ilinux.host`. The host side is `tools/bin/ilinux-host-agent`, which the launcher starts and ties to QEMU; it needs no root. Each value is whitelisted. `capacity`, `status` and `ac` drive the kernel `test_power` battery, so UPower and the bar show the Mac battery. `time` steps the clock when it is more than 2 s off: the guest counter stands still while the Mac sleeps, and the agent resends the time the moment it wakes. `tz` follows the Mac's time zone, e.g. when travelling. Data flows host → guest only |
| `systemd/ilinux-host-bridge.service` → `/etc/systemd/system/` | Starts the bridge when the port exists. Restarts it if it exits |
| `bin/ilinux-timezone-sync` + `systemd/ilinux-timezone-sync.service` | Applies the Mac's time zone at boot. The launcher passes `ilinux.tz=<Area/City>` from macOS `/etc/localtime`; the value is validated against `/usr/share/zoneinfo` |
| `bin/ilinux-clipboard-agent` → `/usr/local/bin/` + `systemd/user/ilinux-clipboard.service` → `/usr/lib/systemd/user/` (`systemctl --global enable`) | Clipboard sharing with macOS. It speaks the SPICE vdagent clipboard protocol over port `com.redhat.spice.0` to QEMU's `qemu-vdagent` (QEMU's Cocoa UI owns the Mac pasteboard) and uses wl-clipboard in the session. UTF-8 text is fetched on demand: nothing crosses until someone pastes. Text taken from the Mac is not echoed back. Python stdlib only |
| `etc/udev/rules.d/70-ilinux-vdagent.rules` | `uaccess` on the vdagent port, so only the logged-in desktop user can open it |
| `etc/systemd/resolved.conf.d/30-ilinux-vm-dns.conf` | Quad9 with opportunistic DNS-over-TLS. The NAT DNS proxy doesn't answer resolved (D-015) |
| `etc/NetworkManager/conf.d/90-ilinux-vm-dns.conf` | `dns=none`, so NetworkManager doesn't hand resolved the dead NAT DNS |
| `etc/environment.d/60-ilinux-vm-vulkan.conf` | `MESA_VK_WSI_DEBUG=nowlts` for the session (Hyprland runs under `systemd --user`). Mesa aims Vulkan FIFO commits at commit-timing timestamps derived from presentation feedback, which has no real vblank behind it in the VM: vkcube ran at 93 fps on the 120 Hz output, 119.5 fps without them. VM only |
| `etc/mpv/mpv.conf` | `hwdec=vaapi`, `gpu-api=opengl`, `vo=gpu` and `profile=fast`, so plain `mpv file` decodes on the Mac's media engine through the VideoToolbox-backed VA-API driver (D-029). VA-API frames reach mpv through EGL dmabuf interop on OpenGL; on Vulkan (Venus) the interop fails and mpv decodes in software. The fast profile cut 4K60 playback from 7.3 W to 3.9 W (F-048); `profile=high-quality` in `~/.config/mpv/mpv.conf` restores mpv's high-quality scaling. Codecs the host doesn't offer fall back to software. VM only |
| `etc/sddm.conf.d/20-ilinux-vm-autologin.conf` | Autologin into the `omarchy.desktop` session (D-016). Delete it to get the SDDM password prompt back |

## Push into a running VM

```bash
tools/vmpush.py virtualization/run/console.sock <file> <guest path> [mode]
```

Pushes are sha256-verified.

## VM package set (D-026)

**Kernel:** `linux-ilinux-vm` (`omarchy-arm64/kernel/linux-ilinux-vm`).

* Build it in the guest with `makepkg`, then
  `pacman -U --overwrite '/usr/lib/modules/7.1.6-vzrun2/*' linux-ilinux-vm-*.pkg.tar.xz`.
* Copy `/usr/share/linux-ilinux-vm/Image-*` to the host (job 019 shows
  how). The launcher boots `images/alarm/Image-7.1.6-vzrun2-pkg`.

**Not installed in the VM:** `limine`, `limine-mkinitcpio-hook`,
`limine-snapper-sync`, `efibootmgr` and `linux-aarch64`.

* With direct kernel boot there is no bootloader or initramfs to maintain.
* Limine's pacman hook failed on every systemd, firmware or module update.
* snapper (btrfs snapshots) stays.


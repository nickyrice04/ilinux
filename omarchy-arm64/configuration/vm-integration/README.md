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
| `etc/systemd/resolved.conf.d/30-ilinux-vm-dns.conf` | Quad9 with opportunistic DNS-over-TLS. The NAT DNS proxy doesn't answer resolved (D-015) |
| `etc/NetworkManager/conf.d/90-ilinux-vm-dns.conf` | `dns=none`, so NetworkManager doesn't hand resolved the dead NAT DNS |
| `etc/sddm.conf.d/20-ilinux-vm-autologin.conf` | Autologin into the `omarchy.desktop` session (D-016). Delete it to get the SDDM password prompt back |

## Push into a running VM

```bash
tools/vmpush.py virtualization/run/console.sock <file> <guest path> [mode]
```

Pushes are sha256-verified.

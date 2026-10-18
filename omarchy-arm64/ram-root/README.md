# Omarchy-style RAM root (roadmap Phase 3, steps 3–4)

A zstd-compressed initramfs that is the whole system. It holds:

* an Arch Linux ARM userspace with systemd and seatd;
* Hyprland on `simpledrm` with Mesa llvmpipe, started through Hyprland's own `start-hyprland`
  supervisor;
* waybar and a foot terminal that shows a live status screen: the time since kernel start in
  block digits, CPU use, memory, the tail of the kernel log, and the single-thread results of
  the repository's portable C benchmarks, run once after the desktop is ready;
* Omarchy's configuration;
* SSH over the USB link (a bulk-only byte pipe by default, or a network function), with web access through the M1's proxy.

VM job [`039-omarchy-ram-root`](../../virtualization/jobs/039-omarchy-ram-root/run.sh) builds
and boot-tests it. Results are in
[`../ram-root-report-2026-10-15.md`](../ram-root-report-2026-10-15.md) (the first build, run
30, attempt 19) and [`../ram-root-report-2026-10-16.md`](../ram-root-report-2026-10-16.md)
(the status-screen build, run 33, for attempt 20).

| Path | What |
|---|---|
| `packages.txt` | The 27 packages asked for; pacman resolves the rest (304 in all) from the official Arch Linux ARM repositories |
| `prune.sh` | Removes what a RAM root never reads (documentation, translations, headers, Python, Perl and others) |
| `overlay/init` | PID 1: bind-mounts the initramfs root onto itself, so `pivot_root` and bubblewrap work, then execs systemd |
| `overlay/etc/systemd/system/` | `ilinux-desktop.service` (Hyprland on tty1 with seatd through `start-hyprland`, started without the ambient `CAP_WAKE_ALARM` pam_systemd gives local sessions, which stops bubblewrap and so glycin's image loaders), `ilinux-usb-gadget@.service` (one gadget per controller: the journal port and the SSH byte pipe), `ilinux-sshd-tty@.service` (`sshd -i` on that pipe), `ilinux-sshd.socket` (10.66.0.2:22, for the network functions) |
| `overlay/etc/systemd/network/`, `overlay/etc/udev/rules.d/`, `overlay/etc/ssh/sshd_config.d/`, `overlay/etc/environment` | udev starts one gadget per device-mode controller; with a network function, USB links keep the names `usb<N>` and the cabled one gets 10.66.0.2/24 and a DHCP server; sshd is key-only, bounds pipe sessions and sets the proxy environment; `/etc/environment` sets it for PAM sessions |
| `overlay/usr/local/` | Gadget script (two bulk-only `gser` ports by default: the journal and the SSH byte pipe; ECM, NCM or EEM with an optional CDC-ACM journal port selectable in `/etc/default/ilinux-usb-gadget`), the desktop-ready probe, the status screen (`ilinux-status`) and the benchmark runner (`ilinux-bench`). The job adds `cpubench` and `membench` here, built from `benchmarks/src/` |
| `home/.config/` | RAM-root edition of Omarchy's `hypr/hyprland.lua`, plus `hypr/ramroot.lua` (session programs, scale 2, the status terminal's font size) and a waybar configuration |

The status screen (`ilinux-status`) redraws once a second, changed rows only, and forks
nothing per tick: the time since kernel start as 3×5 block digits with CPU use beside it,
memory and load, then the benchmark rows, then the last lines of the kernel log (`journalctl
-k -f`; the user is in `systemd-journal`), which the quiet console hides. `ilinux-bench` runs
once, detached, when `/run/ilinux/desktop-ready` appears: eleven steps under `timeout`
(cpubench `freq`, `fma`, `fma_asm`, `intmix`, `sort`, `sgemm` at 3 reps of 0.5 s, `syscall`,
`pingpong`; membench `stream` on 3 × 128 MiB, `fault` on 1 GiB, `latency` up to 128 MiB), about
75 s natively, results in `/run/ilinux/bench/results.jsonl` in the repository's JSON format. A
step that fails or hangs is recorded and the next one runs; the screen then reads "failed".
The binaries are built in the job VM with `gcc -O3 -march=armv8.4-a -pthread` (recorded in
`/usr/share/ilinux/bench-build.txt`), a fixed target the M5 and QEMU's TCG both run; no SME
kernel is compiled in.

USB: one gadget per device-mode controller, ports and USB strings as in the Stage-B inits
(`kernel/experiments/usb-gadget/init.c`), so one M1 command reaches both stages. Any other UDC
(VM tests) is port 4 onwards, in sorted order. `bcdDevice` is 0x0039 here, 0x0036 in boot036's
Stage-B, 0x0038 in boot038's and 0x0139 in boot039's. By default (`FUNCTION=gser` in
`/etc/default/ilinux-usb-gadget`) each gadget has two instances of the kernel's generic serial
function in one configuration, both vendor class 0xff with one bulk-IN and one bulk-OUT endpoint,
no interrupt endpoint (attempt 18's CDC-ACM + CDC-ECM device stopped answering control transfers
right after macOS set the configuration) and no class requests:

| Interface | Function | M5 side | M1 side |
|---|---|---|---|
| 0 | `gser.log` | the journal, written only by this side (`/dev/ttyGS<n>`) | the bulk-log reader (`tools/m1n1-client/bulk-log-reader-brief.md`) |
| 1 | `gser.ssh` | `ilinux-sshd-tty@ttyGS<n+1>.service`: `sshd -i` on the raw port, one connection at a time | `tools/m1n1-client/usb-pipe` as ssh's ProxyCommand (`tools/m1n1-client/usb-ssh-link.md`) |

macOS binds no driver to either interface; the M1's tools open them from user space. Web access
comes through the M1: its localhost-only HTTP CONNECT proxy (`tools/m1n1-client/connect-proxy.py`)
is reverse-forwarded by the ssh session to 127.0.0.1:3128 here, where `/etc/environment` and
sshd's `SetEnv` (`sshd_config.d/25-ilinux-usb-pipe.conf`) already point `HTTPS_PROXY` at it, so
pacman, mise, curl and Claude Code reach the web with no change to the M1's network settings.
Bulk endpoints carry no hang-up, so sshd bounds a connection that never authenticates
(LoginGraceTime 45 s) and a session whose client vanished (ClientAlive 15 s x 3); the port is
free again within about 45 s. VM job [`046-usb-ssh-pipe`](../../virtualization/jobs/046-usb-ssh-pipe/run.sh)
proves the whole chain with dummy_hcd (`native/boot/usb-ssh-link-2026-10-16.md`).

`FUNCTION=ecm` (or `ncm`, `eem`) selects the earlier design instead: a CDC network function
(`usb<N>` from u_ether, 10.66.0.2/24 with a DHCP server, SSH on 10.66.0.2:22 from
`ilinux-sshd.socket`), with `ACM=1` adding a CDC-ACM journal port in front of it. macOS 26.0.1
loads ECM and ACM but has no usable EEM driver (attempt 17).

| UDC | Port | M5 MAC (`dev_addr`, network functions) | M1 MAC (`host_addr`) | M5 link-local |
|---|---|---|---|---|
| `2a2280000.usb` (`usb-drd0`) | 1 | `02:69:6c:69:6e:01` | `02:69:6c:69:6f:01` | `fe80::69:6cff:fe69:6e01` |
| `2aa280000.usb` (`usb-drd1`) | 2 | `02:69:6c:69:6e:02` | `02:69:6c:69:6f:02` | `fe80::69:6cff:fe69:6e02` |
| `382280000.usb` (`usb-drd2`) | 3 | `02:69:6c:69:6e:03` | `02:69:6c:69:6f:03` | `fe80::69:6cff:fe69:6e03` |

Build (on the host; this takes the `vm` lock):

```bash
virtualization/jobs/039-omarchy-ram-root/host-run.sh
```

Output: `virtualization/jobs/039-omarchy-ram-root/out/ramroot.cpio.zst` (gitignored). It holds
the image's SSH host key, so do not publish it.

Operator public keys: `virtualization/jobs/039-omarchy-ram-root/out/authorized_keys`
(gitignored) when present, else the M1's own public key
`kernel/experiments/usb-gadget/authorized_keys`, as the Stage-B initramfs ships it; the build
authorizes them for `root` and `omarchy`. Alternatively, append a small cpio with
`/etc/ssh/authorized_keys.d/root` to the image at delivery time, zero-padded to a 4-byte
boundary (the launcher's `--operator-key` does this). Only public keys enter the image.

# Omarchy-style RAM root (roadmap Phase 3, steps 3–4)

A zstd-compressed initramfs that is the whole system. It holds:

* an Arch Linux ARM userspace with systemd and seatd;
* Hyprland on `simpledrm` with Mesa llvmpipe, started through Hyprland's own `start-hyprland`
  supervisor;
* waybar and a foot terminal that shows a live status screen: the time since kernel start in
  block digits, CPU use, memory, the tail of the kernel log, and the single-thread results of
  the repository's portable C benchmarks, run once after the desktop is ready;
* Omarchy's configuration;
* SSH on the USB network link.

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
| `overlay/etc/systemd/system/` | `ilinux-desktop.service` (Hyprland on tty1 with seatd through `start-hyprland`, started without the ambient `CAP_WAKE_ALARM` pam_systemd gives local sessions, which stops bubblewrap and so glycin's image loaders), `ilinux-sshd.socket` (10.66.0.2:22 only), `ilinux-usb-gadget@.service` |
| `overlay/etc/systemd/network/`, `overlay/etc/udev/rules.d/` | USB links keep the names `usb<N>`; the cabled one gets 10.66.0.2/24 and a DHCP server; udev starts one gadget per device-mode controller |
| `overlay/usr/local/` | Gadget script (CDC-ACM journal port plus CDC-ECM network by default; NCM or EEM selectable in `/etc/default/ilinux-usb-gadget`), the desktop-ready probe, the status screen (`ilinux-status`) and the benchmark runner (`ilinux-bench`). The job adds `cpubench` and `membench` here, built from `benchmarks/src/` |
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

USB ports, the same as boot036's and boot038's Stage-B init (`kernel/experiments/usb-gadget/init.c`),
so one M1 command reaches both stages. Any other UDC (VM tests) is port 4 onwards, in sorted
order. As in boot038, each port's gadget has two functions in one configuration:
* CDC-ACM: a serial port that carries the journal, read-only, with no login on it. On the M5
  it is `/dev/ttyGS<n>`; on macOS it is a `/dev/cu.usbmodem*` device.
* CDC-ECM: the network. macOS 26.0.1 has no usable EEM driver (attempt 17).

| UDC | Port | M5 MAC (`dev_addr`) | M1 MAC (`host_addr`) | M5 link-local |
|---|---|---|---|---|
| `2a2280000.usb` (`usb-drd0`) | 1 | `02:69:6c:69:6e:01` | `02:69:6c:69:6f:01` | `fe80::69:6cff:fe69:6e01` |
| `2aa280000.usb` (`usb-drd1`) | 2 | `02:69:6c:69:6e:02` | `02:69:6c:69:6f:02` | `fe80::69:6cff:fe69:6e02` |
| `382280000.usb` (`usb-drd2`) | 3 | `02:69:6c:69:6e:03` | `02:69:6c:69:6f:03` | `fe80::69:6cff:fe69:6e03` |

The cabled port also has 10.66.0.2/24 and serves 10.66.0.10–13 by DHCP. `bcdDevice` is
0x0039 here, 0x0036 in boot036's Stage-B and 0x0038 in boot038's.

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

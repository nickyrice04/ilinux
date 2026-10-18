# SSH and web access for the M5 over the USB bulk-only link, proven end to end in a VM

2026-10-16 and 17, M5 side session. **Proven in a VM on the second Mac; nothing has run on the M5's
hardware.** The native test is attempt 22, after attempt 21 (boot039) has shown that the bulk-only path
works. Labels: Confirmed / Likely / Hypothesis / Unknown. "Confirmed" means confirmed in a VM or by a
test on the Mac, never on the M5.

## Summary

* **One byte pipe is enough.** Attempt 18 showed that macOS stops talking to the gadget once
  interrupt endpoints are in play, and macOS has no driver for the bulk-only functions it would
  bind. So the link stays bulk-only and driverless: the RAM root's gadget gets a **second `gser`
  interface** next to boot039's kernel-log interface, and `sshd -i` runs on it, one connection at a
  time. On the M1, a small user-space tool built from the macOS SDK (**`usb-pipe`**, IOUSBHost) is
  ssh's ProxyCommand: it opens that interface and relays stdin and stdout to the bulk endpoints. Web
  access comes through the same session: the M1 runs a localhost-only HTTP CONNECT proxy in
  standard-library Python (**`connect-proxy.py`**), reverse-forwarded to `127.0.0.1:3128` on the M5,
  where the RAM root already sets `HTTPS_PROXY` for every session. pacman (through curl), mise and
  Claude Code use it as they are. **Nothing on the M1's network settings changes**: no Internet
  Sharing, no interface, no route.
* **Proof in a VM (job 046), full test PASS:** one `dummy_hcd` kernel is both the M5 and its host. udev
  starts the gadget; OpenSSH `sshd -i` runs on the raw serial port in a network namespace that has only
  its own loopback; `ssh` with `usb-pipe` as ProxyCommand logs in by key; an HTTPS page that only the
  M1 side can reach (a name only the M1's proxy resolves) is fetched on the M5 side through the
  reverse-forwarded CONNECT proxy, while the same fetch made directly fails; 2 MiB each way arrive
  intact; a wrong key is refused; an abandoned handshake and a vanished client each free the port by
  themselves; 25 sessions in a row succeed on a busy single CPU.
* **The M5 side is the RAM-root overlay** (`omarchy-arm64/ram-root/overlay`): `usb-gadget.sh` with
  `FUNCTION=gser` (default; the ECM and ACM design stays selectable), the new
  `ilinux-sshd-tty@.service`, `sshd_config.d/25-ilinux-usb-pipe.conf` (login and keepalive bounds,
  `SetEnv` with the proxy variables), `/etc/environment`, and the proxy environment for the desktop
  session. Job 039 authorizes the M1's public key for `root` and `omarchy` when no operator key file
  is given, and builds `usb_f_serial` for trees that have it as a module.
* **The M1 side is under `tools/m1n1-client/`:** `usb-pipe/` (relay and banner logic in portable C,
  the IOUSBHost backend in Objective-C, a build script), `connect-proxy.py`, `m5-ssh-config`,
  `usb-ssh-link.md` (how to build, check and run it) and the tests `test_usb_pipe.py` and
  `test_connect_proxy.py`. `bulk-log-reader-brief.md` gained the attempt-22 section (accept
  `bcdDevice 0x0039`, never open interface 1).
* **What the VM cannot show** is the M1's half on real hardware: how macOS treats a two-interface
  vendor-class device, the IOUSBHost reads and writes on the real dwc3 cores, and the link's speed.
  The macOS backend builds with the SDK alone and passes a static check, but only the attempt can run it.

## Design

| Choice | Reason | Label |
|---|---|---|
| A second `gser` interface rather than a network function | No interrupt endpoint (attempt 18), no class requests, no macOS driver needed; `USB_CONFIGFS_SERIAL=y` and `USB_F_SERIAL=y` are already in the boot036 and boot039 Image | Confirmed (config, VM) |
| `sshd -i` on the raw port, one connection per sshd | The pipe has no connection semantics; inetd mode gives one session per process and the unit restarts it. No getty, no login on the port | Confirmed (VM) |
| sshd starts with the gadget and sends its banner at once | Bulk IN queues it until the M1 reads; the tool forwards ssh only after it has seen the banner, so the M5's sshd never sees a client that talks to a dead instance | Confirmed (VM) |
| The tool drops stale bytes before the banner | Bulk endpoints keep what an earlier session left. The tool takes the last `SSH-` line after the device has been quiet 400 ms and drops what precedes it | Confirmed (relay tests) |
| `RestartSec=100ms`, and an input drain before sshd starts that waits for 0.2 s of quiet (at most 2 s) | The next sshd's banner must follow the last one's end inside the tool's quiet window. The client's last packets (its disconnect) can reach the port after the previous sshd has exited: queued while the port was closed (the gadget queues no OUT requests then) or still being sent by the host. The drain drops them, so the new sshd starts at a clean boundary; the M1's tool sends nothing before it has seen the new banner, which comes after the drain. It logs how many bytes it dropped. **Two bugs in earlier versions:** a fixed 50 ms window was too short (the lite test with the server ended at once failed 3 of 3), and `timeout dd` never read at all, because the unit's process is a session leader, opening the port made it the controlling terminal, and GNU `timeout` moves its child to a background process group, where a read from the controlling terminal stops with SIGTTIN. The fix is `timeout --foreground` (probed: `dd` returns after 0.21 s with it, hangs to the cap without it) | Confirmed (probe, lite test with the server killed at once, stress). In 33 server starts of the full stress run the drain found nothing to drop: with the SIGHUP fix the live server gets the tail itself |
| **`usb-pipe` ignores SIGHUP and SIGPIPE once it is relaying** | At exit `ssh` writes its last packets (channel close, disconnect) to the ProxyCommand and then sends it SIGHUP. A pipe has no hang-up, so those packets are all that tells the M5's sshd the client left. With the default SIGHUP, a busy CPU lost them: **4 of 25 back-to-back sessions worked**, and each loss cost 80 to 90 s of recovery. With the signals ignored and the flush finished first: **25 of 25** | Confirmed (VM stress; mutation check) |
| `LoginGraceTime 45`, `ClientAliveInterval 15`, `ClientAliveCountMax 3` | A client that gave up before authenticating (a wrong key, Ctrl-C), or vanished after it, leaves its sshd waiting. The grace time frees the port after 45 s, the keepalives after about a minute. Measured with the OpenSSH default of 120 s: a refused key blocked the port for the full 120 s. `LoginGraceTime 0` would leave a pre-auth session stuck for good | Confirmed (VM) |
| The log port streams `journalctl -b -f -n all` | `-f` alone starts at the last ten lines; the M1 reader wants the boot from its start | Confirmed (VM: 512 lines, the first the kernel's "Booting Linux") |
| Reads without a timeout on the M1 | The gadget sets `req->zero` when its write buffer drains and sends packets of at most the endpoint's size, so every burst ends with a short or zero-length packet and a 16 KiB IN request completes at the end of each burst | Confirmed in the source (`u_serial.c`); the IOUSBHost behaviour itself is the attempt's |
| Proxy variables by `SetEnv`, `/etc/environment` and the desktop unit's `EnvironmentFile` | `SetEnv` reaches every SSH command; `EnvironmentFile` gives Hyprland and every terminal started from it the same variables; `/etc/environment` serves PAM logins. `NO_PROXY=localhost,127.0.0.1,::1` keeps local traffic local | Confirmed for SSH; the desktop path is by construction and is exercised by job 039's next boot test |
| Proxy on loopback only; loopback and private destinations refused by default | The M5 reaches the web through the M1, not the M1 itself or its LAN | Confirmed (unit tests) |
| `ssh` config in the repository, keys in `build/control/` | No change to the M1's `~/.ssh`; the private key never leaves the M1; only public keys in Git and images | by construction |

### The pipe tool

`usb-pipe` (macOS, `tools/m1n1-client/usb-pipe/`) matches `1d6b:0104`, `bcdDevice 0x0039`,
configuration 1, interface 1, class `0xff` and the product string "iLinux J716c control channel, port
N" (all fixed in the code), checks the registry properties before opening anything, opens the
interface with `IOUSBHostObjectInitOptionsNone`, checks its descriptors (two interfaces in the
configuration; interface 1 with exactly one bulk IN and one bulk OUT), copies the two pipes and
relays: one thread reads stdin and writes bulk OUT (10 s timeout), the main thread reads bulk IN
(16 KiB, no timeout) and writes stdout. It never sends a control request, selects no alternate
setting, clears no stall, and never opens the device or interface 0 (`test_usb_pipe.py` fails if the
source names those calls). Exit codes: `usb-ssh-link.md`.

The relay, the banner sync and the exit rules are one C file (`relay.c`) with three backends: IOUSBHost
(macOS), a serial device opened raw (`--tty`, the Linux stand-in, which reads the real gadget interface
through the generic usb-serial driver) and an inherited descriptor (`--fd`, the offline tests). The VM
therefore runs the relay code that runs on the M1; only the IOUSBHost calls wait for the attempt.

### The proxy

`connect-proxy.py`: `CONNECT host:port` (ports 443 and 80 by default) and absolute-URI `http://`
requests (forwarded with `Connection: close`, for mirrors), one thread per connection, a 1 MiB backlog
cap per direction, half-close both ways, a 300 s idle timeout, at most 64 connections, one log line per
connection. It refuses to listen on anything but loopback.

## Evidence

All on the second Mac (Virtualization.framework, one vCPU) with job 041's test kernel (`dummy_hcd`, generic
usb-serial), unless noted. `dummy_hcd` moves packets in software: its speeds say nothing about the real link.

| Test | Needs | Result |
|---|---|---|
| **Full** (`run-vz.sh`): the VM-built base root (112 signed Arch Linux ARM packages, 379 MiB) plus the working tree's overlay; systemd 262, udev, OpenSSH 10.6, Python 3.14 | the base from the `vm` lock (23 s with a warm cache) | **PASS**, 124 s; with the 25-session stress, 150 s |
| **Partial** (`run-vz-ramroot.sh`): job 039's own RAM-root image (run 33) plus the overlay; no Python, so no proxy | nothing | **PASS**, 123 s. Adds a 1 MiB TLS fetch through a second reverse forward, certificate checked |
| **Lite** (`lite/run-lite.sh`): the real `usb-gadget.sh` and the Linux `usb-pipe` with Dropbear behind an `nc` bridge in a busybox initramfs | nothing | **PASS** in both modes (the server ended politely, and killed at once, the harsh case for the input drain): 12 sessions, 2 MiB each way |
| Unit tests on the Mac, Python 3.9: `test_connect_proxy.py` 16, `test_usb_pipe.py` 15, `test_make_overlay.py` 7 | nothing | **PASS** |
| The same two Python suites on Linux in the job VM, Python 3.14, gcc 16 | the `vm` lock | **PASS** |
| `native/boot`: `test_ramroot.py` 30, `test_control_channel.py` 10, `test_launcher.py` 37, `test_boot039_package.py` 8, `test_kconfig_guard.py` 7 | nothing | **PASS** |

What the full test showed, in order: udev started `ilinux-usb-gadget@dummy_udc.0`; two `gser` functions,
`bcdDevice 0x0039`, `gser.log` = ttyGS0 (interface 0), `gser.ssh` = ttyGS1 (interface 1), state
`configured`; the host sees two vendor interfaces with bulk endpoints only and binds them as
`/dev/ttyUSB0` and `/dev/ttyUSB1`; the journal port delivered 512 lines in 6 s; `ssh` logged in after
0.5 s with the banner seen after 0.4 s; the session had `HTTPS_PROXY`, `https_proxy` and `NO_PROXY`; the
fetch of `https://web.test:8443/` returned the page through the forward (the proxy logged
`CONNECT web.test:8443 -> 127.0.0.1:8443 1780>/2611< ok`) and the same fetch with the proxy bypassed failed
with "Failed to connect"; 2 MiB each way took 1.1 s each with equal SHA-256; a wrong key was refused
(`Permission denied (publickey)`); the pipe worked again 45 s after that abandoned handshake (the next
session at 57 s) and 53 s after a client was killed mid-session; no `ilinux-*` unit stayed failed.

**Stress, before and after the SIGHUP fix** (25 back-to-back sessions while a busy loop holds the single
CPU, on job 039's RAM root): before, sessions 2, 4, 6 and 8 failed, each with "no SSH banner" because the
previous sshd still waited for a lost close, and each recovery took 80 to 90 s; after, 25 of 25. The new
unit test `test_ssh_exit_does_not_lose_the_last_packets` sends SIGHUP right after the last write against a
slow device: it fails 5 of 5 times with the signal handling removed and passes 5 of 5 with it.

## Findings other sessions may need

* **`ssh` hangs up its ProxyCommand at exit** (`ssh_kill_proxy_command`). Any ProxyCommand over a transport
  without a hang-up of its own must ignore SIGHUP and finish forwarding, or it drops the session's
  last packets whenever the machine is busy. Recoverable (the server's keepalives end it), but a minute each.
* **A background read from a controlling terminal stops.** A systemd service is a session leader; opening a
  serial port from its shell makes that port its controlling terminal. A helper started through GNU `timeout`
  (which gives its child a new process group) then stops with SIGTTIN on its first read. Use
  `timeout --foreground`, or no `timeout`. busybox's `timeout` has no such option and does not need it.
* **A bulk pipe cannot tell sshd that its client left,** so every case where the client goes without a
  clean disconnect is bounded only by sshd's timers. `LoginGraceTime` of OpenSSH's default 120 s is too
  long for this; 45 s is used.
* OpenSSH 10 prints `sshd -T` option names in CamelCase; a lowercase `grep` of its output found nothing and,
  under `pipefail`, ended a script silently. Names that differ only by case collide on the Mac's
  shared-folder files.
* In `ash`, a background job's stdin is replaced by `/dev/null` before its own redirections run, so
  `cmd <&0 &` reads nothing. `dropbear -i` needs a socket on stdin, `sshd -i` does not.
* Apple's unprivileged `sshd` completes key authentication and then stalls in its audit setup, so a
  full ssh session against it on macOS needs privileges; the tests stop at the authenticated handshake there.

## What the VM cannot show / still open

* **Unknown:** what macOS 26 does with a two-interface vendor-class device of `1d6b:0104` (attempts 17 and
  18 saw its composite driver select configuration 1): whether it publishes both interface nubs with no
  driver bound, and whether a user client opens each without an entitlement. Likely yes; check `ioreg` first.
* **Unknown:** the IOUSBHost reads and writes on the real cores, in particular that a 16 KiB IN request
  completes at the end of each burst (the source says it must), the write timeout of 10 s, and whether
  two user clients on two interfaces of one device coexist.
* **Unknown:** the dwc3 cores with two interfaces (IN endpoints 1 and 2, OUT 1 and 2): attempt 21's single
  interface comes first, and its TX FIFO line says whether a second IN endpoint has a sane FIFO.
* **Unknown:** throughput and latency of the real link.
* **Not reproduced:** two `Connection corrupted` lines from sshd at the end of sessions in an early run
  (data and digests were correct). They did not recur in later runs and fit the lost tail above, which is
  fixed; the stress run logged none.

## What attempt 21 needs (boot039, the M1 reading the log)

Unchanged from the handoff (`tools/m1n1-client/stage-b-instructions.md`,
`native/boot/boot039-bulk-log-2026-10-16.md`). One addition for the reader the M1 builds:
accept `bcdDevice 0x0039` next to `0x0139` and keep to interface 0, so the same binary
serves attempt 22 (`bulk-log-reader-brief.md`, last section). The M1 can also build and
test `usb-pipe` and the proxy now (`usb-ssh-link.md`, "Build" and "Offline checks"); they
are not used in attempt 21.

Attempt 21's reading decides attempt 22: the bulk path must work (the log arrives, no EP0
timeout). If it does not, the link design is not the next variable and attempt 22 waits.

## What attempt 22 needs (the RAM root on the boot039 kernel with this link)

1. **The RAM root rebuilt on the boot039 Image** (job 039, run 34 or later) with this
   overlay. Job 039's `out/job.env`:

   ```
   KTREE=/var/tmp/ilinux-boot036/linux
   KERNEL=/mnt/ilinux/build/native-boot039/verified/Image
   IMAGE_SHA=e0e531130a6f6bd7a5768393200a4c6e42f19a65c54c3deb390d53756edef3f7
   ```

   boot039's Image is boot036's byte for byte (`e0e53113…`), with the gadget stack and
   `gser` built in, so the module step builds only the QEMU test NIC's drivers. The job's
   own boot test (QEMU, the desktop, the benchmarks) must pass as for run 33; it has no
   UDC, so the USB units stay idle there, which job 046 covers. The build authorizes the
   M1's key for `root` and `omarchy` unless `out/authorized_keys` names other public keys.
2. **The pin:** `native/boot/ramroot-manifest.json` → the new image's size and SHA-256,
   `image_sha256` = `e0e53113…` (the launcher refuses a RAM root built for another Image),
   `source`, `vm_tested`. `python3 -I native/boot/test_ramroot.py` (30) must pass. No change
   to `launch.py`: the `ramroot` profile already takes any verified package.
3. **The launch:** attempts 19 and 20's command with the boot039 package:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot039-download/ilinux-j716c-boot039 \
     --profile ramroot --ramroot build/native-intake/ramroot.cpio.zst \
     --launch --device auto --confirm BOOT-J716C-RAM-ROOT
   ```

   The boot039 package carries the Stage-B DT with the three dwc3 device-mode nodes (boot036's),
   which attempts 19 and 20 did not have; the RAM root's udev rule then starts one gadget per
   controller. The image is about 227 MB over the proxy (≈ 45 s as in attempt 20).
4. **The M1:** `usb-pipe` built from the SDK and its two test suites passed, the proxy
   started, `m5-ssh-config` in place, the reader accepting `0x0039`, and the readiness
   record with the digests (`usb-ssh-link.md`).
5. **The human:** as in every Stage-B attempt: a fresh M1 restart, the cable re-seated, the
   M1 unlocked (the accessory check), filming the whole screen, Macintosh HD afterwards.
6. **During the run** (`usb-ssh-link.md`, "During attempt 22"): the reader on interface 0
   right after the handoff; once the desktop is up, `ssh -F tools/m1n1-client/m5-ssh-config m5`;
   in the session `env | grep -i proxy`, `curl -sS -o /dev/null -w '%{http_code}\n' https://archlinuxarm.org/`,
   a timed 64 MiB transfer, `systemctl status 'ilinux-*'`. Stop at ten minutes or on a
   reset, panic or M1 panic.
7. **Reading it:**

   | M5 screen (kernel-log tail on the status screen) | M1 | Meaning |
   |---|---|---|
   | `dwc3` probes; `configfs-gadget … high-speed config #1: Bulk-only kernel log port + SSH byte pipe` on the cabled port | both interfaces in `ioreg`, the reader streams the journal, `ssh` logs in, `curl` returns `200` | **the link works**: SSH and the web from native Linux; the RAM root is a machine the M1 can reach |
   | the same | the reader streams, `usb-pipe` exits 2 or 3 | macOS published or bound interface 1 differently from interface 0: report `ioreg -p IOService -l -w0 -r -c IOUSBHostInterface` |
   | the same | `usb-pipe` reports no banner | the M5's sshd did not start on the port: `systemctl status ilinux-sshd-tty@ttyGS1` through the reader's journal stream |
   | the same | ssh logs in, `curl` fails | the forward or the proxy: the proxy log says which; `curl -v` in the session |
   | EP0 timeouts in the M1's host USB log, as in attempt 18 | nothing works | two interfaces or the second IN endpoint changed the outcome of attempt 21: compare the dwc3 TX FIFO lines of attempt 21 |

## Kernel and DT needs

None for attempt 22 beyond the boot039 package: the Image has `USB_CONFIGFS_SERIAL=y` and
`USB_F_SERIAL=y` (Confirmed, job 041's config), and the Stage-B DT has the dwc3 nodes. For
the boot034/035 trees, where the gadget stack is modular, job 039 now also builds
`usb_f_serial.ko`. No change is proposed to the boot039 session's files.

## Reproduce

```sh
WAIT=1 POLL=5 virtualization/jobs/046-usb-ssh-pipe/host-run.sh   # base root; takes the vm lock, 25 s to 6 min
STRESS=25 virtualization/jobs/046-usb-ssh-pipe/run-vz.sh        # full test, then 25 sessions on a busy CPU
virtualization/jobs/046-usb-ssh-pipe/run-vz-ramroot.sh          # partial test on job 039's image, no lock
virtualization/jobs/046-usb-ssh-pipe/lite/run-lite.sh           # lite test, no lock
```

Inputs of the final full run: `Image-test` `17b44d20…` (job 041), base root `e44c1ce9…` (114,924,370 bytes),
Linux `usb-pipe` `1d46dbde…`. Outputs are ignored by Git (`out/` holds test keys).

## Files

* M5: `omarchy-arm64/ram-root/overlay/usr/local/lib/ilinux/usb-gadget.sh`,
  `…/etc/default/ilinux-usb-gadget`, `…/etc/systemd/system/ilinux-sshd-tty@.service` (new),
  `…/etc/systemd/system/ilinux-usb-gadget@.service`, `…/etc/ssh/sshd_config.d/25-ilinux-usb-pipe.conf`
  (new), `…/etc/environment` (new), `…/etc/udev/rules.d/90-ilinux-usb.rules`,
  `omarchy-arm64/ram-root/README.md`, `virtualization/jobs/039-omarchy-ram-root/run.sh`.
* M1: `tools/m1n1-client/usb-pipe/{relay.h,relay.c,usb-pipe.h,usb-pipe.c,iousbhost.m,build.sh}`,
  `tools/m1n1-client/connect-proxy.py`, `tools/m1n1-client/m5-ssh-config`,
  `tools/m1n1-client/usb-ssh-link.md`, `tools/m1n1-client/test_usb_pipe.py`,
  `tools/m1n1-client/test_connect_proxy.py`, `tools/m1n1-client/bulk-log-reader-brief.md`
  (appended section).
* VM: `virtualization/jobs/046-usb-ssh-pipe/` (`README.md`, `run.sh`, `host-run.sh`, `run-vz.sh`, `run-vz-ramroot.sh`,
  `make-overlay.py`, `make-ramroot-overlay.py`, `test_make_overlay.py`, `lite/`, `test-overlay/`).
* This report.

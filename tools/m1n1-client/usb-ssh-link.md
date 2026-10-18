# SSH and web access for the M5 over the USB byte pipe: the M1 side

2026-10-16, M5 side session. For attempt 22 (the RAM root on the boot039 kernel). Labels:
Confirmed / Likely / Hypothesis / Unknown. **Nothing here has run against the M5's hardware;**
the VM proof and the offline tests are in `native/boot/usb-ssh-link-2026-10-16.md`.

## What the M5 presents

Per USB-C port, the RAM root's gadget (`omarchy-arm64/ram-root/overlay/usr/local/lib/ilinux/usb-gadget.sh`)
is one device, `1d6b:0104`, **`bcdDevice 0x0039`**, product "iLinux J716c control channel, port N",
one configuration ("Bulk-only kernel log port + SSH byte pipe") with two interfaces of the
kernel's generic serial function `gser`, each vendor class `0xff` with one bulk-IN and one
bulk-OUT endpoint, no interrupt endpoint and no class requests (as boot039's single interface):

| Interface | M5 side | M1 side |
|---|---|---|
| 0 | `gser.log`: the journal, written only by the M5 (`journalctl -b -f`, CR LF lines) | the bulk-log reader of `bulk-log-reader-brief.md`, which must also accept `bcdDevice 0x0039` (see its last section) |
| 1 | `gser.ssh`: a raw byte pipe with `sshd -i` on it, one connection at a time (`ilinux-sshd-tty@ttyGS<n>.service`) | **`usb-pipe`**, ssh's ProxyCommand (this document) |

macOS binds no driver to a vendor-class interface, so both tools open their interface from
user space with the SDK's IOUSBHost framework. Each opens only its own interface, never the
device (the composite driver holds it) and never the other interface.

Web access: the M1 runs a localhost-only HTTP CONNECT proxy (`connect-proxy.py`), and the
ssh session reverse-forwards `127.0.0.1:3128` on the M5 to it. The RAM root's
`/etc/environment` and sshd's `SetEnv` already point `HTTPS_PROXY`, `HTTP_PROXY` (and the
lower-case forms) at `http://127.0.0.1:3128`, so pacman (through curl), mise, curl and Claude
Code on the M5 reach the web through the M1's own network. The proxy resolves names and
opens the connections; TLS passes through it untouched. **Nothing on the M1 changes**: no
Internet Sharing, no new interface, no route, no network setting. The port on the M5 answers
only while the session is open.

## Build (the SDK only, nothing installed)

```sh
xcode-select -p && xcrun --show-sdk-path && clang --version
ls "$(xcrun --show-sdk-path)/System/Library/Frameworks/IOUSBHost.framework/Headers/IOUSBHostPipe.h"
tools/m1n1-client/usb-pipe/build.sh        # -> build/control/usb-pipe (ignored); prints its SHA-256
python3 -I tools/m1n1-client/test_usb_pipe.py
python3 -I tools/m1n1-client/test_connect_proxy.py
```

If the first two lines fail, stop and report: installing the Command Line Tools is a host
install that needs the user's approval. The tests build their own copy of the tool, run the
relay against a socket pair and a pseudo-terminal, check the macOS backend's source for
forbidden calls, and run a real `ssh` through the tool to a real `sshd -i` on a raw
pseudo-terminal (the M5's layout): on macOS an unprivileged sshd completes the key
authentication and then stalls in Apple's audit setup, so that test ends at the authenticated
handshake; the VM runs the whole session. Both suites pass on the M5 Mac (2026-10-17): 16 and 15 tests.

Sources: `tools/m1n1-client/usb-pipe/` (`relay.c` the relay and banner logic, shared with
the Linux stand-in; `iousbhost.m` the macOS backend; `usb-pipe.c` the command line),
`tools/m1n1-client/connect-proxy.py`, `tools/m1n1-client/m5-ssh-config`.

## Offline checks before the attempt

* `build/control/usb-pipe --dry-run --wait 5` with no M5 attached: prints that no interface
  matched and exits 2, having opened nothing.
* The same with m1n1's device attached (`1209:316d`): still nothing (the matching dictionary
  carries the vendor, product, `bcdDevice`, interface number, configuration and class).
* `python3 -I tools/m1n1-client/connect-proxy.py --port 0` starts and prints its port; stop it
  with Ctrl-C. It refuses `--listen 0.0.0.0`.
* Record the SHA-256 of `build/control/usb-pipe`, of the three sources and of
  `connect-proxy.py` in the readiness record.
* The M1's key `build/control/m1-control` exists (boot036); its public half is
  `kernel/experiments/usb-gadget/authorized_keys`, which the RAM-root build authorizes for
  `root` and `omarchy` (job 039, run 34 or later). The private key never leaves the M1.

## During attempt 22

1. The attempt-21 reader runs on interface 0 as before (same command), built to accept
   `bcdDevice 0x0039`. It and `usb-pipe` can run at the same time.
2. In a second terminal, from the repository root, the proxy (keep it running):

   ```sh
   python3 -I tools/m1n1-client/connect-proxy.py --log build/native-intake/attempt22-proxy.log
   ```

3. Once the M5 screen shows the desktop (the gadget binds about 5 s after the handoff, sshd
   starts with it), in a third terminal:

   ```sh
   ssh -F tools/m1n1-client/m5-ssh-config m5
   ```

   `usb-pipe` waits up to 60 s for the interface, waits for the M5 sshd's banner (dropping
   anything stale in front of it), then relays. Its lines go to
   `build/native-intake/usb-pipe.log`. The host key is recorded in `build/control/known_hosts`
   under the name `m5` on first use. With more than one M5 port cabled, use `m5-port1`,
   `m5-port2` or `m5-port3`.
4. On the M5, in that session (read-only unless noted):

   ```sh
   uname -a; cat /sys/class/udc/*/state; systemctl status 'ilinux-*' --no-pager
   env | grep -i proxy
   curl -sS -o /dev/null -w '%{http_code}\n' https://archlinuxarm.org/
   ```

   The `curl` line is the web test: `200` through the forwarded proxy. The proxy's log on the
   M1 shows one `CONNECT archlinuxarm.org:443 ... ok` line per request.
5. A timed transfer sizes the link: `dd if=/dev/zero bs=1m count=64 | ssh -F tools/m1n1-client/m5-ssh-config m5 'cat > /dev/null'`.
6. Several sessions in a row are fine (one at a time per port: sshd exits after each and the
   unit restarts it within 0.2 s). A session cut by closing the terminal leaves the M5's sshd
   until its keepalives fail (about a minute; measured 53 s); a reconnect in that window ends with "no SSH
   banner" and works on the next try. An idle sshd, and one whose client gave up before it authenticated (a wrong key, Ctrl-C), ends after
   its 45 s login grace time and is replaced at once (measured: usable again 50 s after a refused key); if the M1 connects in the 0.2 s between the two, ssh can fail with
   `kex_exchange_identification` or "Connection closed": run it again. Neither case needs any
   action on the M5.
7. The RAM root does not contain pacman, mise or Claude Code yet: it carries only the
   environment they need (the proxy variables, set for SSH sessions, PAM sessions and the
   desktop). `curl` is there, so the web test above works as it is. The installer-built Omarchy
   root is where the package tools live.

Keep the proxy log, the usb-pipe log and any M5 output local in `build/native-intake/`;
commit excerpts only after checking them for identifiers (`AGENTS.md`).

## Reading usb-pipe's exit

| Exit | Line in the log | Meaning |
|---|---|---|
| 0 | `end: ssh closed the session` | normal |
| 0 | `end: the device ended` / `the interface was terminated` | cable out, M5 reset, or the M5 removed the gadget |
| 2 | `no matching interface in N s` | no device, or `bcdDevice` is not `0x0039` (boot039 Stage-B has only interface 0 and `0x0139`), or macOS has not published the interface (the accessory check holds a new device while the M1 is locked) |
| 3 | `cannot open the interface (... exclusive access ...)` | another process has interface 1 (a second usb-pipe) or a driver bound it: `ioreg -p IOService -l -w0 -r -c IOUSBHostInterface` shows which; never seized |
| 4 | `N interfaces match` or `descriptors are not the SSH byte pipe's` | several ports cabled (use `--port`), or not the RAM root's gadget |
| 5 | `no SSH banner from the device in N ms` | nothing answered on interface 1: `ilinux-sshd-tty@ttyGS<n>` is not running on the M5, or an earlier session is still closing (up to 45 s); retry |
| 5 | `write ... not accepted within N s` | the M5 stopped reading its SSH port (sshd gone) |
| 5 | `pipe stalled` | the endpoint halted; not cleared (that would be a control request); report, the next session may work after the M5 restarts sshd |
| 1 | `writing to ssh failed` | ssh went away first |
| 6 | usage | refused before touching anything |

## Behaviour to expect

* **It outlives `ssh` by a moment.** At exit `ssh` writes its last packets to the tool and sends it SIGHUP.
  The tool ignores SIGHUP and SIGPIPE once it is relaying and finishes forwarding what `ssh` wrote, then
  ends (its log says "ssh closed the session" with the byte counts). Those last packets are the only
  thing that tells the M5's sshd the client left, so a tool that died on the signal would leave the next
  connection waiting for a minute. If the M5 is not reading its port, that last write waits at most the
  10 s write timeout.
* **One session at a time per port.** sshd exits after each session and the unit restarts it within
  0.4 s. A new `ssh` waits for the new banner (up to 20 s, `--banner-wait`).
* **A client that vanishes frees the port by itself,** after the login grace time (45 s, before
  authentication) or the keepalives (about a minute, after). The tool reports "no SSH banner" until then.
* **Run `ssh -F tools/m1n1-client/m5-ssh-config m5` from the repository root:** the config's paths
  (`build/control/...`) are relative.

## The contract (what usb-pipe never does)

It opens the matched `IOUSBHostInterface` with `IOUSBHostObjectInitOptionsNone`, copies its two
bulk pipes, reads IN and writes OUT. It never opens the `IOUSBHostDevice`, never uses the
capture or seize options, sends no control request (no `GET_DESCRIPTOR`, `SET_INTERFACE`,
`CLEAR_FEATURE`), selects no alternate setting, clears no stall, sets no idle policy, and
performs no reset or power change. The only abort it issues is on its own pending IN read
when ssh closes. `test_usb_pipe.py` fails if the source names any of those calls. The
attempt-21 reader's contract (`bulk-log-reader-brief.md`) is unchanged: it never writes.

## What remains for the live attempt (not testable here)

* **Unknown:** what macOS 26 does with a two-interface vendor-class device of `1d6b:0104`:
  attempts 17 and 18 saw the composite driver select configuration 1; whether it publishes
  both `IOUSBHostInterface` nubs with no driver bound, and whether a user client opens each
  without an entitlement (Likely yes, as for one interface). Check with `ioreg` first.
* **Hypothesis:** a 16 KiB IN read completes at the end of each M5 burst. `u_serial` ends a
  burst with a short packet or a zero-length packet when its buffer drains, so a read never
  waits for a full buffer; the VM's host side reads through Linux's usb-serial driver, not
  through this code path, so the macOS read behaviour and the write timeout (10 s) are first
  exercised on the M1.
* **Unknown:** the dwc3 cores with two interfaces (IN endpoints 1 and 2, OUT 1 and 2): attempt
  21's single-interface result comes first; its TX FIFO line says whether a second IN endpoint
  has a sane FIFO.
* **Unknown:** throughput and latency on the real link (dummy_hcd gives no timing).
* The reader and usb-pipe together on one device (two user clients): Likely fine, untested.

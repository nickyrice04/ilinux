# Job 046: SSH and web access over the USB bulk-only link, in a VM

Proves the M5's USB byte pipe (`omarchy-arm64/ram-root`, `gser.log` + `gser.ssh`) and the M1's
tools (`tools/m1n1-client/usb-pipe`, `connect-proxy.py`) end to end with `dummy_hcd`: one kernel is
both the gadget (the M5) and its host (the M1). Report: `native/boot/usb-ssh-link-2026-10-16.md`.

| Step | Where | Needs | Command |
|---|---|---|---|
| Lite test: the real gadget script, the real Linux `usb-pipe`, Dropbear as the SSH server | Mac, Virtualization.framework | job 041's outputs and the Linux `usb-pipe` from a full build, **no lock** | `lite/run-lite.sh` (about 1 minute) |
| Base root: signed Arch Linux ARM packages, `usb-pipe` for Linux, test keys and certificate | workspace Arch VM | the `vm` lock, about 6 minutes | `WAIT=1 POLL=5 host-run.sh` |
| Full test: systemd, OpenSSH `sshd -i`, the proxy, an HTTPS fetch, transfers, recovery | Mac, Virtualization.framework | the base root, **no lock** | `run-vz.sh` (about 3 minutes) |
| Offline unit tests | Mac | nothing | `python3 -I test_make_overlay.py`, `tools/m1n1-client/test_usb_pipe.py`, `tools/m1n1-client/test_connect_proxy.py` |

* `STRESS=25 run-vz.sh` (or `run-vz-ramroot.sh`) adds 25 sessions back to back while a busy loop holds the
  single CPU. It exists because the first run of the loop found that a `usb-pipe` that dies on `ssh`'s
  SIGHUP loses the end of nearly every session under load: 4 of 25 sessions worked before the fix, 25 of 25 after.
* `KILL_NOW=1 lite/run-lite.sh` ends the stand-in server the moment the client returns: the harshest case for the
  M5's input drain. `DRAINPROBE=1 run-vz-ramroot.sh` times the drain's `dd` three ways on the RAM root (it found
  that plain `timeout` stalls it: see the report).
* `USBPIPE=/path/to/usb-pipe` points the Mac-side runners at another Linux `usb-pipe` binary (the VM builds
  the one in `out/build/`, because the Mac has no Linux C toolchain).
* `run-vz.sh` appends an overlay built from the working tree (`make-overlay.py`: the RAM root's
  overlay, `test-overlay/`, `connect-proxy.py`) to the base, so the files under test change without the
  VM. Only a new package set, a new `usb-pipe` binary or new keys need `host-run.sh` again.
* The self-test is `test-overlay/usr/local/lib/ilinux-test/selftest.sh`; `run-vz.sh` judges its
  console output against a fixed list of lines. `out/` is ignored by Git; it holds test keys and the
  VM-built base. Nothing shipped is built here.
* What the full test checks: udev starts `ilinux-usb-gadget@dummy_udc.0`; the host sees one
  `1d6b:0104` device, `bcdDevice 0039`, two vendor interfaces with bulk endpoints only; the journal
  streams on interface 0; `ilinux-sshd-tty@ttyGS1` runs `sshd -i` in a network namespace with only its
  own loopback; `ssh` with the `usb-pipe` ProxyCommand logs in, sees the proxy variables, and fetches
  an HTTPS page that only the M1 side can reach through the reverse-forwarded CONNECT proxy; 2 MiB each
  way with equal digests; a wrong key is refused; a client killed mid-session is replaced after
  `ClientAlive` and the next session works.

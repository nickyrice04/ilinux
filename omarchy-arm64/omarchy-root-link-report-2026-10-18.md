# Omarchy itself with the USB link and Claude Code, for boot040: job 045 `LINK=1 CLAUDE=1 NOPASSWD=1` (VM)

2026-10-18 · VM job [`045-omarchy-installer-root`](../virtualization/jobs/045-omarchy-installer-root/run.sh)
with two new build options · the image for attempt 24
([attempt-25 checklist](../tools/m1n1-client/stage-b-instructions.md)) · follows
[the job 045 report](omarchy-root-report-2026-10-17.md) (the root, deviations 1-15) and job 046's
[USB SSH link](../native/boot/usb-ssh-link-2026-10-16.md) · nothing committed. **VM results only:
nothing here ran on the M5.** Labels: Confirmed / Likely / Hypothesis / Unknown; "Confirmed" means in
the VM, in the build or offline, never on the M5.

## Result

**Confirmed (VM): the root Omarchy's installer built, with job 039's USB link, Claude Code and
Omarchy's own passwordless-sudo grant added, boots on the exact boot040 Image and passes the link test
over dummy_hcd.** In one QEMU TCG guest
with one vCPU (job 046's approach, test-only modules for the exact Image), the M1's tools from the
working tree reached the root as built:

* **SSH as `omarchy` over the `gser` byte pipe** (interface 1), with `tools/m1n1-client/m5-ssh-config`'s
  new `m5o` entry: the session has the proxy variables; the host key ssh recorded is the one the
  root made at boot, whose fingerprint the journal carried over interface 0; the operator's key file
  is readable as the user; root has no key; sudo allows only the clock helper.
* **The clock step** (`tools/m1n1-client/m5-clock.py`): with the clock turned back two days, an HTTPS
  fetch through the proxy fails (`certificate is not yet valid`); the step sets it from the M1's clock
  in one short session (open in 0.8 s, round trips 42-66 ms under TCG) to within 1 ms by the tool's
  readback and 12 ms by the test's own check; the journal records the change.
* **HTTPS through the reverse-forwarded proxy** to a local test server (job 046's way): the page comes
  back with its certificate checked, the direct path fails, the proxy logs the `CONNECT`.
* **`claude --version`: `2.1.303 (Claude Code)` in about 1.5-2.2 s** through mise's shim (an SSH command),
  Omarchy's wrapper and a login shell (Omarchy's account dispatcher), with **no download and no
  request through the proxy**, also with mise's caches aged three days. Signed out.
* **Passwordless sudo for `omarchy`** (user-approved 2026-10-18): `sudo -n id -u` prints `0` over SSH
  and from the desktop session (a transient unit in the user's systemd manager, where Omarchy's
  programs run); Omarchy's own `omarchy-sudo-passwordless --active` reports it active from both; the
  grant is the only unrestricted rule. Omarchy's `--disable`, run in the guest's RAM copy, revoked it
  (`--active` inactive, `sudo -n` refused, the file gone), and the clock step still worked after it
  through the helper's own rule. A login without a key is refused (`Permission denied (publickey)`).
* **The desktop session has the proxy environment** (Hyprland's and Quickshell's processes, the user
  manager), and Omarchy's session ran as in job 045: desktop ready 224.4 s after kernel start (TCG),
  first run done 221.7 s, menu, Chromium (window after 20 s) and Obsidian (23 s), no core dump. The
  final run took 25.5 minutes and passed every check; the packed image's digest was unchanged after it.

**The image:** 2,434,354,327 bytes, SHA-256
`b8eae454809839abcf6e3279e028576fa8e47b835f211968dd198a33a18c66c1`, built 2026-10-19T01:25Z for
boot040's Image `a53d1d47…`; 8,810,610,345 bytes unpacked (+285 MB on attempt 22's root),
11,059,183,616 in 16 KiB pages. **Upload: 2,479,098,098 bytes (Image, image, DT) take 474.9 s at
attempt 22's measured 5.22 MB/s, against the omarchy profile's 900 s deadline** (the launcher's own
estimate: 495.8 s at 5 MB/s, 619.8 s at 4 MB/s); the 3 GiB heap leaves about 0.74 GB to spare.
Pinned in `native/boot/omarchy-root-manifest.json`; the launcher's offline run prints `RAM root PASS`.
It replaces the same build without the grant (2,434,396,211 bytes, `c5fb61d8…7853`, built 00:36Z,
kept in `out/runs/attempt24-nosudo/`), which passed the same test apart from the sudo steps.

Not shown in the VM: real USB (attempt 23 decides whether boot040's link carries data), macOS's
view of a two-interface vendor device and the M1's IOUSBHost path (the VM's M1 reads through Linux's
usb-serial tty), the Internet behind the proxy, a Claude sign-in, native timing.

## What the options add

`LINK=1`, `CLAUDE=1` and `NOPASSWD=1` in `out/job.env` (`link.sh`, called by `ramroot.sh`; `KERNEL`,
`IMAGE_SHA`, `KERNEL_NAME` and `KTREE` name boot040). Job 039's files are taken from Git at `HEAD` and
not changed; what only this root needs is in `link-overlay/`. Each is a deviation from stock Omarchy,
numbered on from the job 045 report's table (rows 16-24 there):

| # | Kind | Addition | Why |
|---|---|---|---|
| 16 | added | Job 039's USB control channel: `usb-gadget.sh`, `ilinux-usb-gadget@.service`, `90-ilinux-usb.rules`, `/etc/default/ilinux-usb-gadget` (`FUNCTION=gser`). Per device-mode controller one gadget, `1d6b:0104`, `bcdDevice 0x0039`, two bulk-only `gser` interfaces: the journal on 0, a raw SSH byte pipe on 1, no interrupt endpoint | The M5's only way to the second computer; the M1's bulk-log reader and `usb-pipe` read them |
| 17 | added | sshd on the pipe: job 039's `ilinux-sshd-tty@.service` (`sshd -i` on the raw port, one connection at a time) and its drop-ins `20-ilinux-ram-root.conf` (key-only) and `25-ilinux-usb-pipe.conf` (LoginGraceTime 45 s, ClientAlive 15 s × 3, `SetEnv` with the proxy) | Omarchy enables no SSH server; this one listens on nothing but the pipe |
| 18 | added | The SSH host key made at each boot (`ilinux-ssh-hostkey.service`, ed25519, before sshd through a drop-in for job 039's unit); its fingerprint to the journal | The image holds no private key; the M1 records a new key after every boot (`build/control/known_hosts-omarchy`, cleared before each) and can check it against the journal |
| 19 | added | The operator's public key for `omarchy`: `/etc/ssh/authorized_keys.d/omarchy`, **0644**, from `out/authorized_keys` when present, else the M1's committed `kernel/experiments/usb-gadget/authorized_keys`, as job 039 does. Root gets none | Key-only logins as the desktop user, where the agents run. sshd reads the file as that user, so it must be readable by it (below) |
| 20 | added | `/etc/environment` (job 039's, replacing the root's empty one): `HTTPS_PROXY`, `HTTP_PROXY` and the lower-case forms at `http://127.0.0.1:3128`, `NO_PROXY` for loopback | The M1's CONNECT proxy, reverse-forwarded by its SSH session. pam_env sets them for the SDDM autologin session and SSH logins; the user manager reads the file through systemd's `99-environment.conf` link, so the desktop session has them too |
| 21 | added | The clock helper `/usr/local/lib/ilinux/set-clock` and one sudo rule for it (`/etc/sudoers.d/ilinux-clock`: `omarchy`, no password, no arguments), in the style of Omarchy's own narrow `NOPASSWD` rules | No clock source in this path (no RTC driver, no route for NTP): every boot starts wrong and TLS fails. The M1 sends its clock over SSH right after connecting |
| 22 | added | Claude Code 2.1.303, installed at build time by running Omarchy's own wrapper once (`~/.local/bin/claude --version`: `MISE_MINIMUM_RELEASE_AGE=0 mise use -g --quiet claude`, mise's `aqua:anthropics/claude-code`); `~/.config/mise/config.toml` gains `claude = "latest"` as on first use | `claude` starts on the M5 without a first-use download. Signed out: no credentials, no token, no account state |
| 23 | changed | mise's download store left out (`~/.cache/mise/downloads-cas`, 127,194,588 bytes: the `claude-linux-arm64.tar.gz` the binary came from) | A second, compressed copy of the binary that the RAM root would hold in memory and the M1 upload at every boot |
| 24 | changed | Passwordless sudo for `omarchy`, **user-approved 2026-10-18** (`NOPASSWD=1`): Omarchy's own permanent grant as `omarchy-sudo-passwordless permanent` writes it (`enable_locked` in Omarchy's settings package): `/etc/sudoers.d/99-omarchy-permanent-nopasswd-1000`, root:root 0440, exactly `omarchy ALL=(ALL) NOPASSWD: ALL` and nothing else (its `--active` and `--disable` match the whole file), checked with `visudo`. The build checks it is the only unrestricted grant. Row 21's clock rule stays, so the clock step survives a revocation | Agents inside Omarchy need sudo for pacman, loading modules and driver work, and the image has no password. The root is RAM-only, offline except through the M1's relay, and SSH takes only the operator's key. Reversible with Omarchy's own `--disable` (until the next boot: the grant is in the image); boot cleanup and the settings package's hook remove only timed grants (`99-omarchy-nopasswd-*`). Omarchy's bar shows its red passwordless-sudo indicator while the grant is on |

What the image holds that must stay private: no SSH host key, private key, pacman keyring, password
or token; the M1's public key; the build's machine-id (as before). `~/.claude` exists, holding only
Omarchy's agent skills (`skills/`), which `omarchy-provision-user` installs. The build scans the root's
text files under `/etc`, `/home`, `/root`, `/usr/local`, `/var`, `/opt` and `/srv` for PEM or OpenSSH
private keys (a whole-line BEGIN marker with base64 lines after it) and stops on any: none. (npm's
documentation quotes the marker inside example strings; the first, looser scan stopped on those.)

## The VM test (`LINK=1`, stage 4)

`boot-test.sh` adds `link-test.sh`'s files to the test overlay (appended to the image, never in it)
and the probe runs `ilinux045-link-test` once the desktop has settled:

* **Test only, for the exact Image:** `dummy_hcd.ko` and `usbserial.ko` (with the generic driver,
  which the tree leaves out), built against boot040's read-only tree (`/var/tmp/ilinux-boot036/linux`,
  whose Image is `a53d1d47…`) as job 039 builds its modules; vermagic `7.1.9-g863199d8b4a3-dirty SMP
  preempt mod_unload aarch64`, equal to the Image's.
* **The M1's side, from the working tree:** the Linux `usb-pipe` (the same relay as on macOS, its
  `--tty` backend), `connect-proxy.py`, `m5-clock.py`, and `m5-ssh-config`'s `m5o` entry with the
  test's paths. Job 046's HTTPS server and its drop-in that gives sshd a network namespace with
  loopback alone, so the proxy is the only way out. A VM-only key, put in `~omarchy/.ssh/authorized_keys`
  at test time; the image's own file keeps the operator's key and is checked as the user reads it.
* **The clock:** both sides share one clock in the VM, so the test turns it back two days (the M5
  starts wrong) and gives `m5-clock.py` the true time on the monotonic clock as the M1's.

| Step | Final run (with the grant) | The same build without the grant, and the iteration |
|---|---|---|
| Gadget, sshd, host key, host's view | as before; this boot's host key `SHA256:MH7z…LWYQ`, made 52 s after boot | `ilinux-usb-gadget@dummy_udc.0` active, `ttyGS0`/`ttyGS1`, `1d6b:0104` `bcdDevice 0039`, two vendor interfaces, bulk only |
| Journal on interface 0 | 1,627 lines in 1.1 s, the boot's host-key fingerprint among them | 1,615-1,622 lines in 1.1-1.2 s |
| SSH as `omarchy` | 1.1 s; `HTTPS_PROXY`, `https_proxy`, `NO_PROXY` set | 1.2 s, the same |
| Before the clock step | `curl: (60) … certificate is not yet valid` | the same |
| Clock step | 2.0 days behind; set within a 53.1 ms round trip; check 9.9 ms behind (36.4 ms); the test's own check −20 ms; journal `moved 172800 s` | 2.0 days → 0.7-1.1 ms by the tool, −12 ms by the test |
| HTTPS through the proxy | page returned; direct: `Failed to connect`; `CONNECT web.test:8443 -> 127.0.0.1:8443 … ok` | the same |
| `claude --version` ×3, caches fresh / aged 3 days | 1.6-2.2 s each, `2.1.303`, versions unchanged, 0 proxy requests | 1.3-1.6 s each, the same |
| Signed out | no `~/.claude/.credentials.json`, no account in `~/.claude.json` | the same |
| sudo | the grant root:root 440, Omarchy's exact rule, the only unrestricted one; `sudo -n id -u` → `0` over SSH and from the desktop session; `--active` active from both | without it: `sudo -n true` refused, the clock helper alone allowed |
| `--disable` (guest RAM only) | `Passwordless sudo has been DISABLED`; `--active` inactive, `sudo -n true` refused, the file gone; the clock step again: 1.0 day → −11 ms | — |
| Key-only | a login without a key: `Permission denied (publickey)`; the next session after 48.7 s (the refused handshake waits out LoginGraceTime) | — |
| Desktop environment | Hyprland, Quickshell and the user manager carry the proxy | the same |
| Sessions | 15 logins as `omarchy`, 16 banners; link test 81.9 s | 9-12 logins |

## Findings

1. **sshd reads `AuthorizedKeysFile` as the user it logs in** (OpenSSH, `auth2-pubkey.c`:
   `user_key_allowed2` opens it under `temporarily_use_uid`). A root-owned 0600 file therefore
   refuses that user. Job 039 writes `/etc/ssh/authorized_keys.d/omarchy` 0600, so its `omarchy`
   logins would be refused (Likely, from the code; job 046 tested `root` only). Job 045 writes 0644;
   the test confirms the user can read it. Job 039 is unchanged here: a follow-up.
2. **Claude Code 2.1.303 is a 285,335,616-byte native binary** (mise's aqua backend, from
   `claude-linux-arm64.tar.gz`). Its loadable segments map on 16 KiB pages and it links no
   page-size-bound allocator (job 039's ELF check); it ran on the build VM's 16 KiB kernel and in the
   guest. **mise keeps the downloaded tarball** (127 MB) in `~/.cache/mise/downloads-cas`: left out
   (deviation 23).
3. **mise does not ask the web before starting an installed `latest` tool**, with its caches fresh or
   aged three days: no request reached the proxy from the shim, Omarchy's wrapper or the dispatcher.
   As none was even attempted, a reachable web on the M5 should change nothing (Likely): `claude`
   starts without a download; a newer release comes with `mise up`.
4. **Omarchy's root resolves names through systemd-resolved, which stalled 30 s on `web.test` in the
   VM** (`Resolving timed out`), for the test's M1 stand-in that shares it. The test gives that
   stand-in its own `nsswitch.conf` (`hosts: files`); on the real M1 macOS resolves. On the M5 the
   proxy resolves every name for programs that use it; a program that resolves a name itself first
   could stall the same way (Hypothesis).
5. **A Linux usb-serial port opens with echo on**, so the bytes the M5's sshd has queued (its banner)
   were echoed back before `usb-pipe` made the port raw; that sshd failed (`Bad packet length`,
   `0x0D0A5353` = its own `"\r\nSS"`), in one of the two runs that reached SSH before the fix. Only
   the VM's stand-in has a tty in between (the M1's `usb-pipe` uses IOUSBHost); the test makes the
   port raw once and starts sshd afresh.
6. The desktop on boot040 is job 045's on boot035: ready 186.9-224.4 s after kernel start under TCG
   in six boots (job 045's boot035 run: 194.8 s), 14,014-14,126 MiB in use when settled, the same
   failed units (`ufw`, `linux-modules-cleanup`, `omarchy-provision-hardware`'s last step, the user's
   `xdg-document-portal`) and no failed `ilinux-` unit.
7. **Omarchy's permanent grant must be the file's only line**: its `--active` and `--disable` read the
   whole file and match `^<account> ALL=(ALL) NOPASSWD: ALL$`, so a comment would make Omarchy treat the
   grant as foreign. Stock Arch `/etc/sudoers` carries `# %wheel ALL=(ALL:ALL) NOPASSWD: ALL` commented
   out; the build's "only unrestricted grant" check skips comment lines.

## What will differ on the M5

* **The link itself** is boot040's question (attempt 23): attempt 21's DMA fault stopped the first
  bulk stream after 36,909 bytes. Two interfaces add a second IN and OUT endpoint per port (Unknown
  on the M5's dwc3).
* **The starting clock:** Likely days or months behind (systemd's build date). Timers that run on
  calendar time (`man-db`, `shadow` and others) may all start once the clock jumps forward
  (Hypothesis): a minute of extra CPU on the one core.
* **Claude Code online:** its own updater may try to update it in the background once it runs
  signed in (Unknown under mise). The sign-in itself goes through the proxy; the link and the M1's
  browser are untested together.
* **Time to desktop:** job 045's estimate holds (40-70 s natively); the image is
  18.5 s longer to upload than attempt 22's.

## Reproduce

With the install on the work disk (job 045's), `out/job.env`:

```sh
LINK=1
CLAUDE=1
NOPASSWD=1
KERNEL_NAME=boot040
KERNEL=/mnt/ilinux/build/native-boot040/verified/Image
IMAGE_SHA=a53d1d47467480d4b56d87c7b1365e9a5c28fd9ee9e5f0164a3e734f85526ad9
KTREE=/var/tmp/ilinux-boot036/linux
ZSTD_FINAL="--ultra -22 --long=27"
VARIANTS=0
```

then `virtualization/jobs/045-omarchy-installer-root/host-run.sh` (the `vm` lock, about 25
minutes: the root, about 11 minutes of zstd, the boot test). `LINKCHECK=1` instead prints the facts
the build depends on (PAM stacks, sudoers, sshd, mise's `claude` entry, the work disk, `KTREE`).
Each rebuild downloads Claude Code again and gives a new digest; `RETEST=1` boot-tests the packed
image after checking its digest. The work disk stays the 10 GiB image (about 1.7 GB free before
the build).

## Evidence

Under the ignored `virtualization/jobs/045-omarchy-installer-root/out/`, never in Git:

* `ramroot.cpio.zst` and `.sha256`: the image above. The attempt-22 image (`d00ba156…`) with its
  records moved to `runs/attempt22/`.
* `deviations.tsv` (28 lines), `build/`: `link-files.txt` (every file the link added, with digests),
  `sshd-T-omarchy.txt` and `sshd-effective.txt` (sshd's effective settings for `omarchy`),
  `authorized-keys-fingerprints.txt`, `claude-install.log`, `claude-mise.txt`, `mise-config.diff`,
  `home-new.txt` (what the install added to the home), `claude-elf-16k-check.txt`,
  `private-contents.txt`.
* `test/`: the final run (`summary.txt`, `results/link-test.log` with every step and the M1 tools'
  output, the journal, captures). `linkmods.txt`, `link-inputs.txt`: the test-only modules and the
  M1 files under test, with digests.
* `runs/attempt24-nosudo/`: the same build without the grant (`c5fb61d8…7853`), with its records and
  test. `runs/iter1*`: the iteration with zstd -3 (`85d3981e…`, superseded): its build, the first link
  test (the resolver stall), the passing retest, the echo race, the passing retest with aged caches.
* `linkcheck/`: the facts `LINKCHECK=1` recorded before the build.

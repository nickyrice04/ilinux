# Stage B attempt 25 (Omarchy itself with the USB link and Claude Code, on boot041): the first data from the M1 to the M5 works; SSH, the clock step, web access through the M1 and a signed-in Claude Code on the M5 all ran for 16 minutes

2026-10-19 (handoff 12:52:29 AM Eastern, 2026-10-19T04:52:29.303Z). **One RAM attempt consumed. Controller PASS, no host
panic.** boot041's package with the launcher's `omarchy` profile and the job 045 Omarchy root built with `LINK=1 CLAUDE=1
NOPASSWD=1`. The human did not film the run (their choice); a 6.6 s phone clip of both screens at about +7.5 min arrived
afterwards. The evidence is the M1-side capture and logs, that clip and the answer the human pasted from Claude Code. The link ended
at **+958.2 s** when the human powered the M5 off or restarted it (confirmed in chat), so the run is **not** a stability result
beyond 16 minutes.

* **Controller:** exit 0 in 476.492 s (upload 473.0 s for 2,479,098,050 bytes = 5.24 MB/s), handoff `04:52:29.303Z`, every gate
  PASS.
* **The link (M1 side, read-only unless noted):** the gadget enumerated at **+19.45 s** (`1d6b:0104`, `bcdDevice 0x0039`, 480 Mbps);
  macOS held it behind "transport restrictions" until the human accepted the accessory prompt (configuration 1 selected at +22.66 s).
  **Both interfaces were published** (macOS bound no driver to either): interface 0 was opened by the bulk-log reader (+22.7 s) and
  interface 1 by `usb-pipe`, two user clients on one device at once.
* **First data from the M1 to the M5 (bulk OUT), through SSH over interface 1:**
  * **the clock step PASSED** (exit 0): session open in 0.5 s; the M5's clock read 2026-09-24, **24.2 days behind**; set; read back
    **1.3 ms ahead** of the M1's, round trip 5.7 ms;
  * a session as `omarchy`: host key equal to the journal's fingerprint, `sudo -n id -u` = 0, `omarchy-sudo-passwordless --active`
    exit 0, `claude --version` = `2.1.303 (Claude Code)`, and **HTTP 200 from `https://archlinuxarm.org/` through the M1's proxy**;
  * **throughput:** 16.8 MB to the M5 in 0.63 s and 16.8 MB from it in 0.66 s, timed from sshd's banner to the end of the session,
    about **25 to 27 MB/s each way** (one run each, including SSH's key exchange, teardown and crypto on the M5's single CPU);
  * the human's interactive session ran **12 minutes** (720.3 s) and moved 72.1 MB to the M5 and 1.9 MB from it.
* **Claude Code signed in and answered a prompt on the M5** (the human did the sign-in; nothing about it is recorded). Through the M1's
  proxy: **118 connections, all `ok`, none refused**; 71.8 MB down, 1.5 MB up.
* **Journal (interface 0, 15 min 58 s):** 642,026 bytes, 5,349 intact records; **no `BUSERR`, `translation fault`, `nobody cared`,
  oops, call trace, segfault or out-of-memory line**; the six DART instances probed as in attempt 24 (v2.4).
* Fresh policy/default checks: **NOT CHECKED.** No retry or settings change.

## Reviewed inputs and controller execution

* M5 handoff `38e91fb` (image work `33c37c8`); M1 readiness `d1ecb81` (the launch ran on that commit, clean tree, record at 0 attempts
  before the launch). The boot041 package is attempt 24's, unchanged (archive `ab49e307…4d28`).
* The image (`build/ramroot045-link/ramroot.cpio.zst`, never committed): 2,434,354,327 bytes, SHA-256 `b8eae454…66c1`, equal to the pin;
  it was read from the image itself before the run (see the readiness entry in `coordination.md`).
* One invocation through `build/native-intake/run-attempt25.py` (attempt 22's wrapper with four lines changed), started detached so
  that no tool timeout could cut the 8-minute upload:

| Item | Result |
|---|---|
| Invocation count | 1 |
| Start / handoff UTC | 2026-10-19T04:44:33.028 / 04:52:29.303 |
| Elapsed / exit | **476.492 s / 0** (`Uploading…` +2.33 s, `RAM upload complete…` +475.32 s, handoff +476.27 s) |
| Package, mode | PASS; `RAM root PASS: 2,434,354,327 bytes…`; `Mode: LIVE RAM LAUNCH` (`--profile omarchy`, deadline 900 s) |
| Boot arguments | `console=tty0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 pd_ignore_unused clk_ignore_unused quiet` (m1n1 appends `idle=nop arm64.nowfxt`) |
| Primary interface, target | PASS: 1209:316d, CDC data interface 1; t6050, boot021 marker, no started secondaries |
| GPIO ADT, board/framebuffer, DAPF layout and correction | PASS (221 pins / 7 groups, exclusions 5,6,7,112,141; 96-byte correction) |
| Final hardware DT, framebuffer descriptor | PASS (16-byte descriptor, readback verified) |
| kboot reply / USB close | PASS |

* **M1 host:** freshly restarted (uptime 947 s at the handoff; the launch waited for the CPU to settle: 90% idle, load 7 and falling),
  `caffeinate -di` running, the read-only gate passed on the first try, no panic report during or after the run (the newest on file is
  attempt 15's). The reader is the unchanged attempt 21 to 24 binary (`77677ee3…`); `usb-pipe` was built from the committed source
  (SHA-256 `94b33396…bffe`). The localhost web proxy, the handoff watcher and a read-only monitor ran as helpers.

## Media and method

**No film of the run** (the human chose not to record). **One short clip arrived after it**: `ShowingforcedBrowserSignIn.MOV`, 6.6 s,
1920×1080, 30 fps, 10 MB, filmed about 1:00 AM (+7.5 min); it was untracked in the repository root and was moved into the ignored
inbox before any commit. It pans from the M1's screen to the M5's. **At 0.5 s (the M1):** the app's terminal tab with Claude Code's
welcome screen (`v2.1.303`), its printed sign-in link ("Browser didn't open? Use the url below to sign in (c to copy)") and the
`Paste code here if prompted >` prompt; above it, at the M5's bash prompt, two `command not found` lines before `claude` ran: a stray
line the human typed (not recorded here) and the typo `cluade`, so **no PATH or image problem**. **At 6.0 s (the M5):** the Omarchy
desktop with Chromium full-screen on Claude's "Log in" page (Continue with Google, Continue with Apple, an e-mail field) and two
first-run notifications at the top right ("Setup Wi-Fi", "Learn Keybindings"). The clip shows the sign-in link and the human's
e-mail address on screen: it is kept local and never committed. The interactive session ran in a terminal tab of the Claude desktop
app, opened by the M1 agent and used by the human; the M1 agent never read that tab. The human pasted Claude Code's answer to one
prompt. **Nothing about the sign-in (link, code, account) is recorded**; one journal line group carried the sign-in page's address
(see below) and its query string was redacted in the local capture. Time base: journal seconds are the M5's journald receipt times,
with journal 0 about 0.23 s after the handoff (`T0`). The review frames were deleted.

## M5 journal and link, literal observations

| Journal s (T0 + s) | Observation |
|---:|---|
| 16.99 | the first records (journald starts; the kernel messages before it are replayed with this time): `systemd` reached userspace after "16.465s (kernel)" |
| 17.0 | six `apple-dart <base>.iommu: t8110-class DART v2.4: PARAMS 0x8e311020 0x30111083 0x2a2a0204 0x00010010 … fault IRQ 43/43/44/44/45/45` lines, each with `v2.2 fault layout … (before reset)` and `initialized` (18 lines, as attempt 24) |
| 17.94 | `ilinux-ssh-hostkey`: this boot's host key, `256 SHA256:… ilinux-m5-boot (ED25519)` (equal to the key `ssh` recorded) |
| 19.10 / 19.22 / 19.20 | `usb-gadget.sh: gadget … bound to … as port 1 / 2 / 3: Bulk-only kernel log port + SSH byte pipe; log on /dev/ttyGS0, sshd on /dev/ttyGS1` (ports 2 and 3: `ttyGS4`/`ttyGS5`, `ttyGS2`/`ttyGS3`); `Started SSH on the USB byte pipe /dev/ttyGS1/3/5` |
| 25.84 to 26.03 | `Reached target Multi-User System`, `Started Simple Desktop Display Manager`, `sddm: Session "…omarchy.desktop" selected`, `Reached target Graphical Interface`, **`Startup finished in 16.465s (kernel) + 9.564s (userspace) = 26.030s`** |
| 27.43 / 30.63 | Hyprland declared ready (`uwsm`); `omarchy-shell` (Quickshell) logging: the desktop session is up about 27 to 31 s after the handoff |
| 76.28 | `ilinux-clock: set from the M1 over SSH: was 2026-09-24T23:47:03Z, now 2026-10-19T04:53:45Z, moved 2092002 s` |
| 77, 378, 679 | **`archlinux-keyring-wkd-sync.service`** starts right after the clock jump, fails in under a second (`status=101`, `gpg: error reading key: Server indicated a failure`, about 1,195 lines each) and is restarted every 300 s: 3,593 lines, 483 KB, **75% of the journal's volume** |
| 391.3 | **`systemd-run … /usr/bin/uwsm-app -- /usr/bin/chromium "https://claude.com/cai/oauth/authorize?…"`**: Claude Code, started from the SSH session, launched Chromium on the M5's desktop with its sign-in page (query withheld) |
| 19 restarts each | `ilinux-sshd-tty@ttyGS3` and `@ttyGS5` (the unused ports 3 and 2): the idle sshd ends after its 45 s login grace time and is restarted, three lines each time (`status=3/NOTIMPLEMENTED`, `Failed with result 'exit-code'`, `Scheduled restart job`); `@ttyGS1` (port 1): 7 |
| 916.63 | the last record the reader got, 41 s before the link ended (routine service restarts) |

**The failed units** the journal names are the VM's: `ufw`, `linux-modules-cleanup`, `omarchy-provision-hardware`,
`xdg-document-portal`, plus the two noise sources above. `systemctl --failed` over SSH at +93 s listed `linux-modules-cleanup`,
`omarchy-provision-hardware` and `ufw`. The M5 reported one CPU (`maxcpus=1`) and, per Claude Code's answer, 126 GiB of memory.

## M1-side observations (read-only)

Times relative to the handoff `T0 = 04:52:29.303Z` (the host log is local Eastern time, UTC−4):

| +s | Event |
|---:|---|
| +0.10 | endpoint-0 and endpoint-0x82 transaction errors on the generic device at the port (m1n1's device being torn down), as at earlier handoffs |
| +0.21 | m1n1's device destroyed (`hardware connection lost`) |
| +19.45 | enumerated `0x1d6b/0104/0039`, "iLinux J716c control channel, port 1", 480 Mbps; **`device functionality blocked by transport restrictions`**, `device will not be registered for matching` |
| +22.66 | `AppleUSBHostCompositeDevice selected configuration 1` (the human accepted the accessory prompt); the reader opened interface 0 at +22.7 s |
| +76.5 | clock step (one `usb-pipe` session of 0.5 s: 3.9 KB to the M5, 4.1 KB from it) |
| +93 | the checks session (1.2 s: 26.9 KB / 8.0 KB); then the two 16 MiB transfers (1.1 s each) |
| +238 | the human's session starts (`usb-pipe` banner at 423 ms; the M5's sshd logs the login at journal 238.1 s) |
| +391 | the proxy's first Claude and Chromium page loads (Chromium opened by Claude Code on the M5) |
| +958.24 | both bulk endpoints report a transaction error, then **`terminateDevice … hardware connection lost`** at +958.35: the human's power-off or restart; `usb-pipe` ends with `read: 0xe00002ed device not responding`, the reader with `not responding` after 642,026 bytes (exit 0) |
| +958 to +976 | three port power-off/on cycles about 8.5 s apart (as at attempts 22 and 24 after a power-off) |
| +1005.72 | a macOS device named "Mac" enumerates at the port: the M5 is running macOS again |

* **`usb-pipe`'s five sessions**: 0.5 s, 1.2 s, 1.1 s, 1.1 s and 720.3 s; five banners, 22 and 44 stale bytes dropped at the first
  and last (what earlier sessions left in the pipe); **162 host-log lines of read timeouts and aborts on endpoint 0x82 are its own
  400 ms quiet reads during banner sync**, not errors. The reader logged 5 s read timeouts whenever the journal was idle, as in attempt
  24, and never a STALL.
* `ioreg` at +23 s, +120 s, +300 s and +600 s (saved locally): one device, two `IOUSBHostInterface` nubs (255/0/0, two endpoints
  each), `AppleUSBHostCompositeDevice`, an `AppleUSBHostDeviceUserClient` on the device (the accessory approval), interface 0 held by
  `[bulk-log-reader]` and from +238 s interface 1 by `[usb-pipe]`; no macOS driver on either interface.
* **The proxy** (localhost only; destinations stay in the local log): 118 connections, all `ok`. By registrable domain: Anthropic and
  Claude 52 (anthropic.com 40, claude.ai 7, claude.com 5; 16 MB down), Chromium's page loads and updates (google.com 9, googleapis.com 7,
  hcaptcha.com 7, and **22 plain-HTTP GETs to Google's component CDN, 30.9 MB**), telemetry (datadoghq 7), GitHub's content host 2
  (14.3 MB), `jdx.dev` 2, `wttr.in` 2, and my one `archlinuxarm.org` test.
* The capture file on disk is 640,850 bytes: the reader captured 642,026 and three journal lines that carried the sign-in page's
  address were redacted afterwards (their query strings only); every record still ends in exactly one CR LF (5,349 of each).
* The M1 stayed healthy: no panic report, load settled, the keep-awake ran.

## Interpretation (bounded)

**Confirmed (M1 logs, the M5's journal, the human's pasted answer):**

* **The link carries data in both directions**: bulk OUT (72.1 MB to the M5 in the long session, 16.8 MB in 0.63 s in the test) and bulk
  IN, through two interfaces of one device with two user clients at once, for 15 min 39 s from enumeration, with **no kernel fault line
  of any kind** (no `BUSERR`, `translation fault`, `nobody cared` or dwc3 message). Attempt 24's DART fix holds for the second
  interface and for OUT traffic: with two passing runs (24 and 25) against two stalls (21 and 23), the both-instance DT is what
  changed the outcome (the cause stays Likely, as in attempt 24).
* **SSH over the byte pipe works**: key-only as `omarchy`, a new host key at every boot that equals the journal's fingerprint, five
  sessions in a row (the unit restarts sshd in 0.4 s), the longest 12 minutes.
* **The clock step works** (24.2 days to 1.3 ms) and **web access through the M1's relay works** (HTTPS to a mirror and to Claude's
  services, 118 of 118 connections), after the clock was right.
* **Claude Code runs signed in on the M5 inside Omarchy as `omarchy`, with passwordless sudo, and answers prompts**; its answer named
  the hostname, Omarchy 4.0.0.r7028, Linux 7.1.9 (dirty) on aarch64, the device-tree model "Apple MacBook Pro (16-inch, M5 Max)", one
  CPU and about 126 GiB of memory (reported by Claude Code, not independently checked).
* **The Omarchy desktop came up about 27 to 31 s after the handoff** (journal times; attempt 22 read about 39 s from its video, a different measure).
* **The `ioreg` question is answered**: macOS publishes both interfaces of a two-interface vendor device and binds no driver; the
  accessory prompt must still be accepted by the human.
* **The sign-in step was confusing** (from the chat and the clip): the human's first reading was that they had to sign in in the browser
  on the M5's screen, which has no input device, because Claude Code had opened one there; **the clip shows the sign-in link and the
  paste prompt printed in the terminal at the same time**, which is the path that worked.

**Likely (not separately tested):**

* The 14.3 MB from GitHub's content host and the two `jdx.dev` connections are **mise** (aqua registry and version lookups) when
  Claude Code's wrapper ran: the VM's finding that mise asks the web nothing (it had none) does not carry over. The 31 MB of
  plain-HTTP component downloads are Chromium's updater, which ran once the web was reachable.
* `archlinux-keyring-wkd-sync` is a timer-driven unit that the clock jump (24 days) fires at once. It cannot succeed on this root
  (gpg's WKD lookups do not use the proxy and there is no direct route), so it fails and retries every 300 s on every boot with a
  clock step.

**Hypothesis:** none new.

**Not established:** the time Claude took to answer (not measured); how the human completed the sign-in; the M5's screen beyond the clip's six
seconds; throughput above a single 16 MiB run each way and under sustained load; stability beyond 16 minutes; more than one
controller attached (ports 2 and 3 had no cable); what Claude Code can do on one CPU beyond the prompt; whether the human used `/logout`
before the power-off.

## Return and next handoff

* At about **12:08:27 AM** the human powered the M5 off or restarted it (confirmed in chat; the link vanished abruptly with nothing
  unusual in the journal before it and no clean-shutdown lines, and a macOS "Mac" device enumerated 47 s later, +1005.7 s). The
  human has not said in words that Macintosh HD is back; the M1's host log shows macOS running. Fresh policy/default/
  installed-object checks: **NOT CHECKED.** Attempt 25 is consumed; no retry or settings change. The fixed E1 probe is still
  **NOT RUN**.
* **For the M5 (proposals, not authorization):**
  * **Checklist and image fixes seen in this run:** (1) `claude` started from SSH launches Chromium on the M5's desktop through
    `uwsm-app`, so the sign-in page opens where nobody can use it; set `BROWSER` to a no-op for SSH sessions and say plainly that the
    link is printed in the terminal, or document it. (2) Mask `archlinux-keyring-wkd-sync` (or give gpg the proxy): it is 75% of
    the journal's volume. (3) The idle sshd on the unused ports restarts every 47 s with three journal lines each time; a
    `SuccessExitStatus` for its grace-time exit would silence it. (4) Chromium's component updater moves tens of MB over the proxy
    at the first run; a policy that disables it would save the M1's bandwidth.
  * **The link is fast enough to change the boot path**: about 25 MB/s each way against m1n1's 5.2 MB/s upload. A small initramfs
    that fetches the 2.4 GB root over the pipe (or ECM/NCM on boot041's DT, now that the DMA fault is fixed) could cut the
    8-minute upload to about 100 s; that needs a root served over the link, which is the M5's design to decide.
  * **Agents on the M5 now have what they need to work on it**: sudo, the web through the M1 and a way to reach the M1. The
    remaining blockers are the machine's own (one CPU, no GPU, power, input), not the link.
  * The reader needs no change; for a console the M1 now has `ssh`, and `scp` or `rsync` over the same config should work
    (untested here).

No media, capture, `ioreg` dumps or identifiers are committed; the sign-in page's address, code and account are not recorded.
Earlier reports are unchanged.

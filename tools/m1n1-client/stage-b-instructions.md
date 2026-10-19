# Stage B — attempt 25: Omarchy itself with the USB link and Claude Code, on boot041

**M5 handoff, 2026-10-19.** Pull latest main with `git pull --ff-only`, preserving local work
and stopping on divergence. Read `coordination.md`, this file,
`omarchy-arm64/omarchy-root-link-report-2026-10-18.md` (the image and its VM proof) and
`native/boot/stage-b-2026-10-18-attempt24-result.md`. Attempt 24 is consumed: with both DART
instances per dwc3 core (boot041), the USB log streamed from the M5 to the M1 for the full ten
minutes with no fault. Attempt 25 boots the Omarchy root with the link on boot041's package, so the
M1 can connect over SSH, set the clock, give the M5 web access and let the human sign in to
Claude. **New in this attempt: the first data from the M1 to the M5** (bulk OUT, which SSH needs;
attempt 24's reader never wrote).
**Native attempt 25 / live checks NOT RUN at this handoff.** Labels: Confirmed / Likely / Hypothesis / Unknown;
"Confirmed" means in code, offline or in the VM, never on the M5.

**Continue the existing installation.** Installed boot021 m1n1 and clean client pin remain
unchanged. Do not repeat provisioning, Stage A, Recovery, macOS installation, `bputil`, `kmutil`
changes, partitioning or m1n1 installation. Keep Macintosh HD at Full Security and as default. No
volume, security or network-settings changes. Install nothing. Signing in to Claude is the human's,
in the M1's browser; nothing about the account is recorded.

## What changes and why

The goal is agents running inside Omarchy on the M5. That needs the USB link (attempts 21 and 23)
on the root Omarchy's own installer built (attempt 22), with the M5's clock right and Claude Code
ready to sign in.

| | Attempt 22 | Attempt 24 | **Attempt 25** |
|---|---|---|---|
| Package | boot035 (no USB controllers in its DT) | boot041 | **boot041**, the same archive as attempt 24 (its Image is boot040's byte for byte, which this root is pinned to) |
| Initrd | job 045's Omarchy root, 2,337,897,871 bytes | the diagnostic Stage-B initramfs | **job 045's Omarchy root rebuilt with `LINK=1 CLAUDE=1 NOPASSWD=1` for boot040's Image, which boot041 shares: 2434354327 bytes, SHA-256 `b8eae454809839abcf6e3279e028576fa8e47b835f211968dd198a33a18c66c1`**, pinned in `native/boot/omarchy-root-manifest.json` |
| Launcher | `--profile omarchy` (900 s, 3 GiB heap) | `stage-b` | **`--profile omarchy`**, unchanged launcher `b14ec7a1…` |
| USB | none | one `gser` interface per port, the journal, read by the M1's reader for ten minutes with no fault | **two `gser` interfaces per port (`bcdDevice 0x0039`)**: interface 0 the journal (the same reader), interface 1 a byte pipe with sshd on it, for the desktop user `omarchy`, key-only, the M1's key |
| Web | none | none | the M1's `connect-proxy.py`, reverse-forwarded by the SSH session; `HTTPS_PROXY` set for SSH logins and the desktop session |
| Clock | wrong (attempt 22's bar) | — | **set from the M1** right after connecting (`m5-clock.py`), before any web access |
| Claude Code | Omarchy's wrapper only (installs on first use) | — | **2.1.303 installed through that wrapper at build time, signed out**; the human signs in from the M1's browser |
| sudo | none (no password) | — | **passwordless for `omarchy`** (user-approved 2026-10-18): Omarchy's own permanent grant, so agents can use pacman, modules and driver tools; Omarchy's bar shows its red passwordless-sudo indicator; `omarchy-sudo-passwordless --disable` revokes it for the rest of the boot (the next boot has it again) |

The root's changes for the link, Claude Code and the sudo grant are deviations 16-24 in
`omarchy-arm64/omarchy-root-report-2026-10-17.md`; the VM proof is
`omarchy-arm64/omarchy-root-link-report-2026-10-18.md`.

## Offline intake before the human restarts (M1)

1. **The boot041 package**, as attempt 24's step 1 (same archive `ab49e307…4d28`, same receipt). If
   attempt 24's intake is still in place, re-run only its `shasum -a 256 -c` and the offline
   `launch.py --package …` line. The handoff records in `native/boot/` are boot041's, unchanged
   since attempt 24.
2. **The image arrives privately.** The human AirDrops `ramroot.cpio.zst` (2.43 GB) from the M5.
   Its own ignored directory, never the repository root, never committed, uploaded or published:

   ```sh
   mkdir -p build/ramroot045-link
   mv ~/Downloads/ramroot.cpio.zst build/ramroot045-link/ramroot.cpio.zst
   stat -f '%z' build/ramroot045-link/ramroot.cpio.zst    # expect 2434354327
   shasum -a 256 build/ramroot045-link/ramroot.cpio.zst   # expect b8eae454809839abcf6e3279e028576fa8e47b835f211968dd198a33a18c66c1
   ```

   It holds no private key, password, keyring or token (its SSH host key is made at each boot), but
   it does hold the build's machine-id, the M1's public key and a passwordless sudo grant for
   `omarchy`: keep it private like attempt 22's.
3. **Offline launcher run and tests** (no USB is opened):

   ```sh
   python3 -I native/boot/launch.py --package build/native-boot041-download/ilinux-j716c-boot041 \
     --profile omarchy --ramroot build/ramroot045-link/ramroot.cpio.zst
   python3 -I native/boot/test_ramroot.py
   python3 -I tools/m1n1-client/test_usb_pipe.py
   python3 -I tools/m1n1-client/test_connect_proxy.py
   python3 -I tools/m1n1-client/test_m5_clock.py
   ```

   plus attempt 24's suites. Expect from the launcher (exit 0):

   ```text
   Package PASS: all files match the repository manifest.
   RAM root PASS: 2,434,354,327 bytes match omarchy-root-manifest.json (VM job 045 with the USB link, Claude Code and passwordless sudo, 2026-10-19T01:25Z).
   Operator key: none; only keys built into the image can log in.
   Mode: OFFLINE ONLY; USB not opened
   Boot arguments: console=tty0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 pd_ignore_unused clk_ignore_unused quiet
   m1n1 must append: idle=nop arm64.nowfxt
   Upload estimate: 2,479,098,050 bytes (Image 44,681,728, initrd 2,434,354,327, DT 61,995): 495.8 s at 5 MB/s, 619.8 s at 4 MB/s (Inferred: size / observed proxy rate). Deadline 900 s.
   ```

   `test_ramroot.py`: 45 cases (its omarchy-pin cases read this image from the pin and check that the
   pin names boot040's Image, which boot041 carries byte for byte; the boot040 size case skips without
   the M5's `build/`). `test_m5_clock.py`: 13 tests (the clock tool against the M5's real helper
   through a stand-in ssh with a fake clock, the helper's refusals, and `m5-ssh-config`'s `m5o`
   entries as `ssh -G` reads them). On the M5 (2026-10-19), with the extracted boot041 package and
   this image, the launcher printed exactly the lines above and these suites passed.
4. **usb-pipe from its committed source** (the SDK only, as `usb-ssh-link.md` says):

   ```sh
   tools/m1n1-client/usb-pipe/build.sh       # prints build/control/usb-pipe's SHA-256 and version
   build/control/usb-pipe --dry-run --wait 5; echo "exit $?"   # no M5 attached: exit 2, nothing opened
   ```

   Record the binary's digest and those of `usb-pipe/*.c`, `*.m`, `connect-proxy.py`, `m5-clock.py`
   and `m5-ssh-config`. The bulk-log reader is attempt 21's and 23's binary; it accepts this root's
   `bcdDevice 0x0039` (`kStageBcd`).
5. **The M5's host key is new at every boot** (the image holds no private key):

   ```sh
   rm -f build/control/known_hosts-omarchy
   ssh -G -F tools/m1n1-client/m5-ssh-config m5o | grep -E '^(user|hostkeyalias|userknownhostsfile|proxycommand) '
   ```

   Expect `user omarchy`, `hostkeyalias m5-omarchy`, `userknownhostsfile build/control/known_hosts-omarchy`,
   `proxycommand build/control/usb-pipe --log build/native-intake/usb-pipe.log`. The key `build/control/m1-control`
   is the M1's own (its public half is `kernel/experiments/usb-gadget/authorized_keys`, the key the image
   authorizes for `omarchy`); it never leaves the M1.
6. **Memory:** the launcher holds the whole image in RAM (about 2.43 GB); quit large apps. **Do not
   pass `--operator-key`**: it would add a second copy, and the image already authorizes the M1's key.
7. **Reviewed controller digests:** unchanged from attempts 22 to 24 (`launch.py` `b14ec7a1…`, the
   other five as listed in `stage-b-instructions.md`).

Prepare fresh ignored `boot041-omarchy-attempt25.json`/`.md` records with the source, procedure,
controller, payload and receipt hashes and the image digest. Push sanitized readiness in
`progress.md` and `coordination.md`, keeping live checks NOT RUN. Tell the human when ready.

## One human-started boot, filmed, then the link

1. Steps 1-3 of attempt 22: both Macs on power, the same direct cable, **a fresh M1 restart**, kept
   awake (`caffeinate -i`), **the cable re-seated after the restart**, the read-only gate (boot the M5
   into the Boot Lab again if it sees no device). Keep the M1 unlocked and its lid open for the whole
   upload. **Start a 30-minute recording before the launch**, the whole screen square-on.
2. After `Running proxy...` and the gate, **once**:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot041-download/ilinux-j716c-boot041 \
     --profile omarchy --ramroot build/ramroot045-link/ramroot.cpio.zst \
     --launch --device auto --confirm BOOT-J716C-OMARCHY-ROOT
   ```

   About 8 minutes of upload (474.9 s at attempt 22's 5.22 MB/s; the deadline is 900 s), then
   the DT checks, the handoff line, exit 0. m1n1's memory lines as in attempt 22's step 5; **never
   transcribe the serial-number line**.
3. **Watch the M5:** attempt 22's sequence (unpack, systemd, SDDM, Omarchy's desktop about 40 s after
   the handoff, its bar's clock wrong). New: the gadget appears on the M1 when udev starts (Hypothesis:
   20-40 s after the handoff), with a product string `iLinux J716c control channel, port N`. If the M5
   shows `BUSERR` or a DART line as in attempts 21 and 23, note the time from the video and stop the link
   steps; leave the desktop up for the clip.
4. **Terminal 1, interface 0 (the journal):** the bulk-log reader exactly as attempts 23 and 24 ran it, its
   output to `build/native-intake/attempt25-log.txt`. Look for `ilinux-ssh-hostkey`'s line: this boot's
   host key, `256 SHA256:… ilinux-m5-boot (ED25519)`.
5. **Terminal 2, the proxy** (keep it running): `python3 -I tools/m1n1-client/connect-proxy.py --log build/native-intake/attempt25-proxy.log`
6. **Terminal 3, connect and set the clock, before any web access:**

   ```sh
   python3 -I tools/m1n1-client/m5-clock.py
   ssh-keygen -l -f build/control/known_hosts-omarchy     # equals the journal's fingerprint (step 4)
   ```

   Expect `session open after …`, the M5's starting clock and its error (Likely days or months behind:
   with no clock source it starts at systemd's build date), `set: …`, then `check: … PASS` (exit 0).
   Exit 2 with `no matching interface` in `build/native-intake/usb-pipe.log`: the interface is not
   published (record `ioreg -p IOUSB -l -w0`); `no SSH banner`: sshd is not on the pipe (the journal on
   interface 0 says why); exit 3: the M5 refused (not this image). Retry at most twice, a minute apart.
   **No web access before `PASS`**: with a wrong clock every TLS check fails.
7. **The session:** `ssh -F tools/m1n1-client/m5-ssh-config m5o`, then on the M5:

   ```sh
   uname -a; id; date -u; env | grep -i proxy
   curl -sS -o /dev/null -w '%{http_code}\n' https://archlinuxarm.org/
   claude --version
   sudo -n id -u; omarchy-sudo-passwordless --active; echo "active exit $?"
   ```

   Expect `omarchy`, the right time, the proxy variables, `200` (the proxy's log shows `CONNECT
   archlinuxarm.org:443 … ok`), `2.1.303 (Claude Code)` with no download (in the VM, mise resolved
   `latest` to the installed version without asking the web, even with its caches aged three days),
   then `0` and `active exit 0`: agents in this session can use sudo without a password (Omarchy's
   permanent grant). Do not run `omarchy-sudo-passwordless --disable` unless the human wants the grant
   off for the rest of this boot.
8. **The human signs in to Claude** (the agent step). In the same session run `claude`. It has no
   browser there, so it prints a sign-in link: open it in the M1's browser (Terminal: ⌘-double-click),
   sign in there, and paste the code the page shows back into the session. Claude Code then starts in
   the M5's Omarchy, as `omarchy`, with the web through the M1. **Never record, paste into a file or
   share the link, the code, the account's name or e-mail, or any token.** The sign-in lives only in the
   M5's RAM (`~/.claude`) and is gone at the next boot; sign out inside Claude Code (`/logout`) before
   the end if the account's session should not outlive the attempt.
9. **One prompt** to show the agent works, e.g. ask it for the output of `uname -m`; record only
   whether it answered and how long it took.
10. Leave the session (`exit`), keep the clip running to 10 minutes after the handoff, stop the
    reader (Ctrl-C) and the proxy, then return the M5 to Macintosh HD.

**Stop rules:** a reset or M1 panic ends the attempt; no relaunch, no retry beyond step 6's two. A
link failure does not stop the desktop part: let the clip run.

## What to record (sanitized, local in `build/native-intake/`)

Upload time and controller exit; the video's times (systemd, desktop, the gadget on the M1);
`ioreg` of the gadget (no serial strings); the reader's byte count; `usb-pipe.log`; `m5-clock.py`'s
lines (the M5's starting clock, the error, the residual, the round trips); the `curl` code; the
Claude Code version; signed in yes or no; the prompt answered yes or no, with its time. Not recorded:
the m1n1 serial-number line, the sign-in link and code, anything about the Claude account, tokens.
The proxy's log names the hosts the M5 reached: keep it local, commit no raw copy.

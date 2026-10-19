# Stage B — attempt 26 (DRAFT, not handed off): the M5's keyboard, switched on over SSH, on boot042

**M5 draft, 2026-10-19. Not a handoff: nothing is committed, released or pinned in `native/boot/` yet.**
boot042 is packaged (`build/native-boot042/`, the packager's boot042 entry applied), and its records, the
root's pin and the pin-bound test change are in `native/boot/`; all uncommitted. At the handoff the M5
commits them, publishes boot042 as the prerelease `native-j716c-boot042`, gives this file its final attempt
number and makes it `stage-b-instructions.md`. Read `coordination.md`, this file,
`native/boot/boot042-keyboard-modules-2026-10-19.md` (what boot042 is and how it was checked) and
`native/boot/stage-b-2026-10-19-attempt25-result.md`. **Native attempt 26 / live checks NOT RUN.** Labels:
Confirmed / Likely / Hypothesis / Unknown; "Confirmed" means in code, offline or in a VM, never on the M5.

**Continue the existing installation.** Installed boot021 m1n1 and the clean client pin remain unchanged.
Do not repeat provisioning, Stage A, Recovery, macOS installation, `bputil`, `kmutil` changes, partitioning
or m1n1 installation. Keep Macintosh HD at Full Security and as default. No volume, security or
network-settings changes. Install nothing. **No storage in this attempt** (storage is attempt 27, with its own
launcher change): the package keeps the NVMe node disabled (the committed launcher requires it), its kernel has
no storage driver at all, and the image holds no storage module. Nothing in this attempt can read, write or
mount the internal drive.

## What changes and why

Attempt 25 brought SSH, the clock step, web access and Claude Code to Omarchy on the M5. The machine still
has no input of its own. Attempt 26 adds the internal keyboard, and does it the way later hardware work
should go: a kernel whose drivers for new hardware are modules, loaded from the SSH session one at a time,
each checked before the next.

| | Attempt 25 | **Attempt 26** |
|---|---|---|
| Package | boot041 | **boot042**: boot041 with three files changed (`Image`, `kernel.config`, `t6050-j716c-stage-b.dtb`); m1n1, the generic DT, both initramfs and `diag-init.c` byte-identical |
| Kernel | boot040's Image | boot041's tree plus dockchannel-hid 0001 and 0002 (the M4/M5 ring transport); **the keyboard path and the storage drivers are modules**, so none of them runs at boot; `HIDRAW` on. Image `0b6df395…b69c`, 44,616,192 bytes |
| Stage-B DT | boot041's | boot041's **plus the MTP nodes** (the RTKit helper, its mailbox, the DockChannel FIFO and its HID child with six interface nodes, the keyboard alias) **and the MTP's DART enabled**, on streams 0-4. USB part and the disabled NVMe node unchanged |
| Initrd | job 045's root for boot040's Image | **job 045's root for boot042's Image**: attempt 25's root plus the four keyboard modules (blacklisted from automatic loading), `ilinux-keyboard`, and attempt 25's four fixes. 2,435,320,732 bytes, SHA-256 `565644bed5aa2d2c7ab594868447c74a33fd9317c6269c3c52570eef86d3bf6f`, built 2026-10-19T22:08:01Z, pinned for boot042's Image `0b6df395…b69c` |
| Launcher | `--profile omarchy`, `b14ec7a1…` | **unchanged** (`b14ec7a1…`), `--profile omarchy` |
| USB link, clock, web, Claude Code, sudo | as attempt 25 | **as attempt 25**, with fixes: an SSH session opens no browser on the M5 (Claude Code's sign-in link is printed in the terminal), `archlinux-keyring-wkd-sync` masked, sshd on an uncabled port waits silently, Chromium's component updates off |
| **New at boot** | — | **one hardware change: the built-in DART driver probes the MTP's DART and resets it** (all its streams disabled). The MTP mailbox binds to the built-in mailbox driver without touching a register. Nothing else new runs until the keyboard steps |
| **New over SSH** | — | `sudo ilinux-keyboard`: apple-rtkit-helper, apple-dockchannel, hid-apple, dockchannel-hid, then the input device and typing on the M5, each with its own go/no-go |

## Offline intake before the human restarts (M1)

1. **The boot042 package**: download the prerelease `native-j716c-boot042`, check it against Git **before
   extraction** (`archive-sha256.txt`), extract, `verify-package` receipt as for boot041. Expect the archive `a2e57c0ccddcd7c8e60affac0ffa033deb9db1639119a7aa93faaedea276a781` (18,877,362 bytes) and `SHA256SUMS` `60299703efd91bdaca8772d5924c123f38b461738a1c3f65424f1b6529ff3ccd`, as `native/boot/archive-sha256.txt` and `intake-manifest-sha256.txt` record them at the handoff.
2. **The delta against attempt 24/25's boot041 download** (the M1's own diff): exactly `Image`,
   `kernel.config` and `t6050-j716c-stage-b.dtb` differ; the M1's property-level diff of the two Stage-B DTs
   finds exactly ten new nodes (`/soc/mtp@294600000`, `/soc/mbox@294608000`, `/soc/fifo@294b14000`, its
   `input@8000` and the six interface nodes under it) and two changed (`/soc/iommu@294800000`: `status`
   removed, `phandle` and `apple,dma-range = <0x100 0x4000 0x0 0xffff0000>` added; `/aliases`: `keyboard`);
   every USB node and `/soc/nvme@45dcc0000` (still `status = "disabled"`) unchanged. `kernel.config` differs
   by exactly the nine symbols of the report's table, plus two `is not set` lines (`HID_CP2112`, `HID_FT260`)
   that `HIDRAW` makes visible.
3. **The image arrives privately**, as attempt 25's (AirDrop into the ignored `build/ramroot045-boot042/`,
   never the repository root, never committed, uploaded or published). Check its size and SHA-256 against
   `native/boot/omarchy-root-manifest.json` (the pin names boot042's Image).

   ```sh
   mkdir -p build/ramroot045-boot042
   mv ~/Downloads/ramroot.cpio.zst build/ramroot045-boot042/ramroot.cpio.zst
   stat -f '%z' build/ramroot045-boot042/ramroot.cpio.zst    # expect 2435320732
   shasum -a 256 build/ramroot045-boot042/ramroot.cpio.zst   # expect 565644bed5aa2d2c7ab594868447c74a33fd9317c6269c3c52570eef86d3bf6f
   ```

   It holds what attempt 25's held (the build's machine-id, the M1's public key, Omarchy's passwordless sudo
   grant for `omarchy`; no private key, password, keyring or token) plus the four keyboard modules and
   `ilinux-keyboard`; keep it private the same way.
4. **Offline launcher run and the suites** (no USB opened):

   ```sh
   python3 -I native/boot/launch.py --package build/native-boot042-download/ilinux-j716c-boot042 \
     --profile omarchy --ramroot build/ramroot045-boot042/ramroot.cpio.zst
   ```

   Expect (exit 0), the RAM-root line naming the pin's source:

   ```text
   Package PASS: all files match the repository manifest.
   RAM root PASS: 2,435,320,732 bytes match omarchy-root-manifest.json (VM job 045 with the USB link, Claude Code, passwordless sudo and boot042's keyboard modules, 2026-10-19T22:08:01Z).
   Operator key: none; only keys built into the image can log in.
   Mode: OFFLINE ONLY; USB not opened
   Boot arguments: console=tty0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 pd_ignore_unused clk_ignore_unused quiet
   m1n1 must append: idle=nop arm64.nowfxt
   Upload estimate: 2,480,000,463 bytes (Image 44,616,192, initrd 2,435,320,732, DT 63,539): 496.0 s at 5 MB/s, 620.0 s at 4 MB/s (Inferred: size / observed proxy rate). Deadline 900 s.
   ```

   plus attempt 25's suites (`test_ramroot.py`, `test_usb_pipe.py`, `test_connect_proxy.py`, `test_m5_clock.py`)
   and the controller suites.
5. **usb-pipe, the reader, the SSH config**: unchanged from attempt 25 (re-run its step 4 and step 5's
   `ssh -G` check; `rm -f build/control/known_hosts-omarchy` before the boot).

Prepare fresh ignored readiness records, push sanitized readiness in `progress.md` and `coordination.md`
keeping live checks NOT RUN, and tell the human when ready.

## The boot (as attempt 25), with one new go/no-go at boot

Steps 1-6 of attempt 25 unchanged: a fresh M1 restart, cable re-seated, `caffeinate -i`, the read-only
gate, a **30-minute recording** started before the launch, then once:

```sh
tools/m1n1-client/run.sh native/boot/launch.py \
  --package build/native-boot042-download/ilinux-j716c-boot042 \
  --profile omarchy --ramroot build/ramroot045-boot042/ramroot.cpio.zst \
  --launch --device auto --confirm BOOT-J716C-OMARCHY-ROOT
```

**Go/no-go 1, before the handoff (the launcher's own check):** `Hardware DT PASS` after m1n1 has prepared
the DT. This is the first time m1n1 sees the MTP nodes (it fills the keyboard node's country code and
layout from the ADT through the `keyboard` alias). A `STOP` here ends the attempt with nothing handed off:
record the line, no retry.

**Go/no-go 2, at boot (the one new hardware change):** the DART driver resets the MTP's DART at about 2-3 s
of kernel time, before the USB controllers bind. **Go** when, as in attempt 25, the gadget enumerates on
the M1 (about 20 s after the handoff), the desktop comes up (27-31 s) and the journal on interface 0 shows
the MTP DART's probe lines (`apple-dart 294800000.iommu: … DART [pagesize 4000, … locked: 0, …]
initialized`) and no fault line for `294800000.iommu`. **No-go** when the M5 freezes, resets, or shows a
fault for that DART: no keyboard steps; note the time (video and journal), keep the clip running, then
**recover by power-cycling the M5** (hold the power button about 10 s until it is off, press it again, boot
Macintosh HD as after every attempt). No relaunch.

Then attempt 25's link steps 4-7 (reader on interface 0, the proxy, `m5-clock.py`, the SSH session's
checks). Add to the session's checks:

```sh
echo "$BROWSER"                                            # /usr/local/lib/ilinux/ssh-browser
systemctl is-enabled archlinux-keyring-wkd-sync.timer      # masked
systemctl status --no-pager 'ilinux-sshd-tty@*' | grep -E '^\S|Active:'   # uncabled ports: activating (start-pre), no restarts
sudo ilinux-keyboard --status                              # all four keyboard modules: not loaded
```

Claude Code's sign-in (attempt 25's steps 8-9) is optional this time; if run, the M5's screen must not open
a browser (fix 1): the link is printed in the terminal, opened on the M1.

## The keyboard, one module at a time (new)

One command runs the steps in order and stops at the first failure: `sudo ilinux-keyboard` in the SSH
session. It prints each step's kernel log lines and `PASS` or `FAIL`, and at the end `RESULT: PASS` or
`RESULT: FAIL at step N: …`. **Record its whole output** (it holds no identifier; the typing test prints
only counts). Each step is its own go/no-go:

| Step | What it does on the M5 | Go | No-go: stop there, record, then |
|---|---|---|---|
| 0 | checks only: boot042, the module digests, the MTP nodes and alias, the MTP DART bound, unlocked, 16 KiB pages, no fault since boot, no keyboard module loaded | `PASS` | nothing was loaded: report the line; end the keyboard part |
| 1 | `apple-rtkit-helper`: binds `mtp@294600000`; the DART gets the MTP's five streams on one table; the MTP CPU's run bit is set and RTKit wakes or boots it | bound, no error, crash or fault line | the MTP did not answer or crashed: end the keyboard part; if the M5 hangs or the link drops, power-cycle (above) |
| 2 | `apple-dockchannel`: binds `fifo@294b14000` (masks and acknowledges its interrupts), creates `input@8000` | bound, child created | end the keyboard part |
| 3 | `hid-apple`: Apple's key mapping, loaded first so the keyboard does not start on hid-generic | loaded | end the keyboard part |
| 4 | `dockchannel-hid`: binds `input@8000`, allocates the 2 MiB ring through the MTP DART, registers it 100 ms after the first DockChannel message (`0xC1`, then `0x91`), creates the interfaces the MTP announces | `Ring registered`, `New interface keyboard`, `Interface keyboard is now ready` | **one retry** if the ring is registered but no keyboard interface came, or no ring at all: `sudo modprobe -r dockchannel-hid`, then `sudo ilinux-keyboard --poll 100` (the driver's debug timer drains the ring every 100 ms, in case no doorbell arrives). Any other failure: end the keyboard part |
| 5 | the keyboard's input device under `input@8000`, and Hyprland's device list | an event device with key capabilities | end the keyboard part |
| 6 | **the human types `omarchy` and Enter on the M5's own keyboard** within 90 s; the script counts key presses and checks Enter came (nothing typed is printed) | `PASS` with the count | not typed in time: run `sudo ilinux-keyboard` again (steps 0-5 pass again and only step 6 repeats) |

**Then the human uses the keyboard on the M5:** Super+Return opens a terminal on the M5's screen; type a line
there (not a password, nothing personal) and confirm on the video that it appears. That is the attempt's
headline result.

**Stop rules for the keyboard part:** no module is unloaded (unloading the helper stops the MTP CPU); no step
is forced past a `FAIL` except step 4's one retry; a hang, reset or lost link ends the attempt (power-cycle).
The trackpad is not part of this attempt: if the MTP announces it, its interface fails to open for want of
firmware, which is expected.

## What to record (sanitized, local in `build/native-intake/`)

As attempt 25 (upload time, controller exit, the video's times, `ioreg` without serial strings, the reader's
byte count, `usb-pipe.log`, `m5-clock.py`'s lines), plus: the launcher's `Hardware DT PASS` line; the MTP
DART's probe lines from the journal; `ilinux-keyboard`'s full output, including any retry; whether typing
appeared on the M5's screen; the uncabled ports' sshd states; the journal's size per minute (attempt 25's
noise sources should be gone). Not recorded: the m1n1 serial-number line, anything typed beyond the test
word, the Claude sign-in link, code or account.

## What the attempt tests, in order

1. m1n1's preparation of the MTP nodes (the launcher's prepared-DT check, go/no-go 1).
2. The MTP DART's reset at boot, the only new hardware write before the SSH session (go/no-go 2), and that
   attempt 25's desktop and link still come up.
3. Attempt 25's four fixes: no browser from SSH, no wkd-sync noise, silent uncabled ports, no component
   updates through the relay.
4. Over SSH, one module at a time: the MTP's RTKit wake (1), the DockChannel FIFO (2), hid-apple (3), the
   ring transport's handshake and the keyboard interface (4), the input device (5), and typing on the M5 (6).

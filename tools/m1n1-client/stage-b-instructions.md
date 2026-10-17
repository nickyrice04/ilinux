# Stage B — attempt 20: the Omarchy RAM root on boot035 with the live status screen

**M5 handoff, 2026-10-16.** Pull latest main with `git pull --ff-only`, preserving
local work and stopping on divergence. Read `coordination.md`, this file,
`native/boot/ramroot-profile-2026-10-15.md` and the new RAM-root report
`omarchy-arm64/ram-root-report-2026-10-16.md`.
Attempt 19 is consumed: the first native Omarchy desktop came up on the M5 and
stayed up, view-only, with two things to fix on the RAM-root side (a red
"started without start-hyprland" notice for 15 s, and a status terminal that
printed one block and then nothing). **Attempt 20 is the same boot, with a new
RAM-root image that fixes both**, so that a filmed 10-minute run carries numbers.
The USB link (boot039, bulk-only) continues separately and is not part of this
attempt. **Native attempt 20 / RAM-root live checks NOT RUN at this handoff.**

**Continue the existing installation.** Installed boot021 m1n1 and clean client
pin remain unchanged. Do not repeat provisioning, Stage A, Recovery, macOS
installation, `bputil`, `kmutil`, partitioning or m1n1 installation. Keep
Macintosh HD at Full Security and as default. No volume, security or
network-settings changes.

## What changes and why

The **package is boot035**, exactly as in attempts 16 and 19: same Image
(`1131a1af…`), same Stage-B DT (no SMC-owned domains, **no USB controllers**),
same m1n1. The **launcher and its RAM-root profile are unchanged** (`launch.py`
`4d55f0c9…`). Only the RAM-root image changes:

| | attempt 19 (run 30) | attempt 20 (run 33) |
|---|---|---|
| RAM root | 182,092,876 bytes, SHA-256 `58bdc6ce…a27e` | **182,420,823 bytes, SHA-256 `67f257327ce308531b0c338babb8b644928cae8148bb34467042cca13cbad3f7`**, pinned in `native/boot/ramroot-manifest.json` |
| Session | `Hyprland` run directly: a red notice "started without start-hyprland" for about 15 s | Hyprland's own `start-hyprland` supervisor starts it (a watchdog pipe; a restart in safe mode after a crash); **no notice** (VM-verified: 0 warning lines in the journal) |
| Status terminal | one block printed once (kernel, display, memory, `desktop ready 7.79 s`), then a shell prompt | **a live screen**, redrawn every second: the time since kernel start in large block digits with CPU use beside it, memory and load, the single-thread results of the repository's `cpubench`/`membench` filling in as each step ends (eleven steps, about 75 s natively), and the last lines of the kernel log (`quiet` hides them on the console; the release ladder shows here) |
| Everything else | fixed arguments `console=tty0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 pd_ignore_unused clk_ignore_unused quiet`; m1n1 appends exactly `idle=nop arm64.nowfxt`; confirmation `BOOT-J716C-RAM-ROOT`; deadline 300 s | unchanged; upload ≈ 227.1 MB (45.4 s at 5 MB/s, 56.8 s at 4 MB/s; attempt 19 measured 5.36 MB/s) |

In the VM (QEMU TCG, one vCPU, the boot035 Image) the new image reached the
desktop with its wallpaper **82.7 s after kernel start** (run 30: 68.4 s;
native attempt 19: 7.79 s), with **0 failed units**, no
start-hyprland warning, the counter advancing between two framebuffer captures
30 s apart (72 s → 91 s), and all eleven benchmark steps finished 224 s after kernel
start (TCG timings; the native run should take about 75 s, Hypothesis from the
measured 4–7× TCG slowdown). **There is still no keyboard or trackpad: the
desktop is view-only, and the video is the evidence.**

## Offline intake before the human restarts

1. **The boot035 package** (downloaded for attempt 16; re-verify, do not
   re-download unless it is missing):

   ```sh
   (
   set -e
   cd build/native-boot035-download
   shasum -a 256 -c ../../native/boot/archive-sha256.txt
   test -d ilinux-j716c-boot035 || tar -xzf ilinux-j716c-boot035.tar.gz
   )
   mkdir -p build/native-intake/receipts build/native-intake/results
   tools/m1n1-client/run.sh tools/m1n1-client/verify-package.py \
     build/native-boot035-download/ilinux-j716c-boot035 \
     --manifest-sha256 "$(cat native/boot/intake-manifest-sha256.txt)" \
     > build/native-intake/receipts/boot035-attempt20.json
   ```

   Archive 16,723,179 bytes, SHA-256
   `81cbbd1ca09ec53bbfe8f616e578c07d7f878a26a7629c2d1de40d969be966e7`; SHA256SUMS
   digest `7635c5e4a25b051fa933ad969e2407c3f6a63cea876570f58052a474cf162f8d`.

2. **The new RAM-root image arrives privately.** The human AirDrops
   `ramroot.cpio.zst` (run 33) from the M5; AirDrop puts it in `~/Downloads`.
   Move it to `build/ramroot/ramroot.cpio.zst` (ignored), **replacing run 30's
   file**, and never into the repository root (attempt 19 had to move it out);
   never commit, upload or publish it (it holds its SSH host key). Verify:

   ```sh
   mkdir -p build/ramroot
   mv ~/Downloads/ramroot.cpio.zst build/ramroot/ramroot.cpio.zst
   stat -f '%z' build/ramroot/ramroot.cpio.zst    # expect 182420823
   shasum -a 256 build/ramroot/ramroot.cpio.zst   # expect 67f257327ce308531b0c338babb8b644928cae8148bb34467042cca13cbad3f7
   ```

   The size and digest must equal `native/boot/ramroot-manifest.json`; the
   launcher refuses anything else, including run 30's image.

3. **Offline launcher run and tests** (no USB is opened):

   ```sh
   python3 -I native/boot/launch.py --package build/native-boot035-download/ilinux-j716c-boot035 \
     --profile ramroot --ramroot build/ramroot/ramroot.cpio.zst
   python3 -I native/boot/test_launcher.py
   python3 -I native/boot/test_ramroot.py
   python3 -I native/boot/test_gpio_guard.py
   python3 -I native/boot/test_entry_guard.py
   python3 -I native/boot/test_dapf_guard.py
   python3 -I native/boot/test_framebuffer.py
   python3 -I native/boot/test_hardware.py
   tools/m1n1-client/run.sh native/boot/test_dapf_guard_adt.py
   tools/m1n1-client/run.sh native/boot/test_launcher_adt.py
   M1N1_SOURCE="$PWD/third_party/m1n1" tools/m1n1-client/run.sh native/boot/test_protocol.py
   ```

   Expect `Package PASS`, `RAM root PASS: 182,420,823 bytes match
   ramroot-manifest.json (VM job 039 run 33, …)`, `Operator key: none` (no
   `--operator-key`: there is no USB link to log in over), the boot arguments
   above, `m1n1 must append: idle=nop arm64.nowfxt` and the upload estimate
   (227,080,994 bytes); the reviewed **102** controller cases plus
   `test_ramroot.py` (30) PASS; the clean client pin
   `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.

Reviewed controller digests (unchanged since attempt 18; record the checked-out
Git commit too):

* `native/boot/launch.py`: `4d55f0c9641f7c572129c7ed374aacd6b91656e41fbb54a7ce05b5d209af840b`
* `native/boot/gpio_guard.py`: `a3c038d036e2bc97679bd29d78d16e42b3db06d96775918abaeb01a53434a755`
* `native/boot/entry_guard.py`: `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713`
* `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
* `native/boot/fdt.py`: `ee577a08bb48242e84dbc50cd1f40a8d1f47a4d4481ca6dd6503829f53615ad3`
* `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

Prepare fresh ignored `boot035-ramroot-attempt20.json`/`.md` records with the
source/procedure/controller/payload/receipt hashes and the RAM-root digest. Push
sanitized readiness in `progress.md` and `coordination.md`, keeping live checks
NOT RUN. Tell the human when ready.

## One human-started RAM-root boot, filmed for ten minutes

1. Both Macs on power, same direct cable. **Restart the M1 fresh**, keep it
   awake with `caffeinate -i`, and **re-seat the cable after the restart**
   (attempts 17 and 18: the read-only gate saw no device until it was
   re-seated). Close any serial tool.
2. **Start recording before the launch command**, at 1080p or 4K, the phone in
   a stand that does not move for the whole run, framing **the whole screen**
   square-on (the glossy panel mirrors the room: dim what is behind the phone,
   and check the frame once with the Boot Lab menu on screen). Attempt 19's clip
   began at kernel 0.07 s and so held neither the upload nor the handoff;
   this one should. Transfer the original file afterwards (AirDrop or cable,
   not Messages).
3. Human saves work, shuts down the M5, holds power for startup options and
   selects **iLinux Boot Lab → Continue**. Keep Macintosh HD as default.
4. After the human reports `Running proxy...` and the gate passes, invoke this
   **once**:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot035-download/ilinux-j716c-boot035 \
     --profile ramroot --ramroot build/ramroot/ramroot.cpio.zst \
     --launch --device auto --confirm BOOT-J716C-RAM-ROOT
   ```

   The upload takes about 45 s before the handoff (42.28 s in attempt 19); the
   launcher's deadline is 300 s. No `m1n1.setup`, shell, reconnect or automatic
   retry.
5. Record the controller result as in attempts 16–19 (times, elapsed, exit,
   every gate, the prepared-DT argument check including m1n1's exact append,
   kboot reply). Exit 0 is not Linux success. No USB device is expected on the
   M1 after the handoff (the boot035 DT has no controllers).
6. **Watch the M5 screen.** Expect a short kernel phase, then the Hyprland
   desktop within about 8 s of the handoff: the Tokyo Night wallpaper, waybar
   along the top (clock, CPU, memory), and the status terminal filling the rest
   of the screen, its text about twice the size of attempt 19's. Rows, top to
   bottom:
   * `kernel`, `display` and `session` lines: the kernel release and page size,
     `card0 on simple-framebuffer`, `Hyprland 0.56.2 under start-hyprland (its
     watchdog)` and `desktop ready N s after kernel start`;
   * `memory`: MiB in use, available, total, and the load average;
   * **the counter**: `H:MM:SS` since kernel start in block digits, redrawn
     every second, with `cpu N% busy over the last second` beside it;
   * **benchmarks**: the header names the compiler and flags and the running
     step (`running cpubench fma (2/11)`), then five rows fill in one by one
     (`freq`, `fma_asm`, `fma`, `intmix`; `sort`, `sgemm`, `syscall`,
     `pingpong`; STREAM `copy`/`scale`/`add`/`triad` GB/s; chase latency at 16
     KiB, 4 MiB, 32 MiB and 128 MiB; first-touch GB/s), ending with `done in N
     s · 11 of 11 steps OK`. Expect about 75 s for the whole run (Hypothesis);
     a step that fails reads `failed` and the rest continue;
   * **kernel log**: the last lines of the kernel log, with timestamps. The
     power-domain release ladder (attempts 16–19 ran it at kernel 20–57 s)
     scrolls through here; any warning after it shows here too.

   **No red notice** should appear at the top right. The waybar clock shows the
   wrong time (no clock source), which is expected.
7. Stop criterion: **10 minutes from the handoff**, or earlier on a reset, a
   kernel panic, a dark panel, or an M1 panic. Keep filming until then even when
   nothing changes: the counter advancing is the stability evidence. Then the
   human powers the M5 off (hold power), selects **Macintosh HD → Continue** and
   confirms the usual desktop return.

   | M5 screen | Meaning |
   |---|---|
   | Desktop, counter advancing, benchmark rows filled, no red notice | **Attempt 20 as intended.** Report the time from handoff to the first desktop frame, the `desktop ready` value, the counter value at the end of the clip, the benchmark rows (read them from the video), and the kernel-log lines seen |
   | Desktop, counter advancing, one or more rows `failed` or the header stuck on `running …` past 5 minutes | Desktop fine, a benchmark step did not finish: report which, and the last kernel-log lines |
   | Desktop with the red notice | The session did not go through `start-hyprland`: report it; the rest of the run is still valid |
   | Counter stops while the desktop stays | The status script or foot died: note the time; the shell prompt may appear in the window |
   | Text console stuck with a systemd error or an emergency shell | Userspace failed: copy the visible lines verbatim |
   | Black screen, no restart to Macintosh HD within about 60 s | simpledrm, seatd or Hyprland did not take the display (or a display domain was released): note the time of the last visible frame |
   | Silent reset to Macintosh HD | Note the time and the last visible lines (the kernel-log rows on the last frame are the record) |
   | Controller rejection (upload, DT or argument gate) | Report the line verbatim; no retry |

8. Push the sanitized attempt-20 report and progress/coordination updates. No
   media, raw target output, RAM-root image or identifiers in Git. The
   benchmark values read from the video are single-thread, one-CPU, software
   rendering running beside them, built with gcc rather than the macOS
   baseline's clang: record them as "native, attempt 20" and make no parity
   claim from them.

## Path toward Omarchy

With the desktop and its numbers on film, the next steps are a working USB link
(boot039: bulk-only, then networking) so the RAM root can be reached over SSH
and measured properly, then the built-in keyboard and trackpad (the MTP input
work and the E1 read-only probe), then storage and efficiency. See `roadmap.md`.

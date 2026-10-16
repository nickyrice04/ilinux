# Stage B — attempt 19: the Omarchy RAM root on boot035 (the launcher's RAM-root profile)

**M5 handoff, 2026-10-16.** Pull latest main with `git pull --ff-only`, preserving
local work and stopping on divergence. Read `coordination.md`, this file and
`native/boot/ramroot-profile-2026-10-15.md`.
Attempt 18 is consumed: boot038's ACM + ECM gadget was enumerated and
configured by the M1, then its control endpoint stopped answering (the
interrupt-IN notification endpoint is the leading suspect; a bulk-only
candidate, boot039, is being prepared separately). **That affects only the USB
link.** This attempt boots the first Omarchy desktop without any USB link.
**Native attempt 19 / RAM-root live checks NOT RUN at this handoff.**

**Continue the existing installation.** Installed boot021 m1n1 and clean client
pin remain unchanged. Do not repeat provisioning, Stage A, Recovery, macOS
installation, `bputil`, `kmutil`, partitioning or m1n1 installation. Keep
Macintosh HD at Full Security and as default. No volume, security or
network-settings changes.

## What changes and why

The **package is boot035**, exactly as in attempt 16, the first stable native
baseline: same Image (`1131a1af…`), same Stage-B DT (no SMC-owned domains, **no
USB controllers**), same m1n1. Only the launch profile changes:

| | attempt 16 (`stage-b`) | attempt 19 (`ramroot`) |
|---|---|---|
| initrd | boot035's 302 KB diagnostic initramfs | the **Omarchy-style Arch RAM root**, VM job 039 run 30: 182,092,876 bytes, SHA-256 `58bdc6cee4e2a9d0b1fd2a800f2549c7e3ea300e0a6e76d3d17db3b08dd5a27e`, pinned in `native/boot/ramroot-manifest.json` |
| Fixed arguments | the diagnostic set | `console=tty0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 pd_ignore_unused clk_ignore_unused quiet`; m1n1 must append exactly `idle=nop arm64.nowfxt` |
| Confirmation | `BOOT-J716C-RAM-DIAGNOSTIC` | `BOOT-J716C-RAM-ROOT` |
| Upload / deadline | ≈ 45 MB / 180 s | ≈ 226.8 MB (45–57 s at 4–5 MB/s) / 300 s |

The RAM root: Arch Linux ARM (304 packages), systemd, seatd, **Hyprland on
`simpledrm` with Mesa llvmpipe** (software rendering, one CPU), Omarchy's
configuration with the Tokyo Night theme, waybar (clock, CPU, memory) and a foot
terminal. In the VM it reached the desktop with its wallpaper 68.4 s after kernel
start under QEMU's emulator, with 0 failed units; native should be faster
(Hypothesis). **There is no keyboard or trackpad support yet: the desktop is
view-only.** boot035's DT has no USB device-mode controller, so the RAM root's
gadget never starts and nothing appears on the M1's USB side after the handoff:
**the video is the evidence.** The boot035 release ladder still runs (`quiet`
hides it); attempt 16 showed it completes without a reset.

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
     > build/native-intake/receipts/boot035-attempt19.json
   ```

   Archive 16,723,179 bytes, SHA-256
   `81cbbd1ca09ec53bbfe8f616e578c07d7f878a26a7629c2d1de40d969be966e7`; SHA256SUMS
   digest `7635c5e4a25b051fa933ad969e2407c3f6a63cea876570f58052a474cf162f8d`.

2. **The RAM-root image arrives privately.** The human AirDrops
   `ramroot.cpio.zst` from the M5. Put it at `build/ramroot/ramroot.cpio.zst`
   (ignored) and verify it; never commit, upload or publish it (it holds its SSH
   host key):

   ```sh
   mkdir -p build/ramroot
   stat -f '%z' build/ramroot/ramroot.cpio.zst    # expect 182092876
   shasum -a 256 build/ramroot/ramroot.cpio.zst   # expect 58bdc6ce…a27e (ramroot-manifest.json)
   ```

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

   Expect `Package PASS`, `RAM root PASS: 182,092,876 bytes …`, `Operator key:
   none` (no `--operator-key` this time: there is no USB link to log in over),
   the boot arguments above, `m1n1 must append: idle=nop arm64.nowfxt` and the
   upload estimate; the reviewed **102** controller cases plus `test_ramroot.py`
   (30) PASS; the clean client pin `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.

Reviewed controller digests (unchanged since attempt 18; record the checked-out
Git commit too):

* `native/boot/launch.py`: `4d55f0c9641f7c572129c7ed374aacd6b91656e41fbb54a7ce05b5d209af840b`
* `native/boot/gpio_guard.py`: `a3c038d036e2bc97679bd29d78d16e42b3db06d96775918abaeb01a53434a755`
* `native/boot/entry_guard.py`: `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713`
* `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
* `native/boot/fdt.py`: `ee577a08bb48242e84dbc50cd1f40a8d1f47a4d4481ca6dd6503829f53615ad3`
* `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

Prepare fresh ignored `boot035-ramroot-attempt19.json`/`.md` records with the
source/procedure/controller/payload/receipt hashes and the RAM-root digest. Push
sanitized readiness in `progress.md` and `coordination.md`, keeping live checks
NOT RUN. Tell the human when ready.

## One human-started RAM-root boot, filmed

1. Both Macs on power, same direct cable. **Restart the M1 fresh**, keep it
   awake with `caffeinate -i`, and **re-seat the cable after the restart**
   (attempts 17 and 18: the read-only gate saw no device until it was
   re-seated). Close any serial tool.
2. Film the M5 screen **before launching**, at 1080p or 4K, phone fixed in a
   stand. This time frame **the whole screen**: the desktop is the result.
   Transfer the original file afterwards (AirDrop or cable, not Messages).
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

   The upload takes about a minute before the handoff; the launcher's deadline
   is 300 s. No `m1n1.setup`, shell, reconnect or automatic retry.
5. Record the controller result as in attempts 16–18 (times, elapsed, exit,
   every gate, the prepared-DT argument check including m1n1's exact append,
   kboot reply). Exit 0 is not Linux success.
6. **Watch the M5 screen.** Expect a short kernel phase (`quiet` keeps it
   brief), then the Hyprland desktop: the Tokyo Night wallpaper, waybar along
   the top with a running clock, CPU and memory, and a foot terminal window
   with a status screen. Note the video time of the handoff and of the first
   desktop frame, and whether the clock advances.
7. Stop criterion: **the desktop visible and steady for 2 minutes**, or **10
   minutes from handoff**, or earlier on a reset, a kernel panic, or an M1
   panic. Then the human powers the M5 off (hold power), selects **Macintosh
   HD → Continue** and confirms the usual desktop return.

   | M5 screen | Meaning |
   |---|---|
   | Hyprland desktop (wallpaper, waybar, terminal), clock advancing | **The first native Omarchy desktop on the M5.** Report time from handoff to desktop. |
   | Text console stuck with a systemd error or an emergency shell | Userspace failed: copy the visible lines verbatim |
   | Black screen, no restart to Macintosh HD within about 60 s | simpledrm, seatd or Hyprland did not take the display (or a display domain was released): note the time of the last visible frame |
   | Silent reset to Macintosh HD | Note the time and the last visible lines, as in attempts 14–15 |
   | Controller rejection (upload, DT or argument gate) | Report the line verbatim; no retry |

8. Push the sanitized attempt-19 report and progress/coordination updates. No
   media, raw target output, RAM-root image or identifiers in Git.

## Path toward Omarchy

If the desktop appears, the next steps are a working USB link (boot039:
bulk-only, then networking) so the RAM root can be reached over SSH and
measured, then the built-in keyboard and trackpad (the MTP input work and the
E1 read-only probe), then storage and efficiency. See `roadmap.md`.

# Stage B — attempt 22: Omarchy itself (VM job 045) as a RAM root on boot035, with the launcher's `omarchy` profile

**M5 handoff, 2026-10-18.** Pull latest main with `git pull --ff-only`, preserving local work
and stopping on divergence. Read `coordination.md`, this file, the root's report
`omarchy-arm64/omarchy-root-report-2026-10-17.md` and `native/boot/ramroot-profile-2026-10-15.md`.
Attempt 21 is consumed: boot039's bulk-only port kept EP0 healthy and the M1's reader streamed
36,909 bytes, then the M5's dwc3 flagged a DMA bus error and the stream stopped
(`native/boot/stage-b-2026-10-18-attempt21-result.md`); boot040 investigates that separately.
**This attempt has no USB link at all**: the boot035 package's DT has no USB controllers, so
attempt 21's fault cannot occur here. It boots the root that Omarchy's own installer built, on the
kernel attempts 16, 19 and 20 ran. **Native attempt 22 / live checks NOT RUN at this handoff.**

**Continue the existing installation.** Installed boot021 m1n1 and clean client pin remain
unchanged. Do not repeat provisioning, Stage A, Recovery, macOS installation, `bputil`, `kmutil`
changes, partitioning or m1n1 installation. Keep Macintosh HD at Full Security and as default. No
volume, security or network-settings changes. Install nothing.

Labels: Confirmed / Likely / Hypothesis / Unknown. "Confirmed" here means confirmed in code, in the
VM or offline, never on the M5.

## What changes and why

| | Attempt 20 (job 039 run 33) | **Attempt 22 (job 045)** |
|---|---|---|
| Root | Omarchy-style: Arch Linux ARM packages with Omarchy's configuration, a session of our own | **Omarchy**: built by Omarchy's installer (the edge aarch64 runtime `omarchy-dev`/`omarchy-settings-dev`), 865 packages, Omarchy's own session (SDDM autologin → uwsm → Hyprland 0.56.2 → Quickshell, Omarchy 4's shell) |
| Image | 182,420,823 bytes, `67f25732…d3f7` | **2,337,897,871 bytes, SHA-256 `d00ba1563312e69ce366b316dab245ea76226c4f0399a6e32d36932aaa63578a`**, pinned in `native/boot/omarchy-root-manifest.json`; 8.53 GB unpacked, 10.77 GB in tmpfs; built 2026-10-18T06:54Z with deviation 15 (`QT_WAYLAND_FRAME_CALLBACK_TIMEOUT=0`) |
| Launcher | `--profile ramroot`, deadline 300 s, ProxyUtils' default 1 GiB heap | **`--profile omarchy`**, deadline **900 s**, **3 GiB heap**, confirmation **`BOOT-J716C-OMARCHY-ROOT`** |
| Upload | 227,080,994 bytes, 42.38 s (measured, 5.36 MB/s) | **2,382,558,042 bytes, about 444.5 s at 5.36 MB/s, 596 s at 4 MB/s** (Inferred) |
| Unchanged | | the boot035 package (Image `1131a1af…`, the Stage-B DT with no USB controllers, m1n1); the fixed RAM-root arguments; m1n1's exact `idle=nop arm64.nowfxt` append; every gate |

The launcher changed for this attempt, for the first time since attempt 18. It gained a third
profile, `omarchy`, and nothing else: the `stage-b` and `ramroot` profiles produce exactly the
committed launcher's sessions, command lines and controller calls (`test_ramroot.py` compares them
case by case, 44 cases). Its new digest is below. The other five controller files are unchanged.
The handoff records (`native/boot/package-manifest.json`, `archive-sha256.txt`,
`intake-manifest-sha256.txt`) point at boot035 again, as the attempt-19 handoff did.

Why the heap matters, from m1n1's code at the pin `57a9339`:

* The launcher places the kernel, the DT and the initrd with `memalign` from the proxy client's heap.
  `ProxyUtils` makes that heap 1 GiB by default. With the default, the job 045 image fails its
  allocation with `Out of memory` before any byte is written (Confirmed, code).
* The heap starts 128 MiB above m1n1's own heap pointer. That pointer sits just above
  `top_of_kernel_data` and m1n1's boot allocations. m1n1 is only told the heap's base, as its own
  heap limit, so the size is the client's bookkeeping (Confirmed, code).
* On this M5, hv002 put a block from that heap at `0x10010db8240`, DRAM + 0.26 GiB (Measured). The
  attempt's writes total about 2.39 GB: kernel, DT and initrd. So they end below about DRAM + 2.5 GiB.
  That is inside the roughly 126 GiB that m1n1 declares to Linux as usable RAM, and far below the
  regions m1n1 takes from the top of memory (Likely).
* The macOS boot's carveout map lists regions at DRAM + 0.56–1.79 GiB. Whether they exist, live,
  in the custom-kernel boot that m1n1 runs in is **Unknown**. Step 5 of the boot reads the facts
  from the screen; the stop rules cover a reset during the upload.

## Offline intake before the human restarts (M1)

1. **The boot035 package** (downloaded for attempt 16): re-verify it, as for attempts 19 and 20.

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
     > build/native-intake/receipts/boot035-attempt22.json
   ```

   Archive 16,723,179 bytes, SHA-256
   `81cbbd1ca09ec53bbfe8f616e578c07d7f878a26a7629c2d1de40d969be966e7`; SHA256SUMS digest
   `7635c5e4a25b051fa933ad969e2407c3f6a63cea876570f58052a474cf162f8d`.

2. **The image arrives privately.** The human AirDrops `ramroot.cpio.zst` (2.34 GB) from the M5;
   AirDrop puts it in `~/Downloads`. Put it in its own ignored directory, so that run 33's file in
   `build/ramroot/` stays usable for the `ramroot` profile, and never in the repository root. Never
   commit, upload or publish it.

   ```sh
   mkdir -p build/ramroot045
   mv ~/Downloads/ramroot.cpio.zst build/ramroot045/ramroot.cpio.zst
   stat -f '%z' build/ramroot045/ramroot.cpio.zst    # expect 2337897871
   shasum -a 256 build/ramroot045/ramroot.cpio.zst   # expect d00ba1563312e69ce366b316dab245ea76226c4f0399a6e32d36932aaa63578a
   ```

   The size and digest must equal `native/boot/omarchy-root-manifest.json`; the launcher refuses
   anything else, including run 33's image and job 045's earlier image (`5c74bced…`).

3. **Offline launcher run and tests** (no USB is opened):

   ```sh
   python3 -I native/boot/launch.py --package build/native-boot035-download/ilinux-j716c-boot035 \
     --profile omarchy --ramroot build/ramroot045/ramroot.cpio.zst
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

   Expect exactly these lines from the launcher (exit 0):

   ```text
   Package PASS: all files match the repository manifest.
   RAM root PASS: 2,337,897,871 bytes match omarchy-root-manifest.json (VM job 045, 2026-10-18T06:54Z).
   Operator key: none; only keys built into the image can log in.
   Mode: OFFLINE ONLY; USB not opened
   Boot arguments: console=tty0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 pd_ignore_unused clk_ignore_unused quiet
   m1n1 must append: idle=nop arm64.nowfxt
   Upload estimate: 2,382,558,042 bytes (Image 44,599,808, initrd 2,337,897,871, DT 60,363): 476.5 s at 5 MB/s, 595.6 s at 4 MB/s (Inferred: size / observed proxy rate). Deadline 900 s.
   ```

   Expect the reviewed **102** controller cases plus `test_ramroot.py` (**44**) to PASS, and the
   clean client pin `57a9339ffd1876e78297b17d34dece8cff8fa1ba`. `--profile ramroot` with run 33's
   image must still print what it printed for attempt 20.

4. **Memory.** The launcher holds the whole image in RAM: 2.41 GB peak in the offline run on the M5
   (Measured). Quit large apps before the launch. **Do not pass `--operator-key`.** The root enables
   no SSH server, boot035 has no USB link, and the key would add a second 2.34 GB copy.

5. **Reviewed controller digests** (record the checked-out Git commit too):
   * `native/boot/launch.py`: `b14ec7a1d6957197d808609a9c4888995598e23ce4c63707db2a58476a9e0740` (**new**: the `omarchy` profile; the committed launcher since attempt 18 was `4d55f0c9…`)
   * `native/boot/gpio_guard.py`: `a3c038d036e2bc97679bd29d78d16e42b3db06d96775918abaeb01a53434a755`
   * `native/boot/entry_guard.py`: `d1fa8ca84aa1c7032c50c8766c8571054047720df35cb7d518310167ec183713`
   * `native/boot/dapf_guard.py`: `bb33d9bebcec3a6cd925ed9e7b28dbabe3c7375c445d7e9d68ace18f4eaa7047`
   * `native/boot/fdt.py`: `ee577a08bb48242e84dbc50cd1f40a8d1f47a4d4481ca6dd6503829f53615ad3`
   * `tools/m1n1-client/usb_identity.py`: `72cc8c2a916b8964b2e4b5afc4c1aac22fe8031a2c2f8658df6882b063a47137`

   Review the launcher diff against `4d55f0c9…` (`git diff 4d53cff -- native/boot/launch.py`): a
   third `Profile` with a `heap` field, `verify_ramroot` taking its record file, the heap passed to
   `ProxyUtils`, and the argument parser accepting the new profile. Nothing in the gates, the DT
   checks or the handoff changes.

Prepare fresh ignored `boot035-omarchy-attempt22.json`/`.md` records with the source, procedure,
controller, payload and receipt hashes and the image digest. Push sanitized readiness in
`progress.md` and `coordination.md`, keeping live checks NOT RUN. Tell the human when ready.

## One human-started boot, filmed (view-only)

1. Both Macs on power, same direct cable. **Restart the M1 fresh**, keep it awake with
   `caffeinate -i`, and **re-seat the cable after the restart**. If the read-only gate still sees no
   device, boot the M5 into the Boot Lab again: in attempt 21 that cleared it when two re-seats did
   not. Close any serial tool. Keep the M1's lid open and the M1 unlocked for the whole upload,
   about 8 minutes.
2. **Start recording before the launch command.** The clip runs about 20 minutes: about 7.5 minutes
   of upload, then 10 minutes from the handoff. Use 1080p or better, with the phone on a charger and
   storage for at least 25 minutes. Frame the whole screen square-on and dim what the panel
   reflects. The m1n1 lines at the end of the upload are evidence (step 5).
3. The human saves work, shuts down the M5, holds power for startup options and selects
   **iLinux Boot Lab → Continue**. Keep Macintosh HD as default.
4. After the human reports `Running proxy...` and the gate passes, invoke this **once**:

   ```sh
   tools/m1n1-client/run.sh native/boot/launch.py \
     --package build/native-boot035-download/ilinux-j716c-boot035 \
     --profile omarchy --ramroot build/ramroot045/ramroot.cpio.zst \
     --launch --device auto --confirm BOOT-J716C-OMARCHY-ROOT
   ```

   * Within seconds the gates pass, the controller prints
     `Board/framebuffer PASS; allocating RAM for Omarchy RAM-root payloads.`, then
     `Uploading DT, initramfs and kernel to RAM.`
   * Then nothing for about 7.5 minutes (6–10 minutes is plausible). The client checksums every byte
     in Python before sending it, so the rate depends on the M1's CPU as well as on USB (Likely).
   * After the last byte, m1n1 checksums the 2.34 GB before it answers. That takes a few seconds
     (Likely); the client waits up to 15 s.
   * Then `RAM upload complete…`, the DT checks and the handoff line; exit 0. Exit 0 is not Linux
     success.
   * The 900-second deadline covers the whole launch. There is no `m1n1.setup`, shell, reconnect or
     automatic retry.
5. **From the video, if legible, copy these m1n1 lines** from the proxy screen. One appears before
   the upload, the rest at its end, before the handoff:
   * `Heap limit: 0x… (… MiB)`
   * `FDT: DRAM at 0x… size 0x…`
   * `FDT: Usable memory is 0x…..0x… (0x…)`
   * `FDT: initrd at 0x… size 0x…`

   They place the 2.34 GB in the M5's RAM, so the M5 session can check them against the carveout
   map. **The same screen prints `FDT: reporting device serial number: …`. Never transcribe,
   publish or share that line, or a frame that shows it.**
6. **Watch the M5 screen.** This root has never run natively, so everything below is a Hypothesis:
   * **While the kernel unpacks**: a black or nearly empty panel. The kernel unpacks 2.34 GB into
     8.56 GB of tmpfs on one CPU, which may take tens of seconds (about 30 s, Hypothesis). `quiet`
     hides kernel lines. systemd may print `[FAILED]` lines for `ufw` and `linux-modules-cleanup`;
     both are expected (no `nf_tables`, no modules for our kernel).
   * **Then Omarchy's desktop**, perhaps after a brief SDDM frame:
     * the default theme's wallpaper;
     * a thin bar along the top, small because Hyprland's automatic scale is 1 without an EDID;
     * its clock, showing a wrong time (no clock source);
     * when the first run finishes, two notifications at the top right, "Setup Wi-Fi" and
       "Learn Keybindings".
   * **Timing**: roughly **40–70 s after kernel start**. That is the VM's 195 s under TCG divided by
     job 039's 8.8–9.7× TCG-to-native ratio, plus about 30 s of unpack. Attempt 20's root reached its
     desktop at 8.5 s.
   * **View-only**: there is no keyboard or trackpad driver, so nothing opens the menu or an app.
     Omarchy's Stay Awake is on, so the panel should stay lit. The first-boot hardware service stops
     at its last step every boot (it asks for `omarchy-mac-boot`, which must never be installed). That
     is expected and does not show on screen.
7. **Stop criterion: 10 minutes from the handoff**, or earlier on a reset, a kernel panic or an M1
   panic. A black or text-only panel is **not** a reason to stop early, because this boot may take
   minutes. Keep filming to 10 minutes. Then the human powers the M5 off (hold power), selects
   **Macintosh HD → Continue** and confirms the usual desktop.

   | Controller / M5 screen | Meaning |
   |---|---|
   | A rejection before `Uploading…` (package, RAM root, gate, argument) | Report the line verbatim; no retry |
   | `STOP: Exception Out of memory` | The launcher ran without the `omarchy` heap (wrong profile or an old launcher). Report it; no retry |
   | USB transport error during the upload, or the M5 resets or returns to the boot picker during it | Note the elapsed time since `Uploading…`. A reset while writing points at the RAM range being written (Hypothesis: a live region within DRAM + 0.3–2.5 GiB). Power off, return, report |
   | `launch exceeded 900 seconds; do not automatically retry` | Slower than about 2.65 MB/s. Report the times of `Uploading…` and of the last line; no retry |
   | Handoff, then a reset within about a minute | The unpack or early boot failed. Note the time and any visible lines |
   | Text console with systemd errors or an emergency shell | Copy the visible lines verbatim |
   | Black for the whole 10 minutes, no reset | The display was not taken over (simpledrm, SDDM, Hyprland), or the boot stalled. Note the last visible frame |
   | **Wallpaper, bar, then the two notifications** | **As intended: the first installer-built Omarchy desktop on the M5.** Report the time from the handoff to the first desktop frame, to the bar and to the notifications. Report whether the clock advances and the panel stays lit to 10 minutes |
   | Desktop, then a dark panel | Idle blanking despite Stay Awake, or a crash. Note the time |
   | Any Hyprland or Omarchy notice on screen | Copy the text |

8. **Record**:
   * the controller result as in attempts 19 to 21: times, elapsed, exit, every gate, the
     prepared-DT argument check with m1n1's exact append, and the kboot reply;
   * the time between `Uploading…` and `RAM upload complete…`, and the upload rate it implies;
   * the m1n1 lines from step 5;
   * the panel timeline.

   Push the sanitized report and the progress and coordination updates. No media, raw target output,
   image or identifiers in Git.

## Privacy

* The image holds no SSH host key, pacman keyring or password, but it holds the build's
  machine-id. It travels by AirDrop and is never committed, uploaded or published.
* m1n1 prints the Mac's serial number on the panel while it prepares the DT (step 5). The video
  stays local, and frames that show it are never shared.

## Path toward Omarchy

This attempt puts Omarchy itself, as its installer builds it, on the M5's screen. It is view-only
and offline by design. The next steps are the USB link (boot040 investigates attempt 21's DMA
fault; the SSH-over-bulk link is VM-proven in job 046), then one boot that combines this root with
the USB kernel and that link, so the root can be reached over SSH, updated, and used by agents
running on the machine. Then the built-in keyboard and trackpad, storage and efficiency. See
`roadmap.md`.

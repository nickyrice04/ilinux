# Stage B attempt 22: the first installer-built Omarchy desktop on the M5, up about 39 s after the handoff and stable for the rest of a 10-minute film

2026-10-18 (handoff 6:26:30 PM Eastern, 2026-10-18T22:26:29.937Z). **One RAM attempt consumed.
Controller PASS, no host panic.** Omarchy itself, as its own installer built it (VM job 045, 865 packages,
SDDM → uwsm → Hyprland 0.56.2 → Quickshell), booted as a view-only RAM root on boot035 through the launcher's new
`omarchy` profile (3 GiB proxy-client heap, 900 s deadline). The M5's panel was filmed from the start of the upload to
628 s after the handoff.

* **Controller:** exit 0 in 460.186 s, handoff `22:26:29.937Z`, every gate PASS. The 2,382,558,042-byte upload took
  **456.5 s (5.22 MB/s)**, inside the checklist's 444-596 s estimate; the 3 GiB heap allocation that the default launcher
  refuses went through, and the M5 stayed up through the whole 7.6-minute write.
* **As intended (video):** a text console with systemd's `[ OK ]` lines at about +18 to +26 s, then Omarchy's desktop:
  **the default wallpaper, the top bar and the two notifications ("Setup Wi-Fi", "Learn Keybindings") by +39.5 s**
  (video 495 s; kernel start ≈ the handoff flash). The clock shows a wrong time, as the checklist predicted
  (`Thursday 23:46`).
* **Stable:** from the first desktop frame to the end of the clip (+628 s) the panel stayed lit and the desktop stayed up:
  a one-second brightness trace of 590 samples stays between 77 and 106 (106 only on the first frame), so there was no
  blackout and no Hyprland or SDDM restart; the bar's clock advanced `23:46` → `23:56`. The human adds that the clock kept
  increasing while its time and day were wrong, which matches the film.
* **No USB, by design:** the M1's host log shows m1n1's device destroyed 0.23 s after the handoff and no USB event for 13
  minutes; no M1 panic.
* **Not legible in the video:** m1n1's `FDT:` memory lines (they scroll past in the last second before the handoff, on the
  same screen that prints the Mac's serial-number line, which I did not open by eye); `Heap limit: 0x10010150000 (128 MiB)`
  was read by OCR from the proxy screen (three clean reads; two others differ by one character).
* Fresh policy/default checks: **NOT CHECKED.** No retry or settings change.

## Reviewed inputs and controller execution

* M5 handoff `7eb2aad` (root rebuild `b520330`); M1 readiness `9ebbdd1` (the launch ran on that commit, clean tree, record at
  0 attempts before the launch).
* The boot035 package, re-verified and not re-downloaded (archive 16,723,179 bytes, SHA-256 `81cbbd1c…`, SHA256SUMS digest
  `7635c5e4…`, clean client pin `57a9339`). The image: 2,337,897,871 bytes, SHA-256 `d00ba156…578a`, equal to
  `omarchy-root-manifest.json`; it reached the M1 by AirDrop into the repository root (untracked) and was moved into the
  ignored `build/ramroot045/` before any commit. **Its content was not decompressed or inspected on the M1** (no zstd tool); its
  zstd frame header was read (window 128 MiB, declared content size 8,561,316,352 bytes) and the build script was read in full.
* One invocation through `build/native-intake/run-attempt22.py` (the sanitized one-shot wrapper):

| Item | Result |
|---|---|
| Invocation count | 1 |
| Start / handoff UTC | 2026-10-18T22:18:49.983 / 22:26:29.937 |
| Elapsed / exit | **460.186 s / 0** |
| `Uploading…` to `RAM upload complete…` | 2.542 s to 459.000 s: **456.5 s, 5.22 MB/s** (estimate 476.5 s at 5 MB/s, 444.5 s at 5.36 MB/s) |
| Handoff after the last byte | 0.95 s (DT checks, DAPF correction, framebuffer descriptor) |
| Package, RAM root, operator key | PASS; `RAM root PASS` 2,337,897,871 bytes (VM job 045); `Operator key: none` |
| Fixed arguments / m1n1 append | `console=tty0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 pd_ignore_unused clk_ignore_unused quiet`; m1n1 appends `idle=nop arm64.nowfxt` |
| Primary interface, target | PASS: 1209:316d, CDC data interface 1; t6050, boot021 marker, no started secondaries |
| GPIO ADT | PASS: 221 pins / 7 groups, exclusions 5,6,7,112,141 |
| `allocating RAM for Omarchy RAM-root payloads` | PASS (the 3 GiB heap) |
| DAPF layout and correction; hardware DT; framebuffer descriptor | PASS (96-byte correction and 16-byte descriptor, readback verified) |
| kboot reply / USB close | PASS |

* **M1 host:** freshly restarted (uptime about 7 min at the launch; the launch waited until the CPU was 88% idle and the load
  average below 8), `caffeinate -di` running, no panic report during or after the run (the newest report on file is
  attempt 15's).

## Before the launch

The pre-flight and the read-only USB gate passed at 22:16:26Z (M1 uptime 4 min) on the first try after the fresh restart. The boot-time load average was 48; the launch waited about 2 minutes for it to fall. No port was opened and
nothing was sent before the launch at 22:18:50Z.

## Media and method

`Attempt22.MOV` (it arrived in the repository root and was moved into the ignored inbox before any commit): **1084.0 s,
1920×1080 landscape, 30 fps, original file** (2.16 GB). It starts about 4.5 s after the launch, on m1n1's proxy screen, so it
holds the whole upload, the handoff and the desktop to **+628 s**. The phone was fixed and the whole panel is in frame.

Time mapping: the brightness dip at video 455-456 s is the handoff, so **video ≈ handoff + 455.5 s (±1 s)**; the controller's
handoff stamp puts video 0 at 22:18:54.4Z. Reviewed locally with AVFoundation (a brightness trace every second, whole frames,
upscaled crops) and Apple's Vision text recognition. Vision returned nothing on whole frames and only garbage on upscaled crops
of the Linux console text, so the text below was read by eye; it works on m1n1's larger text, which is how the heap-limit line
was read. **The m1n1 screen also prints the Mac's serial-number line near the end of the upload: no frame of that screen after
the DT preparation began was opened by eye, the OCR helper withheld every row it could attribute to that line, and nothing from
it is in this report.** Review images deleted; the media stays local.

## M5 screen, literal observations

| Video s | After handoff | Observation |
|---:|---:|---|
| 2 | n/a | m1n1's proxy screen (`Running proxy...`, the USB blocks), ending in `Heap limit: 0x10010150000 (128 MiB)` (three clean OCR reads give `0x10010150000`; the two others, `0x10010f50000` and `0x10010150008`, differ by one character) |
| 0-454 | n/a | the same screen while the upload runs silently |
| 455-456 | 0 | handoff flash (brightness 61 → 36) |
| 463 | +7.5 s | five early error-level kernel lines at the top left, the same as attempts 19 and 20: `kvm_arch_timer: invalid virtual timer IRQ: 0` (0.030377) and `apple-pmgr-pwrstate 2300e0000.power-management:power-controller@0100: PS cs: Failed to reach power state 0xf (now: 0xf00000f)`, `PM: always-on PM domain cs is not on`, `pm_genpd_init failed`, `probe with driver apple-pmgr-pwrstate failed with error -22` (0.0607) |
| ≈ 473-482 | +17.5 to +26.5 s | systemd's console: green `[ OK ]` lines (Plymouth, `Reached target System Initialization`, CUPS, avahi, D-Bus, the Docker and OpenSSH `AF_UNIX` sockets, NetworkManager, `Starting Omarchy first-boot hardware setup deferred from the image build...`, `Started CUPS Scheduler.`); no `[FAILED]` line in the frames read (475.5, 478, 480.5) |
| 484-493 | +28.5 to +38 s | black panel |
| 494 | +38.5 s | the two notifications drawn on the black panel |
| **495** | **+39.5 s** | **wallpaper (a rocket launch), the thin top bar with a centred clock and the two notifications at the top right** |
| 500-1084 | +44.5 to +628 s | the same desktop. `Setup Wi-Fi` (`Click to configure the wireless network`) and `Learn Keybindings` (`Super + K for shortcuts`, `Super + Space for Omarchy Menu`) stay on screen. Clock `Thursday 23:46` at video 505 s, `Thursday 23:56` at 1082 s. Brightness trace 77-106 at one-second steps |

The checklist's expected unpack time (about 30 s) was too long: systemd's first console lines are on screen by about +17.5 s
(the luma rises at video 473 s), so the kernel unpacked the 2.34 GB image into 8.56 GB of tmpfs and reached systemd in at most
about 17 s on one CPU (Observed, ±1 s). The desktop came 22 s after that.

## M1-side observations (read-only)

* The host kernel log (filter: `usb-drd`, `AppleUSBHostPort`): m1n1's device destroyed at 18:26:30.165 (**+0.23 s**), then
  **nothing for 13 minutes**; at 18:39:46 the ports powered off and on (consistent with the M5 shutting down) and at 18:42:30
  a USB device named `Mac` enumerated (consistent with the M5 back in macOS; not independently verified).
* During the window the read-only monitor saw no new panic report and no USB device on the M1 (0 devices through the stop time).
* The M1 stayed healthy (load settled, no panic).

## Interpretation (bounded)

**Confirmed (video, M1 logs):**

* The `omarchy` profile does what its handoff said: a 2.38 GB upload in 456.5 s (5.22 MB/s), every gate PASS, no reset during
  the upload.
* **The installer-built Omarchy root boots natively on the M5 and shows Omarchy's own session** (SDDM autologin → uwsm →
  Hyprland → Quickshell, its first-run notifications) on simpledrm with software rendering and one CPU, view-only. It reached
  the desktop about 39.5 s after the handoff, against the VM's 194.8 s under QEMU TCG (a ratio of about 4.9).
* The desktop stayed up for the remaining 589 s of the film, with the panel lit and the clock advancing.
* The early error-level kernel lines are the same five as in attempts 19 and 20: cosmetic here, not new.

**Observed, meaning limited:**

* **Where the 2.39 GB landed:** the client heap starts at `0x10010150000` (m1n1's own heap limit as printed on its screen;
  DRAM + 0x10150000 ≈ 0.25 GiB if DRAM starts at `0x10000000000` as on earlier m1n1 screens), so the kernel, DT and initrd
  were written between roughly DRAM + 0.25 GiB and DRAM + 2.5 GiB without a reset. That range **overlaps the span (DRAM +
  0.56 to 1.79 GiB) where the macOS boot's carveout map lists regions**, and nothing reset or faulted: consistent with those
  regions not being live in this custom-kernel boot (Likely, not proven: a write into an idle region would not show, and m1n1's
  own memory lines were not legible to check the layout).
* The first desktop frame came after black seconds (+28.5 to +38 s) while SDDM, uwsm and Hyprland started; the notifications are
  drawn before the wallpaper.
* `quiet` hides the kernel log, so the film cannot show whether any unit failed (ufw and linux-modules-cleanup were expected to).

**Not established:** performance (the clock and a moving wallpaper cannot measure it), power, thermals, GPU acceleration,
input (there is no driver), whether Omarchy's first run and the hardware service finished or stopped where the report says,
what runs beyond 628 s (Stay Awake was on), m1n1's `FDT:` memory lines, and the root's content (not inspected on the M1).

## Return and next handoff

* The human powered the M5 off and returned it to Macintosh HD (reported: "powered off and back on the Macintosh HD desktop";
  the M1's host log fits it). The human's first message about what the panel showed arrived empty; a later note says that the
  clock on the Omarchy desktop kept increasing while its time and day were wrong (no clock source: it starts at the same
  `Thursday 23:4x` as attempt 20's root). The video is the evidence for everything else. Fresh
  policy/default/installed-object checks: **NOT CHECKED.** Attempt 22 is consumed; no retry or settings change. The fixed E1
  probe is still **NOT RUN**.
* **For the M5 (proposals, not authorization):**
  * the unpack is faster than assumed (about 17 s, not about 30 s): the next USB-link attempt can expect systemd within about
    20 s of the handoff, and the desktop about 40 s after it;
  * once boot040 fixes the DMA fault, the combined boot (this root on the USB kernel with the SSH-over-bulk link) is the next
    step; it makes the root reachable for measurement and updates, and a two-stage delivery shortens the 7.6-minute upload;
  * if the `FDT:` memory lines are still wanted, the human can read `FDT: DRAM at`, `Usable memory is` and `initrd at` from
    video 453-455 s (about 1 s of footage) to you, **never the serial-number line**, so the carveout map can be checked;
  * for the next film, a 4K recording or a larger console font would make the early console text easier to read; the desktop
    itself needs neither.

No media, image, raw target output, `ioreg` dumps or identifiers beyond the fixed hardware names are committed. Earlier
reports are unchanged except one sentence in attempt 21's about the text recognition.

# Stage B attempt 19: the first native Omarchy desktop on the M5 (boot035 + the Arch RAM root, view-only)

2026-10-16. **One RAM attempt consumed. Controller PASS, no host panic.** Hyprland came up
on the M5's own screen and stayed up.

* **Controller:** exit 0 in 44.441 s, handoff 2026-10-16T23:21:09.364Z, every gate PASS. The
  226,753,047-byte upload took **42.28 s (5.36 MB/s)**, inside the 45-57 s estimate's range
  (just under it).
* **The desktop:** the wallpaper is first visible at video 6.9 s; the RAM root's own status
  terminal prints **`desktop ready 7.79 s after kernel start`**; waybar is live (CPU reading
  100% at 12 s, 28% at 30 s, 1% at 39 s; memory 2.3G to 2.4G); a foot terminal fills the screen
  below it with a shell prompt. Rendering is software (`display card0 on simple-framebuffer`).
* **A cosmetic warning:** a red Hyprland notification, **"Hyprland was started without
  start-hyprland. This is strongly discouraged unless you are in a debugging environment."**,
  is visible at 12 s and gone by 24 s.
* **View-only, as designed:** no keyboard or trackpad support; the pointer sits at the screen
  centre. No USB device appeared on the M1 after the handoff (the boot035 DT has no USB
  controller): the M1 saw only m1n1's device disconnect 0.2 s after the handoff.
* **Steady:** the clip is only 39.5 s, but the human reports the desktop still up when they first
  looked a few minutes after the handoff and again at a later clock check (after 23:29Z, more
  than 8 minutes after the handoff), **with the clock advanced** (it read `Thursday 23:46` in the
  clip). Those checks are human reports, not filmed.
* **Early kernel error lines** were caught in the first frame (below); effect unknown.
* Fresh policy/default checks: **NOT CHECKED.** No retry or settings change.

## Reviewed inputs and controller execution

* M5 handoff `59b12a0`; M1 readiness `9ff7687` (the launch ran on that commit, clean tree).
* The boot035 package, re-verified against the Git pin and not re-downloaded: archive 16,723,179
  bytes, SHA-256 `81cbbd1c…`, manifest digest `7635c5e4…`, Image `1131a1af…`, Stage-B DT without
  USB controllers.
* The RAM root `ramroot.cpio.zst`: 182,092,876 bytes, SHA-256 `58bdc6ce…a27e` (VM job 039 run 30);
  it reached the M1 by AirDrop into the repository root (untracked, not ignored) and was moved
  into the ignored `build/ramroot/` before any commit. **Its content was not decompressed or
  inspected on the M1** (no zstd tool, nothing installed): it is pinned by size, digest and zstd
  frame magic only.
* One invocation through `build/native-intake/run-attempt19.py` (fsync per checkpoint; printed
  deadline 600 s; the launcher's own deadline 300 s):

| Item | Result |
|---|---|
| Invocation count | 1 |
| Start / handoff UTC | 2026-10-16T23:20:25.143 / 23:21:09.364 |
| Elapsed / exit | **44.441 s / 0** (upload 42.28 s) |
| Package, RAM root, operator key | PASS; `RAM root PASS 182,092,876 bytes`; `Operator key: none` |
| Fixed arguments / m1n1 append | `console=tty0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 pd_ignore_unused clk_ignore_unused quiet`; m1n1 must append `idle=nop arm64.nowfxt` |
| Target, marker, secondaries | PASS: t6050, boot021 marker, none started |
| GPIO ADT | PASS: 221 pins / 7 groups, exclusions 5,6,7,112,141 |
| Board/framebuffer, DAPF layout and correction | PASS |
| Final hardware DT, framebuffer descriptor | PASS |
| kboot reply / USB close | PASS |

* **M1 host:** freshly restarted (uptime about 5 min at the launch), `caffeinate -i` running, no panic
  report during or after the run (the newest report on file is attempt 15's).

## Before the launch

After the human's fresh restart the pre-flight and the read-only USB gate passed at 23:15:50Z on the
first try (the human had re-seated the cable as the checklist asks, and booted the M5 into the Boot Lab
last). The M1's load average was 292 at 2 minutes of uptime, so the launch waited about 4.5 minutes
(CPU 79% idle, 1-minute load 12) so that the roughly 227 MB upload would not be slowed. No port was
opened and nothing was sent before the launch at 23:20:25Z.

## Media and method

`Attempt19.MOV`: **39.530 s, 1080×1920 (oriented), 30 fps, original file** (68 MB), user-supplied. It
was saved in the repository root (untracked) and moved into the ignored inbox before any commit. Its
creation time equals the handoff second, so **the clip starts at kernel ≈ 0.07 s and holds neither the
upload nor the handoff**; the first frame already shows kernel lines stamped 0.030-0.060 s. Video time ≈
kernel time within 0.5 s. The phone was moved during the first ≈ 10 s (blurred frames), then held steady.
The screen appears sideways inside the portrait frame from about 7 s; the review rotated those frames.
Reviewed locally with AVFoundation: brightness traces, overview frames and upscaled crops; the status
block is fully legible once the phone is steady. Review images deleted; media stays local.

## M5 screen, literal observations

| Video s | Observation |
|---:|---|
| 0.5 | Kernel lines at the top left: `[ 0.030277] kvm [1]: kvm_arch_timer: Invalid virtual timer IRQ: 0`; `[ 0.060286] apple-pmgr-pwrstate 2300e80000.power-management:power-controller@108: PS cs: Failed to reach power state 0xf (now: 0xf00000f)`; `[ 0.060299] PM: always-on PM domain cs is not on`; `[ 0.060300] … pm_genpd_init failed`; `[ 0.060301] … probe with driver apple-pmgr-pwrstate failed with error -22` |
| 1-6.7 | dark screen, brightness 40-44 |
| **6.9** | **first desktop frame**: the blue wallpaper (brightness jumps 43 → 109) |
| ≈ 8-10 | waybar and the status terminal appear; the phone is being moved (blurred) |
| 12 | steady: waybar with the clock `Thursday 23:46` at the centre and `usb`, `100%`, `2.3G` at the right; the red notification at the top right; the status block and prompt below |
| 22-26 | the notification leaves (brightness falls 82 → 67) |
| 30 | CPU `28%` |
| 39.3 | CPU `1%`, memory `2.4G`, clock still `Thursday 23:46` (end of clip) |

The status block, read at 33 s (digits legible at this zoom):

```
iLinux RAM root: Omarchy-style desktop
kernel   7.1.9-g863199d8b4a3-dirty, 16384-byte pages, 1 CPU
display  card0 on simple-framebuffer
usb
memory   2345 MiB used, 127005 MiB available of 129351
desktop  ready 7.79 s after kernel start

[omarchy@ilinux-m5 ~]$ █
```

* The `usb` line is empty and the waybar `usb` module shows a crossed icon: no UDC, as expected.
* The clock shows the wrong day and time, which is expected with no clock source in the RAM root. It did not
  change within the 27 s between the first and last steady frames (a minute boundary may simply not have
  fallen in the clip); the human reports it advanced later.
* The waybar CPU and memory readings changed between frames, so waybar was running and updating.

## M1-side observations (read-only)

* No USB device appeared on the M1 after the handoff. The host kernel log has one line: m1n1's device
  destroyed (`hardware connection lost`) 0.21 s after the handoff. `ioreg` showed the three controllers with
  nothing attached at +10 s, +8 min and later.
* The M1 stayed healthy (load settled, no panic).

## Interpretation (bounded)

**Confirmed:**

* An Arch userspace booted on the M5 and started a Hyprland session on `simpledrm` with software rendering:
  wallpaper, waybar and a terminal appeared on the panel about 7 s after kernel start, and the desktop was
  still up, with an advancing clock, when the human looked 8 to 10.7 minutes after the handoff
  (human-reported; the exact time of the check was not recorded).
* The path needs no USB link: the image arrives through the m1n1 proxy before Linux starts.
* The release ladder is hidden by `quiet` (not observed here). Attempts 16-18 completed it at 45-57 s kernel
  time with the same boot035 DT, and the desktop outlived that time (human-reported), so releasing the display
  extension domains did not take the display down (Likely).

**Not established:** performance (frame rate, latency, CPU use under load), power and thermals, stability
beyond what the human watched, any failed systemd unit, anything about input, storage, networking, USB, SMP or
GPU acceleration. This is a RAM boot with one CPU and software rendering. No parity claim.

**Observed, effect unknown (for the M5 agent):**

* The Hyprland warning means the session script runs `Hyprland` directly instead of `start-hyprland`.
* The five early error-level kernel lines in the first frame (`kvm_arch_timer: Invalid virtual timer IRQ: 0`;
  the `apple-pmgr-pwrstate` controller at `2300e80000` (`power-controller@108`) failing to bring the `cs`
  domain to power state 0xf, `pm_genpd_init failed` and probe error -22). I cannot tell whether earlier attempts
  printed them, since those clips began after the console had scrolled.

## Return and next handoff

* The human reported the desktop and the clock, powered the M5 off and returned it to the Macintosh HD desktop
  (reported, not independently verified). Fresh policy/default/installed-object checks: **NOT CHECKED.** Attempt 19
  is consumed; no retry or settings change. The fixed E1 probe is still **NOT RUN**.
* **For M5 (proposals, not authorization):**
  * start Hyprland through `start-hyprland` (or the session wrapper) to remove the warning;
  * with no input and no USB link, the screen is the only output channel, so let the RAM root print its own
    measurements on the terminal: for example a single-thread run of the repository's portable C benchmarks at
    startup, a visible uptime counter and the tail of the kernel log (`quiet` hides the release ladder), so a
    filmed 10-minute run carries numbers and shows stability;
  * the USB link (boot039, bulk-only) remains the route to SSH-based measurement; the M1 can build and
    offline-test a user-space reader once the function is chosen;
  * filming: the glossy panel mirrors the room, so the phone's position matters; keep it fixed from the start
    and begin recording before the launch so the upload and handoff are in the clip.

No media, raw target output, RAM-root image or identifiers beyond the fixed gadget ones are committed.
Earlier reports are unchanged.

# Stage B attempt 26 (the M5's own keyboard, on boot042): the keyboard switches on over SSH and types on the M5; every screen update costs the one CPU about half a second, which is the lag and, reproduced on demand, the repeated letters

2026-10-19 (handoff 8:39:17 PM Eastern, 2026-10-20T00:39:17.261Z). **One RAM attempt consumed. Controller PASS, no host
panic.** boot042's package with the launcher's `omarchy` profile and the job 045 Omarchy root with the keyboard modules. No film of the
whole run was supplied; the human typed on the M5, reported in chat, and sent two things: a **33.6 s phone clip** of the M5's screen showing the
slow response and a **photo** of the first seconds of boot (five early kernel lines). The M5 stayed up **63 min 34 s** from the handoff
until the human powered it off or restarted it (confirmed in chat), the longest native run so far (attempt 25: 15 min 39 s of link).
Most of the time after the keyboard result went into one question the human raised, why the desktop feels so slow, and into two
runtime-only A/B tests on the M5 that they approved in chat (listed below).

* **Controller:** exit 0 in 476.856 s (upload 473.4 s for 2,480,000,463 bytes = 5.24 MB/s), handoff `00:39:17.261Z`, every gate PASS,
  including `Hardware DT PASS` for the new MTP nodes (go/no-go 1).
* **The new hardware step passed (go/no-go 2):** the built-in DART driver probed the MTP's DART (`294800000.iommu`, t8110-class v2.4,
  16 streams, DMA window limited to `0x10000004000..0x100ffff3fff`, `locked: 0`, "initialized") at kernel 0.070 s; no freeze, reset or
  fault line followed.
* **The link:** enumerated at **+19.67 s** (`1d6b:0104`, `bcdDevice 0x0039`); configuration 1 was selected 5 ms later with **no
  "transport restrictions" line** (the accessory approval from attempt 25 persisted; Likely); both interfaces published, no macOS driver
  bound. The reader ran on interface 0 and **22 `usb-pipe` SSH sessions** on interface 1 (banners in 426 to 771 ms, the longest 258 s,
  303,496 bytes to the M5 and 211,908 from it). **63 min 14 s of link with no kernel fault line** (no `BUSERR`, `translation fault`,
  `nobody cared`, oops, call trace, segfault or out-of-memory line in 205,394 bytes of journal).
* **The attempt-25 fixes work:** `BROWSER` is the no-op `ssh-browser`, `archlinux-keyring-wkd-sync` is masked (0 lines in the journal,
  75% of attempt 25's), the unused ports' sshd waits for its tty without restarting, and **no Chromium** ran (0 journal lines; 0 Google
  CDN downloads at the proxy, against 22 and 30.9 MB in attempt 25). The clock step passed (25.0 days behind, then 2.3 ms behind; round
  trip 5.0 ms), web access through the M1 worked, `claude --version` 2.1.304, passwordless `sudo`.
* **The keyboard switched on, over SSH, in 1.4 s** (`sudo ilinux-keyboard`, steps 0 to 5 PASS at kernel 114.09 to 115.47 s): RTKit
  started the MTP CPU ("MTP Says Hello", firmware `AppleMTPFirmwareMac-5340.61.4~502`), the DockChannel FIFO bound, `hid-apple` loaded, the
  ring transport registered (2 MiB at iova `0x100ffc00000`), five interfaces were announced, and **`/dev/input/event0` "Apple MTP
  keyboard"** exists (Hyprland sees it). Step 6 with the human typing: **49 key presses, Enter, the word `omarchy` as on a US layout:
  yes.** No multi-touch or trackpad device exists (the interface is announced, no input node; expected).
* **Typing on the M5's screen works but is slow and repeats letters** (human-reported, below). **Measured:** the keyboard path is clean
  (every tap seen once, held 44 to 88 ms, no kernel repeat on any letter, events read within 5.2 ms of their kernel stamp); the cause
  is the desktop: the one CPU stays at 91 to 100% for 0.8 to 6 s after almost every key, about 90% of it user-space time, most of it
  Hyprland's main thread, which draws the 3456×2160 screen in software; **a screen update costs about 0.47 s and the key release waits
  behind it, longer than the terminal's 250 ms repeat delay, so the terminal auto-repeats about 14 times per tap** (134 to 152
  characters for 10 taps in seven runs). **Raising the repeat delay to 1000 ms gave exactly 10 of 10 characters (two runs) and halved the
  CPU per tap.**
* Fresh policy/default checks: **NOT CHECKED.** No retry or settings change on the Mac. Attempt 26 is consumed.

## Reviewed inputs and controller execution

* M5 handoff `b8c877c` (release target `a1cc21a`); M1 readiness `dc1540a` (the launch ran on that commit, clean tree, record at 0
  attempts before the launch). Intake and the offline review are in `coordination.md` (readiness entry for attempt 26).
* The image (`build/ramroot045-boot042/ramroot.cpio.zst`, never committed): 2,435,320,732 bytes, SHA-256 `565644be…bf6f`, equal to the pin;
  read from the image itself before the run (four kernel modules, no storage module, no private key or credential).
* One invocation through `build/native-intake/run-attempt26.py` (attempt 25's wrapper with four lines changed), started detached so
  that no tool timeout could cut the 8-minute upload:

| Item | Result |
|---|---|
| Invocation count | 1 |
| Start / handoff UTC | 2026-10-20T00:31:20.405 / 00:39:17.261 |
| Elapsed / exit | **476.856 s / 0** (`Uploading…` +2.51 s, `RAM upload complete…` +475.90 s, `Hardware DT PASS` +476.82 s, handoff +476.86 s) |
| Package, mode | PASS; `RAM root PASS: 2,435,320,732 bytes…`; `Mode: LIVE RAM LAUNCH` (`--profile omarchy`, deadline 900 s) |
| Boot arguments | `console=tty0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 pd_ignore_unused clk_ignore_unused quiet` (m1n1 appends `idle=nop arm64.nowfxt`) |
| Primary interface, target | PASS: 1209:316d, CDC data interface 1; t6050, boot021 marker, no started secondaries |
| GPIO ADT, board/framebuffer, DAPF layout and correction | PASS (221 pins / 7 groups, exclusions 5,6,7,112,141; RAM correction applied) |
| Final hardware DT, framebuffer descriptor | PASS (CPU topology, AIC3 and timer routes; 16-byte descriptor, readback verified) |
| kboot reply / USB close | PASS |

* **M1 host:** restarted before the attempt (uptime 938 s at the launch), `caffeinate -di` running, the read-only gate passed on the first
  try, no panic report during or after the run. The reader is the unchanged attempt 21 to 25 binary (`77677ee3…`); `usb-pipe` and the
  proxy are attempt 25's. The reader's first run hit its 1800 s limit (171,139 bytes, 1,892 records, journal 17.0 to 1,757.1 s) and a
  second run took over (34,255 bytes, 330 records, journal 1,845.5 to 3,767.8 s; the journal was quiet for 88 s between them) and ended
  with "the device went away" when the M5 did.

## Media and method

**No film of the whole run was supplied.** Two items from the human, both kept local (never committed): a **phone photo** of the M5's screen right after the
upload, with five early kernel lines at the left and, below them, a blue and green shape at the screen's left edge (not identified; the
lines are the ones in the table below), and **`Attempt26-ExampleOfSlowResponse.MOV`**, 33.6 s, 1080×1920 (oriented), 30 fps, 67 MB, a phone
clip of the M5's screen (ignored inbox). Its frames show the wallpaper and then a mostly blue full-screen window; the text is not
legible at the phone's resolution, so the clip is context for the human's description, not a measurement. It shows no sign-in or
personal data. The review frames were deleted.

**What the M1 did on the M5 (all through the SSH byte pipe):** read-only checks at the start (the checklist's session checks);
`sudo ilinux-keyboard` (steps 0 to 5); step 6's reader on its own after a rerun of the script failed (below); then a set of
measurement tools written for this run (committed afterwards, with small edits, as `tools/m1n1-client/m5-probes/`: `keytiming.py`,
`inspect_desktop.py` (was `inspect_m5.py`), `frame_probe.py`, `tap_ab.py` (was `ab_m5.py`), `tap_ab_repeat.py` (was `ab2_m5.py`)):

* `keytiming.py` (as root, **read-only**): reads `/dev/input/event0` without grabbing it and `/proc`; prints each key event with its kernel
  timestamp and its delivery lag, the CPU's busy share every 0.1 s and which processes used the CPU every 0.25 s (its own cost: about 1%).
  The first run ended at the human's Super+Return because my script treated Return as its finish key (fixed: Return with Super held does not
  end it); the per-kernel-worker numbers of that first run were inflated by a bookkeeping bug (a worker that renames itself was counted
  from zero; fixed and unit-tested); the second run is the one used here.
* `inspect_m5.py`, `frame_probe.py` (read-only): load, process CPU totals, Hyprland's threads, mapped graphics libraries, options, layers.
* **Two A/B runs the human approved in chat before each** ("Yes, run the animations on/off A/B on the M5. I'll keep my hands off its
  keyboard." and "Yes, run the repeat-delay and small-window tests on the M5…"). They **changed the running session only, nothing saved,
  and restored everything**: stopped the three leftover `omarchy-menu-select` processes (once), set Hyprland's `animations.enabled` false
  then true and `input.repeat_delay` 1000 then 250 through `hyprctl eval hl.config(...)` (this Hyprland's Lua config API; the old
  `dispatch`/`keyword` forms are refused: a first attempt failed on that at its first command and changed nothing), opened and closed
  terminals through `hl.exec_cmd`, made one a 600×400 floating window, and sent keys with `hl.dsp.send_key_state` (a press, 75 ms, then
  the release, as a real tap). Each terminal ran a one-line script that wrote what it received to a file in `/tmp` (removed
  afterwards), so the characters that reached it are counted exactly. At the end `animations.enabled` was true, `repeat_delay` 250,
  `repeat_rate` 40, no window open, the leftover processes gone.

Time bases: journal seconds are the M5's journald receipt times, with journal 0 about 0.2 s after the handoff (`T0`). **The early kernel
lines are replayed by journald with the time it started (17.0 s), not their kernel time** (the human's photo shows 0.03 to 0.06 s); the
kernel's own times come from the dmesg lines `ilinux-keyboard` printed.

## M5 journal and link, literal observations

| Journal s (T0 + s) | Observation |
|---:|---|
| 17.0 (kernel 0.03 to 0.06) | **the five early error lines the human photographed**, as in attempts 19, 20, 22 and 25: `kvm [1]: kvm_arch_timer: invalid virtual timer IRQ: 0` (KVM stops there; no "Hyp mode" line follows), and for the PMGR domain `cs` (`apple-pmgr-pwrstate 2300e80000…power-controller@108`): `PS cs: Failed to reach power state 0xf (now: 0xf00000f)`, `PM: always-on PM domain cs is not on`, `pm_genpd_init failed`, `probe … failed with error -22`. One warning-level line precedes them in the journal and is not on the screen (`quiet`): `always-on domain cs is not on at boot`; the domains `nub_spmi_a2` and `afr` get the same warning and show **no** failure line |
| 17.02 | seven `apple-dart` lines: the six USB DARTs as in attempt 24 and the MTP's `294800000.iommu` (v2.4, `1 clients, fault IRQ 45`, `locked: 0`) |
| 19.31 / 19.36 / 19.39 | `usb-gadget.sh`: three gadgets bound (ports 1 to 3: `Bulk-only kernel log port + SSH byte pipe`; the cabled port 1 uses `ttyGS2` for the log and `ttyGS3` for sshd) |
| 26.64 to 26.77 | SDDM started, `Reached target Graphical Interface`, logind sessions 1 and 2 |
| 27.65 | Hyprland starting (`Creating the AnimationManager`); the desktop is up about 27 to 31 s after the handoff, as in attempt 25 |
| 30.4 to 32.5 | the Qt shell and the wallpaper daemon: `MESA-EGL: warning: failed to get driver name for fd -1`, `MESA: error: ZINK: vkCreateInstance failed (VK_ERROR_INCOMPATIBLE_DRIVER)`, `egl: failed to create dri2 screen`, `owed … renderer start failed` (no GPU driver; Mesa falls back to software) |
| 52.13 | first SSH login; `ilinux-clock: set from the M1 over SSH: was 2026-09-24T23:46:39Z, now 2026-10-20T00:40:09Z, moved 2163210 s` |
| 114.0 | the keyboard bring-up session (kernel 114.09 to 115.47 s, below) |
| 405 to 739; then 2,011, 2,373, 3,224 on | `xdg-terminal-exec` launches by `uwsm-app`: 19 in all (the human's Super+Return presses early on, then the measurements) |
| every ~47 s | the idle sshd on the cabled port 3 (`ttyGS3`) ends after its 45 s grace time and is restarted (four lines each; 67 restarts in the run); 22 more `Failed with result 'exit-code'` lines are the end of each SSH session |
| 3,767.75 | the last record (the link ended 46 s later) |

**Failed units:** `omarchy-provision-hardware` (a deferred hardware step, exit 75) and `ufw` (`iptables-restore … Failed to initialize nft:
Protocol not supported`: the kernel has no nf_tables), as in attempt 25 minus `linux-modules-cleanup`; `xdg-document-portal`'s FUSE mount
also fails. The M5 reported one CPU and 132,456,016 kB (126.3 GiB) of memory; `/sys/devices/system/cpu` lists `possible`, `present` and
`online` as `0` (`nr_cpus=1`). `dmesg` held no fault, oops or call-trace line.

## The keyboard bring-up, literal

`sudo ilinux-keyboard` at 00:41:11Z:

| Step | Result |
|---|---|
| 0 preconditions | PASS: kernel `7.1.9-g863199d8b4a3-dirty (ilinux@boot042)`, the four module digests, the MTP nodes and keyboard alias, the MTP DART bound with an "initialized" line and no fault since boot |
| 1 `apple-rtkit-helper` | PASS: `RTKit: Initializing (protocol version 12)`, the MTP firmware's syslog (`MTP Says Hello`, `Version: AppleMTPFirmwareMac-5340.61.4~502`, `Personality: MTP_SYS`, `SDK: 25G74`, `Built on: 2026-07-31`), interfaces `comm`, `multi-touch`, `keyboard`, `stm`, `actuator`, `tp-accel`, `mtp` initializing; six "Unknown oslog message" lines |
| 2 `apple-dockchannel` | PASS: `294b14000.fifo` bound, child `294b30000.input` created ("Adding to iommu group 0") |
| 3 `hid-apple` | PASS |
| 4 `dockchannel-hid` | PASS: `M4/M5 ring transport: 2097152 bytes at iova 0x00000100ffc00000`, `Initialized, awaiting packets`, management events for the five interfaces, `Interface keyboard is now ready`, `input: Apple MTP keyboard as …/input0`, `apple 0019:05AC:035A.0003: input,hidraw1: HOST HID v5.10 Keyboard [Apple MTP keyboard]`, then `Ring registered … 2097152 bytes`; `No OF node for subdevice mtp, ignoring` |
| 5 input devices | PASS: `/dev/input/event0: Apple MTP keyboard`; `hid-generic` on `stm`; **no driver on `multi-touch`, `actuator`, `tp-accel`**; Hyprland lists `apple-mtp-keyboard` |
| 6 typing | run on its own (below): **49 presses, Enter, the word as on a US layout: yes** |

* **A rerun of `ilinux-keyboard` fails at step 4** ("dockchannel-hid did not initialize") although all four modules stay loaded and
  the keyboard keeps working: its step-4 check reads only kernel lines newer than the step's start, and a loaded driver prints none.
  Nothing was unloaded or changed. Step 6 was therefore run as its own read-only reader (the script's own Python, standalone).

## The slowness, measured

The human's report (below) was the reason for this part. All numbers are from the M5 over SSH; Hyprland 0.56.2 with the Lua config
provider, one output `3456×2160@60`, scale 1, `XRGB8888`, `simpledrm` only.

**1. Key timing at the kernel (the second `keytiming.py` run, 250.7 s, 157 events; the human did Super+Space ×3, Super+K ×2, Super+Return,
typed `hello` slowly, Super+W, then Enter):**

| Fact | Value |
|---|---|
| Presses / kernel autorepeat events | 20 / 117, **all repeats on the held Super key**, none on any letter |
| Held time of a tap (press to release) | letters 44 to 88 ms (`h` 44, `e` 76, `l` 75, `l` 81, `o` 74, `w` 88); Space 60 to 80; Enter 46 and 76; `k` 68 and 76 |
| Delivery lag (read minus the kernel's stamp), 157 events | min 0.0, median 0.0, **max 5.2 ms**, even while the CPU was at 100% |
| CPU busy (≥ 50% in 0.1 s samples; 91 to 100% inside the stretches) after a key | Super+Space 2.8 s / 0.8 s / 1.0 s; Super+K 4.1 s then 0.8 s; Super+Return 2.3 s; the first letter in the new terminal **6.1 s**; each later letter about 1.8 s; Super+W 1.1 s |
| Split in the busy stretches | user 86 to 95%, system 4 to 8%, irq 0 to 1% |
| Who | Hyprland's main thread: 19.1 s of the run's 250.7 s (its total since boot: 2 min 44 s in 44.5 min); the new terminal (`foot` and its shell) used **111 ms of CPU in its 92-second life** (journal) |

(The first run, Super+Space ×3 then Super+Return, agrees: 0.8 to 2.9 s of full CPU after each press, 2.2 s after Super+Return.)

**2. What Hyprland is.** One main thread (plus four idle `disk$` workers); **`libLLVM.so.23.1`, `libgallium-26.2.4`, `libEGL_mesa`,
`libGLESv2` and `pixman` are mapped into it**: Mesa's LLVM software rasterizer, since there is no GPU driver (Likely). Options now:
animations on, blur and shadow off, rounding 0, `debug:damage_tracking` 2 (full), no screen shader, `render:cm_enabled` true,
`repeat_rate` 40, `repeat_delay` 250. **Layers drawn every frame** (`hyprctl layers`, all from the Qt shell): a full-screen
`omarchy-background` (3456×2160), a full-screen `omarchy-notifications` overlay (3456×2160), `omarchy-bar` (3456×26) and `omarchy-dock`
(3456×207), plus the window.

**3. Leftover menu processes.** Each Super+K ran `omarchy-menu-keybindings` → `omarchy-menu-select Keybindings`, whose last lines wait
`while [[ ! -e $done_file ]]; do sleep 0.05; done` after `omarchy-shell shell summon omarchy.menu`. **Three selectors were still alive**
(started 2,452 s, 2,403 s and 339 s earlier): the done file never appeared (why is Unknown). Each `sleep` is a fork: **idle busy went from
0% (before the first Super+K) to 6.7 to 11.6%**, 13.9 s of CPU ("children of omarchy-menu-select") in the 250 s run.

**4. The A/B (animations, pollers, repeat delay, window size).** Each cycle: open a terminal, five isolated taps (each waited out), five
taps in a quick burst (150 ms apart), Enter. "Release wait" is how long Hyprland took to answer the release request sent 75 ms after
the press (the time the release sat in its queue). Means over the stated samples; Hyprland CPU is for the stretch the CPU stayed busy:

| Phase (cycles after a warm-up) | Hyprland CPU per isolated tap | Release wait | 5-tap burst | Open a terminal | Enter (closes it) | Characters received for 10 taps |
|---|---:|---:|---:|---:|---:|---:|
| A: as found (animations on, 3 leftover pollers, delay 250 ms), 2 cycles + warm-up | 1.12 s | 0.51 to 0.53 s | 5.31 s | 1.00 s | 1.43 s | **152, 151, 151** |
| B: pollers stopped (idle busy 0.3%) | 1.12 s | 0.46 to 0.48 s | 5.57 s | 1.27 s | 1.17 s | 136, 134 |
| C: B + animations off | 1.12 s | 0.46 to 0.47 s | 5.31 s | 1.05 s | 0.85 s | 135, 134 |
| D: B + `repeat_delay` 1000 ms | **0.53 s** | 0.47 s | **2.66 s** | 1.29 s | 0.91 s | **10, 10** |
| E: B + a 600×400 floating terminal, delay 250 ms | 0.59 s | **0.23 s** (0.35 first tap, 0.19 to 0.20 after) | 2.79 s | 1.29 s | 1.09 s | 29, 30 |

Reading (details under Interpretation): the arithmetic fits, (0.075 s hold + 0.5 s release wait − 0.25 s delay) × 40 repeats/s ≈ 13, plus
the tap itself; the repeated characters cost a second frame (1.12 s per tap with them, 0.53 s without); animations changed nothing for
typing; the pollers cost about 9% of a frame; a small window shortens the frame and leaves the CPU per tap about the same (0.53 s
against 0.59 s).

## M1-side observations (read-only)

Times relative to the handoff `T0 = 00:39:17.261Z` (the host log is local Eastern time, UTC−4):

| +s | Event |
|---:|---|
| +0.23 | m1n1's device destroyed (`hardware connection lost`) |
| +19.67 | enumerated `0x1d6b/0104/0039`, "iLinux J716c control channel, port 1", 480 Mbps; configuration 1 selected 5 ms later; **no "transport restrictions" or "will not be registered" line** |
| +19.67 | `Google Chrome` (on the M1) tried to open the device and was refused ("already opened for exclusive access"); benign |
| +20.0 | the reader opened interface 0 (identity "RAM root, `bcdDevice 0x0039`") |
| +52 to +3,700 | 22 `usb-pipe` sessions (0.5 s to 258 s) |
| +3,813.77 | endpoint 0x81 reports a transaction error (+3,813.7 s), then **`terminateDevice … hardware connection lost`** at +3,813.77 s: the human's power-off or restart; the reader ended ("not responding", exit 0) |
| +3,813.8 to +3,822 | two port power-off/on cycles 6.9 s apart |
| +3,845.32 | **a macOS device named "Mac" (`0x05ac/1905`) enumerates at the port**: the M5 is running macOS again (the human has not said so in words) |

* **The host log for the device (730 lines):** 680 endpoint-0x81 read timeouts (the reader's 5 s polls while the journal was idle), 22
  endpoint-0x82 read timeouts and 22 aborts (one pair per `usb-pipe` session: its own 400 ms quiet read at banner sync), the
  enumeration and configuration lines, Chrome's refused open, the final transaction error and disconnect. **Nothing else.**
* `ioreg` at +20 s, +120 s, +300 s and +600 s (saved locally): one device, `AppleUSBHostCompositeDevice` and an
  `AppleUSBHostDeviceUserClient` (the accessory approval), two `IOUSBHostInterface` nubs (255/0/0, two endpoints each), interface 0 held
  by `[bulk-log-reader]`, interface 1 with no driver.
* **The proxy** (localhost only): 8 connections, all `ok`: my one `archlinuxarm.org` test; and **the Omarchy weather widget, every 30
  minutes** (`wttr.in` ×4, `api.open-meteo.com` ×3, at :09:50 and :39:50), which uses the M1's relay by itself.
* The M1 stayed healthy: no panic report, load settled.

## From the human (their words, paraphrased; human-reported, not measured)

After the keyboard steps: *the keyboard is working, but everything is so slow it would be an unusable experience.* The key bindings'
menus (Super+Space, Super+K) take about two seconds to appear; Super+Return opens a terminal but slowly. Typing `omarchy` gave several
`o`s ("ooooooomarchy"), and in the clip `hello` repeated several letters; a terminal opened with roughly a two-second delay, a second one
opened, and closing was fairly quick but not instant. **Positives:** Hyprland itself responded as expected (two terminals tiled side by
side). **Their questions:** could it be the CPU, with only the bare minimum running? Should CPU optimization come before using an agent on
the device? They asked that these concerns be stated to the M5 agent, which this report does. The human also photographed the five early
boot lines and asked whether they mean anything important (answered above and in the proposals).

## Interpretation (bounded)

**Confirmed (measured on the M5 or in the M1's logs):**

* **The MTP keyboard path works end to end on this hardware**: RTKit wake, DockChannel FIFO, ring transport, the keyboard interface, an
  evdev node, Hyprland picking it up, and typed keys arriving at a terminal (the human's typing, and 10 of 10 injected characters at a
  1000 ms repeat delay).
* **The link and SSH held for 63 min with no kernel fault**; the attempt-25 image fixes work; the MTP DART's reset at boot disturbed nothing.
* **The keyboard is not the cause of the lag or the repeated letters**: taps reach the kernel once, 44 to 88 ms long, with no kernel repeat
  on any letter, and are read within 5.2 ms.
* **A screen update costs about 0.47 s of the one CPU at full-screen size** (the release wait, measured in all five phases) and
  about 0.2 s for a 600×400 window; with the repeated characters it is two such frames per tap.
* **The repeated letters are reproduced and explained**: the release is queued behind a frame that lasts longer than the terminal's repeat
  delay (250 ms), so the terminal repeats until the release arrives; 134 to 152 characters for 10 taps in seven runs at 250 ms (0.46 to
  0.53 s release wait), **10 of 10 in two runs at 1000 ms**. (The injected taps go through Hyprland's dispatcher, not libinput, but they pass
  the same event loop; the 0.5 s waits match the 1 to 2 s busy stretches after the human's own taps.)
* **Animations are not the cost** (identical per-tap CPU and release wait with them off); **the three leftover pollers are a small cost**
  (about 9% of a frame, 7 to 12% idle CPU).
* **The five early boot lines are unchanged since attempt 19** and everything that worked, worked with them: KVM does not start (no
  KVM guests on the M5 yet); the `cs` domain does not reach the on state and is skipped, and nothing references it.

**Likely (not separately tested):**

* The desktop is drawn by Mesa's LLVM software rasterizer on the boot CPU (the libraries are mapped; no GPU driver exists), at
  3456×2160 with at least three full-screen layers and a window composited per frame, which is why a frame costs half a second.
* `cs` is a GPU-side block (the generated DT's own comment calls its always-on flag "conservative HYPOTHESIS"); its failure will matter
  when the GPU is brought up, not for today's software-drawn desktop.
* The macOS accessory approval persists across reconnects of the same device (no prompt this time).

**Hypothesis:**

* The fixed cost that remains for a small window (about 0.2 s of latency, 0.5 s of CPU per tap) is full-screen layers
  (`omarchy-background`, `omarchy-notifications`, the dock) or the present of the whole frame to `simpledrm`; the A/B cannot separate them.
* The boot CPU is an efficiency-class core (attempt 20's single-thread benchmarks read about a fifth of the macOS baseline); with
  `cpufreq.off=1` and one CPU, any real speed-up is in more cores, the CPU's speed state, or moving the drawing to a GPU.

**Not established:** what the terminal showed for the human's own `hello` in the last test (their reply came through blank; the A/B
supersedes it); how the human's `omarchy` at normal speed would look at 1000 ms (not retested); the effect of `render:cm_enabled`, a
solid background or removing the overlay layers (not tried); the trackpad; why the Keybindings selector's done file never appears; stability
under sustained load; ports 2 and 3 (never cabled); fresh policy checks.

## Return and next handoff

* At about **8:42:50 PM** the human powered the M5 off or restarted it (confirmed in chat; the link vanished at +3,813.8 s with nothing
  unusual in the journal before it, and a macOS "Mac" device enumerated 31.5 s later). Fresh policy/default/installed-object checks:
  **NOT CHECKED.** Attempt 26 is consumed; no retry or settings change on the Mac. The fixed E1 probe is still **NOT RUN**; storage is
  attempt 27 (a separate launcher change the user reviews first, `decisions.md`).
* **For the M5 (proposals, not authorization), in the order I would try them:**
  1. **Ship a longer key-repeat delay now** (`input.repeat_delay` of 800 to 1000 ms in the image's Hyprland config): verified here, it removes
     the repeated letters (10 of 10) and halves the CPU per keystroke. It costs a slower start of a deliberate key repeat; revisit when a
     frame is under 250 ms.
  2. **Fix the leaked `omarchy-menu-select` pollers** (three leaked in ten minutes of use; 7 to 12% idle CPU): find why the done file never
     appears for Super+K here (the Qt shell menu fails to render, or its close path skips it; Unknown), and bound or replace the 50 ms
     `sleep` loop.
  3. **Cut the cost of a frame**, which is the real fix short of new hardware support: test (a) removing or disabling the full-screen
     `omarchy-notifications` overlay and the wallpaper layer, (b) `render:cm_enabled = false`, (c) smaller or floating windows as
     the default for terminals, (d) why a one-cell change costs 0.2 s even in a small window (damage handling on the `simpledrm` path).
     **Omarchy's own `no-animations` toggle (CPU-rendering machines) changed nothing for typing here**; do not count on it. The tools to
     measure each change exist (`ab_m5.py`-style taps, see 7).
  4. **The structural work, which the human's question points at:** only one CPU is online (`nr_cpus=1`) and it is slow; SMP (the
     secondary-core hurdles in `roadmap.md` Phase 3), CPU frequency and core type (`cpufreq.off=1`, boot CPU part `0x068`) and later a display/GPU
     driver (the mode `simpledrm` exposes is fixed at 3456×2160; a lower mode would cut the pixels four-fold) decide whether the desktop
     is usable. **My answer to the human's question:** agent work over SSH is possible today (attempt 25 ran Claude Code that way) and does
     not need the desktop, but it shares the same slow CPU; CPU optimization should come before anyone relies on the M5's own desktop or on heavy
     agent work there.
  5. **Checklist and image fixes seen in this run:** `ilinux-keyboard` should pass on a rerun (compare module state, not new kernel
     lines, in step 4); the idle sshd on the cabled port still restarts every 47 s with four journal lines each time (a
     `SuccessExitStatus` or a longer grace time would silence it) and each SSH session end logs `Failed with result 'exit-code'`; `ufw`
     (no nf_tables) and `omarchy-provision-hardware` fail as in attempt 25.
  6. **The early boot lines:** the `cs` always-on flag is the DT generator's own conservative guess and the hardware refuses it: revisit it
     (and `afr`, `nub_spmi_a2`, which are also off at boot but come on) when the GPU is next on the list; the `kvm_arch_timer` line means
     the guest-virtual-timer interrupt is missing or zero in the DT's timer description (Likely).
  7. **Tooling:** the measurement scripts are in `tools/m1n1-client/m5-probes/` (a read-only key and CPU timer, two read-only
     desktop inspectors, and two runtime-only tap A/B scripts that need the human's approval for each run), with a README, the Hyprland
     Lua calls that worked on this image, and an offline test (`python3 -I tools/m1n1-client/test_m5_probes.py`).

No media, capture, `ioreg` dumps or identifiers are committed; the human's phone photo and clip stay local. Earlier reports are unchanged.
The probe scripts were committed after the run with small edits (tightened refusals, two path and output fixes) that were not re-run on the M5;
see `tools/m1n1-client/m5-probes/README.md`.

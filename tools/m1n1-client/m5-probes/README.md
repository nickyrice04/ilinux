# M5 desktop probes: key and CPU timing, and runtime-only tap tests, over the USB byte pipe

2026-10-19, M1 side, written during attempt 26 (`native/boot/stage-b-2026-10-19-attempt26-result.md` has the results and what they
mean). Labels: Confirmed / Likely / Hypothesis / Unknown. The M1 ran these on the M5 through `ssh -F tools/m1n1-client/m5-ssh-config m5o`
(the USB byte pipe of `../usb-ssh-link.md`) to find why the Omarchy desktop on the M5 felt slow and repeated letters. They are
standard-library Python 3, **read from stdin** (`python3 -I -`), so nothing is installed on the M5, and their output goes to the ignored
`build/native-intake/` on the M1. **They have only run on the attempt-26 image** (Omarchy 4, Hyprland 0.56.2 with the Lua config, one
CPU, `simpledrm`); the offline tests below check their promises, not the M5's behaviour.

## The scripts

| Script | Runs as | Changes | What it gives |
|---|---|---|---|
| `keytiming.py` | root (`sudo -n`) | **nothing** (read-only; no grab of the input device) | each key event from `/dev/input/eventN` with its kernel timestamp, delivery lag and value (1 press, 0 release, 2 kernel repeat); the CPU's busy share every 0.1 s; CPU per process every 0.25 s; per-press rows (held time, kernel repeats, how long the CPU stayed busy right after, who used it); busy stretches; totals by process and by thread. `--selftest` runs it on made-up data |
| `inspect_desktop.py` | `omarchy` | nothing | six idle seconds of CPU by process, the biggest CPU users, `omarchy-menu*` processes, Hyprland's threads and mapped graphics libraries, its options, the monitor, open windows, the config lines about animations and blur |
| `frame_probe.py` | `omarchy` | nothing | render-related options, the layer surfaces drawn every frame (`hyprctl layers`), the desktop processes that could add per-frame work, the monitor |
| `tap_ab.py` | `omarchy` | **runtime only** (see below) | phases A (as found), B (leftover `omarchy-menu-select` pollers stopped), C (animations off): open a terminal, five isolated taps, a five-tap burst, Enter; per step the seconds the CPU stayed busy, Hyprland's CPU, the release wait, and the characters the terminal received |
| `tap_ab_repeat.py` | `omarchy` | **runtime only** | phases D (`input.repeat_delay` 1000 ms) and E (a 600×400 floating terminal at the original delay), same steps |

## Running them

From the repository root on the M1, with the link up and the clock set (`python3 -I tools/m1n1-client/m5-clock.py`):

```sh
# read-only (the time limit, in seconds, is the last argument; Enter on its own, without Super, ends it early)
ssh -F tools/m1n1-client/m5-ssh-config m5o 'sudo -n python3 -I - /dev/input/event0 600' \
    < tools/m1n1-client/m5-probes/keytiming.py > build/native-intake/keytiming.txt
ssh -F tools/m1n1-client/m5-ssh-config m5o 'python3 -I -' < tools/m1n1-client/m5-probes/inspect_desktop.py > build/native-intake/inspect.txt
ssh -F tools/m1n1-client/m5-ssh-config m5o 'python3 -I -' < tools/m1n1-client/m5-probes/frame_probe.py > build/native-intake/frame.txt
# runtime-only, with the human's approval for the run (see the rules below)
ssh -F tools/m1n1-client/m5-ssh-config m5o 'python3 -I -' < tools/m1n1-client/m5-probes/tap_ab.py > build/native-intake/tap-ab.txt
```

* `usb-pipe` allows one SSH session at a time on interface 1, so a probe and another session cannot overlap; a long probe (a few
  minutes) should be started detached (`perl -MPOSIX -e 'POSIX::setsid(); exec @ARGV' sh -c '…' &`) and watched through its output
  file, so a tool timeout cannot cut it. `keytiming.py` prints only `ARMED: …` until it ends, then the whole report.
* **Do not name the process you grep for on the same command line** (`ssh … 'pgrep -fc omarchy-menu-select'` matches the remote shell
  itself and reports one process too many); the A/B scripts check from Python for this reason.
* The M5's typed keys still reach Hyprland while `keytiming.py` listens, so the human can type as usual; ask them to press **Enter on
  its own** (not Super+Return, which opens a terminal) to end it.

## What the runtime-only scripts change, and the rules

Both change **the running session only**: nothing is saved, and the end of the RAM boot undoes everything. They are for a run the
human has approved *before* it starts (name the changes), with no window open on the M5's desktop (they refuse otherwise, or if `hyprctl` does not answer, because they
send keys to the focused window) and nobody touching the M5's keyboard. They assume the terminal is `foot`, the default on the
attempt-26 image (`foot_running()` names it).

| Script | Changes |
|---|---|
| `tap_ab.py` | stops the `omarchy-menu-select Keybindings` processes (`pkill`, once); `animations.enabled` false then true through `hl.config`; opens and closes terminals (`hl.exec_cmd`, `hl.dsp.window.close`); sends keys to the focused terminal (`hl.dsp.send_key_state`: a press, 75 ms, then the release); one-line scripts and result files under `/tmp/ab-*` (removed at the end) |
| `tap_ab_repeat.py` | `input.repeat_delay` 1000 then back to its original value; makes one terminal a 600×400 floating window (`hl.dsp.window.float/resize/center`); the same terminals, keys and `/tmp/ab-*` files |

Each terminal runs a script that reads one line and writes it to a file, so **the characters that reached it are counted exactly**:
a delayed key release shows up as extra letters. Both scripts restore the original setting in a `finally` block (and on SIGHUP and
SIGTERM, so a dropped link still restores), fall back to `hyprctl reload` if the option did not come back, close a leftover terminal,
and end with an idle measurement. The offline tests check each of these promises on the sources, and that a copy with one of them
broken is flagged.

## This Hyprland's Lua config API (what worked on 0.56.2)

The M5's Omarchy 4 configures Hyprland in Lua, and the old verbs are refused (`hyprctl keyword`: "keyword can't work with non-legacy
parsers. Use eval."; `hyprctl dispatch <old string>` fails with a Lua syntax error). What worked, all through `hyprctl eval '<lua>'`
(answer `ok` on success, an error string otherwise), with `XDG_RUNTIME_DIR=/run/user/<uid>` and `HYPRLAND_INSTANCE_SIGNATURE` set to
the name of the one directory in `$XDG_RUNTIME_DIR/hypr` (what the scripts do):

| Purpose | Lua |
|---|---|
| set an option | `hl.config({ animations = { enabled = false } })`, `hl.config({ input = { repeat_delay = 1000 } })` |
| run a command | `hl.exec_cmd("uwsm-app -- xdg-terminal-exec /tmp/script.sh")` |
| send a key to the focused window | `hl.dispatch(hl.dsp.send_key_state({ mods = "", key = "h", state = "down" }))` then `state = "up"` |
| float, size, centre, close the focused window | `hl.dispatch(hl.dsp.window.float({ action = "on" }))`, `hl.dsp.window.resize({ x = 600, y = 400, relative = false })`, `hl.dsp.window.center()`, `hl.dsp.window.close()` |

Reading still works with the old verbs: `hyprctl getoption <section:key> -j`, `monitors -j`, `clients -j`, `layers`, `activewindow -j`.
Omarchy's own files show the same calls (`/usr/share/omarchy/default/hypr/`; its `toggles/no-animations.lua` is the supported way to
turn animations off, for "machines that render on the CPU").

## Reading the numbers

* **Busy / busy-for:** a 0.1 s sample counts as busy at 50% or more of the one CPU; "busy-for" is how long the CPU stayed busy after the
  action began, until it had been quiet for 1 s. **Release wait** (`up_wait_s`) is how long Hyprland took to answer the release request
  sent 75 ms after the press: the time the release sat in its queue behind the frame the press caused. That is the quantity that, when it
  exceeds the terminal's repeat delay, produces repeated letters (the terminal repeats at `repeat_rate` per second until the release
  arrives).
* CPU time comes from the 100 Hz tick counters in `/proc` (10 ms resolution). A process that starts and exits between two samples is
  visible only as "`<parent>` (children)", once its parent has reaped it. A kernel worker renames itself after the last work item it
  ran; its time is followed by pid, not by name. The M5 kernel had no `/proc/pressure/cpu`, so scheduler wait is not available.
* The injected taps go through Hyprland's dispatcher, not libinput; they pass the same event loop as real keys, and the release waits they
  produced (0.46 to 0.53 s) match the 1 to 2 s busy stretches after a human's own taps.

## Reference numbers (attempt 26, one boot; Hyprland CPU per isolated tap, release wait, characters received for 10 taps)

| Phase | CPU per tap | Release wait | Characters for 10 taps |
|---|---:|---:|---:|
| A: as found (animations on, three leftover pollers, delay 250 ms) | 1.12 s | 0.51 to 0.53 s | 152, 151, 151 |
| B: pollers stopped | 1.12 s | 0.46 to 0.48 s | 136, 134 |
| C: B + animations off | 1.12 s | 0.46 to 0.47 s | 135, 134 |
| D: B + `repeat_delay` 1000 ms | 0.53 s | 0.47 s | **10, 10** |
| E: B + 600×400 floating terminal, delay 250 ms | 0.59 s | 0.23 s | 29, 30 |

## Not tried yet (hypotheses; each is one more phase)

`render:cm_enabled = false`; a solid background instead of the wallpaper layer, and no full-screen notification overlay (both are the
Qt shell's layers, not Hyprland options); a window with no gaps or border; whether a smaller output mode helps once a display driver can
set one. To add a phase, copy `cycle()` from `tap_ab_repeat.py`, set and restore the option the same way (restore in the `finally`
block), and, if it needs a Lua call not in the table above, add the call to the reviewed list in `../test_m5_probes.py` with the reason.

## Differences from the versions that ran in attempt 26

The scripts were committed after the run, with the M5 powered off, so these edits were checked offline only (the tests below) and
**not re-run on the M5**: docstrings and usage lines; both A/B scripts now also refuse to start when `hyprctl clients` does not answer
`[]` exactly (it used to refuse only when the answer named a window), and `tap_ab.py` refuses when it cannot read the animation option
(it used to treat that as "on"); `inspect_desktop.py` greps `/usr/share/omarchy/default/hypr` (it used a path that does not exist on
the image); `frame_probe.py` prints `hyprctl layers` as text (the JSON form did not parse) and is reformatted. The main flow of every
script is as it ran, including all the numbers quoted above.

## Tests

```sh
python3 -I tools/m1n1-client/test_m5_probes.py
```

Offline, on the M1: the scripts parse; `keytiming.py --selftest` passes; the read-only scripts stay read-only; the runtime-only scripts
keep their contract (refuse with a window open, restore in a `finally`, touch only `/tmp/ab-*`, use only the reviewed Lua calls and
`hyprctl` verbs); the README names every script; and every one of those checks catches a mutated copy.

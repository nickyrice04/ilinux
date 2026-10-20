"""Read-only probe of what Hyprland draws on the M5 (written for attempt 26), run as the omarchy user over SSH from the M1:

    ssh -F tools/m1n1-client/m5-ssh-config m5o 'python3 -I -' < tools/m1n1-client/m5-probes/frame_probe.py

Prints the render-related options (`hyprctl getoption`), the layer surfaces drawn on every frame (`hyprctl layers`: on the
attempt-26 desktop a full-screen wallpaper, a full-screen notification overlay, a bar and a dock), the desktop processes that could
add per-frame work, and the monitor. It changes nothing."""
import json
import os
import subprocess

RT = "/run/user/%d" % os.getuid()
ENV = dict(os.environ, XDG_RUNTIME_DIR=RT, HYPRLAND_INSTANCE_SIGNATURE=sorted(os.listdir(RT + "/hypr"))[0])
OPTIONS = ("debug:damage_tracking", "debug:overlay", "debug:damage_blink", "render:cm_enabled", "render:cm_fs_passthrough",
           "render:new_render_scheduling", "decoration:dim_inactive", "decoration:screen_shader", "decoration:active_opacity",
           "decoration:inactive_opacity", "general:gaps_in", "general:border_size", "misc:disable_hyprland_logo",
           "misc:force_default_wallpaper", "misc:animate_manual_resizes", "cursor:no_hardware_cursors", "cursor:inactive_timeout",
           "debug:disable_scale_checks")
SUSPECTS = ("hyprsunset", "hypridle", "swayosd", "mako", "swaync", "waybar", "elephant", "walker", "owe", "quickshell", "xdg-desktop",
            "fcitx", "wireplumber", "pipewire", "gnome-keyring", "Xwayland", "swaybg", "hyprpaper")
MONITOR_KEYS = ("width", "height", "refreshRate", "scale", "currentFormat", "dpmsStatus", "vrr", "activelyTearing", "directScanoutTo",
                "solitary", "solitaryBlockedBy")


def h(*args):
    r = subprocess.run(["hyprctl", *args], capture_output=True, text=True, timeout=60, env=ENV)
    return (r.stdout + r.stderr).strip()


print("== render-related options")
for opt in OPTIONS:
    print("%-30s %s" % (opt, h("getoption", opt, "-j").replace("\n", " ")[:100]))

print("== layers (what is drawn besides windows)")
print("\n".join(line[:200] for line in h("layers").splitlines()[:40]))

print("== suspects running")
for line in subprocess.run(["ps", "-eo", "pid,etimes,time,comm"], capture_output=True, text=True).stdout.splitlines():
    if any(name in line for name in SUSPECTS):
        print(line)

print("== monitors (selected fields)")
try:
    mon = json.loads(h("monitors", "-j"))[0]
    print({k: mon[k] for k in MONITOR_KEYS if k in mon})
except (ValueError, IndexError, KeyError) as e:
    print("monitors error:", e)

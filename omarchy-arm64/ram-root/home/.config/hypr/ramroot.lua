-- RAM root (one CPU, llvmpipe on simpledrm): start what Omarchy's Quickshell session would
-- otherwise provide. swaybg draws the theme background, waybar the bar, and foot a status
-- terminal (the M5 has no keyboard or trackpad driver yet). Each logs to the journal.
-- The wallpaper image does not load yet: gdk-pixbuf 2.44 hands it to glycin, whose sandboxed
-- loader exits with status 1 in this RAM root, so swaybg falls back to Tokyo Night's colour.
local state = os.getenv("HOME") .. "/.local/state/omarchy/current"

-- The 16-inch panel is 254 ppi, but simpledrm reports a 96-dpi size (914x591 mm for 3456x2234),
-- so Omarchy's "auto" picks scale 1. Use 2, as macOS does. Later rules override monitors.lua.
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 2 })

-- Hyprland stops logging once its config is loaded (debug.disable_logs defaults to true).
-- ILINUX_HYPR_LOGS in the unit's environment turns it back on: 1 = log file (it names the GL
-- renderer), stdout = also the journal, which keeps the last line before a crash.
local hypr_logs = os.getenv("ILINUX_HYPR_LOGS")
if hypr_logs == "1" or hypr_logs == "stdout" then
  hl.config({ debug = { disable_logs = false, enable_stdout_logs = hypr_logs == "stdout" } })
end

hl.on("hyprland.start", function()
  hl.exec_cmd("systemd-cat -t swaybg swaybg -c '#1a1b26' -m fill -i " .. state .. "/background")
  hl.exec_cmd("systemd-cat -t waybar waybar")
  hl.exec_cmd("systemd-cat -t foot foot --title=ilinux-status bash -c 'ilinux-status; exec bash -i'")
  hl.exec_cmd("systemd-cat -t ilinux-desktop-ready ilinux-desktop-ready")
end)

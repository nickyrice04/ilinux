-- RAM-root edition of Omarchy's ~/.config/hypr/hyprland.lua (upstream config/hypr/hyprland.lua
-- at the pinned commit). One change: Omarchy's session autostart is skipped, because it
-- launches the Quickshell shell, first-run provisioning, power profiles and udiskie, none of
-- which this image carries. hypr/ramroot.lua starts the wallpaper, waybar and foot instead.

-- Omarchy's bootstrap keeps path setup out of this user config.
dofile((os.getenv("OMARCHY_PATH") or "/usr/share/omarchy") .. "/default/hypr/bootstrap.lua")

-- Mark Omarchy's autostart module as loaded, so default.hypr.omarchy's require() skips it.
package.loaded["default.hypr.autostart"] = true

-- Load Omarchy defaults.
require("default.hypr.omarchy")

-- Personal overrides, as in Omarchy's template, plus the RAM-root session.
require("hypr.monitors")
require("hypr.input")
require("hypr.bindings")
require("hypr.looknfeel")
require("hypr.autostart")
require("hypr.ramroot")

-- Toggle config flags dynamically.
require("default.hypr.toggles")

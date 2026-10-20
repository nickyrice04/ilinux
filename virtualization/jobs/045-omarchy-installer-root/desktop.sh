# desktop.sh: attempt 26's desktop findings (native/boot/stage-b-2026-10-19-attempt26-result.md, "The slowness,
# measured" and "Return and next handoff"), sourced by ramroot.sh (stage 2, inside the job VM) and run on the RAM
# root's snapshot ($C) before the build options. Nothing here depends on the link; every change is recorded.
#  1. input.repeat_delay 1000 ms (Omarchy ships 250): on the M5 one CPU draws each frame in software in about
#     0.47 s, so a key's release waited behind the frame longer than 250 ms and the terminal auto-repeated the
#     letter about 14 times per tap (134-152 characters for 10 taps); at 1000 ms, 10 of 10, with half the CPU
#     per tap. repeat_rate stays Omarchy's 40.
#  2. The shell's menu plugin finishes a select/input request that a newer request or route replaces, so the
#     omarchy-menu-select waiting for it (a 50 ms sleep loop until its done file appears) ends instead of polling
#     until the session ends (three leaked on the M5 in ten minutes, 7-12 % of the CPU): patches/
#     omarchy-shell-menu-abandon-request.patch on Omarchy's Menu.qml, after a dry run against the installed file.
#  3. The weather widget is off: it fetched wttr.in and api.open-meteo.com through the M1's relay every 30 minutes.
#     Omarchy's own way (omarchy plugin disable: PluginRegistry.setEnabled drops the widget's bar entry, "the
#     whole story for a widget") needs the running shell, so the existing user's shell.json is preserved here
#     with only omarchy.weather entries removed (package defaults are used only when no user config exists).

stage_desktop() {
    log "desktop: attempt 26's findings (the key-repeat delay, the menu's replaced requests, the weather widget)"
    local H=$C/home/omarchy t=$C/home/omarchy/.local/state/omarchy/toggles/hypr F=$OUT/build/desktop-files.txt ver
    ver=$(pac "$C" -Q omarchy-dev | cut -d' ' -f2)
    : > "$F"
    echo "omarchy-dev $ver" >> "$F"

    # 1. repeat_delay 1000 ms through Omarchy's toggles directory, which its Hyprland config loads last (after
    #    default/hypr/input.lua and the user's hypr/input.lua), as deviation 15 does; repeat_rate stays Omarchy's.
    grep -q '^    repeat_delay = 250,$' "$C/usr/share/omarchy/default/hypr/input.lua" ||
        { echo "Omarchy's default/hypr/input.lua no longer sets repeat_delay = 250"; return 1; }
    grep -q '^    repeat_rate = 40,$' "$C/usr/share/omarchy/default/hypr/input.lua" ||
        { echo "Omarchy's default/hypr/input.lua no longer sets repeat_rate = 40"; return 1; }
    grep -q '^require("default.hypr.toggles")$' "$H/.config/hypr/hyprland.lua" ||
        { echo "the user's hypr/hyprland.lua does not load Omarchy's toggles last"; return 1; }
    if grep -q -E '^[^-]*repeat_(delay|rate)' "$H/.config/hypr/input.lua"; then
        echo "the user's hypr/input.lua sets a repeat value already"; return 1
    fi
    [ -d "$t" ] || { echo "no toggles directory $t"; return 1; }
    printf '%s\n' '-- iLinux RAM root (job 045, desktop.sh), attempt 26: on the M5 one CPU draws each frame in software in' \
        '-- about 0.47 s, so a key release waits behind the frame longer than the 250 ms repeat delay and the' \
        '-- terminal repeats the letter (134-152 characters for 10 taps); at 1000 ms, 10 of 10, with half the CPU' \
        '-- per tap. repeat_rate stays Omarchy'"'"'s. Revisit when a frame takes less than 250 ms.' \
        'hl.config({ input = { repeat_delay = 1000 } })' > "$t/ilinux-repeat-delay.lua"
    chown 1000:1000 "$t/ilinux-repeat-delay.lua"
    chmod 0644 "$t/ilinux-repeat-delay.lua"
    if chroot "$C" sh -c 'command -v lua' > /dev/null 2>&1; then   # the file as Lua, with a stand-in hl
        chroot "$C" lua -e 'hl = { config = function(c) assert(c.input.repeat_delay == 1000 and c.input.repeat_rate == nil) end }
                           dofile("/home/omarchy/.local/state/omarchy/toggles/hypr/ilinux-repeat-delay.lua")' ||
            { echo "ilinux-repeat-delay.lua does not set input.repeat_delay = 1000 alone"; return 1; }
        echo "ilinux-repeat-delay.lua checked with the root's lua" >> "$F"
    fi
    echo "home/omarchy/.local/state/omarchy/toggles/hypr/ilinux-repeat-delay.lua $(sha256sum < "$t/ilinux-repeat-delay.lua" | cut -d' ' -f1)" >> "$F"
    record changed "Hyprland input.repeat_delay 1000 ms (Omarchy ships 250; repeat_rate stays its 40) through ~/.local/state/omarchy/toggles/hypr/ilinux-repeat-delay.lua, Omarchy's toggles directory, which its Hyprland config loads last: attempt 26 measured on the M5 that a screen update costs the one CPU about 0.47 s and a key's release waits behind it, longer than 250 ms, so the terminal auto-repeated about 14 times per tap (134 to 152 characters for 10 taps in seven runs); at 1000 ms exactly 10 of 10 (two runs) and half the CPU per tap. Costs a slower start of a deliberate key repeat; revisit when a frame is under 250 ms"

    # 2. The menu plugin: a request replaced by a newer one is finished (its done file written), so its
    #    omarchy-menu-select ends. The patch is dry-run against the installed file first; both versions are kept.
    #    --no-backup-if-mismatch: no Menu.qml.orig in the image if a hunk applies at an offset.
    local qml=usr/share/omarchy/shell/plugins/menu/Menu.qml p=$J/patches/omarchy-shell-menu-abandon-request.patch
    [ -f "$C/$qml" ] || { echo "no $qml in the root"; return 1; }
    cp "$C/$qml" "$OUT/build/Menu.qml.before"
    # the request code the patch is for, and the poller it frees
    grep -q '^  function openDmenu(payload) {$' "$C/$qml" && grep -q '^  function openExistingMenu(initialMenu) {$' "$C/$qml" &&
        grep -q 'resultProc.command = \["bash", "-c", ": > " + Util.shellQuote(activeDoneFile)\]' "$C/$qml" &&
        ! grep -q 'abandonRequest' "$C/$qml" ||
        { echo "the installed Menu.qml ($ver) does not have the request code the patch is for (out/build/Menu.qml.before)"; return 1; }
    grep -q '^while \[\[ ! -e \$done_file \]\]; do$' "$C/usr/bin/omarchy-menu-select" && grep -q '^  sleep 0.05$' "$C/usr/bin/omarchy-menu-select" ||
        { echo "the installed omarchy-menu-select ($ver) no longer polls its done file every 50 ms"; return 1; }
    patch --dry-run --no-backup-if-mismatch -s "$C/$qml" "$p" ||
        { echo "the menu patch does not apply to the installed Menu.qml ($ver; out/build/Menu.qml.before)"; return 1; }
    patch --no-backup-if-mismatch -s "$C/$qml" "$p"
    [ ! -e "$C/$qml.orig" ] && [ ! -e "$C/$qml.rej" ] || { echo "patch left a backup or reject next to Menu.qml"; return 1; }
    chown root:root "$C/$qml"; chmod 0644 "$C/$qml"
    [ "$(grep -c '^    root.abandonRequest()$' "$C/$qml")" = 2 ] && grep -q '^  function abandonRequest() {$' "$C/$qml" ||
        { echo "the patched Menu.qml does not have abandonRequest and its two calls"; return 1; }
    cp "$C/$qml" "$OUT/build/Menu.qml.after"
    { echo "$qml before $(sha256sum < "$OUT/build/Menu.qml.before" | cut -d' ' -f1)"
      echo "$qml after $(sha256sum < "$C/$qml" | cut -d' ' -f1)"
      echo "patch $(sha256sum < "$p" | cut -d' ' -f1), $(grep -c '^[+-][^+-]' "$p") changed lines"; } >> "$F"
    record changed "Omarchy's shell menu plugin (/usr/share/omarchy/shell/plugins/menu/Menu.qml of omarchy-dev $ver) finishes a select/input request that a newer request or route replaces (patches/omarchy-shell-menu-abandon-request.patch: abandonRequest(), called first in openDmenu and openExistingMenu, writes the replaced request's done file as Escape does): omarchy-menu-select waits for that file in a 50 ms sleep loop, and without it a second omarchy-menu-select (Super+K twice) or the root menu summoned over one (Super+Space) left the first poller running until the session ended; attempt 26 found three alive on the M5 after ten minutes, 7 to 12 % of the one CPU. Omarchy's menu and its poller script are otherwise unchanged"

    # Preserve the installer's existing user configuration, including the five bar sections.
    # Its center has one clock, not the old three-widget layout. Change only weather entries.
    local sj=home/omarchy/.config/omarchy/shell.json defaults=usr/share/omarchy/config/omarchy/shell.json source
    source=$C/$defaults
    [ ! -e "$C/$sj" ] || source=$C/$sj
    cp "$source" "$OUT/build/shell.json.before"
    chroot "$C" python3 -I -c 'import json, sys; m = json.load(open(sys.argv[1])); assert m["kinds"] == ["bar-widget"], m["kinds"]' \
        /usr/share/omarchy/shell/plugins/panels/weather/manifest.json
    python3 -I "$J/disable_weather.py" --source "$source" --output "$C/$sj"
    chown 1000:1000 "$C/$sj"; chmod 0644 "$C/$sj"
    cp "$C/$sj" "$OUT/build/shell.json.after"
    echo "$sj $(sha256sum < "$C/$sj" | cut -d' ' -f1): existing layout preserved, weather removed" >> "$F"
    record changed "Weather widget removed from the existing installed user shell.json (or package defaults when absent), preserving every other field and all bar sections. Attempt 26 recorded its periodic requests through the M1 relay. The layout remains this image's installed layout; the unrelated world-clock plugin is unchanged."
    cat "$F"
}

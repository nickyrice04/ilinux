# inspect.sh: INSPECT=1 in out/job.env. Copies the installer scripts of the installed runtime
# out of the work disk, and unpacks those of the edge repository's other runtime packages
# (omarchy-dev, omarchy-settings-dev) next to them, for reading on the host. Changes nothing.
stage_inspect() {
    local D=$OUT/inspect
    rm -rf "$D"; mkdir -p "$D/installed" "$D/pkgs"
    if [ -d "$R/usr/share/omarchy" ]; then
        pac "$R" -Q omarchy omarchy-settings > "$D/installed/versions.txt" 2>&1 || true
        cp -R "$R/usr/share/omarchy/install" "$D/installed/install"
        cp "$R/usr/share/omarchy/version" "$D/installed/" 2>/dev/null || true
        mkdir -p "$D/installed/bin"
        cp "$R"/usr/bin/omarchy-{apply,provision,hw,lifecycle,mise,pkg,done,hook,launch-shell,shell,menu}* "$D/installed/bin/" 2>/dev/null || true
    fi
    pacman --config "$W/pacman.conf" --dbpath "$R/var/lib/pacman" --cachedir "$W/cache" --gpgdir "$W/gnupg" \
        -Sw --noconfirm omarchy-dev omarchy-settings-dev > "$D/pkgs/download.log" 2>&1 || true
    local p
    for p in omarchy-dev omarchy-settings-dev; do
        f=$(ls -t "$W"/cache/$p-[0-9]*.pkg.tar.* 2>/dev/null | grep -v '\.sig$' | head -1)
        [ -n "$f" ] || continue
        echo "$(basename "$f")" >> "$D/pkgs/files.txt"
        mkdir -p "$D/pkgs/$p"
        bsdtar -xf "$f" -C "$D/pkgs/$p" .PKGINFO usr/share/omarchy/install usr/share/omarchy/version 'usr/bin/omarchy-*' 2>/dev/null ||
            bsdtar -xf "$f" -C "$D/pkgs/$p" .PKGINFO 'usr/share/omarchy/install/*' 'usr/bin/omarchy-*' 2>> "$D/pkgs/extract.log" || true
    done
    find "$D" -maxdepth 3 | sort | head -50
}

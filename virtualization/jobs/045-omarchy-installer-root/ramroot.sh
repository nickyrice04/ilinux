# ramroot.sh: stage 2 of job 045, sourced by run.sh. A writable snapshot of the installed root
# ($R -> $C) made into the M5's RAM root. The install stays as Omarchy's installer left it; every
# change here is recorded (out/deviations.tsv) with its reason.

# private_keys: text files of the RAM root that hold a private key, as root-relative paths. A key is a
# whole-line PEM or OpenSSH BEGIN marker with base64 lines after it (a header line or two may come
# between); documentation that quotes the marker inside a string (npm's config docs do) is no key.
private_keys() {
    local f
    grep -r -l -I -E -e '^-----BEGIN ([A-Z0-9]+ )*PRIVATE KEY-----$' "$C"/etc "$C"/home "$C"/root "$C"/usr/local \
        "$C"/var "$C"/opt "$C"/srv 2> /dev/null | while read -r f; do
        awk '/^-----BEGIN ([A-Z0-9]+ )*PRIVATE KEY-----$/ { body = 4; next }
             body > 0 { if ($0 ~ /^[A-Za-z0-9+\/=]{40,}$/) { found = 1; exit } body-- }
             END { exit !found }' "$f" && echo "${f#"$C"}"
    done || true
}

stage_ramroot() {
    DEV=$W/deviations-ramroot.tsv
    : > "$DEV"
    log "RAM root: snapshot of the install"
    chroot_down "$C"
    if [ -d "$C" ]; then
        btrfs subvolume list -o "$C" | awk '{print $NF}' | sort -r |
            while read -r sv; do btrfs subvolume delete "$W/$sv" > /dev/null; done
        btrfs subvolume delete "$C" > /dev/null
    fi
    btrfs subvolume snapshot "$R" "$C" > /dev/null

    # PID 1 of the initramfs. The kernel unpacks the image into rootfs and runs /init; job 039's
    # (the committed one) bind-mounts that root onto itself, so it is an ordinary mount that
    # pivot_root and bubblewrap accept, and execs systemd.
    git -c safe.directory='*' -C /mnt/ilinux show HEAD:omarchy-arm64/ram-root/overlay/init > "$C/init"
    chmod 0755 "$C/init"
    record added "/init (job 039's, omarchy-arm64/ram-root/overlay/init): the root is the initramfs; /init makes it a real mount (bubblewrap needs pivot_root) and execs systemd"

    # The image-build mode leaves the keyring to the machine's first boot, which deletes and
    # remakes it (omarchy-provision-hardware); what is here is pacstrap -K's from the build,
    # with its private master key.
    if [ -d "$C/etc/pacman.d/gnupg" ]; then
        rm -rf "$C/etc/pacman.d/gnupg"
        record changed "the build's pacman keyring (pacstrap -K, with its private master key) is left out: no credentials in the image; Omarchy's image first boot makes the machine's own, as it does for any image build"
    fi
    test -e "$C/var/lib/omarchy/image/pacman-keyring" && echo "first boot is asked for a keyring" >> "$OUT/build/ramroot.txt"

    # Omarchy's user setup turns animations and transparency off when it runs in a VM
    # (install/user/hardware/vm-no-animations.sh, omarchy-hw-vm). It ran in the build VM; on the
    # M5, which is no VM, the installer would not have placed these toggles.
    local t=$C/home/omarchy/.local/state/omarchy/toggles/hypr
    if grep -q 'Detected a virtual machine' "$IO/provision-user.log" 2>/dev/null; then
        rm -f "$t/no-animations.lua" "$t/window-opaque.lua"
        record build-host "undid vm-no-animations.sh's two toggles (no-animations, window-opaque): the user setup ran in the build VM, where omarchy-hw-vm is true; on the M5 it is false"
    fi

    # Qt Wayland stops counting a window as shown when its frame callback is more than 100 ms late
    # and repaints the whole window when the callback comes (QT_WAYLAND_FRAME_CALLBACK_TIMEOUT, Qt's
    # default 100). Hyprland on the CPU (llvmpipe, 3456x2234) takes longer than that per frame: so
    # every window of Omarchy's shell timed out on every frame and was repainted in full, and Hyprland
    # composited back to back at 83 % of the one CPU (VM job 048; on the M5 a frame should take
    # 0.6-1.1 s, estimated). Off for the session, through Omarchy's toggle directory, which Hyprland's
    # config loads; Hyprland starts the shell, which inherits it.
    printf '%s\n' '-- iLinux RAM root (job 045, ramroot.sh): Qt never treats a window as hidden for a late frame' \
        '-- callback; CPU-rendered frames take longer than its 100 ms (VM job 048).' \
        'hl.env("QT_WAYLAND_FRAME_CALLBACK_TIMEOUT", "0")' > "$t/ilinux-frame-callbacks.lua"
    chown 1000:1000 "$t/ilinux-frame-callbacks.lua"
    record changed "QT_WAYLAND_FRAME_CALLBACK_TIMEOUT=0 for the session (~/.local/state/omarchy/toggles/hypr/ilinux-frame-callbacks.lua, hl.env): with frames slower than Qt's 100 ms, every shell window timed out and was repainted on every frame, so Hyprland never went idle (VM job 048)"

    # Our kernel has no zram (boot035: CONFIG_ZRAM is not set). Omarchy's zram-generator still
    # declares /dev/zram0, and systemd waited its full 90 s for that device before sysinit.target
    # on every boot (VM job 045, first boot test). Mask the generator.
    install -d "$C/etc/systemd/system-generators"
    ln -sf /dev/null "$C/etc/systemd/system-generators/zram-generator"
    record changed "zram-generator masked (/etc/systemd/system-generators/zram-generator -> /dev/null): our kernel has no CONFIG_ZRAM, so /dev/zram0 never appears and every boot stalled 90 s waiting for it; a kernel with zram would keep Omarchy's swap on zram"

    # The M5 has no keyboard or trackpad driver yet, so nothing ever ends idle: Omarchy's idle
    # chain (screensaver, lock, display off) darkened the VM's panel within minutes. Omarchy's
    # own Stay Awake toggle (omarchy-toggle-idle stay-awake: this state file) keeps it on, as a
    # user would set it from the bar or the menu.
    install -d -o 1000 -g 1000 "$C/home/omarchy/.local/state/omarchy/indicators"
    install -m 0644 -o 1000 -g 1000 /dev/null "$C/home/omarchy/.local/state/omarchy/indicators/stay-awake"
    record changed "Omarchy's Stay Awake toggle on (~/.local/state/omarchy/indicators/stay-awake, what omarchy-toggle-idle stay-awake writes): with no input device the idle chain (screensaver, lock, display off) would leave the M5's panel dark with no way to wake it"

    # Attempt 26's desktop findings (desktop.sh): the key-repeat delay, the menu plugin's replaced requests,
    # the weather widget. Nothing of the link; recorded there.
    . "$J/desktop.sh"
    stage_desktop

    # The build options (link.sh): the USB link to the M1, Claude Code ready to start, and Omarchy's
    # passwordless-sudo grant for the user.
    if [ "$LINK" = 1 ] || [ "$CLAUDE" = 1 ] || [ "$NOPASSWD" = 1 ]; then . "$J/link.sh"; fi
    if [ "$LINK" = 1 ]; then stage_link; fi
    if [ "$CLAUDE" = 1 ]; then stage_claude; fi
    if [ "$NOPASSWD" = 1 ]; then stage_nopasswd; fi

    # A RAM root boots as if freshly installed every time, so systemd's ConditionNeedsUpdate
    # units (ldconfig, hwdb, journal catalog, update-done) would run on every boot; pacman's
    # hooks ran them at install. Stamp /etc and /var as systemd-update-done would.
    local usr_ns
    usr_ns=$(stat -c %.9Y "$C/usr" | tr -d .)
    for d in etc var; do
        printf '# Written by job 045, as systemd-update-done would.\nTIMESTAMP_NSEC=%s\n' "$usr_ns" > "$C/$d/.updated"
    done
    record added "/etc/.updated and /var/.updated (as systemd-update-done writes them after a first boot): a RAM root never keeps that state, so the update units would rerun on every boot"

    # The image's identity, for the boot test and the report.
    mkdir -p "$C/usr/share/ilinux"
    printf 'built %s\nomarchy %s\nkernel %s (Image sha256 %s)\njob 045, ilinux %s\noptions LINK=%s CLAUDE=%s NOPASSWD=%s\n' \
        "$(date -u +%FT%TZ)" "$(pac "$C" -Q omarchy-dev | cut -d' ' -f2)" "$KERNEL_NAME" "$IMAGE_SHA" \
        "$ILINUX_REV" "$LINK" "$CLAUDE" "$NOPASSWD" > "$C/usr/share/ilinux/build-info.txt"
    record added "/usr/share/ilinux/build-info.txt (what was built, from what)"

    # What the image holds that must stay private, for the report.
    { echo "ssh host keys:"; ls "$C"/etc/ssh/ssh_host_* 2>/dev/null || echo "  none"
      echo "machine-id: $(wc -c < "$C/etc/machine-id") bytes"
      echo "user shadow fields: $(chroot "$C" getent shadow omarchy root | cut -d: -f1,2 | sed 's/:\(.\).*/:\1.../' | tr '\n' ' ')"
      echo "authorized keys (public): $(ls "$C"/etc/ssh/authorized_keys.d/ 2>/dev/null | tr '\n' ' ')"
      echo "claude sign-in state (~/.claude/.credentials.json, ~/.claude.json): $(ls -d "$C"/home/omarchy/.claude/.credentials.json "$C"/home/omarchy/.claude.json 2>/dev/null | sed "s#$C##" | tr '\n' ' ' | grep . || echo none)"
      echo "unrestricted sudo grants (NOPASSWD: ALL): $(grep -l -E '^[^#]*NOPASSWD:[[:space:]]*ALL[[:space:]]*$' "$C"/etc/sudoers "$C"/etc/sudoers.d/* 2>/dev/null | sed "s#$C##" | tr '\n' ' ' | grep . || echo none)"
      echo "private keys (PEM or OpenSSH, text files under /etc /home /root /usr/local /var /opt /srv): $(private_keys | tr '\n' ' ' | grep . || echo none)"
    } > "$OUT/build/private-contents.txt"
    # The USB link's rule: no private key in the image (its SSH host key is made at boot)
    if [ "$LINK" = 1 ] && [ -n "$(private_keys)" ]; then
        echo "private keys in the image: $(private_keys | tr '\n' ' ')"; return 1
    fi
    cat "$DEV"
}

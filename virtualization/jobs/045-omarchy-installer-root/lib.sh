# lib.sh: helpers for job 045, sourced by run.sh and its stages (bash, inside the job VM).

log() { printf '[%s] %s\n' "$(date +%T)" "$*"; }
calc() { awk "BEGIN { printf \"%.${2:-1}f\", $1 }"; }   # calc EXPR [DECIMALS]
share() { mkdir -p "/mnt/$1"; mountpoint -q "/mnt/$1" || mount -t virtiofs "$1" "/mnt/$1"; }

# chroot_up ROOT [resolv]: the mounts arch-chroot makes (arch-install-scripts), including the
# bind of the root onto itself, so the root is a mount point inside the chroot. With "resolv",
# also the build VM's resolv.conf over the target's (arch-chroot's DNS), for setup commands
# that reach the network; package installs from outside the chroot do not need it.
RESOLV_MADE=
chroot_up() {
    local r=$1
    mountpoint -q "$r" || mount --bind "$r" "$r"
    mkdir -p "$r"/{dev,proc,sys,run,tmp,etc}
    mount -t proc -o nosuid,noexec,nodev proc "$r/proc"
    mount -t sysfs -o nosuid,noexec,nodev,ro sys "$r/sys"
    mount --rbind /dev "$r/dev"
    mount --make-rslave "$r/dev"
    mount -t tmpfs -o mode=0755,nosuid,nodev run "$r/run"
    mount -t tmpfs -o mode=1777,strictatime,nodev,nosuid tmp "$r/tmp"
    if [ "${2:-}" = resolv ]; then
        RESOLV_MADE=
        if [ -L "$r/etc/resolv.conf" ] || [ ! -e "$r/etc/resolv.conf" ]; then
            RESOLV_MADE=$(readlink "$r/etc/resolv.conf" || echo none)
            rm -f "$r/etc/resolv.conf"
            : > "$r/etc/resolv.conf"
        fi
        mount --bind /etc/resolv.conf "$r/etc/resolv.conf"
    fi
}
chroot_down() {
    local r=$1 m p
    [ -d "$r" ] || return 0
    # Programs a setup step left running inside the root (gpg-agent, started by a keyring
    # package's install script) keep its /dev busy: stop them first.
    for p in /proc/[0-9]*; do
        [ "$(readlink "$p/root" 2>/dev/null)" = "$r" ] && kill "${p#/proc/}" 2>/dev/null
    done
    sleep 1
    for m in opt/packages etc/resolv.conf tmp run dev sys proc work; do
        if mountpoint -q "$r/$m"; then umount -R "$r/$m" 2>/dev/null || umount -R -l "$r/$m" || true; fi
    done
    if [ -n "$RESOLV_MADE" ]; then   # put back what was there: nothing, or the symlink
        rm -f "$r/etc/resolv.conf"
        [ "$RESOLV_MADE" = none ] || ln -s "$RESOLV_MADE" "$r/etc/resolv.conf"
        RESOLV_MADE=
    fi
    # the bind of the root onto itself
    if mountpoint -q "$r"; then umount "$r" 2>/dev/null || umount -l "$r" 2>/dev/null || true; fi
    return 0
}

# pac ROOT ARGS...: pacman on another root with the build's configuration and keyring, the
# package cache outside the root, and the root's own hooks and log.
pac() {
    local root=$1; shift
    pacman --root "$root" --dbpath "$root/var/lib/pacman" --config "$W/pacman.conf" \
        --cachedir "$W/cache" --gpgdir "$W/gnupg" --hookdir "$root/etc/pacman.d/hooks" \
        --logfile "$root/var/log/pacman.log" --noconfirm "$@"
}

# pac_retry ROOT LOG ARGS...: pac -S --needed ARGS into ROOT, logged in LOG. Omarchy's Arch Linux
# ARM mirror resets connections under load: a download error is retried up to five more times,
# pacman resuming from the cache; any other failure returns at once.
pac_retry() {
    local root=$1 log=$2 try
    shift 2
    : > "$log"
    for try in 1 2 3 4 5 6; do
        if pac "$root" -S --needed "$@" > "$log.try" 2>&1; then
            cat "$log.try" >> "$log"; rm -f "$log.try"; return 0
        fi
        cat "$log.try" >> "$log"
        grep -q -E 'failed retrieving file|download library error|failed to synchronize' "$log.try" || break
        echo "=== attempt $try failed on a download error; retrying" >> "$log"
        sleep $((try * 15))
    done
    rm -f "$log.try"
    tail -40 "$log"
    return 1
}

# record KIND TEXT: one deviation from stock Omarchy, appended to $DEV (one file per stage;
# run.sh joins them into out/deviations.tsv). KIND: omitted, changed, added, build-host,
# vm-only. The report's deviation list is checked against that file.
record() {
    printf '%s\t%s\n' "$1" "$2" >> "$DEV"
    log "deviation ($1): $2"
}

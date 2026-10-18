# install.sh: stage 1 of job 045, sourced by run.sh. Omarchy 4 installed into $R by Omarchy's
# own installer, from Omarchy's edge aarch64 repositories, in the order the Omarchy ISO's
# orchestrator runs it (omarchy-iso quattro, configs/airootfs/usr/share/omarchy-iso/orchestrator,
# main.py build_phases and phases_impl.py), for the aarch64 platform. The ISO's phases are
# followed one by one; where the M5 forces a difference (no kernel package, firmware or
# bootloader, no disk, no keyboard, no credentials in the image) the step says so and records
# it (out/deviations.tsv). $R is a btrfs subvolume, as an installed Omarchy root is. Logs go to
# out/install/ ($IO), which later runs keep while the installed root is reused.

OMARCHY_KEY=40DFB630FF42BCFFB047046CF0134EE680CAC571   # bin/omarchy-update-keyring pins it
U=omarchy                 # the install user (archinstall: sudo, no extra groups)
HOST=omarchy              # the configurator's default hostname
# Omarchy's aarch64 ISO is an edge ISO (bin/omarchy-iso-make --arch aarch64 --edge), and edge,
# dev and local-source ISOs install the dev runtime packages, which track the quattro branch
# (builder/build-iso.sh; its arm64-install test does the same). The published 4.0.4 runtime in
# the same repository cannot finish an aarch64 install: its user setup looks for a linux-x64
# Node tarball only, and it has neither the aarch64 package list nor the image-build mode
# (VM job 045, out/inspect/).
RUNTIME=omarchy-dev
SETTINGS=omarchy-settings-dev
ISO_ENV=(OMARCHY_PATH=/usr/share/omarchy OMARCHY_INSTALL=/usr/share/omarchy/install
         OMARCHY_INSTALL_USER=$U OMARCHY_USER_NAME= OMARCHY_USER_EMAIL=
         OMARCHY_MIRROR=edge OMARCHY_ISO_REF=edge OMARCHY_RUNTIME_PACKAGE=$RUNTIME
         OMARCHY_SETTINGS_PACKAGE=$SETTINGS OMARCHY_NVIM_PACKAGE=omarchy-nvim
         OMARCHY_INSTALL_LOG_FILE=/var/log/omarchy-install.log OMARCHY_LOG_TO_STDOUT=1
         PATH=/usr/local/sbin:/usr/local/bin:/usr/bin LANG=C.UTF-8)

# The ISO's _run_target_setup_command: arch-chroot (as root, or -u USER) with the target
# environment, the unified log bound at /var/log/omarchy-install.log.
iso_setup_command() {   # iso_setup_command LOGNAME [--user USER] CMD...
    local name=$1; shift
    local -a who=() env_user=()
    if [ "$1" = --user ]; then
        who=(--userspec="$(chroot "$R" id -u "$2"):$(chroot "$R" id -g "$2")" --groups="$(chroot "$R" id -G "$2" | tr ' ' ,)")
        env_user=(HOME=/home/$2 USER=$2 LOGNAME=$2 SHELL=/bin/bash)
        shift 2
    fi
    : "${OMARCHY_START_EPOCH:=$(date +%s)}"
    : "${OMARCHY_START_TIME:=$(date '+%Y-%m-%d %H:%M:%S')}"
    local rc=0
    chroot "${who[@]}" "$R" /usr/bin/env -i "${ISO_ENV[@]}" "${env_user[@]}" \
        OMARCHY_START_TIME="$OMARCHY_START_TIME" OMARCHY_START_EPOCH="$OMARCHY_START_EPOCH" "$@" \
        > "$IO/$name.log" 2>&1 || rc=$?
    echo "$name exit $rc" | tee -a "$IO/phases.txt"
    return $rc
}

# pac_install NAME ARGS...: pac_retry into $R, logged in $IO/pacman-NAME.log.
pac_install() { local name=$1; shift; pac_retry "$R" "$IO/pacman-$name.log" "$@"; }

install_keyring_and_config() {
    log "build keyring and pacman configuration (Omarchy edge, aarch64)"
    if [ ! -s "$W/gnupg/trustdb.gpg" ] || ! pacman-key --gpgdir "$W/gnupg" --list-keys "$OMARCHY_KEY" > /dev/null 2>&1; then
        rm -rf "$W/gnupg"
        pacman-key --gpgdir "$W/gnupg" --init
        pacman-key --gpgdir "$W/gnupg" --populate archlinuxarm
        # The way Omarchy's own bin/omarchy-update-keyring trusts its signing key.
        pacman-key --gpgdir "$W/gnupg" --recv-keys "$OMARCHY_KEY" --keyserver keys.openpgp.org
        pacman-key --gpgdir "$W/gnupg" --lsign-key "$OMARCHY_KEY"
    fi
    { pacman -Q archlinuxarm-keyring
      gpg --homedir "$W/gnupg" --list-keys --keyid-format long "$OMARCHY_KEY" 2>/dev/null | grep -E '^(pub|uid)'
    } > "$IO/keyring.txt"
    # Omarchy's own aarch64 edge templates; the build copy only points Include at a copy of the
    # mirror list, leaves out DownloadUser (the cache is on the work disk) and downloads two
    # files at a time (the mirror reset connections at five).
    sed -e "s#^Include = /etc/pacman.d/mirrorlist#Include = $W/mirrorlist#" -e '/^DownloadUser/d' \
        -e 's/^ParallelDownloads.*/ParallelDownloads = 2/' \
        /mnt/omarchy/default/pacman/aarch64/pacman-edge.conf > "$W/pacman.conf"
    cp /mnt/omarchy/default/pacman/aarch64/mirrorlist-edge "$W/mirrorlist"
    cp "$W/pacman.conf" "$W/mirrorlist" "$IO/"
}

# Phase "Installing Arch + Omarchy" (arch_install_system).
phase_arch_install_system() {
    log "phase: Installing Arch + Omarchy"
    mkdir -p "$R/var/lib/pacman" "$R/var/log" "$R/etc/pacman.d/hooks"
    # pacstrap -K, as archinstall runs it: an empty keyring in the target first, which the
    # keyring packages' install scripts then populate.
    [ -d "$R/etc/pacman.d/gnupg" ] || pacman-key --gpgdir "$R/etc/pacman.d/gnupg" --init > /dev/null
    chroot_up "$R"
    # minimal_installation: base and base-devel. archinstall would add the selected kernel,
    # its headers and linux-firmware; the M5 boots our kernel, whose Image and DT come through
    # m1n1, and none of linux-firmware's files is for its hardware.
    record omitted "kernel package (linux-aarch64 or the platform kernel), its headers and linux-firmware: the M5 runs the project's boot035 kernel and DT, loaded by m1n1"
    pac_install 01-base -y base base-devel
    # set_mirrors(on_target=True) and the ISO's online configuration: Omarchy's edge
    # templates in the target (post-install/pacman.sh rewrites them from the runtime later).
    install -m 0644 /mnt/omarchy/default/pacman/aarch64/pacman-edge.conf "$R/etc/pacman.conf"
    install -m 0644 /mnt/omarchy/default/pacman/aarch64/mirrorlist-edge "$R/etc/pacman.d/mirrorlist"
    # minimal_installation's hostname and locale (configurator: en_US.UTF-8), then
    # configure_keyboard (systemd-firstboot --keymap, the input-method preference).
    echo "$HOST" > "$R/etc/hostname"
    sed -i 's/^#\(en_US.UTF-8 UTF-8\)/\1/' "$R/etc/locale.gen"
    chroot "$R" locale-gen > "$IO/locale-gen.log" 2>&1
    echo LANG=en_US.UTF-8 > "$R/etc/locale.conf"
    systemd-firstboot --root="$R" --keymap=us --force
    mkdir -p "$R/etc/omarchy"
    printf 'INPUT_METHOD=none\nXKB_LAYOUT=\n' > "$R/etc/omarchy/input-method"
    # setup_swap: zram-generator; the ISO deletes the /etc config archinstall writes.
    pac_install 02-swap zram-generator
    # _install_early_packages: bootstrap, then LuaRocks, then the user seed.
    record omitted "limine and efibootmgr (early bootstrap), and the Limine boot setup: the M5 has no bootloader in this path, and its boot chain must stay as installed"
    pac_install 03-early base-devel git omarchy-keyring archlinuxarm-keyring "$SETTINGS"
    pac_install 04-luarocks lua51 luarocks
    pac_install 05-nvim omarchy-nvim
    # create_users: archinstall's useradd -m -G wheel and its sudoers entry for a sudo user.
    # The configurator would set the human's password (and root's); this image carries none.
    chroot "$R" getent passwd "$U" > /dev/null || chroot "$R" useradd -m -G wheel "$U"
    printf '%s ALL=(ALL) ALL\n' "$U" > "$R/etc/sudoers.d/00_$U"
    chmod 0440 "$R/etc/sudoers.d/00_$U"
    chroot "$R" passwd -l "$U" > /dev/null
    chroot "$R" passwd -l root > /dev/null
    record changed "no password for the user or root (the configurator sets the human's): the image holds no credentials; the session starts by autologin (below)"
    # install_applications: archinstall's PipeWire audio selection (audio_config pipewire):
    # its packages, and pipewire-pulse enabled for the user.
    pac_install 06-audio pipewire pipewire-alsa pipewire-jack pipewire-pulse gst-plugin-pipewire \
        libpulse wireplumber
    local wants=$R/home/$U/.config/systemd/user/default.target.wants
    mkdir -p "$wants"
    ln -sf /usr/lib/systemd/user/pipewire-pulse.service "$wants/pipewire-pulse.service"
    ln -sf /usr/lib/systemd/user/pipewire-pulse.socket "$wants/pipewire-pulse.socket"
    chroot "$R" chown -R "$U:$U" "/home/$U"
    # _runtime_package_list: the runtime, then the ISO's base list (for aarch64 the builder
    # composes it from the runtime package's own lists, below), then the aarch64 boot stack, of
    # which only snapper is kept: limine, limine-mkinitcpio-hook and limine-snapper-sync belong
    # to the bootloader.
    pac_install 07-runtime "$RUNTIME"
    pac "$R" -Ql "$RUNTIME" | awk '{print $2}' | sed "s#^$R##" | grep -E '^/usr/(bin/|share/omarchy/[^/]+/$)' \
        > "$IO/omarchy-files.txt" || true
    pac "$R" -Ss '^omarchy' > "$IO/omarchy-repo-packages.txt" || true
    # The ISO builder's aarch64_default_set (builder/build-iso.sh), on the runtime's own lists:
    # the base list, then omarchy-aarch64.packages if the runtime has one, minus its
    # x86_64-only list, first occurrence kept.
    local L=$R/usr/share/omarchy/install
    local -a lists=("$L/omarchy-base.packages")
    [ ! -f "$L/omarchy-aarch64.packages" ] || lists+=("$L/omarchy-aarch64.packages")
    grep -hv '^#\|^$' "${lists[@]}" | sed -e 's/[[:space:]]*#.*$//' -e '/^[[:space:]]*$/d' |
        awk -v skips="$L/omarchy-x86_64-only.packages" '
            BEGIN { while ((getline line < skips) > 0) { sub(/[ \t]*#.*$/, "", line); if (line != "") skip[line] = 1 } }
            skip[$0] { next }
            !seen[$0]++' > "$IO/omarchy-pkg-defaults-aarch64.txt"
    ls "$L"/*.packages > "$IO/runtime-package-lists.txt"
    # the runtime's own composer, for comparison (the two lists should agree)
    chroot "$R" /usr/bin/env -i OMARCHY_PATH=/usr/share/omarchy PATH=/usr/bin omarchy-pkg-defaults aarch64 \
        > "$IO/omarchy-pkg-defaults-runtime.txt" 2>&1 || true
    record omitted "limine, limine-mkinitcpio-hook and limine-snapper-sync (the ISO adds them on aarch64): no bootloader"
    pac_install 08-defaults $(cat "$IO/omarchy-pkg-defaults-aarch64.txt") snapper
    # Standard archinstall finishers: timezone, NTP, (root password: none, above), fstab.
    ln -sf /usr/share/zoneinfo/UTC "$R/etc/localtime"
    record changed "timezone UTC (the configurator asks or detects it): no location in the image"
    systemctl --root="$R" enable systemd-timesyncd.service > /dev/null 2>&1
    record omitted "fstab (genfstab): the RAM root is the initramfs; there is no disk"
    record omitted "archinstall's network-config copy from the live ISO (network_config iso): there is no live ISO, and the M5 has no network device in this path"
    chroot_down "$R"
}

# Phase "Configuring hibernation": Limine-only, and the M5 has no swap device.
phase_configure_hibernation() {
    record omitted "Configuring hibernation (swapfile and resume): no disk"
}

# Phase "Configuring system" (run_system_finalizer): omarchy-apply-system in the target chroot.
# The build declares an image first (install/helpers/image-target.sh): this root is built in a
# VM, not on the M5, so Omarchy queues its hardware steps for the machine's first boot and
# asks that boot for the machine's own pacman keyring.
phase_run_system_finalizer() {
    log "phase: Configuring system (omarchy-apply-system, image build for aarch64)"
    install -d -m 0755 "$R/var/lib/omarchy" "$R/var/lib/omarchy/image"
    printf 'format=1\nplatform=aarch64\n' > "$R/var/lib/omarchy/image/target"
    chmod 0644 "$R/var/lib/omarchy/image/target"
    chroot_up "$R" resolv
    iso_setup_command apply-system /usr/bin/omarchy-apply-system --install-user "$U" --first-install || true
    chroot_down "$R"
    grep -E 'Starting:|Completed:|Failed:|Image build' "$IO/apply-system.log" > "$IO/apply-system-steps.txt" || true
    cat "$R/var/lib/omarchy/image/deferred-steps" > "$IO/deferred-steps.txt" 2>/dev/null || true
}

# Phase "Staging provisioning": every install stashes the bundled Node tarball.
phase_stage_provisioning_state() {
    log "phase: Staging provisioning"
    install -d -m 0755 "$R/var/lib/omarchy/provisioning" "$R/var/lib/omarchy/provisioning/packages"
    cp "$W/node/$NODE_FILE" "$R/var/lib/omarchy/provisioning/packages/"
}

# Phase "Finalizing Limine boot".
phase_finalize_limine_boot() {
    record omitted "Finalizing Limine boot (limine.conf, UKI): no bootloader"
}

# Phase "Finalizing user" (run_chroot_finalizer): omarchy-provision-user as the user, with the
# ISO's bundled Node tarball at /opt/packages.
phase_run_chroot_finalizer() {
    log "phase: Finalizing user (omarchy-provision-user --force --first-install)"
    chroot_up "$R" resolv
    mkdir -p "$R/opt/packages"
    mount --bind -o ro "$W/node" "$R/opt/packages"
    iso_setup_command provision-user --user "$U" /usr/bin/omarchy-provision-user --force --first-install || true
    chroot_down "$R"
    rmdir "$R/opt/packages" 2>/dev/null || true
    grep -E 'Starting:|Completed:|Failed:|Detected|Image build' "$IO/provision-user.log" > "$IO/provision-user-steps.txt" || true
}

# Phase "Configuring login" (configure_login): the ISO's SDDM state, and the autologin it
# writes for an encrypted install, where the LUKS prompt is the authentication boundary.
phase_configure_login() {
    log "phase: Configuring login"
    install -d -m 0755 "$R/etc/sddm.conf.d"
    printf '[Theme]\nCurrent=omarchy\n\n[Users]\nRememberLastUser=true\nRememberLastSession=true\n' \
        > "$R/etc/sddm.conf.d/99-omarchy-login.conf"
    printf '[Autologin]\nUser=%s\nSession=omarchy.desktop\n' "$U" > "$R/etc/sddm.conf.d/autologin.conf"
    record changed "SDDM autologin, as the ISO writes it for an encrypted install, on a root with no LUKS prompt: the M5 has no keyboard or trackpad driver yet and the image holds no password"
    install -d -m 0755 "$R/var/lib/sddm"
    printf '[Last]\nSession=omarchy.desktop\nUser=%s\n' "$U" > "$R/var/lib/sddm/state.conf"
    chroot "$R" chown sddm:sddm /var/lib/sddm /var/lib/sddm/state.conf
    rm -f "$R/etc/systemd/system/getty@tty1.service.d/autologin.conf"
    systemctl --root="$R" enable sddm.service > /dev/null 2>&1
}

# Phases "Configuring SSH access" and "Configuring Tailscale": no-ops without an autoinstall
# drive. "Configuring DNS resolver": systemd-resolved's stub, set from outside the chroot.
phase_configure_dns_resolver() {
    log "phase: Configuring DNS resolver"
    rm -f "$R/etc/resolv.conf"
    ln -s ../run/systemd/resolve/stub-resolv.conf "$R/etc/resolv.conf"
}

# Phases "Validating boot setup" and "Creating factory snapshot".
phase_validate_and_snapshot() {
    record omitted "Validating boot setup (Limine, UKI, kernel command line) and the @factory snapshot: no bootloader, no disk"
}

stage_install() {
    DEV=$W/deviations-install.tsv
    : > "$DEV"
    rm -rf "$IO"; mkdir -p "$IO"
    : > "$IO/phases.txt"
    install_keyring_and_config
    # The ISO bundles Node's latest linux-arm64 tarball for the offline mise install
    # (builder/build-iso.sh, builder/node-release.sh); the same, with its checksum.
    mkdir -p "$W/node"
    if ! ls "$W"/node/node-v*-linux-arm64.tar.gz > /dev/null 2>&1; then
        curl -fsSL https://nodejs.org/dist/latest/SHASUMS256.txt -o "$W/node/SHASUMS256.txt"
        read -r sha file < <(awk '$2 ~ /-linux-arm64\.tar\.gz$/ {print $1, $2}' "$W/node/SHASUMS256.txt")
        curl -fsSL "https://nodejs.org/dist/latest/$file" -o "$W/node/$file"
        (cd "$W/node" && echo "$sha  $file" | sha256sum -c -)
        rm -f "$W/node/SHASUMS256.txt"
    fi
    NODE_FILE=$(basename "$(ls "$W"/node/node-v*-linux-arm64.tar.gz | head -1)")
    echo "node tarball $NODE_FILE" >> "$IO/phases.txt"
    start=$(date +%s)
    phase_arch_install_system
    echo "packages seconds $(( $(date +%s) - start ))" > "$IO/timings.txt"
    phase_configure_hibernation
    phase_run_system_finalizer
    phase_stage_provisioning_state
    phase_finalize_limine_boot
    phase_run_chroot_finalizer
    phase_configure_login
    phase_configure_dns_resolver
    phase_validate_and_snapshot
    echo "install seconds $(( $(date +%s) - start ))" >> "$IO/timings.txt"
    pac "$R" -Q > "$IO/packages.txt"
    pac "$R" -Qe > "$IO/packages-explicit.txt"
    pac "$R" -Qi | awk -F': ' '/^Name/ {n=$2} /^Installed Size/ {print $2 "\t" n}' |
        awk '{v=$1; u=$2; m=(u=="KiB")?v/1024:(u=="GiB")?v*1024:(u=="B")?v/1048576:v;
              printf "%9.2f MiB  %s\n", m, $3}' | sort -rn > "$IO/package-sizes.txt"
    systemctl --root="$R" list-unit-files --state=enabled --no-pager > "$IO/enabled-units.txt" 2>&1 || true
    cp "$R/var/log/omarchy-install.log" "$IO/omarchy-install.log" 2>/dev/null || true
    date -u +%FT%TZ > "$W/installed.stamp"
    log "$(wc -l < "$IO/packages.txt") packages installed"
}

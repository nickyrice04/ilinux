# linkcheck.sh: LINKCHECK=1 in out/job.env. Read-only facts the USB link build (LINK=1, link.sh)
# and the Claude Code install (CLAUDE=1) depend on, from the installed root ($R), the work disk,
# the build VM and the kernel tree the test-only modules are built against (KTREE). Changes
# nothing; writes out/linkcheck/.
stage_linkcheck() {
    local D=$OUT/linkcheck f
    rm -rf "$D"; mkdir -p "$D"
    set +e +o pipefail   # a report: a missing file or an empty match is a fact, not a failure
    { echo "## work disk"; df -B1 "$W" | tail -1; btrfs filesystem usage -b "$W" 2>/dev/null
      btrfs subvolume list "$W"; du -sb "$W/cache" "$W/node" "$W/tools" 2>/dev/null
      echo "## build VM"; uname -srm; echo "page size $(getconf PAGESIZE)"; gcc --version | head -1
    } > "$D/disk-and-vm.txt" 2>&1
    { echo "## kernel tree $KTREE"
      sha256sum "$KTREE/arch/arm64/boot/Image" 2>&1
      echo "want $IMAGE_SHA"
      cat "$KTREE/include/config/kernel.release" 2>&1
      ls -la "$KTREE/Module.symvers" "$KTREE/scripts/mod/modpost" 2>&1
      grep -E '^(# )?CONFIG_(USB_SERIAL|USB_SERIAL_GENERIC|USB_DUMMY_HCD|USB_GADGET|USB|MODVERSIONS|MODULE_SIG)[ =]' "$KTREE/.config" 2>&1
    } > "$D/kernel-tree.txt" 2>&1
    {
        for f in etc/environment etc/nsswitch.conf etc/hosts etc/pam.d/sddm etc/pam.d/sddm-autologin \
                 etc/pam.d/system-login etc/pam.d/system-auth etc/pam.d/system-local-login \
                 etc/pam.d/system-remote-login etc/pam.d/systemd-user etc/pam.d/sshd etc/pam.d/sudo \
                 usr/share/wayland-sessions/omarchy.desktop home/omarchy/.bash_profile \
                 home/omarchy/.bashrc home/omarchy/.config/mise/config.toml home/omarchy/.local/bin/claude; do
            echo "=== /$f"; grep -v -E '^[[:space:]]*(#|$)' "$R/$f" 2>&1
        done
        echo "=== /etc/sudoers (non-comment)"; grep -v -E '^[[:space:]]*(#|$)' "$R/etc/sudoers"
        for f in "$R"/etc/sudoers.d/*; do echo "=== ${f#$R}"; cat "$f"; done
        echo "=== /etc/ssh/sshd_config (non-comment)"; grep -v -E '^[[:space:]]*(#|$)' "$R/etc/ssh/sshd_config"
        echo "=== /etc/ssh/sshd_config.d"; ls -la "$R/etc/ssh/sshd_config.d" 2>&1
        echo "=== /usr/lib/environment.d /etc/environment.d"; ls -la "$R/usr/lib/environment.d" "$R/etc/environment.d" 2>&1
        echo "=== /etc/mise"; find "$R/etc/mise" -type f -print -exec cat {} \; 2>&1
        echo "=== mise data"; ls -la "$R/home/omarchy/.local/share/mise" "$R/home/omarchy/.local/share/mise/installs" 2>&1
        find "$R/home/omarchy/.local/share/mise" -maxdepth 3 -path '*command-wrappers*' 2>&1 | head -40
        du -sb "$R/home/omarchy/.local/share/mise" "$R/home/omarchy/.cache" 2>&1
        echo "=== Omarchy's bash PATH and mise activation"
        grep -rn -E 'PATH|mise (activate|hook)' "$R/usr/share/omarchy/default/bash" 2>/dev/null | head -30
        echo "=== time"; ls -la --time-style=full-iso "$R/var/lib/systemd/timesync" "$R/usr/lib/clock-epoch" 2>&1
        echo "=== modules"; ls "$R/usr/lib/modules" 2>&1
        echo "=== users"; chroot "$R" id omarchy; chroot "$R" getent passwd omarchy root
        chroot "$R" getent shadow omarchy root | cut -d: -f1,2,3 | sed 's/:\(.\)[^:]*:/:\1...:/'
        echo "=== tools"; chroot "$R" ssh -V 2>&1; chroot "$R" python3 --version; chroot "$R" curl --version | head -1
        ls -la "$R/usr/bin/visudo" "$R/usr/bin/timedatectl" "$R/usr/bin/socat" "$R/usr/bin/jq" 2>&1
    } > "$D/root.txt" 2>&1
    # mise's own view, offline, as the user (the registry entry the wrapper's "claude" resolves to)
    chroot_up "$R"
    chroot --userspec=1000:1000 "$R" /usr/bin/env -i HOME=/home/omarchy USER=omarchy LOGNAME=omarchy \
        PATH=/home/omarchy/.local/bin:/usr/local/bin:/usr/bin LANG=C.UTF-8 MISE_OFFLINE=1 \
        bash -c 'mise --version; echo "## registry"; mise registry claude; echo "## tool"; mise tool claude 2>&1 | head -20
                 echo "## settings"; mise settings 2>&1 | head -60; echo "## ls"; mise ls 2>&1 | head -40
                 echo "## which"; type -a claude; mise which claude 2>&1' > "$D/mise.txt" 2>&1
    chroot_down "$R"
    cat "$D"/*.txt | head -400
    set -e -o pipefail
}

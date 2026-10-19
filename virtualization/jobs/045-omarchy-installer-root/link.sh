# link.sh: the build options LINK=1 and CLAUDE=1 of job 045, sourced by ramroot.sh (stage 2, inside the
# job VM) and run on the RAM root's snapshot ($C) after its own changes. Every addition is recorded.
#  stage_link: the USB link of job 039's RAM root, so the M1 reaches Omarchy itself: the gadget with two
#    bulk-only gser interfaces (the journal on 0, an SSH byte pipe on 1), sshd in inetd mode on the pipe
#    for the desktop user, key-only with the operator's public key, the M1's web proxy in the environment
#    of the desktop session and of SSH logins, and a helper through which the M1 sets the clock. Job 039's
#    files are taken as committed (omarchy-arm64/ram-root/overlay at HEAD) and not changed; what only this
#    root needs is in link-overlay/.
#  stage_claude: Claude Code, installed the way Omarchy installs it on first use: its own wrapper
#    (~/.local/bin/claude, written by omarchy-mise-install) run once, which is mise use -g claude, so
#    claude starts on the M5 without a download. Nothing is signed in.
#  stage_nopasswd (NOPASSWD=1, user-approved 2026-10-18): Omarchy's own permanent passwordless-sudo
#    grant for the desktop user, as omarchy-sudo-passwordless permanent writes it, so that agents in the
#    session can use sudo (pacman, modules, driver work); Omarchy's --disable removes it.

L39=omarchy-arm64/ram-root/overlay   # job 039's layer, read from Git at HEAD
LO=$J/link-overlay

# from39 PATH MODE: one file of job 039's layer, as committed, into the RAM root
from39() {
    install -d "$C/$(dirname "$1")"
    git -c safe.directory='*' -C /mnt/ilinux show "HEAD:$L39/$1" > "$C/$1"
    chmod "$2" "$C/$1"
    echo "$1 $(sha256sum < "$C/$1" | cut -d' ' -f1)" >> "$OUT/build/link-files.txt"
}
# fromlo PATH MODE: one file of link-overlay/ into the RAM root
fromlo() {
    install -D -m "$2" "$LO/$1" "$C/$1"
    echo "$1 $(sha256sum < "$C/$1" | cut -d' ' -f1)" >> "$OUT/build/link-files.txt"
}

stage_link() {
    log "link: the USB gadget, sshd on its byte pipe, the M1's proxy, the clock helper"
    : > "$OUT/build/link-files.txt"
    echo "job 039's layer at ilinux $(git -c safe.directory='*' -C /mnt/ilinux rev-parse --short HEAD)" >> "$OUT/build/link-files.txt"

    # The gadget: one per device-mode controller, started by udev when the controller appears.
    from39 usr/local/lib/ilinux/usb-gadget.sh 0755
    from39 etc/default/ilinux-usb-gadget 0644
    from39 etc/systemd/system/ilinux-usb-gadget@.service 0644
    from39 etc/udev/rules.d/90-ilinux-usb.rules 0644
    grep -qx 'FUNCTION=gser' "$C/etc/default/ilinux-usb-gadget"
    grep -qx 'ACM=0' "$C/etc/default/ilinux-usb-gadget"
    record added "the USB control channel of job 039's RAM root (omarchy-arm64/ram-root/overlay at HEAD: usb-gadget.sh, ilinux-usb-gadget@.service, 90-ilinux-usb.rules, /etc/default/ilinux-usb-gadget with FUNCTION=gser): per device-mode controller one gadget with two bulk-only gser interfaces, the journal on interface 0 and a raw SSH byte pipe on interface 1, no interrupt endpoint: the M5's only way to the second computer, and the M1's own tools read both"

    # sshd on the pipe, one connection at a time, in inetd mode; key-only. Omarchy enables no SSH server.
    from39 etc/systemd/system/ilinux-sshd-tty@.service 0644
    from39 etc/ssh/sshd_config.d/20-ilinux-ram-root.conf 0644
    from39 etc/ssh/sshd_config.d/25-ilinux-usb-pipe.conf 0644
    grep -q '^Include /etc/ssh/sshd_config.d/\*.conf' "$C/etc/ssh/sshd_config"
    record added "sshd on the byte pipe (job 039's ilinux-sshd-tty@.service: sshd -i on the raw port, one connection at a time, restarted after each; sshd_config.d/20-ilinux-ram-root.conf: key-only, no passwords; 25-ilinux-usb-pipe.conf: LoginGraceTime 45, ClientAlive 15 x 3, SetEnv with the proxy): Omarchy enables no SSH server, and this one listens on nothing but the pipe"

    # The host key is made at boot: the image holds no private key.
    [ ! -e "$C/etc/ssh/ssh_host_ed25519_key" ]
    fromlo etc/systemd/system/ilinux-ssh-hostkey.service 0644
    fromlo etc/systemd/system/ilinux-sshd-tty@.service.d/10-ilinux-hostkey.conf 0644
    systemctl --root="$C" enable ilinux-ssh-hostkey.service > /dev/null 2>&1
    record added "the SSH host key made at each boot (ilinux-ssh-hostkey.service, ed25519, before sshd through a drop-in for job 039's unit; its fingerprint to the journal, which interface 0 carries): the image holds no private key, so the M1 records a new host key after every boot (build/control/known_hosts-omarchy, cleared before each)"

    # The operator's public key, for the desktop user only (job 039 also authorizes root). sshd reads an
    # authorized-keys file as the user it logs in, so the file is 0644: a root-only 0600 file, as job
    # 039 writes, would refuse every omarchy login.
    local auth=$OUT/authorized_keys n
    [ -s "$auth" ] || auth=/mnt/ilinux/kernel/experiments/usb-gadget/authorized_keys
    if grep -q -i 'PRIVATE KEY' "$auth"; then echo "$auth holds a private key"; return 1; fi
    ssh-keygen -l -f "$auth" > "$OUT/build/authorized-keys-fingerprints.txt"
    n=$(grep -c -v -E '^[[:space:]]*(#|$)' "$auth")
    [ "$n" -ge 1 ] && [ "$n" = "$(wc -l < "$OUT/build/authorized-keys-fingerprints.txt")" ] ||
        { echo "$auth: $n lines but $(wc -l < "$OUT/build/authorized-keys-fingerprints.txt") public keys"; return 1; }
    install -d -m 0755 "$C/etc/ssh/authorized_keys.d"
    install -m 0644 "$auth" "$C/etc/ssh/authorized_keys.d/omarchy"
    echo "source ${auth#/mnt/ilinux/}" >> "$OUT/build/authorized-keys-fingerprints.txt"
    record added "the operator's public key for the desktop user (/etc/ssh/authorized_keys.d/omarchy, 0644, from out/authorized_keys when present, else the M1's committed key kernel/experiments/usb-gadget/authorized_keys, as job 039 does); root gets none: logins are key-only, as omarchy"

    # The M1's web proxy, reverse-forwarded by its SSH session to 127.0.0.1:3128 here.
    if grep -q -v -E '^[[:space:]]*(#|$)' "$C/etc/environment" 2> /dev/null; then
        echo "/etc/environment is not empty; merge it with job 039's by hand"; return 1
    fi
    from39 etc/environment 0644
    [ -L "$C/usr/lib/environment.d/99-environment.conf" ]
    record added "/etc/environment (job 039's, replacing the root's empty one): HTTPS_PROXY, HTTP_PROXY (and lower case) at http://127.0.0.1:3128, where the M1's SSH session reverse-forwards its CONNECT proxy, NO_PROXY for loopback. pam_env sets them for the SDDM autologin session and SSH logins, and the user manager reads the file through environment.d (systemd's 99-environment.conf link), so the desktop session's programs have them too; the port answers only while that session is open"

    # The clock: the M1 sets it over SSH (tools/m1n1-client/m5-clock.py).
    fromlo usr/local/lib/ilinux/set-clock 0755
    fromlo etc/sudoers.d/ilinux-clock 0440
    record added "the clock helper /usr/local/lib/ilinux/set-clock and one sudo rule for it (/etc/sudoers.d/ilinux-clock: omarchy, no password, no arguments): the M5 has no clock source in this path (no RTC driver, no route for NTP), so every boot starts with a wrong clock and TLS fails; the M1 sends its clock over SSH right after connecting, before any web access"

    # Checks on the files as the root's own tools read them. sshd needs a host key to test its
    # configuration, so a throwaway one in the chroot's /tmp (a tmpfs that goes with chroot_down).
    chroot_up "$C"
    chroot "$C" visudo -c -q
    chroot "$C" ssh-keygen -q -t ed25519 -N '' -f /tmp/hostkey-check
    chroot "$C" /usr/bin/sshd -t -h /tmp/hostkey-check
    chroot "$C" /usr/bin/sshd -T -h /tmp/hostkey-check -C user=omarchy,host=m5,addr=127.0.0.1 > "$OUT/build/sshd-T-omarchy.txt" 2>&1
    chroot "$C" bash -n /usr/local/lib/ilinux/set-clock
    chroot "$C" sh -n /usr/local/lib/ilinux/usb-gadget.sh
    chroot_down "$C"
    grep -i -E '^(authorizedkeysfile|passwordauthentication|kbdinteractiveauthentication|permitrootlogin|pubkeyauthentication|usepam|logingracetime|clientaliveinterval|clientalivecountmax|setenv|hostkey) ' \
        "$OUT/build/sshd-T-omarchy.txt" | tee "$OUT/build/sshd-effective.txt"
    grep -q -i -x 'passwordauthentication no' "$OUT/build/sshd-effective.txt"
    grep -q -i -E '^authorizedkeysfile .*/etc/ssh/authorized_keys\.d/(%u|omarchy)( |$)' "$OUT/build/sshd-effective.txt"
    systemd-analyze --root="$C" verify "$C/etc/systemd/system/ilinux-usb-gadget@.service" \
        "$C/etc/systemd/system/ilinux-sshd-tty@.service" "$C/etc/systemd/system/ilinux-ssh-hostkey.service" \
        > "$OUT/build/link-units-verify.txt" 2>&1 || true
    [ ! -e "$C/etc/ssh/ssh_host_ed25519_key" ] && [ ! -e "$C/tmp/hostkey-check" ]
}

stage_claude() {
    log "Claude Code: Omarchy's own wrapper, run once (mise use -g claude), signed out"
    local H=$C/home/omarchy B=$OUT/build v
    [ -x "$H/.local/bin/claude" ]
    # the wrapper omarchy-mise-install wrote (out/elfcheck/claude-wrapper.txt has the same lines)
    grep -qx 'mise use -g --quiet "claude" || exit 1' "$H/.local/bin/claude"
    grep -qx 'exec mise x "claude" -- "claude" "$@"' "$H/.local/bin/claude"
    [ ! -e "$H/.local/share/mise/installs/claude" ]
    cp "$H/.config/mise/config.toml" "$B/mise-config-before.toml"
    ( cd "$H" && find . -mindepth 1 -printf '%P\n' | LC_ALL=C sort ) > "$B/home-before.txt"
    # As an SSH command on the M5 would run it: the user, PAM's PATH (Omarchy's pam_env.conf line:
    # mise's shims and ~/.local/bin after the system's), the build VM's network.
    chroot_up "$C" resolv
    local t0=$SECONDS rc=0
    timeout 1200 chroot --userspec=1000:1000 --groups="$(chroot "$C" id -G omarchy | tr ' ' ,)" "$C" /usr/bin/env -i \
        HOME=/home/omarchy USER=omarchy LOGNAME=omarchy SHELL=/usr/bin/bash LANG=en_US.UTF-8 \
        PATH=/usr/local/sbin:/usr/local/bin:/usr/bin:/home/omarchy/.local/share/mise/shims:/home/omarchy/.local/bin \
        /home/omarchy/.local/bin/claude --version > "$B/claude-install.log" 2>&1 || rc=$?
    chroot --userspec=1000:1000 "$C" /usr/bin/env -i HOME=/home/omarchy PATH=/usr/bin MISE_OFFLINE=1 \
        bash -c 'mise ls claude; mise which claude; mise where claude' > "$B/claude-mise.txt" 2>&1 || true
    chroot_down "$C"
    echo "wrapper exit $rc after $((SECONDS - t0)) s" >> "$B/claude-install.log"
    cat "$B/claude-install.log" "$B/claude-mise.txt"
    [ "$rc" = 0 ] || return 1
    v=$(grep -o -E '^[0-9]+\.[0-9]+\.[0-9]+' "$B/claude-install.log" | head -1)
    [ -n "$v" ] || { echo "no version from claude --version"; return 1; }
    diff "$B/mise-config-before.toml" "$H/.config/mise/config.toml" > "$B/mise-config.diff" || true
    ( cd "$H" && find . -mindepth 1 -printf '%P\n' | LC_ALL=C sort ) > "$B/home-after.txt"
    LC_ALL=C comm -13 "$B/home-before.txt" "$B/home-after.txt" > "$B/home-new.txt"
    # mise's own directories are the install; anything else the run left behind is listed, and the
    # agent's state (it has none after --version: Likely) would go: no account, no identifier.
    grep -v -E '^(\.local/share/mise|\.local/state/mise|\.cache/mise|\.config/mise)(/|$)' "$B/home-new.txt" \
        > "$B/home-new-outside-mise.txt" || true
    if grep -q -E '^\.claude' "$B/home-new-outside-mise.txt"; then
        grep -E '^\.claude[^/]*$' "$B/home-new-outside-mise.txt" | while read -r p; do rm -rf "${H:?}/$p"; done
        record changed "removed what claude --version wrote in the home ($(grep -E '^\.claude[^/]*$' "$B/home-new-outside-mise.txt" | tr '\n' ' ')): no agent state in the image"
    fi
    # mise keeps the downloaded tarball in its content-addressed download store: a second, compressed
    # copy of the binary, which a RAM root would carry in memory and the M1 would upload every boot.
    if [ -d "$H/.cache/mise/downloads-cas" ]; then
        local cas
        cas=$(du -sb "$H/.cache/mise/downloads-cas" | cut -f1)
        rm -rf "$H/.cache/mise/downloads-cas"
        record changed "mise's download store left out (~/.cache/mise/downloads-cas, $cas bytes: the claude-linux-arm64 tarball the installed binary came from): a second copy that the RAM root would hold in memory and the M1 upload at every boot; mise downloads again only for a version it does not have"
    fi
    du -sb "$H/.local/share/mise/installs/claude" "$H/.cache/mise" 2> /dev/null > "$B/claude-sizes.txt" || true
    find "$H/.local/share/mise/installs/claude" -type f -size +1M -printf '%s %P\n' | sort -rn | head -5 >> "$B/claude-sizes.txt"
    python3 -I /mnt/ilinux/virtualization/jobs/039-omarchy-ram-root/elf_page_check.py "$H/.local/share/mise/installs/claude" \
        > "$B/claude-elf-16k-check.txt" 2>&1 || true
    cat "$B/mise-config.diff" "$B/home-new-outside-mise.txt" "$B/claude-sizes.txt"
    head -4 "$B/claude-elf-16k-check.txt"
    # Signed out: no credentials file, no token in the user's files or the environment.
    [ ! -e "$H/.claude/.credentials.json" ]
    if grep -r -l -I -E 'sk-ant-[A-Za-z0-9_-]{20,}|(CLAUDE_CODE_OAUTH_TOKEN|ANTHROPIC_API_KEY|ANTHROPIC_AUTH_TOKEN)=[A-Za-z0-9]' "$H" "$C/etc/environment" \
           --exclude-dir=installs --exclude-dir=.cache 2> /dev/null; then
        echo "a credential-looking string is in the home or the environment"; return 1
    fi
    record added "Claude Code $v, installed at build time by running Omarchy's own wrapper once (~/.local/bin/claude --version, which runs MISE_MINIMUM_RELEASE_AGE=0 mise use -g --quiet claude: mise's aqua:anthropics/claude-code; ~/.config/mise/config.toml gains claude as on first use), so claude starts on the M5 without a first-use download. Signed out: no credentials, no token"
}

# Omarchy's permanent grant (omarchy-settings: /usr/bin/omarchy-sudo-passwordless, enable_locked and
# read_grant): /etc/sudoers.d/99-omarchy-permanent-nopasswd-<uid>, root:root 0440, holding exactly
# "<account> ALL=(ALL) NOPASSWD: ALL" and nothing else (--active and --disable match the whole file, so
# it carries no comment), checked with visudo -cf. Boot cleanup and the settings package's hook remove
# only the timed grants (99-omarchy-nopasswd-*), so this one survives as on an installed machine.
stage_nopasswd() {
    log "passwordless sudo for omarchy: Omarchy's own permanent grant"
    local uid name f
    uid=$(chroot "$C" id -u omarchy)
    name=$(chroot "$C" id -un "$uid")
    [ "$uid" = 1000 ] && [ "$name" = omarchy ] || { echo "unexpected desktop account $name ($uid)"; return 1; }
    [[ $name =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] || { echo "Omarchy's script refuses the account name $name"; return 1; }
    f=etc/sudoers.d/99-omarchy-permanent-nopasswd-$uid
    [ ! -e "$C/$f" ] && [ ! -e "$C/etc/sudoers.d/99-omarchy-nopasswd-$uid" ] || { echo "a grant for $uid already exists"; return 1; }
    printf '%s ALL=(ALL) NOPASSWD: ALL\n' "$name" > "$C/$f"
    chown root:root "$C/$f"
    chmod 0440 "$C/$f"
    chroot_up "$C"
    chroot "$C" visudo -c -q -f "/$f"
    chroot "$C" visudo -c -q
    chroot_down "$C"
    # nobody else gets an unrestricted grant: the only "NOPASSWD: ALL" in the policy is this one (stock
    # /etc/sudoers carries one for %wheel commented out)
    local others
    others=$(grep -l -E '^[^#]*NOPASSWD:[[:space:]]*ALL[[:space:]]*$' "$C"/etc/sudoers "$C"/etc/sudoers.d/* | sed "s#$C/##")
    [ "$others" = "$f" ] || { echo "unrestricted grants: $others"; return 1; }
    echo "$f $(stat -c '%U:%G %a' "$C/$f") $(sha256sum < "$C/$f" | cut -d' ' -f1)" >> "$OUT/build/link-files.txt"
    record changed "passwordless sudo for omarchy, user-approved 2026-10-18: Omarchy's own permanent grant, as omarchy-sudo-passwordless permanent writes it (/$f, root:root 0440, exactly '$name ALL=(ALL) NOPASSWD: ALL'). Agents in the Omarchy session need sudo for pacman, loading modules and driver work, and the image has no password; it is RAM-only, offline except through the M1's relay, and SSH takes only the operator's key. Reversible with Omarchy's own omarchy-sudo-passwordless --disable; boot cleanup and the package hook leave permanent grants alone. Nothing for root or any other account"
}

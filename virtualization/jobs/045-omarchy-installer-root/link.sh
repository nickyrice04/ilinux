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

    # Attempt 25's findings (native/boot/stage-b-2026-10-19-attempt25-result.md, "For the M5").
    # 1. Claude Code, started over SSH, opened its sign-in page in Chromium on the M5's own screen, through
    #    the BROWSER Omarchy's interactive shell sets (omarchy-launch-browser).
    fromlo etc/profile.d/ilinux-ssh-browser.sh 0644
    fromlo usr/local/lib/ilinux/ssh-browser 0755
    grep -q 'export BROWSER="${BROWSER:-omarchy-launch-browser}"' "$C/usr/share/omarchy/default/bash/envs" ||
        { echo "Omarchy's bash envs no longer keep a BROWSER that is already set"; return 1; }
    record added "SSH sessions open no browser on the M5 (/etc/profile.d/ilinux-ssh-browser.sh: in a login shell with SSH_CONNECTION set, BROWSER=/usr/local/lib/ilinux/ssh-browser, which prints the address and opens nothing; Omarchy's default/bash/envs keeps a BROWSER that is already set): in attempt 25, claude started over SSH opened its sign-in page in Chromium on the M5's screen, where nobody could use it; the desktop session has no SSH_CONNECTION and keeps Omarchy's omarchy-launch-browser"
    # 2. archlinux-keyring-wkd-sync starts right after the clock step and fails every 300 s (gpg's WKD
    #    lookups use no proxy and the M5 has no route): 75% of attempt 25's journal.
    [ -e "$C/usr/lib/systemd/system/archlinux-keyring-wkd-sync.timer" ] ||
        { echo "no archlinux-keyring-wkd-sync.timer in the root"; return 1; }
    systemctl --root="$C" mask archlinux-keyring-wkd-sync.timer archlinux-keyring-wkd-sync.service > /dev/null 2>&1
    [ "$(readlink "$C/etc/systemd/system/archlinux-keyring-wkd-sync.timer")" = /dev/null ]
    record changed "archlinux-keyring-wkd-sync.timer and .service masked: the clock step makes the timer fire at once, and gpg's WKD lookups cannot reach the web here (no route; they ignore the proxy), so the unit failed and was restarted every 300 s, about 1,200 journal lines each time, 75% of attempt 25's journal; the keyring itself is the one the image's first boot makes"
    # 3. On the ports with no cable, sshd -i timed out after its 45 s login grace and was restarted, three
    #    journal lines every 47 s per port.
    fromlo usr/local/lib/ilinux/wait-usb-host 0755
    fromlo etc/systemd/system/ilinux-sshd-tty@.service.d/20-ilinux-wait-host.conf 0644
    record changed "sshd on a USB port starts only once a host has configured that port (ilinux-sshd-tty@.service.d/20-ilinux-wait-host.conf: ExecStartPre /usr/local/lib/ilinux/wait-usb-host, silent while it waits, TimeoutStartSec=infinity; SuccessExitStatus=3, the login grace time's exit since OpenSSH 9.8): in attempt 25 the two uncabled ports restarted sshd 19 times each, three journal lines per 47 s; on the cabled port nothing changes once the M1 has selected the configuration"
    # 4. Chromium's component updater fetched about 31 MB through the M1's relay at its first run.
    fromlo etc/chromium/policies/managed/ilinux-component-updates.json 0644
    grep -a -q '/etc/chromium/policies' "$C/usr/lib/chromium/chromium" ||
        { echo "the chromium binary does not read /etc/chromium/policies"; return 1; }
    record added "Chromium's component updates off (/etc/chromium/policies/managed/ilinux-component-updates.json: ComponentUpdatesEnabled false, Chromium's managed policy): in attempt 25 its updater fetched about 31 MB of components through the M1's relay, which carries the M5's whole web"

    # Checks on the files as the root's own tools read them. sshd needs a host key to test its
    # configuration, so a throwaway one in the chroot's /tmp (a tmpfs that goes with chroot_down).
    chroot_up "$C"
    chroot "$C" visudo -c -q
    chroot "$C" ssh-keygen -q -t ed25519 -N '' -f /tmp/hostkey-check
    chroot "$C" /usr/bin/sshd -t -h /tmp/hostkey-check
    chroot "$C" /usr/bin/sshd -T -h /tmp/hostkey-check -C user=omarchy,host=m5,addr=127.0.0.1 > "$OUT/build/sshd-T-omarchy.txt" 2>&1
    chroot "$C" bash -n /usr/local/lib/ilinux/set-clock
    chroot "$C" sh -n /usr/local/lib/ilinux/usb-gadget.sh
    chroot "$C" sh -n /usr/local/lib/ilinux/wait-usb-host
    chroot "$C" sh -n /usr/local/lib/ilinux/ssh-browser
    chroot "$C" sh -n /etc/profile.d/ilinux-ssh-browser.sh
    chroot "$C" python3 -I -c 'import json, sys; json.load(open(sys.argv[1]))' /etc/chromium/policies/managed/ilinux-component-updates.json
    chroot_down "$C"
    grep -i -E '^(authorizedkeysfile|passwordauthentication|kbdinteractiveauthentication|permitrootlogin|pubkeyauthentication|usepam|logingracetime|clientaliveinterval|clientalivecountmax|setenv|hostkey) ' \
        "$OUT/build/sshd-T-omarchy.txt" | tee "$OUT/build/sshd-effective.txt"
    grep -q -i -x 'passwordauthentication no' "$OUT/build/sshd-effective.txt"
    grep -q -i -E '^authorizedkeysfile .*/etc/ssh/authorized_keys\.d/(%u|omarchy)( |$)' "$OUT/build/sshd-effective.txt"
    systemd-analyze --root="$C" verify "$C/etc/systemd/system/ilinux-usb-gadget@.service" \
        "$C/etc/systemd/system/ilinux-sshd-tty@.service" "$C/etc/systemd/system/ilinux-ssh-hostkey.service" \
        > "$OUT/build/link-units-verify.txt" 2>&1 || true
    [ ! -e "$C/etc/ssh/ssh_host_ed25519_key" ] && [ ! -e "$C/tmp/hostkey-check" ]
    if [ -n "$MODULES" ]; then stage_modules; fi
}

# stage_modules (LINK=1 with MODULES, attempt 26): boot042's keyboard modules (job 050's export,
# MODULES=<its export/modules>) under /usr/lib/modules/<release>, indexed by the root's own depmod, kept
# from loading at boot by a blacklist, and ilinux-keyboard, which loads them over SSH one at a time. The
# trackpad and storage modules of the same build are never put here.
stage_modules() {
    log "modules: boot042's keyboard path, loaded only by ilinux-keyboard"
    local man=$MODULES/manifest.json krel vermagic d n names
    [ -f "$man" ] || { echo "no $man (MODULES must be job 050's export/modules)"; return 1; }
    krel=$(python3 -I -c 'import json, sys; print(json.load(open(sys.argv[1]))["kernel_release"])' "$man")
    vermagic=$(python3 -I -c 'import json, sys; print(json.load(open(sys.argv[1]))["vermagic"])' "$man")
    [ "$(python3 -I -c 'import json, sys; print(json.load(open(sys.argv[1]))["image_sha256"])' "$man")" = "$IMAGE_SHA" ] ||
        { echo "the modules in $MODULES are not for the Image $IMAGE_SHA"; return 1; }
    strings -n 20 "$KERNEL" | grep -qxF "$vermagic" || { echo "vermagic '$vermagic' is not the Image's"; return 1; }
    d=$C/usr/lib/modules/$krel
    [ ! -e "$d" ] || { echo "$d exists already"; return 1; }
    install -d -m 0755 "$C/usr/lib/modules"      # the root has no kernel package, so no modules directory
    cp -a "$MODULES/keyboard-root/usr/lib/modules/$krel" "$C/usr/lib/modules/$krel"
    (cd "$C" && sha256sum -c --quiet "$MODULES/keyboard-root/SHA256SUMS")
    chroot "$C" depmod -a "$krel"
    names=$(sed -E 's#^([^:]*/)?([^/:]+)\.ko:.*#\2#' "$d/modules.dep" | sort | tr '\n' ' ')
    echo "modules.dep: $names" >> "$OUT/build/modules.txt"
    for n in apple-rtkit-helper apple-dockchannel dockchannel-hid hid-apple; do
        case " $names " in *" $n "*) ;; *) echo "depmod did not index $n"; return 1 ;; esac
    done
    if find "$C/usr/lib/modules" -name 'nvme*.ko*' -o -name 'apple-sart*.ko*' -o -name 'hid-magicmouse*.ko*' | grep -q .; then
        echo "a storage or trackpad module is in the root"; return 1
    fi
    # What udev's coldplug asks for at boot, for the MTP nodes of boot042's DT (of_modalias(): name, type,
    # each compatible): each alias resolves to its module before the blacklist is in place and to nothing
    # after it (kmod applies a blacklist to every lookup by alias; -b also to module names); the modules
    # still resolve by name, as ilinux-keyboard loads them. modprobe dry runs in the chroot (its /proc,
    # /sys and /dev mounted, as kmod reads /proc/cmdline); the outputs are kept.
    local alias want mp=$OUT/build/modules-modprobe.txt
    : > "$mp"
    chroot_up "$C"
    for pass in before after; do
        [ "$pass" = after ] && fromlo etc/modprobe.d/ilinux-boot042.conf 0644
        for alias in 'of:NmtpT(null)Capple,t6050-mtpCapple,t6050-rtk-helper-asc4Capple,mtpCapple,rtk-helper-asc4=apple-rtkit-helper' \
                     'of:NfifoT(null)Capple,t6050-dockchannelCapple,dockchannel=apple-dockchannel' \
                     'of:NinputT(null)Capple,t6050-dockchannel-hidCapple,dockchannel-hid=dockchannel-hid'; do
            want=${alias##*=}; alias=${alias%=*}
            { echo "== $pass the blacklist: modprobe -n -v -S $krel '$alias'"; chroot "$C" modprobe -n -v -S "$krel" "$alias" 2>&1; } >> "$mp" || true
            n=$(chroot "$C" modprobe -n -v -S "$krel" "$alias" 2>&1 | grep -c "^insmod .*/$want\.ko" || true)
            if [ "$pass" = before ]; then
                [ "$n" -ge 1 ] || { chroot_down "$C"; cat "$mp"; echo "the alias $alias does not resolve to $want"; return 1; }
            else
                [ "$n" = 0 ] || { chroot_down "$C"; cat "$mp"; echo "the blacklist does not stop $alias"; return 1; }
                echo "coldplug $alias: resolved to $want without the blacklist, to nothing with it" >> "$OUT/build/modules.txt"
            fi
        done
    done
    for n in apple-rtkit-helper apple-dockchannel hid-apple dockchannel-hid; do
        { echo "== by name: modprobe -n -v -S $krel $n"; chroot "$C" modprobe -n -v -S "$krel" "$n" 2>&1; } >> "$mp" || true
        chroot "$C" modprobe -n -v -S "$krel" "$n" 2>&1 | grep -q "^insmod .*/$n\.ko" ||
            { chroot_down "$C"; cat "$mp"; echo "modprobe $n does not resolve by name"; return 1; }
    done
    chroot_down "$C"
    fromlo usr/local/bin/ilinux-keyboard 0755
    chroot "$C" bash -n /usr/local/bin/ilinux-keyboard
    install -d -m 0755 "$C/usr/share/ilinux"   # ramroot.sh writes build-info.txt here later
    { echo "kernel_release $krel"; echo "vermagic $vermagic"; echo "image_sha256 $IMAGE_SHA"
      sed 's/^/sha256 /' "$MODULES/keyboard-root/SHA256SUMS"; } > "$C/usr/share/ilinux/keyboard-modules.txt"
    cat "$OUT/build/modules.txt" "$C/usr/share/ilinux/keyboard-modules.txt"
    record added "boot042's keyboard modules for $krel (apple-rtkit-helper, apple-dockchannel, dockchannel-hid with the MTP ring transport, hid-apple; job 050's build, digests in /usr/share/ilinux/keyboard-modules.txt) under /usr/lib/modules/$krel, indexed by the root's depmod: boot042 builds the keyboard path as modules so that nothing of it runs at boot. Omarchy's linux-modules-cleanup keeps this directory because it is the running kernel's (%v)"
    record added "/etc/modprobe.d/ilinux-boot042.conf blacklists the four keyboard modules: udev's coldplug, which loads modules by device aliases at every boot, must not start the keyboard path (checked: the MTP nodes' aliases load nothing with the blacklist, the modules still load by name)"
    record added "/usr/local/bin/ilinux-keyboard: run over SSH (sudo), it loads the keyboard modules one at a time with a check after each (kernel log, binding, the ring, the keyboard interface, the input device, typing on the M5), stops at the first failure and changes nothing else"
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

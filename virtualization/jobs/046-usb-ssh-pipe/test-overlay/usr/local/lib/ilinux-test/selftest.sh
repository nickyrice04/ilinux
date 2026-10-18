#!/bin/bash
# VM-only self-test (job 046) of the USB SSH byte pipe and the web proxy. In the test kernel
# (job 041's Image-test) dummy_hcd makes this kernel the host of its own gadget, so one boot
# holds both ends: the M5 side is the RAM root's overlay as systemd runs it (the udev rule,
# ilinux-usb-gadget@dummy_udc.0 with gser.log + gser.ssh, ilinux-sshd-tty@ttyGS1 with sshd -i,
# sshd_config.d/25-ilinux-usb-pipe.conf, /etc/environment), in a private network namespace;
# the M1 side is this script in the root namespace: the generic usb-serial driver as the
# host's view of the two interfaces, the Linux build of tools/m1n1-client/usb-pipe as ssh's
# ProxyCommand on interface 1, connect-proxy.py and an HTTPS server on 127.0.0.1, and ssh
# with tools/m1n1-client/m5-ssh-config's settings. Never shipped.
set -u
T=/usr/local/lib/ilinux-test
say() { echo "[selftest] $*"; }
fail() {
    say "FAIL: $*"
    systemctl --no-pager --failed --plain 2>&1 | head -20
    echo "--- usb-pipe log"; cat /tmp/usb-pipe.log 2>/dev/null | tail -20
    echo "--- proxy log"; cat /tmp/proxy.log 2>/dev/null | tail -10
    echo "--- journal (sshd, gadget)"
    journalctl -b --no-pager -o short-monotonic -u 'ilinux-*' 2>&1 | tail -40
    echo "[selftest] END"
    exit 1
}
# The RAM root itself has no Python (the proxy and the HTTPS server need it): then this is a partial
# test, which still runs the real systemd/udev start, OpenSSH, the pipe, the reverse forward's listener
# on the M5 side, transfers and recovery. job 046's own base root has Python, and the test is full.
if command -v python3 > /dev/null 2>&1; then FULL=1; else FULL=0; fi
t0=$(date +%s.%N)
elapsed() { awk -v a="$t0" -v b="$(date +%s.%N)" 'BEGIN {printf "%.1f", b - a}'; }

say "start: $(uname -r), $(systemctl --version | head -1), $(/usr/bin/sshd -V 2>&1 | head -1)"
say "mode: $([ $FULL = 1 ] && echo 'full (Python present: proxy and HTTPS server)' || echo 'partial (no Python in this root: no proxy and no HTTPS server)')"

# ---- the M5 side, as the RAM root's units run it ------------------------------------------
udc=$(ls /sys/class/udc 2>/dev/null | head -1)
[ -n "$udc" ] || fail "no UDC: this kernel has no dummy_hcd"
unit="ilinux-usb-gadget@$udc.service"
for _ in $(seq 60); do systemctl is-active -q "$unit" && break; sleep 1; done
systemctl is-active -q "$unit" || fail "$unit is not active: $(systemctl status --no-pager -n 15 "$unit" 2>&1 | tail -15)"
G=/sys/kernel/config/usb_gadget/ilinux-$(printf '%s' "$udc" | tr -c 'A-Za-z0-9' '_')
[ -d "$G/functions/gser.log" ] && [ -d "$G/functions/gser.ssh" ] || fail "gser.log and gser.ssh missing under $G"
[ "$(cat "$G/bcdDevice")" = 0x0039 ] || fail "bcdDevice $(cat "$G/bcdDevice")"
[ "$(cat "$G/UDC")" = "$udc" ] || fail "the gadget is not bound to $udc"
log_port=$(cat "$G/functions/gser.log/port_num")
ssh_port=$(cat "$G/functions/gser.ssh/port_num")
for _ in $(seq 30); do [ "$(cat "/sys/class/udc/$udc/state")" = configured ] && break; sleep 1; done
say "M5 side: $unit active; gser.log on ttyGS$log_port (interface 0), gser.ssh on ttyGS$ssh_port (interface 1); UDC $(cat "/sys/class/udc/$udc/state"); configuration \"$(cat "$G/configs/c.1/strings/0x409/configuration")\""
sunit="ilinux-sshd-tty@ttyGS$ssh_port.service"
for _ in $(seq 30); do systemctl is-active -q "$sunit" && break; sleep 1; done
systemctl is-active -q "$sunit" || fail "$sunit is not active: $(systemctl status --no-pager -n 15 "$sunit" 2>&1 | tail -15)"
spid=$(systemctl show -p MainPID --value "$sunit")
[ -n "$spid" ] && [ "$spid" != 0 ] && [ -d "/proc/$spid" ] || fail "$sunit has no main process"
[ "$(readlink "/proc/$spid/ns/net")" != "$(readlink /proc/1/ns/net)" ] || fail "sshd is not in the private network namespace (test drop-in)"
effective() {  # effective NAME: the value of one sshd option, from sshd -T or else the RAM root's drop-in
    v=$(/usr/bin/sshd -T 2> /tmp/sshd-T.err | awk -v k="$(echo "$1" | tr A-Z a-z)" 'tolower($1) == k {print $2; exit}')   # OpenSSH 10 prints CamelCase names
    [ -n "$v" ] || v=$(awk -v k="$1" '$1 == k {print $2; exit}' /etc/ssh/sshd_config.d/25-ilinux-usb-pipe.conf)
    echo "$v"
}
say "M5 side: $sunit active (main pid $spid: $(tr '\0' ' ' < "/proc/$spid/cmdline" | cut -c1-60)), private network namespace; LoginGraceTime $(effective LoginGraceTime) ClientAlive $(effective ClientAliveInterval)x$(effective ClientAliveCountMax)"
[ -s /tmp/sshd-T.err ] && say "note: sshd -T printed: $(head -2 /tmp/sshd-T.err | tr '\n' ' ')"
raw=
for _ in $(seq 40); do   # the unit is active once its process exists; the script's stty follows
    if stty -F "/dev/ttyGS$ssh_port" -a 2> /dev/null | tr '\n' ' ' | grep -q -- ' -echo ' &&
       stty -F "/dev/ttyGS$ssh_port" -a 2> /dev/null | tr '\n' ' ' | grep -q -- ' -icanon '; then raw=1; break; fi
    sleep 0.25
done
[ -n "$raw" ] || fail "ttyGS$ssh_port is not raw after 10 s: $(stty -F "/dev/ttyGS$ssh_port" -a 2>&1 | tr '\n' ' ' | cut -c1-200)"

# ---- the M1 side: the device as the host sees it ------------------------------------------
dev=
for _ in $(seq 30); do
    for d in /sys/bus/usb/devices/*; do
        [ -f "$d/idVendor" ] && [ "$(cat "$d/idVendor")" = 1d6b ] && [ "$(cat "$d/idProduct")" = 0104 ] && dev=$d
    done
    [ -n "$dev" ] && break
    sleep 1
done
[ -n "$dev" ] || fail "no 1d6b:0104 device on the host side after 30 s"
[ "$(cat "$dev/bcdDevice")" = 0039 ] || fail "host sees bcdDevice $(cat "$dev/bcdDevice"), not 0039"
[ "$(tr -d ' ' < "$dev/bNumInterfaces")" = 2 ] || fail "host sees $(cat "$dev/bNumInterfaces") interfaces, not 2"
for n in 0 1; do
    intf=$dev:1.$n
    [ "$(cat "$intf/bInterfaceClass")" = ff ] || fail "interface $n class $(cat "$intf/bInterfaceClass") is not ff"
    [ "$(cat "$intf/bNumEndpoints")" = 02 ] || fail "interface $n has $(cat "$intf/bNumEndpoints") endpoints, not 2"
    [ "$(cat "$intf"/ep_*/type | grep -c '^Bulk$')" = 2 ] || fail "interface $n endpoints are not two bulk: $(cat "$intf"/ep_*/type | tr '\n' ' ')"
done
grep -l Interrupt "$dev"/ep_*/type "$dev":1.*/ep_*/type > /dev/null 2>&1 && fail "an interrupt endpoint exists"
say "host sees 1d6b:0104 bcdDevice 0039 \"$(cat "$dev/product")\", $(cat "$dev/configuration"): two vendor interfaces (ff), each bulk IN + bulk OUT ($(cd "$dev:1.0" && ls -d ep_* | tr '\n' ' ')/ $(cd "$dev:1.1" && ls -d ep_* | tr '\n' ' ')), no interrupt endpoint"
echo "1d6b 0104" > /sys/bus/usb-serial/drivers/generic/new_id || fail "cannot give 1d6b:0104 to the generic usb-serial driver"
tty_log= tty_ssh=
for _ in $(seq 15); do
    tty_log=$(cd "$dev:1.0" 2>/dev/null && ls -d ttyUSB* 2>/dev/null | head -1)
    tty_ssh=$(cd "$dev:1.1" 2>/dev/null && ls -d ttyUSB* 2>/dev/null | head -1)
    [ -n "$tty_log" ] && [ -n "$tty_ssh" ] && break
    sleep 1
done
[ -n "$tty_log" ] && [ -n "$tty_ssh" ] || fail "the generic usb-serial driver did not bind both interfaces (log=$tty_log ssh=$tty_ssh)"
say "host side: interface 0 -> /dev/$tty_log (log), interface 1 -> /dev/$tty_ssh (SSH pipe), driver $(basename "$(readlink "$dev:1.1/driver")")"

# ---- the log port, as attempt 21's reader sees it ------------------------------------------
( stty raw -echo 2> /dev/null; timeout 6 cat ) < "/dev/$tty_log" > /tmp/log.txt || true
grep -q 'systemd\[1\]' /tmp/log.txt || fail "no journal over /dev/$tty_log ($(wc -c < /tmp/log.txt) bytes)"
say "log port: $(wc -l < /tmp/log.txt) journal lines over /dev/$tty_log in 6 s; first: $(head -1 /tmp/log.txt | tr -d '\r' | cut -c1-70)"

if [ $FULL = 1 ]; then
# ---- the M1's proxy and the web (an HTTPS server on the M1's network) ----------------------
python3 -I "$T/https_server.py" --port 8443 --cert "$T/cert.pem" --key "$T/key.pem" --dir "$T/www" > /tmp/https.log 2>&1 &
python3 -I "$T/connect-proxy.py" --port 3128 --allow-loopback --allow-ports 8443,443,80 --log /tmp/proxy.log > /tmp/proxy.out 2>&1 &
for _ in $(seq 20); do grep -q 'https on' /tmp/https.log 2>/dev/null && grep -q 'listening on' /tmp/proxy.log 2>/dev/null && break; sleep 0.5; done
curl -sS --cacert "$T/cert.pem" https://web.test:8443/hello.txt | grep -q HELLO-FROM-THE-M1-SIDE || fail "the HTTPS test server does not answer directly: $(cat /tmp/https.log)"
say "M1 side: connect-proxy on 127.0.0.1:3128 (loopback allowed for the test), HTTPS server web.test:8443 (127.0.0.1 here; the M5 side has no DNS and its own loopback)"
fi

# Partial mode, TLS part: with no Python for the CONNECT proxy, an openssl s_server on the M1 side serves a
# file over TLS and the M5 side reaches it through a second reverse forward (3129 -> 8443): TLS, with the
# certificate checked, carried through the SSH tunnel through the byte pipe.
TLS=0
if [ $FULL = 0 ] && [ -x /usr/bin/openssl ] && [ -f "$T/key.pem" ]; then
    mkdir -p /tmp/www && head -c 1048576 /dev/urandom > /tmp/www/big.bin
    ( cd /tmp/www && exec openssl s_server -accept 127.0.0.1:8443 -WWW -quiet -cert "$T/cert.pem" -key "$T/key.pem" ) > /tmp/s_server.log 2>&1 &
    for _ in $(seq 40); do (exec 3<>/dev/tcp/127.0.0.1/8443) 2> /dev/null && { TLS=1; break; }; sleep 0.25; done
    [ $TLS = 1 ] || fail "openssl s_server did not start: $(tail -3 /tmp/s_server.log | tr '\n' ' ')"
    say "M1 side: openssl s_server on 127.0.0.1:8443 serving 1 MiB over TLS (the M5 side reaches it through the forward on its own 127.0.0.1:3129)"
fi

# ---- probe of the M5's input drain (ilinux.drainprobe=1 on the kernel command line): how long does it take?
if grep -q 'ilinux.drainprobe=1' /proc/cmdline; then
    systemctl stop "$sunit"
    for v in "timeout 5" "timeout --foreground 5" "plain"; do
        exec 5<> "/dev/ttyGS$ssh_port"
        stty raw -echo <&5
        stty min 0 time 2 <&5
        a=$(date +%s.%N)
        case "$v" in
            plain) dd of=/dev/null bs=65536 <&5 2> /tmp/dd.err ;;
            *) $v dd of=/dev/null bs=65536 <&5 2> /tmp/dd.err ;;
        esac
        rc=$?; b=$(date +%s.%N)
        ctty=$(awk '{print $7}' /proc/self/stat); sid=$(awk '{print $6}' /proc/self/stat)
        say "drain probe [$v]: dd exit $rc after $(awk -v a="$a" -v b="$b" 'BEGIN {printf "%.2f", b - a}') s; this shell: pid $$ sid $sid tty_nr $ctty"
        exec 5<&-
    done
    systemctl start "$sunit"
    sleep 1
fi

# ---- SSH over the pipe: login, environment, the forwarded proxy, an HTTPS fetch -------------
sed "s|%%TTY%%|/dev/$tty_ssh|" "$T/ssh-config" > /tmp/ssh-config
t1=$(date +%s.%N)
if [ $FULL = 1 ]; then
    cmd='echo SSH-OK "$(id -un)@$(uname -n)" "$HTTPS_PROXY" "$https_proxy" "NO_PROXY=$NO_PROXY"; curl -sS --cacert /usr/local/lib/ilinux-test/cert.pem https://web.test:8443/hello.txt; echo "direct: $(curl -sS --noproxy "*" --max-time 3 --cacert /usr/local/lib/ilinux-test/cert.pem https://web.test:8443/hello.txt 2>&1 | tr -d "\n" | cut -c1-60)"'
else   # the reverse forward's listener is on this side's own loopback: connecting to it must succeed
    cmd='echo SSH-OK "$(id -un)@$(uname -n)" "$HTTPS_PROXY" "$https_proxy" "NO_PROXY=$NO_PROXY"; if (exec 3<>/dev/tcp/127.0.0.1/3128) 2> /dev/null; then echo FORWARD-LISTENING; else echo FORWARD-MISSING; fi'
fi
FWD=
if [ $TLS = 1 ]; then
    FWD="-R 127.0.0.1:3129:127.0.0.1:8443"
    cmd="$cmd"'; curl -sS --max-time 60 --cacert /usr/local/lib/ilinux-test/cert.pem -o /tmp/m5-big.bin https://127.0.0.1:3129/big.bin && echo TLS-FETCH-DONE $(sha256sum /tmp/m5-big.bin | cut -d" " -f1)'
fi
out=$(ssh -F /tmp/ssh-config $FWD m5 "$cmd" 2> /tmp/ssh1.err) ||
    fail "ssh over the pipe failed (exit $?): $(tail -5 /tmp/ssh1.err | tr '\n' ' ')"
say "ssh 1 ($(awk -v a="$t1" -v b="$(date +%s.%N)" 'BEGIN {printf "%.1f", b - a}') s): $(echo "$out" | tr '\n' ' ')"
case "$out" in *"SSH-OK root@"*) ;; *) fail "no SSH-OK as root" ;; esac
case "$out" in *"http://127.0.0.1:3128 http://127.0.0.1:3128 NO_PROXY=localhost,127.0.0.1,::1"*) ;; *) fail "HTTPS_PROXY/https_proxy/NO_PROXY not set as in the RAM root in the session" ;; esac
if [ $FULL = 1 ]; then
    case "$out" in *HELLO-FROM-THE-M1-SIDE*) ;; *) fail "the HTTPS fetch through the forwarded proxy did not return the page" ;; esac
    case "$out" in *"direct: "*HELLO*) fail "the M5 side reached the HTTPS server directly: the forward was not the only way" ;; esac
    for _ in $(seq 20); do grep -q 'CONNECT web.test:8443 -> 127.0.0.1:8443 .* ok' /tmp/proxy.log && break; sleep 0.25; done
    grep -q 'CONNECT web.test:8443 -> 127.0.0.1:8443 .* ok' /tmp/proxy.log || fail "the proxy log shows no completed CONNECT: $(tail -3 /tmp/proxy.log)"
    say "proxy: $(grep CONNECT /tmp/proxy.log | tail -1 | cut -d' ' -f2-)"
else
    case "$out" in *FORWARD-LISTENING*) ;; *) fail "nothing listens on the M5 side's 127.0.0.1:3128: the reverse forward is missing" ;; esac
fi
if [ $TLS = 1 ]; then
    want=$(sha256sum /tmp/www/big.bin | cut -d' ' -f1)
    case "$out" in *"TLS-FETCH-DONE $want"*) ;; *) fail "the TLS fetch through the forward did not return the 1 MiB file intact (wanted $want): $(tail -3 /tmp/ssh1.err | tr '\n' ' ')" ;; esac
    say "tls forward: 1 MiB fetched over TLS through the reverse forward, certificate verified, digest equal"
fi
grep -q 'banner after' /tmp/usb-pipe.log || fail "usb-pipe saw no banner: $(tail -3 /tmp/usb-pipe.log)"
say "usb-pipe: $(grep 'banner after' /tmp/usb-pipe.log | tail -1 | cut -d' ' -f2-)"

# ---- integrity through the pipe: 2 MiB each way ---------------------------------------------
head -c 2097152 /dev/urandom > /tmp/up.bin
t1=$(date +%s.%N)
remote=$(ssh -F /tmp/ssh-config m5 'cat > /tmp/m5-up.bin; sha256sum /tmp/m5-up.bin | cut -d" " -f1' < /tmp/up.bin 2> /tmp/ssh2.err) ||
    fail "upload session failed: $(tail -3 /tmp/ssh2.err | tr '\n' ' ')"
t2=$(date +%s.%N)
[ "$remote" = "$(sha256sum /tmp/up.bin | cut -d' ' -f1)" ] || fail "2 MiB upload: digest mismatch"
ssh -F /tmp/ssh-config m5 'head -c 2097152 /dev/urandom > /tmp/m5-down.bin; cat /tmp/m5-down.bin' > /tmp/m1-down.bin 2> /tmp/ssh3.err ||
    fail "download session failed: $(tail -3 /tmp/ssh3.err | tr '\n' ' ')"
t3=$(date +%s.%N)
remote=$(ssh -F /tmp/ssh-config m5 'sha256sum /tmp/m5-down.bin | cut -d" " -f1' 2> /dev/null)
[ -n "$remote" ] && [ "$(sha256sum /tmp/m1-down.bin | cut -d' ' -f1)" = "$remote" ] || fail "2 MiB download: digest mismatch (m5 $remote)"
[ "$(stat -c %s /tmp/m1-down.bin)" = 2097152 ] || fail "download is $(stat -c %s /tmp/m1-down.bin) bytes"
say "transfer: 2 MiB up in $(awk -v a="$t1" -v b="$t2" 'BEGIN {printf "%.1f", b - a}') s and 2 MiB down in $(awk -v a="$t2" -v b="$t3" 'BEGIN {printf "%.1f", b - a}') s, digests equal (dummy_hcd, no real USB timing)"

# recover NAME: sessions are tried until one works; the pipe has no hang-up, so an sshd whose client is
# gone ends only by its own timers, and usb-pipe finds no banner until the next sshd has started.
recover() {
    local name=$1 i out
    for i in 1 2 3 4 5 6; do
        if out=$(ssh -F /tmp/ssh-config m5 'echo RECOVERED' 2> /tmp/recover.err) && [ "$out" = RECOVERED ]; then
            say "recovered from $name on try $i at $(elapsed) s"
            return 0
        fi
        say "try $i failed as expected while the old sshd lingers: $(grep -o 'no SSH banner.*' /tmp/usb-pipe.log | tail -1 | cut -c1-60)"
        sleep 5
    done
    fail "no session after $name (6 tries): $(tail -3 /tmp/recover.err | tr '\n' ' ')"
}

# ---- the wrong key is refused, and the abandoned handshake frees the port after LoginGraceTime ------
sed 's|/usr/local/lib/ilinux-test/test-key|/usr/local/lib/ilinux-test/wrong-key|' /tmp/ssh-config > /tmp/ssh-config.wrong
if ssh -F /tmp/ssh-config.wrong m5 'echo SHOULD-NOT-RUN' > /tmp/wrong.out 2> /tmp/wrong.err; then fail "login with the wrong key succeeded"; fi
grep -q SHOULD-NOT-RUN /tmp/wrong.out && fail "the wrong key ran a command"
say "wrong key refused: $(grep -i -E 'denied|refused' /tmp/wrong.err | tail -1)"
say "the client gave up after the refused key at $(elapsed) s; that sshd waits for it until LoginGraceTime (45 s)"
recover "the abandoned handshake"

# ---- a client that vanished after it authenticated: ClientAlive ends the session ------------------
timeout -s KILL 8 ssh -F /tmp/ssh-config m5 'sleep 120' > /dev/null 2>&1
say "killed a client mid-session at $(elapsed) s; the M5's sshd must end by ClientAlive (about 60 s) and restart"
recover "the vanished client"

# ---- stress: sessions back to back while this single CPU is busy (ilinux.stress=N on the kernel command line)
# ssh ends a session by writing its last packets to the ProxyCommand and then sending it SIGHUP; a tool that
# dies on that signal before it has forwarded them leaves the server waiting for a client that is gone.
stress=$(grep -o 'ilinux.stress=[0-9]*' /proc/cmdline | cut -d= -f2)
if [ -n "$stress" ] && [ "$stress" -gt 0 ]; then
    say "stress: $stress back-to-back sessions with a CPU hog on this single CPU"
    ( while :; do :; done ) &
    hog=$!
    okc=0 badc=0
    for i in $(seq "$stress"); do
        if out=$(ssh -F /tmp/ssh-config m5 "echo STRESS-$i" 2> /tmp/stress.err) && [ "$out" = "STRESS-$i" ]; then
            okc=$((okc + 1))
        else
            badc=$((badc + 1))
            say "stress session $i failed: $(grep -o 'no SSH banner.*' /tmp/usb-pipe.log | tail -1 | cut -c1-70) at $(elapsed) s"
            [ "$badc" -lt 4 ] || break
            recover "the lost tail of stress session $i"
        fi
    done
    kill "$hog" 2> /dev/null
    say "stress: $okc of $stress sessions ok, $badc failed"
    [ "$badc" = 0 ] || fail "$badc stress sessions failed"
fi

# ---- the units are healthy -------------------------------------------------------------------
others=$(systemctl --failed --no-legend --plain | awk '{print $1}' | grep -v '^ilinux-' | tr '\n' ' ')
mine=$(systemctl --failed --no-legend --plain | awk '{print $1}' | grep '^ilinux-' | tr '\n' ' ')
[ -z "$mine" ] || fail "failed ilinux units: $mine"
say "no failed ilinux units; other failed units: ${others:-none}; sshd starts: $(journalctl -b --no-pager -o cat -u "$sunit" 2>/dev/null | grep -c 'Started'); input the M5 dropped before sshd: $(journalctl -b --no-pager -o cat -u "$sunit" 2>/dev/null | grep -c 'stale bytes') times ($(journalctl -b --no-pager -o cat -u "$sunit" 2>/dev/null | sed -n 's/^dropped \([0-9]*\) stale bytes.*/\1/p' | tr '\n' ' '))"
say "usb-pipe log tail: $(tail -2 /tmp/usb-pipe.log | tr '\n' ' ')"
echo "--- the sshd unit: every session start and end (monotonic seconds since boot; the test started at about $(( $(cut -d' ' -f1 /proc/uptime | cut -d. -f1) - $(elapsed | cut -d. -f1) )) s)"
journalctl -b --no-pager -o short-monotonic -u "$sunit" 2> /dev/null | grep -E 'Accepted publickey|Failed publickey|Postponed|Received disconnect|Disconnected from|ssh_dispatch_run_fatal|Connection (closed|reset)|Timeout|Executing command|Starting session|session closed|Started SSH|Main process exited|Bad packet|Corrupted|corrupt|kex_exchange|Invalid' | sed -e 's/ilinux-m5 //' | cut -c1-175 | head -120
echo "--- the client side: debug lines of the first sessions (ssh -v)"
for f in /tmp/ssh1.err /tmp/ssh2.err /tmp/ssh3.err; do echo "== $f"; grep -E 'Connection (closed|to)|Transferred|Bytes per|Exit status|Disconnect|packet|corrupt|exit|mux|channel .* (close|eof)|Sending command' "$f" | cut -c1-150 | tail -12; done
say "PASS at $(elapsed) s"
echo "[selftest] END"

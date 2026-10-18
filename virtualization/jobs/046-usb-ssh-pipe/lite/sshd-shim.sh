#!/bin/sh
# lite test only: usb-gadget.sh runs "/usr/bin/sshd -i -e" on the raw serial port (stdin and stdout are
# the port). dropbear -i insists on a socket there, so the stand-in is a one-connection bridge: nc
# copies the port to the dropbear daemon that lite-init.sh runs on 127.0.0.1:2222. busybox nc does not
# end when the server closes (it waits for the port to reach EOF, which a tty never does), so this
# shell ends the bridge when the connection to port 2222 (0x08AE) is in CLOSE_WAIT, as sshd -i exits
# when its connection ends.
# ash gives a background job /dev/null as stdin before its own redirections run, so <&0 would copy that:
# keep the port on another descriptor first.
exec 4<&0
/usr/bin/nc 127.0.0.1 2222 <&4 &
ncpid=$!
while kill -0 "$ncpid" 2> /dev/null; do
    if grep -q ':08AE 08 ' /proc/net/tcp; then
        sleep 0.3   # let nc pass on the server's last bytes
        kill "$ncpid" 2> /dev/null
        break
    fi
    sleep 0.1
done
wait "$ncpid" 2> /dev/null
exit 0

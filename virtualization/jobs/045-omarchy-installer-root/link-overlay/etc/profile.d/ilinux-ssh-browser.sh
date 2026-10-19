# VM job 045 (LINK=1), attempt 25's finding: in an SSH login shell, programs that open a web page (Claude
# Code's sign-in, gh) print its address instead of opening a browser on the M5's own screen. Omarchy's
# shell sets BROWSER only when it is unset (default/bash/envs), so this one stays; the desktop session
# has no SSH_CONNECTION and keeps Omarchy's.
if [ -n "${SSH_CONNECTION:-}" ]; then
    export BROWSER=/usr/local/lib/ilinux/ssh-browser
fi

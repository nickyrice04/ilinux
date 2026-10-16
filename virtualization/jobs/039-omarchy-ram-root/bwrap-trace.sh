#!/bin/bash
# Test-only bubblewrap wrapper, for diagnosing a sandbox failure in the VM boot test (never in
# the delivered image): copy it to test-overlay/usr/local/bin/bwrap; guest-measure.sh then
# prints what it recorded. It records how bwrap is called, then runs the real one. Runs 23-25
# used it to find glycin's failure. Per call, /run/ilinux/bwrap/<pid>.args holds the arguments,
# <pid>.bpf the seccomp program passed with --seccomp FD, and <pid>.stderr what bwrap and the
# sandboxed program wrote to stderr (it still reaches the caller too). glycin finds bwrap by
# PATH, and /usr/local/bin comes before /usr/bin.
d=/run/ilinux/bwrap
mkdir -p "$d" 2> /dev/null
log=$d/$$
printf '%q ' "$@" > "$log.args" 2> /dev/null
echo >> "$log.args"
prev=
for a in "$@"; do
    # A memfd reopened through /proc reads from the start without moving bwrap's offset.
    [ "$prev" = --seccomp ] && cat "/proc/$$/fd/$a" > "$log.bpf" 2> /dev/null
    prev=$a
done
exec /usr/bin/bwrap "$@" 2> >(
    # tee must not hold the caller's sockets and memfds (fds above 2) open
    for f in /proc/self/fd/*; do f=${f##*/}; [ "$f" -gt 2 ] && eval "exec $f>&-"; done 2> /dev/null
    exec tee -a "$log.stderr" >&2)

#!/bin/bash
# tools/lock.sh - advisory locks for agents sharing this workspace (coordination.md).
#   lock.sh acquire NAME OWNER "PURPOSE" [TTL_MIN]  take NAME; exit 1 if someone else holds it
#   lock.sh release NAME OWNER [--force]           drop NAME (--force also clears another
#                                                  owner's stale lock; check status first)
#   lock.sh holder NAME                            print the owner, empty if free
#   lock.sh status                                 list every lock with age and staleness
# Lock names:
#   vm          the QEMU Omarchy VM: console commands, restarts, installs into it
#   quiet       a measurement window: nobody else builds, benchmarks or restarts VMs
#   qemu-build  virtualization/qemu/src builds and runtime/ installs
#   git-history history rewrites (none while anyone else is committing)
# Locks live in virtualization/run/locks (gitignored). A lock past its TTL is
# reported as stale but is never taken over silently.
set -u
D="$(cd "$(dirname "$0")/.." && pwd)/virtualization/run/locks"
mkdir -p "$D"

info() { tr '\n' ' ' < "$D/$1.lock/info" 2>/dev/null; }

case "${1:-status}" in
acquire)
  [ $# -ge 4 ] || { echo "usage: lock.sh acquire NAME OWNER PURPOSE [TTL_MIN]" >&2; exit 2; }
  name=$2 owner=$3 purpose=$4 ttl=${5:-120}
  if mkdir "$D/$name.lock" 2>/dev/null; then
    printf 'owner=%s\npurpose=%s\nsince=%s\nttl_min=%s\n' "$owner" "$purpose" "$(date +%s)" "$ttl" \
      > "$D/$name.lock/info"
    echo "acquired $name"
  elif grep -qx "owner=$owner" "$D/$name.lock/info" 2>/dev/null; then
    echo "$name already held by $owner"
  else
    echo "$name is held: $(info "$name")" >&2
    exit 1
  fi ;;
release)
  [ $# -ge 3 ] || { echo "usage: lock.sh release NAME OWNER [--force]" >&2; exit 2; }
  name=$2 owner=$3
  [ -d "$D/$name.lock" ] || { echo "$name is not held"; exit 0; }
  if grep -qx "owner=$owner" "$D/$name.lock/info" 2>/dev/null || [ "${4:-}" = --force ]; then
    rm -rf "$D/$name.lock" && echo "released $name"
  else
    echo "$name is held by someone else: $(info "$name")" >&2
    exit 1
  fi ;;
holder)
  sed -n 's/^owner=//p' "$D/${2:?NAME}.lock/info" 2>/dev/null ;;
status)
  now=$(date +%s) any=0
  for l in "$D"/*.lock; do
    [ -d "$l" ] || continue
    any=1 n=$(basename "$l" .lock)
    since=$(sed -n 's/^since=//p' "$l/info") ttl=$(sed -n 's/^ttl_min=//p' "$l/info")
    age=$(( (now - since) / 60 ))
    stale=""; [ "$age" -gt "$ttl" ] && stale=" STALE"
    echo "$n: $(sed -n 's/^owner=//p' "$l/info") for ${age} min (ttl ${ttl})${stale} - $(sed -n 's/^purpose=//p' "$l/info")"
  done
  [ $any = 1 ] || echo "no locks held" ;;
*)
  echo "usage: lock.sh acquire|release|holder|status ..." >&2; exit 2 ;;
esac

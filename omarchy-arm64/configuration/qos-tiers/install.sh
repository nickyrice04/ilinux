#!/bin/bash
# Install omarchy-qos into a root filesystem (default /).  Intended for the
# disposable test VM or a future native install - never run on the macOS host.
set -euo pipefail
[ "$(uname -s)" = Linux ] || { echo "Linux only" >&2; exit 1; }
here="$(cd "$(dirname "$0")" && pwd)"
root="${1:-/}"
install -Dm755 "$here/bin/omarchy-qos" "$root/usr/bin/omarchy-qos"
install -Dm644 "$here/omarchy-qos.conf" "$root/etc/omarchy-qos.conf"
install -Dm644 "$here/systemd/user/utility.slice" "$root/usr/lib/systemd/user/utility.slice"
install -Dm644 "$here/systemd/user/omarchy-qos.service" "$root/usr/lib/systemd/user/omarchy-qos.service"
install -Dm644 "$here/systemd/system/user@.service.d/omarchy-qos-delegate.conf" \
  "$root/usr/lib/systemd/system/user@.service.d/omarchy-qos-delegate.conf"
install -Dm644 "$here/systemd/system/omarchy-qos-system.service" \
  "$root/usr/lib/systemd/system/omarchy-qos-system.service"
echo "installed into $root; enable with: systemctl --global enable omarchy-qos.service && systemctl enable omarchy-qos-system.service"

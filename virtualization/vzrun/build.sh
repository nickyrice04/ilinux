#!/bin/bash
# Build vzrun into virtualization/bin/ and ad-hoc sign it with the
# com.apple.security.virtualization entitlement.  Nothing is installed.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$here/../bin"
mkdir -p "$out"
swiftc -O -module-cache-path "${TMPDIR:-/tmp}/vzrun-module-cache" "$here/main.swift" -o "$out/vzrun"
codesign --force --sign - --entitlements "$here/vzrun.entitlements" "$out/vzrun"
codesign -d --entitlements - "$out/vzrun" 2>/dev/null | grep -q virtualization && echo "built $out/vzrun (entitlement ok)"

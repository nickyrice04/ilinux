#!/bin/bash
# Build virtualization/app/Omarchy.app: a double-clickable launcher for the
# GPU-accelerated Omarchy VM.  It lives in the workspace (nothing is copied to
# /Applications; drag it to the Dock if you like).
#
# Why a bundle: macOS shows "Omarchy" in the Dock and menu bar, and attributes
# privacy prompts (microphone, Accessibility for --full-grab) to Omarchy
# instead of whatever app happened to start QEMU.  QEMU runs from inside the
# bundle (Contents/MacOS/qemu-system-aarch64, ad-hoc signed with the
# hypervisor entitlement); its libraries and data stay in
# virtualization/qemu/runtime.
#
# Launch options come from virtualization/run/omarchy-app.conf, a bash file
# with OPTIONS=(...) (default: --hetero --fullscreen --console-socket; the
# socket console also keeps the guest getty off a closed stdin) plus optional
# APP_NAP / DISK_CACHE / MEM_MIB / CPUS overrides.
#
#   virtualization/app/build-omarchy-app.sh      # rerun after rebuilding QEMU
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP="$ROOT/virtualization/app/Omarchy.app"
QEMU_SRC="$ROOT/virtualization/qemu/runtime/bin/qemu-system-aarch64"
ENT="$ROOT/virtualization/qemu/qemu.entitlements"
[[ -x $QEMU_SRC ]] || { echo "build QEMU first (virtualization/qemu/build-qemu-virgl.sh)" >&2; exit 1; }

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Omarchy</string>
  <key>CFBundleDisplayName</key><string>Omarchy</string>
  <key>CFBundleIdentifier</key><string>org.ilinux.omarchy-vm</string>
  <key>CFBundleExecutable</key><string>Omarchy</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.1</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>15.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSMicrophoneUsageDescription</key>
  <string>Linux apps in the Omarchy VM can record audio through the Mac's microphone.</string>
</dict></plist>
PLIST

# launch.sh: reads the options and execs the workspace launcher with the
# bundled QEMU.  exec keeps the process (and the bundle's identity) all the
# way into QEMU.
{
  printf '#!/bin/bash\n'
  printf 'ROOT=%q\n' "$ROOT"
  cat <<'LAUNCH'
OPTIONS=(--hetero --fullscreen --console-socket)
CONF="$ROOT/virtualization/run/omarchy-app.conf"
[[ -f $CONF ]] && source "$CONF"
mkdir -p "$ROOT/virtualization/run"
export QEMU="$(cd "$(dirname "$0")/../MacOS" && pwd)/qemu-system-aarch64"
exec "$ROOT/virtualization/qemu/run-omarchy-gpu.sh" "${OPTIONS[@]}" \
  >> "$ROOT/virtualization/run/omarchy-app.log" 2>&1
LAUNCH
} > "$APP/Contents/Resources/launch.sh"
chmod +x "$APP/Contents/Resources/launch.sh"

# Main executable: a tiny Mach-O stub that execs launch.sh (LaunchServices
# did not start a shell script as CFBundleExecutable).
STUB_SRC="$(mktemp -d)/omarchy-stub.c"
cat > "$STUB_SRC" <<'STUB'
#include <libgen.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void)
{
    char exe[PATH_MAX], real[PATH_MAX], script[PATH_MAX];
    uint32_t n = sizeof exe;

    if (_NSGetExecutablePath(exe, &n) || !realpath(exe, real)) {
        return 1;
    }
    snprintf(script, sizeof script, "%s/../Resources/launch.sh", dirname(real));
    execl("/bin/bash", "bash", script, (char *)NULL);
    perror("execl");
    return 1;
}
STUB
clang -O2 -o "$APP/Contents/MacOS/Omarchy" "$STUB_SRC"
rm -rf "$(dirname "$STUB_SRC")"

cp "$QEMU_SRC" "$APP/Contents/MacOS/qemu-system-aarch64"
xattr -c "$APP/Contents/MacOS/qemu-system-aarch64"
codesign --force --sign - --entitlements "$ENT" "$APP/Contents/MacOS/qemu-system-aarch64"
codesign --force --sign - "$APP"
codesign --verify --deep "$APP" && echo "built $APP"

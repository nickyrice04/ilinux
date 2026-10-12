#!/bin/bash
# Build a GPU-accelerated QEMU (HVF + Cocoa + VirGL on native macOS OpenGL)
# entirely inside the workspace: no app install, no Homebrew changes.
#
# Recipe and patches follow omacom/try-omarchy (MIT; third_party/try-omarchy,
# macos/build-qemu-gpu-runtime.sh @ 3c6056d) with these differences:
#   * libepoxy is built from upstream source (no third-party prebuilt bottle)
#   * no ANGLE and no runtime EGL: virglrenderer is built with -Dplatforms=[]
#     (no EGL/GLX code paths), QEMU uses native CGL for gl=on (try-omarchy's
#     current default).  libepoxy still carries EGL *headers/dispatch* because
#     QEMU's virtio-gpu-virgl.c includes ui/egl-helpers.h unconditionally, and
#     is patched so a missing libEGL means "no EGL context" instead of abort()
#     (epoxy probes EGL on every GL entry-point lookup once EGL is compiled in).
#   * workspace QEMU patches (virtualization/qemu/patches/) on top of the
#     try-omarchy series: stable Retina window size, product name from -name
#   * audio uses QEMU's native CoreAudio backend instead of SDL
#   * uses Homebrew's already-installed glib/pixman/pcre2/gettext for linking
# Every source archive is SHA-256 pinned (hashes from try-omarchy where they
# pin the same artifact; libepoxy against GNOME's published sha256sum).
#
#   virtualization/qemu/build-qemu-virgl.sh  ->  virtualization/qemu/runtime/
#   ONLY=qemu virtualization/qemu/build-qemu-virgl.sh   # rebuild QEMU only
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
Q="$ROOT/virtualization/qemu"
DL="$Q/downloads"; SRC="$Q/src"; RT="$Q/runtime"
TO="$ROOT/third_party/try-omarchy/macos/patches"
VENV="$ROOT/tools/venv/bin"
JOBS="${JOBS:-16}"
mkdir -p "$DL" "$SRC" "$RT"
export PATH="$VENV:$PATH"                     # meson, ninja, pkg-config, python3
export MACOSX_DEPLOYMENT_TARGET=15.0
HB=/opt/homebrew/opt
export PKG_CONFIG_PATH=
export PKG_CONFIG_LIBDIR="$RT/lib/pkgconfig:$HB/glib/lib/pkgconfig:$HB/pixman/lib/pkgconfig:$HB/pcre2/lib/pkgconfig:$HB/gettext/lib/pkgconfig:$HB/libffi/lib/pkgconfig:$HB/zstd/lib/pkgconfig"

log() { echo "[build-qemu-virgl] $*"; }
fetch() {  # url sha256 outname
  local out="$DL/$3"
  if [[ ! -f $out ]]; then
    log "download $3"
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 --retry 3 -o "$out.part" "$1"
    mv "$out.part" "$out"
  fi
  local got; got=$(shasum -a 256 "$out" | awk '{print $1}')
  if [[ $2 == TOFU ]]; then
    log "TOFU sha256 $3 = $got"; echo "$got  $3" >> "$Q/tofu-hashes.txt"
  elif [[ $got != "$2" ]]; then
    echo "SHA-256 mismatch for $3: $got != $2" >&2; exit 1
  fi
}
unpack() {  # archive dest
  rm -rf "$2"; mkdir -p "$2"
  tar -xf "$DL/$1" -C "$2" --strip-components=1
}

QEMU_COMMIT=c3d48b7d1e89604920e5b81b91140c2ad39a1943
fetch "https://gitlab.com/qemu-project/qemu/-/archive/$QEMU_COMMIT/qemu-$QEMU_COMMIT.tar.gz" \
  7563781d7dec46f11509801e027f852597235d29ca7afa44a07ed9d8b108b8cd qemu.tar.gz
fetch "https://gitlab.freedesktop.org/slirp/libslirp/-/archive/v4.9.4/libslirp-v4.9.4.tar.gz" \
  3998863b020aeda34bddc567097c6efba55a78cdf6eeee6bcd42c11ef23967da libslirp.tar.gz
fetch "https://gitlab.freedesktop.org/virgl/virglrenderer/-/archive/1.3.0/virglrenderer-1.3.0.tar.gz" \
  065bc56e89e6f631f96101cd62eba0748e48eb888b434edc86e89d05395e76f3 virglrenderer.tar.gz
fetch "https://codeload.github.com/startergo/homebrew-virglrenderer/tar.gz/refs/tags/v1.0.42" \
  950273fbba46905b6112ee2bd0598c1da706c25319a7347058cbc52f04ba96dd virgl-tap.tar.gz
fetch "https://gitlab.com/qemu-project/keycodemapdb/-/archive/f5772a62ec52591ff6870b7e8ef32482371f22c6/keycodemapdb-f5772a62ec52591ff6870b7e8ef32482371f22c6.tar.gz" \
  d014b53382dbb17b8196ad12f50de7f20d0ef1b9f7d54b0be51a6cbb14209195 keycodemapdb.tar.gz
fetch "https://git.kernel.org/pub/scm/utils/dtc/dtc.git/snapshot/dtc-b6910bec11614980a21e46fbccc35934b671bd81.tar.gz" \
  e115f987eec23a1ba25150a46ced1675de3716072d3b4905afb3a9cda0f007c7 dtc.tar.gz
# Official hash published by GNOME (download.gnome.org/.../libepoxy-1.5.10.sha256sum)
fetch "https://download.gnome.org/sources/libepoxy/1.5/libepoxy-1.5.10.tar.xz" \
  072cda4b59dd098bba8c2363a6247299db1fa89411dc221c8b81b8ee8192e623 libepoxy.tar.xz

# Khronos EGL headers (macOS ships none).  Pinned by commit; headers only.
EGL_COMMIT=db3425b8246136faccb5e2782b5694960bd6edf1
mkdir -p "$RT/include/EGL" "$RT/include/KHR"
for h in EGL/egl.h EGL/eglext.h EGL/eglplatform.h KHR/khrplatform.h; do
  [[ -f $RT/include/$h ]] || curl -fsSL --proto '=https' \
    "https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/$EGL_COMMIT/api/$h" -o "$RT/include/$h"
done

if [[ ${ONLY:-all} != qemu ]]; then
# ---- libepoxy (upstream; CGL is its native macOS path) ----
unpack libepoxy.tar.xz "$SRC/libepoxy"
# Local patch: let epoxy build its EGL dispatch on macOS (upstream hard-codes it
# off for __APPLE__ and names no EGL library) - QEMU's virgl code needs the EGL
# API compiled in - while keeping EGL optional at runtime (see below).
python3 - "$SRC/libepoxy/src" <<'PY'
import sys, pathlib
d = pathlib.Path(sys.argv[1])
h = d / "dispatch_common.h"; t = h.read_text()
t = t.replace("#elif defined(__APPLE__)\n#define PLATFORM_HAS_EGL 0", "#elif defined(__APPLE__)\n#define PLATFORM_HAS_EGL ENABLE_EGL", 1)
h.write_text(t)
c = d / "dispatch_common.c"; t = c.read_text()
t = t.replace('#define OPENGL_LIB "/System/Library/Frameworks/OpenGL.framework/Versions/Current/OpenGL"',
              '#define OPENGL_LIB "/System/Library/Frameworks/OpenGL.framework/Versions/Current/OpenGL"\n#define EGL_LIB "libEGL.dylib"', 1)
# ...and make EGL optional at runtime: every GL lookup first asks EGL whether
# its context is current, which aborts when libEGL can't be loaded (macOS has
# none without ANGLE).  Report "no EGL context" instead and fall through to CGL.
old = "    EGLint curapi;\n\n    if (eglQueryContext(eglGetCurrentDisplay(), eglGetCurrentContext(),"
new = ("    EGLint curapi;\n\n#ifdef __APPLE__\n    if (!epoxy_load_egl(false, true))\n"
       "        return EGL_NONE;\n#endif\n\n    if (eglQueryContext(eglGetCurrentDisplay(), eglGetCurrentContext(),")
assert old in t, "epoxy EGL api site not found"
t = t.replace(old, new, 1)
c.write_text(t)
PY
log "build libepoxy"
CFLAGS="-I$RT/include" meson setup "$SRC/libepoxy/build" "$SRC/libepoxy" --prefix="$RT" --libdir=lib --buildtype=release \
  -Degl=yes -Dglx=no -Dx11=false -Dtests=false > "$Q/build-epoxy.log" 2>&1
ninja -C "$SRC/libepoxy/build" -j "$JOBS" install >> "$Q/build-epoxy.log" 2>&1

# ---- libslirp + try-omarchy Darwin NAT fixes ----
unpack libslirp.tar.gz "$SRC/libslirp"
patch -d "$SRC/libslirp" -p1 -f -s -i "$TO/libslirp-darwin-icmp-matching.patch"
patch -d "$SRC/libslirp" -p1 -f -s -i "$TO/libslirp-ipv4-udp-translation.patch"
log "build libslirp"
meson setup "$SRC/libslirp/build" "$SRC/libslirp" --prefix="$RT" --libdir=lib --buildtype=release \
  --wrap-mode=nodownload > "$Q/build-slirp.log" 2>&1
ninja -C "$SRC/libslirp/build" -j "$JOBS" install >> "$Q/build-slirp.log" 2>&1

# ---- virglrenderer 1.3.0 + macOS patch set + native-OpenGL patch ----
unpack virglrenderer.tar.gz "$SRC/virglrenderer"
unpack virgl-tap.tar.gz "$SRC/virgl-tap"
for p in debug-init-logging default-debug-log macos-unified venus-metal-func-ptrs gallium-endian \
         macos-a8-swizzle corefoundation-link a8-shader-swizzle a8-shader-swizzle-texture \
         a8-unpack-alignment bgra-upload-swizzle-core msaa-assertion-fix ignore-surface0-clear \
         venus-errno-debug macos-profile-forcing macos-egl-profile texture-swizzle-core bgra-unified \
         core-profile-frag-datalocation macos-core-profile-fixes gles-dual-source-output; do
  patch -d "$SRC/virglrenderer" -p1 -f -s -i "$SRC/virgl-tap/patches/virglrenderer-$p.patch"
done
patch -d "$SRC/virglrenderer" -p1 -f -s -i "$TO/virgl-native-opengl.patch"
# Local fix: the macOS patch set guards EGL-image teardown with ENABLE_METAL
# only; without EGL (our build) virgl_egl_image_destroy/egl don't exist.
python3 - "$SRC/virglrenderer/src/vrend/vrend_renderer.c" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
old = "#if defined(ENABLE_GBM) || defined(ENABLE_METAL)\n   if (res->egl_image) {"
new = "#if defined(HAVE_EPOXY_EGL_H) && (defined(ENABLE_GBM) || defined(ENABLE_METAL))\n   if (res->egl_image) {"
assert old in s, "virgl EGL guard site not found"
open(p, "w").write(s.replace(old, new, 1))
PY
log "build virglrenderer"
CFLAGS="-I$RT/include" meson setup "$SRC/virglrenderer/build" "$SRC/virglrenderer" --prefix="$RT" \
  --libdir=lib --buildtype=debugoptimized -Db_ndebug=false --wrap-mode=nodownload \
  -Ddrm-renderers=[] -Dvenus=false -Dtests=false -Dvideo=false -Dtracing=none -Dplatforms=[] > "$Q/build-virgl.log" 2>&1
ninja -C "$SRC/virglrenderer/build" -j "$JOBS" install >> "$Q/build-virgl.log" 2>&1

fi  # ONLY != qemu

# ---- QEMU (pinned commit) + try-omarchy patch series, same order ----
unpack qemu.tar.gz "$SRC/qemu"
mkdir -p "$SRC/qemu/subprojects/keycodemapdb" "$SRC/qemu/subprojects/dtc"
tar -xzf "$DL/keycodemapdb.tar.gz" -C "$SRC/qemu/subprojects/keycodemapdb" --strip-components=1
tar -xzf "$DL/dtc.tar.gz" -C "$SRC/qemu/subprojects/dtc" --strip-components=1
for p in qemu-texture-borrowing-11.1 qemu-gpu-spike-resolution-fix qemu-cocoa-product-identity \
         qemu-cocoa-dynamic-display qemu-cocoa-immersive-mode qemu-cocoa-full-grab-focus \
         qemu-cocoa-full-grab-reenable qemu-cocoa-pause-ownership qemu-sdl-audio-device-selection \
         qemu-hda-full-ring-recovery qemu-9p-guest-owner qemu-darwin-strchrnul-compat \
         qemu-hvf-free-page-reclaim qemu-hvf-mapped-sections qemu-darwin-gpu-fence-poll \
         qemu-cocoa-pinch-zoom qemu-cocoa-precise-scroll qemu-cocoa-iso-section-grave-swap \
         qemu-cocoa-injected-text qemu-usb-host-exact-bus; do
  patch -d "$SRC/qemu" -p1 -f -s -i "$TO/$p.patch"
done
# Local fix: without CONFIG_EGL, ui/cocoa.m loses the GL declarations it got
# via ui/egl-context.h; include epoxy's GL header directly for CONFIG_OPENGL.
python3 - "$SRC/qemu/ui/cocoa.m" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
old = '#ifdef CONFIG_EGL\n#include "ui/egl-context.h"\n#endif'
new = old + '\n#ifdef CONFIG_OPENGL\n#include <epoxy/gl.h>\n#endif'
assert old in s, "cocoa.m include site not found"
s = s.replace(old, new, 1)
# try-omarchy's GL trace log references egl_surface unconditionally.
t_old = "                         egl_surface != NULL);"
t_new = ("#ifdef CONFIG_EGL\n                         egl_surface != NULL);\n#else\n"
         "                         0);\n#endif")
assert t_old in s, "cocoa.m trace site not found"
open(p, "w").write(s.replace(t_old, t_new, 1))
PY
for p in "$Q"/patches/qemu-*.patch; do
  patch -d "$SRC/qemu" -p1 -f -s -i "$p"
done
log "configure QEMU"
rm -rf "$SRC/qemu/build"; mkdir -p "$SRC/qemu/build"
( cd "$SRC/qemu/build" &&
  ../configure --prefix="$RT" --python="$VENV/python3" --ninja="$VENV/ninja" \
    --target-list=aarch64-softmmu --without-default-features --enable-system \
    --enable-hvf --disable-tcg --enable-cocoa --enable-opengl --enable-virglrenderer \
    --enable-pixman --enable-slirp --enable-fdt=internal --enable-coreaudio --audio-drv-list=coreaudio \
    --enable-virtfs --enable-download --disable-debug-info --disable-werror \
    --extra-cflags="-mmacosx-version-min=15.0 -I$RT/include" \
    --extra-ldflags="-mmacosx-version-min=15.0 -L$RT/lib -Wl,-rpath,$RT/lib" ) > "$Q/build-qemu.log" 2>&1
log "build QEMU"
ninja -C "$SRC/qemu/build" -j "$JOBS" >> "$Q/build-qemu.log" 2>&1
ninja -C "$SRC/qemu/build" install >> "$Q/build-qemu.log" 2>&1

# HVF requires the hypervisor entitlement; ad-hoc sign the binary.
cat > "$Q/qemu.entitlements" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>com.apple.security.hypervisor</key><true/></dict></plist>
EOF
xattr -c "$RT/bin/qemu-system-aarch64"   # codesign rejects Finder/provenance xattrs
codesign --force --sign - --entitlements "$Q/qemu.entitlements" "$RT/bin/qemu-system-aarch64"
"$RT/bin/qemu-system-aarch64" --version | head -1
log "done: $RT/bin/qemu-system-aarch64"

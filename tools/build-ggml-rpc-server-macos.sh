#!/bin/bash
# Build llama.cpp's ggml RPC server with the Metal backend on macOS using only
# Xcode's clang (no cmake).  Mirrors upstream CMake rules for the pinned commit
# (third_party/llama.cpp @ 61881b1f7): ggml-base + ggml (static backend
# registry) + ggml-cpu (ARM) + ggml-metal (shader source embedded) + ggml-rpc.
#
# Purpose: let Linux guests use this Mac's GPU (incl. the M5 matrix units via
# ggml-metal's Metal-4 tensor path) by offloading ggml graphs over the vzrun
# vsock bridge.  The server must only bind 127.0.0.1 (the RPC protocol is
# unauthenticated); vzrun --vsock-forward connects guests to it.
#
#   tools/build-ggml-rpc-server-macos.sh   ->  tools/bin/ggml-rpc-server
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
L="$ROOT/third_party/llama.cpp"
B="${TMPDIR:-/tmp}/ggml-rpc-build"
OUT="$ROOT/tools/bin"
mkdir -p "$B" "$OUT"
G="$L/ggml"

# Embedded Metal library (same transformation as ggml-metal/CMakeLists.txt).
sed -e "/__embed_ggml-common.h__/r $G/src/ggml-common.h" -e "/__embed_ggml-common.h__/d" \
    < "$G/src/ggml-metal/ggml-metal.metal" > "$B/embed.metal.tmp"
sed -e "/#include \"ggml-metal-impl.h\"/r $G/src/ggml-metal/ggml-metal-impl.h" \
    -e "/#include \"ggml-metal-impl.h\"/d" < "$B/embed.metal.tmp" > "$B/ggml-metal-embed.metal"
cat > "$B/ggml-metal-embed.s" <<EOF
.section __DATA,__ggml_metallib
.globl _ggml_metallib_start
_ggml_metallib_start:
.incbin "$B/ggml-metal-embed.metal"
.globl _ggml_metallib_end
_ggml_metallib_end:
EOF

DEFS=(-DNDEBUG -D_DARWIN_C_SOURCE -DGGML_SCHED_MAX_COPIES=4 -DGGML_USE_CPU -DGGML_USE_METAL
      -DGGML_USE_RPC -DGGML_METAL_EMBED_LIBRARY -DGGML_USE_LLAMAFILE
      -DGGML_VERSION=\"0.0.0-61881b1\" -DGGML_COMMIT=\"61881b1\")
INC=(-I"$G/include" -I"$G/src" -I"$G/src/ggml-cpu" -I"$G/src/ggml-metal" -I"$G/src/ggml-rpc")
OPT=(-O3 -mcpu=apple-m4 -fno-common)
SRCS=(
  src/ggml.c src/ggml.cpp src/ggml-alloc.c src/ggml-backend.cpp src/ggml-backend-meta.cpp
  src/ggml-opt.cpp src/ggml-threading.cpp src/ggml-quants.c src/gguf.cpp
  src/ggml-backend-reg.cpp src/ggml-backend-dl.cpp
  src/ggml-cpu/ggml-cpu.c src/ggml-cpu/ggml-cpu.cpp src/ggml-cpu/repack.cpp src/ggml-cpu/hbm.cpp
  src/ggml-cpu/quants.c src/ggml-cpu/traits.cpp src/ggml-cpu/binary-ops.cpp src/ggml-cpu/unary-ops.cpp
  src/ggml-cpu/vec.cpp src/ggml-cpu/ops.cpp src/ggml-cpu/llamafile/sgemm.cpp
  src/ggml-cpu/arch/arm/quants.c src/ggml-cpu/arch/arm/repack.cpp
  src/ggml-metal/ggml-metal.cpp src/ggml-metal/ggml-metal-device.m src/ggml-metal/ggml-metal-device.cpp
  src/ggml-metal/ggml-metal-common.cpp src/ggml-metal/ggml-metal-context.m src/ggml-metal/ggml-metal-ops.cpp
  src/ggml-rpc/ggml-rpc.cpp src/ggml-rpc/transport.cpp
)
objs=()
pids=()
for s in "${SRCS[@]}"; do
  o="$B/$(echo "$s" | tr '/' '_').o"
  objs+=("$o")
  case "$s" in
    *.c) cc=(clang -std=c11) ;;
    *.m) cc=(clang -x objective-c -fno-objc-arc) ;;
    *)   cc=(clang++ -std=c++17) ;;
  esac
  "${cc[@]}" "${OPT[@]}" "${DEFS[@]}" "${INC[@]}" -c "$G/$s" -o "$o" &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
clang -c "$B/ggml-metal-embed.s" -o "$B/ggml-metal-embed.o"
clang++ -std=c++17 "${OPT[@]}" "${DEFS[@]}" "${INC[@]}" -c "$L/tools/rpc/rpc-server.cpp" -o "$B/rpc-server.o"
clang++ -o "$OUT/ggml-rpc-server" "$B/rpc-server.o" "${objs[@]}" "$B/ggml-metal-embed.o" \
  -framework Foundation -framework Metal -framework MetalKit -framework Accelerate
echo "built $OUT/ggml-rpc-server"

#!/bin/sh
# Invoke a Python client script with this checkout's LLVM tools.
set -eu
client_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_root=$(CDPATH= cd -- "$client_dir/../.." && pwd)
export TOOLCHAIN="$project_root/third_party/LLVM-23.1.3-macOS-ARM64/bin/"
export LLDDIR="$TOOLCHAIN"
export ARCH=aarch64-linux-gnu-
export USE_CLANG=1
mkdir -p "$project_root/build/m1n1-client-tmp"
export TMPDIR="$project_root/build/m1n1-client-tmp"
exec "$client_dir/.venv/bin/python" -I "$@"

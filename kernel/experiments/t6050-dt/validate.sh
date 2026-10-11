#!/bin/bash
# Compile-check the draft t6050 device tree: C-preprocess with the Linux
# dt-bindings headers, then build a DTB with dtc and report its warnings.
# Compile success says nothing about bootability.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$here/../../.."
dtc="$root/third_party/dtc/dtc"
inc="$root/third_party/dt-include"
out="$here/out"
[ -x "$dtc" ] || { echo "build dtc first: make -C third_party/dtc dtc NO_PYTHON=1 NO_YAML=1" >&2; exit 1; }
for dts in "$out"/t6050-*.dts; do
  pre="$out/$(basename "$dts" .dts).pre.dts"
  clang -E -P -nostdinc -undef -D__DTS__ -x assembler-with-cpp -I "$inc" -I "$out" "$dts" -o "$pre"
  "$dtc" -I dts -O dtb -o "$out/$(basename "$dts" .dts).dtb" "$pre"
  echo "OK $(basename "$dts") -> $(basename "$dts" .dts).dtb ($(wc -c < "$out/$(basename "$dts" .dts).dtb") bytes)"
done

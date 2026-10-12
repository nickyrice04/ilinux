#!/bin/bash
# Compile-check the draft t6050 device tree: C-preprocess with the Linux
# dt-bindings headers, then build a DTB with dtc and report its warnings.
# Compile success says nothing about bootability.
# Fails on any dtc error *or warning*.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$here/../../.."
dtc="$root/third_party/dtc/dtc"
inc="$root/third_party/dt-include"
out="$here/out"
[ -x "$dtc" ] || { echo "build dtc first: make -C third_party/dtc dtc NO_PYTHON=1 NO_YAML=1" >&2; exit 1; }
rm -f "$out"/*.pre.dts "$out"/*.pre.dtb
for dts in "$out"/t6050-*.dts; do
  base="$(basename "$dts" .dts)"
  pre="$out/$base.pre.dts"
  clang -E -P -nostdinc -undef -D__DTS__ -x assembler-with-cpp -I "$inc" -I "$out" "$dts" -o "$pre"
  warn="$("$dtc" -I dts -O dtb -o "$out/$base.dtb" "$pre" 2>&1)" || { echo "$warn" >&2; exit 1; }
  if [ -n "$warn" ]; then echo "$warn" >&2; echo "FAIL $base: dtc warnings" >&2; exit 1; fi
  echo "OK $(basename "$dts") -> $base.dtb ($(wc -c < "$out/$base.dtb") bytes, 0 dtc warnings)"
done

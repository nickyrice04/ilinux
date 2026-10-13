#!/bin/bash
# Probe-readiness audit: for each distinct compatible LIST in our t6050 DT,
# does any driver's of_device_id in the built kernel source contain one of its
# strings? A match => the device can probe on that string (t6050-specific or
# its generic fallback). Run in the guest; full tree at /var/tmp/t6050-build.
set -u
K=/var/tmp/t6050-build/linux
DT="$1"
printf '%-42s | %-26s | %s\n' "node compatible (t6050-specific first)" "driver matches on" "driver file"
echo "-------------------------------------------+----------------------------+-------------------------"
# each node's full compatible list, one per line
grep -hoE 'compatible = "[^;]+";' "$DT" | sort -u | while IFS= read -r line; do
  # extract the quoted strings in order
  mapfile -t strs < <(echo "$line" | grep -oE '"[^"]+"' | tr -d '"')
  first="${strs[0]}"
  matched=""; file=""
  for s in "${strs[@]}"; do
    f=$(grep -rlE "\"$s\"" "$K/drivers" "$K/arch/arm64" --include=*.c 2>/dev/null | head -1)
    if [ -n "$f" ]; then matched="$s"; file="${f#$K/}"; break; fi
  done
  if [ -n "$matched" ]; then
    [ "$matched" = "$first" ] && tag="$matched" || tag="$matched (fallback)"
    printf '%-42s | %-26s | %s\n' "$first" "$tag" "$file"
  else
    printf '%-42s | %-26s | %s\n' "$first" "NO MATCH" "core-enumerated or GAP"
  fi
done

#!/bin/bash
# Only executed inside the existing disposable Linux development VM.
set -euo pipefail
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
I=/mnt/ilinux
O=/mnt/job/out
exec > "$O/build.log" 2>&1
W=/var/tmp/ilinux-desktop31
mkdir -p "$W"
if [ ! -d "$W/source" ]; then
  cp -a "$I/build/attempt30/upstream/Hyprland-efb50993780079460b0cbed1363e2166a2de1d9f" "$W/source"
fi
for f in src/render/OpenGL.cpp src/config/values/ConfigValues.cpp; do
  cp "$I/build/attempt30/upstream/Hyprland-efb50993780079460b0cbed1363e2166a2de1d9f/$f" "$W/source/$f"
done
python3 -I "$I/kernel/experiments/desktop31/apply.py" "$W/source"
cp "$I/kernel/experiments/desktop31/ILinuxCopy31.hpp" "$W/source/src/render/"
for dep in udis86 hyprland-protocols; do
  tar -xzf "$I/build/attempt31/upstream/$dep.tar.gz" --strip-components=1 -C "$W/source/subprojects/$dep"
done
pacman -S --needed --noconfirm hyprwayland-scanner
cat /usr/include/hyprutils/math/Mat3x3.hpp > "$O/Mat3x3.hpp"
pacman -Q > "$O/packages-private.txt"
GIT_COMMIT_HASH=efb50993780079460b0cbed1363e2166a2de1d9f GIT_DIRTY=ilinux-copy31 \
  cmake -S "$W/source" -B "$W/build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DNO_HYPRPM=ON
cmake --build "$W/build" --target Hyprland -j8
cp "$W/build/Hyprland" "$O/Hyprland-copy31"
strip "$O/Hyprland-copy31"
sha256sum "$O/Hyprland-copy31"

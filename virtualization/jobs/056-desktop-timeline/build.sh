#!/bin/bash
# Separate build: the held copy31 source/cache is never modified.
set -euo pipefail
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
I=/mnt/ilinux O=/mnt/job/out W=/run/ilinux-timeline31-build
exec > "$O/build.log" 2>&1
# The first disk build ran out of space. Discard only our generated tree;
# rebuild in guest RAM so no cached dependency or other agent's build is lost.
rm -rf /var/tmp/ilinux-timeline31
mkdir -p "$W"
mount -t tmpfs -o size=8G tmpfs "$W"
trap 'umount "$W"' EXIT
# Remove only this job's incomplete/generated archive; thin archives avoid a
# second copy of every object on the existing bounded development disk.
rm -f "$W/build/libhyprland_lib.a"
df -h /var/tmp
if [ ! -d "$W/source" ]; then
  cp -a "$I/build/attempt30/upstream/Hyprland-efb50993780079460b0cbed1363e2166a2de1d9f" "$W/source"
fi
python3 -I - "$I" "$W" <<'PY'
import json,pathlib,shutil,sys
i,w=map(pathlib.Path,sys.argv[1:])
for f in json.loads((i/'kernel/experiments/latency31/source-pins.json').read_text()):
    shutil.copyfile(i/'build/attempt30/upstream/Hyprland-efb50993780079460b0cbed1363e2166a2de1d9f'/f,w/'source'/f)
PY
python3 -I "$I/kernel/experiments/latency31/apply.py" "$W/source"
for dep in udis86 hyprland-protocols; do
  tar -xzf "$I/build/attempt31/upstream/$dep.tar.gz" --strip-components=1 -C "$W/source/subprojects/$dep"
done
GIT_COMMIT_HASH=efb50993780079460b0cbed1363e2166a2de1d9f GIT_DIRTY=ilinux-timeline31 \
  cmake -S "$W/source" -B "$W/build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DNO_HYPRPM=ON \
  -DFETCHCONTENT_SOURCE_DIR_GLAZE=/var/tmp/ilinux-desktop31/build/_deps/glaze-src \
  '-DCMAKE_CXX_ARCHIVE_CREATE=<CMAKE_AR> qcT <TARGET> <LINK_FLAGS> <OBJECTS>'
cmake --build "$W/build" --target Hyprland -j8
# Refresh the seven instrumentation sites once after compilation, so review
# edits delivered during this long build are included in the saved artifact.
python3 -I - "$I" "$W" <<'PY'
import json,pathlib,shutil,sys
i,w=map(pathlib.Path,sys.argv[1:])
for f in json.loads((i/'kernel/experiments/latency31/source-pins.json').read_text()):
    shutil.copyfile(i/'build/attempt30/upstream/Hyprland-efb50993780079460b0cbed1363e2166a2de1d9f'/f,w/'source'/f)
PY
python3 -I "$I/kernel/experiments/latency31/apply.py" "$W/source"
cmake --build "$W/build" --target Hyprland -j8
cp "$W/build/Hyprland" "$O/Hyprland-timeline31"
strip "$O/Hyprland-timeline31"
sha256sum "$O/Hyprland-timeline31"
cc --version | head -1
echo TIMELINE-BUILD-PASS

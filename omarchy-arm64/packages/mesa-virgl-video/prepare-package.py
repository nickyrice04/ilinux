#!/usr/bin/env python3
"""Stage a self-contained, checksummed makepkg directory; run makepkg in Linux."""
import argparse
import hashlib
from pathlib import Path
import shutil

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("destination", type=Path)
a = p.parse_args()
src = Path(__file__).resolve().parent
a.destination.mkdir(parents=True, exist_ok=False)
text = (src / "PKGBUILD.in").read_text()
for path, name, token in [
    (src / "patches/0001-virgl-nv12-decode-option.patch", "0001-virgl-nv12-decode-option.patch", "NV12"),
    (src / "patches/0002-va-lossless-420-download.patch", "0002-va-lossless-420-download.patch", "DOWNLOAD"),
    (src / "ilinux-video", "ilinux-video", "WRAPPER"),
]:
    shutil.copyfile(path, a.destination / name)
    text = text.replace(f"@{token}_SHA256@", hashlib.sha256(path.read_bytes()).hexdigest())
(a.destination / "PKGBUILD").write_text(text)
print(a.destination.resolve())

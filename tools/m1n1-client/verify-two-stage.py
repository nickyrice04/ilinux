#!/usr/bin/env python3
"""Offline intake of both RAM images and stage one's embedded stage-two pin.

Read-only: hashes files, then uses macOS tar to read one member to stdout.
No extraction to disk, image execution, USB access or boot action. This verifies
agreement with reviewed Git records, not native functionality. Run the launcher's
offline package check separately. Python standard library; macOS /usr/bin/tar.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SHA = re.compile(r"[0-9a-f]{64}\Z")


def record(path, profile):
    value = json.loads(Path(path).read_text())
    if (not isinstance(value, dict) or type(value.get("schema")) is not int
            or value["schema"] != 1 or value.get("profile") != profile):
        raise ValueError("unexpected manifest schema/profile")
    if type(value.get("size")) is not int or value["size"] <= 0:
        raise ValueError("invalid manifest size")
    for key in ("sha256", "image_sha256"):
        if not isinstance(value.get(key), str) or not SHA.fullmatch(value[key]):
            raise ValueError("invalid manifest " + key)
    return value


def hash_image(path, expected):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("image must be a regular non-symlink file")
    if path.stat().st_size != expected["size"]:
        raise ValueError("image size differs from manifest")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    if h.hexdigest() != expected["sha256"]:
        raise ValueError("image SHA-256 differs from manifest")


def parse_pin(text):
    pin = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or key in pin:
            raise ValueError("malformed or duplicate embedded pin field")
        pin[key] = value
    for key in ("size", "entries", "unpacked_bytes_16k"):
        if not re.fullmatch(r"[1-9][0-9]{0,13}", pin.get(key, "")):
            raise ValueError("invalid embedded " + key)
        pin[key] = int(pin[key])
    for key in ("sha256", "image_sha256"):
        if not SHA.fullmatch(pin.get(key, "")):
            raise ValueError("invalid embedded " + key)
    return pin


def verify(stage1, stage2, records):
    records = Path(records)
    first = record(records / "ramroot-manifest.json", "ramroot")
    second = record(records / "omarchy-root-manifest.json", "omarchy")
    if first["image_sha256"] != second["image_sha256"]:
        raise ValueError("the manifests name different kernel Images")
    # Hash both images before asking tar to read a member from the verified file.
    hash_image(stage1, first)
    hash_image(stage2, second)
    result = subprocess.run(
        ["/usr/bin/tar", "-xOf", str(Path(stage1).resolve()), "etc/ilinux/stage2-pin"],
        capture_output=True, text=True, timeout=60, check=True)
    if len(result.stdout) > 8192:
        raise ValueError("embedded pin is unexpectedly large")
    pin = parse_pin(result.stdout)
    if any(pin[key] != second[key] for key in ("size", "sha256", "image_sha256")):
        raise ValueError("stage one embeds a different root/kernel pin")
    expected = first.get("stage2")
    if not isinstance(expected, dict) or any(
            pin[key] != expected.get(key)
            for key in ("size", "sha256", "image_sha256", "entries", "unpacked_bytes_16k")):
        raise ValueError("embedded pin differs from the reviewed stage-two metadata")
    return {
        "read_only": True, "status": "PASS", "native": "NOT RUN",
        "stage1": {"size": first["size"], "sha256": first["sha256"]},
        "stage2": {key: pin[key] for key in
                   ("size", "sha256", "image_sha256", "entries", "unpacked_bytes_16k")},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage1", required=True)
    parser.add_argument("--stage2", required=True)
    parser.add_argument("--records", default=str(ROOT / "native/boot"))
    args = parser.parse_args()
    try:
        result = verify(args.stage1, args.stage2, args.records)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        # Do not echo tar output or artifact contents into a public receipt.
        print(json.dumps({"read_only": True, "status": "REFUSED",
                          "reason": str(exc) if isinstance(exc, ValueError) else type(exc).__name__}))
        return 3
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Prepare real pinned driver functions for a userspace regression test.

Reads third-party source as data; never builds or executes it. Run compiled
outputs only in the isolated Linux lab. Output must be an unused directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

BASE = "77cb8f24c2381a8abb7272d7bbdec548d6426a8a"
PATH = "drivers/hid/dockchannel-hid/dockchannel-hid.c"
BASE_SHA256 = "15c1186c3bbb87dddb75c1f1053ab3a2c3a2a1128bba6718bd88977f4b7beb2f"
PATCHED_SHA256 = "e888ddaefc7d05f582b1db831ec9f2bd2e9858f4503242edf7c369866c45605c"
FUNCTIONS = ("dchid_checksum", "dchid_get_firmware", "dchid_handle_init",
             "dchid_handle_event", "dchid_packet_work", "dchid_handle_ack",
             "dchid_handle_packet")


def extract(source):
    start = source.index("#define COMMAND_TIMEOUT_MS")
    end = source.index("static ssize_t apple_layout_id_show")
    sections = [source[start:end]]
    for name in FUNCTIONS:
        match = re.search(r"^static [^\n]*\b" + name + r"\([^;]*?\n\{.*?^}\n",
                          source, re.M | re.S)
        if not match:
            raise ValueError("Unable to extract " + name)
        sections.append(match.group())
    return sections


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    out = args.output.resolve()
    original = subprocess.check_output(["git", "-C", str(args.repo.resolve()),
                                        "show", BASE + ":" + PATH])
    if hashlib.sha256(original).hexdigest() != BASE_SHA256:
        raise ValueError("Pinned driver source digest mismatch")
    out.mkdir(parents=True, exist_ok=False)
    for variant in ("baseline", "patched"):
        target = out / variant / PATH
        target.parent.mkdir(parents=True)
        target.write_bytes(original)
    patch = here / "0001-dockchannel-hid-validate-input-bounds.patch"
    subprocess.run(["patch", "-p1", "-i", str(patch)],
                   cwd=out / "patched", check=True)
    patched = (out / "patched" / PATH).read_bytes()
    if hashlib.sha256(patched).hexdigest() != PATCHED_SHA256:
        raise ValueError("Patched source digest mismatch")
    for variant in ("baseline", "patched"):
        source = (out / variant / PATH).read_text()
        sections = extract(source)
        (out / variant / "driver_types.inc").write_text(sections[0])
        (out / variant / "driver_functions.inc").write_text("\n".join(sections[1:]))
    for name in ("test_parser.c", "run-linux.sh"):
        shutil.copyfile(here / name, out / name)
    (out / "manifest.json").write_text(json.dumps({
        "base_commit": BASE, "source_path": PATH,
        "baseline_sha256": BASE_SHA256, "patched_sha256": PATCHED_SHA256,
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "functions": list(FUNCTIONS),
        "scope": "extracted actual driver functions, synthetic transport/HID hooks",
    }, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    main()

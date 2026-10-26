#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify the reviewed source closure, then render Recovery pages; never run them."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import types

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "native/boot/attempt31ae/manifest.json"
PINS = "native/boot/attempt31ae/source-sha256.txt"
RENDERER = "tools/recovery31ae/write_render.py"
REQUIRED = {MANIFEST, RENDERER, "tools/recovery31ae/prepare.py"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def local_file(root: Path, name: str) -> bytes:
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or str(path) != name or
            any(part in (".", "..") for part in path.parts)):
        raise ValueError("unsafe source path: " + name)
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("source symlink: " + name)
    if not current.is_file() or current.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("missing or oversized source: " + name)
    return current.read_bytes()


def source_closure(root: Path) -> tuple[bytes, dict[str, bytes]]:
    inventory = local_file(root, PINS)
    rows = inventory.decode("utf-8").splitlines()
    if not rows or len(rows) > 4096:
        raise ValueError("empty or excessive source inventory")
    verified = {}
    for row in rows:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", row)
        if match is None:
            raise ValueError("invalid source inventory line")
        expected, name = match.groups()
        if name == PINS or name in verified:
            raise ValueError("duplicate or self-pinned source: " + name)
        data = local_file(root, name)
        if sha(data) != expected:
            raise ValueError("source SHA-256 mismatch: " + name)
        verified[name] = data
    if not REQUIRED <= verified.keys():
        raise ValueError("inventory must pin manifest, renderer and preparation source")
    return inventory, verified


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate manifest key: " + key)
        result[key] = value
    return result


def profile_from_manifest(data: bytes) -> dict:
    manifest = json.loads(data, object_pairs_hook=unique_object)
    if not isinstance(manifest, dict) or manifest.get("schema") != "ilinux-native31ae-delivery-v1":
        raise ValueError("expected reviewed 31AE delivery manifest")
    name = manifest.get("candidate")
    if not isinstance(name, str) or not name or Path(name).name != name or name in (".", ".."):
        raise ValueError("invalid manifest candidate name")
    candidate = {"bytes": manifest.get("candidate_bytes"),
                 "sha256": manifest.get("candidate_sha256"),
                 "url": manifest.get("candidate_url")}
    files = manifest.get("files")
    item = files.get(name) if isinstance(files, dict) else None
    if not isinstance(item, dict) or (item.get("bytes"), item.get("sha256")) != (
            candidate["bytes"], candidate["sha256"]):
        raise ValueError("candidate disagrees with manifest file inventory")
    return {"schema": "ilinux31ae-write-v1", "candidate": candidate}


def load_renderer(data: bytes, path: Path):
    # Execute only the exact source bytes whose digest was checked above.
    # This imports the original renderer; no generated shell block is executed.
    module = types.ModuleType("_ilinux31ae_reviewed_writer")
    module.__file__ = str(path)
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def output_path(root: Path, output: Path) -> Path:
    raw = output if output.is_absolute() else root / output
    if ".." in raw.parts:
        raise ValueError("output traversal is not allowed")
    build = root / "build"
    current = root
    try:
        parts = raw.relative_to(root).parts
    except ValueError as exc:
        raise ValueError("output must be beneath repository build/") from exc
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("output path must not contain symlinks")
    resolved = raw.resolve()
    if build not in resolved.parents or raw.exists():
        raise ValueError("output must be an absent directory beneath repository build/")
    return resolved


def prepare(output: Path, root: Path = ROOT) -> dict:
    root = root.resolve()
    destination = output_path(root, output)
    inventory, verified = source_closure(root)
    profile = profile_from_manifest(verified[MANIFEST])
    renderer = load_renderer(verified[RENDERER], root / RENDERER)
    renderer.validate(profile)
    install = renderer.render(profile, "install")
    rollback = renderer.render(profile, "rollback")
    profile_bytes = (json.dumps(profile, indent=2, sort_keys=True) + "\n").encode()
    outputs = {"profile.json": profile_bytes,
               "install-paste.txt": install.encode(),
               "rollback-paste.txt": rollback.encode(),
               "recovery.html": renderer.page(install, rollback).encode()}
    # Refuse a concurrent source change before creating any output directory.
    current_inventory, current = source_closure(root)
    if current_inventory != inventory or current != verified:
        raise ValueError("reviewed sources changed during preparation")
    destination = output_path(root, destination)
    report = {"schema": "ilinux31ae-reviewed-pages-v1",
              "source_inventory_sha256": sha(inventory),
              "manifest_sha256": sha(verified[MANIFEST]),
              "verified_source_files": len(verified),
              "files": {name: {"bytes": len(data), "sha256": sha(data)}
                        for name, data in sorted(outputs.items())},
              "execution": "NOT_RUN", "network_used": False,
              "human_authorization_required": True,
              "independent_m1_review_required": True}
    destination.mkdir(parents=True)
    for name, data in outputs.items():
        (destination / name).write_bytes(data)
    (destination / "render.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.output), sort_keys=True))
    except (ValueError, OSError, UnicodeError) as exc:
        parser.exit(1, str(exc) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

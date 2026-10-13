"""Verify a received directory against the sender's SHA256SUMS; execute nothing."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pin_check import check_pin


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def regular_file(root, name):
    # Simple portable relative paths only; no symlinks, traversal or special files.
    if not re.fullmatch(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*", name):
        raise ValueError("Unsupported manifest path: " + name)
    parts = name.split("/")
    if any(part in (".", "..") for part in parts):
        raise ValueError("Unsafe manifest path: " + name)
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("Symlink is not a package file: " + name)
    if not path.is_file():
        raise ValueError("Missing or non-regular package file: " + name)
    return path


def verify(root, revision, manifest_digest):
    manifest = regular_file(root, "SHA256SUMS")
    if sha256(manifest) != manifest_digest:
        raise ValueError("SHA256SUMS differs from the sender's handoff digest")
    entries = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64}) [ *](.+)", line)
        if not match:
            raise ValueError("Malformed SHA256SUMS line")
        digest, name = match.groups()
        if name in entries or name == "SHA256SUMS":
            raise ValueError("Duplicate or self-referencing manifest entry: " + name)
        path = regular_file(root, name)
        actual = sha256(path)
        if actual != digest.lower():
            raise ValueError("SHA-256 mismatch: " + name)
        entries[name] = {"sha256": actual, "bytes": path.stat().st_size}
    required = {"Image", "t6050-j716c.dtb", "initramfs.cpio.gz", "m1n1-revision.txt"}
    if not required.issubset(entries):
        raise ValueError("Missing required manifest entries: " + ", ".join(sorted(required - entries.keys())))
    for path in root.rglob("*"):
        name = path.relative_to(root).as_posix()
        if path.is_symlink() or (not path.is_dir() and name not in entries and name != "SHA256SUMS"):
            raise ValueError("Unlisted or non-regular package content: " + name)
    target_revision = regular_file(root, "m1n1-revision.txt").read_text().strip()
    if target_revision != revision:
        raise ValueError("Sender's target m1n1 revision does not match the client pin")
    return {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "checksums_and_declared_revision_verified",
        "manifest_sha256": manifest_digest,
        "m1n1_revision": revision,
        "files": entries,
        "boot_authorized": False,
        "target_version_observed_live": False,
        "next": "Read native/boot/README.md; stop until dedicated boot-entry provisioning and explicit live-session approval; first live test is bounded USB handshake",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--manifest-sha256", required=True,
                        help="SHA-256 of SHA256SUMS from the sender's separate handoff")
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[0-9a-fA-F]{64}", args.manifest_sha256):
            raise ValueError("Expected a 64-digit manifest SHA-256")
        root = args.package.resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Package must be a directory; archives are not extracted")
        result = verify(root, check_pin(), args.manifest_sha256.lower())
    except (ValueError, OSError) as exc:
        parser.exit(1, "Verification FAILED: " + str(exc) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

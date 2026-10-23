#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify and unpack pinned public tool packages only into the guest tmpfs.

No package installation, dependency bypass, key import or maintainer script.
"""
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile

BAD = {"BADSIG", "ERRSIG", "EXPSIG", "EXPKEYSIG", "REVKEYSIG", "NO_PUBKEY",
       "KEYEXPIRED", "SIGEXPIRED", "KEYREVOKED", "FAILURE", "ERROR", "NODATA",
       "UNEXPECTED", "TRUST_UNDEFINED", "TRUST_NEVER", "TRUST_MARGINAL", "TRUST_EXPIRED"}
TRUST = {"TRUST_FULLY", "TRUST_ULTIMATE"}


def signature_status(text, code):
    records = [line[len("[GNUPG:] "):].split() for line in text.splitlines()
               if line.startswith("[GNUPG:] ")]
    if code != 0 or any(not row or row[0] in BAD for row in records):
        raise ValueError("SIGNATURE_REFUSED")
    valid = [row for row in records if row[0] == "VALIDSIG"]
    good = [row for row in records if row[0] == "GOODSIG"]
    trust = [row for row in records if row[0] in TRUST]
    if len(valid) != 1 or len(good) != 1 or len(trust) != 1:
        raise ValueError("SIGNATURE_TRUST_INCOMPLETE")
    if len(valid[0]) < 2 or not re.fullmatch(r"[A-F0-9]{40}|[A-F0-9]{64}", valid[0][1]):
        raise ValueError("SIGNATURE_FINGERPRINT")
    return {"validsig": True, "trust": trust[0][0], "signer_fingerprint": valid[0][1]}


def allowed_member(member):
    name = PurePosixPath(member.name)
    if name.is_absolute() or ".." in name.parts or "\x00" in member.name:
        raise ValueError("ARCHIVE_PATH")
    if not name.parts or name.parts[0] != "usr":
        return False
    if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
        raise ValueError("ARCHIVE_TYPE")
    if member.size < 0 or member.size > 512 * 1024 * 1024:
        raise ValueError("ARCHIVE_SIZE")
    return True


def relocate_pc(text, prefix):
    # Relocate only package configuration data in our extracted copy. The guest
    # system's pkg-config files remain intact, so libdrm/gtest stay discoverable.
    return re.sub(r"(?m)^(\w+=)/usr(?=/|$)", lambda match: match[1] + str(prefix / "usr"), text)


def main():
    job, source, target, output = map(Path, sys.argv[1:])
    if target.exists():
        raise ValueError("TOOLCHAIN_DIRECTORY_EXISTS")
    spec = importlib.util.spec_from_file_location("package_space", job / "package-space.py")
    space = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(space)
    packages = json.loads((job / "packages.json").read_text())["packages"]
    # Copy public verification material only. Never copy private keys; never
    # modify the system keyring or start an agent against it.
    verify_home = target.parent / "verification-keyring"
    verify_home.mkdir(mode=0o700)
    public_files = []
    for name in ("pubring.gpg", "pubring.kbx", "trustdb.gpg"):
        original = Path("/etc/pacman.d/gnupg") / name
        if original.is_file() and not original.is_symlink():
            if original.stat().st_size > 128 * 1024 * 1024:
                raise ValueError("KEYRING_BOUND")
            shutil.copyfile(original, verify_home / name)
            public_files.append(name)
    if "trustdb.gpg" not in public_files or not {"pubring.gpg", "pubring.kbx"}.intersection(public_files):
        raise ValueError("PUBLIC_VERIFICATION_KEYRING_MISSING")
    verified = []
    # Verify every package before extracting any package.
    for package in packages:
        space.check_package_info(package, source)
        archive = source / package["filename"]
        process = subprocess.run([
            "/usr/bin/gpg", "--no-options", "--homedir", str(verify_home),
            "--batch", "--no-auto-key-retrieve", "--no-auto-key-import",
            "--no-autostart", "--status-fd", "1",
            "--verify", str(archive) + ".sig", str(archive)],
            capture_output=True, text=True, timeout=60, check=False)
        status = signature_status(process.stdout, process.returncode)
        verified.append({"name": package["name"], "version": package["version"], **status})
    target.mkdir(mode=0o700)
    members_total = 0
    for package in packages:
        with tarfile.open(source / package["filename"], "r:xz") as archive:
            members = archive.getmembers()
            if len(members) > 40000:
                raise ValueError("ARCHIVE_COUNT")
            admitted = [member for member in members if allowed_member(member)]
            if sum(member.size for member in admitted if member.isfile()) > package["installed_size"]:
                raise ValueError("ARCHIVE_INSTALLED_SIZE")
            # Python's data filter also rejects absolute/outside-target links.
            archive.extractall(target, members=admitted, filter="data")
            members_total += len(admitted)
    relocated = []
    for directory in (target / "usr/lib/pkgconfig", target / "usr/share/pkgconfig"):
        for path in sorted(directory.glob("*.pc")):
            if path.is_symlink() or path.stat().st_size > 128 * 1024:
                raise ValueError("PKGCONFIG_TYPE")
            before = path.read_text()
            after = relocate_pc(before, target)
            if after != before:
                path.write_text(after)
                relocated.append({"file": path.name,
                                  "original_sha256": hashlib.sha256(before.encode()).hexdigest(),
                                  "relocated_sha256": hashlib.sha256(after.encode()).hexdigest()})
    report = {"result": "ISOLATED_TOOLCHAIN_VERIFIED", "packages": verified,
              "extracted_members": members_total, "relocated_pkgconfig": relocated,
              "package_installations": 0, "package_scripts_executed": 0,
              "network_operations": 0}
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print("ISOLATED_TOOLCHAIN_VERIFIED")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create a credential-free offline vendor closure in the Linux build VM."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import tarfile


def checked(path, pin):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != pin['bytes']:
        raise ValueError('INPUT_FILE')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != pin['sha256']:
        raise ValueError('INPUT_HASH')
    return data


def unpack(archive, dest, prefix):
    members = archive.getmembers()
    if len(members) > 30000 or sum(x.size for x in members) > 256 * 1024**2:
        raise ValueError('CRATE_BOUND')
    seen = set()
    for m in members:
        p = PurePosixPath(m.name)
        if (p.is_absolute() or not p.parts or p.parts[0] != prefix or
                '..' in p.parts or '\\' in m.name or m.name in seen or
                not (m.isfile() or m.isdir())):
            raise ValueError('CRATE_PATH_OR_TYPE')
        seen.add(m.name)
    archive.extractall(dest, filter='data')


def checksums(directory, package):
    files = {}
    for p in sorted(directory.rglob('*')):
        if p.is_symlink():
            raise ValueError('VENDOR_SYMLINK')
        if p.is_file():
            files[p.relative_to(directory).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    (directory / '.cargo-checksum.json').write_text(json.dumps({'files': files, 'package': package}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'cached_crates', 'new_crates', 'fatfs_packs', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    if platform.system() != 'Linux' or args.output.exists():
        raise ValueError('FRESH_LINUX_WORKSPACE_REQUIRED')
    manifest = json.loads(args.manifest.read_text())
    vendor = args.output / 'vendor'; vendor.mkdir(parents=True, mode=0o700)
    for filename, pin in manifest['registry_crates'].items():
        path = args.new_crates / filename
        if not path.is_file():
            path = args.cached_crates / filename
        data = checked(path, pin)
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            prefix = pin['name'] + '-' + pin['version']
            unpack(archive, vendor, prefix)
        checksums(vendor / prefix, pin['sha256'])
    # Reconstruct only the pinned public Git object pack, without copying any
    # user's Git configuration, credentials, hooks or checkout modifications.
    bare = args.output / 'fatfs.git'
    git_env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null')
    subprocess.run(['git', 'init', '--bare', str(bare)], check=True, capture_output=True, env=git_env)
    for filename, pin in manifest['fatfs_object_packs'].items():
        (bare / 'objects/pack' / filename).write_bytes(checked(args.fatfs_packs / filename, pin))
    archive_data = subprocess.check_output(['git', '--git-dir=' + str(bare), 'archive',
                                          '--prefix=fatfs-0.4.0/', manifest['fatfs_revision']], env=git_env)
    with tarfile.open(fileobj=io.BytesIO(archive_data), mode='r:') as archive:
        unpack(archive, vendor, 'fatfs-0.4.0')
    checksums(vendor / 'fatfs-0.4.0', None)
    shutil.rmtree(bare)
    cargo_home = args.output / 'cargo-home'; cargo_home.mkdir(mode=0o700)
    url = 'https://github.com/aurora-silicon/fatfs'
    rev = manifest['fatfs_revision']
    config = ('[net]\noffline = true\n[source.crates-io]\nreplace-with = "vendor"\n'
              '[source."git+' + url + '?rev=' + rev + '"]\ngit = "' + url + '"\n'
              'rev = "' + rev + '"\nreplace-with = "vendor"\n'
              '[source.vendor]\ndirectory = ' + json.dumps(str(vendor)) + '\n')
    (cargo_home / 'config.toml').write_text(config)
    print(json.dumps({'schema': 'ilinux097-cargo-vendor-v1',
                      'registry_crates': len(manifest['registry_crates']),
                      'git_revision': rev, 'credentials_copied': False, 'network': False}))


if __name__ == '__main__':
    main()

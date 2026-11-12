#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Export notices for active Cargo dependencies from offline metadata, in VM.

Cargo metadata is private build input because it contains absolute cache paths.
The published index omits those paths and lists only active package IDs, source
URLs, declared license expressions, notice hashes and registry checksums.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def require(value, message):
    if not value:
        raise ValueError(message)


def collect(metadata, output):
    require(sys.platform == 'linux', 'Linux build VM required')
    require(not output.exists(), 'refusing existing license output')
    resolve = metadata['resolve']
    nodes = {node['id']: node for node in resolve['nodes']}
    packages = {package['id']: package for package in metadata['packages']}
    pinned_root = Path(packages[resolve['root']]['manifest_path']).parent.resolve(strict=True)
    pending, active = [resolve['root']], set()
    while pending:
        package_id = pending.pop()
        if package_id in active:
            continue
        require(package_id in packages and package_id in nodes, 'missing resolved package')
        active.add(package_id)
        pending.extend(dependency['pkg'] for dependency in nodes[package_id]['deps'])
    require(1 <= len(active) <= 128, 'unbounded resolved dependency graph')
    output.mkdir(parents=True)
    records = []
    for package_id in sorted(active):
        package = packages[package_id]
        name, version = package['name'], package['version']
        require(re.fullmatch(r'[A-Za-z0-9_.+-]+', name + '-' + version), 'invalid package name')
        root = Path(package['manifest_path']).parent.resolve(strict=True)
        files = {path for path in root.iterdir() if path.is_file() and
                 path.name.upper().startswith(('LICENSE', 'COPYING', 'NOTICE', 'COPYRIGHT'))}
        if package.get('license_file'):
            files.add(root / package['license_file'])
        if package['source'] is None:
            require(root.is_relative_to(pinned_root), 'path dependency escapes pinned Aura tree')
        record = {'name': name, 'version': version,
                  'id': (package['source'] or 'pinned-aura-path') + '#' + name + '@' + version,
                  'source': package['source'], 'license': package.get('license'), 'notices': []}
        checksum = root / '.cargo-checksum.json'
        if checksum.is_file():
            registry_checksum = json.loads(checksum.read_text()).get('package')
            require(registry_checksum is None or re.fullmatch(r'[0-9a-f]{64}', registry_checksum),
                    'invalid registry checksum')
            record['registry_package_checksum'] = registry_checksum
        # Path packages belong to the exact Aura source archive. Its full GPL/MIT
        # license map is exported separately; do not mistake them for missing
        # third-party notices. Resolved registry/Git packages must carry notices.
        require(files or package['source'] is None, 'external package has no license notices: ' + name)
        for path in sorted(files):
            require(not path.is_symlink(), 'license symlink refused')
            resolved = path.resolve(strict=True)
            require(resolved.is_relative_to(root) and resolved.is_file(), 'license escapes package')
            require(0 < resolved.stat().st_size <= 1 << 20, 'unbounded license file')
            data = resolved.read_bytes()
            relative = resolved.relative_to(root)
            target = output / (name + '-' + version) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            require(not target.exists(), 'duplicate license target')
            target.write_bytes(data)
            record['notices'].append({'file': str(target.relative_to(output)), 'bytes': len(data),
                                      'sha256': hashlib.sha256(data).hexdigest()})
        records.append(record)
    index = {'schema': 'ilinux-cargo-notices-v1', 'scope': 'ACTIVE_RESOLVED_PACKAGES',
             'packages': records}
    (output / 'index.json').write_text(json.dumps(index, indent=2) + '\n')
    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('metadata', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    require(args.metadata.stat().st_size <= 16 << 20, 'unbounded Cargo metadata')
    count = collect(json.loads(args.metadata.read_text()), args.output)
    print(json.dumps({'active_packages': count, 'output': args.output.name}))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Export notices from the actual authenticated official Rust 1.96.1 inputs."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile


def main():
    inputs, output = map(Path, sys.argv[1:])
    if output.exists():
        raise ValueError('FRESH_NOTICE_OUTPUT_REQUIRED')
    manifest = json.loads((inputs / 'manifest.json').read_text())
    rows = [x for x in manifest['files'] if x['role'] == 'rust_component' and
            x['component'] in ('rustc', 'rust-src')]
    if {x['component'] for x in rows} != {'rustc', 'rust-src'}:
        raise ValueError('EXACT_RUST_COMPONENTS_REQUIRED')
    records = []
    output.mkdir(parents=True)
    for row in rows:
        path = inputs / row['name']
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('RUST_COMPONENT_HASH')
        with tarfile.open(path, 'r:xz') as archive:
            root = archive.getmembers()[0].name.split('/')[0]
            names = ['LICENSE-MIT', 'LICENSE-APACHE', 'COPYRIGHT']
            if row['component'] == 'rustc':
                names += ['rustc/share/doc/rust/COPYRIGHT-library.html']
            else:
                names += ['rust-src/lib/rustlib/src/rust/library/compiler-builtins/LICENSE.txt',
                          'rust-src/lib/rustlib/src/rust/library/compiler-builtins/libm/LICENSE.txt']
            for name in names:
                member = archive.getmember(root + '/' + name)
                if not member.isfile() or not 0 < member.size < 16 * 1024**2:
                    raise ValueError('NOTICE_BOUND')
                data = archive.extractfile(member).read()
                relative = row['component'] + '/' + name
                target = output / relative; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                records.append({'file': relative, 'bytes': len(data),
                                'sha256': hashlib.sha256(data).hexdigest()})
    result = {'schema': 'ilinux097-rust-notices-v1', 'rust_version': '1.96.1',
              'scope': 'AUTHENTICATED_OFFICIAL_RUST_COMPONENTS',
              'runtime_crates': ['core', 'alloc', 'compiler_builtins'], 'notices': records}
    (output / 'index.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'notice_files': len(records), 'version': '1.96.1'}))


if __name__ == '__main__':
    main()

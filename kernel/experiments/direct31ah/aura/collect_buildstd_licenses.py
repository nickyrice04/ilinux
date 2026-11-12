#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Export exact installed Arch Rust build-std runtime notices in the Linux VM."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def require(value, message):
    if not value:
        raise ValueError(message)


def collect(output):
    require(sys.platform == 'linux', 'Linux build VM required')
    require(not output.exists(), 'refusing existing license output')
    source = Path('/usr/lib/rustlib/src/rust')
    # These are installed package notices, not metadata from the project Cargo
    # graph: -Z build-std adds core/alloc/compiler_builtins outside that graph.
    required = {
        'rust-src/COPYRIGHT': Path('/usr/share/licenses/rust-src/COPYRIGHT'),
        'rust-src/LICENSE-MIT': Path('/usr/share/licenses/rust-src/LICENSE-MIT'),
        'rust/COPYRIGHT-library.html.rustc':
            Path('/usr/share/licenses/rust/COPYRIGHT-library.html.rustc'),
        'compiler-builtins/LICENSE.txt':
            source / 'library/compiler-builtins/LICENSE.txt',
        'compiler-builtins/libm/LICENSE.txt':
            source / 'library/compiler-builtins/libm/LICENSE.txt',
    }
    optional = {
        'rust-src/LICENSE-APACHE': Path('/usr/share/licenses/rust-src/LICENSE-APACHE'),
        'rust/LICENSE-APACHE.rustc': Path('/usr/share/licenses/rust/LICENSE-APACHE.rustc'),
        'source/LICENSE-APACHE': source / 'LICENSE-APACHE',
        'source/LICENSE-MIT': source / 'LICENSE-MIT',
    }
    for name, path in required.items():
        require(path.is_file(), 'required installed Rust notice missing: ' + name)
    files = {**required, **{name: path for name, path in optional.items() if path.is_file()}}
    builtin = required['compiler-builtins/LICENSE.txt'].read_bytes()
    # This pinned compiler-builtins tree includes full MIT, Apache-2.0 and LLVM
    # exception texts in one notice. Do not silently publish only an SPDX label.
    require(b'MIT License' in builtin and b'Apache License' in builtin and
            b'LLVM' in builtin and b'TERMS AND CONDITIONS' in builtin,
            'compiler-builtins full license text not present')
    output.mkdir(parents=True)
    records = []
    for name, path in sorted(files.items()):
        require(0 < path.stat().st_size <= 16 << 20, 'unbounded Rust notice')
        data = path.read_bytes()
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        records.append({'file': name, 'bytes': len(data),
                        'sha256': hashlib.sha256(data).hexdigest()})
    # Arch package versions tie the installed source notices to this toolchain.
    packages = subprocess.check_output(['pacman', '-Q', 'rust', 'rust-src', 'cargo'],
                                       text=True).splitlines()
    index = {'schema': 'ilinux-rust-buildstd-notices-v1',
             'scope': 'INSTALLED_RUST_BUILD_STD_RUNTIME', 'package_versions': packages,
             'rustc': subprocess.check_output(['rustc', '--version'], text=True).strip(),
             'runtime_crates': ['core', 'alloc', 'compiler_builtins'], 'notices': records}
    (output / 'index.json').write_text(json.dumps(index, indent=2) + '\n')
    return {'notice_files': len(records), 'runtime_crates': index['runtime_crates']}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(collect(args.output), indent=2))


if __name__ == '__main__':
    main()

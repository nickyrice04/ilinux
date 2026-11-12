#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Package allowlisted local-user review artifacts, never install or enroll."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('aura', type=Path)
    ap.add_argument('kernel', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('manifest', type=Path)
    args = ap.parse_args()
    if args.output.exists() or args.manifest.exists():
        raise ValueError('refusing existing output')
    files = {}

    def add(name, path):
        if path.is_symlink() or not path.is_file():
            raise ValueError('regular artifact required')
        files[name] = path.read_bytes()

    for variant in ('baseline', 'j716c-proxy'):
        for name in ('aura-boot-128m.macho', 'build_cfg.h', 'build_tag.h', 'padding.json'):
            add('aura/' + variant + '/' + name, args.aura / variant / name)
    for name in ('build-result.json', 'cargo-notices-result.json', 'rust-buildstd-notices-result.json'):
        add('aura/' + name, args.aura / name)
    for path in sorted((args.aura / 'licenses').rglob('*')):
        if path.is_file():
            add('aura/licenses/' + str(path.relative_to(args.aura / 'licenses')), path)
    for name in ('Image', 'kernel.config', 't6050-j716c-diagnostic.dtb',
                 'modules-OFFLINE-REVIEW.tar.gz', 'input-source-files.json'):
        add('linux/' + name, args.kernel / name)
    add('linux/build-evidence.json', args.kernel / 'artifacts.json')
    files['README.txt'] = (
        '31AH OFFLINE REVIEW ONLY\n'
        'Local-user artifact handoff; no installation or restart instructions.\n'
        'Exact public source revisions, reconstructed kernel config, separate original USB delta.\n'
        'No physical M5 runtime, CTXR enforcement or performance parity is established.\n'
        'The two Aura files are alternatives, not two installation stages.\n'
        'The modules archive is for inspection, not loading.\n'
        'No diagnostic initramfs or glibc executable is distributed here.\n'
        'No Apple firmware, host identities, keys, media or upstream per-unit DROM.\n'
        'Source archives/recipes remain separately identified in the Git manifest.\n'
    ).encode('ascii')
    assert len(files) <= 128
    args.output.parent.mkdir(parents=True, exist_ok=True)
    entries = {}
    with args.output.open('xb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=1794355200) as gz:
            with tarfile.open(fileobj=gz, mode='w', format=tarfile.USTAR_FORMAT) as tar:
                for name, data in sorted(files.items()):
                    name = 'ilinux-direct31ah/' + name
                    assert len(data) <= 256 * 1024 * 1024
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mode = 0o644
                    info.mtime = 1794355200
                    info.uid = info.gid = 0
                    info.uname = info.gname = ''
                    tar.addfile(info, io.BytesIO(data))
                    entries[name] = {'bytes': len(data), 'sha256': sha(data)}
    package = args.output.read_bytes()
    manifest = {
        'schema': 'ilinux-direct31ah-offline-bundle-v1',
        'target': {'model': 'Mac17,6', 'board': 'j716c', 'chip_id': '0x6050'},
        'native_authorized': False, 'restart_ready': False,
        'firmware_change_authorized': False,
        'delivery': 'LOCAL_USER_HANDOFF_NOT_PUBLIC_BINARY_RELEASE',
        'reporter_configuration_reproduced': False,
        'sources': {
            'aura': {'commit': 'bd9f3e8273dc79ae9095c19c2c4f32218446ad4e',
                     'url': 'https://github.com/aurora-silicon/aura/archive/bd9f3e8273dc79ae9095c19c2c4f32218446ad4e.tar.gz',
                     'archive_sha256': '6f685971f924781c4f0390ba3a3244ee82b71c1ab90266610d5ad5c6d77c7882'},
            'linux': {'commit': 'dc8f6f77934b471a13c91e7780e2d91ebc904b3d',
                      'url': 'https://github.com/aurora-silicon/linux/archive/dc8f6f77934b471a13c91e7780e2d91ebc904b3d.tar.gz',
                      'archive_sha256': '0a8ae9d9529a4ff1754bcc4294d68cffbd449d82cc1a4a1ecf3aaec1a63a46dd'}},
        'package': {'filename': args.output.name, 'bytes': len(package),
                    'sha256': sha(package), 'files': entries}}
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open('x') as f:
        f.write(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'members': len(entries), 'bytes': len(package), 'sha256': sha(package)}))


if __name__ == '__main__':
    main()

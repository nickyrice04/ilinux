#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build original camera UI locally; launch only with --launch. No camera on build."""
import argparse
import os
from pathlib import Path
import plistlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def private_directory(root, parts):
    root = root.resolve(strict=True)
    current = root
    for part in parts:
        if not part or part in ('.', '..') or '/' in part:
            raise ValueError('invalid build component')
        current = current / part
        if current.is_symlink():
            raise ValueError('symlink build path refused')
        current.mkdir(mode=0o700, exist_ok=True)
        if not current.is_dir() or current.resolve() != current:
            raise ValueError('noncanonical build path refused')
    return current


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--launch', action='store_true', help='Open the UI after building; Start preview opens camera')
    args = p.parse_args()
    if sys.platform != 'darwin':
        p.error('macOS with existing Command Line Tools required; no tools installed')
    os.umask(0o077)
    build = private_directory(ROOT, ('build', 'camera-recorder'))
    cache = private_directory(ROOT, ('build', 'camera-recorder', 'module-cache'))
    app = private_directory(ROOT, ('build', 'camera-recorder', 'iLinux Camera.app'))
    contents = private_directory(ROOT, ('build', 'camera-recorder', 'iLinux Camera.app', 'Contents'))
    macos = private_directory(ROOT, ('build', 'camera-recorder', 'iLinux Camera.app', 'Contents', 'MacOS'))
    output = macos / 'iLinuxCamera'
    # Rebuildable app only, never a media directory. Refuse symlink targets.
    for path in (output, contents / 'Info.plist'):
        if path.is_symlink():
            raise ValueError('symlink app target refused')
    subprocess.run(['/usr/bin/xcrun', 'swiftc', '-swift-version', '5', '-O',
                    '-module-cache-path', str(cache), '-framework', 'AppKit',
                    '-framework', 'AVFoundation', str(HERE / 'CapturePolicy.swift'),
                    str(HERE / 'main.swift'), '-o', str(output)], check=True)
    info = {'CFBundleIdentifier': 'org.ilinux.local-camera', 'CFBundleName': 'iLinux Camera',
            'CFBundleExecutable': 'iLinuxCamera', 'CFBundlePackageType': 'APPL',
            'CFBundleVersion': '1', 'CFBundleShortVersionString': '1.0',
            'NSCameraUsageDescription': 'Preview and silently record the lab display locally after your framing check.',
            'NSHighResolutionCapable': True, 'CaptureWorkspaceRoot': str(ROOT)}
    (contents / 'Info.plist').write_bytes(plistlib.dumps(info))
    # Ad-hoc signing is local to generated build output; no host install or identity.
    subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', str(app)], check=True)
    print('Built camera-only app under build/camera-recorder/. Camera remains closed.')
    if args.launch:
        subprocess.run(['/usr/bin/open', '-n', str(app)], check=True)


if __name__ == '__main__':
    main()

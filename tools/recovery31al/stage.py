# SPDX-License-Identifier: MIT
"""Explicit future lab-Data copy of the two-file 31AL diagnostic kit.

Importing or directly running this module performs no staging. The package
controller is the only production CLI; tests inject workspace-only backends.
No boot object, transaction state, policy, volume or default is changed.
"""
import hashlib
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = '31al-diagnostic'


def require(value):
    if not value:
        raise ValueError('31AL staging refused')


def stage_kit(prepared, root=ROOT, backend=None, *, controller):
    """Copy only on explicit invocation, after the frozen live/fixture guards."""
    root = Path(root).resolve()
    # The admitted caller supplies its already-executing verified functions.
    # Never reopen or execute a mutable controller path at this boundary.
    package = controller
    admitted_root, records, renderer, server = package.admitted(root)
    require(admitted_root == root)
    closure = server.source_closure(root)
    require(closure[1] == records)
    original = package.frozen_stager(root)
    # Reuse the unchanged frozen target guard, metadata policy and live reader.
    _, _, frozen, _, _ = original.checked_sources(root, root / original.INVENTORY)
    prepared = Path(prepared)
    if not prepared.is_absolute():
        prepared = root / prepared
    require(root / 'build' in prepared.parents)
    original.preparation.checked_path(prepared, root, exists=False)
    value, artifacts = package.read_kit(prepared, root, server)
    value = renderer.profile.validate(value)
    require(renderer.profile.canonical(value) == artifacts['profile.json'])
    require(set(artifacts) == {'profile.json', 'ilinux31aj-reader'})
    helper = value['files']['helper']
    require(helper['name'] == 'ilinux31aj-reader')
    require(len(artifacts[helper['name']]) == helper['bytes'] and
            hashlib.sha256(artifacts[helper['name']]).hexdigest() == helper['sha256'])
    files = {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
             for name, data in artifacts.items()}
    fds = {}
    fingerprints = {}
    base_fd = dest_fd = None
    created_files = []
    created = False
    backend = original.LiveBackend() if backend is None else backend
    try:
        # All source artifacts are opened and hashed before querying the target.
        for name, item in files.items():
            path = original.preparation.checked_path(prepared / name, root)
            fds[name] = frozen.secure_open(path)
            fingerprints[name] = original.digest_fd(fds[name], item)
        if backend.synthetic:
            fixture = Path(backend.fixture_root)
            require(fixture.is_absolute() and root in fixture.parents)
            base = fixture / 'lab-data/Users/Shared/iLinuxBoot'
            original.preparation.checked_path(base, root, exists=False)
        else:
            require(type(backend) is original.LiveBackend)
            base = Path(original.BASE)
            for path in (original.LAB, original.DATA):
                fd = frozen.secure_open(path, directory=True)
                os.close(fd)
        binding = original.guard_metadata(backend.observe(frozen), frozen)
        base_fd = frozen.secure_open(base, directory=True)
        require(original.absent_at(base_fd, DESTINATION))

        def recheck_sources():
            require(server.source_closure(root) == closure)
            require(package.read_kit(prepared, root, server) == (value, artifacts))
            for name, item in files.items():
                require(original.digest_fd(fds[name], item) == fingerprints[name])
                current = frozen.secure_open(prepared / name)
                try:
                    require(original.fingerprint(os.fstat(current)) == fingerprints[name])
                finally:
                    os.close(current)

        recheck_sources()
        # New name only; never overwrite or touch the old kit/state directories.
        os.mkdir(DESTINATION, 0o700, dir_fd=base_fd)
        created = True
        dest_fd = os.open(DESTINATION, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                          dir_fd=base_fd)
        os.fchmod(dest_fd, 0o700)
        for name, item in files.items():
            mode = 0o700 if name == 'ilinux31aj-reader' else 0o600
            out = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                          mode, dir_fd=dest_fd)
            created_files.append(name)
            try:
                os.fchmod(out, mode)
                os.lseek(fds[name], 0, os.SEEK_SET)
                digest = hashlib.sha256()
                total = 0
                while True:
                    chunk = os.read(fds[name], 1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    require(total <= item['bytes'])
                    digest.update(chunk)
                    at = 0
                    while at < len(chunk):
                        wrote = os.write(out, chunk[at:])
                        require(wrote > 0)
                        at += wrote
                require(total == item['bytes'] and digest.hexdigest() == item['sha256'])
                require(original.fingerprint(os.fstat(fds[name])) == fingerprints[name])
                os.fsync(out)
            finally:
                os.close(out)
        os.fsync(dest_fd)
        os.fsync(base_fd)
        require(original.guard_metadata(backend.observe(frozen), frozen) == binding)
        recheck_sources()
        for name, item in files.items():
            copied = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dest_fd)
            try:
                original.digest_fd(copied, item)
                info = os.fstat(copied)
                require(info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) ==
                        (0o700 if name == 'ilinux31aj-reader' else 0o600))
            finally:
                os.close(copied)
        # Held descriptors and their names must still identify the same objects.
        current_base = frozen.secure_open(base, directory=True)
        try:
            named, held = os.fstat(current_base), os.fstat(base_fd)
            require((named.st_dev, named.st_ino) == (held.st_dev, held.st_ino))
        finally:
            os.close(current_base)
        named = os.stat(DESTINATION, dir_fd=base_fd, follow_symlinks=False)
        held = os.fstat(dest_fd)
        require(stat.S_ISDIR(named.st_mode) and
                (named.st_dev, named.st_ino) == (held.st_dev, held.st_ino) and
                held.st_uid == os.geteuid() and stat.S_IMODE(held.st_mode) == 0o700)
        require(set(os.listdir(dest_fd)) == set(files))
        return {'schema': 'ilinux31al-lab-data-staging-v1',
                'scope': 'SYNTHETIC_CONTROL' if backend.synthetic else 'MACOS_LAB_DATA_STAGE',
                'staged': True, 'files': dict(sorted(files.items())),
                'diagnostic_only': True, 'boot_object_installed': False,
                'boot_settings_changed': False, 'policy_read': False,
                'default_changed': False, 'volume_created': False, 'native_ready': False}
    except BaseException as exc:
        # Remove only known files created in our held new directory. Foreign
        # files or a replacement named directory are never recursively removed.
        if created:
            if dest_fd is not None:
                for name in created_files:
                    try:
                        os.unlink(name, dir_fd=dest_fd)
                    except OSError:
                        pass
            try:
                current = os.stat(DESTINATION, dir_fd=base_fd, follow_symlinks=False)
                ours = os.fstat(dest_fd) if dest_fd is not None else None
                if ours is not None and (current.st_dev, current.st_ino) == (ours.st_dev, ours.st_ino):
                    os.rmdir(DESTINATION, dir_fd=base_fd)
            except OSError:
                pass
        if isinstance(exc, frozen.Refused):
            raise ValueError('31AL staging refused') from None
        raise
    finally:
        for fd in fds.values():
            os.close(fd)
        if dest_fd is not None:
            os.close(dest_fd)
        if base_fd is not None:
            os.close(base_fd)

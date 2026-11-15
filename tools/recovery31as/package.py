#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare exact 31AS source-only pages around the unchanged 31AR transaction.

No stage or controller-dispatch mode exists. Default/help and check-only are
inert. Serving is a separate bounded read-only operation.
"""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import stat
import sys
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OLD_INVENTORY = 'native/boot/attempt31ar-package/source-sha256.txt'
OLD_INVENTORY_SHA = '9ff372bba278c053a639b5b158fbc907fe17def5f7ef87142fa2daf3147d80fc'
INVENTORY = 'native/boot/attempt31as-page/source-sha256.txt'
PACKAGE = 'tools/recovery31ar/package.py'
OWN = {'tools/recovery31as/' + n for n in ('package.py', 'test_package.py', 'README.md')} | {
    'tools/m1n1-client/attempt31as-instructions.md'}
REQUIRED = ('/usr/bin/id', '/usr/bin/stat', '/usr/bin/mktemp', '/bin/pwd',
            '/bin/cat', '/bin/cp', '/bin/chmod', '/bin/rm', '/bin/rmdir',
            '/usr/sbin/diskutil', '/usr/sbin/sysctl', '/sbin/mount_apfs',
            '/sbin/umount', '/usr/bin/kmutil', '/usr/bin/bputil')
OLD_HASH = '''hash_file() { if test -x /sbin/sha256; then /sbin/sha256 -q "$1"; elif test -x /usr/bin/shasum; then /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'; elif test -x /usr/bin/openssl; then /usr/bin/openssl dgst -sha256 "$1" | /usr/bin/awk '{print $NF}'; else return 1; fi; }'''
NEW_HASH = r'''hash_file() {
  if test -x /sbin/sha256; then
    HASH_DIGEST31AS=$(/sbin/sha256 -q "$1") || return 1
  elif test -x /usr/bin/shasum; then
    HASH_OUTPUT31AS=$(/usr/bin/shasum -a 256 "$1") || return 1
    case "$HASH_OUTPUT31AS" in *$'\n'*) return 1;; esac
    HASH_DIGEST31AS=${HASH_OUTPUT31AS%% *}
  elif test -x /usr/bin/openssl; then
    HASH_OUTPUT31AS=$(/usr/bin/openssl dgst -sha256 "$1") || return 1
    case "$HASH_OUTPUT31AS" in *$'\n'*) return 1;; esac
    HASH_DIGEST31AS=${HASH_OUTPUT31AS##* }
  else return 1
  fi
  case "$HASH_DIGEST31AS" in ''|*[!0123456789abcdef]*) return 1;; esac
  test "${#HASH_DIGEST31AS}" = 64 || return 1
  printf '%s\n' "$HASH_DIGEST31AS"
}'''


def need(ok):
    if not ok:
        raise ValueError('31AS refused')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(name, root=ROOT, limit=8 * 1024 * 1024):
    root = Path(root)
    path = Path(name)
    need(not path.is_absolute() and str(path) == name and
         re.fullmatch(r'[A-Za-z0-9_./-]+', name) and
         all(p not in ('.', '..') for p in path.parts))
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for i, part in enumerate(path.parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if i + 1 < len(path.parts):
                flags |= os.O_DIRECTORY
            following = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = following
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit)
        data = bytearray()
        while len(data) <= limit:
            block = os.read(fd, min(65536, limit + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        after = os.fstat(fd)
        need(len(data) == before.st_size and all(getattr(before, n) == getattr(after, n)
             for n in ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')))
        return bytes(data)
    finally:
        os.close(fd)


def records(raw):
    result = {}
    for line in raw.decode('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
        need(match is not None)
        digest, name = match.groups()
        need(name not in result)
        result[name] = digest
    need(0 < len(result) < 2048)
    return result


def frozen(root=ROOT):
    root = Path(root).resolve()
    raw = read(OLD_INVENTORY, root)
    need(sha(raw) == OLD_INVENTORY_SHA)
    old = records(raw)
    need(len(old) == 162)
    source = read(PACKAGE, root)
    need(sha(source) == old[PACKAGE])
    module = types.ModuleType('verified31ar_for31as')
    module.__file__ = str(root / PACKAGE)
    exec(compile(source, module.__file__, 'exec'), module.__dict__)
    admitted = module.admitted(root)
    need(admitted[2] == old)
    return module, admitted


def admitted(root=ROOT):
    module, old = frozen(root)
    root = old[0]
    inventory = read(INVENTORY, root)
    pins = records(inventory)
    need(set(pins) == set(old[2]) | {OLD_INVENTORY} | OWN)
    need(all(pins[n] == v for n, v in old[2].items()))
    need(pins[OLD_INVENTORY] == OLD_INVENTORY_SHA)
    need(all(sha(read(name, root)) == digest for name, digest in pins.items()))
    need(read(INVENTORY, root) == inventory)
    return module, old, inventory, pins


def render(value, operation, original):
    before = original.render(value, operation)
    raw = original.profile.canonical(value)
    profile_bytes, profile_sha = len(raw), sha(raw)
    check = (NEW_HASH + '\nprofile_file31as() {\n'
       '  work_binding && safe_path "$1" && test -f "$1" &&\n'
       '  test "$(/usr/bin/stat -f %u:%Lp "$1")" = 0:600 &&\n'
       f'  test "$(/usr/bin/stat -f %z "$1")" = {profile_bytes} || return 1\n'
       '  PROFILE_DIGEST31AS=$(hash_file "$1") || return 1\n'
       f'  test "$PROFILE_DIGEST31AS" = {profile_sha}\n'
       '}')
    first = '/usr/bin/cmp -s ./expected-profile.json "$KIT/profile.json"'
    second = '/usr/bin/cmp -s ./expected-profile.json ./profile.json'
    probe = 'test "$(/usr/bin/id -u)" = 0 || fail'
    preflight = ('for REQUIRED31AS in ' + ' '.join(REQUIRED) + '; do\n'
        '  test -x "$REQUIRED31AS" || { printf \'{"schema":"ilinux31as-dependency-refusal-v1",'
        '"missing_tool":"%s","controller_run":false}\\n\' "$REQUIRED31AS" >&2; fail; }\n'
        'done\n' + probe)
    changes = ((OLD_HASH, check),
               (first, 'profile_file31as "$WORK/expected-profile.json" && profile_file31as "$KIT/profile.json"'),
               (second, 'profile_file31as "$WORK/profile.json"'),
               (probe, preflight))
    after = before
    for old, new in changes:
        need(after.count(old) == 1)
        after = after.replace(old, new, 1)
    reverse = after
    for old, new in reversed(changes):
        need(reverse.count(new) == 1)
        reverse = reverse.replace(new, old, 1)
    need(reverse == before and '/usr/bin/cmp' not in after and '/usr/bin/awk' not in after)
    return after


def page(value, original, operation=None):
    text = original.page(value, operation)
    for item in (('install', 'restore') if operation is None else (operation,)):
        old, new = html.escape(original.render(value, item)), html.escape(render(value, item, original))
        need(text.count(old) == 1)
        text = text.replace(old, new, 1)
    return text.replace('31AR guarded native transaction', '31AS Recovery profile verification').replace(
        '<h1>31AR: paired Recovery transaction</h1>', '<h1>31AS: paired Recovery profile verification</h1>')


def generated(original, value):
    return {'profile.json': original.profile.canonical(value),
            'install-paste.txt': render(value, 'install', original).encode(),
            'restore-paste.txt': render(value, 'restore', original).encode(),
            'recovery.html': page(value, original).encode(),
            'install.html': page(value, original, 'install').encode(),
            'restore.html': page(value, original, 'restore').encode()}


def prepare(output, root=ROOT):
    module, old, inventory, pins = admitted(root)
    root, original, value = old[0], old[4], old[5]
    target = module.checked_output(output, root)
    outputs = generated(original, value)
    need(admitted(root)[2:] == (inventory, pins))
    report = {'schema': 'ilinux31as-source-page-preparation-v1',
       'status': 'SOURCE_PROFILE_PAGE_ONLY', 'verified_source_count': len(pins),
       'retained_31AR_source_count': 162, 'source_inventory_sha256': sha(inventory),
       'retained_31AR_inventory_sha256': OLD_INVENTORY_SHA,
       'binary_delivery_verified_on_M1': False, 'helper_rebuild': False,
       'stage_run': False, 'controller_run': False, 'server_started': False,
       'native_ready': False, 'frozen_renderer_reversal_verified': True,
       'changes': ['fixed_utility_preflight', 'checked_hash_producer_builtin_parse',
                   'two_profile_size_and_SHA256_checks'],
       'output': {n: {'bytes': len(b), 'sha256': sha(b)} for n, b in outputs.items()}}
    target.mkdir(parents=True, mode=0o700)
    for name, data in outputs.items():
        with (target / name).open('xb') as stream:
            stream.write(data)
    (target / 'receipt.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    return report


def check_page(path, root=ROOT):
    module, old, inventory, pins = admitted(root)
    path = module.checked_output(path, old[0], exists=True)
    data = module.read_bounded(path, old[0], 256 * 1024)
    expected = generated(old[4], old[5])
    need(path.name in ('recovery.html', 'install.html', 'restore.html') and data == expected[path.name])
    need(admitted(root)[2:] == (inventory, pins))
    return data, {'schema': 'ilinux31as-page-v1', 'status': 'EXACT_PAGE_VERIFIED',
       'verified_source_count': len(pins), 'source_inventory_sha256': sha(inventory),
       'page_bytes': len(data), 'page_sha256': sha(data),
       'server_started': False, 'native_ready': False}


def route(raw, original):
    first = raw.split(b'\r\n', 1)[0].split(b' ')
    requested = first[1] if len(first) == 3 else None
    if requested == b'/31as':
        raw = raw.replace(b' /31as ', b' /31ar ', 1)
    code, head = original(raw)
    return (404, head) if code == 200 and requested not in (b'/', b'/31as') else (code, head)


def service(path, check_only, bind, port, seconds):
    data, result = check_page(path)
    if check_only:
        return result
    module, old, _, _ = admitted()
    server = module.old_module('serve', old[3], old[0])
    ar_request = server.request
    server.request = lambda raw: route(raw, lambda value: module.route_request(value, ar_request))
    with server.make_server(data, bind or '127.0.0.1', port or 0) as active:
        host, selected = active.server_address
        print(json.dumps(dict(result, status='FIXED_PAGE_SERVING', server_started=True,
              seconds=seconds or 600, url=f'http://{host}:{selected}/31as'), sort_keys=True), flush=True)
        server.serve(active, seconds or 600)
    return None


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('arguments refused')


def main(argv=None):
    parser = Parser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--prepare', action='store_true')
    modes.add_argument('--page', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--bind')
    parser.add_argument('--port', type=int)
    parser.add_argument('--seconds', type=int)
    try:
        args = parser.parse_args(argv)
        network = (args.bind, args.port, args.seconds)
        if not (args.prepare or args.page):
            need(args.output is None and not args.check_only and all(v is None for v in network))
            parser.print_help()
            return 0
        if args.prepare:
            need(args.output is not None and not args.check_only and all(v is None for v in network))
            result = prepare(args.output)
        else:
            need(args.output is None and (args.port is None or 0 <= args.port <= 65535))
            need(args.seconds is None or 1 <= args.seconds <= 1800)
            result = service(args.page, args.check_only, *network)
        if result is not None:
            print(json.dumps(result, sort_keys=True))
        return 0
    except KeyboardInterrupt:
        return 0
    except (ValueError, OSError, UnicodeError, KeyError, TypeError):
        print('{"status":"REFUSED","native_ready":false,"host_settings_changed":false}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

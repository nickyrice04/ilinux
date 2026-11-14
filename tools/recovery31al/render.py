# SPDX-License-Identifier: MIT
"""Original, inert renderer for one read-only 31AL Recovery diagnosis.

This module runs no shell or native operation. Frozen 31AK supplies only its
strict profile loader and canonical, held-working-directory identity guard.
"""
import hashlib
import html
import os
from pathlib import Path
import shlex
import stat
import types

ROOT = Path(__file__).resolve().parents[2]
FROZEN = {
    'tools/recovery31ak/render.py':
        'f835d99f7ae1a4cda9a9bed62eab5005c2b6ac598f73d651e67f1b21c7abc3e4',
}


def load_original(root=ROOT):
    """Compile only the pinned renderer, read through no-follow descriptors."""
    root = Path(root).resolve()
    name, digest = next(iter(FROZEN.items()))
    current = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parts = Path(name).parts
        for index, part in enumerate(parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if index < len(parts) - 1:
                flags |= os.O_DIRECTORY
            child = os.open(part, flags, dir_fd=current)
            os.close(current)
            current = child
        before = os.fstat(current)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 65536:
            raise ValueError('frozen source bound')
        data = bytearray()
        while len(data) <= 65536:
            piece = os.read(current, min(16384, 65537 - len(data)))
            if not piece:
                break
            data.extend(piece)
        after = os.fstat(current)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if (len(data) != before.st_size or
                any(getattr(before, key) != getattr(after, key) for key in fields) or
                hashlib.sha256(data).hexdigest() != digest):
            raise ValueError('frozen source identity')
    finally:
        os.close(current)
    module = types.ModuleType('recovery31al_frozen_paths')
    module.__file__ = str(root / name)
    exec(compile(bytes(data), module.__file__, 'exec'), module.__dict__)
    return module


original = load_original()
profile = original.profile
LAB, ORIGINAL, DATA = original.LAB, original.ORIGINAL, original.DATA
KIT = DATA + '/Users/Shared/iLinuxBoot/31al-diagnostic'


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('frozen work anchor')
    return text.replace(old, new, 1)


WORK_BLOCK = once(original.WORK_BLOCK, 'ilinux31ak.XXXXXX', 'ilinux31al.XXXXXX')
WORK_BLOCK = once(
    WORK_BLOCK,
    'cleanup() { if test "${WORK_READY:-0}" = 1 && work_binding; then /bin/rm -f ./profile.json ./candidate.macho ./m1n1-boot021.bin ./ilinux31aj-reader ./snapshot.json; work_binding && /bin/rmdir "$WORK"; fi; }',
    'cleanup() { { if test "${WORK_READY:-0}" = 1 && work_binding; then /bin/rm -f ./profile.json ./ilinux31aj-reader ./diagnostic.json; work_binding && /bin/rmdir "$WORK"; fi; } >/dev/null 2>&1; }')


def render(value):
    """Return one complete block; no installation or restoration mode exists."""
    value = profile.validate(value)
    item = value['files']['helper']
    rows = [
        '(', 'set +x', 'umask 077', 'export LC_ALL=C',
        'PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH',
        'SHELL_STAGE=INPUT_BINDING', 'HELPER_RC=null',
        'shell_status() { case "$SHELL_STAGE" in INPUT_BINDING|WORK_BINDING|OUTPUT_OPEN|HELPER_EXIT|OUTPUT_MISSING|VALIDATOR_FAILED|DIAGNOSTIC_CAPTURED) ;; *) SHELL_STAGE=INPUT_BINDING;; esac; case "$HELPER_RC" in null) ;; *[!0-9]*|\'\') HELPER_RC=null;; *) test "$HELPER_RC" -le 255 2>/dev/null || HELPER_RC=null;; esac; printf \'{"schema":"ilinux31al-shell-diagnostic-v1","stage":"%s","helper_exit":%s,"read_only":true,"writes_authorized":false,"native_ready":false,"identifiers_returned":false,"policy_values_returned":false}\\n\' "$SHELL_STAGE" "$HELPER_RC"; }',
        'fail() { shell_status; printf \'%s\\n\' "DIAGNOSTIC STOP. No boot or policy command was attempted by this block. Do not install, boot or retry. Preserve existing state, return to Macintosh HD/default and report the safe output above."; exit 2; }',
        'test "$(/usr/bin/id -u 2>/dev/null)" = 0 || fail',
        'LAB=' + shlex.quote(LAB), 'ORIGINAL=' + shlex.quote(ORIGINAL),
        'KIT=' + shlex.quote(KIT),
        'safe_path() { local p="$1"; while test "$p" != /; do test ! -L "$p" || return 1; p="${p%/*}"; test -n "$p" || p=/; done; }',
        'hash_file() { if test -x /sbin/sha256; then /sbin/sha256 -q "$1"; elif test -x /usr/bin/shasum; then /usr/bin/shasum -a 256 "$1" | /usr/bin/awk \'{print $1}\'; elif test -x /usr/bin/openssl; then /usr/bin/openssl dgst -sha256 "$1" | /usr/bin/awk \'{print $NF}\'; else return 1; fi; }',
        'check_file() { test -f "$1" && test ! -L "$1" && test "$(/usr/bin/stat -f %z "$1" 2>/dev/null)" = "$2" && test "$(hash_file "$1" 2>/dev/null)" = "$3"; }',
        'safe_path "$KIT" && safe_path "$LAB" && safe_path "$ORIGINAL" || fail',
        'test -d "$KIT" && test -d "$LAB/System/Library/CoreServices" && test -d "$ORIGINAL/System/Library/CoreServices" || fail',
        'test "$LAB" != "$ORIGINAL" || fail',
        'check_file "$KIT/profile.json" ' + str(len(profile.canonical(value))) + ' ' + profile.digest(value) + ' || fail',
        'check_file "$KIT/' + item['name'] + '" ' + str(item['bytes']) + ' ' + item['sha256'] + ' || fail',
        'SHELL_STAGE=WORK_BINDING', '{', WORK_BLOCK, '} 2>/dev/null',
        'work_binding 2>/dev/null || fail',
        '/bin/cp "$KIT/profile.json" ./profile.json 2>/dev/null || fail',
        'work_binding 2>/dev/null || fail',
        'check_file ./profile.json ' + str(len(profile.canonical(value))) + ' ' + profile.digest(value) + ' || fail',
        'work_binding 2>/dev/null || fail',
        '/bin/cp "$KIT/' + item['name'] + '" ./' + item['name'] + ' 2>/dev/null || fail',
        'work_binding 2>/dev/null || fail',
        'check_file ./' + item['name'] + ' ' + str(item['bytes']) + ' ' + item['sha256'] + ' || fail',
        'H="$WORK/ilinux31aj-reader"', 'P="$WORK/profile.json"',
        '/bin/chmod 700 ./ilinux31aj-reader 2>/dev/null || fail',
        'interrupted() { trap - INT TERM HUP; { exec 3>&-; } 2>/dev/null; HELPER_RC=130; SHELL_STAGE=HELPER_EXIT; fail; }',
        'trap interrupted INT TERM HUP',
        'SHELL_STAGE=WORK_BINDING', 'work_binding 2>/dev/null || fail',
        'SHELL_STAGE=OUTPUT_OPEN', 'set -C',
        'if { exec 3> ./diagnostic.json; } 2>/dev/null; then :; else set +C; fail; fi',
        'set +C', 'SHELL_STAGE=WORK_BINDING', 'work_binding 2>/dev/null || fail',
        '{ if "$H" --diagnose-snapshot --target-volume "$LAB" --original-volume "$ORIGINAL" --profile "$P" >&3; then HELPER_RC=0; else HELPER_RC=$?; fi; } 2>/dev/null',
        '{ exec 3>&-; } 2>/dev/null',
        'SHELL_STAGE=HELPER_EXIT', 'shell_status',
        'SHELL_STAGE=WORK_BINDING', 'work_binding 2>/dev/null || fail',
        'SHELL_STAGE=OUTPUT_MISSING',
        'test -f ./diagnostic.json && test ! -L ./diagnostic.json && test -s ./diagnostic.json || fail',
        'SHELL_STAGE=VALIDATOR_FAILED',
        '{ "$H" --validate-diagnostic "$WORK/diagnostic.json" --profile "$P"; } 2>/dev/null || fail',
        'case "$HELPER_RC" in 0|2) ;; *) SHELL_STAGE=HELPER_EXIT; fail;; esac',
        'SHELL_STAGE=DIAGNOSTIC_CAPTURED', 'shell_status',
        'printf \'%s\\n\' "SAFE DIAGNOSTIC SHOWN ABOVE. Capture it from Terminal before leaving. No install, restoration, default selection, security change or native boot was performed. Return to Macintosh HD/default and report; a passing admission record is not permission to install or boot."',
        'exit "$HELPER_RC"', ')',
    ]
    return '\n'.join(rows) + '\n'


def page(value):
    """Return an inert one-box page; serving or pasting is a separate action."""
    return ('<!doctype html><meta charset="utf-8"><title>31AL read-only diagnosis</title>'
            '<style>body{font:18px system-ui;max-width:80em;margin:2em auto;padding:0 1em}'
            'textarea{box-sizing:border-box;width:100%;height:30em;padding:1em;'
            'font:16px/1.5 ui-monospace,monospace;white-space:pre;resize:vertical;'
            'color:#111;background:#f6f6f6;border:1px solid #888}</style>'
            '<h1>31AL: read-only Recovery diagnosis</h1>'
            '<p>Offline preparation only. Use only after the matching kit has been '
            'reviewed and a read-only Recovery diagnostic is explicitly authorized. '
            'This block cannot install or restore a boot object, change policy or '
            'select Startup Disk. It performs no native boot.</p>'
            '<p>Click inside the box, press <strong>Command+A</strong>, then '
            '<strong>Command+C</strong>. Quit the browser, open Utilities Terminal '
            'and paste once. Authenticate only in the system prompt. Capture the '
            'safe JSON visible in Terminal before leaving; no private snapshot '
            'is displayed or persisted.</p>'
            '<label for="diagnostic-block">One read-only diagnostic block</label>'
            '<textarea id="diagnostic-block" readonly spellcheck="false" wrap="off">' +
            html.escape(render(value)) + '</textarea>')

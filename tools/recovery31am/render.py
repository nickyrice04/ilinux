# SPDX-License-Identifier: MIT
"""Inert one-box renderer for conditional read-only Preboot preparation.

The frozen 31AL renderer supplies its strict profile and held-CWD flow. This
module changes only the new kit/work names, companion entrypoints and messages;
rendering does not stage, mount, serve or execute anything.
"""
import hashlib
import html
import os
from pathlib import Path
import stat
import types

ROOT = Path(__file__).resolve().parents[2]
FROZEN = {'tools/recovery31al/render.py':
          '12dad604a2aa2c21789e891da67ca174165940111f7965f43f88b85d845a641f'}


def load_original(root=ROOT):
    root = Path(root).resolve()
    name, expected = next(iter(FROZEN.items()))
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
            raise ValueError('frozen renderer bound')
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
                hashlib.sha256(data).hexdigest() != expected):
            raise ValueError('frozen renderer identity')
    finally:
        os.close(current)
    module = types.ModuleType('recovery31am_frozen_renderer')
    module.__file__ = str(root / name)
    exec(compile(bytes(data), module.__file__, 'exec'), module.__dict__)
    return module


original = load_original()
profile = original.profile
LAB, ORIGINAL, DATA = original.LAB, original.ORIGINAL, original.DATA
KIT = DATA + '/Users/Shared/iLinuxBoot/31am-diagnostic'


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('frozen renderer anchor')
    return text.replace(old, new, 1)


WORK_BLOCK = once(original.WORK_BLOCK, 'ilinux31al.XXXXXX', 'ilinux31am.XXXXXX')


def render(value):
    """Return one complete block; the native companion owns mount cleanup."""
    text = original.render(value)
    text = once(text, original.WORK_BLOCK, WORK_BLOCK)
    text = once(text, original.KIT, KIT)
    text = once(text, 'ilinux31al-shell-diagnostic-v1', 'ilinux31am-shell-result-v1')
    text = once(text,
        '"read_only":true,"writes_authorized":false,"native_ready":false',
        '"preboot_write_requested":false,"boot_settings_changed":false,'
        '"security_settings_changed":false,"native_ready":false')
    text = once(text,
        '"$H" --diagnose-snapshot --target-volume "$LAB" --original-volume "$ORIGINAL" --profile "$P" >&3',
        '"$H" --preboot-diagnose --target-volume "$LAB" --original-volume "$ORIGINAL" --profile "$P" --scratch "$WORK" >&3')
    text = once(text, '--validate-diagnostic', '--validate-result')
    text = once(text,
        'DIAGNOSTIC STOP. No boot or policy command was attempted by this block. Do not install, boot or retry. Preserve existing state, return to Macintosh HD/default and report the safe output above.',
        'CONDITIONAL DIAGNOSTIC STOP. A Preboot mount may remain if the helper was interrupted or cleanup refused; read-only verification may be incomplete. Do not install, boot, retry or clean up a mount by hand. Return to Macintosh HD/default and report the safe output above.')
    text = once(text,
        'SAFE DIAGNOSTIC SHOWN ABOVE. Capture it from Terminal before leaving. No install, restoration, default selection, security change or native boot was performed. Return to Macintosh HD/default and report; a passing admission record is not permission to install or boot.',
        'VALIDATED PREBOOT RESULT SHOWN ABOVE. Record the mount and cleanup fields and any diagnostic refusal. Cleanup failure or interruption may leave a mount present; check the explicit read-only verification field. No install, restoration, default selection, security change or native boot was performed. Return to Macintosh HD/default and report; a passing diagnostic is not permission to install or boot.')
    return text


def page(value):
    return ('<!doctype html><meta charset="utf-8"><title>31AM conditional Preboot check</title>'
            '<style>body{font:18px system-ui;max-width:80em;margin:2em auto;padding:0 1em}'
            'textarea{box-sizing:border-box;width:100%;height:30em;padding:1em;'
            'font:16px/1.5 ui-monospace,monospace;white-space:pre;resize:vertical;'
            'color:#111;background:#f6f6f6;border:1px solid #888}</style>'
            '<h1>31AM: conditional read-only Preboot check</h1>'
            '<p>Offline preparation only. Use only after review and explicit '
            'authorization for the conditional read-only mount and Recovery visit. '
            'The helper leaves an existing valid mount alone. It may create one '
            'temporary read-only Preboot mount when its guarded conditions admit '
            'that operation, then run the existing read-only diagnostic and '
            'attempt only its own mount cleanup. No Preboot filesystem writes, install, '
            'restoration, security setting or native boot is requested.</p>'
            '<p>Click inside the box, press <strong>Command+A</strong> and '
            '<strong>Command+C</strong>. Quit the browser, open Utilities Terminal '
            'and paste once. Keep credentials in the system prompt. Capture the '
            'validated mount, cleanup and diagnostic result visible in Terminal '
            'before leaving. A cleanup failure or interruption remains a stop; '
            'do not retry or manually alter mounts.</p>'
            '<label for="diagnostic-block">One conditional Preboot block</label>'
            '<textarea id="diagnostic-block" readonly spellcheck="false" wrap="off">' +
            html.escape(render(value)) + '</textarea>')

# SPDX-License-Identifier: MIT
"""One-box 31AP wrapper around the exact successful 31AM shell flow.

Only kit name, shell schema and page labels change.  Rendering is inert;
the admitted native helper owns the conditional read-only operation and cleanup.
"""
import hashlib
import html
import os
from pathlib import Path
import stat
import types

ROOT = Path(__file__).resolve().parents[2]
FROZEN = {'tools/recovery31am/render.py':
          '7e0b9d2ffb1cdeae54f6c1e6303c5f3924e0a60acde4e934507ab026540b1bf4'}


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
    module = types.ModuleType('recovery31ap_frozen_renderer')
    module.__file__ = str(root / name)
    exec(compile(bytes(data), module.__file__, 'exec'), module.__dict__)
    return module


original = load_original()
profile = original.profile
LAB, ORIGINAL, DATA = original.LAB, original.ORIGINAL, original.DATA
KIT = DATA + '/Users/Shared/iLinuxBoot/31ap-diagnostic'


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('frozen renderer anchor')
    return text.replace(old, new, 1)


# The frozen native scratch_open contract requires the ilinux31am. prefix.
# mktemp still creates a fresh directory; retaining this prefix reuses no state.
WORK_BLOCK = original.WORK_BLOCK


def render(value):
    text = original.render(value)
    text = once(text, original.KIT, KIT)
    return once(text, 'ilinux31am-shell-result-v1', 'ilinux31ap-shell-result-v1')


def page(value):
    text = original.page(value)
    text = once(text, html.escape(original.render(value)), html.escape(render(value)))
    text = once(text, '<title>31AM conditional Preboot check</title>',
                '<title>31AP typed-policy Preboot check</title>')
    return once(text, '<h1>31AM: conditional read-only Preboot check</h1>',
                '<h1>31AP: typed-policy conditional read-only Preboot check</h1>')

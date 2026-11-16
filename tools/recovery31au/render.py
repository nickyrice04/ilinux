# SPDX-License-Identifier: MIT
"""Reversible namespace adapter over frozen AR rendering and AS hash fixes."""
import hashlib
import html
import types

SOURCE = 'tools/recovery31ar/render.py'
SOURCE_SHA = 'c1fa12292fcb0225aeb16e338b7e7504adb52762d67de257a114c52dc617c159'
KIT = '/Volumes/iLinux Boot Lab - Data/Users/Shared/iLinuxBoot/31au-kit'
STATE = '/Volumes/iLinux Boot Lab - Data/private/var/db/ilinux31au-state'


def derive(data, profile_source, profile, as_module, root):
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA:
        raise ValueError('frozen renderer source refused')
    before = data.decode('utf-8')
    # The old profile source is supplied from the already verified source
    # snapshot instead of reopening a path while executing the renderer.
    changes = (
        ('data = (ROOT / PROFILE_SOURCE).read_bytes()', 'data = FROZEN_PROFILE_SOURCE'),
        ('31ar', '31au'),
        ('31AR', '31AU'),
        ('ilinux31aj-reader', 'ilinux31au-reader'),
    )
    after = before
    counts = []
    for old, new in changes:
        count = after.count(old)
        if not count:
            raise ValueError('renderer selector absent')
        counts.append(count)
        after = after.replace(old, new)
    reverse = after
    for (old, new), count in reversed(tuple(zip(changes, counts))):
        if reverse.count(new) != count:
            raise ValueError('renderer selector collision')
        reverse = reverse.replace(new, old)
    if reverse != before:
        raise ValueError('renderer reversal refused')
    original = types.ModuleType('verified31au_renderer_base')
    original.__file__ = str(root / SOURCE)
    original.FROZEN_PROFILE_SOURCE = profile_source
    exec(compile(after, original.__file__, 'exec'), original.__dict__)
    original.profile = profile
    if original.KIT != KIT or original.STATE != STATE:
        raise ValueError('renderer namespace refused')

    class Renderer:
        def __init__(self):
            self.profile, self.KIT, self.STATE = profile, KIT, STATE
            self.original = original

        def render(self, value, operation):
            fixed = as_module.render(value, operation, original)
            # Only finite shell variables/dependency labels are renamed here.
            # AS itself still verifies all four bootstrap changes in reverse.
            return fixed.replace('31AS', '31AU').replace('31as', '31au')

        def page(self, value, operation=None):
            text = original.page(value, operation)
            operations = ('install', 'restore') if operation is None else (operation,)
            for item in operations:
                old, new = html.escape(original.render(value, item)), html.escape(self.render(value, item))
                if text.count(old) != 1:
                    raise ValueError('whole operation box refused')
                text = text.replace(old, new, 1)
            return text.replace('31AU guarded native transaction',
                                '31AU guarded diagnostic transaction').replace(
                '<h1>31AU: paired Recovery transaction</h1>',
                '<h1>31AU: paired Recovery diagnostic transaction</h1>')

    return Renderer()

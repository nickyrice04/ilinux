#!/usr/bin/env python3
"""Apply the original final-copy experiment to one pinned Hyprland source tree."""
import hashlib
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
source = pathlib.Path(__file__).resolve().parent
pins = {
    'src/render/OpenGL.cpp': '7bbf0f8f6714cc7ed7b6d17dbc670d75f5f17db54637def8d8b322ac3b873d58',
    'src/config/values/ConfigValues.cpp': 'a76f05079454e1f6d4402144e1673cc1cb890d285fbeb947d5afdb004ad97754',
}
for name, digest in pins.items():
    if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
        raise ValueError('upstream source pin differs: ' + name)
p = root / 'src/render/OpenGL.cpp'
text = p.read_text()
assert text.count('void CHyprOpenGLImpl::end() {') == 1
assert 'ILinuxCopy31' not in text
text = text.replace('void CHyprOpenGLImpl::end() {', '#include "ILinuxCopy31.hpp"\n\nvoid CHyprOpenGLImpl::end() {')
text = text.replace('        const auto TEX = g_pHyprRenderer->m_renderData.currentFB->getTexture();',
                    '        const auto COPY_SOURCE = g_pHyprRenderer->m_renderData.currentFB;\n'
                    '        const auto TEX = COPY_SOURCE->getTexture();', 1)
old = '''        if LIKELY (!PRIMITIVE_BLOCKED || g_pHyprRenderer->m_renderMode != RENDER_MODE_NORMAL)
            renderTexturePrimitive(TEX, monbox);'''
new = '''        if (ILinuxCopy31::copy(COPY_SOURCE, monbox, PRIMITIVE_BLOCKED, m_fakeFrame, g_pHyprRenderer->m_renderMode == RENDER_MODE_NORMAL, [&] { renderTexturePrimitive(TEX, monbox); })) {
            // Original iLinux experiment: verified final copy completed.
        } else if LIKELY (!PRIMITIVE_BLOCKED || g_pHyprRenderer->m_renderMode != RENDER_MODE_NORMAL)
            renderTexturePrimitive(TEX, monbox);'''
assert text.count(old) == 1
p.write_text(text.replace(old, new))
(root / 'src/render/ILinuxCopy31.hpp').write_bytes((source / 'ILinuxCopy31.hpp').read_bytes())
p = root / 'src/config/values/ConfigValues.cpp'
text = p.read_text()
anchor = '        MS<Bool>("debug:gl_debugging",'
assert text.count(anchor) == 1
p.write_text(text.replace(anchor, '        MS<Int>("debug:ilinux_copy31", "iLinux opt-in verified final framebuffer copy experiment.", 0, {.min = 0, .max = 1}),\n' + anchor))
print('copy31 patch applied; default off')

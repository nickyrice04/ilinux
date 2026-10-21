#!/usr/bin/env python3
"""Instrument only the pinned original compositor; refuse copy31/other edits."""
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent

SCOPES = {
    'src/render/Renderer.cpp': [
        ('void IHyprRenderer::renderMonitor(PHLMONITOR pMonitor, bool commit) {', 'monitor'),
        ('bool IHyprRenderer::beginRender(PHLMONITOR pMonitor, CRegion& damage, eRenderMode mode, SP<IHLBuffer> buffer, SP<IFramebuffer> fb, bool simple) {', 'begin'),
        ('bool IHyprRenderer::commitPendingAndDoExplicitSync(PHLMONITOR pMonitor) {', 'output_commit'),
    ],
    'src/render/GLRenderer.cpp': [
        ('void CHyprGLRenderer::endRender(const std::function<void()>& renderingDoneCallback) {', 'end_render'),
    ],
    'src/render/OpenGL.cpp': [
        ('void CHyprOpenGLImpl::end() {', 'final_copy'),
        ('void CHyprOpenGLImpl::renderTextureInternal(SP<ITexture> tex, const CBox& box, const STextureRenderData& data) {', 'texture'),
        ('void CHyprOpenGLImpl::renderTexturePrimitive(SP<ITexture> tex, const CBox& box) {', 'primitive'),
    ],
    'src/render/pass/Pass.cpp': [('CRegion CRenderPass::render(const CRegion& damage_) {', 'scene')],
    'src/managers/input/InputManager.cpp': [
        ('void CInputManager::onKeyboardKey(const IKeyboard::SKeyEvent& event, SP<IKeyboard> pKeyboard) {', 'input'),
    ],
    'src/managers/KeybindManager.cpp': [('bool CKeybindManager::onKeyEvent(std::any event, SP<IKeyboard> pKeyboard) {', 'keybind')],
}


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('anchor missing or ambiguous: ' + old[:100])
    return text.replace(old, new)


def apply(root):
    pins = json.loads((HERE / 'source-pins.json').read_text())
    # Validate everything and prepare all replacements before modifying anything.
    texts = {}
    for f, sha in pins.items():
        data = (root / f).read_bytes()
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError('source pin mismatch: ' + f)
        text = data.decode()
        header = os.path.relpath(root / 'src/helpers/ILinuxTimeline.hpp', (root / f).parent)
        text = '#include "' + header + '"\n' + text
        for anchor, tag in SCOPES.get(f, []):
            args = ', int64_t(box.w), int64_t(box.h)' if tag in ('texture', 'primitive') else ''
            if tag == 'input':
                args = ', event.timeMs, int64_t(event.state)'
            text = once(text, anchor, anchor + '\n    ILinuxTimeline::Scope ilinuxScope("' + tag + '"' + args + ');')
        if f == 'src/render/GLRenderer.cpp':
            text = once(text, '            glFinish();', '            { ILinuxTimeline::Scope waitScope("finish_wait"); glFinish(); }')
            anchor='    g_pHyprRenderer->m_renderData.damage = m_renderPass.render(g_pHyprRenderer->m_renderData.damage);'
            text=once(text,anchor,anchor+'\n    const char* drainEnv = std::getenv("ILINUX_LATENCY_DRAIN");\n'
                      '    const bool traceDrain = ILinuxTimeline::getWriter().file && drainEnv && std::strcmp(drainEnv, "1") == 0;\n'
                      '    if (traceDrain) { ILinuxTimeline::Scope drainScope("scene_drain"); glFinish(); }')
            anchor='    if (m_renderMode == RENDER_MODE_FULL_FAKE)'
            text=once(text,anchor,'    if (traceDrain) { ILinuxTimeline::Scope drainScope("final_drain"); glFinish(); }\n\n'+anchor)
        if f == 'src/render/pass/Pass.cpp':
            anchor = '        g_pHyprRenderer->draw(el.element, el.elementDamage);'
            text = once(text, anchor, '        {\n            const auto bounds = el.elementDamage.getExtents();\n'
                        '            ILinuxTimeline::Scope drawScope("element", int64_t(bounds.w), int64_t(bounds.h));\n' + anchor + '\n        }')
        if f == 'src/protocols/core/Compositor.cpp':
            anchor = '    m_resource->setCommit([this](CWlSurface* r) {'
            text = once(text, anchor, anchor + '\n        pid_t tracePid = 0;\n'
                        '        if (ILinuxTimeline::getWriter().file) wl_client_get_credentials(m_client, &tracePid, nullptr, nullptr);\n'
                        '        ILinuxTimeline::Scope commitScope(m_pending.buffer ? "surface_buffer" : "surface_commit", tracePid, 0);')
        texts[f] = text
    for f, text in texts.items():
        (root / f).write_text(text)
    (root / 'src/helpers/ILinuxTimeline.hpp').write_bytes((HERE / 'ILinuxTimeline.hpp').read_bytes())
    print('original compositor timeline applied; off unless ILINUX_LATENCY_TRACE=1')


if __name__ == '__main__':
    apply(Path(sys.argv[1]))

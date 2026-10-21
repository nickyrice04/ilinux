// SPDX-License-Identifier: BSD-3-Clause
// Original, opt-in experiment for Hyprland efb50993780079460b0cbed1363e2166a2de1d9f.
// Included by OpenGL.cpp. No Apple code or hardware register access.
#pragma once

#include <array>
#include <cstdio>
#include <set>
#include <vector>

namespace ILinuxCopy31 {
// projectBoxToTarget is row-major. fullVerts has position == texture coordinates.
// A negative Y scale therefore needs a vertically reversed source rectangle.
inline int orientation(const float* m) {
    const std::array<float, 9> normal = {2, 0, -1, 0, 2, -1, 0, 0, 1};
    const std::array<float, 9> flip = {2, 0, -1, 0, -2, 1, 0, 0, 1};
    bool n = true, f = true;
    for (size_t i = 0; i < 9; ++i) {
        n &= m[i] == normal[i];
        f &= m[i] == flip[i];
    }
    return n ? 1 : f ? -1 : 0;
}

inline bool rgb8(uint32_t f) {
    return f == DRM_FORMAT_ARGB8888 || f == DRM_FORMAT_XRGB8888;
}

// Call only in end(), immediately before the primitive final-copy branch.
// Every new source/destination framebuffer pair is compared byte-for-byte with
// that branch on its first eligible frame. A mismatch permanently falls back.
template <typename Draw>
bool copy(const SP<Render::IFramebuffer>& source, const CBox& box, bool primitiveBlocked,
          bool fake, bool normalMode, Draw original) {
    static auto enabled = CConfigValue<Config::INTEGER>("debug:ilinux_copy31");
    static bool failed = false;
    static FILE* trace = []() -> FILE* {
        if (geteuid() != 1000)
            return nullptr;
        const int fd = open("/run/user/1000/ilinux-copy31.log", O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, 0600);
        if (fd < 0)
            return nullptr;
        FILE* stream = fdopen(fd, "w");
        if (!stream) { close(fd); return nullptr; }
        setvbuf(stream, nullptr, _IOLBF, 0);
        return stream;
    }();
    if (!trace) {
        failed = true;
        return false;
    }
    static std::set<std::pair<GLuint, GLuint>> verified;
    static unsigned calls = 0, copies = 0;
    static int previousMode = -1;
    auto& r = g_pHyprRenderer->m_renderData;
    auto dst = r.outFB;
    const auto matrix = g_pHyprRenderer->projectBoxToTarget(box);
    const int dir = orientation(matrix.getMatrix().data());
    const bool eligible = !failed && !primitiveBlocked && !fake && source && dst && source != dst &&
        normalMode && r.projectionType == Render::RPT_MONITOR &&
        r.pMonitor->m_transform == WL_OUTPUT_TRANSFORM_NORMAL && r.mouseZoomFactor == 1.f &&
        (!r.renderModif.enabled || r.renderModif.modifs.empty()) && dir != 0 &&
        source->m_size == Vector2D(3456, 2160) && dst->m_size == source->m_size &&
        box == CBox(0, 0, 3456, 2160) && rgb8(source->m_drmFormat) && rgb8(dst->m_drmFormat) &&
        !source->getMirrorTexture() && !dst->getMirrorTexture();
    if (++calls == 1 || calls % 120 == 0 || previousMode != *enabled)
        std::fprintf(trace, "ILINUX_COPY31 calls=%u copies=%u enabled=%d eligible=%d cm_or_shader=%d dir=%d srcfmt=%u dstfmt=%u\n",
                     calls, copies, static_cast<int>(*enabled), eligible, primitiveBlocked, dir,
                     source ? source->m_drmFormat : 0, dst ? dst->m_drmFormat : 0);
    previousMode = *enabled;
    if (!*enabled || !eligible || r.damage.empty())
        return false;
    static const bool software = [] {
        auto renderer = reinterpret_cast<const char*>(glGetString(GL_RENDERER));
        return renderer && std::string(renderer).starts_with("llvmpipe (");
    }();
    if (!software)
        return false;
    const GLuint srcID = GLFB(source)->getFBID(), dstID = GLFB(dst)->getFBID();
    if (!srcID || !dstID || srcID == dstID)
        return false;
    GLint readID = 0, drawID = 0;
    glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING, &readID);
    glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING, &drawID);
    if (static_cast<GLuint>(drawID) != dstID)
        return false;
    // Match the normal helper's final scissor state; rectangles themselves bound
    // the writes, leaving undamaged pixels and buffer-age accounting untouched.
    auto blit = [&] {
        g_pHyprOpenGL->scissor(nullptr);
        glBindFramebuffer(GL_READ_FRAMEBUFFER, srcID);
        r.damage.forEachRect([&](const auto& rect) {
            const int x1 = std::clamp<int>(rect.x1, 0, 3456), x2 = std::clamp<int>(rect.x2, 0, 3456);
            const int y1 = std::clamp<int>(rect.y1, 0, 2160), y2 = std::clamp<int>(rect.y2, 0, 2160);
            if (x2 > x1 && y2 > y1)
                glBlitFramebuffer(x1, dir == 1 ? y1 : 2160 - y1, x2, dir == 1 ? y2 : 2160 - y2,
                                  x1, y1, x2, y2, GL_COLOR_BUFFER_BIT, GL_NEAREST);
        });
        glBindFramebuffer(GL_READ_FRAMEBUFFER, readID);
    };
    const auto pair = std::make_pair(srcID, dstID);
    if (!verified.contains(pair)) {
        // Bound startup cost and fail closed if the buffer pool is unexpected.
        if (verified.size() >= 8) { failed = true; return false; }
        GLint pack = 0, row = 0, skipRows = 0, skipPixels = 0, pbo = 0;
        glGetIntegerv(GL_PACK_ALIGNMENT, &pack);
        glGetIntegerv(GL_PACK_ROW_LENGTH, &row);
        glGetIntegerv(GL_PACK_SKIP_ROWS, &skipRows);
        glGetIntegerv(GL_PACK_SKIP_PIXELS, &skipPixels);
        glGetIntegerv(GL_PIXEL_PACK_BUFFER_BINDING, &pbo);
        glBindBuffer(GL_PIXEL_PACK_BUFFER, 0);
        glPixelStorei(GL_PACK_ALIGNMENT, 1);
        glPixelStorei(GL_PACK_ROW_LENGTH, 0);
        glPixelStorei(GL_PACK_SKIP_ROWS, 0);
        glPixelStorei(GL_PACK_SKIP_PIXELS, 0);
        std::vector<uint8_t> a(3456 * 2160 * 4), b(a.size());
        original();
        glBindFramebuffer(GL_READ_FRAMEBUFFER, dstID);
        glReadPixels(0, 0, 3456, 2160, GL_RGBA, GL_UNSIGNED_BYTE, a.data());
        blit();
        glBindFramebuffer(GL_READ_FRAMEBUFFER, dstID);
        glReadPixels(0, 0, 3456, 2160, GL_RGBA, GL_UNSIGNED_BYTE, b.data());
        const GLenum error = glGetError();
        glBindFramebuffer(GL_READ_FRAMEBUFFER, readID);
        glPixelStorei(GL_PACK_ALIGNMENT, pack);
        glPixelStorei(GL_PACK_ROW_LENGTH, row);
        glPixelStorei(GL_PACK_SKIP_ROWS, skipRows);
        glPixelStorei(GL_PACK_SKIP_PIXELS, skipPixels);
        glBindBuffer(GL_PIXEL_PACK_BUFFER, pbo);
        const bool same = a == b && error == GL_NO_ERROR;
        std::fprintf(trace, "ILINUX_COPY31 parity=%d gl_error=%u pair_count=%zu\n", same, error, verified.size() + 1);
        if (!same) {
            failed = true;
            original();
            return true;
        }
        verified.insert(pair);
    } else {
        blit();
        const GLenum error = glGetError();
        if (error != GL_NO_ERROR) {
            failed = true;
            std::fprintf(trace, "ILINUX_COPY31 runtime_error=%u fallback=1\n", error);
            original();
            return true;
        }
    }
    ++copies;
    return true;
}
} // namespace ILinuxCopy31

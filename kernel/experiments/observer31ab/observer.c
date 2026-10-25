/* SPDX-License-Identifier: MIT */
#include "observer.h"

#define PAGE UINT64_C(0x4000)

static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static uint64_t le64(const uint8_t *p)
{
    return (uint64_t)le32(p) | (uint64_t)le32(p + 4) << 32;
}

static int end_of(uint64_t base, uint64_t bytes, uint64_t *end)
{
    if (!bytes || base > UINT64_MAX - bytes) return 0;
    *end = base + bytes;
    return 1;
}

static int overlap(uint64_t a, uint64_t ae, uint64_t b, uint64_t be)
{
    return a < be && b < ae;
}

static enum obs31_status table_valid(const struct obs31_table *t)
{
    uint32_t i, j;
    if (!t) return OBS31_ARGUMENT;
    if (!t->count || t->count > OBS31_RANGE_MAX) return OBS31_SIZE;
    for (i = 0; i < t->count; ++i) {
        const struct obs31_range *r = &t->ranges[i];
        uint64_t pe, ve;
        if (r->physical % PAGE || r->virtual_address % PAGE ||
            r->bytes % PAGE || r->bytes / PAGE > UINT32_MAX ||
            !end_of(r->physical, r->bytes, &pe) ||
            !end_of(r->virtual_address, r->bytes, &ve)) return OBS31_RANGE;
        for (j = 0; j < i; ++j) {
            const struct obs31_range *q = &t->ranges[j];
            if (overlap(r->physical, pe, q->physical, q->physical + q->bytes) ||
                overlap(r->virtual_address, ve, q->virtual_address,
                        q->virtual_address + q->bytes)) return OBS31_OVERLAP;
        }
    }
    return OBS31_OK;
}

enum obs31_status obs31_table_decode(const uint8_t *snapshot, size_t bytes,
    uint32_t count, struct obs31_table *output)
{
    struct obs31_table t = {0};
    enum obs31_status status;
    uint32_t i;
    if (!snapshot || !output) return OBS31_ARGUMENT;
    if (!count || count > OBS31_RANGE_MAX ||
        bytes != (size_t)count * OBS31_RANGE_BYTES) return OBS31_SIZE;
    t.count = count;
    for (i = 0; i < count; ++i) {
        const uint8_t *p = snapshot + (size_t)i * OBS31_RANGE_BYTES;
        t.ranges[i].physical = le64(p);
        t.ranges[i].virtual_address = le64(p + 8);
        t.ranges[i].bytes = (uint64_t)le32(p + 16) << 14;
        /* The remaining four bytes are opaque, not assumed to be zero. */
    }
    status = table_valid(&t);
    if (status != OBS31_OK) return status;
    *output = t;
    return OBS31_OK;
}

static enum obs31_status translate_valid(const struct obs31_table *t,
    uint64_t physical, uint64_t bytes, uint64_t *output)
{
    uint64_t end, cursor = physical, first = 0, expected = 0;
    if (!end_of(physical, bytes, &end)) return OBS31_RANGE;
    while (cursor < end) {
        uint32_t i;
        const struct obs31_range *r = NULL;
        uint64_t va, next;
        for (i = 0; i < t->count; ++i) {
            if (cursor >= t->ranges[i].physical &&
                cursor - t->ranges[i].physical < t->ranges[i].bytes) {
                r = &t->ranges[i];
                break;
            }
        }
        if (!r) return OBS31_UNMAPPED;
        va = r->virtual_address + (cursor - r->physical);
        if (!va) return OBS31_UNMAPPED;
        if (cursor == physical) first = va;
        else if (va != expected) return OBS31_NONCONTIGUOUS;
        next = r->physical + r->bytes;
        if (next > end) next = end;
        expected = va + (next - cursor); /* Bounded by validated range end. */
        cursor = next;
    }
    *output = first;
    return OBS31_OK;
}

enum obs31_status obs31_translate(const struct obs31_table *table,
    uint64_t physical, uint64_t bytes, uint64_t *virtual_address)
{
    enum obs31_status status;
    if (!virtual_address) return OBS31_ARGUMENT;
    status = table_valid(table);
    if (status != OBS31_OK) return status;
    return translate_valid(table, physical, bytes, virtual_address);
}

static enum obs31_status video_valid(const struct obs31_video *v)
{
    uint64_t end, span;
    unsigned depth;
    if (!v) return OBS31_ARGUMENT;
    depth = (unsigned)(v->depth_word & 0xff);
    if (depth != 30 && depth != 32) return OBS31_FORMAT;
    if (!v->physical_base || v->physical_base % 4 ||
        !v->width || !v->height || !v->row_bytes || v->row_bytes % 4 ||
        v->width > UINT64_MAX / 4 || v->row_bytes < v->width * 4 ||
        v->height > UINT64_MAX / v->row_bytes) return OBS31_RANGE;
    span = v->height * v->row_bytes;
    if (!end_of(v->physical_base, span, &end)) return OBS31_RANGE;
    return OBS31_OK;
}

enum obs31_status obs31_video_decode(const uint8_t *prefix, size_t bytes,
    struct obs31_video *output)
{
    struct obs31_video v;
    enum obs31_status status;
    if (!prefix || !output) return OBS31_ARGUMENT;
    if (bytes != OBS31_VIDEO_PREFIX_BYTES) return OBS31_SIZE;
    if (prefix[0] != 2 || prefix[1] != 0 || prefix[2] != 2 || prefix[3] != 0)
        return OBS31_FORMAT;
    v.physical_base = le64(prefix + 40) & ~UINT64_C(3);
    v.display = le64(prefix + 48);
    v.row_bytes = le64(prefix + 56);
    v.width = le64(prefix + 64);
    v.height = le64(prefix + 72);
    v.depth_word = le64(prefix + 80);
    status = video_valid(&v);
    if (status != OBS31_OK) return status;
    *output = v;
    return OBS31_OK;
}

enum obs31_status obs31_marker_plan(const struct obs31_video *video,
    const struct obs31_table *table, uint64_t x, uint64_t y,
    uint32_t width, uint32_t height, struct obs31_marker *output)
{
    struct obs31_marker m = {0};
    enum obs31_status status;
    uint32_t row;
    if (!output) return OBS31_ARGUMENT;
    status = video_valid(video);
    if (status != OBS31_OK) return status;
    status = table_valid(table);
    if (status != OBS31_OK) return status;
    if (!width || width > OBS31_MARKER_WIDTH_MAX ||
        !height || height > OBS31_MARKER_HEIGHT_MAX ||
        width > video->width || height > video->height ||
        x > video->width - width || y > video->height - height)
        return OBS31_BOUNDS;
    m.width = width;
    m.height = height;
    m.depth = (uint32_t)(video->depth_word & 0xff);
    for (row = 0; row < height; ++row) {
        m.rows[row].physical = video->physical_base +
            (y + row) * video->row_bytes + x * 4;
        m.rows[row].bytes = (uint64_t)width * 4;
        status = translate_valid(table, m.rows[row].physical,
            m.rows[row].bytes, &m.rows[row].virtual_address);
        if (status != OBS31_OK) return status;
    }
    *output = m;
    return OBS31_OK;
}

enum obs31_status obs31_paint_ram(const struct obs31_marker *m,
    uint64_t ram_virtual_base, uint8_t *ram, size_t ram_bytes,
    uint32_t foreground, uint32_t background)
{
    uint64_t ram_end;
    uint32_t row, col;
    if (!m || !ram) return OBS31_ARGUMENT;
    if (!m->width || m->width > OBS31_MARKER_WIDTH_MAX || !m->height ||
        m->height > OBS31_MARKER_HEIGHT_MAX || (m->depth != 30 && m->depth != 32))
        return OBS31_FORMAT;
    if (m->depth == 30 && ((foreground | background) >> 30)) return OBS31_FORMAT;
    if (!end_of(ram_virtual_base, ram_bytes, &ram_end)) return OBS31_RANGE;
    for (row = 0; row < m->height; ++row) {
        const struct obs31_row *r = &m->rows[row];
        uint64_t end;
        uint32_t prior;
        if (!r->virtual_address || r->virtual_address % 4 ||
            r->bytes != (uint64_t)m->width * 4 ||
            !end_of(r->virtual_address, r->bytes, &end) ||
            r->virtual_address < ram_virtual_base || end > ram_end)
            return OBS31_BOUNDS;
        for (prior = 0; prior < row; ++prior) {
            const struct obs31_row *p = &m->rows[prior];
            if (overlap(r->virtual_address, end, p->virtual_address,
                        p->virtual_address + p->bytes)) return OBS31_OVERLAP;
        }
    }
    for (row = 0; row < m->height; ++row) {
        size_t offset = (size_t)(m->rows[row].virtual_address - ram_virtual_base);
        for (col = 0; col < m->width; ++col) {
            uint32_t value = (!row || row + 1 == m->height || !col ||
                col + 1 == m->width || ((row ^ col) & 1)) ? foreground : background;
            unsigned byte;
            for (byte = 0; byte < 4; ++byte)
                ram[offset + (size_t)col * 4 + byte] = (uint8_t)(value >> (byte * 8));
        }
    }
    return OBS31_OK;
}

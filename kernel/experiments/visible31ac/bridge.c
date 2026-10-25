/* SPDX-License-Identifier: MIT */
#include "layout.h"
#include "../observer31ab/observer.h"

#define WORD(r, field) ((r)->words[(field) / 8])
#define PAGE4 UINT64_C(4096)
#define PA_MASK UINT64_C(0x000ffffffffff000)
#define PROTECTED_MAX 48u
#define CLEAN_MAX 160u

struct context {
    struct v31_record *record;
    uint64_t protected_pages[PROTECTED_MAX];
    uint32_t protected_count;
    uint32_t vhe;
    uint64_t clean_addresses[CLEAN_MAX];
    uint32_t clean_count;
    uint32_t line_bytes;
};

_Static_assert(sizeof(uintptr_t) == 8, "AArch64 pointer model required");
_Static_assert(sizeof(struct v31_record) == V31_RECORD_BYTES, "record geometry");

static uint32_t u32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
        (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static uint64_t u64(const uint8_t *p)
{
    return (uint64_t)u32(p) | (uint64_t)u32(p + 4) << 32;
}
static void stage(struct v31_record *r, uint64_t value)
{
    visible31ac_barrier();
    WORD(r, V31_R_STAGE) = value;
    visible31ac_barrier();
}
static void refuse(struct v31_record *r, uint64_t status)
{
    WORD(r, V31_R_STATUS) = status;
    stage(r, V31_STAGE_REFUSED);
}
static uint64_t probe(struct context *c, uint64_t va, int write)
{
    uint64_t par;
    WORD(c->record, V31_R_LAST_VA) = va;
    WORD(c->record, V31_R_PROBES)++;
    par = write ? visible31ac_write_at(va) : visible31ac_read_at(va);
    WORD(c->record, V31_R_LAST_PAR) = par;
    return par;
}
static int checked_end(uint64_t base, uint64_t bytes, uint64_t *end)
{
    if (!base || !bytes || bytes > UINT64_MAX - base) return 0;
    *end = base + bytes;
    return 1;
}
static int remember(struct context *c, uint64_t page)
{
    uint32_t i;
    for (i = 0; i < c->protected_count; ++i)
        if (c->protected_pages[i] == page) return 1;
    if (c->protected_count == PROTECTED_MAX) return 0;
    c->protected_pages[c->protected_count++] = page;
    WORD(c->record, V31_R_PROTECTED_PAGES) = c->protected_count;
    return 1;
}
/* Accept only explicitly modelled Normal NC/WB source memory. A successful AT
 * does not authenticate the source or guarantee a later access cannot fault. */
static int readable(struct context *c, uint64_t va, uint64_t bytes)
{
    uint64_t end, cursor;
    if (!checked_end(va, bytes, &end)) return 0;
    cursor = va;
    while (cursor < end) {
        uint64_t par = probe(c, cursor, 0), attr = par >> 56;
        uint64_t next = (cursor | UINT64_C(4095));
        if ((par & 1) ||
            (attr != 0x44 && attr != 0xff) || !remember(c, par & PA_MASK)) return 0;
        if (next == UINT64_MAX) return 0;
        cursor = next + 1;
    }
    return 1;
}
static int snapshot(struct context *c, uint64_t va, uint8_t *out, size_t bytes)
{
    size_t i;
    if (!readable(c, va, bytes)) return 0;
    for (i = 0; i < bytes; ++i)
        out[i] = *(const volatile uint8_t *)(uintptr_t)(va + i);
    WORD(c->record, V31_R_READ_BYTES) += bytes;
    return 1;
}

static uint64_t profile(struct context *c)
{
    struct v31_record *r = c->record;
    uint64_t hcr = WORD(r, V31_R_HCR), tcr = WORD(r, V31_R_TCR);
    uint64_t sctlr = WORD(r, V31_R_SCTLR);
    unsigned e2h = (unsigned)((hcr >> 34) & 1), tge = (unsigned)((hcr >> 27) & 1);
    if (WORD(r, V31_R_EL) != 8) return V31_EL;
    if (e2h != tge) return V31_HCR;
    c->vhe = e2h;
    if ((WORD(r, V31_R_DAIF) & 0x3c0) != 0x3c0) return V31_DAIF;
    if (!(sctlr & 1)) return V31_MMU;
    if (sctlr & (UINT64_C(1) << 25)) return V31_LITTLE_ENDIAN;
    /* Ordinary non-VHE EL2 uses the 64-bit format. In EL2&0, capability does
     * not imply active D128: inspect TCR2 only when D128 and TCRX qualify it.
     * Unknown feature encodings or active D128 refuse before any AT. */
    if (c->vhe && ((WORD(r, V31_R_MMFR3) >> 32) & 15)) {
        uint64_t tcr2;
        if (((WORD(r, V31_R_MMFR3) >> 32) & 15) != 1) return V31_FORMAT;
        if ((WORD(r, V31_R_MMFR3) & 15) != 1) return V31_TCRX;
        tcr2 = visible31ac_read_tcr2();
        WORD(r, V31_R_TCR2) = tcr2;
        WORD(r, V31_R_TCR2_READ) = 1;
        if (tcr2 & (UINT64_C(1) << 5)) return V31_FORMAT;
    }
    if (!c->vhe) {
        if (((tcr >> 16) & 7) > 6) return V31_FORMAT;
    } else {
        if (((tcr >> 32) & 7) > 6) return V31_FORMAT;
    }
    return V31_OK;
}

static uint64_t clean_lines(struct context *c, const struct obs31_table *table,
    uint64_t va, uint64_t end,
    uint64_t par, uint64_t fb_start, uint64_t fb_end)
{
    uint64_t line;
    if (!c->line_bytes) {
        uint64_t ctr = visible31ac_read_ctr();
        uint32_t bytes = 4u << ((ctr >> 16) & 15);
        WORD(c->record, V31_R_CTR) = ctr;
        WORD(c->record, V31_R_LINE_BYTES) = bytes;
        if (bytes < 16 || bytes > 2048) return V31_CACHE_LINE;
        c->line_bytes = bytes;
    }
    line = va & ~((uint64_t)c->line_bytes - 1);
    while (line < end) {
        uint64_t pa = (par & PA_MASK) | (line & UINT64_C(4095)), mapped;
        uint32_t i;
        /* Line size divides the minimum4KiB translation page. The caller
         * splits at every such boundary, so this PAR covers the whole line. */
        if (pa < fb_start || pa > fb_end || c->line_bytes > fb_end - pa)
            return V31_CACHE_EXTENT;
        if (obs31_translate(table, pa, c->line_bytes, &mapped) != OBS31_OK || mapped != line)
            return V31_CACHE_EXTENT;
        for (i = 0; i < c->clean_count; ++i)
            if (c->clean_addresses[i] == line) break;
        if (i == c->clean_count) {
            if (c->clean_count == CLEAN_MAX) return V31_CACHE_LINE;
            c->clean_addresses[c->clean_count++] = line;
            WORD(c->record, V31_R_CLEAN_PLANNED) = c->clean_count;
        }
        if (line > UINT64_MAX - c->line_bytes) return V31_CACHE_EXTENT;
        line += c->line_bytes;
    }
    return V31_OK;
}

static uint64_t writable_row(struct context *c, const struct obs31_table *table,
    const struct obs31_row *row,
    uint64_t fb_start, uint64_t fb_end)
{
    uint64_t cursor = row->virtual_address, end, delta = 0;
    if (!checked_end(cursor, row->bytes, &end)) return V31_FB_TRANSLATION;
    while (cursor < end) {
        uint64_t par = probe(c, cursor, 1);
        uint64_t expected = row->physical + delta;
        uint64_t actual = (par & PA_MASK) | (cursor & UINT64_C(4095));
        uint64_t next = (cursor | UINT64_C(4095));
        uint32_t i;
        WORD(c->record, V31_R_EXPECTED_PA) = expected;
        if (par & 1) return V31_FB_TRANSLATION;
        if (actual != expected) return V31_FB_PA;
        if ((par >> 56) != 0x44 && (par >> 56) != 0xff) return V31_FB_ATTR;
        for (i = 0; i < c->protected_count; ++i)
            if ((actual & ~UINT64_C(4095)) == c->protected_pages[i]) return V31_FB_ALIAS;
        if (next == UINT64_MAX) return V31_FB_TRANSLATION;
        next++;
        if ((par >> 56) == 0xff) {
            uint64_t status = clean_lines(c, table, cursor, next < end ? next : end,
                par, fb_start, fb_end);
            if (status) return status;
        }
        delta += next - cursor;
        cursor = next;
    }
    return V31_OK;
}

void visible31ac_bridge(struct v31_record *r)
{
    struct context c = {0};
    uint8_t boot[OBS31_VIDEO_PREFIX_BYTES], helper[24], count_bytes[4];
    uint8_t raw_table[OBS31_RANGE_MAX * OBS31_RANGE_BYTES];
    uint8_t helper_check[24], count_check[4];
    struct obs31_table table;
    struct obs31_video video;
    struct obs31_marker marker;
    uint64_t status, helper_va, count_va, table_va, image_base, image_bytes;
    uint32_t count, row, col;
    enum obs31_status decoded;
    c.record = r;
    if (WORD(r, V31_R_REASON) != 0) { refuse(r, V31_REASON); return; }
    status = profile(&c);
    if (status) { refuse(r, status); return; }
    stage(r, V31_STAGE_PROFILE);
    image_base = (uint64_t)(uintptr_t)native_image_base;
    image_bytes = (uint64_t)(uintptr_t)native_image_end - image_base;
    if (image_bytes != V31_PAYLOAD_BYTES || !readable(&c, image_base, image_bytes)) {
        refuse(r, V31_IMAGE_READ); return;
    }
    WORD(r, V31_R_IMAGE_PAGES) = c.protected_count;
    if (!snapshot(&c, WORD(r, V31_R_BOOT), boot, sizeof(boot))) {
        refuse(r, V31_BOOT_READ); return;
    }
    if (WORD(r, V31_R_MONITOR) > UINT64_MAX - 416 || !WORD(r, V31_R_MONITOR)) {
        refuse(r, V31_MONITOR_READ); return;
    }
    helper_va = WORD(r, V31_R_MONITOR) + 416;
    if (!snapshot(&c, helper_va, helper, sizeof(helper))) {
        refuse(r, V31_MONITOR_READ); return;
    }
    WORD(r, V31_R_HELPER_VERSION) = u32(helper);
    if (u32(helper) != 10) { refuse(r, V31_HELPER_VERSION); return; }
    count_va = u64(helper + 8); table_va = u64(helper + 16);
    if (!snapshot(&c, count_va, count_bytes, sizeof(count_bytes))) {
        refuse(r, V31_COUNT_READ); return;
    }
    count = u32(count_bytes); WORD(r, V31_R_COUNT) = count;
    if (!count || count > OBS31_RANGE_MAX) { refuse(r, V31_COUNT_RANGE); return; }
    if (!snapshot(&c, table_va, raw_table, (size_t)count * OBS31_RANGE_BYTES)) {
        refuse(r, V31_TABLE_READ); return;
    }
    /* Detect an observed producer change, without claiming atomicity or locking. */
    if (!snapshot(&c, helper_va, helper_check, sizeof(helper_check)) ||
        !snapshot(&c, count_va, count_check, sizeof(count_check))) {
        refuse(r, V31_INPUT_CHANGED); return;
    }
    for (row = 0; row < sizeof(helper); ++row) if (helper[row] != helper_check[row]) {
        refuse(r, V31_INPUT_CHANGED); return;
    }
    if (u32(count_check) != count) { refuse(r, V31_INPUT_CHANGED); return; }
    stage(r, V31_STAGE_SNAPSHOTS);
    decoded = obs31_table_decode(raw_table, (size_t)count * OBS31_RANGE_BYTES, count, &table);
    WORD(r, V31_R_DETAIL) = decoded;
    if (decoded != OBS31_OK) { refuse(r, V31_TABLE_FORMAT); return; }
    decoded = obs31_video_decode(boot, sizeof(boot), &video);
    WORD(r, V31_R_DETAIL) = decoded;
    if (decoded != OBS31_OK) { refuse(r, V31_VIDEO_FORMAT); return; }
    decoded = obs31_marker_plan(&video, &table, 0, 0, 32, 16, &marker);
    WORD(r, V31_R_DETAIL) = decoded;
    if (decoded != OBS31_OK) { refuse(r, V31_PLAN); return; }
    WORD(r, V31_R_FB_PA) = marker.rows[0].physical;
    WORD(r, V31_R_FB_VA) = marker.rows[0].virtual_address;
    stage(r, V31_STAGE_PLANNED);
    for (row = 0; row < marker.height; ++row) {
        status = writable_row(&c, &table, &marker.rows[row], video.physical_base,
            video.physical_base + video.row_bytes * video.height);
        if (status) { refuse(r, status); return; }
    }
    stage(r, V31_STAGE_VALIDATED);
    WORD(r, V31_R_PAINT_ATTEMPT) = 1;
    visible31ac_barrier();
    for (row = 0; row < marker.height; ++row) {
        volatile uint32_t *pixels = (volatile uint32_t *)(uintptr_t)marker.rows[row].virtual_address;
        for (col = 0; col < marker.width; ++col) {
            int foreground = row == 0 || row + 1 == marker.height || col == 0 ||
                col + 1 == marker.width || ((row ^ col) & 1);
            uint32_t color = marker.depth == 30 ? UINT32_C(0x3ff55555) : UINT32_C(0x00ff55aa);
            pixels[col] = foreground ? color : 0;
            WORD(r, V31_R_PAINTED_PIXELS)++;
        }
    }
    visible31ac_barrier();
    for (row = 0; row < c.clean_count; ++row) {
        visible31ac_clean(c.clean_addresses[row]);
        WORD(r, V31_R_CLEAN_COUNT)++;
    }
    visible31ac_barrier();
    stage(r, V31_STAGE_PAINTED);
}

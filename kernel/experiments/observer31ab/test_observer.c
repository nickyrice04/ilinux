/* SPDX-License-Identifier: MIT */
#include "observer.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); exit(1); } } while (0)
#define PAGE UINT64_C(0x4000)
static unsigned oracle_cases;

static void put32(uint8_t *p, uint32_t v)
{
    unsigned i;
    for (i = 0; i < 4; ++i) p[i] = (uint8_t)(v >> (i * 8));
}
static void put64(uint8_t *p, uint64_t v)
{
    put32(p, (uint32_t)v); put32(p + 4, (uint32_t)(v >> 32));
}
static void record(uint8_t *p, uint64_t pa, uint64_t va, uint32_t pages)
{
    put64(p, pa); put64(p + 8, va); put32(p + 16, pages);
    put32(p + 20, UINT32_C(0xfedcba98)); /* Opaque tail is accepted. */
}
static struct obs31_table table(void)
{
    uint8_t bytes[24];
    struct obs31_table t;
    record(bytes, 0x10000, 0x80000, 4);
    CHECK(obs31_table_decode(bytes, sizeof(bytes), 1, &t) == OBS31_OK);
    return t;
}
static void prefix(uint8_t *p)
{
    memset(p, 0xa5, 88);
    p[0] = 2; p[1] = 0; p[2] = 2; p[3] = 0;
    put64(p + 40, 0x10003); put64(p + 48, UINT64_C(0x123456789abcdef0));
    put64(p + 56, 256); put64(p + 64, 60); put64(p + 72, 40);
    put64(p + 80, UINT64_C(0x102000020));
}
static struct obs31_video video(void)
{
    uint8_t p[88]; struct obs31_video v;
    prefix(p); CHECK(obs31_video_decode(p, sizeof(p), &v) == OBS31_OK);
    return v;
}
static struct obs31_marker marker(void)
{
    struct obs31_table t = table(); struct obs31_video v = video();
    struct obs31_marker m;
    CHECK(obs31_marker_plan(&v, &t, 3, 5, 32, 16, &m) == OBS31_OK);
    return m;
}

static void test_table_shape(void)
{
    uint8_t bytes[24 * OBS31_RANGE_MAX];
    struct obs31_table t, before;
    uint32_t i;
    for (i = 0; i < OBS31_RANGE_MAX; ++i)
        record(bytes + (size_t)i * 24, (uint64_t)i * PAGE, 0x100000 + (uint64_t)i * PAGE, 1);
    CHECK(obs31_table_decode(bytes, sizeof(bytes), OBS31_RANGE_MAX, &t) == OBS31_OK);
    CHECK(t.count == OBS31_RANGE_MAX && t.ranges[63].physical == 63 * PAGE);
    memset(&before, 0x5a, sizeof(before));
    for (i = 0; i < 24; ++i) {
        t = before;
        CHECK(obs31_table_decode(bytes, i, 1, &t) == OBS31_SIZE);
        CHECK(!memcmp(&t, &before, sizeof(t)));
    }
    CHECK(obs31_table_decode(bytes, 25, 1, &t) == OBS31_SIZE);
    CHECK(obs31_table_decode(bytes, 0, 0, &t) == OBS31_SIZE);
    CHECK(obs31_table_decode(bytes, sizeof(bytes), UINT32_MAX, &t) == OBS31_SIZE);
    CHECK(obs31_table_decode(NULL, 24, 1, &t) == OBS31_ARGUMENT);
    CHECK(obs31_table_decode(bytes, 24, 1, NULL) == OBS31_ARGUMENT);
}

static void test_table_invalid_ranges(void)
{
    uint8_t b[48]; struct obs31_table t, before;
    struct { uint64_t p, v; uint32_t n; } bad[] = {
        {0x10000,0x80000,0}, {0x10001,0x80000,1}, {0x10000,0x80001,1},
        {UINT64_MAX - PAGE + 1,0x80000,1}, {0x10000,UINT64_MAX - PAGE + 1,1}
    };
    size_t i;
    memset(&before, 0x3c, sizeof(before));
    for (i = 0; i < sizeof(bad)/sizeof(bad[0]); ++i) {
        record(b,bad[i].p,bad[i].v,bad[i].n); t = before;
        CHECK(obs31_table_decode(b,24,1,&t) == OBS31_RANGE);
        CHECK(!memcmp(&t,&before,sizeof(t)));
    }
    record(b,0x10000,0x80000,2);
    record(b+24,0x14000,0xa0000,1);
    CHECK(obs31_table_decode(b,48,2,&t) == OBS31_OVERLAP);
    record(b+24,0x20000,0x84000,1);
    CHECK(obs31_table_decode(b,48,2,&t) == OBS31_OVERLAP);
    record(b,0,0x4000,UINT32_MAX);
    CHECK(obs31_table_decode(b,24,1,&t) == OBS31_OK);
    CHECK(t.ranges[0].bytes == (uint64_t)UINT32_MAX * PAGE);
}

static void test_translate_boundaries(void)
{
    struct obs31_table t = table(); uint64_t va = 77;
    CHECK(obs31_translate(&t,0x10000,1,&va) == OBS31_OK && va == 0x80000);
    CHECK(obs31_translate(&t,0x1ffff,1,&va) == OBS31_OK && va == 0x8ffff);
    va = 77;
    CHECK(obs31_translate(&t,0x20000,1,&va) == OBS31_UNMAPPED && va == 77);
    CHECK(obs31_translate(&t,0x1ffff,2,&va) == OBS31_UNMAPPED && va == 77);
    CHECK(obs31_translate(&t,0,0,&va) == OBS31_RANGE && va == 77);
    CHECK(obs31_translate(&t,UINT64_MAX,2,&va) == OBS31_RANGE && va == 77);
    t.ranges[0].virtual_address = 0;
    CHECK(obs31_translate(&t,0x10000,1,&va) == OBS31_UNMAPPED && va == 77);
    CHECK(obs31_translate(&t,0x10004,4,&va) == OBS31_OK && va == 4);
    CHECK(obs31_translate(&t,0x10004,4,NULL) == OBS31_ARGUMENT);
    t.count = UINT32_MAX;
    CHECK(obs31_translate(&t,0x10004,4,&va) == OBS31_SIZE);
}

static void test_translate_chains(void)
{
    uint8_t b[72]; struct obs31_table t; uint64_t va = 77;
    /* Input order is deliberately not address order. */
    record(b,0x18000,0x88000,1); record(b+24,0x10000,0x80000,1);
    record(b+48,0x14000,0x84000,1);
    CHECK(obs31_table_decode(b,sizeof(b),3,&t) == OBS31_OK);
    CHECK(obs31_translate(&t,0x13ffc,0x4008,&va) == OBS31_OK && va == 0x83ffc);
    t.ranges[0].virtual_address = 0xa0000; va = 77;
    CHECK(obs31_translate(&t,0x13ffc,0x4008,&va) == OBS31_NONCONTIGUOUS && va == 77);
    t.ranges[0].physical = 0x1c000;
    CHECK(obs31_translate(&t,0x13ffc,0x4008,&va) == OBS31_UNMAPPED && va == 77);
}

static void test_translate_oracle(void)
{
    const uint64_t offsets[] = {0,1,4096,16380,16383};
    const uint64_t lengths[] = {1,4,8,16384};
    unsigned mask, page, a, b;
    for (mask = 1; mask < 16; ++mask) {
        struct obs31_table t = {0};
        for (page = 0; page < 4; ++page) if (mask & (1u << page)) {
            struct obs31_range *r = &t.ranges[t.count++];
            r->physical = 0x10000 + (uint64_t)page * PAGE;
            r->virtual_address = 0x80000 + (uint64_t)page * PAGE; r->bytes = PAGE;
        }
        for (page = 0; page < 4; ++page) for (a = 0; a < 5; ++a) for (b = 0; b < 4; ++b) {
            uint64_t pa = 0x10000 + (uint64_t)page * PAGE + offsets[a];
            uint64_t k, va = 77; int mapped = 1;
            enum obs31_status status;
            for (k = 0; k < lengths[b]; ++k) {
                uint64_t slot = (pa + k - 0x10000) / PAGE;
                if (slot >= 4 || !(mask & (1u << slot))) { mapped = 0; break; }
            }
            status = obs31_translate(&t,pa,lengths[b],&va);
            CHECK(mapped ? (status == OBS31_OK && va == pa + 0x70000) :
                           (status == OBS31_UNMAPPED && va == 77));
            ++oracle_cases;
        }
    }
}

static void test_video_decode(void)
{
    uint8_t p[88]; struct obs31_video v, before; unsigned i;
    prefix(p);
    CHECK(obs31_video_decode(p,sizeof(p),&v) == OBS31_OK);
    CHECK(v.physical_base == 0x10000 && v.display == UINT64_C(0x123456789abcdef0));
    CHECK(v.depth_word == UINT64_C(0x102000020) && v.width == 60 && v.height == 40);
    memset(&before,0x7b,sizeof(before));
    for (i = 0; i < 88; ++i) {
        v = before; CHECK(obs31_video_decode(p,i,&v) == OBS31_SIZE);
        CHECK(!memcmp(&v,&before,sizeof(v)));
    }
    CHECK(obs31_video_decode(p,89,&v) == OBS31_SIZE);
    for (i = 0; i < 4; ++i) {
        prefix(p); p[i] ^= 1; v = before;
        CHECK(obs31_video_decode(p,sizeof(p),&v) == OBS31_FORMAT);
        CHECK(!memcmp(&v,&before,sizeof(v)));
    }
    prefix(p); put64(p+80,30);
    CHECK(obs31_video_decode(p,sizeof(p),&v) == OBS31_OK);
    CHECK(obs31_video_decode(NULL,sizeof(p),&v) == OBS31_ARGUMENT);
    CHECK(obs31_video_decode(p,sizeof(p),NULL) == OBS31_ARGUMENT);
}

static void test_video_invalid_geometry(void)
{
    uint8_t p[88]; struct obs31_video v, before;
    struct { unsigned offset; uint64_t value; } bad[] = {
        {40,3},{40,UINT64_MAX-3},{56,0},{56,239},{56,240},{64,0},
        {64,UINT64_MAX},{72,0},{72,UINT64_MAX},{80,24}
    };
    size_t i;
    /* row_bytes240 is valid; use width61 for that explicit insufficient row. */
    memset(&before,0xe7,sizeof(before));
    for (i = 0; i < sizeof(bad)/sizeof(bad[0]); ++i) {
        prefix(p); put64(p+bad[i].offset,bad[i].value);
        if (bad[i].offset == 56 && bad[i].value == 240) put64(p+64,61);
        v = before;
        CHECK(obs31_video_decode(p,sizeof(p),&v) != OBS31_OK);
        CHECK(!memcmp(&v,&before,sizeof(v)));
    }
}

static void test_plan_rows(void)
{
    struct obs31_marker m = marker(); unsigned row;
    CHECK(m.width == 32 && m.height == 16 && m.depth == 32);
    for (row = 0; row < 16; ++row) {
        CHECK(m.rows[row].physical == 0x10000 + (5 + row) * 256 + 12);
        CHECK(m.rows[row].virtual_address == m.rows[row].physical + 0x70000);
        CHECK(m.rows[row].bytes == 128);
    }
}

static void test_plan_rejections(void)
{
    struct obs31_table t = table(); struct obs31_video v = video();
    struct obs31_marker m, before;
    struct { uint64_t x,y; uint32_t w,h; } bad[] = {
        {0,0,0,1},{0,0,1,0},{0,0,33,1},{0,0,1,17},
        {29,0,32,16},{0,25,32,16},{UINT64_MAX,0,1,1},{0,UINT64_MAX,1,1}
    };
    size_t i;
    memset(&before,0x39,sizeof(before));
    for (i = 0; i < sizeof(bad)/sizeof(bad[0]); ++i) {
        m = before;
        CHECK(obs31_marker_plan(&v,&t,bad[i].x,bad[i].y,bad[i].w,bad[i].h,&m) == OBS31_BOUNDS);
        CHECK(!memcmp(&m,&before,sizeof(m)));
    }
    /* The final row is unmapped: no partial output is committed. */
    v.physical_base = 0x1ff00; v.width = 32; v.height = 2; m = before;
    CHECK(obs31_marker_plan(&v,&t,0,0,32,2,&m) == OBS31_UNMAPPED);
    CHECK(!memcmp(&m,&before,sizeof(m)));
    CHECK(obs31_marker_plan(&v,&t,0,0,1,1,NULL) == OBS31_ARGUMENT);
}

static void test_plan_crossing_ranges(void)
{
    uint8_t b[48]; struct obs31_table t; struct obs31_video v = video();
    struct obs31_marker m;
    record(b,0x10000,0x80000,1); record(b+24,0x14000,0x84000,1);
    CHECK(obs31_table_decode(b,sizeof(b),2,&t) == OBS31_OK);
    v.physical_base = 0x13ffc; v.row_bytes = 128; v.width = 32; v.height = 1;
    CHECK(obs31_marker_plan(&v,&t,0,0,32,1,&m) == OBS31_OK);
    CHECK(m.rows[0].virtual_address == 0x83ffc && m.rows[0].bytes == 128);
    t.ranges[1].virtual_address = 0x90000;
    CHECK(obs31_marker_plan(&v,&t,0,0,32,1,&m) == OBS31_NONCONTIGUOUS);
}

static void test_paint_canaries(void)
{
    uint8_t ram[0x4000+32], expected[sizeof(ram)];
    struct obs31_marker m = marker(); unsigned y,x,b;
    const uint32_t fg = UINT32_C(0x12345678), bg = UINT32_C(0x87654321);
    memset(ram,0xa5,sizeof(ram)); memcpy(expected,ram,sizeof(ram));
    /* Independent pixel oracle uses absolute framebuffer positions. */
    for (y = 5; y < 21; ++y) for (x = 3; x < 35; ++x) {
        int use_fg = y == 5 || y == 20 || x == 3 || x == 34 || ((y + x) % 2);
        uint32_t value = use_fg ? fg : bg;
        for (b = 0; b < 4; ++b) expected[16 + y*256 + x*4 + b] = (uint8_t)(value >> (8*b));
    }
    CHECK(obs31_paint_ram(&m,0x80000,ram+16,0x4000,fg,bg) == OBS31_OK);
    CHECK(!memcmp(ram,expected,sizeof(ram)));
    m.depth = 30;
    CHECK(obs31_paint_ram(&m,0x80000,ram+16,0x4000,0x3fffffff,0) == OBS31_OK);
}

static void test_paint_failure_atomic(void)
{
    uint8_t ram[0x4000], before[sizeof(ram)]; struct obs31_marker m = marker();
    memset(ram,0xcc,sizeof(ram)); memcpy(before,ram,sizeof(ram));
    m.rows[15].virtual_address = 0x83ffc;
    CHECK(obs31_paint_ram(&m,0x80000,ram,sizeof(ram),1,0) == OBS31_BOUNDS);
    CHECK(!memcmp(ram,before,sizeof(ram)));
    m = marker(); m.rows[15] = m.rows[0];
    CHECK(obs31_paint_ram(&m,0x80000,ram,sizeof(ram),1,0) == OBS31_OVERLAP);
    CHECK(!memcmp(ram,before,sizeof(ram)));
    m = marker(); m.depth = 30;
    CHECK(obs31_paint_ram(&m,0x80000,ram,sizeof(ram),0x40000000,0) == OBS31_FORMAT);
    CHECK(!memcmp(ram,before,sizeof(ram)));
    m = marker();
    CHECK(obs31_paint_ram(&m,UINT64_MAX-16,ram,sizeof(ram),1,0) == OBS31_RANGE);
    CHECK(obs31_paint_ram(&m,0x80000,NULL,sizeof(ram),1,0) == OBS31_ARGUMENT);
    m.rows[0].bytes = 4;
    CHECK(obs31_paint_ram(&m,0x80000,ram,sizeof(ram),1,0) == OBS31_BOUNDS);
    CHECK(!memcmp(ram,before,sizeof(ram)));
}

int main(void)
{
    test_table_shape(); test_table_invalid_ranges(); test_translate_boundaries();
    test_translate_chains(); test_translate_oracle(); test_video_decode();
    test_video_invalid_geometry(); test_plan_rows(); test_plan_rejections();
    test_plan_crossing_ranges(); test_paint_canaries(); test_paint_failure_atomic();
    CHECK(oracle_cases == 1200);
    puts("OBSERVER31AB_PASS groups=12 translation_oracle_cases=1200 native=NOT_DEPLOYABLE");
    return 0;
}

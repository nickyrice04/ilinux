/* SPDX-License-Identifier: MIT */
#include "gptbat.h"
#include <stdio.h>
#include <stddef.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "check at line %d\n", __LINE__); return 1; } } while (0)

static int test_literal_vectors(void)
{
    const uint64_t pages[] = {0, 1, 0x10000, 0x80000000, 0xffffffff};
    const uint64_t bases[] = {0, 0x4000, 0x40000000, 0x200000000000, 0x3fffffffc000};
    size_t i;
    for (i = 0; i < sizeof(pages) / sizeof(pages[0]); ++i) {
        struct gpu31q_gptbat_page_number page = {pages[i]}, decoded = {99};
        struct gpu31q_gptbat_base base = {99};
        CHECK(gpu31q_gptbat_decode(page, &base) == GPU31Q_GPTBAT_OK);
        CHECK(base.value == bases[i]);
        CHECK(gpu31q_gptbat_encode(base, &decoded) == GPU31Q_GPTBAT_OK);
        CHECK(decoded.value == pages[i]);
    }
    return 0;
}

static int test_page_width(void)
{
    const uint64_t bad[] = {UINT64_C(0x100000000), UINT64_C(0x100000001), UINT64_MAX};
    size_t i;
    for (i = 0; i < sizeof(bad) / sizeof(bad[0]); ++i) {
        struct gpu31q_gptbat_page_number page = {bad[i]};
        struct gpu31q_gptbat_base output = {UINT64_C(0xa5a5)};
        CHECK(gpu31q_gptbat_decode(page, &output) == GPU31Q_GPTBAT_WIDTH);
        CHECK(output.value == UINT64_C(0xa5a5));
    }
    return 0;
}

static int test_base_width(void)
{
    const uint64_t bad[] = {UINT64_C(1) << 46, (UINT64_C(1) << 46) + 0x4000, UINT64_MAX};
    size_t i;
    for (i = 0; i < sizeof(bad) / sizeof(bad[0]); ++i) {
        struct gpu31q_gptbat_base base = {bad[i]};
        struct gpu31q_gptbat_page_number output = {UINT64_C(0xa5a5)};
        CHECK(gpu31q_gptbat_encode(base, &output) == GPU31Q_GPTBAT_WIDTH);
        CHECK(output.value == UINT64_C(0xa5a5));
    }
    return 0;
}

static int test_every_offset(void)
{
    uint64_t offset;
    for (offset = 1; offset < 16384; ++offset) {
        struct gpu31q_gptbat_base base = {UINT64_C(0x3fffffffc000) + offset};
        struct gpu31q_gptbat_page_number output = {UINT64_C(0xa5a5)};
        CHECK(gpu31q_gptbat_encode(base, &output) == GPU31Q_GPTBAT_ALIGNMENT);
        CHECK(output.value == UINT64_C(0xa5a5));
    }
    return 0;
}

static int test_null(void)
{
    struct gpu31q_gptbat_page_number page = {0};
    struct gpu31q_gptbat_base base = {0};
    CHECK(gpu31q_gptbat_decode(page, NULL) == GPU31Q_GPTBAT_ARGUMENT);
    CHECK(gpu31q_gptbat_encode(base, NULL) == GPU31Q_GPTBAT_ARGUMENT);
    return 0;
}

static int test_single_bit_vectors(void)
{
    unsigned bit;
    for (bit = 0; bit < 32; ++bit) {
        struct gpu31q_gptbat_page_number page = {UINT64_C(1) << bit}, result;
        struct gpu31q_gptbat_base base;
        CHECK(gpu31q_gptbat_decode(page, &base) == GPU31Q_GPTBAT_OK);
        CHECK(base.value == (UINT64_C(1) << (bit + 14)));
        CHECK(gpu31q_gptbat_encode(base, &result) == GPU31Q_GPTBAT_OK);
        CHECK(result.value == page.value);
    }
    return 0;
}

static int test_seeded_roundtrips(void)
{
    uint32_t value = UINT32_C(0x31);
    unsigned i;
    for (i = 0; i < 10000; ++i) {
        struct gpu31q_gptbat_page_number page, result;
        struct gpu31q_gptbat_base base;
        value = value * UINT32_C(1664525) + UINT32_C(1013904223);
        page.value = value;
        CHECK(gpu31q_gptbat_decode(page, &base) == GPU31Q_GPTBAT_OK);
        CHECK(gpu31q_gptbat_encode(base, &result) == GPU31Q_GPTBAT_OK);
        CHECK(result.value == page.value);
    }
    return 0;
}

int main(void)
{
    CHECK(test_literal_vectors() == 0);
    CHECK(test_page_width() == 0);
    CHECK(test_base_width() == 0);
    CHECK(test_every_offset() == 0);
    CHECK(test_null() == 0);
    CHECK(test_single_bit_vectors() == 0);
    CHECK(test_seeded_roundtrips() == 0);
    puts("GPU31Q_GPTBAT_PASS");
    return 0;
}

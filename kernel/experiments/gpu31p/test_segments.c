/* Independent synthetic vectors; no Apple firmware bytes are embedded. */
#include "segments.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static const uint8_t golden[32] = {
    0x00, 0x40, 0x66, 0x55, 0x44, 0x33, 0x22, 0x11,
    0x00, 0x00, 0xdd, 0xcc, 0xbb, 0xaa, 0x99, 0x88,
    0x00, 0x80, 0x77, 0x66, 0x55, 0x44, 0x33, 0x22,
    0x00, 0x40, 0x00, 0x00, 0xef, 0xbe, 0xad, 0xde
};

static struct gpu31p_segment sample(void)
{
    struct gpu31p_segment s = {
        UINT64_C(0x1122334455664000), UINT64_C(0x8899aabbccdd0000),
        UINT64_C(0x2233445566778000), UINT32_C(0x4000), UINT32_C(0xdeadbeef)
    };
    return s;
}

static void golden_decode(void)
{
    struct gpu31p_segment out;
    size_t n = 99;
    assert(gpu31p_decode(golden, sizeof(golden), &out, 1, &n) == GPU31P_OK);
    assert(n == 1 && out.descriptor_phys == UINT64_C(0x1122334455664000));
    assert(out.iova == UINT64_C(0x8899aabbccdd0000));
    assert(out.remap == UINT64_C(0x2233445566778000));
    assert(out.size == 0x4000 && out.opaque == UINT32_C(0xdeadbeef));
}

static void golden_encode(void)
{
    struct gpu31p_segment s = sample();
    uint8_t out[32];
    size_t written = 99;
    assert(gpu31p_encode(&s, 1, out, sizeof(out), &written) == GPU31P_OK);
    assert(written == 32 && memcmp(out, golden, 32) == 0);
}

static void unaligned_buffers(void)
{
    uint8_t input[34], output[34];
    struct gpu31p_segment out;
    size_t n = 0;
    memset(input, 0xa5, sizeof(input));
    memset(output, 0xa5, sizeof(output));
    memcpy(input + 1, golden, 32);
    assert(gpu31p_decode(input + 1, 32, &out, 1, &n) == GPU31P_OK);
    assert(gpu31p_encode(&out, n, output + 1, 32, &n) == GPU31P_OK);
    assert(output[0] == 0xa5 && output[33] == 0xa5);
    assert(memcmp(input, output, sizeof(input)) == 0);
}

static void bad_lengths(void)
{
    struct gpu31p_segment out = sample();
    size_t n = 123, length;
    uint8_t bytes[33] = {0};
    for (length = 0; length <= 33; ++length) {
        if (length == 32)
            continue;
        assert(gpu31p_decode(bytes, length, &out, 1, &n) == GPU31P_LENGTH);
        assert(n == 123);
    }
    assert(gpu31p_decode(bytes, SIZE_MAX, &out, 1, &n) == GPU31P_LENGTH);
    assert(gpu31p_encode(&out, SIZE_MAX, bytes, sizeof(bytes), &n) == GPU31P_LENGTH);
    assert(gpu31p_encode(&out, 0, bytes, sizeof(bytes), &n) == GPU31P_LENGTH);
}

static void capacity_and_transaction(void)
{
    struct gpu31p_segment out = sample();
    size_t n = 123;
    uint8_t bytes[32], before[32];
    memset(bytes, 0xa5, sizeof(bytes));
    memcpy(before, bytes, sizeof(bytes));
    assert(gpu31p_decode(golden, 32, &out, 0, &n) == GPU31P_CAPACITY);
    assert(n == 123 && out.opaque == UINT32_C(0xdeadbeef));
    assert(gpu31p_encode(&out, 1, bytes, 31, &n) == GPU31P_CAPACITY);
    assert(n == 123 && memcmp(bytes, before, sizeof(bytes)) == 0);
    out.size = 0;
    assert(gpu31p_encode(&out, 1, bytes, 32, &n) == GPU31P_SPAN);
    assert(n == 123 && memcmp(bytes, before, sizeof(bytes)) == 0);
}

static void zero_size_and_late_failure(void)
{
    uint8_t input[64];
    struct gpu31p_segment output[2] = {sample(), sample()};
    size_t n = 123;
    output[0].opaque = UINT32_C(0x12345678);
    memcpy(input, golden, 32);
    memcpy(input + 32, golden, 32);
    memset(input + 56, 0, 4);
    assert(gpu31p_decode(input, 64, output, 2, &n) == GPU31P_SPAN);
    assert(n == 123 && output[0].opaque == UINT32_C(0x12345678) && output[1].size == 0x4000);
}

static void overflow_domains(void)
{
    unsigned int domain;
    for (domain = 0; domain < 3; ++domain) {
        struct gpu31p_segment s = sample();
        if (domain == 0)
            s.descriptor_phys = UINT64_MAX - s.size + 1;
        else if (domain == 1)
            s.iova = UINT64_MAX - s.size + 1;
        else
            s.remap = UINT64_MAX - s.size + 1;
        assert(gpu31p_validate(&s, 1, 1) == GPU31P_SPAN);
    }
}

static void maximum_valid_span(void)
{
    struct gpu31p_segment s = {UINT64_MAX - 1, UINT64_MAX - 1, UINT64_MAX - 1, 1, UINT32_MAX};
    uint8_t out[32];
    struct gpu31p_segment decoded;
    size_t n = 0;
    assert(gpu31p_encode(&s, 1, out, 32, &n) == GPU31P_OK);
    assert(gpu31p_decode(out, 32, &decoded, 1, &n) == GPU31P_OK);
    assert(decoded.descriptor_phys == UINT64_MAX - 1 && decoded.opaque == UINT32_MAX);
}

static void alignment_policy(void)
{
    struct gpu31p_segment s = sample();
    assert(gpu31p_validate(&s, 1, 16384) == GPU31P_OK);
    assert(gpu31p_validate(&s, 1, 0) == GPU31P_ARGUMENT);
    assert(gpu31p_validate(&s, 1, 3) == GPU31P_ARGUMENT);
    ++s.iova;
    assert(gpu31p_validate(&s, 1, 16384) == GPU31P_ALIGNMENT);
    assert(gpu31p_validate(&s, 1, 1) == GPU31P_OK);
    s = sample();
    --s.size;
    assert(gpu31p_validate(&s, 1, 16384) == GPU31P_ALIGNMENT);
}

static void overlap_each_domain(void)
{
    unsigned int domain;
    for (domain = 0; domain < 3; ++domain) {
        struct gpu31p_segment s[2] = {sample(), sample()};
        s[1].descriptor_phys += 0x4000;
        s[1].iova += 0x4000;
        s[1].remap += 0x4000;
        assert(gpu31p_validate(s, 2, 16384) == GPU31P_OK);
        if (domain == 0)
            --s[1].descriptor_phys;
        else if (domain == 1)
            --s[1].iova;
        else
            --s[1].remap;
        assert(gpu31p_validate(s, 2, 1) == GPU31P_OVERLAP);
    }
}

static void null_arguments(void)
{
    struct gpu31p_segment s = sample();
    uint8_t bytes[32];
    size_t n = 0;
    assert(gpu31p_decode(NULL, 32, &s, 1, &n) == GPU31P_ARGUMENT);
    assert(gpu31p_decode(golden, 32, NULL, 1, &n) == GPU31P_ARGUMENT);
    assert(gpu31p_decode(golden, 32, &s, 1, NULL) == GPU31P_ARGUMENT);
    assert(gpu31p_encode(NULL, 1, bytes, 32, &n) == GPU31P_ARGUMENT);
    assert(gpu31p_encode(&s, 1, NULL, 32, &n) == GPU31P_ARGUMENT);
    assert(gpu31p_encode(&s, 1, bytes, 32, NULL) == GPU31P_ARGUMENT);
    assert(gpu31p_validate(NULL, 1, 1) == GPU31P_ARGUMENT);
}

static void all_counts_roundtrip(void)
{
    struct gpu31p_segment source[GPU31P_MAX_SEGMENTS], decoded[GPU31P_MAX_SEGMENTS];
    uint8_t first[GPU31P_MAX_SEGMENTS * 32], second[GPU31P_MAX_SEGMENTS * 32];
    size_t count, i, written, decoded_count;
    for (i = 0; i < GPU31P_MAX_SEGMENTS; ++i) {
        source[i].descriptor_phys = UINT64_C(0x10000000000) + i * 0x8000u;
        source[i].iova = UINT64_C(0xfffffc0000000000) + i * 0x8000u;
        source[i].remap = UINT64_C(0x20000000000) + i * 0x8000u;
        source[i].size = 0x4000;
        source[i].opaque = UINT32_MAX - (uint32_t)i;
    }
    for (count = 1; count <= GPU31P_MAX_SEGMENTS; ++count) {
        assert(gpu31p_encode(source, count, first, sizeof(first), &written) == GPU31P_OK);
        assert(written == count * 32);
        assert(gpu31p_decode(first, written, decoded, GPU31P_MAX_SEGMENTS, &decoded_count) == GPU31P_OK);
        assert(decoded_count == count);
        assert(gpu31p_encode(decoded, count, second, sizeof(second), &written) == GPU31P_OK);
        assert(memcmp(first, second, written) == 0);
    }
}

int main(void)
{
    golden_decode();
    golden_encode();
    unaligned_buffers();
    bad_lengths();
    capacity_and_transaction();
    zero_size_and_late_failure();
    overflow_domains();
    maximum_valid_span();
    alignment_policy();
    overlap_each_domain();
    null_arguments();
    all_counts_roundtrip();
    puts("GPU31P_SEGMENTS_PASS");
    return 0;
}

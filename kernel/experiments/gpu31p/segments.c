/* Original implementation of a public 32-byte little-endian descriptor shape.
 * This is a host/guest software contract, not a GPU driver or UAT encoder. */
#include "segments.h"

static uint64_t load_le(const uint8_t *p, unsigned int width)
{
    uint64_t value = 0;
    unsigned int i;
    for (i = 0; i < width; ++i)
        value |= (uint64_t)p[i] << (i * 8u);
    return value;
}

static void store_le(uint8_t *p, uint64_t value, unsigned int width)
{
    unsigned int i;
    for (i = 0; i < width; ++i)
        p[i] = (uint8_t)(value >> (i * 8u));
}

static uint64_t address(const struct gpu31p_segment *s, unsigned int domain)
{
    if (domain == 0)
        return s->descriptor_phys;
    return domain == 1 ? s->iova : s->remap;
}

enum gpu31p_error gpu31p_validate(const struct gpu31p_segment *segments,
                                size_t count, uint32_t granule)
{
    size_t i, j;
    unsigned int domain;
    if (!segments || !granule || (granule & (granule - 1u)))
        return GPU31P_ARGUMENT;
    if (!count || count > GPU31P_MAX_SEGMENTS)
        return GPU31P_LENGTH;
    for (i = 0; i < count; ++i) {
        if (!segments[i].size)
            return GPU31P_SPAN;
        if (segments[i].size % granule)
            return GPU31P_ALIGNMENT;
        for (domain = 0; domain < 3; ++domain) {
            uint64_t base = address(&segments[i], domain);
            if (base > UINT64_MAX - segments[i].size)
                return GPU31P_SPAN;
            if (base % granule)
                return GPU31P_ALIGNMENT;
        }
    }
    for (i = 0; i < count; ++i)
        for (j = i + 1; j < count; ++j)
            for (domain = 0; domain < 3; ++domain) {
                uint64_t a = address(&segments[i], domain);
                uint64_t b = address(&segments[j], domain);
                if (a < b + segments[j].size && b < a + segments[i].size)
                    return GPU31P_OVERLAP;
            }
    return GPU31P_OK;
}

enum gpu31p_error gpu31p_decode(const uint8_t *bytes, size_t length,
                              struct gpu31p_segment *segments, size_t capacity,
                              size_t *count)
{
    struct gpu31p_segment scratch[GPU31P_MAX_SEGMENTS];
    enum gpu31p_error result;
    size_t n, i;
    if (!bytes || !segments || !count)
        return GPU31P_ARGUMENT;
    if (!length || length % GPU31P_SEGMENT_BYTES ||
        length > GPU31P_MAX_SEGMENTS * GPU31P_SEGMENT_BYTES)
        return GPU31P_LENGTH;
    n = length / GPU31P_SEGMENT_BYTES;
    if (capacity < n)
        return GPU31P_CAPACITY;
    for (i = 0; i < n; ++i) {
        const uint8_t *p = bytes + i * GPU31P_SEGMENT_BYTES;
        scratch[i].descriptor_phys = load_le(p, 8);
        scratch[i].iova = load_le(p + 8, 8);
        scratch[i].remap = load_le(p + 16, 8);
        scratch[i].size = (uint32_t)load_le(p + 24, 4);
        scratch[i].opaque = (uint32_t)load_le(p + 28, 4);
    }
    result = gpu31p_validate(scratch, n, 1);
    if (result != GPU31P_OK)
        return result;
    for (i = 0; i < n; ++i)
        segments[i] = scratch[i];
    *count = n;
    return GPU31P_OK;
}

enum gpu31p_error gpu31p_encode(const struct gpu31p_segment *segments, size_t count,
                              uint8_t *bytes, size_t capacity, size_t *written)
{
    size_t i, length;
    enum gpu31p_error result;
    if (!segments || !bytes || !written)
        return GPU31P_ARGUMENT;
    if (!count || count > GPU31P_MAX_SEGMENTS)
        return GPU31P_LENGTH;
    length = count * GPU31P_SEGMENT_BYTES;
    if (capacity < length)
        return GPU31P_CAPACITY;
    result = gpu31p_validate(segments, count, 1);
    if (result != GPU31P_OK)
        return result;
    for (i = 0; i < count; ++i) {
        uint8_t *p = bytes + i * GPU31P_SEGMENT_BYTES;
        store_le(p, segments[i].descriptor_phys, 8);
        store_le(p + 8, segments[i].iova, 8);
        store_le(p + 16, segments[i].remap, 8);
        store_le(p + 24, segments[i].size, 4);
        store_le(p + 28, segments[i].opaque, 4);
    }
    *written = length;
    return GPU31P_OK;
}

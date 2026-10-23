/* Original offline ADT segment codec. No hardware or allocation operations. */
#ifndef ILINUX_GPU31P_SEGMENTS_H
#define ILINUX_GPU31P_SEGMENTS_H

#include <stddef.h>
#include <stdint.h>

#define GPU31P_SEGMENT_BYTES 32u
#define GPU31P_MAX_SEGMENTS 32u

/* Names follow the public ADT layout, not a claim about CPU address translation.
 * opaque is uninterpreted and must survive a round trip unchanged. */
struct gpu31p_segment {
    uint64_t descriptor_phys;
    uint64_t iova;
    uint64_t remap;
    uint32_t size;
    uint32_t opaque;
};

enum gpu31p_error {
    GPU31P_OK = 0,
    GPU31P_ARGUMENT,
    GPU31P_LENGTH,
    GPU31P_CAPACITY,
    GPU31P_SPAN,
    GPU31P_ALIGNMENT,
    GPU31P_OVERLAP
};

/* Validate one role's descriptor list. granule is an explicit caller policy,
 * not a discovered hardware page size. Address spaces of different roles must
 * be checked separately. End-exclusive overflow is rejected conservatively. */
enum gpu31p_error gpu31p_validate(const struct gpu31p_segment *segments,
                                size_t count, uint32_t granule);

/* Unaligned input/output buffers are allowed. Output is untouched on error.
 * The caller supplies genuinely accessible buffers of the stated capacities.
 * Buffers and struct arrays must not alias. The codec applies granule=1; callers
 * can separately require the observed 16 KiB alignment with gpu31p_validate. */
enum gpu31p_error gpu31p_decode(const uint8_t *bytes, size_t length,
                              struct gpu31p_segment *segments, size_t capacity,
                              size_t *count);
enum gpu31p_error gpu31p_encode(const struct gpu31p_segment *segments, size_t count,
                              uint8_t *bytes, size_t capacity, size_t *written);

#endif

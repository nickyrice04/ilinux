/* SPDX-License-Identifier: MIT */
#ifndef ILINUX_SPTM31Z_MEMORY_H
#define ILINUX_SPTM31Z_MEMORY_H

#include <stddef.h>
#include <stdint.h>

/* Original software bounds and API. These are not Apple wire structures. */
#define SPTM31Z_MAX_RESERVATIONS 16u
#define SPTM31Z_MAX_AVAILABLE (SPTM31Z_MAX_RESERVATIONS + 1u)

struct sptm31z_phys_range { uint64_t base, bytes; };
struct sptm31z_decoded_memory {
    struct sptm31z_phys_range ram;
    uint64_t monitor_first_available;
    uint64_t iboot_high_water;
    uint64_t page_bytes;
};
struct sptm31z_memory_plan {
    struct sptm31z_decoded_memory source;
    size_t reserved_count, available_count;
    struct sptm31z_phys_range reserved[SPTM31Z_MAX_RESERVATIONS];
    struct sptm31z_phys_range available[SPTM31Z_MAX_AVAILABLE];
    uint64_t available_bytes;
};
enum sptm31z_memory_status {
    SPTM31Z_MEMORY_OK = 0, SPTM31Z_MEMORY_ARGUMENT,
    SPTM31Z_MEMORY_ALIGNMENT, SPTM31Z_MEMORY_RANGE,
    SPTM31Z_MEMORY_OVERLAP
};

/* Produce the exact page-aligned complement of retained reservations within
 * [monitor_first_available, ram.end). iBoot's high-water mark is compared and
 * retained, never substituted for the monitor boundary. Both marks are physical
 * addresses; a monitor boundary below the iBoot high-water mark is inconsistent
 * and refused, never repaired by taking their maximum. Reservations must be
 * nonempty, disjoint, wholly inside ram and aligned to page_bytes; their order
 * is immaterial. Zero reservations accepts a NULL array. An empty result is a
 * valid plan with zero available_count, not permission to reclaim anything.
 *
 * Caller-decoded inputs are assumptions: the caller must authenticate/bind the
 * actual monitor handoff, address domain, version, bounds, allocation ownership
 * and page granule before using any result. This does not inspect a native ABI,
 * dereference a physical address, create mappings or establish permissions.
 * The caller must include every additional live image, argument, stack, table,
 * firmware and device reservation that intersects the candidate allocation
 * range. Their ownership must remain in effect for the entire plan lifetime.
 * The copied reservations cannot be released through this API. Constructing a
 * new plan does not establish that previously reserved storage is reusable.
 *
 * No callbacks, allocation or hardware operations. Invalid input leaves output
 * unchanged. Caller serializes access, supplies valid C objects/array lengths,
 * and keeps output disjoint from input objects. NOT_DEPLOYABLE: successful
 * arithmetic validation is not qualification of a native monitor profile.
 */
enum sptm31z_memory_status sptm31z_plan_memory(
    const struct sptm31z_decoded_memory *memory,
    const struct sptm31z_phys_range *reserved, size_t reserved_count,
    struct sptm31z_memory_plan *output);

#endif

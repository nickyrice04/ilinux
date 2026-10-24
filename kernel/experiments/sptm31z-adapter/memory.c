/* SPDX-License-Identifier: MIT */
#include "memory.h"

static int range_end(struct sptm31z_phys_range range, uint64_t *end)
{
    if (range.bytes == 0 || range.base > UINT64_MAX - range.bytes)
        return 0;
    *end = range.base + range.bytes;
    return 1;
}

static void append(struct sptm31z_memory_plan *plan, uint64_t begin, uint64_t end)
{
    if (begin == end)
        return;
    plan->available[plan->available_count].base = begin;
    plan->available[plan->available_count].bytes = end - begin;
    plan->available_count++;
    plan->available_bytes += end - begin;
}

enum sptm31z_memory_status sptm31z_plan_memory(
    const struct sptm31z_decoded_memory *memory,
    const struct sptm31z_phys_range *reserved, size_t reserved_count,
    struct sptm31z_memory_plan *output)
{
    struct sptm31z_memory_plan plan = {0};
    uint64_t end, cursor, page;
    size_t i, j;

    if (!memory || !output || reserved_count > SPTM31Z_MAX_RESERVATIONS ||
        (reserved_count && !reserved))
        return SPTM31Z_MEMORY_ARGUMENT;
    page = memory->page_bytes;
    if (!page || (page & (page - 1)))
        return SPTM31Z_MEMORY_ALIGNMENT;
    if (!range_end(memory->ram, &end) ||
        memory->monitor_first_available < memory->ram.base ||
        memory->monitor_first_available > end ||
        memory->iboot_high_water < memory->ram.base || memory->iboot_high_water > end ||
        memory->monitor_first_available < memory->iboot_high_water)
        return SPTM31Z_MEMORY_RANGE;
    if ((memory->ram.base | memory->ram.bytes | memory->monitor_first_available |
         memory->iboot_high_water) & (page - 1))
        return SPTM31Z_MEMORY_ALIGNMENT;

    plan.source = *memory;
    plan.reserved_count = reserved_count;
    for (i = 0; i < reserved_count; i++) {
        uint64_t reservation_end;
        if (!range_end(reserved[i], &reservation_end) ||
            reserved[i].base < memory->ram.base || reservation_end > end)
            return SPTM31Z_MEMORY_RANGE;
        if ((reserved[i].base | reserved[i].bytes) & (page - 1))
            return SPTM31Z_MEMORY_ALIGNMENT;
        plan.reserved[i] = reserved[i];
    }
    for (i = 1; i < reserved_count; i++) {
        struct sptm31z_phys_range item = plan.reserved[i];
        j = i;
        while (j && plan.reserved[j - 1].base > item.base) {
            plan.reserved[j] = plan.reserved[j - 1];
            j--;
        }
        plan.reserved[j] = item;
    }
    for (i = 1; i < reserved_count; i++) {
        uint64_t previous_end = plan.reserved[i - 1].base + plan.reserved[i - 1].bytes;
        if (previous_end > plan.reserved[i].base)
            return SPTM31Z_MEMORY_OVERLAP;
    }

    cursor = memory->monitor_first_available;
    for (i = 0; i < reserved_count; i++) {
        uint64_t reservation_end = plan.reserved[i].base + plan.reserved[i].bytes;
        if (reservation_end <= cursor)
            continue;
        if (plan.reserved[i].base > cursor)
            append(&plan, cursor, plan.reserved[i].base);
        cursor = reservation_end;
    }
    append(&plan, cursor, end);
    *output = plan;
    return SPTM31Z_MEMORY_OK;
}

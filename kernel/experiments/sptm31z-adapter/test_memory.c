/* SPDX-License-Identifier: MIT */
#include "memory.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static const uint64_t page = UINT64_C(0x4000);
static const uint64_t base = UINT64_C(0x10000000000);

static struct sptm31z_decoded_memory example(void)
{
    struct sptm31z_decoded_memory value = {{base, 16 * page}, base + 4 * page,
                                         base + 2 * page, page};
    return value;
}

static void unchanged(enum sptm31z_memory_status expected,
                      const struct sptm31z_decoded_memory *memory,
                      const struct sptm31z_phys_range *reserved, size_t count)
{
    struct sptm31z_memory_plan output, before;
    memset(&output, 0xa5, sizeof(output));
    memcpy(&before, &output, sizeof(output));
    assert(sptm31z_plan_memory(memory, reserved, count, &output) == expected);
    assert(memcmp(&output, &before, sizeof(output)) == 0);
}

static void high_water_counterexample(void)
{
    struct sptm31z_decoded_memory memory = example();
    struct sptm31z_memory_plan output;
    assert(memory.iboot_high_water + page <= memory.monitor_first_available);
    /* An allocation at the old iBoot mark would overwrite a monitor-used page.
     * The first returned page must start at the later monitor boundary. */
    assert(sptm31z_plan_memory(&memory, NULL, 0, &output) == SPTM31Z_MEMORY_OK);
    assert(output.available_count == 1);
    assert(output.available[0].base == base + 4 * page);
    assert(output.available[0].bytes == 12 * page);
    assert(output.available_bytes == 12 * page);
    memory.iboot_high_water = base + page;
    assert(output.source.iboot_high_water == base + 2 * page);
}

static void reservation_edges_and_snapshot(void)
{
    struct sptm31z_decoded_memory memory = example();
    struct sptm31z_phys_range reserved[] = {
        {base + 10 * page, 2 * page}, {base + 3 * page, 2 * page},
        {base, page}, {base + 15 * page, page}
    };
    struct sptm31z_memory_plan output;
    assert(sptm31z_plan_memory(&memory, reserved, 4, &output) == SPTM31Z_MEMORY_OK);
    assert(output.available_count == 2);
    assert(output.available[0].base == base + 5 * page && output.available[0].bytes == 5 * page);
    assert(output.available[1].base == base + 12 * page && output.available[1].bytes == 3 * page);
    assert(output.available_bytes == 8 * page);
    assert(output.reserved[0].base == base && output.reserved[3].base == base + 15 * page);
    reserved[0].bytes = 0;
    memory.monitor_first_available = base;
    assert(output.reserved[2].bytes == 2 * page);
    assert(output.source.monitor_first_available == base + 4 * page);
}

static void empty_and_touching(void)
{
    struct sptm31z_decoded_memory memory = example();
    struct sptm31z_phys_range reserved[] = {{base + 4 * page, 5 * page},
                                           {base + 9 * page, 7 * page}};
    struct sptm31z_memory_plan output;
    assert(sptm31z_plan_memory(&memory, reserved, 2, &output) == SPTM31Z_MEMORY_OK);
    assert(output.available_count == 0 && output.available_bytes == 0);
    memory.monitor_first_available = base + memory.ram.bytes;
    assert(sptm31z_plan_memory(&memory, NULL, 0, &output) == SPTM31Z_MEMORY_OK);
    assert(output.available_count == 0);
}

static void invalid_arguments_and_alignment(void)
{
    struct sptm31z_decoded_memory memory = example();
    struct sptm31z_phys_range reserved = {base + 5 * page, page};
    unchanged(SPTM31Z_MEMORY_ARGUMENT, NULL, NULL, 0);
    unchanged(SPTM31Z_MEMORY_ARGUMENT, &memory, NULL, 1);
    unchanged(SPTM31Z_MEMORY_ARGUMENT, &memory, &reserved, SPTM31Z_MAX_RESERVATIONS + 1);
    assert(sptm31z_plan_memory(&memory, NULL, 0, NULL) == SPTM31Z_MEMORY_ARGUMENT);
    memory.page_bytes = 0;
    unchanged(SPTM31Z_MEMORY_ALIGNMENT, &memory, NULL, 0);
    memory.page_bytes = 3;
    unchanged(SPTM31Z_MEMORY_ALIGNMENT, &memory, NULL, 0);
    memory = example();
    memory.monitor_first_available++;
    unchanged(SPTM31Z_MEMORY_ALIGNMENT, &memory, NULL, 0);
    memory = example();
    reserved.base++;
    unchanged(SPTM31Z_MEMORY_ALIGNMENT, &memory, &reserved, 1);
    reserved.base--;
    reserved.bytes--;
    unchanged(SPTM31Z_MEMORY_ALIGNMENT, &memory, &reserved, 1);
}

static void invalid_ranges(void)
{
    struct sptm31z_decoded_memory memory = example();
    struct sptm31z_phys_range reserved;
    memory.ram.bytes = 0;
    unchanged(SPTM31Z_MEMORY_RANGE, &memory, NULL, 0);
    memory = example();
    memory.ram.base = UINT64_MAX - page + 1;
    memory.ram.bytes = page;
    unchanged(SPTM31Z_MEMORY_RANGE, &memory, NULL, 0);
    memory = example();
    memory.monitor_first_available = base - page;
    unchanged(SPTM31Z_MEMORY_RANGE, &memory, NULL, 0);
    memory = example();
    memory.monitor_first_available = base + 17 * page;
    unchanged(SPTM31Z_MEMORY_RANGE, &memory, NULL, 0);
    memory = example();
    memory.iboot_high_water = base + 17 * page;
    unchanged(SPTM31Z_MEMORY_RANGE, &memory, NULL, 0);
    memory = example();
    memory.iboot_high_water = memory.monitor_first_available + page;
    unchanged(SPTM31Z_MEMORY_RANGE, &memory, NULL, 0);
    memory = example();
    reserved = (struct sptm31z_phys_range){base - page, 2 * page};
    unchanged(SPTM31Z_MEMORY_RANGE, &memory, &reserved, 1);
    reserved = (struct sptm31z_phys_range){base + 15 * page, 2 * page};
    unchanged(SPTM31Z_MEMORY_RANGE, &memory, &reserved, 1);
    reserved = (struct sptm31z_phys_range){UINT64_MAX, 1};
    unchanged(SPTM31Z_MEMORY_RANGE, &memory, &reserved, 1);
    reserved = (struct sptm31z_phys_range){base, 0};
    unchanged(SPTM31Z_MEMORY_RANGE, &memory, &reserved, 1);
}

static void overlapping_reservations_refuse(void)
{
    struct sptm31z_decoded_memory memory = example();
    struct sptm31z_phys_range reserved[] = {{base + 5 * page, 2 * page},
                                           {base + 6 * page, page}};
    unchanged(SPTM31Z_MEMORY_OVERLAP, &memory, reserved, 2);
    reserved[1] = reserved[0];
    unchanged(SPTM31Z_MEMORY_OVERLAP, &memory, reserved, 2);
    /* Even overlaps wholly below the allocation boundary are inconsistent. */
    reserved[0] = reserved[1] = (struct sptm31z_phys_range){base, page};
    unchanged(SPTM31Z_MEMORY_OVERLAP, &memory, reserved, 2);
}

static void maximum_split(void)
{
    struct sptm31z_decoded_memory memory = {{base, 33 * page}, base, base, page};
    struct sptm31z_phys_range reserved[SPTM31Z_MAX_RESERVATIONS];
    struct sptm31z_memory_plan output;
    size_t i;
    for (i = 0; i < SPTM31Z_MAX_RESERVATIONS; i++)
        reserved[i] = (struct sptm31z_phys_range){base + (31 - 2 * i) * page, page};
    assert(sptm31z_plan_memory(&memory, reserved, SPTM31Z_MAX_RESERVATIONS, &output) ==
           SPTM31Z_MEMORY_OK);
    assert(output.available_count == SPTM31Z_MAX_AVAILABLE);
    assert(output.available_bytes == 17 * page);
    for (i = 0; i < output.available_count; i++)
        assert(output.available[i].base == base + 2 * i * page && output.available[i].bytes == page);
}

static void exhaustive_page_complement(void)
{
    unsigned mask, boundary;
    /* Independent bitmap oracle covers every 8-page reservation subset at
     * every monitor boundary, including empty, clipped and adjacent cases. */
    for (mask = 0; mask < 256; mask++) {
        for (boundary = 0; boundary <= 8; boundary++) {
            struct sptm31z_decoded_memory memory = {{base, 8 * page}, base + boundary * page,
                                                   base, page};
            struct sptm31z_phys_range reserved[8];
            struct sptm31z_memory_plan output;
            size_t count = 0, i, j;
            unsigned seen = 0, wanted = 0;
            for (i = 0; i < 8; i++) {
                if (mask & (1u << i))
                    reserved[count++] = (struct sptm31z_phys_range){base + i * page, page};
                else if (i >= boundary)
                    wanted |= 1u << i;
            }
            assert(sptm31z_plan_memory(&memory, reserved, count, &output) == SPTM31Z_MEMORY_OK);
            for (i = 0; i < output.available_count; i++) {
                assert(output.available[i].base >= memory.monitor_first_available);
                for (j = 0; j < output.available[i].bytes / page; j++) {
                    unsigned bit = 1u << ((output.available[i].base - base) / page + j);
                    assert(!(seen & bit));
                    seen |= bit;
                }
            }
            assert(seen == wanted);
        }
    }
}

int main(void)
{
    high_water_counterexample();
    reservation_edges_and_snapshot();
    empty_and_touching();
    invalid_arguments_and_alignment();
    invalid_ranges();
    overlapping_reservations_refuse();
    maximum_split();
    exhaustive_page_complement();
    puts("SPTM31Z_MEMORY_PASS groups=8 bitmap_cases=2304 native=NOT_DEPLOYABLE");
    return 0;
}

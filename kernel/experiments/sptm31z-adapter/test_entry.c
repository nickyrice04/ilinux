/* SPDX-License-Identifier: MIT */
#include "entry.h"
#include "memory.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static struct sptm31z_entry_snapshot capture(uint64_t reason)
{
    struct sptm31z_entry_snapshot entry;
    struct sptm31z_entry_words words = {reason, 1, UINT64_MAX};
    enum sptm31z_entry_status expected = reason <= 4 ? SPTM31Z_ENTRY_OK :
                                                       SPTM31Z_ENTRY_UNKNOWN_REASON;
    assert(sptm31z_capture_entry(SPTM31Z_T6050_25G83_OBSERVED, words, &entry) == expected);
    return entry;
}

static void known_reasons_and_roles(void)
{
    const enum sptm31z_kind expected[] = {SPTM31Z_COLD, SPTM31Z_SECONDARY,
        SPTM31Z_WARM, SPTM31Z_HIBERNATION, SPTM31Z_PANIC};
    uint64_t reason;
    for (reason = 0; reason <= 4; reason++) {
        struct sptm31z_entry_snapshot entry = capture(reason);
        struct sptm31z_boot_words boot = {21, 22};
        struct sptm31z_panic_words panic = {23, 24};
        assert(entry.kind == expected[reason]);
        assert(entry.raw.x0 == reason && entry.raw.x1 == 1 && entry.raw.x2 == UINT64_MAX);
        assert(sptm31z_get_boot_words(&entry, &boot) ==
               (reason == 0 ? SPTM31Z_ENTRY_OK : SPTM31Z_ENTRY_ROLE));
        if (reason == 0)
            assert(boot.iboot_arguments == 1 && boot.monitor_arguments == UINT64_MAX);
        else
            assert(boot.iboot_arguments == 21 && boot.monitor_arguments == 22);
        assert(sptm31z_get_panic_words(&entry, &panic) ==
               (reason == 4 ? SPTM31Z_ENTRY_OK : SPTM31Z_ENTRY_ROLE));
        if (reason == 4)
            assert(panic.message == 1 && panic.core_dump_flag == UINT64_MAX);
        else
            assert(panic.message == 23 && panic.core_dump_flag == 24);
        /* No truncation, dereference or replacement of the raw observation. */
        assert(entry.raw.x1 == 1 && entry.raw.x2 == UINT64_MAX);
    }
}

static void full_width_unknowns(void)
{
    const uint64_t reasons[] = {5, 255, 256, 257, 260, UINT64_C(0x100000000), UINT64_MAX};
    size_t i;
    for (i = 0; i < sizeof(reasons) / sizeof(reasons[0]); i++) {
        struct sptm31z_entry_snapshot entry = capture(reasons[i]);
        struct sptm31z_boot_words boot = {21, 22};
        struct sptm31z_panic_words panic = {23, 24};
        assert(entry.kind == SPTM31Z_UNRECOGNIZED && entry.raw.x0 == reasons[i]);
        assert(sptm31z_get_boot_words(&entry, &boot) == SPTM31Z_ENTRY_ROLE);
        assert(sptm31z_get_panic_words(&entry, &panic) == SPTM31Z_ENTRY_ROLE);
        assert(boot.iboot_arguments == 21 && boot.monitor_arguments == 22);
        assert(panic.message == 23 && panic.core_dump_flag == 24);
    }
}

static void invalid_profiles_and_snapshots(void)
{
    struct sptm31z_entry_snapshot entry, before;
    struct sptm31z_entry_words words = {0, 1, 2};
    struct sptm31z_boot_words boot = {21, 22};
    struct sptm31z_panic_words panic = {23, 24};
    memset(&entry, 0xa5, sizeof(entry));
    memcpy(&before, &entry, sizeof(entry));
    assert(sptm31z_capture_entry(SPTM31Z_NO_PROFILE, words, &entry) == SPTM31Z_ENTRY_PROFILE);
    assert(memcmp(&entry, &before, sizeof(entry)) == 0);
    assert(sptm31z_capture_entry((enum sptm31z_profile)99, words, &entry) == SPTM31Z_ENTRY_PROFILE);
    assert(memcmp(&entry, &before, sizeof(entry)) == 0);
    assert(sptm31z_capture_entry(SPTM31Z_T6050_25G83_OBSERVED, words, NULL) == SPTM31Z_ENTRY_ARGUMENT);
    assert(sptm31z_get_boot_words(NULL, &boot) == SPTM31Z_ENTRY_ARGUMENT);
    assert(sptm31z_get_panic_words(NULL, &panic) == SPTM31Z_ENTRY_ARGUMENT);
    entry = capture(0);
    assert(sptm31z_get_boot_words(&entry, NULL) == SPTM31Z_ENTRY_ARGUMENT);
    assert(sptm31z_get_panic_words(&entry, NULL) == SPTM31Z_ENTRY_ARGUMENT);
    entry.kind = SPTM31Z_PANIC;
    assert(sptm31z_get_boot_words(&entry, &boot) == SPTM31Z_ENTRY_ROLE);
    assert(sptm31z_get_panic_words(&entry, &panic) == SPTM31Z_ENTRY_ROLE);
    entry = capture(0);
    entry.profile = SPTM31Z_NO_PROFILE;
    assert(sptm31z_get_boot_words(&entry, &boot) == SPTM31Z_ENTRY_PROFILE);
    assert(sptm31z_get_panic_words(&entry, &panic) == SPTM31Z_ENTRY_PROFILE);
    assert(boot.iboot_arguments == 21 && boot.monitor_arguments == 22);
    assert(panic.message == 23 && panic.core_dump_flag == 24);
}

static void opaque_copy_and_alignment(void)
{
    const uint8_t physical_value[8] = {0x08, 0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01};
    uint8_t storage[SPTM31Z_MONITOR_BYTES + 1];
    uint8_t *bytes = storage + 1;
    struct sptm31z_entry_snapshot entry = capture(0);
    struct sptm31z_monitor_snapshot output;
    size_t i;
    for (i = 0; i < SPTM31Z_MONITOR_BYTES; i++)
        bytes[i] = (uint8_t)(i * 13 + 7);
    assert(sptm31z_snapshot_monitor(&entry, bytes, SPTM31Z_MONITOR_BYTES, &output) ==
           SPTM31Z_ENTRY_OK);
    assert(memcmp(output.private_bytes, bytes, SPTM31Z_MONITOR_BYTES) == 0);
    memset(bytes, 0, SPTM31Z_MONITOR_BYTES);
    entry.raw.x2 = 0;
    assert(output.entry.raw.x2 == UINT64_MAX);
    for (i = 0; i < SPTM31Z_MONITOR_BYTES; i++)
        assert(output.private_bytes[i] == (uint8_t)(i * 13 + 7));
    memcpy(bytes + 24, physical_value, 8);
    entry = output.entry;
    assert(sptm31z_snapshot_monitor(&entry, bytes, SPTM31Z_MONITOR_BYTES, &output) ==
           SPTM31Z_ENTRY_OK);
    assert(output.first_available.value == UINT64_C(0x0102030405060708));
}

static void rejected_copy(enum sptm31z_entry_status expected,
    const struct sptm31z_entry_snapshot *entry, const uint8_t *bytes, size_t length)
{
    struct sptm31z_monitor_snapshot output, before;
    memset(&output, 0xa5, sizeof(output));
    memcpy(&before, &output, sizeof(output));
    assert(sptm31z_snapshot_monitor(entry, bytes, length, &output) == expected);
    assert(memcmp(&output, &before, sizeof(output)) == 0);
}

static void exact_length_and_null_rejections(void)
{
    struct sptm31z_entry_snapshot entry = capture(0);
    uint8_t byte = 0;
    size_t length;
    /* A one-byte input makes an accidental read-before-length-check detectable
     * under the sanitizer; no overlong input is actually supplied. */
    for (length = 0; length < SPTM31Z_MONITOR_BYTES; length++)
        rejected_copy(SPTM31Z_ENTRY_LENGTH, &entry, &byte, length);
    rejected_copy(SPTM31Z_ENTRY_LENGTH, &entry, &byte, SPTM31Z_MONITOR_BYTES + 1);
    rejected_copy(SPTM31Z_ENTRY_LENGTH, &entry, &byte, SIZE_MAX);
    /* Both shorter measured SDK sizes are already in the exhaustive loop.
     * All larger measured SDK sizes are independently refused as well. */
    rejected_copy(SPTM31Z_ENTRY_LENGTH, &entry, &byte, 856);
    rejected_copy(SPTM31Z_ENTRY_LENGTH, &entry, &byte, 864);
    rejected_copy(SPTM31Z_ENTRY_LENGTH, &entry, &byte, 872);
    rejected_copy(SPTM31Z_ENTRY_LENGTH, &entry, &byte, 880);
    rejected_copy(SPTM31Z_ENTRY_ARGUMENT, &entry, NULL, SPTM31Z_MONITOR_BYTES);
    rejected_copy(SPTM31Z_ENTRY_ARGUMENT, NULL, &byte, SPTM31Z_MONITOR_BYTES);
    assert(sptm31z_snapshot_monitor(&entry, &byte, SPTM31Z_MONITOR_BYTES, NULL) ==
           SPTM31Z_ENTRY_ARGUMENT);
}

static void cold_copy_only(void)
{
    uint8_t byte = 0;
    uint64_t reason;
    for (reason = 1; reason <= 5; reason++) {
        struct sptm31z_entry_snapshot entry = capture(reason);
        rejected_copy(SPTM31Z_ENTRY_ROLE, &entry, &byte, SPTM31Z_MONITOR_BYTES);
    }
    {
        struct sptm31z_entry_snapshot entry = capture(0);
        entry.raw.x0 = 4;
        rejected_copy(SPTM31Z_ENTRY_ROLE, &entry, &byte, SPTM31Z_MONITOR_BYTES);
        entry = capture(0);
        entry.profile = SPTM31Z_NO_PROFILE;
        rejected_copy(SPTM31Z_ENTRY_PROFILE, &entry, &byte, SPTM31Z_MONITOR_BYTES);
    }
}

static void separate_profile_and_memory_validation(void)
{
    uint8_t bytes[SPTM31Z_MONITOR_BYTES] = {0};
    struct sptm31z_entry_snapshot entry = capture(0);
    struct sptm31z_monitor_snapshot output;
    const uint8_t opaque_values[] = {0, 10, 12, 255};
    size_t i;
    for (i = 0; i < sizeof(opaque_values); i++) {
        /* Arbitrary data does not select a profile or qualify native memory. */
        memset(bytes, opaque_values[i], sizeof(bytes));
        assert(sptm31z_snapshot_monitor(&entry, bytes, sizeof(bytes), &output) == SPTM31Z_ENTRY_OK);
        assert(output.entry.profile == SPTM31Z_T6050_25G83_OBSERVED);
        assert(memcmp(output.private_bytes, bytes, sizeof(bytes)) == 0);
    }
    entry.profile = SPTM31Z_NO_PROFILE;
    rejected_copy(SPTM31Z_ENTRY_PROFILE, &entry, bytes, sizeof(bytes));
    /* Snapshot success does not supply any RAM bounds. */
    {
        struct sptm31z_decoded_memory memory = {{0, 0}, 0, 0, 0x4000};
        struct sptm31z_memory_plan plan;
        assert(sptm31z_plan_memory(&memory, NULL, 0, &plan) == SPTM31Z_MEMORY_RANGE);
    }
    {
        /* Fixed synthetic little-endian value is physical base + four pages;
         * the independently supplied old iBoot mark is only base + two pages. */
        const uint8_t physical_value[8] = {0, 0, 1, 0, 0, 1, 0, 0};
        const uint64_t base = UINT64_C(0x10000000000), page = 0x4000;
        struct sptm31z_decoded_memory memory = {{base, 16 * page}, 0, base + 2 * page, page};
        struct sptm31z_phys_range reservation = {base + 8 * page, 2 * page};
        struct sptm31z_memory_plan plan;
        entry = capture(0);
        memset(bytes, 0, sizeof(bytes));
        memcpy(bytes + 24, physical_value, 8);
        assert(sptm31z_snapshot_monitor(&entry, bytes, sizeof(bytes), &output) == SPTM31Z_ENTRY_OK);
        memory.monitor_first_available = output.first_available.value;
        assert(sptm31z_plan_memory(&memory, &reservation, 1, &plan) == SPTM31Z_MEMORY_OK);
        assert(plan.available_count == 2 && plan.available_bytes == 10 * page);
        assert(plan.available[0].base == base + 4 * page && plan.available[0].bytes == 4 * page);
        assert(plan.available[1].base == base + 10 * page && plan.available[1].bytes == 6 * page);
        memset(bytes + 24, 0xff, 8);
        assert(sptm31z_snapshot_monitor(&entry, bytes, sizeof(bytes), &output) == SPTM31Z_ENTRY_OK);
        assert(output.first_available.value == UINT64_MAX);
        memory.monitor_first_available = output.first_available.value;
        assert(sptm31z_plan_memory(&memory, &reservation, 1, &plan) == SPTM31Z_MEMORY_RANGE);
    }
}

static void every_byte_position(void)
{
    uint8_t bytes[SPTM31Z_MONITOR_BYTES] = {0};
    struct sptm31z_entry_snapshot entry = capture(0);
    struct sptm31z_monitor_snapshot output;
    size_t position, i;
    for (position = 0; position < SPTM31Z_MONITOR_BYTES; position++) {
        memset(bytes, 0, sizeof(bytes));
        bytes[position] = 0xa7;
        assert(sptm31z_snapshot_monitor(&entry, bytes, sizeof(bytes), &output) == SPTM31Z_ENTRY_OK);
        for (i = 0; i < SPTM31Z_MONITOR_BYTES; i++)
            assert(output.private_bytes[i] == (i == position ? 0xa7 : 0));
    }
}

int main(void)
{
    known_reasons_and_roles();
    full_width_unknowns();
    invalid_profiles_and_snapshots();
    opaque_copy_and_alignment();
    exact_length_and_null_rejections();
    cold_copy_only();
    separate_profile_and_memory_validation();
    every_byte_position();
    puts("SPTM31Z_ENTRY_PASS groups=8 length_cases=854 byte_position_cases=848 native=NOT_DEPLOYABLE");
    return 0;
}

/* SPDX-License-Identifier: MIT */
#include "registration.h"
#include "../sptm31z-adapter/memory.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "topology_fixture.h"

static struct sptm31z_entry_snapshot cold(void)
{
    struct sptm31z_entry_snapshot entry;
    const struct sptm31z_entry_words words = {0, 1, UINT64_MAX};
    assert(sptm31z_capture_entry(SPTM31Z_T6050_25G83_OBSERVED, words, &entry) == SPTM31Z_ENTRY_OK);
    return entry;
}

static void reject(enum sptm31aa_status expected,
    const struct sptm31z_entry_snapshot *entry, const struct sptm31aa_cpu_record *records,
    size_t count, struct sptm31aa_boot_identity boot)
{
    struct sptm31aa_registration_plan plan, before;
    memset(&plan, 0xa5, sizeof(plan));
    memcpy(&before, &plan, sizeof(plan));
    assert(sptm31aa_prepare_registration(entry, records, count, boot, &plan) == expected);
    assert(memcmp(&plan, &before, sizeof(plan)) == 0);
}

static void exact_mapping(const struct sptm31aa_registration_plan *plan,
    const struct sptm31aa_cpu_record *records, size_t count)
{
    size_t i;
    assert(plan->count == count);
    for (i = 0; i < count; i++) {
        assert(plan->registrations[i].logical_ordinal == i);
        assert(plan->registrations[i].source_cpu_id == records[i].source_cpu_id);
        assert(plan->registrations[i].source_class == records[i].source_class);
        assert(plan->registrations[i].physical_id_argument == records[i].adt_reg);
    }
}

static void sparse_labels_and_owned_output(void)
{
    struct sptm31z_entry_snapshot entry = cold();
    struct sptm31aa_cpu_record records[] = {{900, 77, 0x203}, {12, 80, 1}, {600, UINT32_MAX, 0x101}};
    struct sptm31aa_boot_identity boot = {900, 0x203};
    struct sptm31aa_registration_plan plan;
    assert(sptm31aa_prepare_registration(&entry, records, 3, boot, &plan) == SPTM31AA_OK);
    exact_mapping(&plan, records, 3);
    records[1].adt_reg = 99;
    records[1].source_class = 0;
    entry.raw.x2 = 0;
    boot.adt_reg = 0;
    assert(plan.registrations[1].physical_id_argument == 1 && plan.registrations[1].source_class == 80);
    assert(plan.entry.raw.x2 == UINT64_MAX && plan.boot.adt_reg == 0x203);
}

static void arguments_and_count(void)
{
    struct sptm31z_entry_snapshot entry = cold();
    struct sptm31aa_cpu_record record = {7, 0, 0};
    struct sptm31aa_boot_identity boot = {7, 0};
    reject(SPTM31AA_ARGUMENT, NULL, &record, 1, boot);
    reject(SPTM31AA_ARGUMENT, &entry, NULL, 1, boot);
    assert(sptm31aa_prepare_registration(&entry, &record, 1, boot, NULL) == SPTM31AA_ARGUMENT);
    reject(SPTM31AA_COUNT, &entry, &record, 0, boot);
    /* Oversized count must be refused before reading beyond this one record. */
    reject(SPTM31AA_COUNT, &entry, &record, SPTM31AA_MAX_CPUS + 1, boot);
    reject(SPTM31AA_COUNT, &entry, &record, SIZE_MAX, boot);
}

static void entry_roles_and_integrity(void)
{
    struct sptm31aa_cpu_record record = {0, 0, 0};
    struct sptm31aa_boot_identity boot = {0, 0};
    const uint64_t reasons[] = {1, 2, 3, 4, 5, 256, UINT64_MAX};
    size_t i;
    for (i = 0; i < sizeof(reasons) / sizeof(reasons[0]); i++) {
        struct sptm31z_entry_snapshot entry;
        struct sptm31z_entry_words words = {reasons[i], 1, 2};
        enum sptm31z_entry_status status = sptm31z_capture_entry(SPTM31Z_T6050_25G83_OBSERVED, words, &entry);
        assert(status == SPTM31Z_ENTRY_OK || status == SPTM31Z_ENTRY_UNKNOWN_REASON);
        reject(SPTM31AA_ENTRY, &entry, &record, 1, boot);
    }
    {
        struct sptm31z_entry_snapshot entry = cold();
        entry.kind = SPTM31Z_PANIC;
        reject(SPTM31AA_ENTRY, &entry, &record, 1, boot);
        entry = cold();
        entry.profile = SPTM31Z_NO_PROFILE;
        reject(SPTM31AA_ENTRY, &entry, &record, 1, boot);
    }
}

static void affinity_width_and_zero_extension(void)
{
    struct sptm31z_entry_snapshot entry = cold();
    struct sptm31aa_cpu_record records[] = {{0, 0, UINT32_MAX}, {1, 0, 0x80000000}, {2, 0, 0}};
    struct sptm31aa_boot_identity boot = {0, UINT32_MAX};
    struct sptm31aa_registration_plan plan;
    assert(sptm31aa_prepare_registration(&entry, records, 3, boot, &plan) == SPTM31AA_OK);
    assert(plan.registrations[0].physical_id_argument == UINT64_C(0xffffffff));
    assert(plan.registrations[1].physical_id_argument == UINT64_C(0x80000000));
    records[2].adt_reg = UINT64_C(1) << 32;
    reject(SPTM31AA_AFFINITY_WIDTH, &entry, records, 3, boot);
    records[2].adt_reg = UINT64_MAX;
    reject(SPTM31AA_AFFINITY_WIDTH, &entry, records, 3, boot);
    records[2].adt_reg = 0;
    boot.adt_reg = UINT64_C(1) << 32;
    reject(SPTM31AA_AFFINITY_WIDTH, &entry, records, 3, boot);
}

static void boot_identity_must_match_first(void)
{
    struct sptm31z_entry_snapshot entry = cold();
    const struct sptm31aa_cpu_record records[] = {{7, 0, 2}, {8, 0, 3}, {9, 0, 4}};
    struct sptm31aa_boot_identity boot = {8, 3};
    reject(SPTM31AA_BOOT_ORDER, &entry, records, 3, boot);
    boot = (struct sptm31aa_boot_identity){7, 3};
    reject(SPTM31AA_BOOT_ORDER, &entry, records, 3, boot);
    boot = (struct sptm31aa_boot_identity){8, 2};
    reject(SPTM31AA_BOOT_ORDER, &entry, records, 3, boot);
    boot = (struct sptm31aa_boot_identity){99, 99};
    reject(SPTM31AA_BOOT_ORDER, &entry, records, 3, boot);
}

static void duplicate_pairs(void)
{
    struct sptm31z_entry_snapshot entry = cold();
    struct sptm31aa_boot_identity boot = {100, 0};
    struct sptm31aa_cpu_record records[8];
    size_t a, b, i;
    for (a = 0; a < 8; a++) {
        for (b = a + 1; b < 8; b++) {
            for (i = 0; i < 8; i++)
                records[i] = (struct sptm31aa_cpu_record){(uint32_t)(100 + i), 0, i};
            records[b].source_cpu_id = records[a].source_cpu_id;
            reject(SPTM31AA_DUPLICATE_SOURCE, &entry, records, 8, boot);
            records[b].source_cpu_id = (uint32_t)(100 + b);
            records[b].adt_reg = records[a].adt_reg;
            reject(SPTM31AA_DUPLICATE_AFFINITY, &entry, records, 8, boot);
        }
    }
}

static void maximum_capacity(void)
{
    struct sptm31z_entry_snapshot entry = cold();
    struct sptm31aa_cpu_record records[SPTM31AA_MAX_CPUS];
    struct sptm31aa_registration_plan plan;
    struct sptm31aa_boot_identity boot = {UINT32_MAX, 0};
    size_t i;
    for (i = 0; i < SPTM31AA_MAX_CPUS; i++)
        records[i] = (struct sptm31aa_cpu_record){UINT32_MAX - (uint32_t)i, (uint32_t)(i % 3), i * 0x100};
    assert(sptm31aa_prepare_registration(&entry, records, SPTM31AA_MAX_CPUS, boot, &plan) == SPTM31AA_OK);
    exact_mapping(&plan, records, SPTM31AA_MAX_CPUS);
    for (i = 0; i < SPTM31AA_MAX_CPUS; i++) {
        uint64_t old = records[i].adt_reg;
        records[i].adt_reg |= UINT64_C(1) << 32;
        reject(SPTM31AA_AFFINITY_WIDTH, &entry, records, SPTM31AA_MAX_CPUS, boot);
        records[i].adt_reg = old;
    }
}

static unsigned permutation_cases;
static void permutations(unsigned *order, size_t depth)
{
    size_t i;
    if (depth == 5) {
        const struct sptm31aa_cpu_record original[] = {
            {900, 77, 0x203}, {12, 80, 1}, {600, 77, 0x101}, {0, 80, 3}, {44, 0, 2}};
        struct sptm31z_entry_snapshot entry = cold();
        struct sptm31aa_cpu_record records[5];
        struct sptm31aa_boot_identity boot = {900, 0x203};
        struct sptm31aa_registration_plan plan;
        for (i = 0; i < 5; i++)
            records[i] = original[order[i]];
        if (order[0] == 0) {
            assert(sptm31aa_prepare_registration(&entry, records, 5, boot, &plan) == SPTM31AA_OK);
            exact_mapping(&plan, records, 5);
        } else {
            reject(SPTM31AA_BOOT_ORDER, &entry, records, 5, boot);
        }
        permutation_cases++;
        return;
    }
    for (i = depth; i < 5; i++) {
        unsigned saved = order[depth];
        order[depth] = order[i];
        order[i] = saved;
        permutations(order, depth + 1);
        saved = order[depth];
        order[depth] = order[i];
        order[i] = saved;
    }
}

static void all_orders(void)
{
    unsigned order[] = {0, 1, 2, 3, 4};
    permutations(order, 0);
    assert(permutation_cases == 120);
}

static void pinned_project_topology(void)
{
    struct sptm31z_entry_snapshot entry = cold();
    struct sptm31aa_registration_plan plan;
    size_t i;
    assert(PROJECT_CPU_COUNT == 18);
    assert(sptm31aa_prepare_registration(&entry, project_cpus, PROJECT_CPU_COUNT,
                                        project_boot, &plan) == SPTM31AA_OK);
    exact_mapping(&plan, project_cpus, PROJECT_CPU_COUNT);
    for (i = 0; i < PROJECT_CPU_COUNT; i++) {
        assert(plan.registrations[i].source_cpu_id == i);
        assert(plan.registrations[i].physical_id_argument == (i / 6) * 256 + i % 6);
        assert(plan.registrations[i].source_class == (i < 12 ? 77u : 80u));
    }
    assert(plan.registrations[2].physical_id_argument == 2);
}

static void width_does_not_authenticate_topology(void)
{
    struct sptm31z_entry_snapshot entry = cold();
    struct sptm31aa_cpu_record records[] = {{0, 77, 0}, {2, 77, 0x40002}};
    struct sptm31aa_boot_identity boot = {0, 0};
    struct sptm31aa_registration_plan plan;
    /* This deliberately wrong diagnostic identity fits the API width. Without
     * authenticated ADT provenance, no arithmetic validator can detect it.
     * The pinned fixture above supplies CPU2's actual ADT reg=2 instead. */
    assert(sptm31aa_prepare_registration(&entry, records, 2, boot, &plan) == SPTM31AA_OK);
    assert(plan.registrations[1].physical_id_argument == 0x40002);
    assert(plan.registrations[1].physical_id_argument != project_cpus[2].adt_reg);
}

static void compose_with_frozen_entry_and_memory(void)
{
    struct sptm31z_entry_snapshot entry = cold();
    uint8_t bytes[SPTM31Z_MONITOR_BYTES] = {0};
    struct sptm31z_monitor_snapshot monitor;
    struct sptm31z_decoded_memory memory = {{0x100000, 0x20000}, 0, 0x108000, 0x4000};
    struct sptm31z_memory_plan ranges;
    struct sptm31aa_registration_plan registrations;
    /* Independently encoded physical boundary0x110000, after iBoot0x108000. */
    bytes[26] = 0x11;
    assert(sptm31z_snapshot_monitor(&entry, bytes, sizeof(bytes), &monitor) == SPTM31Z_ENTRY_OK);
    memory.monitor_first_available = monitor.first_available.value;
    assert(sptm31z_plan_memory(&memory, NULL, 0, &ranges) == SPTM31Z_MEMORY_OK);
    assert(ranges.available_count == 1 && ranges.available[0].base == 0x110000 &&
           ranges.available[0].bytes == 0x10000);
    assert(sptm31aa_prepare_registration(&monitor.entry, project_cpus, PROJECT_CPU_COUNT,
                                        project_boot, &registrations) == SPTM31AA_OK);
    assert(registrations.registrations[2].physical_id_argument == 2);
    /* These are prepared data artifacts, with no claim that monitor calls ran. */
}

int main(void)
{
    sparse_labels_and_owned_output();
    arguments_and_count();
    entry_roles_and_integrity();
    affinity_width_and_zero_extension();
    boot_identity_must_match_first();
    duplicate_pairs();
    maximum_capacity();
    all_orders();
    pinned_project_topology();
    width_does_not_authenticate_topology();
    compose_with_frozen_entry_and_memory();
    puts("SPTM31AA_REGISTRATION_PASS groups=11 permutations=120 duplicate_cases=56 project_cpus=18 native=NOT_DEPLOYABLE");
    return 0;
}

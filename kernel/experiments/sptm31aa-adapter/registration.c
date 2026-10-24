/* SPDX-License-Identifier: MIT */
#include "registration.h"

enum sptm31aa_status sptm31aa_prepare_registration(
    const struct sptm31z_entry_snapshot *entry,
    const struct sptm31aa_cpu_record *records, size_t count,
    struct sptm31aa_boot_identity boot,
    struct sptm31aa_registration_plan *output)
{
    struct sptm31aa_registration_plan plan = {0};
    struct sptm31z_boot_words words;
    size_t i, j;

    if (!entry || !records || !output)
        return SPTM31AA_ARGUMENT;
    if (!count || count > SPTM31AA_MAX_CPUS)
        return SPTM31AA_COUNT;
    if (sptm31z_get_boot_words(entry, &words) != SPTM31Z_ENTRY_OK)
        return SPTM31AA_ENTRY;
    if (boot.adt_reg > UINT32_MAX)
        return SPTM31AA_AFFINITY_WIDTH;
    for (i = 0; i < count; i++) {
        if (records[i].adt_reg > UINT32_MAX)
            return SPTM31AA_AFFINITY_WIDTH;
        for (j = 0; j < i; j++) {
            if (records[i].source_cpu_id == records[j].source_cpu_id)
                return SPTM31AA_DUPLICATE_SOURCE;
            if (records[i].adt_reg == records[j].adt_reg)
                return SPTM31AA_DUPLICATE_AFFINITY;
        }
    }
    if (records[0].source_cpu_id != boot.source_cpu_id || records[0].adt_reg != boot.adt_reg)
        return SPTM31AA_BOOT_ORDER;

    plan.entry = *entry;
    plan.boot = boot;
    plan.count = count;
    for (i = 0; i < count; i++) {
        plan.registrations[i].logical_ordinal = (uint32_t)i;
        plan.registrations[i].source_cpu_id = records[i].source_cpu_id;
        plan.registrations[i].source_class = records[i].source_class;
        plan.registrations[i].physical_id_argument = (uint64_t)(uint32_t)records[i].adt_reg;
    }
    *output = plan;
    return SPTM31AA_OK;
}

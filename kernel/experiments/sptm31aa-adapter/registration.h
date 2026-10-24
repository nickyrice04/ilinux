/* SPDX-License-Identifier: MIT */
#ifndef ILINUX_SPTM31AA_REGISTRATION_H
#define ILINUX_SPTM31AA_REGISTRATION_H

#include <stddef.h>
#include <stdint.h>
#include "../sptm31z-adapter/entry.h"

/* Original bounded storage policy, not a measured monitor or hardware limit. */
#define SPTM31AA_MAX_CPUS 64u

struct sptm31aa_cpu_record {
    uint32_t source_cpu_id;
    /* Opaque caller metadata; zero may mean unspecified. Never used to sort. */
    uint32_t source_class;
    /* Caller-decoded ADT reg, kept wide so narrowing can be checked. This is
     * an affinity identifier, NOT a physical-memory address or raw MPIDR. */
    uint64_t adt_reg;
};
struct sptm31aa_boot_identity {
    uint32_t source_cpu_id;
    uint64_t adt_reg;
};
struct sptm31aa_registration {
    /* Predicted registration-order ordinal, NOT an observed monitor result. */
    uint32_t logical_ordinal;
    uint32_t source_cpu_id;
    uint32_t source_class;
    /* Exact single uint64 argument, zero-extended from the checked ADT value.
     * No CPU-data address, stack pointer or inferred Aff2 bits are added. */
    uint64_t physical_id_argument;
};
struct sptm31aa_registration_plan {
    struct sptm31z_entry_snapshot entry;
    struct sptm31aa_boot_identity boot;
    size_t count;
    struct sptm31aa_registration registrations[SPTM31AA_MAX_CPUS];
};
enum sptm31aa_status {
    SPTM31AA_OK = 0, SPTM31AA_ARGUMENT, SPTM31AA_COUNT, SPTM31AA_ENTRY,
    SPTM31AA_AFFINITY_WIDTH, SPTM31AA_BOOT_ORDER,
    SPTM31AA_DUPLICATE_SOURCE, SPTM31AA_DUPLICATE_AFFINITY
};

/* Prepare an immutable, owned registration list for a future qualified bridge.
 * The input order is preserved exactly. The independently supplied boot
 * identity must match row0; the API never moves a boot row or sorts by IDs or
 * classes. Source IDs and affinities must each be unique; those refusal rules
 * are original validation policy, not claimed monitor duplicate-call behavior.
 * The full raw affinity must fit uint32_t before zero-extension to the API's
 * uint64 argument. No truncation, MPIDR fallback, masking or Aff2 inference.
 * Frozen31Z's cold-only role accessor validates the entry snapshot structurally.
 * That check does not prove authentic entry, helper initialization or permission.
 *
 * Caller must bind records to the actual ordered, supported ADT CPU set and
 * boot identity. This API cannot infer missing CPUs or authenticate a raw value:
 * even a wrong diagnostic MPIDR may fit uint32_t. Keep source IDs/classes distinct
 * from predicted ordinals. A future bridge may consume registrations in order
 * only after independently qualifying resident-monitor, boot-CPU, pre-lockdown,
 * memory and stack prerequisites, the dispatch transport and any helper services
 * actually used, plus the matching image/exception lifecycle.
 * The real registration API is void: no success result or physical start is
 * synthesized here. No calls, callbacks, mutable progress cursor or retry API.
 * Reconstructing/replaying a plan does not authorize duplicate registration.
 *
 * Inputs/output must be valid disjoint C objects, serialized by the caller.
 * On failure output remains unchanged; on success all records are owned copies.
 * Retain the result unchanged while a consumer uses it. NOT_DEPLOYABLE: this is
 * preparation of arguments, not a native adapter or hardware-ready state.
 */
enum sptm31aa_status sptm31aa_prepare_registration(
    const struct sptm31z_entry_snapshot *entry,
    const struct sptm31aa_cpu_record *records, size_t count,
    struct sptm31aa_boot_identity boot,
    struct sptm31aa_registration_plan *output);

#endif

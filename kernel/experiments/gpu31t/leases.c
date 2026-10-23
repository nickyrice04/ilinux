/* SPDX-License-Identifier: MIT */
#include "leases.h"

static bool clean(struct gpu31t_batch *batch)
{
    bool pending = false;
    batch->phase = GPU31T_CLEANING;
    for (size_t i = batch->attempted; i != 0; --i) {
        struct gpu31t_entry *entry = &batch->entries[i - 1];
        if (!entry->preparation.cleanup_required)
            continue;
        entry->cleanup_attempted = true;
        entry->completion = batch->ops.complete(batch->ops.context,
            entry->resource, entry->preparation.lease);
        pending |= !entry->completion.released;
    }
    return pending;
}

enum gpu31t_result gpu31t_prepare(struct gpu31t_batch *batch,
    const struct gpu31t_ops *ops, const uint64_t *resources, size_t count)
{
    if (!batch || !ops || !resources || !ops->prepare || !ops->complete ||
        count == 0 || count > GPU31T_MAX_LEASES)
        return GPU31T_ARGUMENT;
    if (batch->phase != GPU31T_EMPTY)
        return GPU31T_STATE;
    struct gpu31t_batch next = {0};
    next.phase = GPU31T_PREPARING;
    next.requested = count;
    next.ops = *ops;
    for (size_t i = 0; i < count; ++i)
        next.entries[i].resource = resources[i];
    *batch = next;
    for (size_t i = 0; i < count; ++i) {
        struct gpu31t_entry *entry = &batch->entries[i];
        entry->preparation = batch->ops.prepare(batch->ops.context, entry->resource);
        batch->attempted = i + 1;
        if (!entry->preparation.accepted) {
            batch->phase = clean(batch) ? GPU31T_UNRESOLVED : GPU31T_FAILED;
            return GPU31T_PREPARE_FAILED;
        }
    }
    batch->phase = GPU31T_PREPARED;
    return GPU31T_OK;
}

enum gpu31t_result gpu31t_finish(struct gpu31t_batch *batch)
{
    if (!batch)
        return GPU31T_ARGUMENT;
    if (batch->phase != GPU31T_PREPARED)
        return GPU31T_STATE;
    if (clean(batch)) {
        batch->phase = GPU31T_UNRESOLVED;
        return GPU31T_CLEANUP_PENDING;
    }
    batch->phase = GPU31T_RELEASED;
    return GPU31T_OK;
}

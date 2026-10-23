/* SPDX-License-Identifier: MIT */
#ifndef ILINUX_GPU31T_LEASES_H
#define ILINUX_GPU31T_LEASES_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Original resource bound, not a firmware limit or wire structure. */
#define GPU31T_MAX_LEASES 16u
struct gpu31t_prepared {
    bool accepted;
    bool cleanup_required;
    uint32_t status; /* Opaque: ownership must not be inferred from this value. */
    uint64_t lease;  /* Caller token; not a serialized address. Zero is allowed. */
};
struct gpu31t_completed { bool released; uint32_t status; };
struct gpu31t_ops {
    struct gpu31t_prepared (*prepare)(void *context, uint64_t resource);
    struct gpu31t_completed (*complete)(void *context, uint64_t resource,
                                      uint64_t lease);
    void *context;
};
struct gpu31t_entry {
    uint64_t resource;
    struct gpu31t_prepared preparation;
    struct gpu31t_completed completion;
    bool cleanup_attempted;
};
enum gpu31t_phase {
    GPU31T_EMPTY = 0, GPU31T_PREPARING, GPU31T_PREPARED, GPU31T_CLEANING,
    GPU31T_FAILED, GPU31T_RELEASED, GPU31T_UNRESOLVED
};
struct gpu31t_batch {
    enum gpu31t_phase phase;
    size_t requested, attempted;
    struct gpu31t_ops ops;
    struct gpu31t_entry entries[GPU31T_MAX_LEASES];
};
enum gpu31t_result {
    GPU31T_OK = 0, GPU31T_ARGUMENT, GPU31T_STATE,
    GPU31T_PREPARE_FAILED, GPU31T_CLEANUP_PENDING
};

/* Zero-initialize batch before its first use. Caller serializes access, keeps
 * context/resources alive through cleanup or external recovery, and prevents
 * overlap among batch, ops and resources. Callbacks must return normally and
 * report ownership truthfully, including partial failure. ALL leases must remain
 * independently completable even while another lease is unresolved; dependent
 * backing-pin/mapping chains need a separate policy. Preparation must not expose
 * resources to firmware or other consumers: automatic failure cleanup requires
 * the same safe-release condition as finish. This is not an authentication boundary.
 *
 * Nonempty bounded batches only. Each prepare is invoked at most once, in order.
 * Stop on the first !accepted result. Cleanup then visits every explicit
 * obligation in reverse order, including the failing entry if it owns one.
 * Each obligation gets at most one complete call; a false released result is
 * retained as UNRESOLVED and requires caller recovery. No automatic retry.
 * Reentrant API calls are refused while callbacks run. No locking is supplied.
 * Invalid arguments/state leave the batch untouched and call nothing.
 *
 * OK/PREPARED means all prepare callbacks accepted. It establishes no cache or
 * page-table publication, GPU visibility, firmware acknowledgment or readiness.
 * There is no actual memory/device operation except caller-injected callbacks.
 */
enum gpu31t_result gpu31t_prepare(struct gpu31t_batch *batch,
    const struct gpu31t_ops *ops, const uint64_t *resources, size_t count);

/* Only PREPARED may finish. Releases each explicit obligation once in reverse
 * order and preserves every opaque result. Stop/failure cleanup already ran
 * inside prepare; calling finish again is refused, including after UNRESOLVED.
 * Caller must independently prove firmware has stopped using these resources
 * before finishing. Device completion is never inferred by this helper. */
enum gpu31t_result gpu31t_finish(struct gpu31t_batch *batch);
#endif

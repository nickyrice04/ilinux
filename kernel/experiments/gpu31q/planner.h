/* SPDX-License-Identifier: MIT */
#ifndef ILINUX_GPU31Q_PLANNER_H
#define ILINUX_GPU31Q_PLANNER_H

#include <stddef.h>
#include <stdint.h>

/* Local resource bounds, not firmware or ioctl limits. */
#define GPU31Q_MAX_OPS 64u
#define GPU31Q_MAX_OBJECTS 64u

/* The pinned public Asahi GEM binding flag values. */
#define GPU31Q_UNBIND UINT32_C(1)
#define GPU31Q_READ UINT32_C(2)
#define GPU31Q_WRITE UINT32_C(4)
#define GPU31Q_SINGLE_PAGE UINT32_C(8)

enum gpu31q_status {
    GPU31Q_OK = 0,
    GPU31Q_ARGUMENT,
    GPU31Q_LIMIT,
    GPU31Q_WINDOW,
    GPU31Q_RESERVATION,
    GPU31Q_OBJECT,
    GPU31Q_FLAGS,
    GPU31Q_ALIGNMENT,
    GPU31Q_RANGE,
    GPU31Q_CAPACITY
};

/* One userspace GPU VA space. Every end is exclusive. No CPU physical address,
 * firmware descriptor address, ASC role, PTE or hardware profile is accepted.
 * Parameters must eventually come from a qualified driver; synthetic tests do
 * not qualify G17C. page_size is explicit, never guessed from the host page. */
struct gpu31q_space {
    uint64_t page_size;
    uint64_t vm_start;
    uint64_t vm_end;
    uint64_t kernel_start;
    uint64_t kernel_end;
    uint64_t kernel_min_size;
};

/* Actual accessible object extent, not a requested size assumed to be rounded. */
struct gpu31q_object {
    uint32_t handle;
    uint64_t size;
};

/* Native C input representation. This is not a wire struct or ioctl argument. */
struct gpu31q_op {
    uint32_t flags;
    uint32_t handle;
    uint64_t offset;
    uint64_t size;
    uint64_t addr;
};

struct gpu31q_planned {
    struct gpu31q_op op;
    uint64_t object_bytes_accessed;
};

/* Pure validation. Empty/reversed reservations and zero minimums are refused. */
enum gpu31q_status gpu31q_validate_space(const struct gpu31q_space *space);

/* Validate the entire ordered batch before publishing any output. Duplicate
 * input addresses are allowed: a later operation may replace an earlier one.
 * No mapping state, lifetime, locking, visibility or completion is modeled.
 * Each caller-provided array must be accessible for its stated count/capacity.
 * Output storage and output_count must not overlap inputs or each other.
 * On failure, output bytes and output_count remain untouched. A zero-operation
 * batch is accepted, including NULL operation/output arrays, and returns count0.
 * This local transaction does NOT make a later kernel ioctl atomic. */
enum gpu31q_status gpu31q_plan(
    const struct gpu31q_space *space,
    const struct gpu31q_object *objects, size_t object_count,
    const struct gpu31q_op *ops, size_t op_count,
    struct gpu31q_planned *output, size_t output_capacity,
    size_t *output_count);

#endif

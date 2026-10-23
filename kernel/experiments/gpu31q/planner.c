/* SPDX-License-Identifier: MIT */
#include "planner.h"

static int aligned(uint64_t value, uint64_t page_size)
{
    return (value & (page_size - UINT64_C(1))) == 0;
}

enum gpu31q_status gpu31q_validate_space(const struct gpu31q_space *s)
{
    if (s == NULL)
        return GPU31Q_ARGUMENT;
    if (s->page_size == 0 ||
        (s->page_size & (s->page_size - UINT64_C(1))) != 0)
        return GPU31Q_ALIGNMENT;
    if (s->vm_start >= s->vm_end)
        return GPU31Q_WINDOW;
    if (!aligned(s->vm_start, s->page_size) ||
        !aligned(s->vm_end, s->page_size) ||
        !aligned(s->kernel_start, s->page_size) ||
        !aligned(s->kernel_end, s->page_size))
        return GPU31Q_ALIGNMENT;
    if (s->kernel_start >= s->kernel_end || s->kernel_min_size == 0 ||
        s->kernel_start < s->vm_start || s->kernel_end > s->vm_end ||
        s->kernel_end - s->kernel_start < s->kernel_min_size)
        return GPU31Q_RESERVATION;
    return GPU31Q_OK;
}

static enum gpu31q_status inspect_op(
    const struct gpu31q_space *s,
    const struct gpu31q_object *objects, size_t object_count,
    const struct gpu31q_op *op, uint64_t *access)
{
    uint64_t end;
    size_t i;
    if ((op->flags & GPU31Q_UNBIND) != 0) {
        if (op->flags != GPU31Q_UNBIND || op->handle != 0 || op->offset != 0)
            return GPU31Q_FLAGS;
        *access = 0;
    } else {
        if ((op->flags & ~(GPU31Q_READ | GPU31Q_WRITE | GPU31Q_SINGLE_PAGE)) != 0 ||
            (op->flags & (GPU31Q_READ | GPU31Q_WRITE)) == 0)
            return GPU31Q_FLAGS;
        *access = (op->flags & GPU31Q_SINGLE_PAGE) != 0 ? s->page_size : op->size;
    }
    if (!aligned(op->addr, s->page_size) ||
        !aligned(op->size, s->page_size) ||
        !aligned(op->offset, s->page_size))
        return GPU31Q_ALIGNMENT;
    if (op->size == 0 || op->addr > UINT64_MAX - op->size)
        return GPU31Q_RANGE;
    end = op->addr + op->size;
    if (op->addr < s->vm_start || end > s->vm_end)
        return GPU31Q_RANGE;
    if (op->addr < s->kernel_end && s->kernel_start < end)
        return GPU31Q_RESERVATION;
    if ((op->flags & GPU31Q_UNBIND) != 0)
        return GPU31Q_OK;
    for (i = 0; i < object_count; ++i) {
        if (objects[i].handle == op->handle) {
            if (op->offset > objects[i].size ||
                *access > objects[i].size - op->offset)
                return GPU31Q_OBJECT;
            return GPU31Q_OK;
        }
    }
    return GPU31Q_OBJECT;
}

enum gpu31q_status gpu31q_plan(
    const struct gpu31q_space *s,
    const struct gpu31q_object *objects, size_t object_count,
    const struct gpu31q_op *ops, size_t op_count,
    struct gpu31q_planned *output, size_t output_capacity,
    size_t *output_count)
{
    struct gpu31q_planned pending[GPU31Q_MAX_OPS];
    enum gpu31q_status status;
    size_t i, j;
    if (output_count == NULL || (object_count != 0 && objects == NULL) ||
        (op_count != 0 && (ops == NULL || output == NULL)))
        return GPU31Q_ARGUMENT;
    if (object_count > GPU31Q_MAX_OBJECTS || op_count > GPU31Q_MAX_OPS)
        return GPU31Q_LIMIT;
    if (output_capacity < op_count)
        return GPU31Q_CAPACITY;
    status = gpu31q_validate_space(s);
    if (status != GPU31Q_OK)
        return status;
    for (i = 0; i < object_count; ++i) {
        if (objects[i].handle == 0 || objects[i].size == 0)
            return GPU31Q_OBJECT;
        for (j = 0; j < i; ++j)
            if (objects[j].handle == objects[i].handle)
                return GPU31Q_OBJECT;
    }
    for (i = 0; i < op_count; ++i) {
        status = inspect_op(s, objects, object_count, &ops[i],
                            &pending[i].object_bytes_accessed);
        if (status != GPU31Q_OK)
            return status;
        pending[i].op = ops[i];
    }
    for (i = 0; i < op_count; ++i)
        output[i] = pending[i];
    *output_count = op_count;
    return GPU31Q_OK;
}

#include "ring_math.h"

#include <stddef.h>

bool acipc_queue_init(struct acipc_software_queue *queue, uint64_t slots)
{
    if (!queue || !slots)
        return false;
    *queue = (struct acipc_software_queue){slots, 0, 0};
    return true;
}

bool acipc_queue_occupancy(const struct acipc_software_queue *queue,
                           uint64_t *used)
{
    if (!queue || !used || !queue->slots || queue->head >= queue->slots ||
        queue->tail >= queue->slots)
        return false;
    *used = queue->head >= queue->tail
                ? queue->head - queue->tail
                : queue->slots - (queue->tail - queue->head);
    return true;
}

bool acipc_queue_push(struct acipc_software_queue *queue, uint64_t count)
{
    uint64_t used, next;

    if (!acipc_queue_occupancy(queue, &used) ||
        count > queue->slots - 1 - used ||
        !acipc_index_advance(queue->slots, queue->head, count, &next))
        return false;
    queue->head = next;
    return true;
}

bool acipc_queue_pop(struct acipc_software_queue *queue, uint64_t count)
{
    uint64_t used, next;

    if (!acipc_queue_occupancy(queue, &used) || count > used ||
        !acipc_index_advance(queue->slots, queue->tail, count, &next))
        return false;
    queue->tail = next;
    return true;
}

bool acipc_index_advance(uint64_t slots, uint64_t index, uint64_t steps,
                         uint64_t *next)
{
    uint64_t remainder;

    if (!next || slots == 0 || index >= slots)
        return false;
    remainder = steps % slots;
    /* index + remainder could overflow even though the result fits. */
    *next = remainder >= slots - index
                ? remainder - (slots - index)
                : index + remainder;
    return true;
}

bool acipc_span_valid(uint64_t buffer_bytes, struct acipc_buffer_span span)
{
    return span.offset <= buffer_bytes &&
           span.length <= buffer_bytes - span.offset;
}

bool acipc_slot_span(uint64_t slots, uint64_t stride, uint64_t index,
                     uint64_t buffer_bytes, struct acipc_buffer_span *span)
{
    struct acipc_buffer_span candidate;

    if (!span || slots == 0 || stride == 0 || index >= slots ||
        slots > UINT64_MAX / stride || slots * stride > buffer_bytes)
        return false;
    candidate.offset = index * stride;
    candidate.length = stride;
    if (!acipc_span_valid(buffer_bytes, candidate))
        return false;
    *span = candidate;
    return true;
}

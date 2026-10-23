/* SPDX-License-Identifier: MIT */
#include "ring.h"
#include <string.h>

enum gpu31u_result gpu31u_begin(struct gpu31u_ring *ring, uint32_t capacity,
    uint32_t consumer, uint32_t producer, uint64_t mapped_bytes,
    uint64_t allowed_types, const struct gpu31u_ops *ops)
{
    if (!ring || !ops || !ops->copy || !ops->publish || !capacity ||
        consumer >= capacity || producer >= capacity ||
        mapped_bytes < (uint64_t)capacity * GPU31U_RECORD_BYTES)
        return GPU31U_ARGUMENT;
    if (ring->phase != GPU31U_FRESH)
        return GPU31U_STATE;
    ring->capacity = capacity;
    ring->consumer = consumer;
    ring->captured_producer = producer;
    ring->allowed_types = allowed_types;
    ring->ops = *ops;
    ring->phase = consumer == producer ? GPU31U_DONE : GPU31U_ACTIVE;
    return consumer == producer ? GPU31U_EMPTY : GPU31U_OK;
}

enum gpu31u_result gpu31u_next(struct gpu31u_ring *ring)
{
    uint8_t record[GPU31U_RECORD_BYTES] = {0};
    struct gpu31u_effect effect;
    uint32_t type, next;
    if (!ring)
        return GPU31U_ARGUMENT;
    if (ring->phase == GPU31U_DONE)
        return GPU31U_EMPTY;
    if (ring->phase != GPU31U_ACTIVE)
        return GPU31U_STATE;
    ring->phase = GPU31U_BUSY;
    ring->record_valid = false;
    ring->publication_attempted = false;
    effect = ring->ops.copy(ring->ops.context,
        (uint64_t)ring->consumer * GPU31U_RECORD_BYTES, record);
    ring->copy_status = effect.status;
    if (!effect.accepted) {
        ring->phase = GPU31U_REJECTED;
        return GPU31U_COPY_FAILED;
    }
    memcpy(ring->record, record, sizeof(record));
    ring->record_valid = true;
    type = (uint32_t)record[0] | ((uint32_t)record[1] << 8) |
           ((uint32_t)record[2] << 16) | ((uint32_t)record[3] << 24);
    ring->record_type = type;
    /* Deliberately refuse the >=64 alias of a hardware variable shift. */
    if (type >= 64 || !(ring->allowed_types & (UINT64_C(1) << type))) {
        ring->phase = GPU31U_REJECTED;
        return GPU31U_TYPE_REFUSED;
    }
    next = ring->consumer == ring->capacity - 1 ? 0 : ring->consumer + 1;
    ring->proposed_consumer = next;
    ring->publication_attempted = true;
    effect = ring->ops.publish(ring->ops.context, next);
    ring->publish_status = effect.status;
    if (!effect.accepted) {
        ring->phase = GPU31U_PUBLICATION_UNKNOWN;
        return GPU31U_PUBLISH_UNKNOWN;
    }
    ring->consumer = next;
    ring->phase = next == ring->captured_producer ? GPU31U_DONE : GPU31U_ACTIVE;
    return GPU31U_OK;
}

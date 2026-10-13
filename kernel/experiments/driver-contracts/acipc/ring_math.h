#ifndef ILINUX_ACIPC_RING_MATH_H
#define ILINUX_ACIPC_RING_MATH_H

#include <stdbool.h>
#include <stdint.h>

/* Offline host-buffer arithmetic only. Hardware index encoding is unknown. */
struct acipc_buffer_span {
    uint64_t offset;
    uint64_t length;
};

/* Explicit software policy: one empty slot distinguishes full from empty.
 * No synchronization, firmware encoding or DMA layout is implied. */
struct acipc_software_queue {
    uint64_t slots;
    uint64_t head;
    uint64_t tail;
};

bool acipc_queue_init(struct acipc_software_queue *queue, uint64_t slots);
bool acipc_queue_occupancy(const struct acipc_software_queue *queue,
                           uint64_t *used);
bool acipc_queue_push(struct acipc_software_queue *queue, uint64_t count);
bool acipc_queue_pop(struct acipc_software_queue *queue, uint64_t count);

/* index is an ordinary, zero-based software index in [0, slots). */
bool acipc_index_advance(uint64_t slots, uint64_t index, uint64_t steps,
                         uint64_t *next);

/* A software view, NOT a decoded hardware/DMA descriptor. */
bool acipc_span_valid(uint64_t buffer_bytes, struct acipc_buffer_span span);

/* Return a slot's byte span; reject truncated buffers and integer overflow. */
bool acipc_slot_span(uint64_t slots, uint64_t stride, uint64_t index,
                     uint64_t buffer_bytes, struct acipc_buffer_span *span);

#endif

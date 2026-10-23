/* SPDX-License-Identifier: MIT */
#ifndef ILINUX_GPU31U_RING_H
#define ILINUX_GPU31U_RING_H
#include <stdbool.h>
#include <stdint.h>

#define GPU31U_RECORD_BYTES 72u
enum gpu31u_phase { GPU31U_FRESH = 0, GPU31U_ACTIVE, GPU31U_BUSY,
                    GPU31U_DONE, GPU31U_REJECTED, GPU31U_PUBLICATION_UNKNOWN };
enum gpu31u_result { GPU31U_OK = 0, GPU31U_EMPTY, GPU31U_ARGUMENT,
                     GPU31U_STATE, GPU31U_COPY_FAILED, GPU31U_TYPE_REFUSED,
                     GPU31U_PUBLISH_UNKNOWN };
struct gpu31u_effect { bool accepted; uint32_t status; };
/* Original adapter API, not firmware structures. Copy must fill exactly one
 * stable record on success. Publish must order all preceding record reads before
 * the actual consumer-index store with the platform's required DMA/device
 * synchronization. A C11 fence alone does not satisfy that contract.
 * A refused publish may have had effects: the batch stops without retry. */
struct gpu31u_ops {
    struct gpu31u_effect (*copy)(void *context, uint64_t byte_offset,
                                uint8_t record[GPU31U_RECORD_BYTES]);
    struct gpu31u_effect (*publish)(void *context, uint32_t consumer);
    void *context;
};
struct gpu31u_ring {
    enum gpu31u_phase phase;
    uint32_t capacity, consumer, captured_producer;
    uint64_t allowed_types;
    struct gpu31u_ops ops;
    uint8_t record[GPU31U_RECORD_BYTES];
    bool record_valid, publication_attempted;
    uint32_t record_type, proposed_consumer, copy_status, publish_status;
};

/* Caller supplies a zero-initialized, untampered ring; stable validated mapping
 * size and index snapshot; sole-consumer serialization; and truthful bounded
 * callbacks. No input may overlap ring state. Producer owns only unpublished
 * slots and must not overwrite unread records. Runtime mapping/address/role
 * qualification, index acquisition barriers and lifetimes are caller duties.
 * Equal indices mean EMPTY under this ring contract, never a full ring.
 * No MMIO, DMA mapping, discovery, firmware submission or readiness claim. */
enum gpu31u_result gpu31u_begin(struct gpu31u_ring *ring, uint32_t capacity,
    uint32_t consumer, uint32_t producer, uint64_t mapped_bytes,
    uint64_t allowed_types, const struct gpu31u_ops *ops);

/* Consumes at most one record toward the captured producer. New producer
 * progress is deliberately ignored. OK: raw record retained, publication
 * accepted by adapter; not firmware acknowledgment. Refused type/copy never
 * publishes. Refused publication retains the record and proposed index in a
 * terminal state; caller must reconcile externally, never blindly retry.
 * Callback reentrancy returns STATE without touching the active operation.
 * Callbacks may inspect state, never modify it. No reset/reuse API. */
enum gpu31u_result gpu31u_next(struct gpu31u_ring *ring);
#endif

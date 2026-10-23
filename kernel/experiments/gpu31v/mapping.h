/* SPDX-License-Identifier: MIT */
#ifndef ILINUX_GPU31V_MAPPING_H
#define ILINUX_GPU31V_MAPPING_H
#include <stdbool.h>
#include <stdint.h>

#define GPU31V_MAPPING_BYTES 24u
#define GPU31V_MAPPING_SLOTS 256u
#define GPU31V_MAPPING_RING_BYTES (GPU31V_MAPPING_BYTES * GPU31V_MAPPING_SLOTS)
#define GPU31V_CONSUMER_OFFSET 0u
#define GPU31V_PRODUCER_OFFSET 16u

/* Original software API, not an Apple object layout. Firmware address conversion
 * and the actual mapping must already be qualified by the caller. Flags select
 * only the observed wire values 1/5; no permission meaning is assigned. */
struct gpu31v_mapping {
    uint64_t firmware_va, byte_length;
    unsigned gart_page_shift;
    bool flag_bit2;
};
enum gpu31v_phase { GPU31V_FRESH = 0, GPU31V_PREPARED, GPU31V_FULL,
    GPU31V_BUSY, GPU31V_SUBMITTED, GPU31V_WRITE_UNKNOWN,
    GPU31V_PUBLICATION_UNKNOWN };
enum gpu31v_result { GPU31V_OK = 0, GPU31V_QUEUE_FULL, GPU31V_ARGUMENT,
    GPU31V_STATE, GPU31V_WRITE_UNCERTAIN, GPU31V_PUBLISH_UNCERTAIN };
struct gpu31v_effect { bool accepted; uint32_t status; };
struct gpu31v_ops {
    struct gpu31v_effect (*write)(void *context, uint64_t byte_offset,
        const uint8_t record[GPU31V_MAPPING_BYTES]);
    struct gpu31v_effect (*publish)(void *context, uint32_t producer);
    void *context;
};
struct gpu31v_submission {
    enum gpu31v_phase phase;
    uint32_t consumer, producer, proposed_producer;
    uint8_t record[GPU31V_MAPPING_BYTES];
    struct gpu31v_ops ops;
    bool write_attempted, publication_attempted;
    uint32_t write_status, publish_status;
};

/* Encode the checked 24-byte variant. Stricter software policy: length is a
 * nonzero multiple of 4KiB fitting the 32-bit unit count; VA+length cannot wrap;
 * firmware page shift is14 and the GART ratio must fit a nonzero16-bit power of
 * two (GART shift14..29). No address-domain conversion or mapping is performed.
 * Invalid inputs leave output untouched. Inputs/outputs must not overlap. */
enum gpu31v_result gpu31v_encode(const struct gpu31v_mapping *mapping,
    uint8_t record[GPU31V_MAPPING_BYTES]);

/* Requires zero-initialized, untampered submission; acquired and valid index
 * snapshot; at least6144 mapped data bytes; sole-producer serialization and a
 * consumer which only advances through published entries. Snapshot acquisition,
 * mapping lifetime/coherence and actual DMA ordering are adapter obligations.
 * No callback or device operation occurs here, including FULL/invalid inputs.
 * The caller must preserve these conditions through submit. No inputs overlap
 * submission. No reset/reuse API: unknown effects require external reconciliation. */
enum gpu31v_result gpu31v_prepare(struct gpu31v_submission *submission,
    const struct gpu31v_mapping *mapping, uint32_t consumer, uint32_t producer,
    uint64_t mapped_bytes, const struct gpu31v_ops *ops);

/* One bounded attempt: write exactly24 bytes to the unpublished slot, then
 * publish the producer index. The publish callback must perform the platform's
 * actual data visibility/barriers before storing at producer control+16. A C11
 * fence is not a DMA contract. Callbacks are bounded and cannot modify state or
 * retain record pointers after return. Reentrant submit is refused.
 * Write/publication refusal may have effects: retain receipt and stop, no retry.
 * OK means adapter acceptance only, not wakeup, firmware receipt/completion or
 * readiness. Native progress/backpressure policy, including the observed
 * near-full helper, remains external. No waiting, doorbell, MMIO, discovery or
 * native adapter is supplied. */
enum gpu31v_result gpu31v_submit(struct gpu31v_submission *submission);
#endif

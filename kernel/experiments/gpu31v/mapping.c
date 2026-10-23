/* SPDX-License-Identifier: MIT */
#include "mapping.h"
#include <string.h>

static void put_le(uint8_t *out, uint64_t value, unsigned bytes)
{
    for (unsigned i = 0; i < bytes; ++i)
        out[i] = (uint8_t)(value >> (i * 8));
}

enum gpu31v_result gpu31v_encode(const struct gpu31v_mapping *mapping,
    uint8_t record[GPU31V_MAPPING_BYTES])
{
    uint8_t encoded[GPU31V_MAPPING_BYTES] = {0};
    uint64_t count;
    if (!mapping || !record || !mapping->byte_length ||
        (mapping->byte_length & UINT64_C(4095)) ||
        mapping->byte_length > UINT64_MAX - mapping->firmware_va ||
        mapping->gart_page_shift < 14 || mapping->gart_page_shift > 29)
        return GPU31V_ARGUMENT;
    count = mapping->byte_length / 4096;
    if (count > UINT32_MAX)
        return GPU31V_ARGUMENT;
    put_le(encoded, mapping->firmware_va, 8);
    put_le(encoded + 8, count, 4);
    put_le(encoded + 16, UINT64_C(1) << (mapping->gart_page_shift - 14), 2);
    put_le(encoded + 18, mapping->flag_bit2 ? 5 : 1, 2);
    memcpy(record, encoded, sizeof(encoded));
    return GPU31V_OK;
}

enum gpu31v_result gpu31v_prepare(struct gpu31v_submission *submission,
    const struct gpu31v_mapping *mapping, uint32_t consumer, uint32_t producer,
    uint64_t mapped_bytes, const struct gpu31v_ops *ops)
{
    uint8_t encoded[GPU31V_MAPPING_BYTES];
    uint32_t next;
    if (!submission || !ops || !ops->write || !ops->publish ||
        consumer >= GPU31V_MAPPING_SLOTS || producer >= GPU31V_MAPPING_SLOTS ||
        mapped_bytes < GPU31V_MAPPING_RING_BYTES)
        return GPU31V_ARGUMENT;
    if (submission->phase != GPU31V_FRESH)
        return GPU31V_STATE;
    if (gpu31v_encode(mapping, encoded) != GPU31V_OK)
        return GPU31V_ARGUMENT;
    next = (producer + 1) % GPU31V_MAPPING_SLOTS;
    submission->consumer = consumer;
    submission->producer = producer;
    submission->proposed_producer = next;
    submission->ops = *ops;
    memcpy(submission->record, encoded, sizeof(encoded));
    submission->phase = next == consumer ? GPU31V_FULL : GPU31V_PREPARED;
    return next == consumer ? GPU31V_QUEUE_FULL : GPU31V_OK;
}

enum gpu31v_result gpu31v_submit(struct gpu31v_submission *submission)
{
    struct gpu31v_effect effect;
    if (!submission)
        return GPU31V_ARGUMENT;
    if (submission->phase == GPU31V_FULL)
        return GPU31V_QUEUE_FULL;
    if (submission->phase != GPU31V_PREPARED)
        return GPU31V_STATE;
    submission->phase = GPU31V_BUSY;
    submission->write_attempted = true;
    effect = submission->ops.write(submission->ops.context,
        (uint64_t)submission->producer * GPU31V_MAPPING_BYTES,
        submission->record);
    submission->write_status = effect.status;
    if (!effect.accepted) {
        submission->phase = GPU31V_WRITE_UNKNOWN;
        return GPU31V_WRITE_UNCERTAIN;
    }
    submission->publication_attempted = true;
    effect = submission->ops.publish(submission->ops.context,
        submission->proposed_producer);
    submission->publish_status = effect.status;
    if (!effect.accepted) {
        submission->phase = GPU31V_PUBLICATION_UNKNOWN;
        return GPU31V_PUBLISH_UNCERTAIN;
    }
    submission->phase = GPU31V_SUBMITTED;
    return GPU31V_OK;
}

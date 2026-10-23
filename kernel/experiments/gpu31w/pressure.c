/* SPDX-License-Identifier: MIT */
#include "pressure.h"

enum gpu31w_result gpu31w_prepare(struct gpu31w_submission *submission,
    const struct gpu31v_mapping *mapping, uint32_t consumer, uint32_t producer,
    uint64_t mapped_bytes, const struct gpu31v_ops *ops,
    const struct gpu31w_transport *transport)
{
    enum gpu31v_result result;
    if (!submission || !transport || !transport->note ||
        transport->provider_role != GPU31W_PROVIDER_ROLE ||
        transport->endpoint != GPU31W_ENDPOINT)
        return GPU31W_ARGUMENT;
    if (submission->phase != GPU31W_FRESH)
        return GPU31W_STATE;
    result = gpu31v_prepare(&submission->mapping, mapping, consumer, producer,
        mapped_bytes, ops);
    if (result != GPU31V_OK && result != GPU31V_QUEUE_FULL)
        return GPU31W_ARGUMENT;
    submission->transport = *transport;
    submission->note_required = result == GPU31V_OK &&
        consumer == (producer + 2) % GPU31V_MAPPING_SLOTS;
    submission->note_word = GPU31W_NOTE;
    submission->phase = result == GPU31V_QUEUE_FULL ? GPU31W_FULL : GPU31W_PREPARED;
    return result == GPU31V_QUEUE_FULL ? GPU31W_QUEUE_FULL : GPU31W_OK;
}

enum gpu31w_result gpu31w_submit(struct gpu31w_submission *submission)
{
    struct gpu31v_effect effect;
    enum gpu31v_result result;
    if (!submission)
        return GPU31W_ARGUMENT;
    if (submission->phase == GPU31W_FULL)
        return GPU31W_QUEUE_FULL;
    if (submission->phase != GPU31W_PREPARED)
        return GPU31W_STATE;
    submission->phase = GPU31W_BUSY;
    if (submission->note_required) {
        submission->note_attempted = true;
        effect = submission->transport.note(submission->transport.context,
            submission->transport.endpoint, submission->note_word, false);
        submission->note_status = effect.status;
        submission->note_accepted = effect.accepted;
        if (!effect.accepted) {
            submission->phase = GPU31W_STOPPED;
            return GPU31W_NOTE_UNKNOWN;
        }
    }
    result = gpu31v_submit(&submission->mapping);
    submission->phase = result == GPU31V_OK ? GPU31W_DONE : GPU31W_STOPPED;
    if (result == GPU31V_WRITE_UNCERTAIN)
        return GPU31W_WRITE_UNKNOWN;
    if (result == GPU31V_PUBLISH_UNCERTAIN)
        return GPU31W_PUBLISH_UNKNOWN;
    return result == GPU31V_OK ? GPU31W_OK : GPU31W_STATE;
}

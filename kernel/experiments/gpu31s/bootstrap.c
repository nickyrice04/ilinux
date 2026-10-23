/* SPDX-License-Identifier: MIT */
#include "bootstrap.h"
#include <stddef.h>

#define ADDRESS_MASK (GPU31S_FW_ADDRESS_LIMIT - 1)

enum gpu31s_status gpu31s_encode_start(struct gpu31s_fw_address address, uint64_t *word)
{
    if (!word) return GPU31S_ARGUMENT;
    if (address.value >= GPU31S_FW_ADDRESS_LIMIT) return GPU31S_ADDRESS_WIDTH;
    *word = GPU31S_START_HEADER | address.value;
    return GPU31S_OK;
}

enum gpu31s_status gpu31s_decode_start(uint64_t word, struct gpu31s_fw_address *address)
{
    if (!address) return GPU31S_ARGUMENT;
    if ((word & ~ADDRESS_MASK) != GPU31S_START_HEADER) return GPU31S_HEADER;
    address->value = word & ADDRESS_MASK;
    return GPU31S_OK;
}

enum gpu31s_status gpu31s_classify_received(uint64_t word, struct gpu31s_received *result)
{
    struct gpu31s_received decoded = {0};
    if (!result) return GPU31S_ARGUMENT;
    decoded.raw = word;
    decoded.discriminator = (unsigned)((word >> 48) & UINT64_C(0x3f));
    decoded.branch = decoded.discriminator == 2 ? GPU31S_RX_CASE_2 :
                     decoded.discriminator == 9 ? GPU31S_RX_CASE_9 : GPU31S_RX_OTHER;
    *result = decoded;
    return GPU31S_OK;
}

enum gpu31s_status gpu31s_submit_start(const struct gpu31s_transport *transport,
    struct gpu31s_fw_address address, struct gpu31s_submission *result)
{
    struct gpu31s_submission submission = {0};
    enum gpu31s_status status;
    if (!transport || !result) return GPU31S_ARGUMENT;
    if (transport->endpoint_selector != GPU31S_BOOT_ENDPOINT || !transport->submit)
        return GPU31S_BINDING;
    status = gpu31s_encode_start(address, &submission.word);
    if (status != GPU31S_OK) return status;
    submission.transport_status = transport->submit(transport->context, submission.word);
    *result = submission;
    return GPU31S_OK;
}

/* SPDX-License-Identifier: MIT */
#include "gptbat.h"
#include <stddef.h>

enum gpu31q_gptbat_status gpu31q_gptbat_decode(
    struct gpu31q_gptbat_page_number input, struct gpu31q_gptbat_base *output)
{
    if (output == NULL)
        return GPU31Q_GPTBAT_ARGUMENT;
    if (input.value > UINT32_MAX)
        return GPU31Q_GPTBAT_WIDTH;
    output->value = input.value * UINT64_C(16384);
    return GPU31Q_GPTBAT_OK;
}

enum gpu31q_gptbat_status gpu31q_gptbat_encode(
    struct gpu31q_gptbat_base input, struct gpu31q_gptbat_page_number *output)
{
    if (output == NULL)
        return GPU31Q_GPTBAT_ARGUMENT;
    if (input.value >= (UINT64_C(1) << 46))
        return GPU31Q_GPTBAT_WIDTH;
    if (input.value % UINT64_C(16384) != 0)
        return GPU31Q_GPTBAT_ALIGNMENT;
    output->value = input.value / UINT64_C(16384);
    return GPU31Q_GPTBAT_OK;
}

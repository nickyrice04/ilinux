/* SPDX-License-Identifier: MIT */
#ifndef ILINUX_GPU31Q_GPTBAT_H
#define ILINUX_GPU31Q_GPTBAT_H

#include <stdint.h>

/* Distinct format domains. Neither type is a qualified CPU physical address,
 * GPU VA, ASC descriptor address, PTE, readiness indicator or register value. */
struct gpu31q_gptbat_page_number { uint64_t value; };
struct gpu31q_gptbat_base { uint64_t value; };

enum gpu31q_gptbat_status {
    GPU31Q_GPTBAT_OK = 0,
    GPU31Q_GPTBAT_ARGUMENT,
    GPU31Q_GPTBAT_WIDTH,
    GPU31Q_GPTBAT_ALIGNMENT
};

/* Static format only: 32 meaningful page-number bits and 14 offset bits.
 * The API accepts no register address and performs no register/memory access.
 * Zero round-trips but proves no validity, initialization or readiness.
 * Inputs are values, outputs must be valid writable objects. Failure leaves
 * output untouched. Caller must separately establish runtime applicability. */
enum gpu31q_gptbat_status gpu31q_gptbat_decode(
    struct gpu31q_gptbat_page_number input, struct gpu31q_gptbat_base *output);
enum gpu31q_gptbat_status gpu31q_gptbat_encode(
    struct gpu31q_gptbat_base input, struct gpu31q_gptbat_page_number *output);

#endif

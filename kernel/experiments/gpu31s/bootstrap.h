/* SPDX-License-Identifier: MIT */
#ifndef ILINUX_GPU31S_BOOTSTRAP_H
#define ILINUX_GPU31S_BOOTSTRAP_H
#include <stdint.h>

/* Retained-image message representation. Not a native hardware profile. */
#define GPU31S_FW_ADDRESS_LIMIT (UINT64_C(1) << 44)
#define GPU31S_START_HEADER UINT64_C(0x0081000000000000)
#define GPU31S_BOOT_ENDPOINT UINT32_C(0x20)
struct gpu31s_fw_address { uint64_t value; };
enum gpu31s_status { GPU31S_OK = 0, GPU31S_ARGUMENT, GPU31S_ADDRESS_WIDTH,
                    GPU31S_HEADER, GPU31S_BINDING };
enum gpu31s_rx_branch { GPU31S_RX_OTHER = 0, GPU31S_RX_CASE_2, GPU31S_RX_CASE_9 };
struct gpu31s_received {
    uint64_t raw;
    unsigned discriminator;
    enum gpu31s_rx_branch branch;
};

/* Conversion into firmware address space is caller-owned. Integer fit, zero
 * and lack of alignment restrictions are format properties, not authorization
 * to use the address. No CPU/GPU/address-role conversion is performed here. */
enum gpu31s_status gpu31s_encode_start(struct gpu31s_fw_address address, uint64_t *word);
enum gpu31s_status gpu31s_decode_start(uint64_t word, struct gpu31s_fw_address *address);
enum gpu31s_status gpu31s_classify_received(uint64_t word, struct gpu31s_received *result);

/* Injected transport only; no platform IO implementation is supplied.
 * endpoint_selector is a service selector, not ADT GFX/GFX1 or a controller ID.
 * The caller establishes correct firmware/provider/address identity, attachment,
 * locking and lifetime. Valid callback arguments must remain alive throughout.
 * Caller serializes calls and prevents output/input overlap. */
typedef uint32_t (*gpu31s_word_submit)(void *context, uint64_t word);
struct gpu31s_transport {
    uint32_t endpoint_selector;
    gpu31s_word_submit submit;
    void *context;
};
struct gpu31s_submission {
    uint64_t word;
    uint32_t transport_status; /* Uninterpreted; includes failure codes. */
};
/* OK means the injected callback was called once, not successful hardware boot.
 * Format/binding failure calls nothing and leaves output unchanged. No retries,
 * waits, readiness promotion, allocation or implicit endpoint switching. */
enum gpu31s_status gpu31s_submit_start(const struct gpu31s_transport *transport,
    struct gpu31s_fw_address address, struct gpu31s_submission *result);
#endif

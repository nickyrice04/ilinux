/* SPDX-License-Identifier: MIT */
#include "bootstrap.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

struct fake { unsigned calls; uint64_t word; uint32_t status; };
static uint32_t submit(void *context, uint64_t word)
{
    struct fake *fake = context;
    fake->calls++;
    fake->word = word;
    return fake->status;
}
static unsigned groups;
static void formats(void)
{
    struct gpu31s_fw_address a = {0}, decoded = {0};
    uint64_t word = UINT64_MAX;
    unsigned bit;
    assert(gpu31s_encode_start(a, &word) == GPU31S_OK);
    assert(word == UINT64_C(0x0081000000000000));
    assert(gpu31s_decode_start(word, &decoded) == GPU31S_OK && !decoded.value); groups++;

    a.value = GPU31S_FW_ADDRESS_LIMIT - 1;
    assert(gpu31s_encode_start(a, &word) == GPU31S_OK);
    assert(word == UINT64_C(0x00810fffffffffff));
    assert(gpu31s_decode_start(word, &decoded) == GPU31S_OK && decoded.value == a.value); groups++;

    /* Alignment is not inferred from a message's integer field. */
    a.value = 1;
    assert(gpu31s_encode_start(a, &word) == GPU31S_OK);
    assert(word == UINT64_C(0x0081000000000001)); groups++;

    for (bit = 44; bit < 64; bit++) {
        a.value = UINT64_C(1) << bit;
        word = UINT64_C(0xfeed1234);
        assert(gpu31s_encode_start(a, &word) == GPU31S_ADDRESS_WIDTH);
        assert(word == UINT64_C(0xfeed1234));
    }
    a.value = UINT64_MAX;
    assert(gpu31s_encode_start(a, &word) == GPU31S_ADDRESS_WIDTH); groups++;

    for (bit = 44; bit < 64; bit++) {
        decoded.value = 77;
        word = GPU31S_START_HEADER ^ (UINT64_C(1) << bit);
        assert(gpu31s_decode_start(word, &decoded) == GPU31S_HEADER);
        assert(decoded.value == 77);
    }
    assert(gpu31s_decode_start(0, &decoded) == GPU31S_HEADER); groups++;

    assert(gpu31s_encode_start(a, NULL) == GPU31S_ARGUMENT);
    assert(gpu31s_decode_start(0, NULL) == GPU31S_ARGUMENT);
    assert(gpu31s_classify_received(0, NULL) == GPU31S_ARGUMENT); groups++;

    { uint64_t seed = UINT64_C(0x123456789abcdef0); unsigned i;
      for (i = 0; i < 10000; i++) {
          seed = seed * UINT64_C(6364136223846793005) + 1;
          a.value = seed & (GPU31S_FW_ADDRESS_LIMIT-1);
          assert(gpu31s_encode_start(a, &word) == GPU31S_OK);
          assert((word >> 48) == UINT64_C(0x81));
          assert(((word >> 44) & 15) == 0);
          assert(gpu31s_decode_start(word, &decoded) == GPU31S_OK);
          assert(decoded.value == a.value);
      } }
    groups++;
}
static void received(void)
{
    struct gpu31s_received r;
    unsigned code, flags;
    for (code = 0; code < 64; code++) {
        for (flags = 0; flags < 1024; flags++) {
            uint64_t word = ((uint64_t)flags << 54) | ((uint64_t)code << 48) |
                            UINT64_C(0x0000a50f12cafe01);
            enum gpu31s_rx_branch expected = code == 2 ? GPU31S_RX_CASE_2 :
                code == 9 ? GPU31S_RX_CASE_9 : GPU31S_RX_OTHER;
            assert(gpu31s_classify_received(word, &r) == GPU31S_OK);
            assert(r.raw == word && r.discriminator == code && r.branch == expected);
        }
    }
    groups++;
    assert(gpu31s_classify_received(GPU31S_START_HEADER, &r) == GPU31S_OK);
    assert(r.discriminator == 1 && r.branch == GPU31S_RX_OTHER);
    assert(gpu31s_classify_received(UINT64_MAX, &r) == GPU31S_OK);
    assert(r.raw == UINT64_MAX && r.discriminator == 63 && r.branch == GPU31S_RX_OTHER);
    groups++;
}
static void transport(void)
{
    struct fake fake = {0, 0, 0};
    struct gpu31s_transport transport = {GPU31S_BOOT_ENDPOINT, submit, &fake};
    struct gpu31s_submission result;
    unsigned char before[sizeof result];
    struct gpu31s_fw_address address = {UINT64_C(0x123456789ab)};
    unsigned i;
    assert(gpu31s_submit_start(&transport, address, &result) == GPU31S_OK);
    assert(fake.calls == 1 && fake.word == UINT64_C(0x00810123456789ab));
    assert(result.word == fake.word && result.transport_status == 0); groups++;

    fake.status = UINT32_C(0xe00002bc);
    assert(gpu31s_submit_start(&transport, address, &result) == GPU31S_OK);
    assert(fake.calls == 2 && result.transport_status == UINT32_C(0xe00002bc));
    /* A transport error is preserved, with no retry or inferred initialization. */
    groups++;

    memset(&result, 0xa5, sizeof result); memcpy(before, &result, sizeof result);
    for (i = 0; i < 256; i++) {
        if (i == GPU31S_BOOT_ENDPOINT) continue;
        transport.endpoint_selector = i;
        assert(gpu31s_submit_start(&transport, address, &result) == GPU31S_BINDING);
        assert(fake.calls == 2 && memcmp(before, &result, sizeof result) == 0);
    }
    transport.endpoint_selector = UINT32_MAX;
    assert(gpu31s_submit_start(&transport, address, &result) == GPU31S_BINDING);
    assert(fake.calls == 2 && memcmp(before, &result, sizeof result) == 0); groups++;

    transport.endpoint_selector = GPU31S_BOOT_ENDPOINT;
    transport.submit = NULL;
    assert(gpu31s_submit_start(&transport, address, &result) == GPU31S_BINDING);
    assert(fake.calls == 2 && memcmp(before, &result, sizeof result) == 0);
    transport.submit = submit; address.value = GPU31S_FW_ADDRESS_LIMIT;
    assert(gpu31s_submit_start(&transport, address, &result) == GPU31S_ADDRESS_WIDTH);
    assert(fake.calls == 2 && memcmp(before, &result, sizeof result) == 0); groups++;

    assert(gpu31s_submit_start(NULL, address, &result) == GPU31S_ARGUMENT);
    assert(gpu31s_submit_start(&transport, address, NULL) == GPU31S_ARGUMENT);
    assert(fake.calls == 2 && memcmp(before, &result, sizeof result) == 0); groups++;
}
int main(void)
{
    formats(); received(); transport();
    assert(groups == 14);
    puts("GPU31S_BOOTSTRAP_PASS");
    return 0;
}

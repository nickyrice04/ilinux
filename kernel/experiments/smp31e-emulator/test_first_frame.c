/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Userspace instruction differential; run only in the existing ARM64 VM. */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#ifndef __aarch64__
#error "This differential harness requires an ARM64 Linux VM"
#endif
#ifndef __linux__
#error "Do not run this harness on the macOS reference host"
#endif

extern void smp31e_store_frame(void *, uint64_t, uint64_t, uintptr_t *);
extern const uint32_t smp31e_frame_word;

static _Alignas(16) unsigned char stack[16384];

int main(void)
{
    static const uint64_t cases[][2] = {
        {UINT64_C(0x2929292929292929), UINT64_C(0x10000000974)},
        {UINT64_C(0x2929292929292929), UINT64_C(0x1000000097c)},
        {0, UINT64_MAX}, {UINT64_MAX, 0},
    };
    unsigned char expected[sizeof(stack)];
    const size_t top = sizeof(stack);
    size_t i;
    if (smp31e_frame_word != UINT32_C(0xa9be7bfd)) {
        fputs("instruction word mismatch\n", stderr);
        return 1;
    }
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        uintptr_t resulting_sp = 0;
        memset(stack, 0xa5, sizeof(stack));
        memcpy(expected, stack, sizeof(stack));
        memcpy(expected + top - 32, &cases[i][0], sizeof(uint64_t));
        memcpy(expected + top - 24, &cases[i][1], sizeof(uint64_t));
        smp31e_store_frame(stack + top, cases[i][0], cases[i][1], &resulting_sp);
        if (resulting_sp != (uintptr_t)(stack + top - 32) ||
            memcmp(stack, expected, sizeof(stack))) {
            fprintf(stderr, "frame/canary mismatch in case %zu\n", i);
            return 1;
        }
    }
    puts("{\"result\":\"VM_STP_DIFFERENTIAL_PASS\",\"cases\":4,"
         "\"frame_bytes\":32,\"saved_lr_offset\":-24,"
         "\"privileged_instructions\":false,\"native_reset_execution\":\"NOT RUN\"}");
    return 0;
}

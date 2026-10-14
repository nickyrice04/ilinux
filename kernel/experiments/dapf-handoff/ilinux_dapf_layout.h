/* Original iLinux register-layout validation. SPDX-License-Identifier: MIT */
#ifndef ILINUX_DAPF_LAYOUT_H
#define ILINUX_DAPF_LAYOUT_H
#include <stddef.h>
#include <stdint.h>

/* ADT instance records are four little-endian u32 words, one per reg range.
 * Select only DAPF instance zero. GAPF is a different block: never program it
 * with DAPF register offsets. Return 1 found, 0 absent, -1 malformed. */
static int ilinux_dapf_index(const unsigned char *data, size_t len,
                             size_t reg_count, unsigned *out)
{
    unsigned selected = 0;
    int found = 0;
    if (!data || !out || !len || len % 16 || len / 16 != reg_count || reg_count > 256)
        return -1;
    for (size_t i = 0; i < reg_count; i++) {
        const unsigned char *p = data + i * 16;
        uint32_t type = (uint32_t)p[0] | (uint32_t)p[1] << 8 |
                        (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
        uint32_t instance = (uint32_t)p[4] | (uint32_t)p[5] << 8 |
                            (uint32_t)p[6] << 16 | (uint32_t)p[7] << 24;
        if (type == UINT32_C(0x44415046) && instance == 0) {
            if (found) return -1;
            selected = (unsigned)i;
            found = 1;
        }
    }
    if (found) *out = selected;
    return found;
}
#endif

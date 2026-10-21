/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Original t6050 contract. No register accesses; no guessed fallback. */
#ifndef ILINUX_LAYOUT31_H
#define ILINUX_LAYOUT31_H
static unsigned smp31_mask(const unsigned short *desc, unsigned bytes,
                           unsigned cluster, unsigned core)
{
    if (!desc || bytes != 12 || cluster >= 3 || core >= 6)
        return 0;
    for (unsigned i = 0; i < 3; i++)
        if (desc[2 * i] != 6 || desc[2 * i + 1] != 6 * i)
            return 0;
    return 1u << (desc[2 * cluster + 1] + core);
}
#endif

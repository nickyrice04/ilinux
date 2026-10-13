#include "startup_layout.h"

int ilinux_startup_masks(const struct ilinux_cluster_bits *layout, size_t count,
                        unsigned cluster, unsigned core,
                        struct ilinux_startup_masks *out)
{
    uint32_t used = 0;
    if (!layout || !out || !count || count > 32 || cluster >= count)
        return -1;
    for (size_t i = 0; i < count; ++i) {
        unsigned first = layout[i].first, n = layout[i].count;
        if (!n || first >= 32 || n > 32 - first)
            return -1;
        for (unsigned bit = first; bit < first + n; ++bit) {
            uint32_t mask = UINT32_C(1) << bit;
            if (used & mask)
                return -1;
            used |= mask;
        }
    }
    if (core >= layout[cluster].count)
        return -1;
    out->global = UINT32_C(1) << (layout[cluster].first + core);
    out->local = UINT32_C(1) << core;
    return 0;
}

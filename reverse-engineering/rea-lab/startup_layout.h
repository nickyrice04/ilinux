/* Original experiment over supplied topology data. No MMIO or CPU startup.
 * Its output is a candidate layout, NOT validated t6050 register semantics. */
#ifndef ILINUX_STARTUP_LAYOUT_H
#define ILINUX_STARTUP_LAYOUT_H
#include <stddef.h>
#include <stdint.h>

struct ilinux_cluster_bits {
    unsigned count;
    unsigned first;
};

struct ilinux_startup_masks {
    uint32_t global;
    uint32_t local;
};

/* Returns 0 only for a complete non-overlapping 32-bit layout and valid core.
 * Errors leave *out unchanged. The caller must validate hardware separately. */
int ilinux_startup_masks(const struct ilinux_cluster_bits *layout, size_t count,
                        unsigned cluster, unsigned core,
                        struct ilinux_startup_masks *out);
#endif
